#!/usr/bin/env python3
"""Video signal health classifier for the capture monitor.

Provides frame-level signal classification to detect:
- Active video (normal content)
- Black screen (no signal or blanked output)
- Color bars (test pattern)
- Frozen/static frames
- No signal
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class FrameHealth:
    """Result of classify_frame_signal()."""
    active: bool = False
    signal_class: str = "unknown"
    reason: str = ""
    brightness: float = 0.0
    variance: float = 0.0
    black_fraction: float = 0.0
    saturated_fraction: float = 0.0
    edge_density: float = 0.0
    colorbar_score: float = 0.0
    likely_black_screen: bool = False
    likely_color_bars: bool = False
    recommended_recovery: str = ""


def classify_frame_signal(
    frame: np.ndarray,
    motion_score: float = 0.0,
    min_brightness: float = 8.0,
    min_variance: float = 25.0,
) -> FrameHealth:
    """Classify a video frame's signal health.

    Returns a FrameHealth dataclass with signal classification and metrics.
    """
    h = FrameHealth()

    if frame is None or frame.size == 0:
        h.signal_class = "no_frame"
        h.reason = "empty or null frame"
        return h

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

    # Basic stats
    h.brightness = round(float(np.mean(gray)), 2)
    h.variance = round(float(np.var(gray)), 2)

    # Black/saturated pixel fractions
    total_pixels = gray.size
    h.black_fraction = round(float(np.sum(gray < 10)) / total_pixels, 4)
    h.saturated_fraction = round(float(np.sum(gray > 245)) / total_pixels, 4)

    # Edge density (indicator of actual content vs flat signal)
    edges = cv2.Canny(gray, 50, 150)
    h.edge_density = round(float(np.sum(edges > 0)) / total_pixels, 4)

    # Simple color bar detection (look for vertical bands of uniform color)
    h.colorbar_score = _estimate_colorbar_score(frame) if len(frame.shape) == 3 else 0.0

    # Classification logic
    if h.black_fraction > 0.95:
        h.signal_class = "black_screen"
        h.likely_black_screen = True
        h.reason = f"black_fraction={h.black_fraction:.2%}"
        h.recommended_recovery = "check_input_signal"
    elif h.brightness < min_brightness:
        h.signal_class = "no_signal_or_black"
        h.likely_black_screen = True
        h.reason = f"brightness={h.brightness:.1f} < {min_brightness}"
        h.recommended_recovery = "check_input_signal"
    elif h.variance < min_variance:
        h.signal_class = "flat_signal"
        h.reason = f"variance={h.variance:.1f} < {min_variance}"
        h.recommended_recovery = "verify_source_output"
    elif h.colorbar_score > 0.6:
        h.signal_class = "color_bars"
        h.likely_color_bars = True
        h.active = False
        h.reason = f"colorbar_score={h.colorbar_score:.2f}"
        h.recommended_recovery = "waiting_for_content"
    elif motion_score >= 2.0:
        h.signal_class = "active_motion"
        h.active = True
        h.reason = f"motion={motion_score:.1f}, brightness={h.brightness:.1f}"
    else:
        h.signal_class = "active"
        h.active = True
        h.reason = f"brightness={h.brightness:.1f}, variance={h.variance:.1f}"

    return h


def _estimate_colorbar_score(frame: np.ndarray) -> float:
    """Estimate likelihood that the frame shows color bars (0.0 - 1.0).

    Color bars have strong vertical uniformity with distinct horizontal bands.
    """
    if frame is None or frame.size == 0 or len(frame.shape) < 3:
        return 0.0

    h, w = frame.shape[:2]
    if h < 10 or w < 10:
        return 0.0

    # Sample vertical columns and check uniformity
    # True color bars have very low vertical variance but high horizontal variance
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].astype(float)

    # Vertical variance (should be low for color bars)
    col_samples = [w // 8, w // 4, w // 2, 3 * w // 4, 7 * w // 8]
    vert_vars = []
    for col in col_samples:
        if col < w:
            vert_vars.append(float(np.var(hue[:, col])))

    avg_vert_var = np.mean(vert_vars) if vert_vars else 1000.0

    # Horizontal variance at middle row (should be high for color bars)
    mid_row = h // 2
    horiz_var = float(np.var(hue[mid_row, :]))

    # Color bars: low vertical var + high horizontal var
    if avg_vert_var < 50 and horiz_var > 200:
        return min(1.0, horiz_var / (avg_vert_var + 1.0) / 100.0)

    return 0.0
