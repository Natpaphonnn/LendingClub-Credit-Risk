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

# ---- staging at reporting date 2015-12-31 — E4 definitions (notes/08_prereg_extensions.md), EX-POST illustration
from ecl_lib import staging_e4  # noqa: E402
staging = staging_e4(port, mA, LGD, "2015-12-01")
staging_bs = staging_e4(port, mA, LGD, "2015-12-01", s2=(2, 3), s3_min=4)     # post-hoc, backstop-consistent (gate R8-1)

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
       "total": tot.to_dict(), "staging": staging.to_dict(orient="list"), "staging_backstop": staging_bs.to_dict(orient="list"), "scenarios": scen, "b_passed": b_passed}
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

## Allowance at reporting date 2015-12-31 for the 2015-vintage sub-portfolio — EX-POST ILLUSTRATION (monthly DPD is not in the data)

Pre-registered E4 thresholds (stage 2 = 1–2 missed, stage 3 = ≥ 3 missed):

{r2(staging).to_markdown(index=False)}

Post-hoc, backstop-consistent variant (gate R8-1): the first missed instalment is due in the month after the last payment, so m missed due dates
≈ 30(m − 1) to 30m DPD. Stage 2 = 2–3 missed (≈ > 30 DPD backstop), stage 3 = ≥ 4 missed (≈ ≥ 90 DPD); 1 missed stays in stage 1:

{r2(staging_bs).to_markdown(index=False)}

- Stage definitions (notes/08_prereg_extensions.md §E4): m = instalments due by Dec-2015 and not paid, visible **only for loans that ultimately
  charged off** (delinquent loans that later cured are invisible → stage 2 is understated). DPD at the report date ≈ 30(m − 1) to 30m, so the
  pre-registered labels "1 missed ≈ 30 DPD, 3 ≈ 90 DPD" are one bucket generous (gate R8-1) — see the backstop-consistent variant.
- Scope: 2015 originations only (not the whole book outstanding at Dec-2015); EIR = contractual rate (origination fees ignored).
- Stage 1 → 12-month ECL; stage 2 → lifetime ECL; both from hazards conditional on survival (not conditioned on delinquency → stage 2 allowance
  understated). Stage 3 → LGD × outstanding principal at the first missed payment.
- This uses the final status (hindsight); it illustrates stage mechanics and is not an allowance a lender could have booked at Dec-2015.
  A refit-at-reporting-date version is in reports/phase2/ecl_benchmark.md.

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
