#!/bin/bash
T=$SP/tools
B="--env CMUX_TMP_MAX_MOUNTED=8 --env CMUX_TMP_NO_KEYLOOP=1 --env CMUX_TMP_KEEP_ATTACHED=1"
C="--env CMUX_TMP_NO_THEME_REVEAL=1 --env CMUX_TMP_NO_REVEAL_REFRESH=1 --env CMUX_TMP_NO_INTERACTIVE_SYNC=1 --env CMUX_TMP_NEAR_ZERO_OPACITY=1"
F="--env CMUX_TMP_SYNC_REVEAL=1 --env CMUX_TMP_FORCE_REVEAL=1 --env CMUX_TMP_SIDEBAR_PREVIEW=1 --env CMUX_TMP_FORCE_BEFORE_SELECT=1"
run() { echo "=== $1"; "$T/run.sh" "$@" | grep -E "first pixel|swap|settled|sidebar first|frames"; }
run P2_preselect $B $C $F --env CMUX_TMP_EQUATABLE=1
run Q_pages $B $C $F --env CMUX_TMP_APPKIT_HOST=1 --env CMUX_TMP_APPKIT_HOST_LAZY=1
run R_addsub $B $C $F --env CMUX_TMP_EQUATABLE=1 --env CMUX_TMP_ADDSUB_PROBE=1
