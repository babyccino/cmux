#!/bin/bash
# usage: run.sh <label> [--env K=V ...]   runs one autodrive session in the tagged app
set -u
SP="${SP:-$(cd "$(dirname "$0")/.." && pwd)}"
APP="$HOME/Library/Developer/Xcode/DerivedData/cmux-ws-lag-rel/Build/Products/Release/cmux DEV ws-lag-rel.app"
BG=/tmp/cmux-debug-ws-lag-rel-bg.log
PH=/tmp/cmux-tmp-photon.log
label=$1; shift
mkdir -p "$SP/runs"
pids() { pgrep -f "cmux-ws-lag-rel/Build/Products/Release/cmux DEV ws-lag-rel.app/Contents/MacOS/"; }
for p in $(pids); do kill "$p"; done
for i in $(seq 1 50); do [ -z "$(pids)" ] && break; sleep 0.2; done
for p in $(pids); do kill -9 "$p"; done
rm -f "$PH"
touch "$BG"; mark=$(wc -l < "$BG")
open -n --env CMUX_TMP_PHOTON=1 --env "CMUX_TMP_AUTODRIVE=${AUTODRIVE:-6,700,12}" "$@" --stdout "$BG" --stderr "$BG" "$APP"
for i in $(seq 1 40); do (cd ~/Code/cmux && CMUX_TAG=ws-lag-rel scripts/cmux-debug-cli.sh list-workspaces >/dev/null 2>&1) && break; sleep 0.25; done
"$SP/tools/paint.sh"
osascript -e 'tell application id "com.cmuxterm.app.debug.ws.lag.rel" to activate' >/dev/null 2>&1
for i in $(seq 1 600); do grep -q "autodrive done\|autodrive fail" "$PH" 2>/dev/null && break; sleep 0.5; done
sleep 1.5
for p in $(pids); do kill "$p"; done
for i in $(seq 1 50); do [ -z "$(pids)" ] && break; sleep 0.2; done
for p in $(pids); do kill -9 "$p"; done
tail -n +"$((mark+1))" "$BG" > "$SP/runs/$label.bg.log"
cp "$PH" "$SP/runs/$label.photon.log" 2>/dev/null
python3 "$SP/tools/analyze.py" "$SP/runs/$label" | tee "$SP/runs/$label.summary"
