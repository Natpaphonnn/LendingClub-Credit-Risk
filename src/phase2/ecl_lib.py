"""Shared ECL helpers (notes/03_prereg_phase2.md §ECL and notes/08_prereg_extensions.md §E4–E5)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hazard import Scaler, cif, design, expand, fit_mnl, hazards  # noqa: E402
from riskutils import annuity_schedule, as_float, code_events, lgd_ead_at_default, payments_due  # noqa: E402

H = 36


def pooled_lgd(defaults: pd.DataFrame, discount_months=None):
    """EAD-weighted LGD on defaulted loans. discount_months=k discounts net recoveries by (1 + EIR)^-k (E5)."""
    lgd, ead = lgd_ead_at_default(defaults.funded_amnt, defaults.total_rec_prncp, defaults.recoveries,
                                  defaults.collection_recovery_fee)
    if discount_months is not None:
        r = defaults.int_rate.to_numpy(float) / 1200.0
        net = defaults.recoveries.to_numpy(float) - defaults.collection_recovery_fee.to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            lgd = np.where(ead > 0, np.clip(1 - net * (1 + r) ** (-discount_months) / ead, 0, 1), np.nan)
    ok = ead > 0
    return float((lgd[ok] * ead[ok]).sum() / ead[ok].sum()), lgd, ead


def schedule(port):
    r = (port.int_rate.to_numpy() / 1200.0)[:, None]
    t = np.arange(1, H + 1)[None, :]
    _, EAD = annuity_schedule(port.funded_amnt.to_numpy(), port.int_rate.to_numpy(), H)
    return r, EAD, (1 + r) ** (-t)


def ecl_from(hd, hp, EAD, DF, LGD, ead_shift=0):
    """ead_shift = k: loss at default MOB t uses EAD at MOB t−k (90-DPD definition: k = 2)."""
    s_prev, md, C = cif(hd, hp)
    E = EAD if ead_shift == 0 else EAD[:, np.maximum(np.arange(H) - ead_shift, 0)]
    loss = md * LGD * E
    return {"pd12": C[:, 11], "pdlife": C[:, -1], "ecl12": (loss * DF)[:, :12].sum(1), "ecl_life": (loss * DF).sum(1),
            "el_life_undisc": loss.sum(1), "s_prev": s_prev, "hd": hd}


def realised_loss(port):
    is_def = port.loan_status.isin(["Charged Off", "Default"]).to_numpy()
    return np.where(is_def, port.funded_amnt - port.total_rec_prncp - port.recoveries + port.collection_recovery_fee, 0.0)


def fit_hazard_asof(loans, report_date, start="2012-09-01", lag_m=6, default_shift=0):
    """Refit the A-spec hazard using only outcomes observable by report_date − lag (E5). default_shift=2 → 90-DPD events."""
    cut = pd.Timestamp(report_date).to_period("M").to_timestamp() - pd.DateOffset(months=lag_m)
    tr = loans[(loans.issue_dt >= start) & (loans.issue_dt <= pd.Timestamp(report_date))].copy()
    W = np.minimum(36, payments_due(tr.issue_dt, cut.strftime("%Y-%m-%d")))
    tr["W_R"] = W
    tr = tr[tr.W_R >= 1].reset_index(drop=True)
    dm = as_float(tr.default_mob) + default_shift
    T, ev = code_events(tr.loan_status.to_numpy(), tr.lp_mob, dm, tr.W_R)
    tr["T"], tr["event"] = T, ev
    return fit_on(tr)


def fit_on(tr):
    sc = Scaler(tr)
    li, t, y, w = expand(tr)
    B, cov, its = fit_mnl(design(t, sc.loan_cols(tr)[li]), y, w)
    return {"B": B, "scaler": sc, "n_loans": len(tr), "n_rows": len(t), "defaults": int((y == 1).sum()),
            "prepays": int((y == 2).sum()), "iters": its}


def staging_e4(port, model, LGD, report="2015-12-01"):
    """E4 staging at the reporting date (EX-POST; monthly DPD is not in the data).
    m = missed instalments by the report month (only visible for loans that ultimately charged off);
    stage 3: m >= 3 (~90 DPD) -> LGD x EAD at default; stage 2: m in {1, 2} (~30 DPD proxy) -> lifetime ECL;
    stage 1: other performing -> 12-month ECL; prepaid by the report month -> derecognised."""
    r, EAD, _ = schedule(port)
    hd, hp = hazards(model["scaler"].loan_cols(port), model["B"])
    s_prev, _, _ = cif(hd, hp)
    due = payments_due(port.issue_dt, report)
    d = as_float(port.default_mob)
    is_def = port.loan_status.isin(["Charged Off", "Default"]).to_numpy()
    m = np.where(is_def & (np.nan_to_num(d, nan=np.inf) <= due), due - np.nan_to_num(d, nan=0) + 1, 0)
    p = np.where(port.event.to_numpy() == 2, port["T"].to_numpy(), np.inf)
    st3 = m >= 3
    st2 = (m >= 1) & (m <= 2)
    gone = (m == 0) & (p <= due)
    st1 = (m == 0) & ~gone
    n = len(port)
    ecl12, ecll = np.zeros(n), np.zeros(n)
    for i in np.where(st1 | st2)[0]:
        a = int(min(due[i], H - 1))
        md_c = s_prev[i, a:] * hd[i, a:] / s_prev[i, a]
        loss = md_c * LGD * EAD[i, a:] * (1 + r[i, 0]) ** -np.arange(1, H - a + 1)
        ecl12[i], ecll[i] = loss[:12].sum(), loss.sum()
    d_idx = np.clip(np.nan_to_num(d, nan=1).astype(int) - 1, 0, H - 1)
    ead_def = EAD[np.arange(n), d_idx]                        # outstanding principal at first missed payment
    ead_perf = EAD[np.arange(n), np.minimum(due, H - 1)]
    ead_rep = np.where(st2 | st3, ead_def, ead_perf)
    rows = [("Stage 1 (performing, no missed instalment visible; 12-month ECL)", st1, ecl12),
            ("Stage 2 (1–2 missed instalments ≈ ≥ 30 DPD, ex-post proxy; lifetime ECL)", st2, ecll),
            ("Stage 3 (≥ 3 missed instalments ≈ 90 DPD; LGD × EAD at default)", st3, LGD * ead_def),
            ("derecognised (prepaid by the report month)", gone, np.zeros(n))]
    t = pd.DataFrame([{"stage": nm, "loans": int(msk.sum()), "gross EAD $m": float(ead_rep[msk].sum() / 1e6) if "derecog" not in nm else 0.0,
                       "allowance $m": float(al[msk].sum() / 1e6)} for nm, msk, al in rows])
    t["coverage %"] = (100 * t["allowance $m"] / t["gross EAD $m"].replace(0, np.nan)).round(2)
    return t
