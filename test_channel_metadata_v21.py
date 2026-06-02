#!/usr/bin/env python3
import cv2
from channel_metadata import extract_channel_metadata, choose_best_metadata
from focus_detector import detect_focus

LIVE = "/mnt/data/8f6523ff-64f8-4272-834a-1748014670b2.png"
GUIDE = "/mnt/data/32a1da10-f5b3-469a-ab2a-d54ed4d09883.png"
INFO = "/mnt/data/3c1119e0-510e-4819-864f-7050b49006f3.png"


def assert_contains(value, expected):
    assert expected.lower() in str(value or "").lower(), f"expected {expected!r} in {value!r}"


def main():
    live_img = cv2.imread(LIVE)
    guide_img = cv2.imread(GUIDE)
    info_img = cv2.imread(INFO)
    assert live_img is not None and guide_img is not None and info_img is not None

    live = extract_channel_metadata(live_img, screen_hint="live_banner")
    assert live["screen_type"] == "live_banner"
    assert live["channel_number"] == "111", live
    assert live["channel_code"] == "MAGN", live
    assert_contains(live["program_title"], "Beachfront Bargain")
    assert_contains(live["displayed_datetime_text"], "12:36")

    gf = detect_focus(guide_img, None)
    guide = extract_channel_metadata(guide_img, focus=gf, screen_hint="guide")
    assert guide["screen_type"] == "guide"
    assert guide["channel_number"] == "114", guide
    assert_contains(guide["program_title"], "How I Met")
    assert_contains(guide["displayed_datetime_text"], "12:39")

    info = extract_channel_metadata(info_img, screen_hint="info")
    assert info["screen_type"] == "info"
    assert info["channel_number"] == "117", info
    assert info["channel_code"] == "POP", info
    assert_contains(info["program_title"], "Schitt")
    assert_contains(info["displayed_datetime_text"], "12:42")

    merged = choose_best_metadata([live, guide, info])
    assert merged["channel_number"] == "114", merged  # guide focus indicates highlighted channel destination
    assert merged["channel_code"] == "POP" or merged["channel_code"] == "MAGN" or merged["channel_code"] == "", merged
    assert merged["program_title"], merged
    print("CHANNEL_METADATA_V21_OK")

if __name__ == "__main__":
    main()
