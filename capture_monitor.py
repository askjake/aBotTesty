#!/usr/bin/env python3
"""Capture-card/stream monitor for the merged JAMboree Lite + active-video app.

The monitor is intentionally boring and sturdy:
- one background thread owns cv2.VideoCapture
- callers can ask for latest JPEG/frame/status without touching cv2 directly
- active-video is inferred from brightness + variance + motion + v19 health classifier
- capture source can be switched at runtime between local devices and RTSP/HTTP streams
"""
from __future__ import annotations

import logging
import os
import platform
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import cv2
import numpy as np

from video_health import classify_frame_signal

log = logging.getLogger("merged.capture")


_BACKEND_MAP = {
    "any": cv2.CAP_ANY,
    "dshow": getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY),
    "msmf": getattr(cv2, "CAP_MSMF", cv2.CAP_ANY),
    "v4l2": getattr(cv2, "CAP_V4L2", cv2.CAP_ANY),
    "ffmpeg": getattr(cv2, "CAP_FFMPEG", cv2.CAP_ANY),
}

# Common RTSP path patterns for Hi3520D and similar low-cost HDMI encoders.
# If the operator supplies only rtsp://host[:port], the monitor can probe these.
_RTSP_PATH_CANDIDATES = [
    "",           # root
    "/0",
    "/1",
    "/live/0/main",
    "/live0",
    "/stream1",
    "/ch0",
    "/main",
    "/h264",
]

_STREAM_PREFIXES = ("rtsp://", "rtmp://", "http://", "https://")


def is_stream_url(device: Any) -> bool:
    """Return True when a device specifier is a network/video stream URL."""
    return isinstance(device, str) and device.lower().startswith(_STREAM_PREFIXES)


def coerce_device_value(device: Any) -> int | str:
    """Normalize device values without breaking URLs.

    JSON/HTML forms tend to send local device indexes as strings. OpenCV expects
    integers for local indexes, but URLs and file paths must remain strings.
    """
    if isinstance(device, int):
        return device
    text = str(device).strip()
    if not text:
        return 0
    if is_stream_url(text):
        return text
    try:
        return int(text)
    except ValueError:
        return text


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
    backend_name: str = "unknown"
    brightness: float = 0.0
    variance: float = 0.0
    motion_score: float = 0.0
    fps_estimate: float = 0.0
    last_frame_age_s: Optional[float] = None
    last_frame_ts: Optional[float] = None
    signal_class: str = "unknown"
    active_reason: str = ""
    black_fraction: float = 0.0
    saturated_fraction: float = 0.0
    edge_density: float = 0.0
    colorbar_score: float = 0.0
    likely_black_screen: bool = False
    likely_color_bars: bool = False
    recommended_recovery: str = ""
    device: str = ""
    device_label: str = ""
    device_type: str = "local"  # local, rtsp, http, stream, file-ish
    rtsp_url: str = ""
    source_generation: int = 0


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
        jpeg_every_n_frames: int = 2,
        rtsp_reconnect_delay: float = 2.0,
        rtsp_tcp_transport: bool = True,
        source_label: str = "Configured input",
    ) -> None:
        self._lock = threading.RLock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._enabled = False
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_jpeg: Optional[bytes] = None
        self._prev_gray_small: Optional[np.ndarray] = None
        self._fps_window: list[float] = []
        self._source_generation = 0

        self.signal_min_brightness = float(signal_min_brightness)
        self.signal_min_variance = float(signal_min_variance)
        self.motion_threshold = float(motion_threshold)
        # v28: encode JPEG less often.  The capture card still runs at full rate,
        # but /video.mjpg can reuse the latest encoded JPEG.  This cuts CPU while
        # preserving crawler access to every raw latest frame.
        self.jpeg_every_n_frames = max(1, int(jpeg_every_n_frames or 1))
        self.rtsp_reconnect_delay = float(rtsp_reconnect_delay)
        self.rtsp_tcp_transport = bool(rtsp_tcp_transport)

        self.device: int | str = 0
        self.backend_name = "any"
        self.backend = cv2.CAP_ANY
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.source_label = str(source_label or "Configured input")
        self._is_stream = False
        self._status = VideoStatus()
        self._configure_source_locked(device=device, backend=backend, width=width, height=height, fps=fps, label=source_label)

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

    def switch_source(
        self,
        device: int | str,
        backend: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
        label: Optional[str] = None,
        start: bool = True,
    ) -> Dict[str, Any]:
        """Switch the active capture input without restarting Flask.

        Existing crawler/teacher objects keep calling monitor.get_frame(), so a
        single monitor instance is kept alive and only its underlying VideoCapture
        source is replaced.
        """
        with self._lock:
            was_running = self._running
            old_enabled = self._enabled
            self._enabled = False
            self._status.enabled = False
            self._status.status = "switching"
            self._release_locked()
            self._latest_frame = None
            self._latest_jpeg = None
            self._prev_gray_small = None
            self._fps_window = []
            self._configure_source_locked(
                device=device,
                backend=backend if backend is not None else self.backend_name,
                width=width if width is not None else self.width,
                height=height if height is not None else self.height,
                fps=fps if fps is not None else self.fps,
                label=label if label is not None else self.source_label,
            )
            self._enabled = bool(start or old_enabled)
            self._status.enabled = self._enabled
            if self._enabled:
                self._status.status = "starting"
            if self._enabled and not was_running:
                self._running = True
                self._status.running = True
                self._thread = threading.Thread(target=self._loop, name="CaptureMonitor", daemon=True)
                self._thread.start()
            return self.get_status()

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def get_jpeg(self) -> Optional[bytes]:
        # v29: the MJPEG route must never block behind capture-side health
        # analysis.  If the capture thread is holding the lock, serve the most
        # recent immutable JPEG reference rather than freezing the monitor page.
        if self._lock.acquire(blocking=False):
            try:
                return self._latest_jpeg
            finally:
                self._lock.release()
        return self._latest_jpeg

    def get_status(self) -> Dict[str, Any]:
        # Prefer a consistent locked status, but do not let /api/status stall the UI
        # if the capture loop is momentarily busy.
        acquired = self._lock.acquire(blocking=False)
        try:
            st = asdict(self._status)
            if self._status.last_frame_ts:
                st["last_frame_age_s"] = round(time.time() - self._status.last_frame_ts, 3)
            return st
        finally:
            if acquired:
                self._lock.release()

    def _device_type(self, device: int | str) -> str:
        if not isinstance(device, str):
            return "local"
        low = device.lower()
        if low.startswith("rtsp://"):
            return "rtsp"
        if low.startswith(("http://", "https://")):
            return "http"
        if low.startswith("rtmp://"):
            return "rtmp"
        return "stream" if "://" in low else "local"

    def _resolve_backend(self, backend: str, device: int | str) -> tuple[str, int]:
        name = str(backend or "any").lower().strip()
        if is_stream_url(device):
            # Network capture is dramatically more reliable through OpenCV/FFMPEG.
            name = "ffmpeg"
        code = _BACKEND_MAP.get(name, cv2.CAP_ANY)
        if platform.system().lower() != "windows" and name == "dshow":
            # Keeps Linux/macOS smoke tests from failing merely because DSHOW is Windows-only.
            code = cv2.CAP_ANY
        return name, code

    def _configure_source_locked(
        self,
        device: int | str,
        backend: str = "dshow",
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        label: str = "Configured input",
    ) -> None:
        self.device = coerce_device_value(device)
        self.backend_name, self.backend = self._resolve_backend(str(backend or "any"), self.device)
        self.width = int(width or 1280)
        self.height = int(height or 720)
        self.fps = int(fps or 30)
        self.source_label = str(label or self.source_label or "Configured input")
        self._is_stream = is_stream_url(self.device)
        self._source_generation += 1
        prior_open_count = getattr(self._status, "open_count", 0)
        self._status = VideoStatus(
            running=self._running,
            enabled=self._enabled,
            status="idle" if not self._enabled else "starting",
            device=str(self.device),
            device_label=self.source_label,
            device_type=self._device_type(self.device),
            rtsp_url=str(self.device) if self._device_type(self.device) == "rtsp" else "",
            backend_name=self.backend_name,
            backend=self.backend_name.upper(),
            open_count=prior_open_count,
            source_generation=self._source_generation,
        )

    def _release_locked(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                log.exception("capture release failed")
        self._cap = None

    def _open_stream_locked(self) -> bool:
        """Open an RTSP/HTTP stream with appropriate options and warm-up."""
        self._release_locked()
        device_url = str(self.device)

        if self.rtsp_tcp_transport and device_url.lower().startswith("rtsp://"):
            # OpenCV/FFMPEG reads this environment variable when opening streams.
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

        urls_to_try = [device_url]
        # If the base URL did not include a stream path, try common encoder paths.
        if device_url.lower().startswith("rtsp://") and device_url.rstrip("/").count("/") <= 2:
            base = device_url.rstrip("/")
            urls_to_try = []
            for path in _RTSP_PATH_CANDIDATES:
                candidate = f"{base}{path}" if path else base
                if candidate not in urls_to_try:
                    urls_to_try.append(candidate)

        last_error = ""
        for test_url in urls_to_try:
            log.debug("Trying stream input: %s", test_url)
            cap = cv2.VideoCapture(test_url, self.backend)
            if not cap.isOpened():
                last_error = f"cannot open stream: {test_url}"
                try:
                    cap.release()
                except Exception:
                    pass
                continue

            frame = None
            for _ in range(30):
                ok, maybe = cap.read()
                if ok and maybe is not None and maybe.size:
                    frame = maybe
                    break
                time.sleep(0.1)

            if frame is None:
                last_error = f"stream opened but returned no frames: {test_url}"
                try:
                    cap.release()
                except Exception:
                    pass
                continue

            self.device = test_url
            self._cap = cap
            self._status.device = str(test_url)
            if str(test_url).lower().startswith("rtsp://"):
                self._status.rtsp_url = str(test_url)
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
            log.info("Stream connected: %s (%sx%s)", test_url, frame.shape[1], frame.shape[0])
            return True

        self._status.status = "error"
        self._status.last_error = last_error or f"cannot open stream: {device_url}"
        log.warning("Failed to open stream input %s: %s", device_url, self._status.last_error)
        return False

    def _open_local_locked(self) -> bool:
        """Open a local capture device (V4L2/DSHOW/MSMF/etc)."""
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

    def _open_locked(self) -> bool:
        if self._is_stream:
            return self._open_stream_locked()
        return self._open_local_locked()

    def _store_frame_locked(self, frame: np.ndarray) -> None:
        now = time.time()
        self._latest_frame = frame
        next_frame_count = int(self._status.frame_count) + 1

        if next_frame_count % self.jpeg_every_n_frames == 0 or self._latest_jpeg is None:
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if ok:
                self._latest_jpeg = buf.tobytes()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
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
        self._status.width = int(frame.shape[1])
        self._status.height = int(frame.shape[0])
        health = classify_frame_signal(
            frame,
            motion_score=motion,
            min_brightness=self.signal_min_brightness,
            min_variance=self.signal_min_variance,
        )

        self._status.brightness = health.brightness
        self._status.variance = health.variance
        self._status.motion_score = round(motion, 2)
        self._status.fps_estimate = round(fps_estimate, 2)
        self._status.active = bool(health.active)
        self._status.status = health.signal_class
        self._status.signal_class = health.signal_class
        self._status.active_reason = health.reason
        self._status.black_fraction = health.black_fraction
        self._status.saturated_fraction = health.saturated_fraction
        self._status.edge_density = health.edge_density
        self._status.colorbar_score = health.colorbar_score
        self._status.likely_black_screen = health.likely_black_screen
        self._status.likely_color_bars = health.likely_color_bars
        self._status.recommended_recovery = health.recommended_recovery
        if motion >= self.motion_threshold and self._status.active and self._status.signal_class not in {"color_bars", "active_static_ui"}:
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
                time.sleep(self.rtsp_reconnect_delay if self._is_stream else 0.2)
                continue

            try:
                ok, frame = cap.read()
            except Exception as exc:
                with self._lock:
                    self._status.last_error = f"read exception: {exc}"
                    self._status.status = "error"
                    self._release_locked()
                time.sleep(self.rtsp_reconnect_delay if self._is_stream else 0.5)
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
                time.sleep(self.rtsp_reconnect_delay if self._is_stream else 1.0)
            else:
                time.sleep(0.08)
