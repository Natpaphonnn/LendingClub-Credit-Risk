"""Article figures (8), regenerated in one consistent style. Aggregates only.

Usage: nice -n 19 .venv/bin/python -I src/report/article_figures.py
Output: reports/figures/article/fig{1..8}_*.png

Thai social versions (1080×1080, same data and calculations as fig3/fig7/fig6/fig8; English figures untouched):
       nice -n 19 .venv/bin/python -I src/report/article_figures.py --th
Output: reports/figures/article_th/fig{1..4}_th.png
"""
import json
import pickle
import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
sys.path.insert(0, str(ROOT / "src" / "phase2"))
from config import ACC, ART, INTERIM, TRAIN, load_base, split_mask  # noqa: E402
from hazard import cif, hazards  # noqa: E402
sys.path.insert(0, str(ROOT / "src" / "lib"))
from riskutils import default_by_mob  # noqa: E402

OUT = ROOT / "reports" / "figures" / "article"
OUT.mkdir(parents=True, exist_ok=True)
REP1, REP2 = ROOT / "reports" / "phase1", ROOT / "reports" / "phase2"

SURF, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SEQ5 = ["#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
SOURCE = "Data: LendingClub via Kaggle (Nathan George); analysis: this project"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
    "axes.titlesize": 11, "axes.titleweight": "normal", "axes.titlelocation": "left", "lines.linewidth": 2.2,
    "legend.frameon": False, "legend.fontsize": 10,
})


def _fits(fig, artist, margin=0.985):
    r = fig.canvas.get_renderer()
    return artist.get_window_extent(r).x1 <= margin * fig.bbox.width


def finish(fig, title, subtitle, name, source=SOURCE):
    """Title, subtitle (wrapped to as many lines as needed to fit the width) and source; fails if any text is clipped (gate: fig3)."""
    import textwrap
    h = fig.get_figheight()
    fig.suptitle(title, x=0.012, y=1 - 0.10 / h, ha="left", va="top", fontsize=14, fontweight="bold", color=INK)
    sub = fig.text(0.012, 1 - 0.48 / h, subtitle, ha="left", va="top", fontsize=10.5, color=INK2)
    width = len(subtitle)
    while not _fits(fig, sub) and width > 40:
        width = int(width * 0.9)
        sub.set_text("\n".join(textwrap.wrap(subtitle, width)))
    extra = 0.22 * sub.get_text().count("\n")
    fig.text(0.012, 0.08 / h, source, ha="left", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.30 / h, 1, 1 - (0.80 + extra) / h))
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, Hh = fig.bbox.width, fig.bbox.height
    drawn = list(fig.texts) + [fig._suptitle]
    for ax in fig.axes:
        drawn += [ax.title, ax._left_title, ax._right_title, ax.xaxis.label, ax.yaxis.label] + list(ax.texts)
        if ax.get_legend():
            drawn += list(ax.get_legend().get_texts())
    for t in drawn:
        if t is None or not t.get_visible() or not str(t.get_text()).strip():
            continue
        bb = t.get_window_extent(r)
        assert bb.x0 >= -1 and bb.x1 <= W + 1 and bb.y0 >= -1 and bb.y1 <= Hh + 1, f"{name}: clipped text {t.get_text()[:40]!r}"
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", OUT / name)


def thresh(ax, y, label, x_text=None, va="bottom"):
    ax.axhline(y, color=MUTED, linewidth=1, linestyle="--", zorder=1)
    xt = ax.get_xlim()[0] if x_text is None else x_text
    ax.text(xt, y, f" {label}", color=INK2, fontsize=9, va=va, ha="left")


def band_mob12():
    """Default by month 12 by issue quarter × scorecard band (cut points fixed on training). Used by fig7 and fig2_th."""
    b1 = load_base(["issue_dt", "issue_q", "default_mob"]).join(pd.read_parquet(ART / "scores_m1.parquet", columns=["score_m1"]))
    cuts = np.quantile(b1.loc[split_mask(b1, TRAIN), "score_m1"], [0.2, 0.4, 0.6, 0.8])
    b1["band"] = 1 + np.searchsorted(cuts, b1.score_m1.to_numpy(), side="right")
    b1["d12"] = default_by_mob(b1.default_mob, 12)
    b1["ql"] = b1.issue_dt.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.to_timestamp()
    obs = b1[b1.ql + pd.DateOffset(months=12) <= pd.Timestamp("2018-09-01")]
    t5 = obs.groupby(["issue_q", "band"]).d12.mean().unstack()
    return t5[t5.index >= "2012Q4"]


mj = json.loads((REP1 / "metrics.json").read_text())
mon = pd.DataFrame(json.loads((REP1 / "monitoring.json").read_text()))

if "--th" in sys.argv:
    sys.path.insert(0, str(ROOT / "src" / "report"))
    from article_figures_th import render_th  # noqa: E402
    render_th(mj, mon, band_mob12)
    sys.exit(0)

# ------------------------------------------------------------------ Fig 1: data traps
con = duckdb.connect()
v = con.execute(f"""SELECT year(strptime(issue_d,'%b-%Y')) yr,
  sum((loan_status IN ('Fully Paid','Charged Off') OR loan_status LIKE 'Does not meet%')::INT) resolved,
  sum((NOT (loan_status IN ('Fully Paid','Charged Off') OR loan_status LIKE 'Does not meet%'))::INT) open_
  FROM '{ACC}' WHERE TRY_STRPTIME(issue_d,'%b-%Y') IS NOT NULL GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(v.yr, v.resolved / 1e3, color=BLUE, width=0.7, label="outcome known (paid off / charged off)")
ax.bar(v.yr, v.open_ / 1e3, bottom=v.resolved / 1e3, color=ORANGE, width=0.7, label="still open at data cut (Mar 2019)")
for x, a, b in zip(v.yr, v.resolved, v.open_):
    if x <= 2009:
        ax.annotate(f"{int(a+b):,}", (x, (a + b) / 1e3), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9, color=INK2)
ax.set_xticks(v.yr)
ax.set_ylabel("loans issued (thousands)")
ax.grid(axis="x", visible=False)
ax.legend(loc="upper left")
finish(fig, "Two traps before any model: 2007–08 is tiny, 2016–18 is unfinished",
       "Accepted loans by issue year. The 2007–08 crisis cohort is ~3k loans; most 2016–18 loans had no final outcome yet.",
       "fig1_data_traps.png")

# ------------------------------------------------------------------ Fig 2: champion vs LC grade (OOT Gini with CI)
fig, ax = plt.subplots(figsize=(9, 3.9))
models = [("LC sub-grade (benchmark)", "LC_subgrade", MUTED), ("WoE scorecard (explainable)", "M1_scorecard", BLUE),
          ("Monotone LightGBM (champion)", "M2_lgbm", ORANGE)]
for i, (lab, k, c) in enumerate(models):
    for s, mk, off in (("validation_2014", "o", 0.14), ("oot_2015", "D", -0.14)):
        r = mj[s][k]
        g, lo, hi = 100 * r["gini"], 100 * r["gini_lo"], 100 * r["gini_hi"]
        ax.errorbar(g, i + off, xerr=[[g - lo], [hi - g]], fmt=mk, color=c, markersize=8, capsize=3, linewidth=1.5,
                    markerfacecolor=c if s == "oot_2015" else SURF)
        ax.text(hi + 0.15, i + off, f"{g:.1f}", va="center", fontsize=9.5, color=INK2)
ax.set_yticks(range(3), [m[0] for m in models])
ax.set_xlabel("Gini (×100), 95% bootstrap CI")
ax.set_ylim(-0.6, 2.6)
ax.grid(axis="y", visible=False)
h1 = plt.Line2D([], [], marker="o", color=INK2, markerfacecolor=SURF, linestyle="", label="validation 2014")
h2 = plt.Line2D([], [], marker="D", color=INK2, linestyle="", label="out-of-time 2015")
ax.legend(handles=[h1, h2], loc="upper left")
d = mj["oot_2015"]["delta_gini_M2_minus_M1"]
finish(fig, "The champion beats LendingClub's own grades on unseen 2015 loans",
       f"Application data only. LightGBM − scorecard = +{100*d['point']:.1f} Gini [{100*d['lo']:.1f}, {100*d['hi']:.1f}], above the pre-registered +2.0 bar.",
       "fig2_champion_vs_lc.png")

# ------------------------------------------------------------------ Fig 3: ranking survives, calibration drifts
m3 = mon[mon.KS_M2.notna()]
m4 = mon[mon.AE12_M2.notna()]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
ax = axes[0]
x = np.arange(len(m3))
ax.fill_between(x, 100 * m3.KS_M2_lo, 100 * m3.KS_M2_hi, color=ORANGE, alpha=0.18, linewidth=0)
ax.plot(x, 100 * m3.KS_M2, color=ORANGE, marker="o", markersize=5)
ax.set_ylim(15, 32)
ax.set_xticks(x, m3.issue_q, rotation=45, ha="right", fontsize=9)
thresh(ax, 0.9 * 100 * mj["validation_2014"]["M2_lgbm"]["ks"], "amber line (0.9 × validation KS)", va="top")
ax.set_title("Ranking: KS on matured quarters (×100)")
ax = axes[1]
x = np.arange(len(m4))
ax.plot(x, m4.AE12_M2, color=ORANGE, marker="o", markersize=5)
ax.axhline(1.0, color=BASE, linewidth=1)
ax.set_xticks(x, m4.issue_q, rotation=45, ha="right", fontsize=9)
ax.set_ylim(0.85, 1.55)
thresh(ax, 1.10, "1.10 amber")
thresh(ax, 1.25, "1.25 red")
ax.set_title("Level: actual / expected defaults by month 12")
finish(fig, "The model kept ranking borrowers well — its default level drifted",
       f"Champion (LightGBM) by issue quarter. KS never breached its alarm on quarters with complete outcomes (2014Q1–2015Q3); A/E by month 12 later climbed to {m4.AE12_M2.max():.2f}.",
       "fig3_ranking_vs_level.png")

# ------------------------------------------------------------------ Fig 6: PSI is the wrong alarm (calendar time)
b = load_base(["issue_dt", "issue_q", "bad", "default_mob"]).join(pd.read_parquet(ART / "scores_m2.parquet"))
b["d6"] = default_by_mob(b.default_mob, 6)
trm = split_mask(b, TRAIN)
r6 = b.loc[trm, "d6"].mean() / b.loc[trm, "bad"].mean()
ae6 = []
for q, g in b[b.issue_dt >= "2014-01-01"].groupby("issue_q"):
    qe = g.issue_dt.max().to_period("Q").end_time.to_period("M").to_timestamp()
    k = qe + pd.DateOffset(months=12)
    if k <= pd.Timestamp("2019-03-01"):
        ae6.append({"issue_q": q, "known": k, "ae6": g.d6.sum() / (g.pd_m2.sum() * r6)})
ae6 = pd.DataFrame(ae6)
mon["qe"] = pd.PeriodIndex(mon.issue_q, freq="Q").end_time.to_period("M").to_timestamp()
mon["k_psi"] = mon.qe
mon["k12"] = mon.qe + pd.DateOffset(months=18)
fig, axes = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.4]})
ax = axes[0]
ax.plot(mon.k_psi, mon.PSI_M2, color=ORANGE, marker="o", markersize=4)
ax.set_ylim(0, 0.3)
thresh(ax, 0.10, "0.10 amber", x_text=pd.Timestamp("2014-01-01"))
thresh(ax, 0.25, "0.25 red", x_text=pd.Timestamp("2014-01-01"))
ax.set_title("Population stability index of the champion score (no labels needed) — never alarmed")
ax = axes[1]
k12 = mon[mon.AE12_M2.notna()]
ax.plot(k12.k12, k12.AE12_M2, color=BLUE, marker="o", markersize=4, label="defaults by month 12 (pre-registered)")
ax.plot(ae6.known, ae6.ae6, color=AQUA, marker="o", markersize=4, linestyle=":", label="defaults by month 6 (exploratory; failed its 60m confirmatory test)")
ax.axhline(1.0, color=BASE, linewidth=1)
thresh(ax, 1.10, "1.10 amber", x_text=pd.Timestamp("2014-01-01"))
thresh(ax, 1.25, "1.25 red", x_text=pd.Timestamp("2014-01-01"))
fb_q = mon[mon.deterioration == "YES"].issue_q.iloc[0]                       # first deteriorated vintage (pre-registered truth)
fa = mon[mon.flag_AE12_M2.isin(["AMBER", "RED"])].iloc[0]                    # first champion month-12 alarm
first_bad = pd.Period(fb_q, freq="Q").start_time
first_amber = pd.Timestamp(fa.k12)
alarm_q = str(pd.Period(first_amber, freq="Q"))
n_booked = int(b[(b.issue_q >= fb_q) & (b.issue_q <= alarm_q)].shape[0])
for a in axes:
    a.axvspan(first_bad, first_amber, color=YELLOW, alpha=0.12, linewidth=0)
ax.text(first_bad + pd.DateOffset(months=1), 1.30, f"first worse vintage issued ({first_bad:%b %Y})\n→ first month-12 alarm ({first_amber:%b %Y}):\n~{n_booked/1e3:.0f}k loans booked meanwhile",
        fontsize=9, color=INK2, va="bottom")
ax.set_ylim(0.85, 1.9)
ax.set_title("Actual / expected defaults, plotted at the date each value became knowable")
ax.legend(loc="upper left", fontsize=9)
finish(fig, "Population stability is the wrong alarm: it never fired",
       "Points at the date each value could first be known, if the model were live from 2015 (its own training labels completed only in 2017).",
       "fig6_alarm_timeline.png")

# ------------------------------------------------------------------ Fig 7: default at MOB 12 by risk band
t5 = band_mob12()
fig, ax = plt.subplots(figsize=(10, 4.8))
x = np.arange(len(t5))
labels = {1: "band 1 (riskiest 20% at training)", 2: "band 2", 3: "band 3", 4: "band 4", 5: "band 5 (safest 20%)"}
for bnd, col in zip([5, 4, 3, 2, 1], SEQ5):
    ax.plot(x, 100 * t5[bnd], color=col, marker="o", markersize=4, label=labels[bnd])
ax.set_xticks(x, t5.index, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("defaulted by month 12, %")
ax.legend(loc="upper left", fontsize=9, ncol=2)
finish(fig, "Same score, more defaults: the drift hit every risk band",
       "Share of loans defaulted by month 12, by issue quarter and scorecard band (cut points fixed on 2012–13 training data).",
       "fig7_bands_mob12.png")

# ------------------------------------------------------------------ Fig 4: prepayment as competing risk
p2 = pd.read_parquet(INTERIM / "p2_loans.parquet")
p15 = p2[(p2.yr == 2015) & (p2.issue_dt <= "2015-09-01")].reset_index(drop=True)      # fully observable to MOB 36
with open(INTERIM / "p2" / "model_A.pkl", "rb") as fh:
    mA = pickle.load(fh)
hd, hp = hazards(mA["scaler"].loan_cols(p15), mA["B"])
_, _, C = cif(hd, hp)
naive = 1 - np.cumprod(1 - hd, axis=1)
act = np.array([default_by_mob(p15.default_mob, m).mean() for m in range(1, 37)])
mob = np.arange(1, 37)
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(mob, 100 * naive.mean(0), color=MUTED, linestyle="--", label="same hazards, prepayment treated as censoring")
ax.plot(mob, 100 * C.mean(0), color=BLUE, label="model with prepayment as competing risk")
ax.plot(mob, 100 * act, color=ORANGE, label="actual")
for arr, col, dy in ((naive.mean(0), MUTED, 0), (C.mean(0), BLUE, -0.4), (act, ORANGE, 0.4)):
    ax.text(36.4, 100 * arr[-1] + dy, f"{100*arr[-1]:.1f}%", color=col, fontsize=10, va="center")
ax.set_xlim(0, 39)
ax.set_xticks([6, 12, 18, 24, 30, 36])
ax.set_xlabel("months on book")
ax.set_ylabel("cumulative default, %")
ax.legend(loc="upper left")
finish(fig, f"Treat prepayment as censoring and lifetime PD is overstated by {100*(naive.mean(0)[-1]/C.mean(0)[-1]-1):.0f}%",
       "Loans issued Jan–Sep 2015 (observable to month 36). Model trained on 2012–13; its gap to actual is the 2015 drift.",
       "fig4_prepayment_competing_risk.png")

# ------------------------------------------------------------------ Fig 8: lifetime-EL backtest + overlay
ov = json.loads((REP2 / "overlay.json").read_text())
q = pd.DataFrame(ov["by_quarter"])
fig, ax = plt.subplots(figsize=(9.5, 4.6))
x = np.arange(len(q))
w = 0.27
ax.bar(x - w, q["EL_pred $m"], width=w, color=BLUE, label="expected loss at origination (model)")
ax.bar(x, q["EL_ovl12 $m"], width=w, color=BLUE, alpha=0.45, hatch="//", edgecolor=BLUE, linewidth=0,
       label="with month-12 overlay (illustrative, in-sample)")
ax.bar(x + w, q["realised $m"], width=w, color=ORANGE, label="actual loss")
for i, rr in q.iterrows():
    ax.text(i + w, rr["realised $m"] + 1, f"×{rr['realised/pred']:.2f}", ha="center", fontsize=9, color=INK2)
ax.set_xticks(x, q.issue_q)
ax.set_ylabel("$ million (net principal loss)")
ax.set_ylim(0, q["realised $m"].max() * 1.25)
ax.grid(axis="x", visible=False)
ax.legend(loc="upper left", fontsize=9)
tot = ov["total"]
finish(fig, f"Realised loss came in at {tot['realised/pred']:.2f}× expected; in-sample month-12 overlay closes {100*tot['gap closed MOB12']:.0f}%",
       f"2015 loans; lifetime EL at origination, not an allowance. Overlay = EL × month-12 A/E "
       f"(month-6: {100*tot['gap closed MOB6']:.0f}%). Illustrative.",
       "fig8_ecl_backtest_overlay.png")

# ------------------------------------------------------------------ Fig 5: simple cutoff vs MILP
pcj = json.loads((REP2 / "policy_C.json").read_text())["0.05"]
pc = pd.DataFrame(pcj["table"])
dfx = pd.DataFrame(pcj["diffs"])
dC = dfx[(dfx["difference ($m, OOT 2015)"] == "C−M2 NPV") & (dfx.bootstrap == "loan")].iloc[0]
pc = pc[pc.set == "OOT 2015"].reset_index(drop=True)
name = {"C: MILP cells": "MILP-optimised policy", "approve all": "approve everyone",
        "M2": "simple PD cutoff (champion)", "M1": "scorecard cutoff", "S": "single PD threshold tuned to NPV"}
key = lambda p: "M2" if p.startswith("Phase 1 M2") else "M1" if p.startswith("Phase 1 M1") else "S" if p.startswith("single") else p  # noqa: E731
pc["lab"] = [f"{name.get(key(p), p)}  ({a:.0f}% approved)" for p, a in zip(pc.policy, pc["approval %"])]
appr = dict(zip(pc.policy.map(key), pc["approval %"]))
order = [2, 0, 4, 3, 1]
pc = pc.iloc[order].reset_index(drop=True)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, col, ttl in ((axes[0], "realised profit $m", "Pre-registered (wrong: no funding cost)"),
                     (axes[1], "EXPLORATORY realised NPV $m", "Exploratory: NPV at 5% funding cost")):
    cols = [ORANGE if "MILP" in lb else (BLUE if "simple" in lb else MUTED) for lb in pc.lab]
    ax.barh(pc.lab, pc[col], color=cols)
    for i, vv in enumerate(pc[col]):
        ax.text(vv, i, f" ${vv:.0f}m", va="center", fontsize=10)
    ax.set_xlim(0, pc[col].max() * 1.22)
    ax.set_title(ttl, fontsize=10.5)
    ax.set_xlabel("$ million, 2015 loans")
    ax.grid(axis="y", visible=False)
axes[0].invert_yaxis()
finish(fig, "The optimiser adds nothing over one PD threshold (exploratory metric)",
       f"Without funding cost, 'approve everyone' looks best. At 5%: MILP − cutoff = −${-dC['point']:.1f}m, 95% CI {dC['95% CI']}. "
       "Levels depend on cash timing.",
       "fig5_policy_cutoff_vs_milp.png")
