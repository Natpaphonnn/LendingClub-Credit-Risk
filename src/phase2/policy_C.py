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
        pts = sc1["bins"][c].assign(d[c]).map(sc1["points"][c])
        assert pts.notna().all(), c
        s += pts.astype(int).to_numpy()
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

    # best single loan-level PD threshold on 2014 under the same objective and constraints (gate R9-4)
    vs = va.sort_values("pd_m2")
    cum_n = np.arange(1, len(vs) + 1)
    feas = (cum_n >= APPROVAL_MIN * len(vs)) & (vs.pd_m2.cumsum().to_numpy() / cum_n <= BAD_MAX)
    k_best = int(np.argmax(np.where(feas, vs.npv.cumsum().to_numpy(), -np.inf)))
    thr = float(vs.pd_m2.iloc[k_best])
    oo["m1"] = m1_score(oo)
    va["m1"] = m1_score(va)
    rows = []
    for nm, d in (("validation 2014", va), ("OOT 2015", oo)):
        rows.append({"set": nm, **evaluate(d, d.cell.isin(approved).to_numpy(), "C: MILP cells")})
        rows.append({"set": nm, **evaluate(d, np.ones(len(d), bool), "approve all")})
        rows.append({"set": nm, **evaluate(d, (d.pd_m2 <= CUT2).to_numpy(), f"Phase 1 M2 cutoff (PD ≤ {CUT2:.4f})")})
        rows.append({"set": nm, **evaluate(d, (d.m1 >= CUT1).to_numpy(), f"Phase 1 M1 cutoff (score ≥ {CUT1})")})
        rows.append({"set": nm, **evaluate(d, (d.pd_m2 <= thr).to_numpy(), f"single PD threshold, same objective (PD ≤ {thr:.4f})")})

    # paired bootstrap of policy differences on OOT 2015 (gate R9-1): loan-level and issue-month block, B = 500
    masks = {"C": oo.cell.isin(approved).to_numpy(), "M2": (oo.pd_m2 <= CUT2).to_numpy(), "all": np.ones(len(oo), bool)}
    prof = (oo.total_pymnt - oo.collection_recovery_fee - oo.funded_amnt).to_numpy()
    npvr = realised_npv(oo)
    mon_ = oo.issue_dt.dt.month.to_numpy() - 1
    rng_b = np.random.default_rng(20261119 + int(rate * 1000))
    diffs = {}
    for kind in ("loan", "month"):
        bs = {k: [] for k in ("C−M2 profit", "C−M2 NPV", "C−all profit", "C−all NPV")}
        for _ in range(500):
            w = (np.bincount(rng_b.integers(0, len(oo), len(oo)), minlength=len(oo)) if kind == "loan"
                 else np.bincount(rng_b.integers(0, 12, 12), minlength=12)[mon_]).astype(float)
            for nmv, v in (("profit", prof), ("NPV", npvr)):
                bs[f"C−M2 {nmv}"].append((w * v * (masks["C"].astype(float) - masks["M2"])).sum() / 1e6)
                bs[f"C−all {nmv}"].append((w * v * (masks["C"].astype(float) - masks["all"])).sum() / 1e6)
        for k, v in bs.items():
            pt = ((prof if "profit" in k else npvr) * (masks["C"].astype(float) - masks["M2" if "M2" in k else "all"])).sum() / 1e6
            diffs[(k, kind)] = (pt, *np.percentile(v, [2.5, 97.5]))
    grid = pd.DataFrame({"decile (0 = lowest PD)": np.repeat(range(10), 3), "amount band": ["≤10k", "10–20k", ">20k"] * 10,
                         "n (2014)": g.n.to_numpy(), "mean PD %": 100 * g.pd_sum.to_numpy() / np.maximum(g.n.to_numpy(), 1),
                         "E[NPV]/loan $ (2014)": g.npv.to_numpy() / np.maximum(g.n.to_numpy(), 1), "approve": x})
    dtab = pd.DataFrame([{"difference ($m, OOT 2015)": k, "bootstrap": kind, "point": round(v[0], 2), "95% CI": f"[{v[1]:.2f}, {v[2]:.2f}]"}
                         for (k, kind), v in diffs.items()])
    # demo aggregates (exploratory): single PD cutoff swept on 2015 loans — approval %, realised approved bad %, realised NPV $m
    grid_c = np.round(np.arange(0.05, 0.4001, 0.0025), 4)
    labd = oo.bad.notna().to_numpy()
    curve = {"cutoff": grid_c.tolist(), "approval %": [], "approved bad %": [], "realised NPV $m": []}
    for cth in grid_c:
        mk = (oo.pd_m2 <= cth).to_numpy()
        curve["approval %"].append(100 * mk.mean())
        curve["approved bad %"].append(100 * oo.bad.to_numpy()[mk & labd].mean())
        curve["realised NPV $m"].append(npvr[mk].sum() / 1e6)
    mC_ = oo.cell.isin(approved).to_numpy()
    marks = {"MILP": {"approval %": 100 * mC_.mean(), "approved bad %": 100 * oo.bad.to_numpy()[mC_ & labd].mean(),
                      "realised NPV $m": npvr[mC_].sum() / 1e6},
             "pre-registered cutoff": {"cutoff": CUT2, "approval %": 100 * (oo.pd_m2 <= CUT2).mean(),
                                       "approved bad %": 100 * oo.bad.to_numpy()[(oo.pd_m2 <= CUT2).to_numpy() & labd].mean(),
                                       "realised NPV $m": npvr[(oo.pd_m2 <= CUT2).to_numpy()].sum() / 1e6}}
    res_all[rate] = {"table": pd.DataFrame(rows), "grid": grid, "approved_cells": sorted(int(i) for i in approved), "diffs": dtab,
                     "curve": curve, "marks": marks}

base = res_all[0.05]
md = [f"# C — profit-optimal approval policy (generated by src/phase2/policy_C.py)\n",
      f"MILP over 30 cells (M2-PD decile on 2014 × amount band), maximise expected NPV on validation 2014 subject to approval ≥ "
      f"{100*APPROVAL_MIN:.0f}% and expected bad rate (mean M2 PD) ≤ {100*BAD_MAX:.0f}%. Expected NPV from A hazards, LGD {100*LGD:.1f}%, "
      "discount 5% p.a. Evaluation on OOT 2015 uses realised cash: total_pymnt (incl. recoveries) − collection fee − funded (undiscounted) "
      "= the pre-registered metric. The last column ('EXPLORATORY realised NPV') is NOT pre-registered: realised cash discounted at the same "
      "rate with approximate timing (payments spread evenly to last payment month; recoveries 6 months later).\n",
      "## Results (discount 5%)\n", base["table"].round(2).to_markdown(index=False),
      "\n## Paired bootstrap of policy differences on OOT 2015 (discount 5%; gate R9-1)\n", base["diffs"].to_markdown(index=False),
      "\n'C' is optimal only over the 30 pre-registered cells: a single loan-level PD threshold chosen on 2014 under the same objective and "
      "constraints is shown as a benchmark row (gate R9-4). The 11% constraint is on mean M2 PD, which under-predicts already on 2014 "
      "(realised approved bad rate on 2014 is in the table) — the breach is not only drift (gate R9-3).\n",
      "\n## Cell decisions (discount 5%)\n", base["grid"].round(2).to_markdown(index=False)]
for rate in (0.03, 0.08):
    t = res_all[rate]["table"]
    md += [f"\n## Sensitivity: discount {int(rate*100)}% — OOT rows\n", t[t.set == "OOT 2015"].round(2).to_markdown(index=False),
           "\nPaired bootstrap differences:\n", res_all[rate]["diffs"].to_markdown(index=False),
           f"\napproved cells: {res_all[rate]['approved_cells']}\n"]
(REP2 / "policy_C.md").write_text("\n".join(md) + "\n")
(REP2 / "policy_C.json").write_text(json.dumps({str(k): {"table": v["table"].to_dict(orient="list"),
                                                         "approved_cells": v["approved_cells"],
                                                         "diffs": v["diffs"].to_dict(orient="list"),
                                                         "curve": v["curve"], "marks": v["marks"]} for k, v in res_all.items()},
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
