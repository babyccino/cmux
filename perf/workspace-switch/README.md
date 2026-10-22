# Workspace switch latency probes

Measurement tools from the workspace switch latency work. This branch is not for merging: the
`CMUX_TMP_*` toggles in `Sources/` exist only to A/B test switch behavior.

## Build

```bash
CMUX_TUI_CLIENT_MAX_FALLBACK=1 CMUX_DEV_BACKEND_MODE=local \
  ./scripts/reload.sh --tag ws-lag-rel --release --no-global-cli-links
```

The tools assume the `ws-lag-rel` tag and 7 workspaces, with next/previous workspace bound to
cmd+shift+] and cmd+shift+[.

## Run

```bash
perf/workspace-switch/tools/run.sh <label> --env CMUX_TMP_KEEP_ATTACHED=1 ...
MINSEQ=6 python3 perf/workspace-switch/tools/analyze.py perf/workspace-switch/runs/<label>
```

`run.sh` launches the tagged app with `CMUX_TMP_PHOTON=1` (streams the app's own window through
ScreenCaptureKit and logs each pixel change) and `CMUX_TMP_AUTODRIVE=count,gapMs,delaySec`
(posts the switch shortcut as key events). `paint.sh` gives every terminal a distinct background
so a terminal swap shows up as a large pixel change. `analyze.py` reports key to first pixel
change, key to terminal swap (over 20% of the main area changed) and key to settled.
`MINSEQ=6` drops the first lap, when every workspace is visited for the first time.

`tools/Q.env` holds the best configuration. `ladder*.sh` run a set of configurations back to
back. `prof.sh` runs one configuration with an xctrace Time Profiler attached; `tree.py`,
`callers.py`, `callees.py` and `appframes.py` read the exported time-profile XML.

`results/` keeps the summaries of the runs, labelled by configuration.

## Results (warm switches, median ms)

| Configuration | First pixel | Terminal swap | Settled |
|---|---|---|---|
| Stock | 95 | 117 | 153 |
| P: keep attached, pre-select swap, sidebar preview, equatable pages | 17 | 20 | 69 |
| Q: P with a per-workspace AppKit page host instead of equatable pages | 19-22 | 32-35 | 36-37 |
