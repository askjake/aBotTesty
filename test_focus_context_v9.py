#!/usr/bin/env python3
import cv2
import numpy as np

from focus_detector import detect_focus, draw_focus_overlay

img = np.zeros((720, 1280, 3), dtype=np.uint8)
img[:] = (18, 18, 24)
cv2.putText(img, "dish   Home   Guide   TV Viewing Options", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (235, 235, 235), 2)
cv2.putText(img, "TV Viewing Options", (90, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255, 255, 255), 2)
cv2.putText(img, "Closed Captioning", (130, 270), cv2.FONT_HERSHEY_SIMPLEX, 1.05, (245, 245, 245), 2)
cv2.putText(img, "Off", (850, 270), cv2.FONT_HERSHEY_SIMPLEX, 1.05, (245, 245, 245), 2)
cv2.rectangle(img, (110, 222), (995, 300), (0, 0, 255), 6)
cv2.putText(img, "Options   CC   Apps   Close", (80, 660), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)

focus = detect_focus(img)
overlay = draw_focus_overlay(img, focus)
assert overlay is not None and overlay.shape == img.shape
assert focus.get("found"), focus
assert focus.get("bbox"), focus
assert "ui_context" in focus, focus
assert focus.get("screen_title") or focus["ui_context"].get("screen_title"), focus
assert focus.get("tokens"), focus
print("FOCUS_CONTEXT_V9_OK", focus.get("screen_title"), focus.get("human_label"), focus.get("focus_role"), focus.get("context_confidence"))
