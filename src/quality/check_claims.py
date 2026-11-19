"""Re-check every claim in notes/05_claims_and_limitations.md (C1-C26) + the '45% above expected' figure.

Where possible the value is RE-DERIVED independently (raw/interim data, sklearn instead of own metric code); otherwise read
from the source report the claim cites. PASS = equal at the precision stated in the claim.
Output: reports/quality/claims_check.md ; exit code 1 if any FAIL.
Usage: nice -n 19 .venv/bin/python -I src/quality/check_claims.py
"""
import json
import re
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
for p in ("src/lib", "src/phase1", "src/audit"):
    sys.path.insert(0, str(ROOT / p))
from config import ART, TRAIN, OOT, VALID, load_base, split_mask  # noqa: E402
from leakage_map import classify  # noqa: E402
from riskutils import default_by_mob  # noqa: E402

R1, R2 = ROOT / "reports" / "phase1", ROOT / "reports" / "phase2"
ACC = ROOT / "data" / "interim" / "accepted_2007_to_2018Q4.parquet"
J = lambda p: json.loads(Path(p).read_text())  # noqa: E731
m1, mon = J(R1 / "metrics.json"), pd.DataFrame(J(R1 / "monitoring.json"))
mb, ecl, ov, pc = J(R2 / "macro_B.json"), J(R2 / "ecl.json"), J(R2 / "overlay.json"), J(R2 / "policy_C.json")
rows = []


CLAIMS_DOC = (ROOT / "notes" / "05_claims_and_limitations.md").read_text().replace("−", "-")
DOC_ROWS = {m.group(1): m.group(0) for m in re.finditer(r"^\| (C\d+) \|.*$", CLAIMS_DOC, flags=re.M)}


def chk(cid, what, stated, got, source, how, doc_id=None):
    """stated: list of strings exactly as they appear in the claim's row of notes/05 (precision taken from the string).
    got: recomputed values (numbers or strings). PASS needs (i) every value to match at the stated precision and
    (ii) every stated string to appear verbatim in the notes/05 row (doc_id defaults to the claim id prefix)."""
    s_ = [str(x) for x in (stated if isinstance(stated, (list, tuple)) else [stated])]
    g_ = list(got) if isinstance(got, (list, tuple)) else [got]
    ok_vals, shown = len(s_) == len(g_), []
    for a, b in zip(s_, g_):
        try:
            x = float(a.replace(",", ""))
            nd = len(a.split(".")[1]) if "." in a else 0
            shown.append(f"{float(b):.{nd}f}")
            ok_vals &= abs(round(float(b), nd) - x) < 10 ** -nd / 2 + 1e-12
        except ValueError:
            shown.append(str(b))
            ok_vals &= str(a) == str(b)
    row = DOC_ROWS.get(doc_id or re.match(r"C\d+", cid).group(0) if (doc_id or cid.startswith("C")) else "", "")
    in_doc = "n/a (not in notes/05)" if not cid.startswith("C") else ("yes" if all(a in row for a in s_) else
                                                                     "NO: " + ", ".join(a for a in s_ if a not in row))
    ok = ok_vals and (in_doc in ("yes", "n/a (not in notes/05)"))
    rows.append({"id": cid, "check": what, "stated (notes/05)": ", ".join(s_), "recomputed": ", ".join(shown),
                 "stated text found in notes/05": in_doc, "result": "PASS" if ok else "FAIL", "how": how, "source": source})


def md_table(path, header_startswith):
    """Parse the first markdown table that follows a heading starting with header_startswith."""
    lines = Path(path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("#") and header_startswith in l)
    tab = [l for l in lines[i + 1:] if l.startswith("|")]
    out = []
    for l in lines[i + 1:]:
        if l.startswith("|"):
            out.append(l)
        elif out:
            break
    cells = [[c.strip() for c in l.strip("|").split("|")] for l in out if not l.startswith("|:") and not set(l) <= set("|:- ")]
    return pd.DataFrame(cells[1:], columns=cells[0])


con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")
A = f"(SELECT *, strptime(issue_d,'%b-%Y') dt FROM '{ACC}' WHERE TRY_STRPTIME(issue_d,'%b-%Y') IS NOT NULL)"

# C1
n_all, n07, n08 = con.execute(f"SELECT count(*), sum((year(dt)=2007)::INT), sum((year(dt)=2008)::INT) FROM {A}").fetchone()
chk("C1", "loans 2007 / 2008 / total", ["603", "2,393", "2,260,668"], [n07, n08, n_all], "raw parquet", "duckdb count (re-derived)")
# C2
FIN = "('Fully Paid','Charged Off','Does not meet the credit policy. Status:Fully Paid','Does not meet the credit policy. Status:Charged Off')"
r = con.execute(f"""SELECT year(dt) y, 100*avg((loan_status IN {FIN})::INT) FROM {A} WHERE trim(term)='36 months' AND year(dt)>=2015
                    GROUP BY 1 ORDER BY 1""").fetchall()
r2 = con.execute(f"""SELECT quarter(dt), 100*avg(CASE WHEN loan_status IN {FIN} THEN (loan_status LIKE '%Charged Off')::INT END)
                    FROM {A} WHERE trim(term)='36 months' AND year(dt)=2016 AND quarter(dt)<=2 GROUP BY 1 ORDER BY 1""").fetchall()
chk("C2", "36m % resolved 2015/16/17/18; 2016Q1 vs Q2 bad among resolved %", ["99.9", "71.8", "40.1", "12.0", "16.1", "22.4"],
    [v for _, v in r] + [v for _, v in r2], "raw parquet", "duckdb (re-derived)")
# C3
cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM '{ACC}'").fetchall()]
lk = classify()
cls = pd.Series([lk[c][0] for c in cols])
chk("C3", "POST / LC / total columns", ["38", "9", "151"], [(cls == "POST").sum(), (cls == "LC").sum(), len(cols)],
    "src/audit/leakage_map.py", "classify() over file header (re-derived)")
# C4
r = con.execute(f"""SELECT strftime(dt,'%Y-%m'), 100*avg((coalesce(length(trim("desc")),0)>0)::INT) FROM {A}
                    WHERE dt BETWEEN DATE '2014-03-01' AND DATE '2014-04-01' GROUP BY 1 ORDER BY 1""").fetchall()
after = con.execute(f"""SELECT 100*avg((coalesce(length(trim("desc")),0)>0)::INT) FROM {A} WHERE dt >= DATE '2014-05-01'""").fetchone()[0]
chk("C4", "desc share 2014-03 / 2014-04 / after (%)", ["25", "0.3", "0"], [r[0][1], r[1][1], after], "raw parquet", "duckdb (re-derived)")

# Phase 1 scores (independent recompute with sklearn)
b = load_base().join(pd.read_parquet(ART / "scores_m1.parquet", columns=["score_m1", "pd_m1"])).join(pd.read_parquet(ART / "scores_m2.parquet"))
sg = {g: i for i, g in enumerate(sorted(b.sub_grade.dropna().unique()))}
oo = b[split_mask(b, OOT) & b.bad.notna()]
va = b[split_mask(b, VALID) & b.bad.notna()]
g = lambda y, s: 100 * (2 * roc_auc_score(y, s) - 1)  # noqa: E731
o = m1["oot_2015"]
chk("C5a", "OOT Gini M2 [CI]", ["36.8", "36.3", "37.3"], [g(oo.bad, oo.pd_m2), 100 * o["M2_lgbm"]["gini_lo"], 100 * o["M2_lgbm"]["gini_hi"]],
    "metrics.json + sklearn", "point re-derived with sklearn; CI read", doc_id="C5")
chk("C5b", "OOT Gini M1 [CI]", ["33.7", "33.1", "34.2"], [g(oo.bad, -oo.score_m1), 100 * o["M1_scorecard"]["gini_lo"], 100 * o["M1_scorecard"]["gini_hi"]],
    "metrics.json + sklearn", "point re-derived with sklearn; CI read", doc_id="C5")
d = o["delta_gini_M2_minus_M1"]
chk("C5c", "ΔGini M2−M1 [CI]", ["3.1", "2.8", "3.4"], [g(oo.bad, oo.pd_m2) - g(oo.bad, -oo.score_m1), 100 * d["lo"], 100 * d["hi"]],
    "metrics.json + sklearn", "point re-derived; CI read", doc_id="C5")
dl = o["delta_gini_M2_minus_LC"]
chk("C6", "OOT Gini LC sub-grade [CI]; paired M2 − LC [CI]", ["35.7", "35.2", "36.3", "1.05", "0.56", "1.48"],
    [g(oo.bad, oo.sub_grade.map(sg)), 100 * o["LC_subgrade"]["gini_lo"], 100 * o["LC_subgrade"]["gini_hi"],
     g(oo.bad, oo.pd_m2) - g(oo.bad, oo.sub_grade.map(sg)), 100 * dl["lo"], 100 * dl["hi"]],
    "metrics.json + sklearn", "points re-derived; CIs read")
c1, c2 = m1["cutoff"]["M1_scorecard|validation_2014"]["cutoff"], m1["cutoff"]["M2_lgbm|validation_2014"]["cutoff"]
chk("C7", "validation approval % M2 vs M1", ["82.1", "77.4"], [100 * (va.pd_m2 <= c2).mean(), 100 * (va.score_m1 >= c1).mean()],
    "metrics.json cutoffs + scores", "approval re-derived")
mat = mon[mon.KS_M2.notna()]
chk("C8", "KS M2 min / max on matured quarters; validation KS; min ≥ 0.9×valid", ["25.9", "27.1", "26.4"],
    [100 * mat.KS_M2.min(), 100 * mat.KS_M2.max(), 100 * m1["validation_2014"]["M2_lgbm"]["ks"]], "monitoring.json + metrics.json", "read")
rows[-1]["result"] = rows[-1]["result"] if mat.KS_M2.min() >= 0.9 * m1["validation_2014"]["M2_lgbm"]["ks"] else "FAIL"
citl = 100 * (oo.pd_m2.mean() - oo.bad.mean())
cm = m1["cutoff"]["M2_lgbm|oot_2015"]
appr = oo[oo.pd_m2 <= c2]
chk("C9", "CITL M2 pp [CI]; OOT approved bad % [CI]", ["-1.75", "-1.87", "-1.63", "11.91", "11.78", "12.04"],
    [citl, 100 * o["M2_lgbm"]["citl_lo"], 100 * o["M2_lgbm"]["citl_hi"], 100 * appr.bad.mean(), 100 * cm["approved_bad_ci"][0], 100 * cm["approved_bad_ci"][1]],
    "metrics.json + scores", "points re-derived; CIs read")
chk("C10", "max PSI M2 2014–2018", ["0.058"], [mon.PSI_M2.max()], "monitoring.json", "read")
ms = mon.set_index("issue_q")
chk("C11", "PSI M1 2018Q3 / Q4; % below cutoff 2014Q1 / 2018Q4", ["0.11", "0.12", "21", "10"],
    [ms.PSI_M1["2018Q3"], ms.PSI_M1["2018Q4"], 100 * ms.pct_below_cut_M1["2014Q1"], 100 * ms.pct_below_cut_M1["2018Q4"]], "monitoring.json", "read")
q = b.groupby("issue_q")
ru = q.revol_util.median()
sv = q.verification_status.apply(lambda s_: 100 * (s_ == "Source Verified").mean())
sv_after = sv[(sv.index >= "2014Q1") & (sv.index <= "2018Q4")]
chk("C12", "median revol_util 2013Q2 → 2017Q4; Source Verified % 2013Q2; min / max 2014Q1–2018Q4",
    ["59", "41", "16", "35", "47"], [ru["2013Q2"], ru["2017Q4"], sv["2013Q2"], sv_after.min(), sv_after.max()], "p1_base", "pandas (re-derived)")
cuts = np.quantile(b.loc[split_mask(b, TRAIN), "score_m1"], [0.2, 0.4, 0.6, 0.8])
b["band"] = 1 + np.searchsorted(cuts, b.score_m1.to_numpy(), side="right")
b["d12"] = default_by_mob(b.default_mob, 12)
bm = b.groupby(["issue_q", "band"]).d12.mean().mul(100)
chk("C13", "band1 @12 2013Q4→2016Q3; band5 2013Q4→2016Q3 (%)", ["7.0", "10.8", "1.1", "2.3"],
    [bm["2013Q4", 1], bm["2016Q3", 1], bm["2013Q4", 5], bm["2016Q3", 5]], "p1_base + scores", "re-derived")
first_amber_m2 = ms.index[ms.flag_AE12_M2.isin(["AMBER", "RED"])][0]
fmt_m = lambda k: pd.Timestamp(k).strftime("%b %Y")  # noqa: E731
nbooked = int(b[(b.issue_q >= "2015Q2") & (b.issue_q <= "2016Q4")].shape[0])
chk("C14", "first amber (M2) quarter / knowable; first red knowable M2, M1; loans 2015Q2–16Q4",
    ["2015Q2", "Dec 2016", "Sep 2017", "Jun 2017", "544,642"],
    [first_amber_m2, fmt_m(ms.known_MOB12[first_amber_m2]), fmt_m(ms.known_MOB12[ms.index[ms.flag_AE12_M2 == "RED"][0]]),
     fmt_m(ms.known_MOB12[ms.index[ms.flag_AE12_M1 == "RED"][0]]), nbooked], "monitoring.json + p1_base", "read + count")
ex = md_table(R1 / "exploratory_early_signal.md", "First flag")
e15 = ex[(ex.signal == "A/E MOB6 M2") & (ex.level == "AMBER/RED")].iloc[0]
chk("C15", "MOB6 first amber (M2) knowable", ["Jun 2016"], [fmt_m(e15["knowable at"])], "exploratory_early_signal.md", "parsed")
rows[-1]["result"] = rows[-1]["result"] if e15["first issue quarter"] == "2015Q2" else "FAIL"
mt = md_table(R2 / "mob6_test.md", "Summary")
cf = md_table(R2 / "mob6_test.md", "Discovery-period confusion matrix").set_index("model")
chk("C16", "MOB6 2016–17 flagged (M1 = M2); discovery M2 sensitivity / specificity (descriptive)", ["7/7", "1/2", "6/6"],
    [mt["sensitivity (amber+)"][0].split(" ")[0], cf.loc["M2", "sensitivity"], cf.loc["M2", "specificity"]], "mob6_test.md", "parsed")
rows[-1]["result"] = rows[-1]["result"] if mt["sensitivity (amber+)"][1].split(" ")[0] == "7/7" else "FAIL"
pa = pd.read_parquet(ROOT / "data" / "interim" / "p2" / "pred_A.parquet")
p15 = pa[pa.issue_q.str.startswith("2015")]
chk("C17", "2015 lifetime PD naive / competing-risks / actual (%)", ["18.2", "13.6", "14.9"],
    [100 * p15.pd_life_naive.mean(), 100 * p15.pd_life.mean(), 100 * oo.bad.mean()], "pred_A.parquet + p1_base", "re-derived")
sa = md_table(R2 / "survival_A.md", "A/E of cumulative default by period").set_index("period")
f = lambda per, cs: [float(sa.loc[per, c]) for c in cs if sa.loc[per, c] not in ("nan", "")]  # noqa: E731
A3 = ["A/E@12", "A/E@24", "A/E@36"]
chk("C18", "A/E train (mean @12/24/36); 2014 min/max; 2015 min/max; 2016 min/max; 2017 @12",
    ["1.01", "0.98", "1.02", "1.07", "1.11", "1.26", "1.39", "1.44"],
    [np.mean(f("train 2012Q4-13", A3)), min(f("valid 2014", A3)), max(f("valid 2014", A3)), min(f("OOT 2015", A3)), max(f("OOT 2015", A3)),
     min(f("2016", A3)), max(f("2016", A3)), f("2017", A3)[0]], "survival_A.md", "parsed")
chk("C19", "θ [CI]; rule b rel. change %; stress multiplier", ["-0.038", "-0.094", "-0.004", "-27.1", "0.91"],
    [mb["rule_a"]["theta"], mb["rule_a"]["ci"][0], mb["rule_a"]["ci"][1], 100 * mb["rule_b"]["rel_change"], mb["rule_c"]["multiplier"]],
    "macro_B.json", "read")
rows[-1]["result"] = rows[-1]["result"] if (not mb["rule_a"]["pass"] and mb["rule_b"]["pass"] and not mb["rule_c"]["pass"]) else "FAIL"
chk("C20", "γ_u default (level coefficient)", ["-0.062"], [mb["primary"]["gamma_u_default"]], "macro_B.json", "read")
t = ecl["total"]
chk("C21", "pred EL $m / realised $m / ratio / % of realised missed", ["234.9", "273.8", "1.17", "14"],
    [t["pred EL (undisc) $m"], t["realised loss $m"], t["realised / predicted"], 100 * (1 - t["pred EL (undisc) $m"] / t["realised loss $m"])],
    "ecl.json", "read")
eb = md_table(R2 / "ecl.md", "Backtest by risk band")
chk("C22", "realised/pred safest band 1 / riskiest band 5", ["1.52", "1.00"],
    [float(eb["realised / predicted"].iloc[0]), float(eb["realised / predicted"].iloc[-1])], "ecl.md", "parsed")
chk("C23", "12m ECL $m (%), lifetime $m (%), LGD % [CI]", ["100.7", "2.8", "202.7", "5.6", "88.8", "88.6", "89.0"],
    [t["day-1 ECL 12m $m"], 100 * t["day-1 ECL 12m $m"] / t["funded $m"], t["lifetime ECL $m"], 100 * t["lifetime ECL $m"] / t["funded $m"],
     100 * ecl["LGD"], 100 * ecl["LGD_CI"][0], 100 * ecl["LGD_CI"][1]], "ecl.json", "read")
ot = ov["total"]
chk("C24", "overlay EL MOB12 / MOB6 $m; gap closed % MOB12 / MOB6", ["256.0", "237.3", "54", "6"],
    [ot["EL_ovl12 $m"], ot["EL_ovl6 $m"], 100 * ot["gap closed MOB12"], 100 * ot["gap closed MOB6"]], "overlay.json", "read")
P = pd.DataFrame(pc["0.05"]["table"])
P = P[P.set == "OOT 2015"].set_index("policy")
P.index = [("M2 cutoff" if i.startswith("Phase 1 M2") else i) for i in P.index]
chk("C25", "undiscounted profit approve-all / MILP $m", ["230.3", "222.3"],
    [P.loc["approve all", "realised profit $m"], P.loc["C: MILP cells", "realised profit $m"]], "policy_C.json", "read")
chk("C26", "NPV@5% cutoff / MILP / approve-all $m", ["47.4", "45.6", "28.4"],
    [P.loc["M2 cutoff", "EXPLORATORY realised NPV $m"], P.loc["C: MILP cells", "EXPLORATORY realised NPV $m"],
     P.loc["approve all", "EXPLORATORY realised NPV $m"]], "policy_C.json", "read")

# ---- extensions (notes/08_prereg_extensions.md; results notes/10_extensions_results.md)
R4 = ROOT / "reports" / "phase4"
p60 = pd.read_parquet(ROOT / "data" / "interim" / "p4_60m.parquet")
p60["issue_dt"] = pd.to_datetime(p60.issue_dt)
ref60 = p60[(p60.issue_dt >= "2012-09-01") & (p60.issue_dt <= "2013-12-01")]
d6r, d12r = default_by_mob(ref60.default_mob, 6), default_by_mob(ref60.default_mob, 12)
r6_60, ref12_60 = d6r.mean() / ref60.pd_m2.mean(), d12r.mean()
tp = tn = npos = nneg = 0
for qq in [f"{y}Q{k}" for y in range(2014, 2018) for k in (1, 2, 3, 4)][:15]:
    gq = p60[p60.issue_q == qq]
    ae6 = default_by_mob(gq.default_mob, 6).sum() / (gq.pd_m2.sum() * r6_60)
    truth = default_by_mob(gq.default_mob, 12).mean() >= 1.2 * ref12_60
    npos += truth
    nneg += (not truth)
    tp += truth and ae6 > 1.10
    tn += (not truth) and ae6 <= 1.10
chk("C27", "60m MOB-6 test: sensitivity / specificity / specificity %", ["9/9", "4/6", "67"],
    [f"{tp}/{npos}", f"{tn}/{nneg}", 100 * tn / nneg], "p4_60m.parquet", "re-derived from row-level 60m table")
v27 = json.loads((R4 / "mob6_60m_test.json").read_text())["results"]["M2"]["verdict"]
rows[-1]["result"] = rows[-1]["result"] if v27 == "FAIL" else "FAIL"
aj = json.loads((R4 / "asof_model.json").read_text())
sa_ = pd.read_parquet(ROOT / "data" / "interim" / "p4" / "scores_asof.parquet")
bo = b.join(sa_)
oo_ = bo[split_mask(bo, OOT) & bo.bad.notna()]
dga = aj["oot_delta_gini_asof_minus_M2"]
chk("C28", "as-of Gini [CI]; ΔGini vs reference [CI]", ["33.1", "32.6", "33.7", "-3.65", "-3.95", "-3.37"],
    [g(oo_.bad, oo_.pd12_asof), 100 * aj["oot_final"]["asof_PD12"]["gini_lo"], 100 * aj["oot_final"]["asof_PD12"]["gini_hi"],
     g(oo_.bad, oo_.pd12_asof) - g(oo_.bad, oo_.pd_m2), 100 * dga["lo"], 100 * dga["hi"]], "asof_model.json + sklearn", "points re-derived")
mo = pd.DataFrame(aj["monitoring"])
chk("C29", "as-of first amber knowable / first red knowable / max PSI", ["Jun 2017", "Sep 2017", "0.079"],
    [fmt_m(aj["first_amber"]["knowable"]), fmt_m(aj["first_red"]["knowable"]), mo.PSI.max()], "asof_model.json", "read")
rows[-1]["result"] = rows[-1]["result"] if (aj["first_amber"]["issue_q"], aj["first_red"]["issue_q"]) == ("2015Q4", "2016Q1") else "FAIL"
eb_ = json.loads((R2 / "ecl_benchmark.json").read_text())
c_ = eb_["(c) refit at 2014-12-31, discounted LGD (k=12)"]
a_ = eb_["(a) reference A, undiscounted LGD"]
chk("C30", "refit pred EL $m / realised $m / ratio refit / ratio reference", ["249.0", "273.8", "1.10", "1.17"],
    [c_["backtest: pred EL (undisc.) $m"], eb_["realised_loss_m"], c_["realised / predicted"], a_["realised / predicted"]], "ecl_benchmark.json", "read")
d_ = eb_["(d) 90-DPD default definition, discounted LGD (k=12)"]
b_ = eb_["(b) reference A, discounted LGD (k=12)"]
chk("C31", "LGD discounted / undiscounted %; 12m ECL 90-DPD / reference (disc.) $m; 90-DPD backtest ratio",
    ["90.4", "88.8", "80.1", "102.5", "1.17"],
    [100 * eb_["LGD_discounted"]["12"], 100 * eb_["LGD_undiscounted"], d_["day-1 12m ECL $m"], b_["day-1 12m ECL $m"], d_["realised / predicted"]],
    "ecl_benchmark.json", "read")
stg = pd.DataFrame(ecl["staging"])
chk("C32", "stage 2 loans / stage 3 loans / stage 1 allowance $m / coverage %", ["1,571", "2,300", "112.3", "3.75"],
    [stg.loans[1], stg.loans[2], stg["allowance $m"][0], stg["coverage %"][0]], "ecl.json", "read")

# ---- the 'up to 47% above expected' figure (notes/04_story.md one-line answer + fig3 subtitle)
trm = split_mask(b, TRAIN)
r12 = b.loc[trm, "d12"].mean() / b.loc[trm, "bad"].mean()
ae = {qq: gg.d12.sum() / (gg.pd_m2.sum() * r12) for qq, gg in b[b.issue_q.isin(ms.index[ms.AE12_M2.notna()])].groupby("issue_q")}
peak_q = max(ae, key=ae.get)
chk("X47", "peak MOB-12 A/E (champion) and its quarter ('up to 47% above expected')", ["1.47", "2016Q3"], [ae[peak_q], peak_q],
    "p1_base + scores", "re-derived: Σ defaults by MOB12 / (Σ PD_M2 × r12)")
sa_q = md_table(R2 / "survival_A.md", "By issue quarter").set_index("issue_q")
chk("X47b", "corroboration: lifetime-model A/E @12 for 2016Q3", ["1.44"], [float(sa_q.loc["2016Q3", "AE@12"])], "survival_A.md",
    "independent model (competing-risks hazard)")
story = (ROOT / "notes" / "04_story.md").read_text()
rows[-2]["stated text found in notes/05"] = "story: " + ("yes" if "up to 47% above" in story and "1.47 (2016Q3)" in story else "NO")
if not rows[-2]["stated text found in notes/05"].endswith("yes"):
    rows[-2]["result"] = "FAIL"

T = pd.DataFrame(rows)
n_fail = (T.result == "FAIL").sum()
md = (f"# Claim re-check — {len(T)} checks, {len(T) - n_fail} PASS, {n_fail} FAIL\n\n"
      "Generated by src/quality/check_claims.py. 'how' says whether the number was re-derived independently or read from the cited file.\n\n"
      + T.to_markdown(index=False) + "\n")
(ROOT / "reports" / "quality" / "claims_check.md").write_text(md)
print(md)
sys.exit(1 if n_fail else 0)
