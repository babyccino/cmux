#!/bin/bash
T=$SP/tools
Q=$(cat $T/Q.env)
run() { echo "=== $1"; "$T/run.sh" "$@" >/dev/null; MINSEQ=6 python3 $T/analyze.py $T/../runs/$1 | grep -E "first pixel|swap|settled|eventAge"; }
run S_alpha $Q --env CMUX_TMP_PAGE_ALPHA=1
run T_alpha_batch $Q --env CMUX_TMP_PAGE_ALPHA=1 --env CMUX_TMP_BATCH_COMMIT=1
run U_all $Q --env CMUX_TMP_PAGE_ALPHA=1 --env CMUX_TMP_BATCH_COMMIT=1 --env CMUX_TMP_NO_SELECTION_OWC=1
AUTODRIVE=6,60,12 run U_burst $Q --env CMUX_TMP_PAGE_ALPHA=1 --env CMUX_TMP_BATCH_COMMIT=1 --env CMUX_TMP_NO_SELECTION_OWC=1
AUTODRIVE=6,60,12 run Q_burst2 $Q
