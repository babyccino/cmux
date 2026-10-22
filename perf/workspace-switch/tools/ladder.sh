#!/bin/bash
T=$SP/tools
B="--env CMUX_TMP_MAX_MOUNTED=6 --env CMUX_TMP_NO_KEYLOOP=1 --env CMUX_TMP_KEEP_ATTACHED=1"
F="--env CMUX_TMP_SYNC_REVEAL=1 --env CMUX_TMP_FORCE_REVEAL=1"
run() { echo "=== $1"; "$T/run.sh" "$@" | grep -v "^photon started"; }
run A_stock
run B_mounted $B
run C_force $B $F
run D_flush $B $F --env CMUX_TMP_FLUSH=1
run E_notheme $B $F --env CMUX_TMP_FLUSH=1 --env CMUX_TMP_NO_THEME_REVEAL=1
run F_norefresh $B $F --env CMUX_TMP_FLUSH=1 --env CMUX_TMP_NO_THEME_REVEAL=1 --env CMUX_TMP_NO_REVEAL_REFRESH=1
run G_nointeractive $B $F --env CMUX_TMP_FLUSH=1 --env CMUX_TMP_NO_THEME_REVEAL=1 --env CMUX_TMP_NO_REVEAL_REFRESH=1 --env CMUX_TMP_NO_INTERACTIVE_SYNC=1
run H_cascadeonly $B --env CMUX_TMP_NO_THEME_REVEAL=1 --env CMUX_TMP_NO_REVEAL_REFRESH=1 --env CMUX_TMP_NO_INTERACTIVE_SYNC=1
