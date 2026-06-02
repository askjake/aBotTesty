# v17 Timing Completion Analysis

## What was wrong

The previous timing model learned one number called `response_s`. In practice, that number was the time from button press to the first visible screen change. That is useful, but it is not the same as the time required for the destination screen/menu to finish loading.

The old `wait_after_action()` logic did this:

1. Send button.
2. Poll with quick visual fingerprints.
3. Mark `first_change_s` when the screen first differs from the before frame.
4. Stop after a short expected/hard-capped observation window.
5. Capture `after_fp` and learn the transition.

That caused the crawler to learn transitional frames as real destinations when menus were still animating, fading, dimming, loading, or showing partial overlays.

## Evidence from uploaded snapshots/data

The uploaded run contained:

- 3,683 learned states
- 346 transition edges
- 6,896 state screenshots
- Several high-latency transition samples where the captured destination was visually noisy, partly loaded, or semantically weak

Examples observed in the uploaded `crawler_data` included:

- `options` landing on `TV Viewing Options` correctly sometimes, but also recording incomplete/weak transient states around the same feature.
- `home`, `guide`, `select`, `options`, and `ddiamond` recording snapshots with low focus confidence, weak OCR, or live-video overlay content when the command was intended to reach a menu/modal.
- Timing samples with only one visual sample because full OCR/capture cost leaked into the measurement path.

## v17 refactor

v17 separates timing into three phases:

```text
button press -> action_start_s -> action_complete_s
```

Where:

- `action_start_s` = first visible reaction on screen
- `action_complete_s` = screen appears visually stable and suitable to learn
- `stable_window_s` = how long the screen was stable before capture

The crawler now stores these fields per action:

- `avg_start_s`
- `last_start_s`
- `avg_complete_s`
- `last_complete_s`
- `avg_stable_s`
- `remarkable_count`
- `last_flags`
- `last_remarkable`

The old fields remain for backwards compatibility:

- `avg_response_s`
- `last_response_s`

Those now map to start timing.

## Completion gate

The new `wait_after_action()` does not immediately learn the first changed frame. It waits for consecutive stable visual fingerprints using:

- `completion_stability_threshold`
- `completion_stable_observations_required`
- `completion_min_observe_s`
- `max_completion_observe_s`

Then it captures the final state.

If the final capture still looks like a transitional menu frame, v17 waits and recaptures using:

- `completion_extra_wait_on_incomplete_s`
- `completion_extra_attempts`

## Remarkable timing flags

v17 compares current timing against learned expectations and records flags such as:

- `remarkable_slow_start`
- `remarkable_slow_completion`
- `completion_uncertain`
- `low_information_menu_transition`
- `weak_menu_ocr_no_focus`
- `post_completion_recapture`

These flags are stored in the edge timing sample and action timing stats, and exposed to the engineering dashboard.

## Highest ROI behavior improvements

1. Do not learn transitional frames as destination states.
2. Keep fast key execution for known paths, but verify at completion checkpoints.
3. Treat slow completion as different from slow remote reaction.
4. Flag remarkable timing instead of silently poisoning average timing.
5. Use conservative human assumptions: menu-like actions should usually land on a focusable menu, titled modal, or recognizable page; otherwise keep watching briefly.

## New configuration fields

```python
max_completion_observe_s = 6.0
completion_min_observe_s = 0.35
completion_quiet_s = 0.45
completion_stability_threshold = 0.992
completion_stable_observations_required = 3
completion_extra_wait_on_incomplete_s = 1.2
completion_extra_attempts = 2
remarkable_timing_multiplier = 2.75
remarkable_timing_min_delta_s = 1.0
```

## Validation

Validated with:

- Python compile checks
- `test_autonomous_crawler.py`
- `test_timing_execution_v14.py`
- `test_transition_completion_timing_v17.py`
- `test_manual_teaching_v13.py`
- `test_fork_merge_v15.py`
- `test_dashboards_v16.py`

Full `compileall` also passes after correcting malformed top-level duplicate JAMboree files from the uploaded store.
