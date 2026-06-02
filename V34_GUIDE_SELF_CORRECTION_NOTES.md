# v34 Guide / Self-Correction Bundle

## What v34 fixes immediately

### 1. `/send_key` no longer treats raw channel numbers as nonexistent SGS buttons

The failure:

```text
ValueError: No SGS mapping for 250
```

happened because `/send_key` received `key=250`, normalized it as a single synthetic button named `250`, and passed that to the SGS bridge. The SGS map correctly has buttons for `2`, `5`, `0`, and `select`, but not a button named `250`.

v34 changes `key_sequence_for()` so raw multi-digit numeric strings are interpreted as channel-entry intent:

```text
250    -> 2, 5, 0, select
CH_206 -> 2, 0, 6, select
7      -> 7
```

This preserves keypad digits while self-correcting the common operator/app path where a guide channel number gets sent directly.

## New guide intelligence

v34 adds `extract_guide_grid()` in `channel_metadata.py`. It teaches the app that the DISH guide is a structured selectable grid:

- each visible row is a channel;
- the left strip contains channel number/code/logo/icon identity;
- each time cell in that row is a selectable program option;
- the red focus rectangle identifies the currently selected row/cell;
- every visible program cell can be represented as a relative button sequence from the current focus.

Example from the provided screenshot:

```json
{
  "selected": {
    "channel_number": "250",
    "channel_code": "ION",
    "title": "Hawaii Five-O",
    "button_sequence": ["select"],
    "icon_signature": "ah16:..."
  },
  "counts": {
    "rows": 7,
    "channels": 6,
    "programs": 27,
    "program_options": 35
  }
}
```

The visual channel logo/icon is recorded as a stable perceptual signature, not a bulky image blob. OCR text from the channel strip is still retained as `channel_logo_text`.

## New endpoints

### Analyze current guide

```http
POST /api/guide/analyze
Content-Type: application/json

{"learn": true}
```

Returns the current guide grid, selected cell, visible rows, visible programs, and what the crawler brain learned.

### Select a visible guide program

```http
POST /api/guide/select
Content-Type: application/json

{"query": "Hawaii Five", "dry_run": true}
```

`dry_run=true` returns the planned relative button sequence without pressing anything. With `dry_run=false`, the route is executed through the same teacher/operator learning path as manual remote control.

## Crawler brain additions

`ChannelRecord` now keeps guide-specific identity and program data:

- `channel_code`
- `channel_name`
- `channel_logo_texts`
- `icon_signatures`
- `programs`
- `guide_observations`
- `guide_rows_seen`

The new `CrawlerBrain.learn_guide_grid()` method can ingest a full visible guide screen and update many channel/program records at once, instead of learning only from explicit `CH_n` tuning.

## Current intelligence answer

Can it find programs in the guide? **Yes, v34 adds the primitives.** It can now parse the visible guide grid and search both the current screen and learned program records.

Can it select a desired program from the guide? **Yes for visible guide cells.** v34 computes relative navigation from the current selected cell to the target visible cell and can execute the sequence. The next phase is cross-page/time-window search: page through guide rows/times, collect a larger schedule index, then select from that index.

Does it understand channel logos/icons? **Now it records them.** v34 stores both OCR text from the channel strip and a perceptual icon signature alongside channel/program records.

Does it know the guide shows multiple selectable channel/program options? **Now explicitly.** The guide reader returns rows, cells, selected cell, and button sequences for visible cells.

## Validation

Executed in the bundle root:

```bash
python3 -m py_compile merged_app.py auto_crawler.py channel_metadata.py channel_surf_agent.py sequence_learner.py
python3 test_guide_self_correction_v34.py
python3 test_intelligence_v33.py
python3 test_demonstration_practice_v32.py
python3 test_channel_metadata_v25.py
```

Observed results:

```text
guide self-correction v34: OK
intelligence v33 map slicing: OK
demonstration practice v32 synthetic test: OK
CHANNEL_METADATA_V25_OK
```
