"""TFRS 9-style ECL for the OOT portfolio (36m loans issued 2015) — prereg §ECL.

PD (marginal by month) from A (score-only hazard); if macro_B.json says B passed, also baseline/adverse/weighted from B.
LGD pooled from train defaults; EAD = scheduled annuity balance; discount at EIR.
Outputs: reports/phase2/ecl.md, reports/phase2/ecl.json, reports/figures/p2_ecl_backtest.png
Usage: nice -n 19 .venv/bin/python -I src/phase2/ecl.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FIG, INTERIM, SEED  # noqa: E402
from hazard import cif, hazards  # noqa: E402
sys.path.insert(0, str(ROOT / "src" / "lib"))
from riskutils import annuity_schedule, lgd_ead_at_default, payments_due  # noqa: E402
from plotstyle import S, plt, save  # noqa: E402

ART2, REP2 = INTERIM / "p2", ROOT / "reports" / "phase2"
H = 36
loans = pd.read_parquet(INTERIM / "p2_loans.parquet")
trn = loans[(loans.issue_dt >= "2012-09-01") & (loans.issue_dt <= "2013-12-01")]
port = loans[loans.yr == 2015].reset_index(drop=True)
with open(ART2 / "model_A.pkl", "rb") as fh:
    mA = pickle.load(fh)
mB = json.loads((REP2 / "macro_B.json").read_text())
b_passed = mB["decision"].startswith("B PASSES")

# ---- LGD (train defaults)
dft = trn[trn.loan_status.isin(["Charged Off", "Default"])].copy()
dft["lgd"], dft["ead_d"] = lgd_ead_at_default(dft.funded_amnt, dft.total_rec_prncp, dft.recoveries, dft.collection_recovery_fee)
dft = dft[dft.ead_d > 0]
LGD = float((dft.lgd * dft.ead_d).sum() / dft.ead_d.sum())
rng = np.random.default_rng(SEED + 11)
bs = []
lg, ed = dft.lgd.to_numpy(), dft.ead_d.to_numpy()
for _ in range(500):
    i = rng.integers(0, len(dft), len(dft))
    bs.append((lg[i] * ed[i]).sum() / ed[i].sum())
LGD_CI = np.percentile(bs, [2.5, 97.5])
qcut = np.quantile(trn.pd_m2, [0.2, 0.4, 0.6, 0.8])
dft["band"] = 1 + np.searchsorted(qcut, dft.pd_m2, side="right")   # band 1 = safest .. 5 = riskiest
lgd_band = dft.groupby("band").apply(lambda g: (g.lgd * g.ead_d).sum() / g.ead_d.sum(), include_groups=False)

# ---- EAD schedule and discount factors
r = (port.int_rate.to_numpy() / 1200.0)[:, None]
t = np.arange(1, H + 1)[None, :]
_, EAD = annuity_schedule(port.funded_amnt.to_numpy(), port.int_rate.to_numpy(), H)   # balance at start of month t
DF = (1 + r) ** (-t)


def ecl_from(hd, hp):
    s_prev, md, C = cif(hd, hp)
    loss = md * LGD * EAD
    return {"pd12": C[:, 11], "pdlife": C[:, -1], "ecl12": (loss * DF)[:, :12].sum(1), "ecl_life": (loss * DF).sum(1),
            "el_life_undisc": loss.sum(1), "s_prev": s_prev, "hd": hd}


L = mA["scaler"].loan_cols(port)
hdA, hpA = hazards(L, mA["B"])
A = ecl_from(hdA, hpA)

# ---- realised loss (net principal loss) for backtest
is_def = port.loan_status.isin(["Charged Off", "Default"]).to_numpy()
real_loss = np.where(is_def, port.funded_amnt - port.total_rec_prncp - port.recoveries + port.collection_recovery_fee, 0.0)
port["band"] = 1 + np.searchsorted(qcut, port.pd_m2, side="right")
port["el_pred"], port["loss_real"] = A["el_life_undisc"], real_loss
port["ecl12"], port["ecl_life"] = A["ecl12"], A["ecl_life"]


def agg(g):
    return pd.Series({"loans": len(g), "funded $m": g.funded_amnt.sum() / 1e6, "pred lifetime PD %": 100 * A["pdlife"][g.index].mean(),
                      "actual default %": 100 * g.loan_status.isin(["Charged Off", "Default"]).mean(),
                      "pred EL (undisc) $m": g.el_pred.sum() / 1e6, "realised loss $m": g.loss_real.sum() / 1e6,
                      "realised / predicted": g.loss_real.sum() / g.el_pred.sum(),
                      "day-1 ECL 12m $m": g.ecl12.sum() / 1e6, "lifetime ECL $m": g.ecl_life.sum() / 1e6})


by_q = port.groupby("issue_q").apply(agg, include_groups=False).reset_index()
by_b = port.groupby("band").apply(agg, include_groups=False).reset_index()
tot = agg(port)

# ---- staging at reporting date 2015-12-31
rep = pd.Timestamp("2015-12-01")
# payments fall due at issue + t (MOB t); by Dec-2015, `age` payments have fallen due -> next exposure month is MOB age+1.
# (Fixed off-by-one in quality step: previously age included +1, which put Jan-2016 first-missed payments into stage 3.)
age = payments_due(port.issue_dt, "2015-12-01")
d_age = port.default_mob.astype("float64").to_numpy()      # MOB of first missed payment (NaN if no default)
p_age = np.where(port.event.to_numpy() == 2, port["T"].to_numpy(), np.inf)
stage3 = is_def & (d_age <= age)             # first missed payment due on or before Dec-2015 (pre-registered)
gone = (~stage3) & (p_age <= age)            # paid off on or before Dec-2015
perf = ~stage3 & ~gone
s_prev, hd = A["s_prev"], A["hd"]
ecl12_rep = np.zeros(len(port))
ecl_life_rep = np.zeros(len(port))
for i in np.where(perf)[0]:
    a = int(age[i])
    if a >= H:
        continue
    sa = s_prev[i, a]                       # survival to start of MOB a+1 (index a)
    md_c = s_prev[i, a:] * hd[i, a:] / sa   # conditional marginal default for MOB a+1..36
    df_c = (1 + r[i, 0]) ** -np.arange(1, H - a + 1)
    loss = md_c * LGD * EAD[i, a:] * df_c
    ecl12_rep[i], ecl_life_rep[i] = loss[:12].sum(), loss.sum()
ead_rep = np.array([EAD[i, min(int(age[i]), H - 1)] for i in range(len(port))])          # performing: balance at reporting
d_idx = np.clip(np.nan_to_num(d_age, nan=1).astype(int) - 1, 0, H - 1)
ead_rep = np.where(stage3, EAD[np.arange(len(port)), d_idx], ead_rep)                # stage 3: balance at default month
st3_alloc = (LGD * ead_rep * stage3).sum()
missed_at_rep = age - d_age + 1                     # payments missed by Dec-2015 (first missed = MOB d_age, due issue + d_age)
n_lt90 = int((stage3 & (missed_at_rep < 3)).sum())
staging = pd.DataFrame([
    {"stage": "Stage 1 (performing; 12-month ECL)", "loans": int(perf.sum()), "gross EAD $m": ead_rep[perf].sum() / 1e6,
     "allowance $m": ecl12_rep[perf].sum() / 1e6},
    {"stage": "Stage 2 (SICR) — NOT allocable: no monthly DPD / refreshed PD in data", "loans": 0, "gross EAD $m": 0.0,
     "allowance $m": 0.0},
    {"stage": "  memo: if ALL performing were Stage 2 (lifetime ECL) — upper bound", "loans": int(perf.sum()),
     "gross EAD $m": ead_rep[perf].sum() / 1e6, "allowance $m": ecl_life_rep[perf].sum() / 1e6},
    {"stage": "Stage 3 (defaulted by Dec-2015; LGD × EAD)", "loans": int(stage3.sum()),
     "gross EAD $m": ead_rep[stage3].sum() / 1e6, "allowance $m": st3_alloc / 1e6},
    {"stage": "derecognised (prepaid by Dec-2015)", "loans": int(gone.sum()), "gross EAD $m": 0.0, "allowance $m": 0.0}])
staging["coverage %"] = (100 * staging["allowance $m"] / staging["gross EAD $m"].replace(0, np.nan)).round(2)

# ---- scenarios (only if B passed)
scen_md, scen = "", {}
if b_passed:
    from rule_B import macro_path  # noqa: E402
    with open(ART2 / "model_B_primary.pkl", "rb") as fh:
        mBm = pickle.load(fh)
    LB = mBm["scaler"].loan_cols(port)
    for nm in ("baseline", "adverse"):
        h1, h2 = hazards(LB, mBm["B_macro"], macro_path(port, nm))
        e = ecl_from(h1, h2)
        scen[nm] = {k: float(e[k].sum()) for k in ("ecl12", "ecl_life", "el_life_undisc")} | {"mean_pdlife": float(e["pdlife"].mean())}
    scen["weighted_70_30"] = {k: 0.7 * scen["baseline"][k] + 0.3 * scen["adverse"][k] for k in scen["baseline"]}
    scen_md = "## Macro scenarios (B passed)\n\n" + pd.DataFrame(scen).T.to_markdown() + "\n"
else:
    scen_md = ("## Macro scenarios\n\nNot produced: B failed the pre-registered Plan B rule (see reports/phase2/macro_B.md). "
               "ECL above is score-only (through-the-cycle-ish, no forward-looking overlay) — a TFRS 9 gap stated plainly.\n")

out = {"LGD": LGD, "LGD_CI": LGD_CI.tolist(), "LGD_by_band": lgd_band.to_dict(), "n_train_defaults": len(dft),
       "total": tot.to_dict(), "staging": staging.to_dict(orient="list"), "scenarios": scen, "b_passed": b_passed}
(REP2 / "ecl.json").write_text(json.dumps(out, indent=1, default=float))


def r2(d):
    d = d.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].round(3)
    return d


md = f"""# TFRS 9-style ECL — OOT portfolio: 36m loans issued 2015 (generated by src/phase2/ecl.py)

PD: A model (score-only competing-risks hazard, fit 2012-09..2013-12). **LGD = {100*LGD:.1f}%** [{100*LGD_CI[0]:.1f}, {100*LGD_CI[1]:.1f}]
(EAD-weighted, {len(dft):,} train defaults; LGD_i = 1 − (recoveries − collection fee) / (funded − principal received)).
EAD = scheduled annuity balance; prepayment via competing risk. Discount = EIR (int_rate/12).

LGD by M2-PD quintile band (1 = safest; train cut points), sensitivity only: {', '.join(f'B{int(k)} {100*v:.1f}%' for k, v in lgd_band.items())}

## Portfolio totals (day 1 = at origination; all loans Stage 1 at origination)

{r2(tot.to_frame('2015 portfolio').T).to_markdown(index=False)}

## Backtest by issue quarter — predicted lifetime EL (undiscounted, at origination) vs realised net principal loss

{r2(by_q).to_markdown(index=False)}

## Backtest by risk band (M2 PD quintile on train; 5 = riskiest)

{r2(by_b).to_markdown(index=False)}

## Allowance at reporting date 2015-12-31 (stage logic stated plainly)

{r2(staging).to_markdown(index=False)}

- Stage 1 = performing at Dec-2015 → 12-month ECL from remaining life (hazards conditional on survival to Dec-2015).
- Stage 2 needs a significant-increase-in-credit-risk test (30 DPD backstop or a refreshed lifetime PD vs origination). LC data has
  no monthly delinquency history and no refreshed scores, so stage 2 **cannot be allocated**; the memo row shows the lifetime-ECL upper bound.
- Stage 3 = default month (last payment + 1) ≤ Dec-2015 → allowance = LGD × scheduled EAD at that point (simplification).
- **EX-POST / HINDSIGHT (independent review MA-5):** stage 3 membership uses the *final* status (the loan later charged off). At the
  reporting date {n_lt90:,} of the {int(stage3.sum()):,} stage-3 loans had fewer than 3 missed payments (< 90 DPD), so a real bank would
  not yet have classed them as credit-impaired; the same last-payment proxy could flag ≥ 30 DPD for stage 2, which this table does not do.
  Treat this table as an illustration of the stage mechanics, not as an allowance a lender could have booked at Dec-2015.

{scen_md}
"""
(REP2 / "ecl.md").write_text(md)
print(md)

fig, ax = plt.subplots(figsize=(7.5, 3.8))
x = np.arange(len(by_q))
ax.bar(x - 0.2, by_q["pred EL (undisc) $m"], width=0.4, color=S[0], label="predicted lifetime EL at origination")
ax.bar(x + 0.2, by_q["realised loss $m"], width=0.4, color=S[1], label="realised net principal loss")
for i, v in enumerate(by_q["realised / predicted"]):
    ax.text(i, max(by_q["pred EL (undisc) $m"][i], by_q["realised loss $m"][i]) * 1.02, f"×{v:.2f}", ha="center", fontsize=8)
ax.set_xticks(x, by_q.issue_q)
ax.set_ylabel("$ million")
ax.set_title("2015 vintage: lifetime expected loss vs what was actually lost")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.grid(axis="x", visible=False)
save(fig, FIG / "p2_ecl_backtest.png")
