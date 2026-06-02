#!/usr/bin/env python3
"""Focus/highlight perception for Dish/STB UI screens.

This generalizes the red-highlight logic from Jake's aBitTesty focus scripts.
It detects the red focus parallelogram/rectangle, OCRs the focused region and
nearby context, and returns a compact perception payload that can be embedded
inside crawler states and transitions.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("merged.focus")


@dataclass
class FocusObservation:
    found: bool = False
    confidence: float = 0.0
    bbox: Optional[List[int]] = None  # x,y,w,h
    bbox_norm: Optional[List[float]] = None
    center_norm: Optional[List[float]] = None
    corners: List[List[int]] = field(default_factory=list)
    area: float = 0.0
    aspect: float = 0.0
    red_density: float = 0.0
    contour_vertices: int = 0
    focus_text: str = ""
    context_text: str = ""
    label_text: str = ""
    tokens: List[str] = field(default_factory=list)
    row_guess: Optional[int] = None
    col_guess: Optional[int] = None
    region: str = ""
    warning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_STOP = {"the", "and", "for", "you", "your", "are", "with", "this", "that", "press", "select"}


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9]{2,}", str(text or "").lower())
    return sorted(set(w for w in words if w not in _STOP))[:80]


def red_focus_mask(bgr: np.ndarray) -> np.ndarray:
    """Strict-ish red mask copied from prior focus scripts, with cleanup.

    Dish focus borders are usually saturated red; this catches hue wraparound at
    both ends of HSV. Morphological close/dilate connects broken parallelogram
    borders so contours become usable.
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array((0, 120, 120)), np.array((12, 255, 255)))
    m2 = cv2.inRange(hsv, np.array((160, 120, 120)), np.array((180, 255, 255)))
    mask = cv2.bitwise_or(m1, m2)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def _safe_crop(frame: np.ndarray, rect: Tuple[int, int, int, int], pad: int = 0) -> np.ndarray:
    x, y, w, h = rect
    H, W = frame.shape[:2]
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(W, x + w + pad)
    y2 = min(H, y + h + pad)
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


def _ocr_image(img: np.ndarray, pytesseract_mod: Any = None, psm: int = 6, whitelist: Optional[str] = None) -> str:
    if img is None or not getattr(img, "size", 0):
        return ""
    if pytesseract_mod is None:
        try:
            import pytesseract as pytesseract_mod  # type: ignore
        except Exception:
            return ""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        # TV UI text is low-res; upscale + CLAHE improves OCR significantly.
        scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        scaled = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(scaled)
        scaled = cv2.bilateralFilter(scaled, 5, 35, 35)
        _, bw = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cfg = f"--oem 3 --psm {int(psm)}"
        if whitelist:
            cfg += f" -c tessedit_char_whitelist={whitelist}"
        return " ".join(pytesseract_mod.image_to_string(bw, config=cfg).split())[:1000]
    except Exception as exc:
        log.debug("focus OCR failed: %s", exc)
        return ""


def detect_focus(frame: np.ndarray, pytesseract_mod: Any = None) -> Dict[str, Any]:
    if frame is None or not getattr(frame, "size", 0):
        return FocusObservation(found=False, warning="empty frame").to_dict()

    H, W = frame.shape[:2]
    mask = red_focus_mask(frame)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best: Optional[Dict[str, Any]] = None

    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w <= 0 or h <= 0:
            continue
        area = float(cv2.contourArea(c))
        bbox_area = float(w * h)
        aspect = float(w / h)
        # Avoid tiny red logos and huge whole-frame effects. Keep very wide focus bars possible.
        if area < 250 or bbox_area < 650 or bbox_area > 0.45 * W * H:
            continue
        if not (0.25 <= aspect <= 9.0):
            continue
        roi_mask = mask[y:y+h, x:x+w]
        red_density = float(np.mean(roi_mask > 0))
        if red_density < 0.035:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.035 * peri, True)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect).astype(int).tolist()
        # Score favors large, dense, quadrilateral-ish, non-noisy red borders.
        quad_bonus = 0.18 if 4 <= len(approx) <= 8 else 0.0
        density_score = min(1.0, red_density * 4.5)
        area_score = min(1.0, bbox_area / max(1.0, W * H * 0.10))
        score = 0.42 * area_score + 0.40 * density_score + quad_bonus
        # Focus is rarely at extreme outer border; mild center preference only.
        cx = (x + w / 2) / W
        cy = (y + h / 2) / H
        if 0.02 < cx < 0.98 and 0.02 < cy < 0.98:
            score += 0.05
        if best is None or score > best["score"]:
            best = {
                "score": score,
                "bbox": (x, y, w, h),
                "area": area,
                "aspect": aspect,
                "red_density": red_density,
                "corners": box,
                "vertices": int(len(approx)),
            }

    if not best:
        return FocusObservation(found=False, warning="red focus not detected").to_dict()

    x, y, w, h = best["bbox"]
    # Crop the focus and surrounding contextual regions. The earlier scripts OCR'd
    # the label below the highlight; keep that, and add a larger local context crop.
    focus_crop = _safe_crop(frame, (x, y, w, h), pad=6)
    label_rect = (x, y + h + int(0.04 * h), w, int(0.65 * h))
    label_crop = _safe_crop(frame, label_rect, pad=4)
    context_crop = _safe_crop(frame, (x - int(0.30 * w), y - int(0.40 * h), int(1.60 * w), int(2.00 * h)), pad=8)

    label_text = _ocr_image(label_crop, pytesseract_mod, psm=7, whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -_&:+./")
    focus_text = _ocr_image(focus_crop, pytesseract_mod, psm=6)
    context_text = _ocr_image(context_crop, pytesseract_mod, psm=6)
    all_text = " ".join(t for t in [focus_text, label_text, context_text] if t)

    cx = x + w / 2.0
    cy = y + h / 2.0
    row_guess = int(min(5, max(0, cy / max(1, H) * 5)))
    col_guess = int(min(7, max(0, cx / max(1, W) * 7)))
    if cy < H * 0.22:
        region = "top/nav"
    elif cy > H * 0.78:
        region = "bottom/action"
    elif cx < W * 0.25:
        region = "left-pane"
    elif cx > W * 0.74:
        region = "right-pane"
    else:
        region = "center-grid"

    obs = FocusObservation(
        found=True,
        confidence=round(max(0.0, min(1.0, best["score"])), 4),
        bbox=[int(x), int(y), int(w), int(h)],
        bbox_norm=[round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4)],
        center_norm=[round(cx / W, 4), round(cy / H, 4)],
        corners=[[int(a), int(b)] for a, b in best["corners"]],
        area=round(float(best["area"]), 2),
        aspect=round(float(best["aspect"]), 3),
        red_density=round(float(best["red_density"]), 4),
        contour_vertices=int(best["vertices"]),
        focus_text=focus_text,
        context_text=context_text,
        label_text=label_text,
        tokens=tokenize(all_text),
        row_guess=row_guess,
        col_guess=col_guess,
        region=region,
    )
    return obs.to_dict()


def draw_focus_overlay(frame: np.ndarray, focus: Optional[Dict[str, Any]] = None) -> np.ndarray:
    if frame is None or not getattr(frame, "size", 0):
        return frame
    out = frame.copy()
    focus = focus or detect_focus(frame)
    if not focus.get("found") or not focus.get("bbox"):
        cv2.putText(out, "focus: not detected", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        return out
    x, y, w, h = [int(v) for v in focus["bbox"]]
    corners = focus.get("corners") or []
    if len(corners) >= 4:
        pts = np.array(corners, dtype=np.int32)
        cv2.polylines(out, [pts], True, (0, 255, 0), 4)
    else:
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 4)
    label = focus.get("label_text") or focus.get("focus_text") or focus.get("region") or "focus"
    label = str(label)[:60]
    cv2.rectangle(out, (x, max(0, y - 34)), (min(out.shape[1]-1, x + max(220, len(label) * 14)), y), (0, 0, 0), -1)
    cv2.putText(out, f"FOCUS {focus.get('confidence', 0):.2f}: {label}", (x + 6, max(24, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return out
