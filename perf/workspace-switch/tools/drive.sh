#!/bin/bash
# usage: drive.sh <count> <gap>
cd ~/Code/cmux
for i in $(seq 1 $1); do
  if [ $((i % 4)) -lt 2 ]; then m=workspace.next; else m=workspace.previous; fi
  CMUX_QUIET=1 CMUX_TAG=ws-lag-rel scripts/cmux-debug-cli.sh rpc $m >/dev/null 2>&1
  perl -e "select(undef,undef,undef,$2)"
done
