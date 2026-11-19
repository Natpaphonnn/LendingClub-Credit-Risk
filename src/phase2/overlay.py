"""ILLUSTRATIVE / IN-SAMPLE management overlay for the 2015 ECL backtest (Nat decision 2, after Phase 2).

Rule (fixed before running): for each 2015 issue quarter q and k in {6, 12}:
  A/E_k(q)  = observed cumulative default at MOB k / mean A-model CIF_default(k)
  EL_ovl(q) = EL_pred(q) × A/E_k(q)          (EL_pred = undiscounted lifetime EL at origination, as in ecl.py)
  knowable  = quarter end + k + 6 months (charge-off lag)
  gap closed = (EL_ovl − EL_pred) / (realised − EL_pred)
Not a validated method: MOB-6 was discovered on 2015 vintages and tested on 2016–17, so no unseen vintage remains.

Outputs: reports/phase2/overlay.md, reports/phase2/overlay.json
Usage: nice -n 19 .venv/bin/python -I src/phase2/overlay.py
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
from config import INTERIM  # noqa: E402
from hazard import cif, hazards  # noqa: E402
sys.path.insert(0, str(ROOT / "src" / "lib"))
from riskutils import annuity_schedule, default_by_mob  # noqa: E402

ART2, REP2 = INTERIM / "p2", ROOT / "reports" / "phase2"
H = 36
port = pd.read_parquet(INTERIM / "p2_loans.parquet")
port = port[port.yr == 2015].reset_index(drop=True)
with open(ART2 / "model_A.pkl", "rb") as fh:
    mA = pickle.load(fh)
LGD = json.loads((REP2 / "ecl.json").read_text())["LGD"]

hd, hp = hazards(mA["scaler"].loan_cols(port), mA["B"])
_, md, C = cif(hd, hp)
r = (port.int_rate.to_numpy() / 1200.0)[:, None]
P = port.funded_amnt.to_numpy()[:, None]
t = np.arange(1, H + 1)[None, :]
_, EAD = annuity_schedule(port.funded_amnt.to_numpy(), port.int_rate.to_numpy(), H)
port["el_pred"] = (md * LGD * EAD).sum(1)
port["cif6"], port["cif12"] = C[:, 5], C[:, 11]
is_def = port.loan_status.isin(["Charged Off", "Default"])
port["loss"] = np.where(is_def, port.funded_amnt - port.total_rec_prncp - port.recoveries + port.collection_recovery_fee, 0.0)
port["d6"] = default_by_mob(port.default_mob, 6)      # nullable-safe (bug fixed here in Phase 3 prep)
port["d12"] = default_by_mob(port.default_mob, 12)
port["q_end"] = port.issue_dt.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.to_timestamp()

rows = []
for q, g in port.groupby("issue_q"):
    el, real = g.el_pred.sum(), g.loss.sum()
    r_ = {"issue_q": q, "EL_pred $m": el / 1e6, "realised $m": real / 1e6, "realised/pred": real / el}
    for k in (6, 12):
        ae = g[f"d{k}"].mean() / g[f"cif{k}"].mean()
        r_[f"A/E{k}"] = ae
        r_[f"EL_ovl{k} $m"] = el * ae / 1e6
        r_[f"gap closed MOB{k}"] = (el * ae - el) / (real - el)
        r_[f"knowable MOB{k}"] = (g.q_end.iloc[0] + pd.DateOffset(months=k + 6)).strftime("%Y-%m")
    rows.append(r_)
T = pd.DataFrame(rows)
tot = {"EL_pred $m": T["EL_pred $m"].sum(), "realised $m": T["realised $m"].sum()}
for k in (6, 12):
    tot[f"EL_ovl{k} $m"] = T[f"EL_ovl{k} $m"].sum()
    tot[f"gap closed MOB{k}"] = (tot[f"EL_ovl{k} $m"] - tot["EL_pred $m"]) / (tot["realised $m"] - tot["EL_pred $m"])
tot["realised/pred"] = tot["realised $m"] / tot["EL_pred $m"]
(REP2 / "overlay.json").write_text(json.dumps({"by_quarter": T.to_dict(orient="list"), "total": tot}, indent=1, default=float))
md_ = ("# ILLUSTRATIVE / IN-SAMPLE — management overlay from early A/E (2015 ECL backtest)\n\n"
       "**Not a validated method.** MOB-6 was discovered on 2015 vintages and tested on 2016–17; no unseen vintage remains. "
       "Overlay = predicted lifetime EL × A/E of cumulative default at MOB k (A model), per issue quarter; knowable at quarter end + k + 6 months.\n\n"
       f"## Total (2015 portfolio)\n\npredicted EL ${tot['EL_pred $m']:.1f}m, realised ${tot['realised $m']:.1f}m (×{tot['realised/pred']:.3f}). "
       f"Overlay MOB-6 → ${tot['EL_ovl6 $m']:.1f}m (closes {100*tot['gap closed MOB6']:.0f}% of the gap); "
       f"overlay MOB-12 → ${tot['EL_ovl12 $m']:.1f}m (closes {100*tot['gap closed MOB12']:.0f}%).\n\n## By issue quarter\n\n"
       + T.round(3).to_markdown(index=False) + "\n")
(REP2 / "overlay.md").write_text(md_)
print(md_)
