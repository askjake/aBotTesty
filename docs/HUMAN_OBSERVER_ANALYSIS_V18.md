# v18 Human Observer Analysis

## Evidence reviewed

The uploaded `jamboree.zip` contained a long-running crawler dataset and the app code from the current v17 line.

Current learned dataset summary from `crawler_data`:

- 4,294 learned states
- 528 learned transition edges
- Brain schema: `jamboree_crawler_brain_v7_phased_timing`
- v17 phased timing is active and useful: timing now separates action-start from action-completion.

## What the snapshots showed

The biggest perception failure was not remote control. It was **treating transient TV/STB visual states as real menu destinations**.

Common failure patterns found:

- **DISH loading/interstitial screens learned as destination states.** Several dark screens with the DISH logo/progress area were labeled as real UI, for example with bogus titles like `rye → desh rye`.
- **DISH logo or red broadcast graphics mistaken for focus.** Low-confidence red shapes near the top-left or in video art were sometimes treated as the active red focus selector.
- **Passive video content creates junk states.** A human knows changing video frames are usually the same “watching TV” state unless an overlay, info banner, guide, menu, PIN dialog, or purchase prompt appears.
- **Feature intent was under-modeled.** The app could identify text, but it did not always understand that PIN prompts, PPV screens, timers/recording confirmations, rating blocks, and settings toggles are special task contexts.

Quality indicators in the old graph analysis:

- 990 low-confidence focus states
- 862 likely DISH-logo-as-focus states
- 469 no-focus states
- 225 missing-title states
- 17 actions with recent `completion_uncertain` timing flags

## What a human would do differently

A human watching TV subconsciously does several things the crawler did not consistently do:

1. **Wait through loading.** A person does not map the spinner/progress screen as the menu. They wait for the menu to finish.
2. **Separate video from UI.** A person ignores video-frame changes unless an actionable overlay appears.
3. **Look for title + focus + affordances.** Humans read page title, grey-box title, selected item, highlighted value, and button affordances together.
4. **Recognize task modes.** PIN entry, PPV purchase, timer setup, recording confirmation, and parental/rating blocks are not generic menus.
5. **Avoid risky confirmation.** Humans inspect PPV title/price and back out unless a purchase test is explicitly authorized.
6. **Notice annoyance/friction.** Excessive loading, weak focus visibility, unclear state, and repeated timeout/backtracking are product-quality signals, not just crawler noise.

## v18 upgrades integrated

### 1. Human observer layer

New file: `human_observer.py`

It classifies each observation as one of:

- `loading_interstitial`
- `passive_video`
- `pin_prompt`
- `purchase_or_ppv`
- `timer_or_recording_flow`
- `actionable_ui`
- `unknown_visual`

It also emits:

- `feature_tags`
- `test_goals`
- `risk_flags`
- `annoyance_flags`
- `recommended_actions`
- `avoid_actions`
- channel hints
- human-readable summaries

### 2. Better loading treatment

The crawler now detects DISH-style loading by combining:

- loading text
- DISH logo presence
- center progress dots
- low-information dark screen
- logo-misread-as-focus evidence

Loading/interstitial states are marked transient and skipped as exploration frontiers.

### 3. Passive video collapse

Passive video is recognized and collapsed more aggressively. This reduces junk states caused by normal video motion while still allowing meaningful overlay/menu actions like guide/info/options/home/channel changes.

### 4. Risk/task-aware action policy

The crawler now adjusts action choices based on human cues:

- PIN prompt: prefer remembered PIN/back/home; avoid random navigation.
- PPV/purchase: prefer read/info/back; avoid confirm/order/purchase.
- Timer/recording: prefer confirmation-oriented actions and follow-up verification.
- Passive video: prefer guide/info/options/recall/home/channel changes instead of directional spam.
- Loading: wait, do not explore.

### 5. Human playbooks

New file: `human_playbooks.py`

Includes goal templates for:

- verify parental-control block and PIN unlock
- block/unblock channel or rating
- set/verify timer or recording
- inspect PPV availability and pricing
- search content and verify results

New page/API:

- `/human`
- `/api/human/current`
- `/api/human/playbooks`
- `/api/human/backlog`

### 6. Dashboard enrichment

Engineering dashboard data now includes:

- human screen kind
- human confidence
- feature tags
- test goals
- annoyance flags
- risk flags
- human screen-kind breakdown

## Testing

Validated in this bundle:

- `python3 -m compileall -q .`
- `test_human_observer_v18.py`
- `test_transition_completion_timing_v17.py`
- `test_timing_execution_v14.py`
- `test_fork_merge_v15.py`
- `test_manual_teaching_v13.py`
- `test_parental_active_v12.py`
- `test_focus_context_v11.py`
- `test_intelligence_features.py`
- `test_transition_journal_v6.py`
- `test_autonomous_crawler.py`
- `test_dashboards_v16.py`
- Human playbooks smoke test

## Practical recommendation

Keep the current graph/brain/screenshots. Use v18 as a code update. Then run:

1. `/human` to inspect current-screen interpretation.
2. `/api/human/backlog` to see feature/test opportunities found in the graph.
3. `/dashboard/eng` to watch human screen-kind breakdown and timing flags.
4. Teacher Mode for feature demos; then use “Explore from here.”

The crawler should now spend less time learning spinners/video noise and more time learning TV features the way a human tester would: menus, dialogs, confirmations, purchase boundaries, PIN prompts, ratings/channels, timer/recording behavior, and annoying friction.
