"""E2 — As-of model (realistic deployment): decision date 2014-12-31, label bad12 known by 2014-06 (notes/08_prereg_extensions.md §E2).

Train 2012-09..2013-03, validation 2013-04..2013-06 (36m loans); same monotone LightGBM spec and 12-config grid, selected by validation log loss.
Outputs: reports/phase4/asof_model.md, reports/phase4/asof_model.json, reports/figures/p4_asof_monitoring.png;
         data/interim/p4/asof_lgbm.txt, data/interim/p4/scores_asof.parquet (row-level, git-ignored)
Usage: nice -n 19 .venv/bin/python -I src/phase4/asof_model.py
"""
import itertools
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
for p in ("src/phase1", "src/lib"):
    sys.path.insert(0, str(ROOT / p))
from config import (ART, ASOF, B_BOOT, CATEGORICAL, CHARGEOFF_LAG_M, FEATURES, FIG, INTERIM, MONO_DEC, MONO_INC,  # noqa: E402
                    OOT, SEED, load_base, split_mask)
from metrics import evaluate, psi  # noqa: E402
from plotstyle import MUTED, S, plt, save  # noqa: E402
from riskutils import default_by_mob  # noqa: E402

REP4, ART4 = ROOT / "reports" / "phase4", INTERIM / "p4"
REP4.mkdir(parents=True, exist_ok=True)
ART4.mkdir(parents=True, exist_ok=True)
TR, VA = ("2012-09-01", "2013-03-01"), ("2013-04-01", "2013-06-01")

df = load_base().join(pd.read_parquet(ART / "scores_m2.parquet"))
df["bad12"] = default_by_mob(df.default_mob, 12)
# information-set check: every bad12 event used in fitting happened (first missed payment) by 2014-06
tr_m, va_m = split_mask(df, TR), split_mask(df, VA)
fit = df[tr_m | va_m]
last_event = (fit.issue_dt.dt.to_period("M") + 12).max().to_timestamp()
assert last_event <= pd.Timestamp("2014-06-01"), last_event

cats = {c: sorted(df.loc[tr_m, c].dropna().unique()) for c in CATEGORICAL}
X = df[FEATURES].copy()
for c in CATEGORICAL:
    X[c] = pd.Categorical(X[c], categories=cats[c])
mono = [(-1 if f in MONO_DEC else 1 if f in MONO_INC else 0) for f in FEATURES]
dtr = lgb.Dataset(X[tr_m], df.loc[tr_m, "bad12"], categorical_feature=CATEGORICAL, free_raw_data=False)
dva = lgb.Dataset(X[va_m], df.loc[va_m, "bad12"], reference=dtr, categorical_feature=CATEGORICAL, free_raw_data=False)
grid, best = [], None
for nl, mcs, l2 in itertools.product([15, 31, 63], [200, 1000], [0, 10]):
    params = dict(objective="binary", metric="binary_logloss", learning_rate=0.05, num_leaves=nl, min_child_samples=mcs,
                  lambda_l2=l2, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, monotone_constraints=mono,
                  monotone_constraints_method="advanced", seed=SEED, num_threads=4, verbose=-1, deterministic=True,
                  force_row_wise=True)
    ev = {}
    m = lgb.train(params, dtr, 3000, valid_sets=[dva], valid_names=["v"],
                  callbacks=[lgb.early_stopping(100, verbose=False), lgb.record_evaluation(ev)])
    ll = min(ev["v"]["binary_logloss"])
    grid.append({"num_leaves": nl, "min_child_samples": mcs, "lambda_l2": l2, "best_iter": m.best_iteration, "valid_logloss_bad12": ll})
    if best is None or ll < best[1]:
        best = (m, ll, {"num_leaves": nl, "min_child_samples": mcs, "lambda_l2": l2})
model, ll, cfg = best
model.save_model(str(ART4 / "asof_lgbm.txt"), num_iteration=model.best_iteration)
df["pd12_asof"] = model.predict(X, num_iteration=model.best_iteration)
df[["pd12_asof"]].astype(np.float32).to_parquet(ART4 / "scores_asof.parquet")

# ---- (i)-(iii) OOT 2015
oo = df[split_mask(df, OOT)]
lab = oo[oo.bad.notna()]
res_final, smp = evaluate({"asof_PD12": lab.pd12_asof.to_numpy(), "M2_reference": lab.pd_m2.to_numpy()}, lab.bad.to_numpy(),
                          {"asof_PD12": None, "M2_reference": None}, B=B_BOOT, seed=SEED + 40)
dg = np.array(smp["asof_PD12"]["gini"]) - np.array(smp["M2_reference"]["gini"])
res12, smp12 = evaluate({"asof_PD12": oo.pd12_asof.to_numpy(), "M2_reference": oo.pd_m2.to_numpy()}, oo.bad12.to_numpy(),
                        {"asof_PD12": oo.pd12_asof.to_numpy(), "M2_reference": None}, B=B_BOOT, seed=SEED + 41, slope=False)
out = {"config": cfg, "valid_logloss_bad12": ll, "n_train": int(tr_m.sum()), "n_valid": int(va_m.sum()),
       "train_bad12": float(df.loc[tr_m, "bad12"].mean()), "valid_bad12": float(df.loc[va_m, "bad12"].mean()),
       "oot_final": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in res_final.items()},
       "oot_delta_gini_asof_minus_M2": {"point": float(res_final["asof_PD12"]["gini"] - res_final["M2_reference"]["gini"]),
                                        "lo": float(np.percentile(dg, 2.5)), "hi": float(np.percentile(dg, 97.5))},
       "oot_bad12": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in res12.items()}}

# ---- (iv) realistic monitoring: A/E12 = Σ bad12 / Σ PD12 ; (v) PSI vs as-of train
edges = np.unique(np.quantile(df.loc[tr_m, "pd12_asof"], np.linspace(0, 1, 11)[1:-1]))
bc = lambda x: np.bincount(np.searchsorted(edges, x, side="right"), minlength=len(edges) + 1)  # noqa: E731
ref_counts = bc(df.loc[tr_m, "pd12_asof"].to_numpy())
df["q_end"] = df.issue_dt.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.to_timestamp()
flag = lambda v: "RED" if v > 1.25 else "AMBER" if v > 1.10 else "green"  # noqa: E731
pflag = lambda v: "RED" if v >= 0.25 else "AMBER" if v >= 0.10 else "green"  # noqa: E731
rows = []
for q, d in df[df.issue_dt >= "2015-01-01"].groupby("issue_q"):
    qe = d.q_end.iloc[0]
    r = {"issue_q": q, "n": len(d), "mean PD12 %": 100 * d.pd12_asof.mean(), "PSI": psi(ref_counts, bc(d.pd12_asof.to_numpy()))}
    r["PSI flag"] = pflag(r["PSI"])
    k12 = qe + pd.DateOffset(months=12 + CHARGEOFF_LAG_M)
    if k12 <= pd.Timestamp(ASOF):
        r["bad12 %"] = 100 * d.bad12.mean()
        r["A/E12"] = d.bad12.sum() / d.pd12_asof.sum()
        r["A/E flag"] = flag(r["A/E12"])
        r["knowable"] = k12.strftime("%Y-%m")
    rows.append(r)
M = pd.DataFrame(rows)
out["monitoring"] = M.to_dict(orient="list")
first = M[M["A/E flag"].isin(["AMBER", "RED"])] if "A/E flag" in M else pd.DataFrame()
out["first_amber"] = None if first.empty else {"issue_q": first.issue_q.iloc[0], "knowable": first.knowable.iloc[0]}
firstred = M[M["A/E flag"] == "RED"] if "A/E flag" in M else pd.DataFrame()
out["first_red"] = None if firstred.empty else {"issue_q": firstred.issue_q.iloc[0], "knowable": firstred.knowable.iloc[0]}
(REP4 / "asof_model.json").write_text(json.dumps(out, indent=1, default=float))


def ci(d, k, s=100, nd=1):
    return f"{s*d[k]:.{nd}f} [{s*d[k+'_lo']:.{nd}f}, {s*d[k+'_hi']:.{nd}f}]"


g = pd.DataFrame(grid).sort_values("valid_logloss_bad12").round(5)
Mf = M.copy()
for c in Mf.columns:
    if Mf[c].dtype.kind == "f":
        Mf[c] = Mf[c].round(3)
dgo = out["oot_delta_gini_asof_minus_M2"]
md = f"""# E2 — As-of model (decision date 2014-12-31; pre-registered, commit 4562602)

Train {TR[0][:7]}..{TR[1][:7]} (n = {out['n_train']:,}, bad12 {100*out['train_bad12']:.2f}%), validation {VA[0][:7]}..{VA[1][:7]}
(n = {out['n_valid']:,}, bad12 {100*out['valid_bad12']:.2f}%). Every bad12 event used in fitting occurred by 2014-06 (asserted).
Selected config {cfg} (validation log loss {ll:.5f}).

## OOT 2015 — ranking and calibration (95% bootstrap CI, B = {B_BOOT})

| model | Gini vs final 36m bad | KS vs final | Gini vs bad12 | mean PD12 % | observed bad12 % | CITL12 (pp) |
|---|---|---|---|---:|---:|---|
| **As-of model (bad12, data to 2014-06)** | {ci(res_final['asof_PD12'], 'gini')} | {ci(res_final['asof_PD12'], 'ks')} | {ci(res12['asof_PD12'], 'gini')} | {100*res12['asof_PD12']['mean_pd']:.2f} | {100*res12['asof_PD12']['bad_rate']:.2f} | {ci(res12['asof_PD12'], 'citl', 100, 2)} |
| Reference M2 (full 36m labels, 2012-09..2013-12) | {ci(res_final['M2_reference'], 'gini')} | {ci(res_final['M2_reference'], 'ks')} | {ci(res12['M2_reference'], 'gini')} | – | – | – |

Paired ΔGini (as-of − reference) on final outcome: {100*dgo['point']:.2f} [{100*dgo['lo']:.2f}, {100*dgo['hi']:.2f}].

## Realistic monitoring — what a lender with this model would have seen

A/E12 = Σ bad12 / Σ PD12 (no scaling); knowable at quarter end + 18 months. First amber: {out['first_amber']}; first red: {out['first_red']}.

{Mf.to_markdown(index=False)}

## Grid (selection by validation log loss on bad12)

{g.to_markdown(index=False)}
"""
(REP4 / "asof_model.md").write_text(md)
print(md)

Mk = M[M["A/E12"].notna()] if "A/E12" in M else M.iloc[:0]
fig, ax = plt.subplots(figsize=(9, 3.8))
x = np.arange(len(Mk))
ax.plot(x, Mk["A/E12"], color=S[0], marker="o", markersize=4, label="as-of model: actual / expected defaults by month 12")
for yv, lb in ((1.10, "1.10 amber"), (1.25, "1.25 red")):
    ax.axhline(yv, color=MUTED, linewidth=1, linestyle="--")
    ax.text(0, yv + 0.01, lb, color=MUTED, fontsize=8)
ax.axhline(1.0, color="#c3c2b7", linewidth=1)
ax.set_xticks(x, [f"{q}\n({k})" for q, k in zip(Mk.issue_q, Mk.knowable)], fontsize=7)
ax.set_title("As-of model (built with data to 2014-06): A/E by issue quarter, date knowable in brackets")
ax.legend(frameon=False, loc="upper left")
save(fig, FIG / "p4_asof_monitoring.png")
