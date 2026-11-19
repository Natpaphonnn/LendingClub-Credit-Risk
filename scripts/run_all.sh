#!/usr/bin/env bash
# Full pipeline from data/raw (Phase 0-2 + overlay + article figures). Usage: bash scripts/run_all.sh [logfile]
set -euo pipefail
cd "$(dirname "$0")/.."
PY="nice -n 19 .venv/bin/python -I"
LOG="${1:-reports/quality/runtime.log}"
: > "$LOG"; : > "$LOG.stderr"
# raw LendingClub inputs must match the committed manifest (gate R1-5); BLS values are pinned by bls_values.sha256 inside fetch_bls.py
(cd data/raw && shasum -a 256 -c --quiet "../../raw_inputs.sha256") || { echo "FAILED: raw input checksums" | tee -a "$LOG"; exit 1; }
# rebuild everything derived from raw (gate R10-1: convert_to_parquet skips existing parquet, so start from an empty data/interim)
rm -rf data/interim
step() { local s=$SECONDS; echo ">> $*" | tee -a "$LOG"; $PY "$@" > /dev/null 2>>"$LOG.stderr" || { echo "FAILED: $*" | tee -a "$LOG"; exit 1; }; echo "   $((SECONDS-s)) s" | tee -a "$LOG"; }
T0=$SECONDS
step src/audit/convert_to_parquet.py data/raw data/interim
step src/audit/run_audit.py data/interim data/raw/dictionary/LCDataDictionary.xlsx reports/audit
step src/audit/make_figures.py data/interim reports/figures
for s in build_dataset train_scorecard train_lgbm evaluate monitoring vintage explore_early_signal; do step src/phase1/$s.py; done
for s in mob6_60m_test asof_model; do step src/phase4/$s.py; done          # before phase 2: ecl_benchmark uses the as-of score
step src/phase2/fetch_bls.py
for s in build_loans fit_A rule_B ecl ecl_benchmark policy_C mob6_test overlay; do step src/phase2/$s.py; done
step src/report/article_figures.py
step src/quality/grid_sensitivity.py
step src/quality/leakage_split_proof.py
step src/report/build_demo.py
# checks (gate R10-5): tests, strict claim re-check, number provenance — fail-fast
check() { local s=$SECONDS; echo ">> $*" | tee -a "$LOG"; nice -n 19 "$@" >> "$LOG.stderr" 2>&1 || { echo "FAILED: $*" | tee -a "$LOG"; exit 1; }; echo "   $((SECONDS-s)) s" | tee -a "$LOG"; }
check .venv/bin/python -m pytest -q -p no:cacheprovider tests
check .venv/bin/python -I src/quality/check_claims.py
check .venv/bin/python -I src/quality/check_note_numbers.py
echo "TOTAL $((SECONDS-T0)) s" | tee -a "$LOG"
