#!/usr/bin/env python3
import cv2
import numpy as np
from focus_detector import detect_focus, draw_focus_overlay

img = np.zeros((360, 640, 3), dtype=np.uint8)
img[:] = (25, 35, 45)
# red parallelogram-ish focus outline
pts = np.array([[120, 110], [360, 110], [398, 190], [150, 190]], dtype=np.int32)
cv2.polylines(img, [pts], True, (0, 0, 255), 8)
cv2.putText(img, "SETTINGS", (155, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
obs = detect_focus(img)
assert obs["found"], obs
assert obs["confidence"] > 0.25, obs
assert obs["bbox"] and obs["bbox"][2] > 150, obs
ov = draw_focus_overlay(img, obs)
assert ov.shape == img.shape
print("FOCUS_DETECTOR_V8_OK", obs["bbox"], obs["confidence"], obs["region"])
