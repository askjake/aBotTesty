# v27 — PPV Nav + Banner Capture Dashboards

## Changes

- Added PPV Purchase Test Lab links across the primary app tabs/pages.
- Surf/dashboard rows now expose flattened live-banner capture fields:
  - `live_banner_program_title`
  - `live_banner_program_description`
  - `live_banner_program_time_range`
  - `live_banner_channel_number`
  - `live_banner_channel_code`
  - `live_banner_displayed_time`
  - `live_banner_logo_text`
  - `live_banner_valid`
  - `live_banner_validation_score`
  - `live_banner_validation_flags`
- Channel catalog rows now keep the latest observed live-banner facts:
  - `latest_live_banner_program_title`
  - `latest_live_banner_program_description`
  - `latest_live_banner_program_time_range`
  - `latest_live_banner_channel_number`
  - `latest_live_banner_channel_code`
  - `latest_live_banner_displayed_time`
  - `latest_live_banner_logo_text`
  - `latest_live_banner_valid`
  - `latest_live_banner_score`
  - `latest_live_banner_flags`
  - `banner_valid_pct`
- Exec/Engineering dashboards now display banner validity and banner-captured program/channel facts.
- Superset export now includes the banner capture fields in `stb_channel_surf` and `stb_observed_channel_catalog`, plus the helper SQL view exposes latest banner fields.

## Why

The channel surf catalog should distinguish general metadata from the most trustworthy live-banner capture. This makes it obvious which rows were validated from the Live TV banner and which need another scan.
