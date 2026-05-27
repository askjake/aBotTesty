# v34 Latest Data Analysis and Next Intelligence Phase

## Current data snapshot analyzed

From `crawler_data/crawler_brain.json` and `crawler_data/nav_graph.json` in the v33 upload:

- Navigation graph: about 6,801 states and 1,749 edges.
- Brain state-action records: about 1,392 state/action entries.
- Known OCR/semantic tokens: about 24,205.
- Known menu titles: about 3,866.
- Known focused items: about 4,853.
- Known setting pairs: about 1,553.
- Learned channel records before v34: 0.
- Learned sequences: 394.
- Sequence learner stats showed many mined sequences/suggestions, but zero successful suggestion outcomes, meaning the learner was mining paths but not yet proving them in a closed feedback loop.

## What the data says about learning effectiveness

The crawler has advanced strongly in broad UI discovery:

- It is no longer only a button masher; it has a large state graph and persistent action timing/reward history.
- It has learned many screen labels, focused items, menu titles, and settings pairs.
- It has route planning, graph slicing, demonstration practice, manual teacher mode, and adaptive timing.

The weak points are now clear:

1. **Channel/program intelligence was under-modeled.** The graph had no persistent channel records even though channel surf logs had hundreds of observations. v34 starts correcting that by letting guide screens populate channels/programs directly.
2. **Sequence suggestions were not being closed-loop scored.** The learner can mine sequences, but success/failure outcome feedback must be attached to actual post-condition verification.
3. **Stats integrity needs hard guards.** Some historical aggregate records can show successes greater than attempts. v34 does not destroy that data, but the next phase should add repair/invariant checks before dashboards or rewards consume those counters.
4. **Guide detail-panel extraction alone is not enough.** The old reader could identify the selected show, but it did not model the guide as a grid of multiple choices. v34 changes that.

## Next phase recommendation

### Phase 35: Closed-loop Guide Navigator and Feature Discovery Planner

Build a planner around four loops:

1. **Observe**
   - Parse current screen.
   - If guide: extract rows, programs, channel identities, icons, selected cell, time headers.
   - If not guide: classify the surface and decide whether `guide`, `back`, `home`, or `live` is the best anchor.

2. **Index**
   - Store visible guide data into a schedule index.
   - Record `channel_number + channel_code + icon_signature + program_title + time_label + relative_sequence`.
   - Page down/up/right/left through guide time and channel ranges, collecting more rows/cells.

3. **Act**
   - Given a target program/channel/feature, choose the safest known route.
   - Use dry-run planning first.
   - Execute one segment at a time.

4. **Verify and self-correct**
   - Verify the resulting screen contains the expected program/channel/title.
   - If mismatch, record the failed sequence and reason.
   - Try alternate path: retune channel, reopen guide, adjust row/time offset, or use search.
   - Update sequence suggestion outcome stats so mined sequences become proven, not just guessed.

## Infrastructure discovery enhancements

Add a passive/active discovery module that records:

- current STB alias, receiver ID, IP, SGS reachability, command latency;
- capture health, frame rate, active/black/colorbar status;
- OCR availability and average extraction time;
- guide extraction confidence by screen;
- failed command mapping attempts and auto-corrections;
- route execution latency and verification result.

Expose that in a `/api/diagnostics/intelligence` endpoint and dashboard tile.

## Performance collector/analyzer/learner

Add a small time-series collector for:

- action start latency;
- action completion latency;
- OCR/guide extraction duration;
- graph match duration;
- route plan duration;
- command failure rate;
- guide parse confidence;
- program selection success rate.

Use those metrics to auto-tune:

- settle time per action/screen kind;
- OCR depth frequency;
- graph candidate limits;
- when to use fast known paths versus deep verification;
- when to stop crawling a loop and reseed from a new anchor.

## Why this is the right next step

The app is already good at discovering screens. The next leap is task intelligence: “find this program,” “select this guide cell,” “prove I landed on the expected show,” “repair if not,” and “learn which route worked.” That turns a crawler into an operator apprentice.
