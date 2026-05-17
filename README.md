# aBotTesty — STB Learning, Navigation, and Human-Observer Automation

`aBotTesty` is a Flask-based set-top-box automation lab. It combines live video capture, JAMboree Lite / SGS remote control, autonomous UI exploration, manual teaching, timing intelligence, learned navigation maps, dashboards, and human-style feature testing.

The app’s core loop is simple but powerful:

```text
watch the TV screen → understand the current UI → press remote buttons → wait for the screen to actually finish changing → learn what happened
```

It is designed around the STB alias `found1`, but the architecture can be reused for other boxes by updating the STB store/config.

---

## What this app does

### 1. Monitors the active video input

The app reads from a capture device and exposes:

- live MJPEG video
- still snapshots
- active-video status
- screen classification APIs
- focus/overlay debug views

### 2. Controls the set-top box

Remote commands are sent through the merged JAMboree Lite / SGS route layer. The app can send single keys, key sequences, direct channel numbers, route replays, and test/playbook actions.

### 3. Learns the UI as a graph

The crawler learns:

```text
before screen --button/sequence--> after screen
```

Each node stores screen perception. Each edge stores the action, reward, timing, confidence, before/after screenshots, OCR deltas, focus movement, and route-usefulness.

### 4. Learns like a human operator

The newer logic does not blindly treat every screenshot as equal. It tries to identify whether the screen is:

- actionable UI
- passive video
- loading/interstitial
- PIN prompt
- PPV/purchase flow
- timer/recording flow
- settings/menu screen
- risky/irreversible screen

### 5. Lets a human teach it

Teacher Mode lets you manually drive the STB while the app records your button presses and snapshots as high-confidence demonstrations. The crawler can then explore from the point you showed it.

### 6. Tracks progress and known-unknowns

The dashboard layer shows what the app knows, what it does not know yet, which actions are reliable, where perception is weak, which paths are flaky, and where the testing backlog lives.

---

## Quick start on Windows

From the project folder:

```bat
run_merged_app.bat
```

Then open:

```text
http://127.0.0.1:8502/monitor
```

If running from another machine on the LAN, replace `127.0.0.1` with the host IP.

---

## Main pages

| Page | Purpose |
|---|---|
| `/monitor` | Live video + manual remote-control buttons |
| `/crawl` | Autonomous crawler control page |
| `/intelligence` | Learned map, routes, transitions, confidence, graph exploration |
| `/teach` | Manual teaching / demonstration recorder |
| `/parental` | Parental-control test lab and PIN workflow controls |
| `/human` | Human-observer interpretation, playbooks, test backlog |
| `/dashboards` | Dashboard hub |
| `/dashboard/exec` | Executive learning/progress dashboard |
| `/dashboard/eng` | Engineering/training/debug dashboard |

---

## Main API routes

### Video and monitor

| Route | Purpose |
|---|---|
| `/video.mjpg` | MJPEG stream |
| `/snapshot.jpg` | Current frame JPEG |
| `/api/status` | Combined app/video/STB/crawler status |
| `/api/active-video` | Active video status only |
| `/screen` | Compatibility screen-state endpoint |
| `/screenshot` | Compatibility screenshot endpoint |

### Remote control

| Route | Purpose |
|---|---|
| `/send_key` | POST a key, for example `{ "key": "guide" }` |
| `/key/<key>` | Browser-friendly key route |
| `/api/tune?channel=206` | Direct channel tune by digits + select |
| `/auto/sgs/found1/<button>/<delay>` | JAMboree Lite-style route |

### Crawler and learned graph

| Route | Purpose |
|---|---|
| `/api/crawl/start` | Start crawl with optional config overrides |
| `/api/crawl/stop` | Stop crawler |
| `/api/crawl/status` | Runtime status, counters, events, learning summary |
| `/api/crawl/graph` | Raw learned graph |
| `/api/crawl/map` | Visual/intelligence map payload |
| `/api/crawl/transitions` | Before/button/after transition journal |
| `/api/crawl/classify` | Classify current live screen |
| `/api/crawl/focus` | Current focus/context analysis |
| `/api/crawl/focus/overlay.jpg` | Screenshot with detected focus/page/block overlay |
| `/api/crawl/enrich_context` | Reprocess saved screenshots with newer perception logic |
| `/api/crawl/review_context_quality` | Find weak OCR/focus/title captures |

### Route planning / goals

| Route | Purpose |
|---|---|
| `/api/crawl/candidates?q=settings` | Search learned states/screens |
| `/api/crawl/plan` | Plan route to a target screen |
| `/api/crawl/navigate` | Navigate to a learned target screen |
| `/api/crawl/goal` | Navigate to a semantic goal and optionally execute final sequence |

### Teacher mode

| Route | Purpose |
|---|---|
| `/api/teach/start` | Start manual teaching session |
| `/api/teach/stop` | Stop/save session |
| `/api/teach/status` | Active/latest session status |
| `/api/teach/sessions` | List saved sessions |
| `/api/teach/record_key` | Record a key transition directly |
| `/api/teach/annotate` | Add human note to the session |
| `/api/teach/explore_from_here` | Start autonomous exploration from the current live screen |

### Parental-control lab

| Route | Purpose |
|---|---|
| `/api/parental/status` | Current parental-lab state |
| `/api/parental/remember_pin` | Store local test PIN memory |
| `/api/parental/enter_pin_if_prompt` | Enter remembered PIN if a PIN prompt is detected |
| `/api/parental/setup` | Try setup/find workflow |
| `/api/parental/verify` | Verify blocked content/PIN prompt behavior |
| `/api/parental/disable` | Try disable workflow |

### Human-observer and dashboards

| Route | Purpose |
|---|---|
| `/api/human/current` | Human-style interpretation of the current screen |
| `/api/human/playbooks` | Available test playbooks |
| `/api/human/backlog` | Known-unknowns and testing backlog |
| `/api/dashboards/summary` | Dashboard summary |
| `/api/dashboards/exec` | Executive dashboard data |
| `/api/dashboards/eng` | Engineering dashboard data |
| `/api/dashboards/superset.zip` | Superset-friendly export bundle |

---

## Data written by the app

The app learns into `crawler_data/`:

```text
crawler_data/
  nav_graph.json                    # learned screen/action graph
  crawler_brain.json                # action rewards, timing, concepts, channels
  learned_sequences.json            # mined useful button sequences
  unreachable_states.json           # states/routes that failed and need retry
  parental_control_memory.json      # local remembered test PIN, if used
  states/                           # saved screenshots
  manual_sessions/                  # human teaching demonstrations
```

Recommended policy:

- Keep old screenshots and graph data when upgrading.
- Back up `crawler_data` before major experiments.
- Reset/downgrade timing data if upgrading from a pre-v17 build.
- Treat old route confidence as advisory until v17+ revalidates completion timing.

---

## Core learning model

The app learns a directed graph:

```text
State A -- action/button/sequence --> State B
```

A state is not just an image. It can include:

- perceptual hashes
- color histogram
- brightness / variance / entropy
- edge density
- OCR text/tokens
- detected focus region
- page name
- menu/block title
- focused item/value
- semantic tags
- risk flags
- UI pattern classification
- human-observer classification

A transition can include:

- before screenshot
- action or sequence
- after screenshot
- confidence
- reward
- timing phases
- OCR/token delta
- focus movement
- whether it discovered something new
- whether it looked like loading/passive video/risky UI

---

## Focus and context detection

The app detects the red DISH focus outline/parallelogram using HSV red masking and contour scoring. It then OCRs surrounding regions to infer what a human would understand:

```text
DISH page name       → top-left title after DISH logo
Grey block title     → title at the top of a smaller grey panel
Focused item         → selected tile/row/button
Focused value        → setting value beside/near the focused row
Neighbor text        → left/right/up/down context
Action bar           → bottom buttons/options
Risk context         → purchase/delete/reset/PIN/adult/parental/etc.
```

Example perception:

```json
{
  "page_name": "Parental Control Settings",
  "block_title": "TV Viewing Options",
  "screen_title": "Parental Control Settings",
  "menu_title": "TV Viewing Options",
  "focused_item": "TV Activity",
  "human_label": "TV Viewing Options → TV Activity"
}
```

Debug the current focus overlay here:

```text
http://127.0.0.1:8502/api/crawl/focus/overlay.jpg
```

---

## Timing model

v17+ separates timing into phases:

```text
button press → action starts on screen → action completes / screen stabilizes
```

This matters because many STB screens begin changing quickly but are not ready for another meaningful decision until fade/load/menu drawing finishes.

The app learns:

- start latency
- completion latency
- stable-window time
- timing flags
- remarkable timing events

Timing flags include:

- `completion_uncertain`
- `low_information_menu_transition`
- `weak_menu_ocr_no_focus`
- `post_completion_recapture`
- `remarkable_slow_start`
- `remarkable_slow_completion`

Human interpretation:

```text
The remote reacted quickly, but the menu was not done loading yet.
```

This prevents the crawler from learning transitional/fading/loading frames as real destination screens.

---

## Teacher Mode

Open:

```text
http://127.0.0.1:8502/teach
```

Teacher Mode lets a human demonstrate a feature path. While recording, normal monitor buttons are captured as demonstrations.

Typical workflow:

1. Start teaching session.
2. Manually navigate to a feature.
3. Add notes such as `Found PPV list` or `This is the channel lock page`.
4. Stop/save session.
5. Click **Explore from current screen** to let the crawler branch out from that feature.

Teacher Mode supports fast bursts. A sequence such as:

```text
right → right → down → select
```

can be learned as one meaningful transition instead of slowing down after each key.

---

## Continuous autonomous exploration

For long exploration runs, use:

```text
Max steps: 0
Max states: 0 or high value
Max depth: 18+
Attempts/action: 2-3
Continuous exploration: enabled
Active reseed: enabled
Risky SELECT: disabled
Execution mode: balanced
```

The crawler rewards:

- new screens
- new OCR/context
- new menu titles
- new focused items
- new setting/value pairs
- new transition edges
- known routes that lead to unexplored frontier

It penalizes:

- no-op buttons
- same-screen loops
- repeated discoveries without new information
- passive video masquerading as UI
- loading/interstitial captures
- risky SELECT contexts

---

## Human Observer

Open:

```text
http://127.0.0.1:8502/human
```

The Human Observer layer tries to think like a person watching TV:

- Is this screen actionable?
- Is it just live video?
- Is it still loading?
- Is there a PIN prompt?
- Is this a PPV/purchase flow?
- Is this a timer/recording flow?
- What would I notice or wait for?
- What action would be annoying or dangerous?
- What feature/test goal does this screen relate to?

Example classifications:

```text
loading_interstitial
passive_video
pin_prompt
purchase_or_ppv
timer_or_recording_flow
actionable_ui
unknown_visual
```

This lets the app avoid creating junk states from passive video and helps it recognize feature workflows like parental controls, timers, PPV, search, and channel locks.

---

## Playbooks

The app includes human-style feature playbooks, including:

- verify parental-control block and PIN unlock
- block/unblock channel or rating
- set/verify timer or recording
- inspect PPV availability and pricing
- search content and verify results

These playbooks are intentionally conservative. They can navigate, observe, and verify, but risky actions such as purchases or irreversible settings should require explicit human approval.

---

## Parental Control Lab

Open:

```text
http://127.0.0.1:8502/parental
```

The lab can remember a local test PIN and use it when it detects a PIN prompt. It is designed around this flow:

```text
find parental-control settings
set or verify PIN
turn/block settings on
try blocked content/channel
verify PIN popup appears
enter remembered PIN
unlock/verify behavior
return to settings
turn controls off
```

Safety notes:

- Use dry-run first.
- Watch the live monitor the first time.
- Keep purchase/risky SELECT disabled.
- Do not store real customer PINs.
- The remembered PIN is local app test data.

---

## Dashboards

Open:

```text
http://127.0.0.1:8502/dashboards
```

Dashboards:

```text
/dashboard/exec
/dashboard/eng
```

The Superset export is available at:

```text
/api/dashboards/superset.zip
```

The export includes CSVs and helper SQL for:

- states
- transitions
- action timing
- rewards
- coverage
- known-unknowns
- timeline
- perception quality
- focus confidence
- transition confidence
- route reliability

---

## Recommended upgrade process

Before replacing app code:

```powershell
Copy-Item .\crawler_data .\crawler_data_backup_before_upgrade -Recurse
```

Then copy the new app files over the old app folder, keeping `crawler_data`.

When moving from older builds to v17+:

- Keep screenshots and graph.
- Keep menu/title/focus/channel/concept memory.
- Clear or downgrade old timing data if it was learned before phased-completion timing.
- Let the new version revalidate important routes.

---

## Common troubleshooting

### Tesseract debug spam

Lines like this are normal when OCR debug logging is enabled:

```text
pytesseract - ['tesseract', '...Temp\\tess_xxx_input.PNG', ...]
```

They mean the app is OCRing cropped regions. To reduce noise, set the `pytesseract` logger to WARNING.

### `unwind landed elsewhere`

This means BACK did not return to the exact expected screen. That is not always a bug. On STBs, BACK can close popups, exit apps, return to live TV, or jump to a parent menu. The app records this as learning data.

### App goes idle

Use v7+ continuous reseed settings:

- continuous exploration enabled
- reseed when idle enabled
- max steps `0`
- max states `0` or high

### Menus learned while still loading

Use v17+ phased-completion timing. It waits for completion/stability, not just first visual reaction.

---

## Tests

Common local checks:

```bat
.venv\Scripts\activate.bat
python test_endpoints.py
python test_autonomous_crawler.py
python test_transition_completion_timing_v17.py
python test_human_observer_v18.py
```

Not every bundle contains every historical test file, but the app is built to keep tests small and targeted.

---

## Safety model

The app should not be allowed to blindly execute risky actions. Keep guardrails enabled unless you are intentionally running a supervised test.

Risky contexts include:

- purchase / PPV / rent / order
- delete / erase / factory reset
- payment / billing
- parental / adult / PIN / password
- account settings
- service cancellation

Recommended default:

```text
Risky SELECT: disabled
Execution mode: balanced
Teacher Mode: supervised
Parental Lab: dry-run first
PPV: observe/list only, do not confirm purchase
```

---

## Project philosophy

This app is not just a remote-control script. It is a learning agent for STB behavior.

The goal is to move from:

```text
press button and hope
```

to:

```text
understand what screen I am on
know where focus is
know what changed
know when loading finished
know what is risky
remember what a human taught me
explore nearby possibilities
explain progress and uncertainty
```

That is the path toward an automated tester that watches TV like a patient, curious human operator.