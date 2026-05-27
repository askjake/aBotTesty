# v21 Channel Metadata Analysis

The v20 Channel Surf parser used a broad text-regex fallback over combined live/info/guide OCR. That caused false associations: phone numbers, program times, random OCR artifacts, and unrelated guide rows could become the channel name or program title.

v21 changes this to geometry-first parsing:

1. Live TV banner reads the top overlay by stable ROIs.
2. Guide reads the red-focused grid tile, the selected channel row, and the right-side detail panel separately.
3. TV Show/Info reads the title, episode/details, channel block, and clock block separately.
4. The merged observation prefers field-specific sources rather than whichever regex happened to match first.

The key human insight is that a viewer does not read the whole screen as one paragraph. A viewer knows where the channel number lives, where the program title lives, and which guide row focus will tune to.
