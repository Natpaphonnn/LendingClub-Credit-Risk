#!/usr/bin/env bash
# Full pipeline from data/raw (Phase 0-2 + overlay + article figures). Usage: bash scripts/run_all.sh [logfile]
set -euo pipefail
cd "$(dirname "$0")/.."
PY="nice -n 19 .venv/bin/python -I"
LOG="${1:-reports/quality/runtime.log}"
: > "$LOG"
step() { local s=$SECONDS; echo ">> $*" | tee -a "$LOG"; $PY "$@" > /dev/null 2>>"$LOG.stderr" || { echo "FAILED: $*" | tee -a "$LOG"; exit 1; }; echo "   $((SECONDS-s)) s" | tee -a "$LOG"; }
T0=$SECONDS
step src/audit/convert_to_parquet.py data/raw data/interim
step src/audit/run_audit.py data/interim data/raw/dictionary/LCDataDictionary.xlsx reports/audit
step src/audit/make_figures.py data/interim reports/figures
for s in build_dataset train_scorecard train_lgbm evaluate monitoring vintage explore_early_signal; do step src/phase1/$s.py; done
for s in fetch_bls build_loans fit_A rule_B ecl ecl_benchmark policy_C mob6_test overlay; do step src/phase2/$s.py; done
for s in mob6_60m_test asof_model; do step src/phase4/$s.py; done
step src/report/article_figures.py
step src/quality/grid_sensitivity.py
step src/quality/leakage_split_proof.py
echo "TOTAL $((SECONDS-T0)) s" | tee -a "$LOG"
