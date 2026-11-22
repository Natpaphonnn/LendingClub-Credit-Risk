"""Independent re-derivation of every ECL and policy claim in notes/07_article_draft.md (Nat, 2026-11-20).

Separate code path from the pipeline: reads the RAW Kaggle .csv.gz with duckdb (own SQL for population, event timing and features),
scores with the frozen LightGBM model FILE only (own model frame), refits every competing-risks hazard with sklearn's multinomial
logistic regression (not the project's Newton solver), and re-implements annuity balances, LGD, discounting, ECL, backtest, overlay,
staging, the MILP policy and the paired bootstrap. Imports nothing from src/phase1, src/phase2 or src/lib except the frozen definition
lists in config.py (feature names, windows) — definitions, not computations.

Each check: the value exactly as stated in the article (string), the independently recomputed value, PASS if they agree at the stated
precision. Bootstrap CI end points use an independent random stream, so they are compared with a Monte-Carlo tolerance of ±0.10 ($m).
Output: reports/quality/rederive_ecl_policy.md ; exit 1 on any FAIL.
Usage: nice -n 19 .venv/bin/python -I src/quality/rederive_ecl_policy.py
"""
import json
import re
import sys
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.interpolate import BSpline
from scipy.optimize import Bounds, LinearConstraint, milp
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
import warnings  # noqa: E402

warnings.simplefilter("error", ConvergenceWarning)      # a non-converged refit must fail, not pass silently

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
from config import CATEGORICAL, DERIVED, FEATURES, NUMERIC  # noqa: E402  (definitions only)

RAW = ROOT / "data" / "raw" / "accepted_2007_to_2018Q4.csv.gz"
ARTICLE = (ROOT / "notes" / "07_article_draft.md").read_text().replace("−", "-")
H = 36
rng = np.random.default_rng(7)          # independent of the pipeline's seeds

# ------------------------------------------------------------------ 1. population and outcomes straight from the raw file
num_sql = ",\n  ".join(f"TRY_CAST({c} AS DOUBLE) AS {c}" for c in NUMERIC)
con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")
L = con.execute(f"""
WITH r AS (
  SELECT *, TRY_STRPTIME(issue_d, '%b-%Y')::DATE AS idt, TRY_STRPTIME(last_pymnt_d, '%b-%Y')::DATE AS ldt
  FROM read_csv('{RAW}', header=true, all_varchar=true, null_padding=true, ignore_errors=true)
)
SELECT id, idt, loan_status,
  TRY_CAST(funded_amnt AS DOUBLE) AS funded, TRY_CAST(int_rate AS DOUBLE) AS rate, TRY_CAST(loan_amnt AS DOUBLE) AS amt,
  TRY_CAST(total_rec_prncp AS DOUBLE) AS prin_rec, TRY_CAST(recoveries AS DOUBLE) AS rec,
  TRY_CAST(collection_recovery_fee AS DOUBLE) AS fee, TRY_CAST(total_pymnt AS DOUBLE) AS paid,
  12 * (year(ldt) - year(idt)) + month(ldt) - month(idt) AS lmob,
  {num_sql},
  TRY_CAST(fico_range_low AS DOUBLE) + 2 AS fico,
  12 * (year(idt) - year(TRY_STRPTIME(earliest_cr_line, '%b-%Y'))) + month(idt) - month(TRY_STRPTIME(earliest_cr_line, '%b-%Y')) AS credit_hist_months,
  TRY_CAST(loan_amnt AS DOUBLE) / NULLIF(TRY_CAST(annual_inc AS DOUBLE), 0) AS loan_to_income,
  CASE WHEN emp_length = '< 1 year' THEN 0 WHEN emp_length = '10+ years' THEN 10
       ELSE TRY_CAST(regexp_extract(emp_length, '^([0-9]+)', 1) AS INT) END AS emp_length_yrs,
  home_ownership, verification_status, purpose
FROM r
WHERE idt IS NOT NULL AND trim(term) = '36 months' AND application_type = 'Individual' AND loan_status NOT LIKE 'Does not meet%'
  AND idt >= DATE '2009-01-01' AND idt <= DATE '2015-12-01'
""").df()
L["idt"] = pd.to_datetime(L.idt)
for c in ("lmob", "credit_hist_months", "emp_length_yrs"):
    L[c] = pd.to_numeric(L[c]).astype(float)
L["yr"] = L.idt.dt.year
L["q"] = L.idt.dt.to_period("Q").astype(str)
L["is_def"] = L.loan_status.isin(["Charged Off", "Default"])
L["dmob"] = np.where(L.is_def, np.where(L.lmob.isna(), 1, L.lmob + 1), np.nan)     # first missed payment = month after last payment
L["final"] = L.loan_status.isin(["Charged Off", "Default", "Fully Paid"])

# ------------------------------------------------------------------ 2. frozen champion score (model file only)
booster = lgb.Booster(model_file=str(ROOT / "data" / "interim" / "p1" / "lgbm.txt"))
assert booster.feature_name() == list(FEATURES)
cats = json.loads((ROOT / "data" / "interim" / "p1" / "lgbm_cats.json").read_text())
X = L[FEATURES].astype({c: float for c in NUMERIC + DERIVED}).copy()
for c in CATEGORICAL:
    X[c] = pd.Categorical(L[c].where(L[c].isin(cats[c])), categories=cats[c])
L["pd"] = booster.predict(X)
L["lp"] = np.log(L.pd / (1 - L.pd))

# ------------------------------------------------------------------ 3. competing-risks hazard, refitted with sklearn
_KN = np.r_[[1.0] * 4, 1 + 35 / 3, 1 + 70 / 3, [36.0] * 4]
BASIS = BSpline.design_matrix(np.arange(1, 37, dtype=float), _KN, 3).toarray()[:, 1:]       # 5 columns (6 df incl. intercept)


def events(d, W, shift=0):
    """event 1 = default at d (+shift), 2 = prepay (fully paid ≥ 3 months early), 0 = censored."""
    dm = d.dmob.to_numpy() + shift
    p = np.maximum(d.lmob.to_numpy(), 1)
    T, ev = W.astype(float).copy(), np.zeros(len(d), int)
    m1 = d.is_def.to_numpy() & (np.nan_to_num(dm, nan=999) <= W)
    T[m1], ev[m1] = dm[m1], 1
    fp = (d.loan_status == "Fully Paid").to_numpy()
    m2 = fp & (np.nan_to_num(p, nan=999) <= np.minimum(33, W))
    T[m2], ev[m2] = p[m2], 2
    m3 = fp & (np.nan_to_num(p, nan=-1) > 33) & (np.nan_to_num(p, nan=999) <= W)
    T[m3] = p[m3]
    return T.astype(int), ev


class Hazard:
    def __init__(self, d, W, shift=0, basis_cols=5):
        self.mr, self.sr = d.rate.mean(), d.rate.std()
        la = np.log(d.amt)
        self.ma, self.sa = la.mean(), la.std()
        self.k = basis_cols
        T, ev = events(d, W, shift)
        keep = T >= 1
        T, ev, dd = T[keep], ev[keep], d[keep]
        idx = np.repeat(np.arange(len(dd)), T)
        t = np.arange(len(idx)) - np.repeat(np.cumsum(T) - T, T) + 1
        y = np.zeros(len(t), int)
        y[np.cumsum(T) - 1] = ev
        Z = self.design(self.cols(dd)[idx], t)
        self.m = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=5000, tol=1e-10).fit(Z, y)
        self.max_mob = int(T.max())
        self.n_def = int((ev == 1).sum())

    def cols(self, d):
        return np.column_stack([d.lp.to_numpy(), (d.rate.to_numpy() - self.mr) / self.sr, (np.log(d.amt.to_numpy()) - self.ma) / self.sa])

    def design(self, C, t):
        return np.column_stack([BASIS[t - 1][:, :self.k], C[:, 0], C[:, 0] * t / 36, C[:, 1], C[:, 2]])

    def hazards(self, d):
        C, n = self.cols(d), len(d)
        hd_, hp_ = np.empty((n, H)), np.empty((n, H))
        for s in range(0, n, 50_000):
            m_ = min(n - s, 50_000)
            P = self.m.predict_proba(self.design(np.repeat(C[s:s + m_], H, axis=0), np.tile(np.arange(1, H + 1), m_)))
            hd_[s:s + m_], hp_[s:s + m_] = P[:, 1].reshape(m_, H), P[:, 2].reshape(m_, H)
        return hd_, hp_


def cif(hd, hp):
    s = np.cumprod(1 - hd - hp, axis=1)
    sp = np.hstack([np.ones((len(hd), 1)), s[:, :-1]])
    return sp, sp * hd


def annuity(d):
    r = d.rate.to_numpy()[:, None] / 1200
    P = d.funded.to_numpy()[:, None]
    t = np.arange(1, H + 1)[None, :]
    pmt = P * r / (1 - (1 + r) ** -H)
    bal = P * (1 + r) ** (t - 1) - pmt * ((1 + r) ** (t - 1) - 1) / r          # balance at the start of month t
    return r, pmt[:, 0], bal


train = L[(L.idt >= "2012-09-01") & (L.idt <= "2013-12-01")].reset_index(drop=True)
port = L[L.yr == 2015].reset_index(drop=True)
W_full = lambda d: np.minimum(36, 12 * (2018 - d.idt.dt.year) + 9 - d.idt.dt.month).to_numpy()  # noqa: E731  (outcomes to 2018-09)
A = Hazard(train, W_full(train))

# LGD (pooled, EAD-weighted, train-window defaults)
dtr = train[train.is_def]
ead_d = (dtr.funded - dtr.prin_rec).to_numpy()
net = (dtr.rec - dtr.fee).to_numpy()
ok = ead_d > 0
LGD = float((np.clip(1 - net / ead_d, 0, 1)[ok] * ead_d[ok]).sum() / ead_d[ok].sum())
r12 = dtr.rate.to_numpy() / 1200
LGD12 = float((np.clip(1 - net * (1 + r12) ** -12 / ead_d, 0, 1)[ok] * ead_d[ok]).sum() / ead_d[ok].sum())

r, pmt, bal = annuity(port)
DF = (1 + r) ** -np.arange(1, H + 1)[None, :]
hd, hp = A.hazards(port)
sp, md = cif(hd, hp)
real = np.where(port.is_def, port.funded - port.prin_rec - port.rec + port.fee, 0.0)
EL = (md * LGD * bal).sum(1)
ecl12, ecll = (md * LGD * bal * DF)[:, :12].sum(), (md * LGD * bal * DF).sum()

# in-sample
_, _, bal_t = annuity(train)
_, md_t = cif(*A.hazards(train))
in_ratio = np.where(train.is_def, train.funded - train.prin_rec - train.rec + train.fee, 0).sum() / (md_t * LGD * bal_t).sum()

# refit at 2014-12-31 (outcomes to 2014-06): pre-registered 2012-09 start for months 1–21, tails from reference A or the 2009-start refit
def refit_set(start):
    d = L[(L.idt >= start) & (L.idt <= "2014-12-01")].copy()
    W = np.minimum(36, 12 * (2014 - d.idt.dt.year) + 6 - d.idt.dt.month).to_numpy()
    keep = W >= 1
    return d[keep].reset_index(drop=True), W[keep]


d12, W12 = refit_set("2012-09-01")
R12 = Hazard(d12, W12, basis_cols=4)            # last basis column is zero for t ≤ 24.3: not identified, dropped
d09, W09 = refit_set("2009-01-01")
R09 = Hazard(d09, W09)
cut = R12.max_mob


def splice(early, tail):
    a, b = early.hazards(port), tail.hazards(port)
    return [np.hstack([x[:, :cut], y[:, cut:]]) for x, y in zip(a, b)]


def el_of(h):
    return (cif(*h)[1] * LGD * bal).sum()


ratio_c = real.sum() / el_of(splice(R12, A))
ratio_cc = real.sum() / el_of(splice(R12, R09))

# later default definitions: default dated at the 3rd / 4th missed instalment; EAD = scheduled balance at the first missed month
ecl12_disc = (md * LGD12 * bal * DF)[:, :12].sum()
res_late = {}
for k in (2, 3):
    Hk = Hazard(train, W_full(train), shift=k)
    _, mdk = cif(*Hk.hazards(port))
    balk = bal[:, np.maximum(np.arange(H) - k, 0)]
    res_late[k] = (mdk * LGD12 * balk * DF)[:, :12].sum()

# overlay (MOB-12 A/E per issue quarter)
q = port.q.to_numpy()
obs12 = (np.nan_to_num(port.dmob.to_numpy(), nan=999) <= 12)
C12 = md[:, :12].sum(1)
ovl = sum(EL[q == qq].sum() * obs12[q == qq].mean() / C12[q == qq].mean() for qq in np.unique(q))
gap_closed = (ovl - EL.sum()) / (real.sum() - EL.sum())

# staging at Dec-2015 (missed instalments m from the first missed payment month)
due = (12 * (2015 - port.idt.dt.year) + 12 - port.idt.dt.month).to_numpy()
dm = port.dmob.to_numpy()
m = np.where(port.is_def & (np.nan_to_num(dm, nan=999) <= due), due - np.nan_to_num(dm, nan=0) + 1, 0)
st = {"s2_pre": int(((m >= 1) & (m <= 2)).sum()), "s3_pre": int((m >= 3).sum()), "s2_bs": int(((m >= 2) & (m <= 3)).sum()), "s3_bs": int((m >= 4).sum())}

# ------------------------------------------------------------------ 4. policy C
va = L[L.yr == 2014].reset_index(drop=True)
lab = va[va.final]
# exact cutoff: largest PD value whose cumulative approved bad rate (ties grouped) ≤ 11%
g = lab.groupby("pd").is_def.agg(["sum", "size"]).sort_index()
pd_cut = float(g.index[(g["sum"].cumsum() / g["size"].cumsum() <= 0.11).to_numpy()].max())


def exp_npv(d, rate):
    hd_, hp_ = A.hazards(d)
    sp_, _ = cif(hd_, hp_)
    _, pm, bl = annuity(d)
    disc = (1 + rate) ** (-np.arange(1, H + 1) / 12)
    cash = sp_ * ((1 - hd_ - hp_) * pm[:, None] + hp_ * bl + hd_ * (1 - LGD) * bl)
    return (cash * disc).sum(1) - d.funded.to_numpy()


def real_npv(d, rate):
    n = np.maximum(np.nan_to_num(d.lmob.to_numpy(), nan=1), 1)
    mr = (1 + rate) ** (1 / 12) - 1
    pay = (d.paid - d.rec).to_numpy()
    return pay / n * (1 - (1 + mr) ** -n) / mr + (d.rec - d.fee).to_numpy() * (1 + mr) ** -(n + 6) - d.funded.to_numpy()


dec = np.quantile(va.pd, np.linspace(0, 1, 11)[1:-1])
cell = lambda d: np.searchsorted(dec, d.pd.to_numpy(), side="right") * 3 + np.searchsorted([10_000, 20_000], d.funded.to_numpy(), side="left")  # noqa: E731
pol = {}
for rate in (0.03, 0.05, 0.08):
    va["npv"], port["npv"] = exp_npv(va, rate), exp_npv(port, rate)
    cv, co = cell(va), cell(port)
    n_c = np.bincount(cv, minlength=30)
    v_c = np.bincount(cv, weights=va.npv, minlength=30)
    p_c = np.bincount(cv, weights=va.pd, minlength=30)
    sol = milp(-v_c, constraints=LinearConstraint(np.vstack([n_c, p_c - 0.11 * n_c]), [0.75 * len(va), -np.inf], [np.inf, 0]),
               integrality=np.ones(30), bounds=Bounds(0, 1))
    appr = np.where(np.round(sol.x) == 1)[0]
    sv = va.sort_values("pd")
    cn = np.arange(1, len(sv) + 1)
    feas = (cn >= 0.75 * len(sv)) & (sv.pd.cumsum().to_numpy() / cn <= 0.11)
    thr = float(sv.pd.iloc[int(np.argmax(np.where(feas, sv.npv.cumsum().to_numpy(), -np.inf)))])
    mC, mM, mS = np.isin(co, appr), (port.pd <= pd_cut).to_numpy(), (port.pd <= thr).to_numpy()
    prof = (port.paid - port.fee - port.funded).to_numpy()
    rn = real_npv(port, rate)
    diffs = []
    for _ in range(500):
        w = np.bincount(rng.integers(0, len(port), len(port)), minlength=len(port))
        diffs.append((w * rn * (mC.astype(float) - mM)).sum() / 1e6)
    pol[rate] = {"npv_cut": rn[mM].sum() / 1e6, "npv_milp": rn[mC].sum() / 1e6, "npv_all": rn.sum() / 1e6, "npv_single": rn[mS].sum() / 1e6,
                 "prof_all": prof.sum() / 1e6, "prof_milp": prof[mC].sum() / 1e6, "diff": (rn * (mC.astype(float) - mM)).sum() / 1e6,
                 "ci": np.percentile(diffs, [2.5, 97.5]), "appr_milp": 100 * mC.mean(), "appr_cut": 100 * mM.mean()}
p5, p3, p8 = pol[0.05], pol[0.03], pol[0.08]

# ------------------------------------------------------------------ 5. compare with the article
rows = []


def chk(cid, what, stated, got, tol=None):
    s = stated.replace("−", "-")
    found = s in ARTICLE
    num = float(re.sub(r"[^0-9.\-]", "", s.split("[")[0].split(" to ")[0]) or "nan") if re.search(r"\d", s) else None
    if tol is None:
        dec_ = len(re.sub(r"[^0-9.]", "", s).split(".")[1]) if "." in re.sub(r"[^0-9.]", "", s) else 0
        ok = num is not None and round(float(got), dec_) == round(num, dec_)
    else:
        ok = abs(float(got) - num) <= tol
    rows.append({"id": cid, "claim": what, "stated in article": stated, "recomputed": got if isinstance(got, str) else round(float(got), 4),
                 "in article": "yes" if found else "NO", "result": "PASS" if ok and found else "FAIL"})


chk("E1", "2015 portfolio funded ($bn)", "$3.62 billion", port.funded.sum() / 1e9)
chk("E2", "pooled LGD (%)", "88.8%", 100 * LGD)
chk("E3", "recoveries ≈ share of exposure at default (%)", "about 11%", 100 * (1 - LGD))
chk("E4", "day-1 12-month ECL ($m)", "$100 million", ecl12 / 1e6)
chk("E5", "lifetime ECL ($m)", "$201 million", ecll / 1e6)
chk("E6", "predicted lifetime EL, undiscounted ($m)", "$232 million", EL.sum() / 1e6)
chk("E7", "realised net principal loss ($m)", "$274 million", real.sum() / 1e6)
chk("E8", "realised / predicted", "1.18×", real.sum() / EL.sum())
chk("E9", "in-sample realised / predicted (development window)", "1.03×", in_ratio)
chk("E10", "refit at 2014-12: max months on book observed", "21 months", cut)
chk("E11", "refit (months 1–21) + reference tail: realised / predicted", "1.27×", ratio_c)
chk("E12", "refit with a knowable tail: realised / predicted", "1.41×", ratio_cc)
chk("E13", "month-12 overlay: share of gap closed (%)", "57%", 100 * gap_closed)
chk("E14", "12m ECL, default at 3rd missed instalment ($m, discounted LGD)", "$79 million", res_late[2] / 1e6)
chk("E15", "12m ECL, default at 4th missed instalment ($m)", "$68 million", res_late[3] / 1e6)
chk("E16", "12m ECL, reference definition, discounted LGD ($m)", "$101 million", ecl12_disc / 1e6)
chk("E17", "staging: 1–2 missed instalments (loans)", "1,571", st["s2_pre"])
chk("E18", "staging: ≥ 3 missed instalments (loans)", "2,300", st["s3_pre"])
chk("E19", "staging, backstop-consistent: 2–3 missed (loans)", "1,521", st["s2_bs"])
chk("E20", "staging, backstop-consistent: ≥ 4 missed (loans)", "1,640", st["s3_bs"])
chk("P1", "undiscounted realised profit, approve everyone ($m)", "$230 million", p5["prof_all"])
chk("P2", "undiscounted realised profit, MILP ($m)", "$222 million", p5["prof_milp"])
chk("P3", "realised NPV at 5%: PD cutoff ($m)", "$47.5 million", p5["npv_cut"])
chk("P4", "realised NPV at 5%: MILP ($m)", "$45.8 million", p5["npv_milp"])
chk("P5", "realised NPV at 5%: approve everyone ($m)", "$28.4 million", p5["npv_all"])
chk("P6", "realised NPV at 5%: single threshold tuned to NPV ($m)", "$44.9 million", p5["npv_single"])
chk("P7", "MILP − cutoff at 5% ($m)", "-$1.7 million", p5["diff"])
chk("P8", "bootstrap CI lower end ($m; MC tolerance ±0.10)", "-2.7 to -0.8", p5["ci"][0], tol=0.10)
rows[-1]["recomputed"] = f"[{p5['ci'][0]:.2f}, {p5['ci'][1]:.2f}]"
ok_hi = abs(p5["ci"][1] - (-0.8)) <= 0.10
rows[-1]["result"] = "PASS" if rows[-1]["result"] == "PASS" and ok_hi else "FAIL"
chk("P9", "approval: PD cutoff (%)", "82%", p5["appr_cut"])
chk("P10", "approval: MILP (%)", "86%", p5["appr_milp"])
rows.append({"id": "P11", "claim": "at 3% MILP and cutoff indistinguishable (CI contains 0); at 8% MILP better and approves fewer",
             "stated in article": "indistinguishable / approves fewer", "recomputed": f"3%: {p3['diff']:+.2f} [{p3['ci'][0]:.2f}, {p3['ci'][1]:.2f}]; "
             f"8%: {p8['diff']:+.2f}, approval {p8['appr_milp']:.1f}% vs {p8['appr_cut']:.1f}%",
             "in article": "yes" if "indistinguishable" in ARTICLE and "approves fewer" in ARTICLE else "NO",
             "result": "PASS" if (p3["ci"][0] < 0 < p3["ci"][1]) and p8["diff"] > 0 and p8["appr_milp"] < p8["appr_cut"] else "FAIL"})

T = pd.DataFrame(rows)
n_fail = int((T.result == "FAIL").sum())
md_ = (f"# Independent re-derivation of the article's ECL and policy claims — {len(T)} checks, {len(T) - n_fail} PASS, {n_fail} FAIL\n\n"
       "Generated by src/quality/rederive_ecl_policy.py: raw .csv.gz → duckdb (own SQL) → frozen model file → hazards refitted with sklearn →\n"
       "own ECL / backtest / overlay / staging / MILP / bootstrap code. Nothing is read from reports/ or the pipeline's interim tables.\n\n"
       f"Population check: 2015 portfolio {len(port):,} loans; train window {len(train):,} loans, {A.n_def:,} defaults in the hazard panel; "
       f"refit 2012-09 start: max MOB {R12.max_mob}; PD cutoff {pd_cut:.4f}.\n\n" + T.to_markdown(index=False) + "\n")
(ROOT / "reports" / "quality" / "rederive_ecl_policy.md").write_text(md_)
print(md_)
sys.exit(1 if n_fail else 0)
