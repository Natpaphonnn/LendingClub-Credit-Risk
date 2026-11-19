"""Evaluate M1 vs M2 (+ LC sub_grade benchmark) on validation and OOT; cutoff rule; reason codes (prereg §5-6).

Outputs: reports/phase1/evaluation.md, reports/phase1/metrics.json, reports/figures/p1_*.png
Usage: nice -n 19 .venv/bin/python -I src/phase1/evaluate.py
"""
import json
import pickle
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (ART, B_BOOT, BAD_RATE_TARGET, CATEGORICAL, FEATURES, FIG, OOT, REP, SEED, VALID,  # noqa: E402
                    load_base, split_mask)
from metrics import decile_table, evaluate  # noqa: E402
from plotstyle import S, plt, save  # noqa: E402

df = load_base()
s1 = pd.read_parquet(ART / "scores_m1.parquet")
s2 = pd.read_parquet(ART / "scores_m2.parquet")
df = df.join(s1[["score_m1", "pd_m1"]]).join(s2)
sg = sorted(df.sub_grade.dropna().unique())
df["lc_rank"] = df.sub_grade.map({g: i for i, g in enumerate(sg)}).astype(float)  # A1=0 ... G5=34 (riskier higher)

sections, M = [], {}


def emit(title, body, note=None):
    sections.append(f"## {title}\n\n" + (f"{note}\n\n" if note else "") + body + "\n")
    print(f"\n### {title}\n{body[:2500]}")


def fmt_ci(d, k, scale=1, nd=2):
    v = d.get(k)
    if v is None:
        return ""
    lo, hi = d.get(k + "_lo"), d.get(k + "_hi")
    s = f"{v*scale:.{nd}f}"
    return s + (f" [{lo*scale:.{nd}f}, {hi*scale:.{nd}f}]" if lo is not None else "")


# ------------------------------------------------------------------ discrimination & calibration
for name, window in [("validation_2014", VALID), ("oot_2015", OOT)]:
    d = df[split_mask(df, window) & df.bad.notna()]
    y = d.bad.to_numpy()
    models = {"M1_scorecard": -d.score_m1.to_numpy(), "M2_lgbm": d.pd_m2.to_numpy(), "LC_subgrade": d.lc_rank.to_numpy()}
    pds = {"M1_scorecard": d.pd_m1.to_numpy(), "M2_lgbm": d.pd_m2.to_numpy(), "LC_subgrade": None}
    res, smp = evaluate(models, y, pds, B=B_BOOT, seed=SEED)
    dg = np.array(smp["M2_lgbm"]["gini"]) - np.array(smp["M1_scorecard"]["gini"])
    res["delta_gini_M2_minus_M1"] = {"point": res["M2_lgbm"]["gini"] - res["M1_scorecard"]["gini"],
                                     "lo": float(np.percentile(dg, 2.5)), "hi": float(np.percentile(dg, 97.5))}
    dgl = np.array(smp["LC_subgrade"]["gini"]) - np.array(smp["M1_scorecard"]["gini"])
    res["delta_gini_LC_minus_M1"] = {"point": res["LC_subgrade"]["gini"] - res["M1_scorecard"]["gini"],
                                     "lo": float(np.percentile(dgl, 2.5)), "hi": float(np.percentile(dgl, 97.5))}
    dml = np.array(smp["M2_lgbm"]["gini"]) - np.array(smp["LC_subgrade"]["gini"])
    res["delta_gini_M2_minus_LC"] = {"point": res["M2_lgbm"]["gini"] - res["LC_subgrade"]["gini"],
                                     "lo": float(np.percentile(dml, 2.5)), "hi": float(np.percentile(dml, 97.5))}
    M[name] = {"n": int(len(y)), "bad_rate": float(y.mean()), **res}
    rows = []
    for m in models:
        r = res[m]
        rows.append({"model": m, "Gini (×100)": fmt_ci(r, "gini", 100, 1), "KS (×100)": fmt_ci(r, "ks", 100, 1),
                     "mean PD %": f"{100*r['mean_pd']:.2f}" if "mean_pd" in r else "",
                     "CITL (pp)": fmt_ci(r, "citl", 100, 2), "calib slope": fmt_ci(r, "slope", 1, 3),
                     "Brier": fmt_ci(r, "brier", 1, 4), "log loss": fmt_ci(r, "logloss", 1, 4)})
    dgp = res["delta_gini_M2_minus_M1"]
    emit(f"Discrimination & calibration — {name} (n={len(y):,}, bad rate {100*y.mean():.2f}%)",
         pd.DataFrame(rows).to_markdown(index=False),
         f"95% bootstrap CI in brackets (B={B_BOOT}). CITL = mean PD − observed bad rate. "
         f"Paired ΔGini (M2 − M1) = {100*dgp['point']:.2f} [{100*dgp['lo']:.2f}, {100*dgp['hi']:.2f}] Gini points. "
         f"LC sub_grade − M1 = {100*res['delta_gini_LC_minus_M1']['point']:.2f} "
         f"[{100*res['delta_gini_LC_minus_M1']['lo']:.2f}, {100*res['delta_gini_LC_minus_M1']['hi']:.2f}]. "
         f"M2 − LC sub_grade = {100*res['delta_gini_M2_minus_LC']['point']:.2f} "
         f"[{100*res['delta_gini_M2_minus_LC']['lo']:.2f}, {100*res['delta_gini_M2_minus_LC']['hi']:.2f}] (descriptive benchmark comparison).")
    if name == "oot_2015":
        for m in ("M1_scorecard", "M2_lgbm"):
            t = decile_table(pds[m], y)
            M[name][m]["deciles"] = t.to_dict(orient="list")
        t1 = decile_table(pds["M1_scorecard"], y).rename(columns={"mean_pd": "M1_mean_pd", "bad_rate": "M1_bad_rate"})
        t2 = decile_table(pds["M2_lgbm"], y).rename(columns={"mean_pd": "M2_mean_pd", "bad_rate": "M2_bad_rate"})
        tt = t1.merge(t2.drop(columns="n"), on="decile")
        for c in tt.columns[2:]:
            tt[c] = (100 * tt[c]).round(2)
        emit("Calibration by PD decile — OOT 2015 (%, each model's own deciles)", tt.to_markdown(index=False))
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        lim = max(tt[["M1_mean_pd", "M2_mean_pd", "M1_bad_rate", "M2_bad_rate"]].max()) * 1.05
        ax.plot([0, lim], [0, lim], color="#c3c2b7", linewidth=1, linestyle="--")
        ax.plot(tt.M1_mean_pd, tt.M1_bad_rate, color=S[0], marker="o", label="M1 scorecard")
        ax.plot(tt.M2_mean_pd, tt.M2_bad_rate, color=S[1], marker="o", label="M2 LightGBM")
        ax.set_xlabel("mean predicted PD, %")
        ax.set_ylabel("observed bad rate, %")
        ax.set_title("OOT 2015 calibration by decile")
        ax.legend(frameon=False)
        save(fig, FIG / "p1_calibration_oot.png")

dgp = M["oot_2015"]["delta_gini_M2_minus_M1"]
champion = "M2_lgbm" if (dgp["point"] >= 0.02 and dgp["lo"] > 0) else "M1_scorecard"
M["champion"] = champion
emit("Pre-registered decision rule", f"ΔGini (M2 − M1) on OOT = {100*dgp['point']:.2f} points, 95% CI "
     f"[{100*dgp['lo']:.2f}, {100*dgp['hi']:.2f}]. Rule: M2 champion iff ΔGini ≥ 2.0 and CI lower bound > 0. "
     f"→ **Champion = {champion}**")

# ------------------------------------------------------------------ cutoff rule (validation) applied to OOT
va = df[split_mask(df, VALID) & df.bad.notna()]
oo = df[split_mask(df, OOT) & df.bad.notna()]


def cutoff_m1(d, target):
    t = d.groupby("score_m1").bad.agg(["sum", "size"]).sort_index(ascending=False)
    t["cum_bad"], t["cum_n"] = t["sum"].cumsum(), t["size"].cumsum()
    t["appr_bad_rate"] = t.cum_bad / t.cum_n
    ok = t[t.appr_bad_rate <= target]
    return int(ok.index.min())


def cutoff_m2(d, target):
    t = d.groupby("pd_m2").bad.agg(["sum", "size"]).sort_index()
    t["appr_bad_rate"] = t["sum"].cumsum() / t["size"].cumsum()
    ok = t[t.appr_bad_rate <= target]
    return float(ok.index.max())


c1, c2 = cutoff_m1(va, BAD_RATE_TARGET), cutoff_m2(va, BAD_RATE_TARGET)
rng = np.random.default_rng(SEED + 1)


def policy_stats(d, approve):
    y, a = d.bad.to_numpy(), approve.to_numpy().astype(float)
    n = len(y)
    pt = (a.mean(), (y * a).sum() / a.sum(), (y * (1 - a)).sum() / (1 - a).sum())
    bs = []
    for _ in range(B_BOOT):
        w = np.bincount(rng.integers(0, n, n), minlength=n)
        bs.append(((w * a).sum() / w.sum(), (w * y * a).sum() / (w * a).sum()))
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return pt, lo, hi


rows = []
for m, cut, fn in [("M1_scorecard", c1, lambda d: d.score_m1 >= c1), ("M2_lgbm", c2, lambda d: d.pd_m2 <= c2)]:
    for nm, d in [("validation_2014", va), ("oot_2015", oo)]:
        pt, lo, hi = policy_stats(d, fn(d))
        rows.append({"model": m, "cutoff": cut if m == "M1_scorecard" else f"PD ≤ {cut:.4f}", "set": nm,
                     "approval %": f"{100*pt[0]:.1f} [{100*lo[0]:.1f}, {100*hi[0]:.1f}]",
                     "approved bad %": f"{100*pt[1]:.2f} [{100*lo[1]:.2f}, {100*hi[1]:.2f}]",
                     "declined bad %": f"{100*pt[2]:.2f}", "all bad %": f"{100*d.bad.mean():.2f}"})
        M.setdefault("cutoff", {})[f"{m}|{nm}"] = {"cutoff": cut, "approval": pt[0], "approved_bad": pt[1],
                                                    "approval_ci": [lo[0], hi[0]], "approved_bad_ci": [lo[1], hi[1]],
                                                    "declined_bad": pt[2]}
emit("Cutoff rule — set on validation 2014 (approved bad rate ≤ 11.0%), applied unchanged to OOT 2015",
     pd.DataFrame(rows).to_markdown(index=False), "95% bootstrap CI in brackets.")

# strategy curves
grid = np.linspace(0.5, 1.0, 51)
curves = {}
for m, key, asc in [("M1_scorecard", "score_m1", False), ("M2_lgbm", "pd_m2", True)]:
    for nm, d in [("validation_2014", va), ("oot_2015", oo)]:
        s = d.sort_values(key, ascending=asc).bad.to_numpy()
        cb = np.cumsum(s) / np.arange(1, len(s) + 1)
        curves[(m, nm)] = [float(cb[max(int(g * len(s)) - 1, 0)]) for g in grid]
sc = pd.DataFrame({"approval_%": (100 * grid).round(0)})
for (m, nm), v in curves.items():
    sc[f"{m}|{nm}"] = (100 * np.array(v)).round(2)
emit("Strategy curve — approved bad rate (%) by approval rate", sc.iloc[::5].to_markdown(index=False))
M["strategy_curve"] = sc.to_dict(orient="list")
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for i, m in enumerate(["M1_scorecard", "M2_lgbm"]):
    ax.plot(100 * grid, 100 * np.array(curves[(m, "oot_2015")]), color=S[i], label=f"{m.split('_')[0]} — OOT 2015")
    ax.plot(100 * grid, 100 * np.array(curves[(m, "validation_2014")]), color=S[i], linestyle=":",
            label=f"{m.split('_')[0]} — validation 2014")
ax.axhline(100 * BAD_RATE_TARGET, color="#898781", linewidth=1, linestyle="--")
ax.text(51, 100 * BAD_RATE_TARGET + 0.15, "11% target (set on 2014)", color="#898781", fontsize=8)
ax.set_xlabel("approval rate, %")
ax.set_ylabel("bad rate among approved, %")
ax.set_title("Strategy curve: same approval rate, worse bad rate in 2015")
ax.legend(frameon=False, fontsize=8)
save(fig, FIG / "p1_strategy_curve.png")

# ------------------------------------------------------------------ reason codes (OOT declines)
with open(ART / "scorecard.pkl", "rb") as fh:
    sc_obj = pickle.load(fh)
cols = sc_obj["cols"]
maxp = {c: max(sc_obj["points"][c].values()) for c in cols}
dec1 = oo[oo.score_m1 < c1].index
P = s1.loc[dec1, [f"pts__{c}" for c in cols]]
P.columns = cols
short = pd.DataFrame({c: maxp[c] - P[c] for c in cols})
arr = short.to_numpy()
order = np.argsort(-arr, axis=1)[:, :4]
top = np.array(cols)[order]
top_short = np.take_along_axis(arr, order, axis=1)
top = np.where(top_short > 0, top, None)
r1 = pd.Series(top[:, 0]).value_counts(normalize=True).mul(100).round(1)
r4 = pd.Series(top.ravel()).dropna().value_counts().div(len(dec1)).mul(100).round(1)
rc = pd.DataFrame({"reason (characteristic)": r4.index, "% of declines with it in top-4": r4.values,
                   "% as top-1": [r1.get(k, 0.0) for k in r4.index]})
emit(f"Reason codes — M1, OOT 2015 declines (n={len(dec1):,}, 'points below max' method)",
     rc.to_markdown(index=False))

# M2 TreeSHAP on OOT declines
booster = lgb.Booster(model_file=str(ART / "lgbm.txt"))
cats = json.loads((ART / "lgbm_cats.json").read_text())
dec2 = oo[oo.pd_m2 > c2].index
X = df.loc[dec2, FEATURES].copy()
for c in CATEGORICAL:
    X[c] = pd.Categorical(X[c], categories=cats[c])
contrib = booster.predict(X, pred_contrib=True)[:, :-1]
o2 = np.argsort(-contrib, axis=1)[:, :4]
top2 = np.array(FEATURES)[o2]
top2 = np.where(np.take_along_axis(contrib, o2, axis=1) > 0, top2, None)
r2_1 = pd.Series(top2[:, 0]).value_counts(normalize=True).mul(100).round(1)
emit(f"Reason codes — M2 TreeSHAP, OOT 2015 declines (n={len(dec2):,}) — top-1 frequency (top 12)",
     pd.DataFrame({"feature": r2_1.index[:12], "% as top-1": r2_1.values[:12]}).to_markdown(index=False))
both = dec1.intersection(dec2)
t1 = pd.Series(top[:, 0], index=dec1).loc[both]
t2 = pd.DataFrame(top2, index=dec2).loc[both]
agree1 = float((t1.to_numpy() == t2[0].to_numpy()).mean())
in4 = float(np.mean([a in set(b) for a, b in zip(t1.to_numpy(), t2.to_numpy())]))
M["reason_agreement"] = {"n_both_declined": int(len(both)), "top1_equal": agree1, "m1_top1_in_m2_top4": in4,
                         "n_decl_m1": int(len(dec1)), "n_decl_m2": int(len(dec2))}
emit("Reason-code agreement (applicants declined by both models)",
     f"n = {len(both):,}; M1 top-1 == M2 top-1: {100*agree1:.1f}%; M1 top-1 within M2 top-4: {100*in4:.1f}%. "
     "Low agreement is expected partly because M2 can use correlated substitutes (e.g. avg_cur_bal vs tot_hi_cred_lim).")

(REP / "evaluation.md").write_text("# Phase 1 evaluation (generated by src/phase1/evaluate.py)\n\n" + "\n".join(sections))


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


(REP / "metrics.json").write_text(json.dumps(_clean(M), indent=1))
print("champion:", champion)
