#!/bin/bash
# Paints every terminal surface in the tagged app with a distinct background color.
cd ~/Code/cmux
n=17
for s in $(CMUX_TAG=ws-lag-rel scripts/cmux-debug-cli.sh tree --all 2>/dev/null | grep -o 'surface:[0-9]* \[terminal\]' | cut -d' ' -f1); do
  n=$((n+23))
  CMUX_TAG=ws-lag-rel scripts/cmux-debug-cli.sh send --surface "$s" "clear; printf '\\033[48;5;${n}m\\033[2J\\033[H'; for i in \$(seq 1 40); do printf '%s ' $s\$i; done; echo
" >/dev/null 2>&1
done
