#!/usr/bin/env python3
from __future__ import annotations
import platform
import cv2

backend = cv2.CAP_DSHOW if platform.system().lower() == "windows" else cv2.CAP_ANY
print("Scanning video capture devices...")
for i in range(10):
    cap = cv2.VideoCapture(i, backend)
    opened = cap.isOpened()
    ret, frame = (False, None)
    if opened:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        for _ in range(10):
            ret, frame = cap.read()
            if ret and frame is not None and frame.size:
                break
    if opened and ret and frame is not None:
        print(f"  Device {i}: OK frame={frame.shape[1]}x{frame.shape[0]}")
    elif opened:
        print(f"  Device {i}: opens but produced no frame")
    else:
        print(f"  Device {i}: not available")
    cap.release()
print("Done.")
