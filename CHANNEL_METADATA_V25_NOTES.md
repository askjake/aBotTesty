# v25 Hyphenated Channel + Banner Validation

Adds support for DISH hyphenated/subchannel numbers such as `CAROL 092-14` and validates live-banner metadata before promoting it into Channel Surf dashboards.

## Key changes

- Channel numbers now accept `NNN-NN` forms.
- Live banner metadata carries `banner_valid`, `banner_validation_score`, and `banner_validation_flags`.
- Channel Surf observations flag invalid banners.
- Exec/Eng/Superset dashboards include live-banner validation metrics.
- Observed channel catalog keeps hyphenated channel numbers and sorts by base/suffix.
