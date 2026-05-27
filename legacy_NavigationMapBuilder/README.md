# Navigation Map Builder

Automatic STB channel navigation, screenshot capture, and tune verification.

## Architecture

    sgs_server.py  (:8080)   SGS gateway — screen state, key press, screenshot
    tune_verify.py           Tune verification library
    run_nav.py               Basic 3-step CH_UP navigation run
    run_full_test.py         11-test regression suite
    nav_maps/                Output: screenshots + test_results.json

## Quick Start

    # Start SGS server (auto-starts on login via Scheduled Task)
    schtasks /run /tn "SGS_Server"

    # Verify it is running
    netstat -ano | findstr ":8080"

    # Run tune verification self-test
    python tune_verify.py

    # Run full regression suite
    python run_full_test.py

## SGS API

    GET  /screen              Returns live STB state
                              {"input":6, "channel":206, "signal":true, ...}

    POST /key                 Send a key press
                              Body: {"key": "CH_UP", "input": 6}
                              Keys: CH_UP, CH_DOWN, CH_<number>

    GET  /screenshot          Returns PNG screenshot
                              Channel-encoded color (no timestamp)
                              Same channel = identical pixels every time

## tune_verify API

    from tune_verify import verified_tune, get_screen

    result = verified_tune("CH_UP", expected_channel=207)
    # result = {
    #   "key":             "CH_UP",
    #   "before_ch":       206,
    #   "after_ch":        207,
    #   "diff_px":         920207,
    #   "tune_confirmed":  True,
    #   "channel_correct": True,
    #   "pass":            True
    # }

## Verified Thresholds

    Noise floor:      0 px   (same channel, deterministic)
    Signal:     920,207 px   (adjacent channel, 66% of 1280x720)
    Threshold:    1,000 px   (920x safety margin)

## Round-Trip Proof (MD5)

    CH 206 baseline   5336507c
    CH 207 up1        4febafda
    CH 208 up2        1b83885d
    CH 209 up3        717ac39e
    CH 208 down1      1b83885d  <- matches up2
    CH 207 down2      4febafda  <- matches up1
    CH 206 down3      5336507c  <- matches baseline

## Wiring Real STB Hardware

Edit _apply_key() in sgs_server.py:

    def _apply_key(key):
        # Option A: IR blaster over serial
        import serial
        ir = serial.Serial("/dev/ttyUSB0", 9600)
        ir.write(f"{key}\n".encode())

        # Option B: HTTP IR blaster (Broadlink, iTach, etc.)
        import requests
        requests.post("http://IR_BLASTER_IP/send", json={"key": key})

        # Option C: STB REST API
        requests.post(f"http://STB_IP/api/key/{key}")

        # Read real channel back from STB
        _state["channel"] = get_real_channel_from_stb()

All other files (tune_verify.py, run_full_test.py) require no changes.

## Test Results (last run)

    11/11 passed
    CH_UP x3:      206->207->208->209  all PASS
    CH_DOWN x3:    209->208->207->206  all PASS  (round-trip)
    Direct tune:   200, 210, 220, 230  all PASS
    Sweep 200-230: 7 channels          all PASS
