#!/bin/bash
# usage: prof.sh <label> [open args...]  driven run with Time Profiler attached
SP="${SP:-$(cd "$(dirname "$0")/.." && pwd)}"
label=$1; shift
rm -rf "$SP/$label.trace"
AUTODRIVE=${AUTODRIVE:-6,700,16} "$SP/tools/run.sh" "$label" "$@" > "$SP/runs/$label.out" 2>&1 &
runner=$!
sleep 9
PID=$(pgrep -f "cmux-ws-lag-rel/Build/Products/Release/cmux DEV ws-lag-rel.app/Contents/MacOS/" | head -1)
echo "pid=$PID"
xcrun xctrace record --instrument "Time Profiler" --attach "$PID" --time-limit 30s --output "$SP/$label.trace" >/dev/null 2>&1
wait $runner
cat "$SP/runs/$label.out" | grep -v "photon started"
