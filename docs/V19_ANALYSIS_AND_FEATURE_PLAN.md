# V19 Analysis Notes — STB Human-Style Test Upgrade

## Evidence reviewed

- `crawler_brain(1).json` schema: `jamboree_crawler_brain_v7_phased_timing`, updated `2026-05-23T16:36:46+00:00`
- `learned_sequences.json` schema: `sequence_learner_v2`, updated `2026-05-23T16:29:37+00:00`
- `unreachable_states.json` schema: `persistence_tracker_v2`, updated `2026-05-23T17:42:33+00:00`
- latest cropped states archive: `4,899` screenshots

## Observed weak spots

### 1. Inactive video was too binary

The capture monitor previously used brightness/variance thresholds only. That can confuse:
- valid static UI / color bars
- true STB black screen
- passive video with little motion

V19 adds `video_health.py`, classifying frames as `active_video`, `active_static_ui`, `color_bars`, `black_screen`, or `blank_or_no_signal`.

### 2. Black screen is a defect, not a passive stop condition

Black-screen frames were present in the newest screenshot sample. V19 treats this as STB/video misbehavior and attempts `ch_up`, `ch_down`, then `live` before giving up.

### 3. Sequence timing is polluted by long interaction windows

Several learned sequences show very large average times, which is not a real button cadence. These should not drive fast replay timing.

Top sequence timing outliers:
[
  [
    "up,down,left,right,select",
    296.234,
    12,
    24.958
  ],
  [
    "up,down,left,right",
    249.473,
    13,
    17.404
  ],
  [
    "ch_down,ch_up,ch_down,ch_up,ch_down",
    247.332,
    4,
    5.0
  ],
  [
    "info,guide,home,ch_down,ch_up",
    224.568,
    4,
    7.125
  ],
  [
    "guide,home,ch_down,ch_up,recall",
    223.64,
    3,
    6.25
  ],
  [
    "info,guide,home,options,input",
    217.776,
    7,
    7.536
  ],
  [
    "guide,home,options,input,recall",
    216.623,
    4,
    3.312
  ],
  [
    "down,left,right,select,back",
    216.325,
    12,
    21.521
  ],
  [
    "back,info,guide,home,options",
    211.312,
    3,
    21.417
  ],
  [
    "left,right,select,back,info",
    210.725,
    11,
    15.591
  ],
  [
    "up,down,left",
    210.597,
    13,
    14.154
  ],
  [
    "back,info,guide,home,ch_down",
    209.451,
    9,
    7.444
  ]
]

### 4. Route restoration is still dropping important states

High-priority unreachable states include diagnostics and parental-control screens:

[
  [
    "screen_41dfac938e",
    0.92,
    14,
    "Diagnostics \u2192 Receiver 1",
    "linear_menu"
  ],
  [
    "after_5bef615817",
    0.92,
    12,
    "Diagnostics \u2192 Settings",
    "linear_menu"
  ],
  [
    "after_d6e9db50e9",
    0.92,
    12,
    "Parental Control PIN Prompt \u2192 TV Activity",
    "linear_menu"
  ],
  [
    "before_9cfc68a81c",
    0.92,
    12,
    "Parental Control PIN Prompt \u2192 6hours",
    "grid_menu"
  ],
  [
    "before_2e22b1f79d",
    0.92,
    12,
    "Parental Control PIN Prompt \u2192 en = \u00b0 . ~ an) \u2014~ V3 ae iH . . ! 4 ' . a _. a , ne in , . 1 . \" A : ' i et oe ' ",
    "pin_prompt"
  ],
  [
    "before_250e530d3c",
    0.92,
    12,
    "Parental Control PIN Prompt \u2192 on | Parental Controls",
    "linear_menu"
  ],
  [
    "before_94e71e29d1",
    0.92,
    12,
    "Parental Control PIN Prompt \u2192 noo |.",
    "pin_prompt"
  ],
  [
    "before_5b0d9338c8",
    0.92,
    12,
    "Parental Control PIN Prompt \u2192 a =I ee | seceae pa ee ee ees",
    "linear_menu"
  ],
  [
    "screen_15df94bb01",
    0.92,
    10,
    "Diagnostics \u2192 Receiver 1",
    "linear_menu"
  ],
  [
    "screen_87a64e0a81",
    0.92,
    12,
    "Diagnostics \u2192 Receiver 1",
    "linear_menu"
  ],
  [
    "screen_67932a5776",
    0.92,
    12,
    "Diagnostics \u2192 Receiver 1",
    "linear_menu"
  ],
  [
    "after_6315586a8c",
    0.92,
    10,
    "Parental Control PIN Prompt \u2192 HEHES",
    "pin_prompt"
  ]
]

### 5. The crawler needs explicit feature missions

Humans do not just wander. They run missions:
- collect sys diagnostics
- inspect guide alignment
- channel surf
- check DVR timers/recordings
- inspect OnDemand shelves
- inspect PPV availability without buying
- verify parental blocking/PIN unlock

V19 adds a Channel Surf Lab and a sys-diagnostics bootstrap hook as the first concrete mission layer.
