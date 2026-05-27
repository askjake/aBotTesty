# v30 PPV / On Demand Pricing and Purchase Limits

This release adds purchase-price extraction and purchase guardrails to the PPV / On Demand lab.

## New behavior

- Recognizes dollar amounts such as `$24.99` from Rent / purchase-option screens.
- Recognizes free assets from text such as `FREE`, `Free On Demand`, or `Available On Demand` without a dollar amount.
- Maintains per-session purchase limits in `crawler_data/ppv_purchase_limits.json`.
- Logs purchase analysis, limit blocks, and confirmed purchase records in `crawler_data/ppv_purchase_test_log.json`.
- Adds PPV purchase/price rows to Exec, Engineering, and Superset dashboards.
- Adds an operator-editable On Demand navigation sequence on `/ppv`.

## Limits

- Individual limit: maximum allowed for a single asset.
- Session limit: maximum allowed total spend for the current PPV test session.
- `0` means free-only.
- `unlimited` means no cap.

## Safety

The PPV workflow still requires explicit arming and `confirm_purchase=true`. Final confirmation requires `final_confirm=true`. If a screen already looks like a purchase-confirmation dialog, v30 refuses to press SELECT unless final confirmation is explicitly requested.
