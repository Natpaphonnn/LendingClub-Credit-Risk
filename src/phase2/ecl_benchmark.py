"""E5 — ECL benchmark (notes/08_prereg_extensions.md §E5) with gate fixes (reports/quality/gate_round1.md, gate_round2.md).

- (c) primary refit at 2014-12-31: the pre-registered 2012-09 start observes at most MOB 21, so the refit is used only for MOB 1–21
  (fitted with check=False: the unsupported last spline column is zero for t ≤ 24.3 and cannot affect those months); MOB 22–36 hazards
  come from reference A — whose outcomes run past the reporting date, so (c) is a LOWER BOUND on the knowable-only gap (gate R7-1).
- (c'') knowable tail: MOB 22–36 from the 2009-start refit (outcomes to 2014-06); (c2) full-horizon 2009-start refit (degraded pre-2012-09 score).
- (c') as-of sensitivity: score covariate = logit of the as-of PD12 (data to 2014-06) and LGD from defaults known by 2014-06.
- (d) pre-registered "90-DPD" = default at the 3rd missed instalment (d + 2) ≈ 60 DPD at that due date (gate R8-2); (d') post-hoc d + 3 ≈ 90 DPD.
- Descriptive additions: in-sample backtest of A, count × EAD × LGD decomposition, 12-month backtest, MOB-window split.
Outputs: reports/phase2/ecl_benchmark.md, reports/phase2/ecl_benchmark.json
Usage: nice -n 19 .venv/bin/python -I src/phase2/ecl_benchmark.py
"""
import json
import pickle
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CATEGORICAL, FEATURES, INTERIM  # noqa: E402
from ecl_lib import ecl_from, fit_hazard_asof, fit_on, pooled_lgd, realised_loss, schedule, staging_e4  # noqa: E402
from hazard import cif, hazards  # noqa: E402
from riskutils import as_float, code_events, default_by_mob, lgd_ead_at_default, payments_due  # noqa: E402
from scoring import load_categories, score  # noqa: E402

REP2 = ROOT / "reports" / "phase2"
H = 36
loans = pd.read_parquet(INTERIM / "p2_loans.parquet")
loans["issue_dt"] = pd.to_datetime(loans.issue_dt)
trn = loans[(loans.issue_dt >= "2012-09-01") & (loans.issue_dt <= "2013-12-01")]
mA = pickle.load(open(INTERIM / "p2" / "model_A.pkl", "rb"))
dft = trn[trn.loan_status.isin(["Charged Off", "Default"])]

# ---- as-of score for every loan (as-of model: data to 2014-06)
booster = lgb.Booster(model_file=str(INTERIM / "p4" / "asof_lgbm.txt"))
p12, _ = score(booster, loans, FEATURES, CATEGORICAL, load_categories(INTERIM / "p4" / "asof_cats.json"))
p12 = np.clip(p12, 1e-6, 1 - 1e-6)
lp_asof = pd.Series(np.log(p12 / (1 - p12)), index=loans.index)

port = loans[loans.yr == 2015].copy()
port_asof = port.copy()
port_asof["lp"] = lp_asof.loc[port.index].to_numpy()
port, port_asof = port.reset_index(drop=True), port_asof.reset_index(drop=True)

# ---- LGD
LGD_u, _, _ = pooled_lgd(dft)
LGD_d = {k: pooled_lgd(dft, discount_months=k)[0] for k in (6, 12, 24)}
known = dft[(dft.issue_dt.dt.to_period("M") + as_float(dft.default_mob).astype(int)).dt.to_timestamp() <= pd.Timestamp("2014-06-01")]
LGD_known_d12, _, _ = pooled_lgd(known, discount_months=12)
LGD_known_u, _, _ = pooled_lgd(known)

# ---- models
m_ref = {"B": mA["B"], "scaler": mA["scaler"]}
# Gate R7-1 / R2-1: the pre-registered 2012-09 start identifies MOB 1–21 only. Primary (c): refit hazards for MOB 1–21, reference-A hazards
# for MOB 22–36 (stated assumption). Sensitivities: 2009-start refit (full horizon, but pre-2012-09 vintages have a degraded score), as-of score.
m_r14_prereg = fit_hazard_asof(loans, "2014-12-31", check=False)
m_r14_prereg_a = fit_hazard_asof(loans, "2014-12-31", check=False, lp=lp_asof)
m_r14 = fit_hazard_asof(loans, "2014-12-31", start="2009-01-01")
CUT_ID = m_r14_prereg["max_mob_observed"]
m_r15 = fit_hazard_asof(loans, "2015-12-31")
tr90 = trn.copy().reset_index(drop=True)
T, ev = code_events(tr90.loan_status.to_numpy(), tr90.lp_mob, as_float(tr90.default_mob) + 2, tr90.W)
tr90["T"], tr90["event"] = T, ev
m_90 = fit_on(tr90)
tr91 = trn.copy().reset_index(drop=True)
T, ev = code_events(tr91.loan_status.to_numpy(), tr91.lp_mob, as_float(tr91.default_mob) + 3, tr91.W)
tr91["T"], tr91["event"] = T, ev
m_91 = fit_on(tr91)

r, EAD, DF = schedule(port)
real = realised_loss(port)
is_def = port.loan_status.isin(["Charged Off", "Default"]).to_numpy()
dmob = as_float(port.default_mob)


def hz(model, p):
    if "early" in model:                       # composite: identified refit months, reference tail
        hd, hp = hz(model["early"], p if model.get("early_port") is None else model["early_port"])
        td, tp = hz(model["tail"], port)
        hd[:, CUT_ID:], hp[:, CUT_ID:] = td[:, CUT_ID:], tp[:, CUT_ID:]
        return hd, hp
    return hazards(model["scaler"].loan_cols(p), model["B"])


def run(model, lgd, p=port, shift=0):
    hd, hp = hz(model, p)
    return ecl_from(hd, hp, EAD, DF, lgd, ead_shift=shift), hd, hp


def decomposition(model, p=port, shift=0):
    """realised / predicted = (default count ratio) × (EAD per default ratio) × (LGD ratio) — gate R8-1."""
    hd, hp = hz(model, p)
    _, md, _ = cif(hd, hp)
    E = EAD if shift == 0 else EAD[:, np.maximum(np.arange(H) - shift, 0)]
    n_pred, ead_pred = md.sum(), (md * E).sum()
    ead_real = np.where(is_def, port.funded_amnt - port.total_rec_prncp, 0.0)
    n_real = is_def.sum()
    return {"count ratio": n_real / n_pred, "EAD/default ratio": (ead_real.sum() / n_real) / (ead_pred / n_pred),
            "LGD ratio": (real.sum() / ead_real.sum()) / LGD_u,
            "mean default MOB pred": float((md * np.arange(1, H + 1)).sum() / n_pred),
            "mean default MOB actual": float(np.nanmean(np.where(is_def, dmob, np.nan)))}


def window_split(e, cut=21):
    """predicted (undiscounted EL) vs realised loss by default MOB window — gate R2-1."""
    loss_t = e["el_by_t"]
    rl = np.where(is_def & (dmob <= cut), real, 0.0).sum(), np.where(is_def & (dmob > cut), real, 0.0).sum()
    return {f"MOB 1–{cut}": (loss_t[:, :cut].sum() / 1e6, rl[0] / 1e6), f"MOB {cut+1}–36+": (loss_t[:, cut:].sum() / 1e6, rl[1] / 1e6)}


scen = {"(a) reference A, undiscounted LGD": (m_ref, LGD_u, port, 0),
        "(b) reference A, discounted LGD (k=12)": (m_ref, LGD_d[12], port, 0),
        "(c) refit at 2014-12-31 as pre-registered (MOB 1–21) + reference tail, discounted LGD (k=12)":
            ({"early": m_r14_prereg, "tail": m_ref}, LGD_d[12], port, 0),
        "(c') (c) with as-of score and LGD from defaults known by 2014-06":
            ({"early": m_r14_prereg_a, "tail": m_ref, "early_port": port_asof}, LGD_known_d12, port, 0),
        "(c'') (c) with the MOB 22–36 tail from the 2009-start refit (knowable at 2014-12)":
            ({"early": m_r14_prereg, "tail": m_r14}, LGD_d[12], port, 0),
        "(c2) sensitivity: refit from 2009-01 vintages (full horizon; degraded pre-2012-09 score)": (m_r14, LGD_d[12], port, 0),
        "(d) default at 3rd missed instalment (≈ 60 DPD; pre-registered as '90-DPD'), discounted LGD (k=12)": (m_90, LGD_d[12], port, 2),
        "(d') post-hoc: default at 4th missed instalment (≈ 90 DPD), discounted LGD (k=12)": (m_91, LGD_d[12], port, 3)}
rows, out, splits, decs = [], {}, {}, {}
for nm, (mdl, lgd_ecl, p, sh) in scen.items():
    e, hd, hp = run(mdl, lgd_ecl, p, sh)
    lgd_bt = LGD_known_u if nm.startswith("(c')") else LGD_u
    eu, _, _ = run(mdl, lgd_bt, p, sh)
    _, md, _ = cif(hd, hp)
    E = EAD if sh == 0 else EAD[:, np.maximum(np.arange(H) - sh, 0)]
    eu["el_by_t"] = md * lgd_bt * E
    r_ = {"scenario": nm, "mean 12m PD %": 100 * e["pd12"].mean(), "mean lifetime PD %": 100 * e["pdlife"].mean(),
          "day-1 12m ECL $m": e["ecl12"].sum() / 1e6, "lifetime ECL $m": e["ecl_life"].sum() / 1e6}
    if not nm.startswith("(b)"):
        r_["backtest: pred EL (undisc.) $m"] = eu["el_life_undisc"].sum() / 1e6
        r_["realised / predicted"] = real.sum() / eu["el_life_undisc"].sum()
        splits[nm] = window_split(eu)
        decs[nm] = decomposition(mdl, p, sh)
    rows.append(r_)
    out[nm] = r_
T_ = pd.DataFrame(rows)

# ---- 12-month backtest (R8-6): day-1, loans defaulting by MOB 12
eA, hdA, hpA = run(m_ref, LGD_u)
_, mdA, _ = cif(hdA, hpA)
el12 = (mdA[:, :12] * LGD_u * EAD[:, :12]).sum() / 1e6
real12 = np.where(is_def & (dmob <= 12), real, 0.0).sum() / 1e6
pd12_pred, pd12_obs = 100 * eA["pd12"].mean(), 100 * default_by_mob(port.default_mob, 12).mean()

# ---- in-sample backtest of A (R8-1): its own development window
trp = trn.reset_index(drop=True)
_, EADt, _ = schedule(trp)
hdt, hpt = hazards(m_ref["scaler"].loan_cols(trp), m_ref["B"])
_, mdt, _ = cif(hdt, hpt)
in_pred = (mdt * LGD_u * EADt).sum()
in_real = realised_loss(trp).sum()
_, ead_d_tr = lgd_ead_at_default(dft.funded_amnt, dft.total_rec_prncp, dft.recoveries, dft.collection_recovery_fee)
dft_r = dft.reset_index(drop=True)
_, EADd, _ = schedule(dft_r)
sched_at_d = EADd[np.arange(len(dft_r)), np.clip(as_float(dft_r.default_mob).astype(int) - 1, 0, H - 1)]
ead_bias = float(ead_d_tr.sum() / sched_at_d.sum())

# in-sample A/E by issue year of the 2009-start refit (why c2 is not the primary)
trc = loans[(loans.issue_dt >= "2009-01-01") & (loans.issue_dt <= "2014-12-31")].copy()
trc["W_R"] = np.minimum(36, payments_due(trc.issue_dt, "2014-06-01"))
trc = trc[trc.W_R >= 1].copy()
_, evc = code_events(trc.loan_status.to_numpy(), trc.lp_mob, as_float(trc.default_mob), trc.W_R)
hdc, hpc = hazards(m_r14["scaler"].loan_cols(trc), m_r14["B"])
_, mdc, _ = cif(hdc, hpc)
trc["pred"] = (mdc * (np.arange(H)[None, :] < trc.W_R.to_numpy()[:, None])).sum(1)
trc["act"] = evc == 1
c2tab = trc.groupby(trc.issue_dt.dt.year).agg(loans=("act", "size"), mean_lp=("lp", "mean"), pred=("pred", "sum"), act=("act", "sum"))
c2tab["A/E"] = c2tab.act / c2tab.pred
c2tab.index.name = "issue year"

st = staging_e4(port, m_r15, LGD_d[12], "2015-12-01")
info = {k: {kk: v[kk] for kk in ("n_loans", "defaults", "prepays", "issue_window", "max_mob_observed") if kk in v}
        for k, v in (("refit_2014_prereg_2012start", m_r14_prereg), ("refit_2014_from_2009", m_r14), ("refit_2015", m_r15))}
out.update({"LGD_undiscounted": LGD_u, "LGD_discounted": LGD_d, "LGD_known_by_2014_06_disc12": LGD_known_d12,
            "LGD_known_by_2014_06_undisc": LGD_known_u, "n_defaults_known_by_2014_06": len(known),
            "realised_loss_m": real.sum() / 1e6, "models": info, "model_90dpd_defaults": m_90["defaults"], "model_d3_defaults": m_91["defaults"],
            "decomposition": decs, "mob_window_split": {k: {kk: list(vv) for kk, vv in v.items()} for k, v in splits.items()},
            "backtest_12m": {"pred_EL_12m_undisc_m": el12, "realised_12m_m": real12, "ratio": real12 / el12,
                             "pd12_pred_pct": pd12_pred, "pd12_obs_pct": pd12_obs},
            "in_sample_A": {"pred_m": in_pred / 1e6, "realised_m": in_real / 1e6, "ratio": in_real / in_pred,
                            "EAD_at_default_vs_scheduled_train": ead_bias},
            "staging_refit_2015": st.to_dict(orient="list"),
            "refit_2009_insample_by_year": c2tab.reset_index().to_dict(orient="list")})
(REP2 / "ecl_benchmark.json").write_text(json.dumps(out, indent=1, default=float))


def f2(v, c):
    return "" if pd.isna(v) else f"{v:.3f}" if "realised" in c else f"{v:.2f}"


Tf = T_.copy()
for c in Tf.columns[1:]:
    Tf[c] = Tf[c].map(lambda v, c=c: f2(v, c))
D = pd.DataFrame(decs).T.round(3).reset_index().rename(columns={"index": "scenario"})
S = pd.DataFrame([{"scenario": k, **{f"{w} pred / realised $m": f"{a:.1f} / {b:.1f} (×{b/a:.2f})" for w, (a, b) in v.items()}}
                  for k, v in splits.items()])
stf = st.copy()
for c in ("gross EAD $m", "allowance $m"):
    stf[c] = stf[c].round(1)
md = f"""# E5 — ECL benchmark for the 2015 portfolio (pre-registered 4562602; gate-round-1 fixes) — generated by src/phase2/ecl_benchmark.py

LGD (EAD-weighted, {len(dft):,} train-window defaults): undiscounted **{100*LGD_u:.1f}%**; discounted at EIR with recoveries k months after
default: k = 6 → {100*LGD_d[6]:.1f}%, **k = 12 → {100*LGD_d[12]:.1f}%**, k = 24 → {100*LGD_d[24]:.1f}%. Defaults known by 2014-06 only
({len(known):,}): {100*LGD_known_u:.1f}% undiscounted, {100*LGD_known_d12:.1f}% discounted (recovery amounts are still final values — limitation).
Realised net principal loss of the 2015 vintage: ${real.sum()/1e6:.1f}m.

Refits (outcomes observed only up to reporting date − 6 months). Identifiability is asserted for every full-horizon fit; the (c) early model is
fitted with check=False and used only for the MOB range it identifies:
- at 2014-12-31 as pre-registered: issued {info['refit_2014_prereg_2012start']['issue_window'][0]}..{info['refit_2014_prereg_2012start']['issue_window'][1]},
  {info['refit_2014_prereg_2012start']['n_loans']:,} loans, max MOB observed **{CUT_ID}**, {info['refit_2014_prereg_2012start']['defaults']:,} defaults
- at 2015-12-31 (staging): issued {info['refit_2015']['issue_window'][0]}..{info['refit_2015']['issue_window'][1]}, {info['refit_2015']['n_loans']:,} loans,
  max MOB observed {info['refit_2015']['max_mob_observed']} (all spline columns supported; MOB 34–36 extrapolate the last cubic piece)
- **Gate fix (R7-1 / R2-1):** the first version reported the 2014-12 refit over 36 months, but with max MOB {CUT_ID} its last spline coefficient is
  unidentified and MOB {CUT_ID+1}–36 hazards were extrapolation (the reported 1.10× was an artefact; fit_mnl now refuses such a design). The
  pre-registered refit is therefore used only for MOB 1–{CUT_ID}; MOB {CUT_ID+1}–36 hazards come from reference A — **a stated assumption, not
  a pre-registered element** (bug-driven deviation, notes/10). Reference A was fitted on outcomes observed after the reporting date, so (c) is a
  **lower bound** on the knowable-only gap; (c'') takes the tail from the 2009-start refit instead (all inputs knowable except the score and
  final recovery amounts).
- (c2) sensitivity: refit on vintages from 2009-01 (outcomes still only to 2014-06; {info['refit_2014_from_2009']['n_loans']:,} loans, max MOB
  {info['refit_2014_from_2009']['max_mob_observed']}). Not the primary: M2 scores pre-2012-09 loans with several bureau fields missing, so their
  score is inflated relative to their outcomes, which flattens the fitted score slope (in-sample A/E by issue year below).
- Scores: (c) uses the reference M2 score (trained on full 36-month labels → post-2014 information); (c') replaces it with the as-of model's PD12
  (data to 2014-06) and uses LGD from defaults known by 2014-06. (d) 3rd-missed-instalment model: {m_90['defaults']:,} defaults;
  (d') 4th: {m_91['defaults']:,} (horizon 36: defaults with d + k > 36 are censored — a slight bias against these definitions). Mapping: the
  first missed instalment is due in month d, so at the k-th missed due date the loan is ≈ 30(k − 1) days past due (gate R8-1/R8-2).

## Scenarios

{Tf.to_markdown(index=False)}

Backtest columns use undiscounted LGD so they compare like-for-like with realised net principal loss.

## Decomposition of realised / predicted (gate R8-1): count × EAD per default × LGD

{D.to_markdown(index=False)}

In-sample backtest of A on its own development window (2012-09..2013-12): realised ${in_real/1e6:.1f}m vs predicted ${in_pred/1e6:.1f}m
(**×{in_real/in_pred:.3f}**). Actual exposure at default (funded − principal received) is ×{ead_bias:.3f} the scheduled balance at the default
month on train defaults: the scheduled-balance EAD understates exposure at default, so part of every gap is structural, not drift.

## Predicted vs realised by default-MOB window (gate R2-1)

{S.to_markdown(index=False)}

(c2) in-sample check — predicted vs actual defaults within each loan's observed window (fit data):

{c2tab.round(3).to_markdown()}

## 12-month backtest (gate R8-6)

Day 1, reference A: undiscounted 12-month EL ${el12:.1f}m vs realised loss of loans defaulting by MOB 12 ${real12:.1f}m (×{real12/el12:.2f});
12-month PD {pd12_pred:.2f}% predicted vs {pd12_obs:.2f}% observed.

## Staging at 2015-12-31 under the refit-at-2015-12-31 model and discounted LGD — EX-POST ILLUSTRATION

{stf.to_markdown(index=False)}

Same definitions and caveats as reports/phase2/ecl.md (monthly DPD is not in the data; cured delinquencies are invisible; stage 2 understated).
"""
(REP2 / "ecl_benchmark.md").write_text(md)
print(md)
