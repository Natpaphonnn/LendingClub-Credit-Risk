"""Phase 0: convert the raw Kaggle CSV.gz files to parquet (all columns as VARCHAR) in data/interim/.

All-VARCHAR on purpose: the accepted file has footer/summary rows and mixed types; we cast with
TRY_CAST in the audit queries instead of trusting type inference. DuckDB streams the gzip, so RAM
stays bounded (memory_limit below).

Usage:  nice -n 19 .venv/bin/python -I src/audit/convert_to_parquet.py <raw_dir> <interim_dir> [stem ...]
"""
import sys
import time
from pathlib import Path

import duckdb

raw, interim = Path(sys.argv[1]), Path(sys.argv[2])
interim.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4; SET preserve_insertion_order=true;")  # keep CSV row order (reproducibility)
con.execute(f"SET temp_directory='{interim / '_duckdb_tmp'}'")

stems = sys.argv[3:] or ["accepted_2007_to_2018Q4", "rejected_2007_to_2018Q4"]
for stem in stems:
    src, dst = raw / f"{stem}.csv.gz", interim / f"{stem}.parquet"
    if dst.exists():
        print(f"skip {dst} (exists)")
        continue
    t = time.time()
    con.execute(
        f"""COPY (SELECT * FROM read_csv('{src}', all_varchar=true, header=true,
                                          quote='"', escape='"', strict_mode=false,
                                          null_padding=true, max_line_size=10000000))
            TO '{dst}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 200000)"""
    )
    n = con.execute(f"SELECT count(*) FROM '{dst}'").fetchone()[0]
    print(f"{stem}: {n:,} rows -> {dst} ({dst.stat().st_size/1e6:.0f} MB) in {time.time()-t:.0f}s")
