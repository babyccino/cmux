#!/bin/bash
T=$SP/tools
B="--env CMUX_TMP_MAX_MOUNTED=6 --env CMUX_TMP_NO_KEYLOOP=1 --env CMUX_TMP_KEEP_ATTACHED=1"
C="--env CMUX_TMP_NO_THEME_REVEAL=1 --env CMUX_TMP_NO_REVEAL_REFRESH=1 --env CMUX_TMP_NO_INTERACTIVE_SYNC=1"
F="--env CMUX_TMP_SYNC_REVEAL=1 --env CMUX_TMP_FORCE_REVEAL=1"
run() { echo "=== $1"; "$T/run.sh" "$@" | grep -E "swap|settled|sidebar first|frames|flushed|onChange"; }
run A2_stock
run I_nearzero $B --env CMUX_TMP_NEAR_ZERO_OPACITY=1
run J_equatable $B --env CMUX_TMP_EQUATABLE=1
run K_combo $B $C --env CMUX_TMP_NEAR_ZERO_OPACITY=1 --env CMUX_TMP_EQUATABLE=1
run L_combo_force $B $C $F --env CMUX_TMP_NEAR_ZERO_OPACITY=1 --env CMUX_TMP_EQUATABLE=1
run M_appkitlazy $B $C --env CMUX_TMP_APPKIT_HOST=1 --env CMUX_TMP_APPKIT_HOST_LAZY=1
