# v24 Trusted Channel Metadata Guard

Problem fixed: broad OCR/legacy `program_guess` fields were polluting Channel Surf dashboards with bogus titles such as `ee panes site`, repeated OCR fragments, and ad/video texture text.

Changes:

- Channel metadata merge now uses trusted screen-specific regions only.
- Noisy program titles are rejected before being stored as `program_title_guess`.
- Legacy blob-level `program_guess` is quarantined in dashboards.
- Dashboard channel catalogs now prefer `live_metadata`, `info_metadata`, `guide_metadata`, and `best_metadata` fields over old OCR soup.
- Rejected old rows are flagged with `dashboard_rejected_legacy_program_guess` or `metadata_rejected_noisy_program_title`.
- Guide metadata now has a local red-focus fallback and a stronger displayed-time crop.

Expected behavior:

- Old dirty historical rows will show blank latest program titles instead of false titles.
- New scans should repopulate the channel catalog with trusted titles from live/info/guide regions.
- Channel/program accuracy should recover without disabling v23 region-first crawler perception.
