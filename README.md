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

## v4 Intelligence Console

Open:

```text
http://127.0.0.1:8502/intelligence
```

The intelligence console adds:

- Visual learned menu map rendered from `crawler_data/nav_graph.json`.
- Per-button confidence and learned timing table.
- Route planning to any learned screen/state.
- One-click navigation test to a selected learned node.
- Direct channel navigation/testing with channel records in `crawler_data/crawler_brain.json`.
- Goal/settings assistant: search for a learned menu or settings screen, preview the route, then optionally execute a final key sequence.

Important safety behavior:

- The app can navigate to learned settings screens, but it does not guess irreversible setting toggles.
- For settings changes, provide an explicit final sequence such as `down,down,select,right,select` after the app has learned the target screen.
- `select` remains blocked on risky OCR text unless you enable risky SELECT.

New API endpoints:

```text
GET  /api/crawl/map
GET  /api/crawl/state/<state_id>/image
GET  /api/crawl/candidates?q=settings
POST /api/crawl/plan
POST /api/crawl/navigate
POST /api/crawl/goal
```

Example route plan:

```json
{"query":"audio settings"}
```

Example navigation test:

```json
{"target_state":"screen_abc123","dry_run":false}
```

Example channel tune:

```json
{"channel":206,"dry_run":false}
```

Example settings goal:

```json
{
  "query":"caption settings",
  "desired_value":"captions on",
  "final_sequence":["down","select"],
  "dry_run":false
}
```

## v5 Continuous Deep Explorer + Flowchart Map

Open the same console:

```text
http://127.0.0.1:8502/intelligence
```

v5 adds a continuous exploration engine so you do not have to manually restart the crawl. In the crawl setup panel, leave **Continually explore until stopped** checked. Set **Max steps** to `0` for unlimited exploration, or to a finite number if you want a bounded run.

### Continuous exploration behavior

The crawler now tracks persistent `state + action` coverage in `crawler_data/crawler_brain.json`:

```text
state_id + button -> attempts, successes, noops, failures, discoveries, avg_reward
```

It repeatedly rebuilds its frontier from learned screens that still have under-tested actions. When it exhausts the known map, it idles, keeps classifying the live screen, and resumes automatically when new/transient screens appear.

Useful knobs:

| GUI field | Meaning |
|---|---|
| Max steps | `0` means run until stopped; otherwise stop after N actions |
| Max states | Stop after this many learned screens |
| Max depth | Maximum route depth away from root |
| Attempts/action | How many times to try each button on each screen before treating it as saturated |
| Idle sweep s | Wait time before checking for passive/transient new states after a sweep |
| Max cycles | `0` means unlimited sweep cycles |

### Reward / penalty changes

v5 rewards:

- new screen/state discovery
- new OCR tokens
- new menu/settings/feature concepts
- new transition edges
- known transitions that lead to screens with unexplored buttons

v5 penalizes:

- no-op buttons
- same-screen loops
- repeat transitions with no new information
- inactive video
- blocked risky `select`

This gives the explorer a bias toward “new rooms and useful hallways,” while discouraging it from repeatedly rediscovering the same screen unless that screen is a bridge to new territory.

### Flowchart map

The map is now a flowchart-style graph:

```text
[screenshot/state] -- button + confidence + reward + attempts --> [next screenshot/state]
```

Each node includes:

- representative screenshot thumbnail
- state label / OCR hint
- state kind: screen, menu, settings, feature, or channel
- confidence
- observation count
- remaining untested actions
- incoming/outgoing transition details when clicked

Each edge includes:

- button/action label
- confidence
- average reward
- attempt count
- self-loop handling for buttons that do not move the UI
- curved parallel arrows when multiple buttons connect the same pair of screens

### New / updated API behavior

`POST /api/crawl/start` accepts these additional fields:

```json
{
  "continuous_exploration_enabled": true,
  "max_steps": 0,
  "max_states": 250,
  "max_depth": 12,
  "max_action_attempts_per_state": 2,
  "continuous_idle_s": 2.0,
  "max_cycles": 0
}
```

`GET /api/crawl/status` and `GET /api/crawl/map` now include a `coverage` object showing:

```text
total_state_actions
tried_state_actions
saturated_state_actions
remaining_state_actions
completion_pct
discoveries
remaining_by_state
```

### Synthetic verification

The bundle includes:

```text
test_continuous_flow_map.py
```

Run:

```bat
.venv\Scripts\activate.bat
python test_continuous_flow_map.py
```

Expected output:

```text
CONTINUOUS_FLOW_MAP_OK
```

## v6 — Transition Flow + Human-like Exploration Console

This build improves the intelligence console and crawler map readability.

New in v6:

- Explicit transition memory: every learned edge is represented as `before screen → button/sequence → after screen`.
- Rich transition samples now save before/after state IDs, labels, screenshots, OCR text/tokens, OCR deltas, reward details, timing, confidence, and channel/action sequence metadata.
- New `/api/crawl/transitions` endpoint for transition-card inspection.
- `/api/crawl/map` now returns schema `jamboree_visual_flow_map_v3` with `transitions[]`, `layout`, and before/after metadata on edges.
- The console flowchart now uses vertical lanes by depth rather than compressing many thumbnails into one tiny bottom row.
- Unlinked/passive discoveries are wrapped into separate readable columns.
- The UI now has three map views: Flowchart, Before/Button/After transition cards, and Frontier/remaining-actions view.
- Added curiosity randomness so the crawler mostly exploits high-reward paths but occasionally tries lower-ranked under-sampled actions to escape local loops.
- Larger state cards, larger thumbnails, labeled edge arrows, current-state highlighting, selected-node detail panel, and coverage/frontier metrics.

Recommended continuous exploration settings:

```text
Max steps: 0
Max states: 350
Max depth: 18
Attempts/action: 3
Continually explore: checked
Rewarded self-exploration: checked
Adaptive timing: checked
Risky SELECT: unchecked
Curiosity: 0.12 to 0.18
```

Open the console:

```text
http://127.0.0.1:8502/intelligence
```


## v7 continuous watchdog / active reseed update

This version fixes the crawler appearing to go idle after a short run by adding explicit stop reasons and a continuous reseed loop. When the graph frontier is exhausted, the crawler no longer simply waits or finishes. In continuous mode it actively probes human-like anchor sequences such as Back, Home, Home→Guide, Live, Guide, DVR, Settings, Info, Options, and Input, then classifies the resulting screen and continues exploration.

New status fields:
- `last_stop_reason` — explains why the worker became idle, such as `max_steps_reached`, `max_states_reached`, `frontier_exhausted_for_current_limits`, `single_pass_complete`, or `stop_requested`.
- `last_error` — shows exceptions if the crawler crashed.

New/updated controls on `/crawl` and `/intelligence`:
- `Continually explore until stopped`
- `When frontier runs dry, actively reseed from Home/Guide/Live/etc.`
- `Idle/reseed anchor sequences` using semicolon-separated sequences, for example `back; home; home,guide; live; guide; info`.
- `Max steps = 0` means unlimited.
- `Max states = 0` means unlimited.

Recommended long-run settings:
- Max steps: `0`
- Max states: `0` or a high value such as `500`
- Max depth: `18`
- Attempts/action: `3`
- Continual exploration: checked
- Active reseed: checked
- Risky SELECT: unchecked


## v8 focus-aware perception

This build adds a generalized red-focus detector derived from the earlier `aBitTesty` focus scripts.  Each crawler observation now tries to identify the active red focus parallelogram/rectangle, OCR the focused tile and nearby label/context region, and attach that perception to the state and transition samples.

Useful routes:

- `/api/crawl/focus` — classify the current screen and return focus bounding box, focus confidence, focused text, context OCR, and linked state.
- `/api/crawl/focus/overlay.jpg` — live screenshot with the detected focus outlined.
- `/api/crawl/map` — now includes `focus`, `focus_label`, and focus-aware transition deltas.

The crawler still works without Tesseract installed; in that mode it will detect the red focus position visually and skip OCR text enrichment.


## v9 semantic focus/context upgrades

This build adds a richer perception layer on top of the v8 red-focus detector. It now tries to understand the *meaning* around the red focus parallelogram, not just its location.

New capabilities:

- Detect the red focused tile/row using HSV masking and contour geometry.
- OCR multiple regions: focused box, same row, nearby context, header/title band, action bar, and left/right/up/down neighbors.
- Infer screen/menu title such as `Home`, `Guide`, `Diagnostics`, `TV Viewing Options`, `Parental Control Settings`, `Live TV`, `DVR`, or `Search`.
- Infer focused item and value, e.g. `Closed Captioning = Off` or `Parental Controls = On`.
- Detect semantic tags such as settings, parental, guide, DVR, search, channel, diagnostics, actions, and content.
- Flag risky context terms such as purchase, delete, reset, parental, passcode, lock, adult, or unpair.
- Reward new menu titles, focused items, and setting/value pairs during autonomous exploration.
- One-click enrichment endpoint to reprocess existing saved screenshots with the v9 context model.

Useful endpoints:

```text
/api/crawl/focus
/api/crawl/focus/overlay.jpg
/api/crawl/enrich_context
```

The Intelligence Console now includes an **Enrich saved graph context** button so existing `crawler_data` can become smarter without starting over.

## v10 DISH page/block title context upgrades

v10 refactors the perception logic around the actual Hopper/DISH layout observed in the collected crawler screenshots:

- `page_name` is now extracted from the top-left title lane immediately after the red DISH logo.
- `block_title` is now extracted separately from the top of the smaller grey menu/block panel when present.
- `screen_title` prefers `page_name`, then `block_title`, then legacy header OCR.
- `menu_title` preserves the grey-box/block title when available.
- `title_source` records where the title came from, such as `dish_after_logo_words`, `dish_after_logo_crop`, `grey_box_header`, or `upper_block_title_words`.
- Focus detection now avoids confusing the red DISH logo or red artwork/icons with the red focus outline.
- Home top-nav focus uses a fallback positional model for Menu/Home/Shows/Sports/Movies when OCR is noisy.
- The focus overlay now displays PAGE and BOX titles independently and outlines the detected grey menu block.

Useful fields in `/api/crawl/focus`, `/api/crawl/map`, and enriched graph nodes:

```json
{
  "page_name": "Parental Control Settings",
  "block_title": "TV Viewing Options",
  "screen_title": "Parental Control Settings",
  "menu_title": "TV Viewing Options",
  "title_source": "dish_after_logo_crop",
  "grey_box_bbox": [253, 35, 760, 685],
  "focused_item": "TV Activity",
  "human_label": "TV Viewing Options → TV Activity"
}
```

## v11 perception + parental-control upgrades

### Tesseract whitelist fix
The DEBUG line `unknown command line argument '-_&:+./'` was caused by a literal space in the OCR whitelist config. v11 strips whitespace from the whitelist before passing it to Tesseract, so punctuation like `-_&:+./` is no longer parsed as a separate command-line argument.

### Context QA and recovery
New endpoint:

```text
POST /api/crawl/review_context_quality
```

Body:

```json
{"max_nodes": 0, "auto_enrich": true}
```

It flags and optionally reprocesses states with missing focus, low focus confidence, missing screen title, weak focused-item OCR, OCR soup, and PIN popups. The report is useful before route planning because it tells you which parts of the learned graph are trustworthy.

### Better red-focus selection
v11 scores red candidates using nearby OCR words, bottom overlay position, and text-label evidence. This prevents red logos/artwork, such as FOX LIVE badges or red graphics in the video, from beating the real red focus outline.

### Overlay/menu block context
v11 adds left-strip overlay title recovery for screens such as `Recall` and `Trending Live`, in addition to the v10 DISH top-left page name and grey-box block-title logic.

### Parental Control Lab
Open:

```text
http://127.0.0.1:8502/parental
```

New endpoints:

```text
GET  /api/parental/status
POST /api/parental/remember_pin
POST /api/parental/enter_pin_if_prompt
POST /api/parental/setup
POST /api/parental/verify
POST /api/parental/disable
```

The PIN is remembered only in the local app data file:

```text
crawler_data/parental_control_memory.json
```

Recommended workflow:
1. Use dry-run setup first.
2. Run setup once the learned route to Parental Control Settings looks correct.
3. Verify by tuning a known blocked test channel.
4. Let the agent detect the parental PIN popup and enter the remembered PIN.
5. Disable controls using the remembered PIN.


## v13 Manual Teacher Mode

Open `http://127.0.0.1:8502/teach` to manually drive the set-top while the app records a demonstration session. Every recorded remote press is stored as a before-screen → button/sequence → after-screen transition and is fed directly into `crawler_data/nav_graph.json` and `crawler_data/crawler_brain.json`.

Teacher Mode endpoints:

- `POST /api/teach/start` — begin a teaching session.
- `POST /api/teach/stop` — stop and save the session under `crawler_data/manual_sessions/`.
- `GET /api/teach/status` — inspect active/latest teaching session.
- `GET /api/teach/sessions` — list saved sessions.
- `POST /api/teach/record_key` — record one key transition directly.
- `POST /api/teach/annotate` — add operator notes to the active session.
- `POST /api/teach/explore_from_here` — start autonomous continuous exploration from the current live screen instead of returning home first.

When a teaching session is active, the normal `/monitor` and `/send_key` controls automatically record transitions, so you can use the monitor window as the teaching cockpit.

## v14 Timed Execution + Fast Teacher Burst

This build separates button execution speed from perception depth.

New behavior:
- Known path replay presses buttons quickly and verifies at checkpoints.
- Manual Teacher Mode sends buttons immediately and learns after the operator pauses.
- Fast visual checkpoints skip OCR unless the transition is new, uncertain, or a configured deep checkpoint.
- Timing outliers are clipped so one blocked OCR/capture sample cannot poison future button timing.
- Existing crawler brains are sanitized on crawler start using `timing_outlier_clip_s`.

Useful controls:
- `crawler_execution_mode`: `deep`, `balanced`, or `tunnel`
- `crawler_fast_known_path_enabled`: true/false
- `crawler_max_adaptive_observe_s`: hard cap for post-button observation
- `crawler_timing_outlier_clip_s`: max latency sample stored as button timing
- `crawler_route_replay_gap_s`: fast gap for learned route replay
- `teacher_fast_recording_enabled`: send immediately; learn after burst pause
- `teacher_burst_idle_s`: pause duration before a manual burst is learned

Teacher Mode:
- Open `/teach`
- Start recording
- Drive with buttons normally
- Fast button bursts are learned as one sequence transition, e.g. `right,down,select`.
- Use `Flush pending burst` before stopping if you want to force the checkpoint immediately.

## v16 Learning Dashboards

Open the dashboard hub:

```text
http://127.0.0.1:8502/dashboards
```

Views:

```text
/dashboard/exec  - leadership dashboard
/dashboard/eng   - engineering/training dashboard
```

Superset-friendly export:

```text
/api/dashboards/superset.zip
```

The export includes CSV datasets, SQL helper views, and a manifest describing the Executive and Engineering dashboards.

## v20 Channel Surf / Displayed Clock / Dashboard Integration

v20 integrates Channel Surf into the main app navigation and dashboards.

New Channel Surf modes:

- `direct` — numeric tune explicit channels or ranges.
- `channel_up` — tune a starting channel, then use CH+ to discover what the receiver considers the next available channel.
- `channel_down` — tune a starting channel, then use CH-.

This matters because skipped channel numbers are real operational data. The app now logs requested channel, observed channel guess, input method, navigation key, and skipped/jumped channel notes.

v20 also extracts the receiver-displayed current time from Guide/Info/live UI header regions and compares it to the actual wall-clock moment. Time drift candidates appear in the Engineering and Executive dashboards and in the Superset export.

New Superset datasets:

```text
stb_channel_surf
stb_display_time_checks
stb_sysdiag_bootstrap
```

New dashboard route remains:

```text
/channel_surf
```

## v21 Channel Metadata Parser

v21 adds screen-specific channel/program parsing for Live TV banners, Guide rows, and TV Show/Info pages.  The Channel Surf agent no longer guesses channel/program fields from one giant OCR blob.  It now reads stable regions separately:

- Live TV banner: program title, description, channel code/number, visible date/time, and watermark/logo text.
- Guide: selected/focused grid tile, selected channel row, right-side program detail panel, and visible guide date/time.
- TV Show / Info: program title, episode/subtitle, description, channel code/number, date/time, and action buttons.

New observation fields include `live_metadata`, `info_metadata`, `guide_metadata`, `best_metadata`, `channel_code_guess`, `program_title_guess`, and `program_description_guess`. Dashboards and Superset exports include the new metadata confidence/source fields.

## v22 Dashboard Channel Catalog Upgrade

v22 adds dashboard and Superset visibility for the Channel Surf data that matters most during lineup validation:

- observed channel number + observed channel code/name
- learned channel name/symbols from the crawler brain, when available
- latest observed program title and description per channel
- latest observed STB displayed time per channel
- all observed STB displayed-time reads by surface: live, info, guide
- time drift/discrepancy values beside the channel/program context

New dashboard payload fields:

```text
exec.channel_catalog
exec.observed_stb_times
eng.channel_catalog
eng.observed_stb_times
```

New Superset datasets:

```text
stb_observed_channel_catalog
stb_observed_stb_times
```

New Superset helper views:

```text
v_stb_observed_channel_latest
v_stb_observed_clock_by_surface
```

## v23 Region-First Perception for the Main Crawler

v23 generalizes the Channel Metadata Parser idea into the rest of the crawler.  The crawler now tries to read known regions first before falling back to broad OCR:

```text
known screen family → expected regions → targeted OCR/vision → broaden only if expectations fail
```

Examples:

- Live TV: top banner, channel line, clock, progress/status bar.
- Guide: selected row, selected grid cell, right-side detail panel, visible guide clock.
- TV Show / Info: title area, channel/time cluster, description panel, action buttons.
- Menus/settings: DISH top-left page title, grey block title, focused row/tile, action bar.
- DVR/OnDemand/content shelves: top page context, focused tile/row, right-side or lower detail area.

New endpoint:

```text
/api/crawl/region_first
```

The response includes:

```text
screen_family
confidence
stage: targeted | common | broad
expected_regions
satisfied_regions
missing_expectations
suggested_actions
avoid_actions
quality_flags
regions
```

The result is attached to each learned state under:

```json
focus.region_first
```

The action planner also uses these hints.  For example, guide-like screens prioritize grid movement and Info/Select; loading screens recommend wait and avoid arrow/select; passive/live TV prioritizes Info, Guide, CH+/CH−, and Options.

This makes the crawler behave less like a full-screen OCR scraper and more like a human operator who knows where important UI facts normally live.

---

## v26 Notes: PPV Purchase Test Lab and Always-On Monitor Learning

### PPV purchase testing

Earlier versions treated PPV/purchase screens as observe-only. v26 adds an explicitly armed PPV test workflow for test accounts.

Open:

```text
/ppv
```

APIs:

```text
GET  /api/ppv/status
GET  /api/ppv/analyze
POST /api/ppv/arm
POST /api/ppv/disarm
POST /api/ppv/purchase_current
```

The PPV workflow remains guarded by default. To enable purchase testing, set this in `config.json`:

```json
{
  "ppv_purchase_test_enabled": true
}
```

Then arm the workflow from `/ppv` or `/api/ppv/arm`. Actual purchase steps require both an active arm window and `confirm_purchase=true` in the request. This prevents accidental ordering on non-test accounts.

### Always-on monitor learning

v26 also makes operator actions from `/monitor`, `/send_key`, `/key/<key>`, and `/api/tune` learn automatically. The app records these user-driven commands as high-value customer-path demonstrations using the same before → button/sequence → after transition logic as autonomous crawling.

Config:

```json
{
  "monitor_auto_learning_enabled": true,
  "monitor_auto_learning_interrupts_crawler": true,
  "monitor_auto_learning_gap_s": 0.075
}
```

If the autonomous crawler is running and a human sends a monitor command, the crawler is stopped and the operator command is recorded as the new authoritative path. These transitions receive extra reward weight because they represent likely customer/operator navigation paths.

Status endpoint:

```text
/api/monitor_learning/status
```
