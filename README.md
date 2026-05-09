# Merged Active Video Monitor + JAMboree Lite SGS Controller

This bundle merges the two roles into one Flask app:

1. **Active video monitor** — reads the capture card, exposes `/video.mjpg`, `/snapshot.jpg`, `/screen`, and active-video status JSON.
2. **STB control** — reuses JAMboree Lite's SGS controller/store and controls the STB alias **`found1`** through the same JAMboree Lite path.

The default `base.txt` is pre-seeded for:

```json
{
  "found1": {
    "protocol": "SGS",
    "role": "hopper",
    "remote": "sgs",
    "ip": "192.168.0.145",
    "stb": "R1886469480-82",
    "receiver": "XAF7486e214f5de",
    "cid": 1004
  }
}
```

## Run on Windows

Copy this folder to the server, for example:

```text
C:\Users\Systems1\Documents\Merged_STB_Monitor
```

Then double-click:

```text
run_merged_app.bat
```

Open:

```text
http://127.0.0.1:8502/monitor
```

From another machine on the LAN:

```text
http://192.168.0.172:8502/monitor
```

## If you want it to replace the existing JAMboree Lite port

Edit `config.json`:

```json
"server_port": 5003
```

Then stop the old JAMboree Lite process before launching this merged app. The merged app includes the JAMboree Lite routes, so `/auto/...`, `/get-stb-list`, and `/sgs/...` remain available.

You can also override the port temporarily:

```bat
set MERGED_SERVER_PORT=5003
run_merged_app.bat
```

## Main Routes

| Route | Purpose |
|---|---|
| `/monitor` | Web UI with live video and remote buttons |
| `/video.mjpg` | MJPEG stream from active capture input |
| `/snapshot.jpg` | Current frame as JPEG |
| `/api/status` | Combined STB + video monitor status |
| `/api/active-video` | Active video status only |
| `/send_key` | Compatibility POST endpoint, e.g. `{ "key": "KEY_UP" }` |
| `/key/<key>` | Browser-friendly key route, e.g. `/key/guide` |
| `/api/tune?channel=206` | Sends digits + select for direct channel tuning |
| `/screen` | NavigationMapBuilder-style state endpoint |
| `/key` | NavigationMapBuilder-style POST endpoint |
| `/screenshot` | NavigationMapBuilder-style screenshot endpoint |
| `/auto/sgs/found1/<button>/<delay>` | Original JAMboree Lite-style route |

## Capture device

The default capture device is index `1`, matching the prior `00-1 Pro Capture` work. To rescan:

```bat
.venv\Scripts\activate.bat
python scan_capture_devices.py
```

Then update `config.json`:

```json
"capture_device": 1
```

Or override temporarily:

```bat
set MERGED_CAPTURE_DEVICE=0
run_merged_app.bat
```

## Quick tests after launch

```bat
.venv\Scripts\activate.bat
python test_endpoints.py
```

Manual key test:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8502/send_key" -Method POST -ContentType "application/json" -Body '{"key":"KEY_UP"}'
```

Direct tune test:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8502/api/tune?channel=206" -Method GET
```

## Notes

- The merged app does **not** require the old JAMboree Lite server to be running separately.
- The legacy NavigationMapBuilder source is included in `legacy_NavigationMapBuilder/` for reference and regression scripts.
- Active video detection uses frame brightness + variance, with motion shown as an additional score. It does not attempt OCR by default.

## Autonomous crawl / learned navigation map

This version includes an autonomous crawler at:

```text
http://127.0.0.1:8502/crawl
```

The crawler learns the STB UI as a graph:

```text
screen_state --remote_button--> next_screen_state
```

It uses the capture card as feedback and JAMboree Lite SGS as the remote-control path for `found1`.

### What the crawler does

1. Captures the current video frame.
2. Builds a screen fingerprint using:
   - perceptual hash / difference hash / average hash
   - HSV color histogram
   - brightness, variance, entropy, and edge-density features
   - optional OCR text if `pytesseract` and the Tesseract binary are installed
3. Matches the fingerprint against previously learned states.
4. Sends one remote key through SGS.
5. Waits for the UI to settle.
6. Captures the next screen.
7. Records the transition into `crawler_data/nav_graph.json`.
8. Attempts to unwind with `back`, or recovers by using `home` and replaying known graph paths.

### Crawler routes

| Route | Purpose |
|---|---|
| `/crawl` | Browser UI for starting/stopping exploration and viewing graph status |
| `/api/crawl/start` | POST JSON config overrides and start crawler |
| `/api/crawl/stop` | Stop current crawler run |
| `/api/crawl/status` | Runtime status, recent events, state/edge counts |
| `/api/crawl/graph` | Full learned graph JSON |
| `/api/crawl/classify` | Fingerprint current screen and add/match it as a state |
| `/api/crawl/reset` | Clear learned graph; crawler must be stopped |
| `/api/crawl/export` | Download `nav_graph.json` |

### Default safety behavior

The default exploration keys are:

```json
["up", "down", "left", "right", "guide", "back", "home", "info", "select"]
```

`select` is guarded. If OCR sees risky words such as purchase, rent, subscribe, delete, factory, reset, payment, PIN, or parental, the crawler blocks SELECT unless `allow_select_on_dangerous_text` is enabled.

If OCR is not available, the crawler still works using visual matching only, but the risky-screen guard becomes less informed. For first runs, keep a short step limit such as 25-50 and watch the `/crawl` page.

### Example API start

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8502/api/crawl/start" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"max_steps":50,"max_states":25,"enabled_keys":["up","down","left","right","guide","back","home","info"]}'
```

Add `select` after the map is stable:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8502/api/crawl/start" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"max_steps":100,"enabled_keys":["up","down","left","right","guide","back","home","info","select"]}'
```

### Learned artifacts

The crawler writes:

```text
crawler_data/
  nav_graph.json
  states/
    screen_*.jpg
```

The graph can be consumed later by a navigation planner that says, for example, “from Home, press GUIDE then DOWN twice then SELECT.”

### Optional OCR setup

The Python package is optional, but OCR only works when both are present:

```bat
.venv\Scripts\activate.bat
pip install pytesseract
```

Then install the Windows Tesseract binary and ensure `tesseract.exe` is on PATH. Without it, the app continues using visual fingerprints.

## v3 Autonomous Crawl Enhancements

The crawler UI at `/crawl` now supports:

- **Starting button / sequence**: enter `guide`, `home,guide`, `dvr`, etc. The crawler presses this after HOME and treats the resulting screen as the crawl root.
- **Rewarded self-exploration**: when enabled, actions receive reward for discovering new screens, new OCR tokens, menus, settings, and feature-like screens. Future action ordering is biased toward buttons that historically discover useful states.
- **Adaptive timing**: the crawler polls the capture feed after each remote command and learns per-button response timing. Slow actions get longer settle windows; quick actions tighten up automatically.
- **Direct channel learning**: enable channel learning and provide a channel list such as `200,205,206,207,208,209,210`. The crawler enters digits with a short `channel_digit_gap_s`, waits for tuning, screenshots the result, and stores channel number/name/symbol guesses in `crawler_data/crawler_brain.json`.

New API endpoints:

```text
GET  /api/crawl/brain
GET  /api/crawl/channels
```

Learning files:

```text
crawler_data/nav_graph.json       # states and edges
crawler_data/crawler_brain.json   # action rewards, timing model, learned channels
crawler_data/states/*.jpg         # representative screenshots
```
