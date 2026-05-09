#!/usr/bin/env python3
"""Capture-card monitor for the merged JAMboree Lite + active-video app.

The monitor is intentionally boring and sturdy:
- one background thread owns cv2.VideoCapture
- callers can ask for latest JPEG/frame/status without touching cv2 directly
- active-video is inferred from brightness + variance + motion
"""
from __future__ import annotations

import logging
import platform
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("merged.capture")


_BACKEND_MAP = {
    "any": cv2.CAP_ANY,
    "dshow": getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY),
    "msmf": getattr(cv2, "CAP_MSMF", cv2.CAP_ANY),
    "v4l2": getattr(cv2, "CAP_V4L2", cv2.CAP_ANY),
}


@dataclass
class VideoStatus:
    running: bool = False
    enabled: bool = False
    active: bool = False
    status: str = "idle"
    last_error: str = ""
    frame_count: int = 0
    open_count: int = 0
    fail_streak: int = 0
    width: int = 0
    height: int = 0
    backend: str = "UNKNOWN"
    brightness: float = 0.0
    variance: float = 0.0
    motion_score: float = 0.0
    fps_estimate: float = 0.0
    last_frame_age_s: Optional[float] = None
    last_frame_ts: Optional[float] = None


class CaptureMonitor:
    def __init__(
        self,
        device: int | str = 1,
        backend: str = "dshow",
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        signal_min_brightness: float = 8.0,
        signal_min_variance: float = 25.0,
        motion_threshold: float = 2.0,
    ) -> None:
        self.device = device
        self.backend_name = backend.lower()
        self.backend = _BACKEND_MAP.get(self.backend_name, cv2.CAP_ANY)
        if platform.system().lower() != "windows" and self.backend_name == "dshow":
            # Keeps Linux/macOS smoke tests from failing merely because DSHOW is Windows-only.
            self.backend = cv2.CAP_ANY
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.signal_min_brightness = float(signal_min_brightness)
        self.signal_min_variance = float(signal_min_variance)
        self.motion_threshold = float(motion_threshold)

        self._lock = threading.RLock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._enabled = False
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_jpeg: Optional[bytes] = None
        self._prev_gray_small: Optional[np.ndarray] = None
        self._status = VideoStatus()
        self._fps_window: list[float] = []

    def start(self) -> None:
        with self._lock:
            self._enabled = True
            self._status.enabled = True
            if self._running:
                self._status.status = "streaming" if self._cap is not None else "starting"
                return
            self._running = True
            self._status.running = True
            self._status.status = "starting"
            self._thread = threading.Thread(target=self._loop, name="CaptureMonitor", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._enabled = False
            self._status.enabled = False
            self._status.status = "idle"
            self._release_locked()

    def shutdown(self) -> None:
        with self._lock:
            self._enabled = False
            self._running = False
            self._status.enabled = False
            self._status.running = False
            self._release_locked()

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def get_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            st = asdict(self._status)
            if self._status.last_frame_ts:
                st["last_frame_age_s"] = round(time.time() - self._status.last_frame_ts, 3)
            return st

    def _release_locked(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                log.exception("capture release failed")
        self._cap = None

    def _open_locked(self) -> bool:
        self._release_locked()
        cap = cv2.VideoCapture(self.device, self.backend)
        if not cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
            self._status.status = "error"
            self._status.last_error = f"cannot open capture device={self.device!r} backend={self.backend_name}"
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        frame = None
        for _ in range(20):
            ok, maybe = cap.read()
            if ok and maybe is not None and maybe.size:
                frame = maybe
                break
            time.sleep(0.05)

        if frame is None:
            try:
                cap.release()
            except Exception:
                pass
            self._status.status = "error"
            self._status.last_error = f"capture device opened but returned no frame: {self.device!r}"
            return False

        self._cap = cap
        self._status.open_count += 1
        self._status.fail_streak = 0
        self._status.status = "streaming"
        self._status.width = int(frame.shape[1])
        self._status.height = int(frame.shape[0])
        try:
            self._status.backend = cap.getBackendName()
        except Exception:
            self._status.backend = self.backend_name.upper()
        self._store_frame_locked(frame)
        return True

    def _store_frame_locked(self, frame: np.ndarray) -> None:
        now = time.time()
        self._latest_frame = frame

        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if ok:
            self._latest_jpeg = buf.tobytes()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        variance = float(np.var(gray))
        small = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
        motion = 0.0
        if self._prev_gray_small is not None:
            motion = float(np.mean(cv2.absdiff(small, self._prev_gray_small)))
        self._prev_gray_small = small

        self._fps_window.append(now)
        cutoff = now - 3.0
        self._fps_window = [t for t in self._fps_window if t >= cutoff]
        fps_estimate = 0.0 if len(self._fps_window) < 2 else (len(self._fps_window) - 1) / max(0.001, self._fps_window[-1] - self._fps_window[0])

        self._status.frame_count += 1
        self._status.last_frame_ts = now
        self._status.brightness = round(brightness, 2)
        self._status.variance = round(variance, 2)
        self._status.motion_score = round(motion, 2)
        self._status.fps_estimate = round(fps_estimate, 2)
        self._status.active = bool(
            brightness >= self.signal_min_brightness
            and variance >= self.signal_min_variance
        )
        self._status.status = "active" if self._status.active else "no_signal_or_black"
        if motion >= self.motion_threshold:
            self._status.status = "active_motion"

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
                enabled = self._enabled
                cap = self._cap
            if not enabled:
                time.sleep(0.2)
                continue
            if cap is None:
                with self._lock:
                    self._open_locked()
                time.sleep(0.2)
                continue

            try:
                ok, frame = cap.read()
            except Exception as exc:
                with self._lock:
                    self._status.last_error = f"read exception: {exc}"
                    self._status.status = "error"
                    self._release_locked()
                time.sleep(0.5)
                continue

            if ok and frame is not None and frame.size:
                with self._lock:
                    self._status.fail_streak = 0
                    self._store_frame_locked(frame)
                time.sleep(0.005)
                continue

            with self._lock:
                self._status.fail_streak += 1
                streak = self._status.fail_streak
                self._status.status = "read_fail"
            if streak >= 8:
                with self._lock:
                    self._status.status = "reconnecting"
                    self._release_locked()
                time.sleep(1.0)
            else:
                time.sleep(0.08)
