# v31 On Demand Flow Intelligence

Evidence from `nav_graph(2).zip` showed 25 PPV/On Demand events, including 19 operator-observed purchase-flow transitions.  The app clearly detected that the operator was in On Demand/Purchase context, saw On Demand landing, asset summary, purchase option, one final confirmation screen, and a paid `$19.99` option.

The weaker areas were title fidelity and old log rows without structured display-clock context.  Titles like `ole rey DJANGO...`, `Watch Now`, or OCR fragments were being treated as asset titles.  v31 adds stage-specific parsing for the On Demand screens and captures receiver-displayed time from On Demand pages into dashboard rows.

Key changes:

- Default PPV navigation uses `channel:1`, because this STB enters On Demand that way.
- New `ondemand_flow_intelligence.py` classifies screens into:
  - `on_demand_landing`
  - `asset_summary`
  - `episode_list`
  - `purchase_option`
  - `purchase_confirmation`
  - `loading`
  - `unknown`
- `/monitor` operator actions continue to learn graph transitions and now also write PPV/On Demand stage-transition observations when relevant.
- PPV dashboard rows include stage, operator key, On Demand displayed time, drift, source, and confidence.
- Superset export includes `stb_ppv_display_times`.

Analysis of the uploaded transaction log:

- Operator PPV/On Demand observations: 19
- Stage coverage: On Demand landing, asset summary, purchase option, final confirmation observed
- Replication readiness: high, because the data includes channel-1 entry, select transitions, price observation, and final confirmation observation
- Price observed: `$19.99` in the structured purchase option stage
- Displayed On Demand clock samples observed around `Sun 5/24 | 2:23p` through `2:33p`

Remaining caution:

Asset-title OCR from the old run is still weak on several frames.  v31 improves future captures, but existing corrupted title rows should be treated as low-trust unless later re-observed with trusted region parsing.
