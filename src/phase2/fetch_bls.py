"""Fetch BLS LAUS state unemployment rates (seasonally adjusted, monthly, 2007-2018) via BLS Public Data API v1 (no key).

Series: LASST{FIPS}0000000000003 (51 = 50 states + DC). v1 limits: 25 series and 10 years per request.
Raw JSON responses -> data/raw/macro/ ; tidy table -> data/interim/state_unemployment.parquet (state, month, ur)
Usage: .venv/bin/python -I src/phase2/fetch_bls.py
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "macro"
RAW.mkdir(parents=True, exist_ok=True)
FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11",
        "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
        "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30",
        "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
        "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
        "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56"}
sid = {f"LASST{f}0000000000003": st for st, f in FIPS.items()}
ids = list(sid)
batches = [ids[i:i + 25] for i in range(0, len(ids), 25)]
rows = []
for bi, b in enumerate(batches):
    for y0, y1 in (("2007", "2016"), ("2017", "2018")):
        out = RAW / f"bls_laus_b{bi}_{y0}_{y1}.json"
        if not out.exists():
            req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/",
                                         data=json.dumps({"seriesid": b, "startyear": y0, "endyear": y1}).encode(),
                                         headers={"Content-Type": "application/json", "User-Agent": "research-script"})
            out.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            time.sleep(1)
        js = json.loads(out.read_text())
        assert js["status"] == "REQUEST_SUCCEEDED", js.get("message")
        for s in js["Results"]["series"]:
            for d in s["data"]:
                if d["period"].startswith("M") and d["period"] != "M13":
                    rows.append({"state": sid[s["seriesID"]], "month": f"{d['year']}-{d['period'][1:]}-01",
                                 "ur": float(d["value"])})
df = pd.DataFrame(rows).drop_duplicates(["state", "month"])
df["month"] = pd.to_datetime(df["month"])
df = df.sort_values(["state", "month"]).reset_index(drop=True)
df.to_parquet(ROOT / "data" / "interim" / "state_unemployment.parquet")
print(df.groupby("state").size().describe())
print(df.month.min(), df.month.max(), df.state.nunique(), "states;", len(df), "rows")
