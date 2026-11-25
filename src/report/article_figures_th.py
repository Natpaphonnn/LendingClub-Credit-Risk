"""Thai social-media figures (1080×1080) — called by `article_figures.py --th`. Aggregates only.

Same data and calculations as the English article figures:
  fig1_th ← fig3 (KS and month-12 A/E of the champion, reports/phase1/monitoring.json + metrics.json)
  fig2_th ← fig7 (month-12 default by scorecard band, article_figures.band_mob12)
  fig3_th ← fig6, with the realistic as-of model (reports/phase4/asof_model.json; PSI panel = champion PSI, claim C10)
  fig4_th ← fig8 without the illustrative overlay (reports/phase2/overlay.json)
Every number printed in a figure must be in that figure's whitelist; whitelisted values are computed here and the
headline ones are asserted against the claims table (notes/05_claims_and_limitations.md) and check_note_numbers.
"""
import json
import re
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import YearLocator, DateFormatter
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "figures" / "article_th"
BG, INK, RED, OK, SEC, GRID = "#EEF1F4", "#14213D", "#D7263D", "#2E9E6A", "#5B6577", "#D3D8DF"
DPI, SIDE, MIN_PX = 100, 1080, 26
SOURCE = "ข้อมูล: LendingClub (Kaggle) ไม่ใช่ธนาคารไทย"
TH_MON = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
ACRONYMS = {"KS", "PSI"}          # the only all-caps Latin words allowed on a figure
L, R = 64 / SIDE, 1 - 64 / SIDE   # side margins (figure fraction)


def px(v):
    """Font size in points for v pixels on the 1080 canvas."""
    return v * 72 / DPI


def th_month(ts):
    ts = pd.Timestamp(ts)
    return f"{TH_MON[ts.month - 1]} {ts.year}"


def pick_font():
    names = {f.name for f in fm.fontManager.ttflist}
    for n in ("IBM Plex Sans Thai", "Thonburi"):
        if n in names:
            return n
    raise SystemExit("no Thai font found (IBM Plex Sans Thai or Thonburi)")


def style(font):
    plt.rcParams.update({
        "font.family": font, "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
        "axes.edgecolor": SEC, "axes.labelcolor": SEC, "xtick.color": SEC, "ytick.color": SEC, "text.color": INK,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1.0, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "xtick.labelsize": px(26), "ytick.labelsize": px(26), "axes.labelsize": px(26),
        "axes.titlesize": px(30), "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.titlecolor": INK,
        "axes.titlepad": 14, "lines.linewidth": 3.5, "legend.frameon": False, "legend.fontsize": px(26),
        "ytick.major.size": 0, "xtick.major.size": 6, "axes.unicode_minus": False,
    })


def canvas(title, subtitle):
    """Figure with title + subtitle at the top and the source at the bottom; returns (fig, top of plot area)."""
    fig = plt.figure(figsize=(SIDE / DPI, SIDE / DPI), dpi=DPI)
    t = fig.text(L, 1 - 52 / SIDE, title, fontsize=px(50), fontweight="bold", color=INK, va="top", linespacing=1.2)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    y = t.get_window_extent(r).y0 / SIDE - 16 / SIDE
    s = fig.text(L, y, subtitle, fontsize=px(28), color=SEC, va="top", linespacing=1.35)
    fig.canvas.draw()
    fig.text(L, 34 / SIDE, SOURCE, fontsize=px(26), color=SEC, va="bottom")
    return fig, s.get_window_extent(r).y0 / SIDE - 30 / SIDE


def stack(fig, top, heights, left=0.125, bottom_px=125, between_px=128, title_px=62):
    """Titled panels stacked from `top` down to `bottom_px`; `heights` are relative panel heights."""
    avail = top * SIDE - bottom_px - title_px - between_px * (len(heights) - 1)
    y, axes = top * SIDE - title_px, []
    for hrel in heights:
        hh = avail * hrel / sum(heights)
        axes.append(fig.add_axes((left, (y - hh) / SIDE, R - left, hh / SIDE)))
        y -= hh + between_px
    return axes


def year_axis(ax, lo, hi):
    ax.set_xlim(pd.Timestamp(lo), pd.Timestamp(hi))
    ax.xaxis.set_major_locator(YearLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    ax.grid(axis="x", visible=False)


def hline(ax, y, label, x, color=SEC, va="bottom", ha="left"):
    ax.axhline(y, color=color, linewidth=2, linestyle=(0, (6, 4)), zorder=1)
    ax.text(x, y, label, color=color, fontsize=px(26), va=va, ha=ha)


NUM = re.compile(r"\d[\d.,]*(?:Q\d)?")


def finish(fig, name, allowed):
    """Gates: every text inside the canvas, ≥ 26 px, no all-caps words except KS/PSI, every printed number whitelisted."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    texts = [(t, False) for t in fig.texts]
    for ax in fig.axes:
        texts += [(t, False) for t in [ax.title, ax._left_title, ax._right_title, ax.xaxis.label, ax.yaxis.label] + list(ax.texts)]
        if ax.get_legend():
            texts += [(t, False) for t in ax.get_legend().get_texts()]
        for axis, (v0, v1) in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):   # drawn ticks only
            texts += [(t, True) for loc, t in zip(axis.get_majorticklocs(), axis.get_majorticklabels())
                      if min(v0, v1) <= loc <= max(v0, v1)]
    seen, boxes = [], []
    for t, is_tick in texts:
        s = str(t.get_text())
        if not t.get_visible() or not s.strip():
            continue
        bb = t.get_window_extent(r)
        assert bb.x0 >= 0 and bb.x1 <= SIDE and bb.y0 >= 0 and bb.y1 <= SIDE, f"{name}: text outside canvas {s[:40]!r}"
        size_px = t.get_fontsize() * DPI / 72
        assert size_px >= MIN_PX - 1e-6, f"{name}: {size_px:.1f}px < {MIN_PX}px: {s[:40]!r}"
        caps = [w for w in re.findall(r"[A-Za-z]{2,}", s) if w.isupper() and w not in ACRONYMS]
        assert not caps, f"{name}: all-caps word(s) {caps} in {s[:40]!r}"
        if not is_tick:
            for s2, bb2 in boxes:
                assert not bb.overlaps(bb2), f"{name}: text overlap {s[:30]!r} / {s2[:30]!r}"
            boxes.append((s, bb))
            for tok in NUM.findall(s):
                tok = tok.rstrip(".,")
                assert tok in allowed, f"{name}: number {tok!r} not whitelisted (text {s[:50]!r})"
                seen.append(tok)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI)
    plt.close(fig)
    with Image.open(OUT / name) as im:
        assert im.size == (SIDE, SIDE), f"{name}: size {im.size}"
    print("wrote", OUT / name, "| numbers:", " ".join(sorted(set(seen))))


def qstart(qs):
    return pd.PeriodIndex(list(qs), freq="Q").start_time


def render_th(mj, mon, band_mob12):
    font = pick_font()
    print("Thai font:", font)
    style(font)
    claims = (ROOT / "notes" / "05_claims_and_limitations.md").read_text()

    # ---------------------------------------------------------------- fig1_th ← fig3: ranking holds, level drifts
    m3, m4 = mon[mon.KS_M2.notna()], mon[mon.AE12_M2.notna()]
    ks_lo, ks_hi = f"{100 * m3.KS_M2.min():.1f}", f"{100 * m3.KS_M2.max():.1f}"
    ks_val = f"{100 * mj['validation_2014']['M2_lgbm']['ks']:.1f}"
    ae_max = m4.AE12_M2.max()
    q_max = m4.loc[m4.AE12_M2.idxmax(), "issue_q"]
    assert f"KS (champion) {ks_lo}–{ks_hi}, never < 0.9 × {ks_val}" in claims          # C8
    assert (f"{ae_max:.2f}", q_max) == ("1.46", "2016Q3")                                 # cover / C-table headline
    assert (m3.issue_q.iloc[0], m3.issue_q.iloc[-1]) == ("2014Q1", "2015Q3")
    fig, top = canvas("เรียงลูกหนี้ถูก แต่ระดับความเสี่ยงเพี้ยน",
                      "โมเดลหลัก (LightGBM) แยกตามไตรมาสที่ปล่อยกู้\nKS วัดเฉพาะไตรมาสที่รู้ผลครบแล้ว (2014Q1–2015Q3)")
    ax1, ax2 = stack(fig, top, [0.37, 0.63])
    lo, hi = "2013-11-01", "2017-11-01"
    x = qstart(m3.issue_q)
    ax1.fill_between(x, 100 * m3.KS_M2_lo, 100 * m3.KS_M2_hi, color=OK, alpha=0.18, linewidth=0)
    ax1.plot(x, 100 * m3.KS_M2, color=OK, marker="o", markersize=8)
    ax1.set_ylim(14, 32)
    ax1.set_yticks([20, 30])
    year_axis(ax1, lo, hi)
    hline(ax1, 0.9 * float(ks_val), "เส้นเตือน: 0.9 × KS ตอน validate", pd.Timestamp("2015-10-01"), va="top")
    ax1.set_title(f"การจัดอันดับ: KS (×100) คงที่ {ks_lo}–{ks_hi}", color=OK)
    x = qstart(m4.issue_q)
    ax2.plot(x, m4.AE12_M2, color=RED, marker="o", markersize=8)
    ax2.axhline(1.0, color=SEC, linewidth=1.2)
    ax2.set_ylim(0.85, 1.62)
    ax2.set_yticks([1.0, 1.2, 1.4, 1.6])
    year_axis(ax2, lo, hi)
    hline(ax2, 1.10, "1.10 เตือนเหลือง", pd.Timestamp(lo))
    hline(ax2, 1.25, "1.25 เตือนแดง", pd.Timestamp(lo))
    xm = qstart([q_max])[0]
    ax2.annotate(f"{ae_max:.2f} ({q_max})", (xm, ae_max), xytext=(-20, 18), textcoords="offset points",
                 ha="right", fontsize=px(30), fontweight="bold", color=RED)
    ax2.set_title("ระดับ: ผิดนัดจริง ÷ ที่คาด ภายในเดือนที่ 12", color=RED)
    finish(fig, "fig1_th.png", {"2014Q1", "2015Q3", "0.9", "100", ks_lo, ks_hi, "1.10", "1.25", "12",
                                f"{ae_max:.2f}", q_max})

    # ---------------------------------------------------------------- fig2_th ← fig7: concept drift in every band
    t5 = band_mob12()
    a, b = "2013Q4", "2016Q3"
    v = {(k, q): f"{100 * t5.loc[q, k]:.1f}" for k in (1, 5) for q in (a, b)}
    assert f"band 1 @MOB12 {v[1, a]}% → {v[1, b]}%; band 5 {v[5, a]}% → {v[5, b]}% ({a} → {b})" in claims   # C13
    vint = (ROOT / "reports" / "phase1" / "vintage.md").read_text()                                          # cross-check
    for q in (a, b):
        row = next(l for l in vint.splitlines() if l.startswith(f"| {q}"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert abs(float(cells[5]) - 100 * t5.loc[q, 1]) < 0.006 and abs(float(cells[13]) - 100 * t5.loc[q, 5]) < 0.006, q
    fig, top = canvas("คะแนนเท่าเดิม แต่ผิดนัดมากขึ้นทุกกลุ่ม",
                      "% ผิดนัดภายในเดือนที่ 12 แยกตามกลุ่มคะแนน 5 กลุ่ม\n(จุดตัดกลุ่มกำหนดจากข้อมูลปี 2012–13 แล้วไม่เปลี่ยน)")
    ax = fig.add_axes((0.105, 0.115, R - 0.105, top - 0.115))
    x = qstart(t5.index)
    for k in (2, 3, 4):
        ax.plot(x, 100 * t5[k], color=SEC, alpha=0.35, linewidth=2.5)
    ax.plot(x, 100 * t5[1], color=RED, linewidth=4.5)
    ax.plot(x, 100 * t5[5], color=INK, linewidth=4.5)
    for k, col in ((1, RED), (5, INK)):
        for q, off, ha in ((a, (0, 16) if k == 5 else (10, -14), "center" if k == 5 else "left"), (b, (0, 16), "center")):
            xq = qstart([q])[0]
            ax.plot([xq], [100 * t5.loc[q, k]], "o", color=col, markersize=13, markeredgecolor=BG, markeredgewidth=2.5, zorder=5)
            ax.annotate(f"{v[k, q]}%", (xq, 100 * t5.loc[q, k]), xytext=off, textcoords="offset points", ha=ha,
                        va="top" if off[1] < 0 else "baseline",
                        fontsize=px(32), fontweight="bold", color=col)
    ax.text(x[0], 100 * t5[1].iloc[0] + 1.3, "กลุ่มเสี่ยงสุด 20%", color=RED, fontsize=px(28), fontweight="bold")
    ax.text(x[0], 100 * t5[5].iloc[0] - 1.6, "กลุ่มเสี่ยงต่ำสุด 20%", color=INK, fontsize=px(28), fontweight="bold", va="top")
    ax.text(pd.Timestamp("2016-10-01"), 5.6, "อีก 3 กลุ่ม", color=SEC, fontsize=px(26), alpha=0.9)
    ax.set_ylim(-1.5, 13.5)
    ax.set_yticks([0, 4, 8, 12])
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0f}%")
    year_axis(ax, "2012-08-01", "2017-11-01")
    finish(fig, "fig2_th.png", {"12", "5", "2012", "13", "3", "20", *v.values()})

    # ---------------------------------------------------------------- fig3_th ← fig6: the realistic (as-of) alarm
    asof = json.loads((ROOT / "reports" / "phase4" / "asof_model.json").read_text())
    am = pd.DataFrame(asof["monitoring"]).dropna(subset=["A/E12"])
    am["k"] = pd.to_datetime(am.knowable)
    first_worse = mon.loc[mon.deterioration == "YES", "issue_q"].iloc[0]
    fa = am[am["A/E flag"].isin(["AMBER", "RED"])].iloc[0]
    fr = am[am["A/E flag"] == "RED"].iloc[0]
    assert {"issue_q": fa.issue_q, "knowable": fa.knowable} == asof["first_amber"]
    assert {"issue_q": fr.issue_q, "knowable": fr.knowable} == asof["first_red"]
    assert (first_worse, fa.knowable, fr.knowable) == ("2015Q2", "2017-06", "2017-09")                          # C29
    t_bad, t_amb, t_red = pd.Period(first_worse, "Q").start_time, fa.k, fr.k
    months = (t_amb.year - t_bad.year) * 12 + t_amb.month - t_bad.month
    alarm_q = str(pd.Period(t_amb, "Q"))
    n_booked = int(mon[(mon.issue_q >= first_worse) & (mon.issue_q <= alarm_q)].n.sum())
    assert (months, n_booked) == (26, 687_800)                                                                   # demo / check_note_numbers
    assert "decision date 2014-12-31" in (ROOT / "reports" / "phase4" / "asof_model.md").read_text()
    psi_max = mon.PSI_M2.max()
    assert f"PSI ≤ {psi_max:.3f} all quarters 2014Q1–2018Q4 (amber 0.10)" in claims and psi_max < 0.06         # C10
    fig, top = canvas("สัญญาณเตือนดังช้าไป 26 เดือน",
                      f"ระหว่างนั้นปล่อยกู้ไปแล้ว {n_booked:,} สัญญา\n"
                      "โมเดล as-of (ใช้ข้อมูลถึง 31 ธ.ค. 2014) · จุดวางตามวันที่รู้ผลได้จริง")
    ax1, ax2 = stack(fig, top, [0.66, 0.34])
    lo, hi = "2014-01-01", "2019-06-01"
    for ax in (ax1, ax2):
        ax.axvspan(t_bad, t_amb, color=RED, alpha=0.08, linewidth=0)
        ax.axvline(t_bad, color=RED, linewidth=2)
        year_axis(ax, lo, hi)
    ax1.plot(am.k, am["A/E12"], color=INK, linewidth=3, zorder=3)
    for _, rr in am.iterrows():
        f = rr["A/E flag"]
        ax1.plot([rr.k], [rr["A/E12"]], "o", markersize=14 if f != "green" else 11, zorder=4,
                 color=OK if f == "green" else (BG if f == "AMBER" else RED),
                 markeredgecolor=OK if f == "green" else RED, markeredgewidth=3.5)
    ax1.axhline(1.0, color=SEC, linewidth=1.2)
    hline(ax1, 1.10, "1.10 เตือนเหลือง", pd.Timestamp(lo))
    hline(ax1, 1.25, "1.25 เตือนแดง", pd.Timestamp(hi), va="top", ha="right")
    ax1.set_ylim(0.85, 1.55)
    ax1.set_yticks([1.0, 1.2, 1.4])
    ax1.annotate(f"เหลือง {th_month(t_amb)}", (t_amb, fa["A/E12"]), xytext=(26, -38), textcoords="offset points",
                 va="top", fontsize=px(28), fontweight="bold", color=RED,
                 arrowprops={"arrowstyle": "-", "color": RED, "linewidth": 1.5, "shrinkA": 0, "shrinkB": 9})
    ax1.annotate(f"แดง {th_month(t_red)}", (t_red, fr["A/E12"]), xytext=(-20, 0), textcoords="offset points",
                 ha="right", va="center", fontsize=px(28), fontweight="bold", color=RED)
    ax1.text(t_bad - pd.DateOffset(months=1), 1.53, f"{th_month(t_bad)}\nเริ่มปล่อย\nกลุ่มที่แย่ลง",
             va="top", ha="right", fontsize=px(26), color=RED, linespacing=1.25)
    ax1.text(t_bad + (t_amb - t_bad) / 2 + pd.DateOffset(months=3), 0.90, f"{months} เดือน", ha="center", va="bottom",
             fontsize=px(32), fontweight="bold", color=RED)
    ax1.set_title("ผิดนัดจริง ÷ ที่คาด ภายในเดือนที่ 12", color=INK)
    ax2.plot(pd.to_datetime(mon.known_PSI), mon.PSI_M2, color=OK, marker="o", markersize=7)
    ax2.set_ylim(0, 0.135)
    ax2.set_yticks([0, 0.05])
    ax2.yaxis.set_major_formatter(lambda y, _: f"{y:.2f}")
    hline(ax2, 0.10, "เส้นเตือน PSI 0.10", pd.Timestamp("2016-08-01"))
    km = pd.Timestamp(mon.loc[mon.PSI_M2.idxmax(), "known_PSI"])
    ax2.annotate(f"สูงสุด {psi_max:.3f} ไม่เคยเกิน 0.06", (km, psi_max), xytext=(-40, 4), textcoords="offset points",
                 ha="right", va="bottom", fontsize=px(26), color=OK, fontweight="bold")
    ax2.set_title("PSI ของคะแนนโมเดลหลัก: เงียบตลอด", color=OK)
    finish(fig, "fig3_th.png", {str(months), f"{n_booked:,}", "31", "2014", "12", "1.10", "1.25", str(t_amb.year),
                                str(t_bad.year), "0.10", f"{psi_max:.3f}", "0.06"})

    # ---------------------------------------------------------------- fig4_th ← fig8: lifetime-EL backtest (no overlay)
    ov = json.loads((ROOT / "reports" / "phase2" / "overlay.json").read_text())
    q = pd.DataFrame(ov["by_quarter"])
    tot = ov["total"]
    ratio, pred, real = f"{tot['realised/pred']:.2f}", f"{tot['EL_pred $m']:.1f}", f"{tot['realised $m']:.1f}"
    assert f"predicted EL ${pred}m vs realised ${real}m (×{ratio}" in claims                                     # C21
    assert list(q.issue_q) == ["2015Q1", "2015Q2", "2015Q3", "2015Q4"]
    fig, top = canvas(f"ความเสียหายจริงสูงกว่าที่คาด {ratio} เท่า",
                      "สินเชื่อที่ปล่อยปี 2015: ผลขาดทุนตลอดอายุที่โมเดลคาดไว้ตอนปล่อย\n"
                      "เทียบกับที่เกิดจริง (เป็น backtest ไม่ใช่การตั้งสำรองจริง)")
    ax = fig.add_axes((0.14, 0.20, R - 0.14, top - 0.20 - 0.10))
    xx = range(len(q))
    w = 0.36
    ax.bar([i - w / 2 for i in xx], q["EL_pred $m"], width=w, color=SEC, label="คาดไว้ตอนปล่อยกู้")
    ax.bar([i + w / 2 for i in xx], q["realised $m"], width=w, color=RED, label="เกิดจริง")
    rq = [f"{x:.2f}" for x in q["realised/pred"]]
    for i, rr in q.iterrows():
        ax.text(i + w / 2, rr["realised $m"] + 1.5, f"×{rq[i]}", ha="center", fontsize=px(28), fontweight="bold", color=RED)
    ax.set_xticks(list(xx), [f"ไตรมาส {i + 1}" for i in xx])
    ax.yaxis.set_major_formatter(lambda y, _: f"\\${y:.0f}m")
    ax.set_ylim(0, q["realised $m"].max() * 1.12)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, handlelength=1.2, columnspacing=1.5, borderaxespad=0.3)
    fig.text(L, 0.105, f"รวมทั้งปี: คาด \\${pred}m · จริง \\${real}m", fontsize=px(28), fontweight="bold", color=INK, va="bottom")
    finish(fig, "fig4_th.png", {ratio, pred, real, "2015", *rq, "1", "2", "3", "4"})
