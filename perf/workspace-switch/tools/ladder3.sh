#!/bin/bash
T=$SP/tools
B="--env CMUX_TMP_MAX_MOUNTED=6 --env CMUX_TMP_NO_KEYLOOP=1 --env CMUX_TMP_KEEP_ATTACHED=1"
C="--env CMUX_TMP_NO_THEME_REVEAL=1 --env CMUX_TMP_NO_REVEAL_REFRESH=1 --env CMUX_TMP_NO_INTERACTIVE_SYNC=1 --env CMUX_TMP_NEAR_ZERO_OPACITY=1 --env CMUX_TMP_EQUATABLE=1"
F="--env CMUX_TMP_SYNC_REVEAL=1 --env CMUX_TMP_FORCE_REVEAL=1"
run() { echo "=== $1"; "$T/run.sh" "$@" | grep -E "first pixel|swap|settled|sidebar first|frames|flushed|onChange"; }
run L2_combo_force $B $C $F
run N_sidebar $B $C $F --env CMUX_TMP_SIDEBAR_PREVIEW=1
run O_preselect $B $C $F --env CMUX_TMP_SIDEBAR_PREVIEW=1 --env CMUX_TMP_FORCE_BEFORE_SELECT=1
