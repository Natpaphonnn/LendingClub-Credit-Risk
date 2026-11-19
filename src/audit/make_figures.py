"""Phase 0 figures (aggregates only) -> reports/figures/.

Usage:  nice -n 19 .venv/bin/python -I src/audit/make_figures.py <interim_dir> <fig_dir>
"""
import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

interim, figdir = Path(sys.argv[1]), Path(sys.argv[2])
figdir.mkdir(parents=True, exist_ok=True)
ACC = interim / "accepted_2007_to_2018Q4.parquet"

SURF, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # categorical slots 1-4, fixed order
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 2,
})

con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")
con.execute(f"""CREATE VIEW acc AS SELECT *, year(strptime(issue_d,'%b-%Y')) yr,
  TRY_CAST(regexp_replace(term,'[^0-9]','','g') AS INT) term_m, TRY_CAST(int_rate AS DOUBLE) rate,
  TRY_CAST(fico_range_low AS DOUBLE) fico
  FROM '{ACC}' WHERE TRY_STRPTIME(issue_d,'%b-%Y') IS NOT NULL""")
FINAL = ("('Fully Paid','Charged Off','Does not meet the credit policy. Status:Fully Paid',"
         "'Does not meet the credit policy. Status:Charged Off')")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(figdir / name, dpi=150)
    plt.close(fig)
    print("wrote", figdir / name)


# 1. volume by year
v = con.execute("SELECT yr, count(*) n FROM acc GROUP BY 1 ORDER BY 1").df()
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(v.yr, v.n / 1e3, color=S[0], width=0.7)
for x, y in zip(v.yr, v.n):
    if x <= 2009 or x == 2018:
        ax.annotate(f"{y:,}", (x, y / 1e3), textcoords="offset points", xytext=(0, 3), ha="center",
                    fontsize=8, color=INK2)
ax.set_title("Accepted loans by issue year (thousands)")
ax.set_xticks(v.yr)
ax.grid(axis="x", visible=False)
ax.text(0, -0.18, "2007-2008 together are ~3k loans: the 'pre-crisis' training sample is small.",
        transform=ax.transAxes, color=INK2, fontsize=8.5)
save(fig, "p0_volume_by_year.png")

# 2. resolved share by year × term
m = con.execute(f"""SELECT yr, term_m, 100*avg((loan_status IN {FINAL})::INT) pct FROM acc
                    WHERE term_m IN (36,60) GROUP BY 1,2 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(8, 3.6))
for i, t in enumerate([36, 60]):
    d = m[m.term_m == t]
    ax.plot(d.yr, d.pct, color=S[i], marker="o", markersize=5, label=f"{t}-month")
ax.axhline(95, color=MUTED, linewidth=1, linestyle="--")
ax.text(2016.15, 96.5, "95% resolved", color=MUTED, fontsize=8)
ax.set_ylim(0, 105)
ax.set_title("Share of loans with a final status (Fully Paid / Charged Off), %")
ax.legend(frameon=False, loc="lower left")
ax.set_xticks(sorted(m.yr.unique()))
save(fig, "p0_matured_share.png")

# 3. desc share by year
d = con.execute("""SELECT yr, 100*avg((coalesce(length(trim("desc")),0)>0)::INT) pct FROM acc GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(8, 3.2))
ax.bar(d.yr, d.pct, color=S[0], width=0.7)
for x, y in zip(d.yr, d.pct):
    ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=8, color=INK2)
ax.set_ylim(0, 110)
ax.set_title("Loans with a non-empty borrower description (desc), % by issue year")
ax.set_xticks(d.yr)
ax.grid(axis="x", visible=False)
save(fig, "p0_desc_share.png")

# 4. mean int_rate by FICO bin, per era
g = con.execute("""SELECT CASE WHEN yr<=2009 THEN '2007-09' WHEN yr<=2012 THEN '2010-12'
  WHEN yr<=2015 THEN '2013-15' ELSE '2016-18' END era, fico, avg(rate) r, count(*) n
  FROM acc WHERE fico BETWEEN 660 AND 800 GROUP BY 1,2 HAVING count(*)>=100 ORDER BY 1,2""").df()
fig, ax = plt.subplots(figsize=(8, 4))
for i, e in enumerate(sorted(g.era.unique())):
    d = g[g.era == e]
    ax.plot(d.fico, d.r, color=S[i], marker="o", markersize=3.5, label=e)
ax.set_xlabel("fico_range_low (5-point bins)")
ax.set_ylabel("mean int_rate, %")
ax.set_title("Mean int_rate by FICO bin: steady decline, no sharp step at any bin")
ax.legend(frameon=False, title="issue era")
save(fig, "p0_rate_by_fico.png")
