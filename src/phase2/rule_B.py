"""B — Plan B rule test (a)/(b)/(c), exactly as notes/03_prereg_phase2.md §B. Report written either way.

Outputs: reports/phase2/macro_B.md, reports/phase2/macro_B.json, data/interim/p2/model_B_*.pkl
Usage: nice -n 19 .venv/bin/python -I src/phase2/rule_B.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import INTERIM, SEED  # noqa: E402
from hazard import NAMES, Scaler, cif, design, expand, fit_mnl, hazards  # noqa: E402

ART2, REP2 = INTERIM / "p2", ROOT / "reports" / "phase2"
B_BOOT = 200
REGION = {**{s: "Northeast" for s in "CT ME MA NH RI VT NJ NY PA".split()},
          **{s: "Midwest" for s in "IL IN MI OH WI IA KS MN MO NE ND SD".split()},
          **{s: "South" for s in "DE FL GA MD NC SC VA DC WV AL KY MS TN AR LA OK TX".split()},
          **{s: "West" for s in "AZ CO ID MT NV NM UT WY AK CA HI OR WA".split()}}

ur = pd.read_parquet(INTERIM / "state_unemployment.parquet")
states = sorted(ur.state.unique())
sidx = {s: i for i, s in enumerate(states)}
U = ur.pivot(index="state", columns="month", values="ur").loc[states].to_numpy()   # (51, 144) from 2007-01
M0 = pd.Timestamp("2007-01-01")


def month_index(dt):
    return (dt.dt.year - M0.year) * 12 + (dt.dt.month - M0.month)


def macro_rows(loans, li, t):
    """realised (u, d12u) for loan rows li at MOB t."""
    s = loans.addr_state.map(sidx).to_numpy()[li]
    m = month_index(loans.issue_dt).to_numpy()[li] + t - 1
    return np.column_stack([U[s, m], U[s, m] - U[s, m - 12]])


def macro_path(loans, scenario, H=36):
    s = loans.addr_state.map(sidx).to_numpy()
    m0 = month_index(loans.issue_dt).to_numpy()
    tt = np.arange(H)
    if scenario == "realised":
        m = m0[:, None] + tt[None, :]
        u, d = U[s[:, None], m], U[s[:, None], m] - U[s[:, None], m - 12]
    elif scenario == "baseline":
        u = np.repeat(U[s, m0][:, None], H, axis=1)
        d = np.zeros_like(u)
    elif scenario == "adverse":
        a0 = (2008 - 2007) * 12  # 2008-01
        path = U[:, a0 + tt] - U[:, [a0]]                     # (51, H)
        d12 = U[:, a0 + tt] - U[:, a0 + tt - 12]
        u = U[s, m0][:, None] + path[s]
        d = d12[s]
    return np.stack([u, d], axis=2)


def fit_set(loans, label):
    sc = Scaler(loans)
    li, t, y, w = expand(loans, nonevent_frac=0.25, seed=SEED)
    L = sc.loan_cols(loans)[li]
    mac = macro_rows(loans, li, t)
    X0 = design(t, L)
    X1 = design(t, L, mac)
    B0, c0, _ = fit_mnl(X0, y, w)
    B1, c1, _ = fit_mnl(X1, y, w)
    # bootstrap (E3 correctness fix, notes/08_prereg_extensions.md): every replicate redraws the 25% non-event subsample
    # from the FULL loan-month panel, then resamples issue quarters with replacement.
    liF, tF, yF, _ = expand(loans)
    X1F = design(tF, sc.loan_cols(loans)[liF], macro_rows(loans, liF, tF)).astype(np.float32)
    uq, qiF = np.unique(loans.issue_q.to_numpy()[liF], return_inverse=True)
    wS = np.where(yF > 0, 1.0, 4.0)
    rng = np.random.default_rng(SEED + 7)
    th = []
    p = X1.shape[1]
    for b in range(B_BOOT):
        cnt = np.bincount(rng.integers(0, len(uq), len(uq)), minlength=len(uq))
        sub = (yF > 0) | (np.random.default_rng(SEED + 1000 + b).random(len(yF)) < 0.25)
        wb = wS * cnt[qiF]
        keep = sub & (wb > 0)
        Bb, _, _ = fit_mnl(X1F[keep].astype(np.float64), yF[keep], wb[keep], B0=B1, iters=6, tol=1e-6)
        th.append(Bb[p - 2, 0] + Bb[p - 1, 0])
        if (b + 1) % 50 == 0:
            print(f"  [{label}] bootstrap {b+1}/{B_BOOT}", flush=True)
    th = np.array(th)
    se = np.sqrt(np.diag(c1))
    res = {"label": label, "n_loans": len(loans), "n_rows": len(t), "n_quarters": len(uq),
           "gamma_u_default": B1[p - 2, 0], "gamma_u_default_se": se[p - 2],
           "gamma_d12_default": B1[p - 1, 0], "gamma_d12_default_se": se[p - 1],
           "gamma_u_prepay": B1[p - 2, 1], "gamma_d12_prepay": B1[p - 1, 1],
           "theta": B1[p - 2, 0] + B1[p - 1, 0], "theta_lo": float(np.percentile(th, 2.5)),
           "theta_hi": float(np.percentile(th, 97.5)), "theta_boot_sd": float(th.std())}
    return res, sc, B0, B1


loans = pd.read_parquet(INTERIM / "p2_loans.parquet")
fitL = loans[(loans.issue_dt >= "2009-01-01") & (loans.issue_dt <= "2014-12-01")].reset_index(drop=True)
oot = loans[loans.yr == 2015].reset_index(drop=True)

print("fitting primary (2009-2014) ...", flush=True)
prim, sc, B0, B1 = fit_set(fitL, "primary 2009-2014")
with open(ART2 / "model_B_primary.pkl", "wb") as fh:
    pickle.dump({"scaler": sc, "B_score_only": B0, "B_macro": B1, "names": NAMES + ["u", "d12u"]}, fh)
a_pass = bool(prim["theta"] > 0 and prim["theta_lo"] > 0)

# (b) OOT 2015, realised path
L = sc.loan_cols(oot)
hd0, hp0 = hazards(L, B0)
hd1, hp1 = hazards(L, B1, macro_path(oot, "realised"))
pd0, pd1 = cif(hd0, hp0)[2][:, 35], cif(hd1, hp1)[2][:, 35]
o = oot.assign(pd0=pd0, pd1=pd1, region=oot.addr_state.map(REGION))
lab = o[o.bad.notna()]
cells = lab.groupby(["issue_q", "region"]).agg(n=("bad", "size"), obs=("bad", "mean"), pred_score_only=("pd0", "mean"),
                                                pred_macro=("pd1", "mean")).reset_index()
err0 = (cells.pred_score_only - cells.obs).abs().mean()
err1 = (cells.pred_macro - cells.obs).abs().mean()


def ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


ll0, ll1 = ll(lab.pd0.to_numpy(), lab.bad.to_numpy()), ll(lab.pd1.to_numpy(), lab.bad.to_numpy())
b_pass = bool(err1 <= 0.90 * err0 and ll1 <= ll0)

# (c) stress multiplier on 2015 portfolio
hb, hpb = hazards(L, B1, macro_path(oot, "baseline"))
ha, hpa = hazards(L, B1, macro_path(oot, "adverse"))
pdb, pda = cif(hb, hpb)[2][:, 35], cif(ha, hpa)[2][:, 35]
mult = float(pda.sum() / pdb.sum())
c_pass = bool(1.1 <= mult <= 3.0)

print("fitting sensitivity (2012-09..2014-12) ...", flush=True)
sens, *_ = fit_set(loans[(loans.issue_dt >= "2012-09-01") & (loans.issue_dt <= "2014-12-01")].reset_index(drop=True),
                   "sensitivity 2012-09..2014")

decision = "B PASSES -> A + B" if (a_pass and b_pass and c_pass) else "B FAILS -> Plan B: A + C"
out = {"primary": prim, "sensitivity": sens,
       "rule_a": {"theta": prim["theta"], "ci": [prim["theta_lo"], prim["theta_hi"]], "pass": a_pass},
       "rule_b": {"err_score_only": err0, "err_macro": err1, "rel_change": err1 / err0 - 1, "logloss_score_only": ll0,
                  "logloss_macro": ll1, "pass": b_pass},
       "rule_c": {"multiplier": mult, "mean_pd_baseline": float(pdb.mean()), "mean_pd_adverse": float(pda.mean()),
                  "pass": c_pass},
       "decision": decision}
(REP2 / "macro_B.json").write_text(json.dumps(out, indent=1, default=float))
c = cells.copy()
for k in ("obs", "pred_score_only", "pred_macro"):
    c[k] = (100 * c[k]).round(2)
ref_u = ur[ur.month.isin([pd.Timestamp("2008-01-01"), pd.Timestamp("2009-10-01"), pd.Timestamp("2010-12-01"),
                          pd.Timestamp("2015-01-01"), pd.Timestamp("2016-12-01"), pd.Timestamp("2018-12-01")])]
uref = ref_u.groupby("month").ur.agg(["min", "median", "max"]).reset_index()
uref["month"] = uref.month.dt.strftime("%Y-%m")


def fmt(r):
    return (f"| {r['label']} | {r['n_loans']:,} | {r['n_quarters']} | {r['gamma_u_default']:.4f} | "
            f"{r['gamma_d12_default']:.4f} | **{r['theta']:.4f} [{r['theta_lo']:.4f}, {r['theta_hi']:.4f}]** | "
            f"{r['gamma_u_prepay']:.4f} | {r['gamma_d12_prepay']:.4f} |")


md = f"""# B — macro (Plan B rule test, generated by src/phase2/rule_B.py)

**Decision: {decision}**

| rule | statistic | threshold | result |
|---|---|---|---|
| (a) sign + significance | θ = γ_u + γ_Δ12u (default) = {prim['theta']:.4f}, 95% block-bootstrap CI [{prim['theta_lo']:.4f}, {prim['theta_hi']:.4f}] | θ > 0 and CI > 0 | {'PASS' if a_pass else 'FAIL'} |
| (b) OOT value | cell error macro {100*err1:.3f} pp vs score-only {100*err0:.3f} pp ({100*(err1/err0-1):+.1f}%); log loss {ll1:.5f} vs {ll0:.5f} | ≤ −10% and log loss not worse | {'PASS' if b_pass else 'FAIL'} |
| (c) stress size | adverse/baseline lifetime PD multiplier = {mult:.3f} (mean PD {100*pdb.mean():.2f}% → {100*pda.mean():.2f}%) | 1.1 – 3.0 | {'PASS' if c_pass else 'FAIL'} |

## Macro coefficients (log-odds per 1 pp; bracket = block-bootstrap CI by issue quarter, B={B_BOOT})

Hessian standard errors are not shown: the fit uses a weighted non-event subsample and ignores clustering, so they are not valid for
inference (independent review MA-3). The bootstrap keeps the 25% subsample fixed (as pre-registered); θ also moved from −0.0185 to −0.0379
when the frozen M2 score was re-fit in the deterministic re-run (same rule outcome: FAIL). Since E3 (notes/08_prereg_extensions.md) every
bootstrap replicate redraws the 25% non-event subsample from the full panel before resampling issue quarters.

| fit | loans | issue quarters | γ_u default | γ_Δ12u default | θ default | γ_u prepay | γ_Δ12u prepay |
|---|---:|---:|---|---|---|---|---|
{fmt(prim)}
{fmt(sens)}

(sensitivity row = pre-registered robustness, not part of the rule)

## Rule (b) cells — OOT 2015, issue quarter × Census region (%)

{c.to_markdown(index=False)}

## Context: state unemployment (BLS LAUS, SA), min / median / max across 51 states

{uref.to_markdown(index=False)}
"""
(REP2 / "macro_B.md").write_text(md)
print(md)
