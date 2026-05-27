#!/usr/bin/env python3
"""Video signal health classification for STB capture frames.

The old monitor used only brightness + variance. That is too blunt for the
current lab because a valid input may be static/color bars, while a true black
screen usually means the STB/video path is misbehaving.

This module classifies frames into human-meaningful signal states:
  - active_video / active_static_ui
  - color_bars
  - black_screen
  - blank_or_no_signal
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import cv2
import numpy as np


@dataclass
class VideoHealth:
    signal_class: str
    active: bool
    reason: str
    brightness: float
    variance: float
    motion_score: float = 0.0
    black_fraction: float = 0.0
    white_fraction: float = 0.0
    saturated_fraction: float = 0.0
    bright_saturated_fraction: float = 0.0
    edge_density: float = 0.0
    colorbar_score: float = 0.0
    likely_black_screen: bool = False
    likely_color_bars: bool = False
    likely_static_ui: bool = False
    recommended_recovery: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _edge_density(gray: np.ndarray) -> float:
    small = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(small, 70, 150)
    return float(np.mean(edges > 0))


def _colorbar_score(frame: np.ndarray) -> float:
    """Detect classic vertical color bars or solid-color test patterns.

    This is intentionally heuristic. We look for high saturation, several
    distinct vertical-band colors, and relatively stable color inside bands.
    """
    if frame is None or not frame.size:
        return 0.0
    h, w = frame.shape[:2]
    roi = frame[int(h * 0.12): int(h * 0.88), int(w * 0.05): int(w * 0.95)]
    if roi.size == 0:
        return 0.0

    # Downsample heavily so this is cheap in the monitor loop.
    small = cv2.resize(roi, (96, 48), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    sat = float(np.mean(hsv[:, :, 1] > 90))
    val = float(np.mean(hsv[:, :, 2] > 70))
    if sat < 0.28 or val < 0.30:
        return 0.0

    # Average hue per vertical band. Color bars have multiple distinct hue bands.
    bands = 8
    hues = []
    band_stability = []
    for i in range(bands):
        x1 = int(i * small.shape[1] / bands)
        x2 = int((i + 1) * small.shape[1] / bands)
        band = hsv[:, x1:x2, :]
        mask = (band[:, :, 1] > 90) & (band[:, :, 2] > 60)
        if np.mean(mask) < 0.20:
            continue
        hues.append(float(np.median(band[:, :, 0][mask])))
        band_stability.append(float(np.std(band[:, :, 0][mask])))

    if len(hues) < 4:
        return 0.0

    # Count distinct hue clusters. Hue wraps at 180 in OpenCV HSV; use coarse bins.
    bins = {int(h // 15) for h in hues}
    distinct = min(1.0, len(bins) / 6.0)
    stable = 1.0 - min(1.0, (float(np.mean(band_stability)) if band_stability else 90.0) / 55.0)
    return round(max(0.0, min(1.0, 0.55 * sat + 0.30 * distinct + 0.15 * stable)), 4)


def classify_frame_signal(
    frame: np.ndarray,
    motion_score: float = 0.0,
    min_brightness: float = 8.0,
    min_variance: float = 25.0,
) -> VideoHealth:
    if frame is None or not getattr(frame, "size", 0):
        return VideoHealth(
            signal_class="no_frame",
            active=False,
            reason="no frame available",
            brightness=0.0,
            variance=0.0,
            motion_score=float(motion_score or 0.0),
            recommended_recovery="reopen_capture",
        )

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    brightness = float(np.mean(gray))
    variance = float(np.var(gray))
    black_fraction = float(np.mean(gray < 18))
    white_fraction = float(np.mean(gray > 240))
    saturated_fraction = float(np.mean(hsv[:, :, 1] > 100))
    bright_saturated_fraction = float(np.mean((hsv[:, :, 1] > 90) & (hsv[:, :, 2] > 80)))
    edges = _edge_density(gray)
    bars = _colorbar_score(frame)

    # True black: this is not "input inactive" in this lab. It is an STB/video
    # output defect that should trigger channel recovery and be logged.
    if brightness < max(6.0, min_brightness) or black_fraction > 0.92:
        return VideoHealth(
            signal_class="black_screen",
            active=False,
            reason="mostly black frame; input exists but STB/video output is likely bad",
            brightness=round(brightness, 2),
            variance=round(variance, 2),
            motion_score=round(float(motion_score or 0.0), 2),
            black_fraction=round(black_fraction, 4),
            white_fraction=round(white_fraction, 4),
            saturated_fraction=round(saturated_fraction, 4),
            bright_saturated_fraction=round(bright_saturated_fraction, 4),
            edge_density=round(edges, 5),
            colorbar_score=bars,
            likely_black_screen=True,
            recommended_recovery="try_ch_up_ch_down_then_live",
        )

    # Color bars are a valid active input/capture condition in this lab.
    if bars >= 0.56 or (saturated_fraction > 0.55 and variance > 450):
        return VideoHealth(
            signal_class="color_bars",
            active=True,
            reason="high-saturation test-pattern/color-bar-like frame; treat input as active",
            brightness=round(brightness, 2),
            variance=round(variance, 2),
            motion_score=round(float(motion_score or 0.0), 2),
            black_fraction=round(black_fraction, 4),
            white_fraction=round(white_fraction, 4),
            saturated_fraction=round(saturated_fraction, 4),
            bright_saturated_fraction=round(bright_saturated_fraction, 4),
            edge_density=round(edges, 5),
            colorbar_score=bars,
            likely_color_bars=True,
        )

    # Static menus/guide screens often have little motion but are absolutely active.
    if variance >= min_variance or edges > 0.015 or saturated_fraction > 0.035:
        return VideoHealth(
            signal_class="active_static_ui" if float(motion_score or 0.0) < 0.5 else "active_video",
            active=True,
            reason="visible non-black content with enough structure/color",
            brightness=round(brightness, 2),
            variance=round(variance, 2),
            motion_score=round(float(motion_score or 0.0), 2),
            black_fraction=round(black_fraction, 4),
            white_fraction=round(white_fraction, 4),
            saturated_fraction=round(saturated_fraction, 4),
            bright_saturated_fraction=round(bright_saturated_fraction, 4),
            edge_density=round(edges, 5),
            colorbar_score=bars,
            likely_static_ui=float(motion_score or 0.0) < 0.5,
        )

    return VideoHealth(
        signal_class="blank_or_no_signal",
        active=False,
        reason="low structure/color; capture may be blank/no signal",
        brightness=round(brightness, 2),
        variance=round(variance, 2),
        motion_score=round(float(motion_score or 0.0), 2),
        black_fraction=round(black_fraction, 4),
        white_fraction=round(white_fraction, 4),
        saturated_fraction=round(saturated_fraction, 4),
        bright_saturated_fraction=round(bright_saturated_fraction, 4),
        edge_density=round(edges, 5),
        colorbar_score=bars,
        recommended_recovery="recheck_capture_or_try_live",
    )
