"""C — profit-optimal approval policy (MILP) under approval-volume and bad-rate constraints (prereg §C).
Run only when B failed. Optimise on validation 2014 (model-expected NPV), evaluate on OOT 2015 with realised cash.

Outputs: reports/phase2/policy_C.md, reports/phase2/policy_C.json, reports/figures/p2_C_policy.png
Usage: nice -n 19 .venv/bin/python -I src/phase2/policy_C.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ART, FIG, INTERIM, REP  # noqa: E402
from hazard import cif, hazards  # noqa: E402
sys.path.insert(0, str(ROOT / "src" / "lib"))
from riskutils import annuity_schedule  # noqa: E402
from plotstyle import S, plt, save  # noqa: E402

ART2, REP2 = INTERIM / "p2", ROOT / "reports" / "phase2"
H = 36
APPROVAL_MIN, BAD_MAX = 0.75, 0.11
loans = pd.read_parquet(INTERIM / "p2_loans.parquet")
with open(ART2 / "model_A.pkl", "rb") as fh:
    mA = pickle.load(fh)
LGD = json.loads((REP2 / "ecl.json").read_text())["LGD"]
with open(ART / "scorecard.pkl", "rb") as fh:
    sc1 = pickle.load(fh)
mj = json.loads((REP / "metrics.json").read_text())
CUT1 = mj["cutoff"]["M1_scorecard|validation_2014"]["cutoff"]
CUT2 = mj["cutoff"]["M2_lgbm|validation_2014"]["cutoff"]


def m1_score(d):
    s = np.zeros(len(d), dtype=int)
    for c in sc1["cols"]:
        s += sc1["bins"][c].assign(d[c]).map(sc1["points"][c]).fillna(0).astype(int).to_numpy()
    return s


def exp_npv(d, annual_rate):
    hd, hp = hazards(mA["scaler"].loan_cols(d), mA["B"])
    s_prev, _, _ = cif(hd, hp)
    P = d.funded_amnt.to_numpy()[:, None]
    t = np.arange(1, H + 1)[None, :]
    pmt, ead = annuity_schedule(d.funded_amnt.to_numpy(), d.int_rate.to_numpy(), H)
    pmt = pmt[:, None]
    df = (1 + annual_rate) ** (-t / 12)
    cash = s_prev * ((1 - hd - hp) * pmt + hp * ead + hd * (1 - LGD) * ead)
    return (df * cash).sum(1) - P[:, 0]


va = loans[loans.yr == 2014].reset_index(drop=True)
oo = loans[loans.yr == 2015].reset_index(drop=True)
dec_cuts = np.quantile(va.pd_m2, np.linspace(0, 1, 11)[1:-1])
AMT = [10_000, 20_000]


def cell(d):
    dec = np.searchsorted(dec_cuts, d.pd_m2.to_numpy(), side="right")         # 0 = lowest PD
    amt = np.searchsorted(AMT, d.funded_amnt.to_numpy(), side="left")          # ≤10k, (10k,20k], >20k
    return dec * 3 + amt


res_all = {}
for rate in (0.05, 0.03, 0.08):
    va["npv"], oo["npv"] = exp_npv(va, rate), exp_npv(oo, rate)
    va["cell"], oo["cell"] = cell(va), cell(oo)
    g = va.groupby("cell").agg(n=("npv", "size"), npv=("npv", "sum"), pd_sum=("pd_m2", "sum")).reindex(range(30), fill_value=0)
    N = len(va)
    c = -g.npv.to_numpy()                                                    # maximise NPV
    A = np.vstack([g.n.to_numpy(), g.pd_sum.to_numpy() - BAD_MAX * g.n.to_numpy()])
    cons = LinearConstraint(A, [APPROVAL_MIN * N, -np.inf], [np.inf, 0.0])
    sol = milp(c, constraints=cons, integrality=np.ones(30), bounds=Bounds(0, 1))
    assert sol.success, sol.message
    x = np.round(sol.x).astype(int)
    approved = set(np.where(x == 1)[0])

    def realised_npv(d):
        """EXPLORATORY (not pre-registered): approx. timing — borrower payments spread evenly over MOB 1..n
        (n = months to last payment, ≥1); net recoveries at n + 6; discounted at the same annual rate."""
        n = np.maximum(d.lp_mob.fillna(1).to_numpy(), 1)
        pay = (d.total_pymnt - d.recoveries).to_numpy()
        mr = (1 + rate) ** (1 / 12) - 1
        annuity = (1 - (1 + mr) ** -n) / mr                       # PV of 1 per month for n months
        rec = (d.recoveries - d.collection_recovery_fee).to_numpy() * (1 + mr) ** -(n + 6)
        return pay / n * annuity + rec - d.funded_amnt.to_numpy()

    def evaluate(d, mask, name):
        a = d[mask]
        lab = a[a.bad.notna()]
        prof = (a.total_pymnt - a.collection_recovery_fee - a.funded_amnt)
        return {"policy": name, "approval %": 100 * mask.mean(), "approved bad % (realised)": 100 * lab.bad.mean(),
                "expected bad % (M2 PD)": 100 * a.pd_m2.mean(), "realised profit $m": prof.sum() / 1e6,
                "realised profit / loan $": prof.mean(), "expected NPV $m": a.npv.sum() / 1e6,
                "EXPLORATORY realised NPV $m": realised_npv(a).sum() / 1e6}

    oo["m1"] = m1_score(oo)
    va["m1"] = m1_score(va)
    rows = []
    for nm, d in (("validation 2014", va), ("OOT 2015", oo)):
        rows.append({"set": nm, **evaluate(d, d.cell.isin(approved).to_numpy(), "C: MILP cells")})
        rows.append({"set": nm, **evaluate(d, np.ones(len(d), bool), "approve all")})
        rows.append({"set": nm, **evaluate(d, (d.pd_m2 <= CUT2).to_numpy(), f"Phase 1 M2 cutoff (PD ≤ {CUT2:.4f})")})
        rows.append({"set": nm, **evaluate(d, (d.m1 >= CUT1).to_numpy(), f"Phase 1 M1 cutoff (score ≥ {CUT1})")})
    grid = pd.DataFrame({"decile (0 = lowest PD)": np.repeat(range(10), 3), "amount band": ["≤10k", "10–20k", ">20k"] * 10,
                         "n (2014)": g.n.to_numpy(), "mean PD %": 100 * g.pd_sum.to_numpy() / np.maximum(g.n.to_numpy(), 1),
                         "E[NPV]/loan $ (2014)": g.npv.to_numpy() / np.maximum(g.n.to_numpy(), 1), "approve": x})
    res_all[rate] = {"table": pd.DataFrame(rows), "grid": grid, "approved_cells": sorted(int(i) for i in approved)}

base = res_all[0.05]
md = [f"# C — profit-optimal approval policy (generated by src/phase2/policy_C.py)\n",
      f"MILP over 30 cells (M2-PD decile on 2014 × amount band), maximise expected NPV on validation 2014 subject to approval ≥ "
      f"{100*APPROVAL_MIN:.0f}% and expected bad rate (mean M2 PD) ≤ {100*BAD_MAX:.0f}%. Expected NPV from A hazards, LGD {100*LGD:.1f}%, "
      "discount 5% p.a. Evaluation on OOT 2015 uses realised cash: total_pymnt (incl. recoveries) − collection fee − funded (undiscounted) "
      "= the pre-registered metric. The last column ('EXPLORATORY realised NPV') is NOT pre-registered: realised cash discounted at the same "
      "rate with approximate timing (payments spread evenly to last payment month; recoveries 6 months later).\n",
      "## Results (discount 5%)\n", base["table"].round(2).to_markdown(index=False),
      "\n## Cell decisions (discount 5%)\n", base["grid"].round(2).to_markdown(index=False)]
for rate in (0.03, 0.08):
    t = res_all[rate]["table"]
    md += [f"\n## Sensitivity: discount {int(rate*100)}% — OOT rows\n", t[t.set == "OOT 2015"].round(2).to_markdown(index=False),
           f"\napproved cells: {res_all[rate]['approved_cells']}\n"]
(REP2 / "policy_C.md").write_text("\n".join(md) + "\n")
(REP2 / "policy_C.json").write_text(json.dumps({str(k): {"table": v["table"].to_dict(orient="list"),
                                                         "approved_cells": v["approved_cells"]} for k, v in res_all.items()},
                                               indent=1, default=float))
print("\n".join(md))

t = base["table"]
t = t[t.set == "OOT 2015"].reset_index(drop=True)
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
for ax, col, ttl in ((axes[0], "realised profit $m", "Pre-registered: realised profit, undiscounted"),
                     (axes[1], "EXPLORATORY realised NPV $m", "Exploratory: realised NPV @ 5%")):
    ax.barh(t.policy, t[col], color=[S[1] if p.startswith("C:") else S[0] for p in t.policy])
    for i, v in enumerate(t[col]):
        ax.text(v, i, f" ${v:.0f}m", va="center", fontsize=8)
    ax.set_title(ttl, fontsize=10)
    ax.set_xlim(0, t[col].max() * 1.25)
    ax.set_xlabel("$ million, OOT 2015")
    ax.grid(axis="y", visible=False)
axes[0].set_yticks(range(len(t)), [f"{p}  ({a:.0f}% appr., {b:.1f}% bad)" for p, a, b in
                                   zip(t.policy, t["approval %"], t["approved bad % (realised)"])], fontsize=8)
fig.suptitle("Policy choice evaluated on 2015 loans", x=0.01, ha="left", fontweight="bold")
save(fig, FIG / "p2_C_policy.png")
