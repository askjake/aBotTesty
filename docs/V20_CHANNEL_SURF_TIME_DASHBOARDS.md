# v20 Channel Surf, Display Clock, and Dashboard Integration

## Why this exists

The v19 channel surf feature proved useful, but it was still isolated from the rest of the UI and dashboards. v20 integrates it into the main navigation, adds engineering/executive/Superset reporting, and adds receiver displayed-clock checks.

## New behavior

### Channel Surf in app navigation

The Channel Surf Lab is now linked from the Monitor, Intelligence, Teacher, Human Observer, Parental, Dashboard Hub, and dashboard nav bars.

### Direct tune and channel step modes

The Channel Surf Lab now supports:

- `direct`: numeric channel entry for explicit lists/ranges.
- `channel_up`: numeric tune once, then repeatedly press CH+.
- `channel_down`: numeric tune once, then repeatedly press CH-.

Channel step mode is intentionally important because providers can skip channel numbers. The app logs both the requested/expected channel and the observed channel guess, then flags skipped/jumped transitions.

### Displayed clock extraction

For live, Info, and Guide captures, v20 tries to extract the receiver-displayed current time. It prioritizes high-signal regions such as the header band / DISH title lane and date+time patterns. It deliberately avoids treating ordinary guide program start times as the receiver clock unless they appear in a header-like source.

Logged fields include:

- `live_time_context`
- `info_time_context`
- `guide_time_context`
- `time_discrepancy_flags`
- `display_time_drift_minutes`

### Dashboard/Superset integration

The dashboards now include Channel Surf and displayed-clock data.

New Superset datasets:

- `stb_channel_surf`
- `stb_display_time_checks`
- `stb_sysdiag_bootstrap`

New helper views:

- `v_stb_channel_surf_quality`
- `v_stb_display_time_drift`

## Validation

Validated with:

```text
compileall: OK
test_video_health_v19.py: OK
test_channel_surf_v19.py: OK
test_channel_surf_v20.py: OK
test_dashboards_v16.py: OK
test_human_observer_v18.py: OK
test_transition_completion_timing_v17.py: OK
test_autonomous_crawler.py: OK
```
