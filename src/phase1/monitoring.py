"""Monitoring backtest 2014Q1..2018Q4 (prereg §7) for M1 and M2.

Signals per issue quarter, with the calendar date each one becomes knowable:
  PSI (score) / CSI (characteristics)  -> quarter end (no labels)
  MOB-12 default A/E                   -> quarter end + 12 + 6 months (charge-off lag); observable if <= as-of 2019-03
  KS on final 36m outcome              -> quarter end + 36 + 6 months; only quarters >= 99% resolved
Deterioration (ground truth) = MOB-12 default rate >= 1.2 x train-window MOB-12 default rate.

Outputs: reports/phase1/monitoring.md, reports/phase1/monitoring.json, reports/figures/p1_psi.png, p1_ae_mob12.png
Usage: nice -n 19 .venv/bin/python -I src/phase1/monitoring.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ART, ASOF, B_BOOT, CHARGEOFF_LAG_M, FEATURES, FIG, REP, SEED, TRAIN, load_base, split_mask  # noqa: E402
from metrics import Disc, psi  # noqa: E402
from plotstyle import INK2, MUTED, S, plt, save  # noqa: E402

df = load_base()
df = df.join(pd.read_parquet(ART / "scores_m1.parquet", columns=["score_m1", "pd_m1"]))
df = df.join(pd.read_parquet(ART / "scores_m2.parquet"))
with open(ART / "scorecard.pkl", "rb") as fh:
    sc = pickle.load(fh)
mj = json.loads((REP / "metrics.json").read_text())
CUT1 = mj["cutoff"]["M1_scorecard|validation_2014"]["cutoff"]
CUT2 = mj["cutoff"]["M2_lgbm|validation_2014"]["cutoff"]
KS_REF = {"M1": mj["validation_2014"]["M1_scorecard"]["ks"], "M2": mj["validation_2014"]["M2_lgbm"]["ks"]}

asof = pd.Timestamp(ASOF)
df["q_end"] = df.issue_dt.dt.to_period("Q").dt.end_time.dt.normalize().dt.to_period("M").dt.to_timestamp()
df["def12"] = (df.default_mob <= 12).astype(float)  # default_mob is NaN for non-defaulted loans -> 0
tr = df[split_mask(df, TRAIN)]
mon = df[df.issue_dt >= pd.Timestamp("2014-01-01")].copy()
quarters = sorted(mon.issue_q.unique())

# reference bands
edges = {"M1": np.unique(np.quantile(tr.score_m1, np.linspace(0, 1, 11)[1:-1])),
         "M2": np.unique(np.quantile(tr.pd_m2, np.linspace(0, 1, 11)[1:-1]))}
col = {"M1": "score_m1", "M2": "pd_m2"}


def band_counts(x, e):
    return np.bincount(np.searchsorted(e, x, side="right"), minlength=len(e) + 1)


ref = {m: band_counts(tr[col[m]].to_numpy(), edges[m]) for m in edges}

# CSI reference (train binning of every candidate feature)
allb = sc["all_bins"]
ref_csi = {}
for f in FEATURES:
    lab = allb[f].assign(tr[f])
    ref_csi[f] = lab.value_counts().reindex(allb[f].labels).fillna(0).to_numpy()

r12 = tr.def12.mean() / tr.bad.mean()   # MOB12 defaults as share of final bads in train
def12_train = tr.def12.mean()
rng = np.random.default_rng(SEED + 2)


def flag(v, amber, red, higher_is_bad=True):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if higher_is_bad:
        return "RED" if v >= red else "AMBER" if v >= amber else "green"
    return "RED" if v < red else "AMBER" if v < amber else "green"


rows, csi_rows = [], []
for q in quarters:
    d = mon[mon.issue_q == q]
    qe = d.q_end.iloc[0]
    r = {"issue_q": q, "n": len(d), "known_PSI": qe.strftime("%Y-%m")}
    for m in ("M1", "M2"):
        r[f"PSI_{m}"] = psi(ref[m], band_counts(d[col[m]].to_numpy(), edges[m]))
    r["score_M1_mean"] = d.score_m1.mean()
    r["score_M1_p10"], r["score_M1_p50"], r["score_M1_p90"] = np.percentile(d.score_m1, [10, 50, 90])
    r["pd_M2_mean"] = d.pd_m2.mean()
    r["pct_below_cut_M1"] = (d.score_m1 < CUT1).mean()
    r["pct_decline_M2"] = (d.pd_m2 > CUT2).mean()
    # CSI
    csis = {}
    for f in FEATURES:
        cur = allb[f].assign(d[f]).value_counts().reindex(allb[f].labels).fillna(0).to_numpy()
        csis[f] = psi(ref_csi[f], cur)
    csi_rows.append({"issue_q": q, **csis})
    r["CSI_n_amber+"] = int(sum(v >= 0.10 for v in csis.values()))
    r["CSI_n_red"] = int(sum(v >= 0.25 for v in csis.values()))
    # MOB12 A/E
    known12 = qe + pd.DateOffset(months=12 + CHARGEOFF_LAG_M)
    r["known_MOB12"] = known12.strftime("%Y-%m")
    if known12 <= asof:
        r["def12_rate"] = d.def12.mean()
        for m, pcol in (("M1", "pd_m1"), ("M2", "pd_m2")):
            r[f"AE12_{m}"] = d.def12.sum() / (d[pcol].sum() * r12)
    # final outcome KS (matured quarters)
    known_f = qe + pd.DateOffset(months=36 + CHARGEOFF_LAG_M)
    r["pct_final"] = d.bad.notna().mean()
    if r["pct_final"] >= 0.99:
        lab = d[d.bad.notna()]
        r["bad_rate_final"] = lab.bad.mean()
        r["known_final"] = known_f.strftime("%Y-%m")
        for m, s in (("M1", -lab.score_m1.to_numpy()), ("M2", lab.pd_m2.to_numpy())):
            dz = Disc(s, lab.bad.to_numpy())
            r[f"KS_{m}"] = dz.auc_ks()[1]
            n = len(lab)
            bs = [dz.auc_ks(np.bincount(rng.integers(0, n, n), minlength=n).astype(float))[1] for _ in range(B_BOOT)]
            r[f"KS_{m}_lo"], r[f"KS_{m}_hi"] = np.percentile(bs, [2.5, 97.5])
    rows.append(r)

T = pd.DataFrame(rows)
C = pd.DataFrame(csi_rows).set_index("issue_q")
for m in ("M1", "M2"):
    T[f"flag_PSI_{m}"] = T[f"PSI_{m}"].map(lambda v: flag(v, 0.10, 0.25))
    T[f"flag_AE12_{m}"] = T.get(f"AE12_{m}", pd.Series(dtype=float)).map(lambda v: flag(v, 1.10, 1.25))
    T[f"flag_KS_{m}"] = T.get(f"KS_{m}", pd.Series(dtype=float)).map(
        lambda v: flag(v, 0.90 * KS_REF[m], 0.80 * KS_REF[m], higher_is_bad=False))
T["deterioration"] = T.def12_rate.map(lambda v: "" if pd.isna(v) else ("YES" if v >= 1.2 * def12_train else "no"))
T["def12_vs_train"] = T.def12_rate / def12_train


# ---------------- tables
def pct(x, nd=2):
    return "" if pd.isna(x) else f"{100*x:.{nd}f}"


def num(x, nd=3):
    return "" if pd.isna(x) else f"{x:.{nd}f}"


t1 = pd.DataFrame({
    "issue_q": T.issue_q, "n": T.n.map("{:,}".format), "PSI M1": T.PSI_M1.map(num), "flag": T.flag_PSI_M1,
    "PSI M2": T.PSI_M2.map(num), "flag ": T.flag_PSI_M2, "CSI ≥0.10 (of 59)": T["CSI_n_amber+"],
    "CSI ≥0.25": T["CSI_n_red"], "M1 score p10/p50/p90": [f"{a:.0f}/{b:.0f}/{c:.0f}" for a, b, c in
                                                           zip(T.score_M1_p10, T.score_M1_p50, T.score_M1_p90)],
    "M1 % < cutoff": T.pct_below_cut_M1.map(lambda v: pct(v, 1)), "M2 mean PD %": T.pd_M2_mean.map(pct),
    "M2 % decline": T.pct_decline_M2.map(lambda v: pct(v, 1)), "known at": T.known_PSI})
t2 = pd.DataFrame({
    "issue_q": T.issue_q, "MOB12 default %": T.def12_rate.map(pct), "× train": T.def12_vs_train.map(lambda v: num(v, 2)),
    "deterioration?": T.deterioration, "A/E M1": T.get("AE12_M1").map(lambda v: num(v, 2)), "flag": T.flag_AE12_M1,
    "A/E M2": T.get("AE12_M2").map(lambda v: num(v, 2)), "flag ": T.flag_AE12_M2, "known at": T.known_MOB12})
t2 = t2[T.def12_rate.notna()]
mat = T[T.get("KS_M1").notna()]
t3 = pd.DataFrame({
    "issue_q": mat.issue_q, "final bad %": mat.bad_rate_final.map(pct),
    "KS M1 ×100": [f"{100*a:.1f} [{100*b:.1f}, {100*c:.1f}]" for a, b, c in zip(mat.KS_M1, mat.KS_M1_lo, mat.KS_M1_hi)],
    "flag": mat.flag_KS_M1,
    "KS M2 ×100": [f"{100*a:.1f} [{100*b:.1f}, {100*c:.1f}]" for a, b, c in zip(mat.KS_M2, mat.KS_M2_lo, mat.KS_M2_hi)],
    "flag ": mat.flag_KS_M2, "known at": mat.known_final})
m1cols = sc["cols"]
t4 = C[m1cols].T.round(3)
t4.index.name = "M1 characteristic CSI"
top_csi = C.max().sort_values(ascending=False).head(12)
t5 = C[top_csi.index].T.round(3)
t5.index.name = "feature (top-12 by max CSI)"


def first(sig, levels=("AMBER", "RED")):
    s = T[T[sig].isin(levels)]
    return None if s.empty else s.iloc[0]


summ = []
for sig, known in [("flag_PSI_M1", "known_PSI"), ("flag_PSI_M2", "known_PSI"), ("flag_AE12_M1", "known_MOB12"),
                   ("flag_AE12_M2", "known_MOB12"), ("flag_KS_M1", "known_final"), ("flag_KS_M2", "known_final")]:
    for lv in (("AMBER", "RED"), ("RED",)):
        f = first(sig, lv)
        summ.append({"signal": sig.replace("flag_", ""), "level": "/".join(lv),
                     "first issue quarter flagged": "never" if f is None else f.issue_q,
                     "knowable at": "" if f is None else f[known]})
fd = T[T.deterioration == "YES"]
summ.append({"signal": "DETERIORATION (MOB12 ≥ 1.2× train)", "level": "truth",
             "first issue quarter flagged": "none" if fd.empty else fd.iloc[0].issue_q,
             "knowable at": "" if fd.empty else fd.iloc[0].known_MOB12})
t6 = pd.DataFrame(summ)

note = (f"Reference = train window (2012-09..2013-12). PSI bands = train deciles. Thresholds (pre-registered): PSI/CSI "
        f"<0.10 green, 0.10–0.25 AMBER, ≥0.25 RED; A/E >1.10 AMBER, >1.25 RED; KS <0.90× validation KS AMBER, <0.80× RED "
        f"(validation KS M1 {100*KS_REF['M1']:.1f}, M2 {100*KS_REF['M2']:.1f}). Train MOB12 default rate = "
        f"{100*def12_train:.2f}%; MOB12/final ratio r = {r12:.3f}. Cutoffs: M1 score ≥ {CUT1}, M2 PD ≤ {CUT2:.4f}.")
md = ["# Phase 1 monitoring backtest (generated by src/phase1/monitoring.py)\n", note + "\n",
      "## 1. Population stability (no labels) — knowable at quarter end\n", t1.to_markdown(index=False),
      "\n## 2. Early performance — MOB-12 default A/E\n",
      "Expected = Σ PD × r (r from train). Observable only when quarter end + 18 months ≤ 2019-03.\n",
      t2.to_markdown(index=False),
      "\n## 3. Final-outcome KS (quarters ≥ 99% resolved)\n", t3.to_markdown(index=False),
      "\n## 4. First flag per signal (detection timing)\n", t6.to_markdown(index=False),
      "\n## 5. CSI — M1 characteristics by issue quarter\n", t4.to_markdown(),
      "\n## 6. CSI — top-12 features by max CSI (all 59 candidates)\n", t5.to_markdown()]
(REP / "monitoring.md").write_text("\n".join(md) + "\n")
T.to_json(REP / "monitoring.json", orient="records", indent=1)
print("\n".join(md))

# ---------------- figures
x = np.arange(len(T))
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(x, T.PSI_M1, color=S[0], marker="o", markersize=4, label="M1 scorecard")
ax.plot(x, T.PSI_M2, color=S[1], marker="o", markersize=4, label="M2 LightGBM")
for yv, lb in ((0.10, "0.10 amber"), (0.25, "0.25 red")):
    ax.axhline(yv, color=MUTED, linewidth=1, linestyle="--")
    ax.text(6, yv + 0.003, lb, color=INK2, fontsize=8, va="bottom", ha="left")
ax.set_xticks(x, T.issue_q, rotation=45, ha="right", fontsize=8)
ax.set_title("Score PSI vs train (2012-09..2013-12), by issue quarter")
ax.legend(frameon=False, loc="upper left")
save(fig, FIG / "p1_psi.png")

T2 = T[T.def12_rate.notna()]
x2 = np.arange(len(T2))
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(x2, T2.AE12_M1, color=S[0], marker="o", markersize=4, label="M1 scorecard")
ax.plot(x2, T2.AE12_M2, color=S[1], marker="o", markersize=4, label="M2 LightGBM")
for yv, lb in ((1.10, "1.10 amber"), (1.25, "1.25 red")):
    ax.axhline(yv, color=MUTED, linewidth=1, linestyle="--")
    ax.text(len(T2) - 0.6, yv, lb, color=INK2, fontsize=8, va="bottom", ha="right")
ax.axhline(1.0, color="#c3c2b7", linewidth=1)
ax.set_xticks(x2, [f"{q}\n({k})" for q, k in zip(T2.issue_q, T2.known_MOB12)], fontsize=7)
ax.set_title("MOB-12 default: actual / expected by issue quarter (date knowable in brackets)")
ax.legend(frameon=False, loc="upper left")
save(fig, FIG / "p1_ae_mob12.png")
