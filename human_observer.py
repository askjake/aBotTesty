#!/usr/bin/env python3
"""Human-like perception cues for the JAMboree/STB crawler.

This module sits above raw OCR/focus detection.  Its job is to answer the
questions a human answers subconsciously while watching TV:

* Is this a real interactive screen, or just a loading/wait state?
* Is this passive video content that should collapse into one "watching TV"
  state instead of thousands of unique video frames?
* Is this a PIN, rating-block, PPV/purchase, timer/recording, or settings flow?
* What would a careful operator do next, and what should be avoided?

It intentionally uses cheap visual heuristics + OCR text.  It does not need a
model server and it is safe to run inside timing checkpoints.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


PIN_RE = re.compile(r"\b(pin|passcode|password|enter\s+(?:your\s+)?(?:pin|code)|parental\s+(?:pin|code))\b", re.I)
RATING_BLOCK_RE = re.compile(r"\b(blocked|locked|restricted|rating|parental\s+control|not\s+authorized|unlock)\b", re.I)
PPV_RE = re.compile(r"\b(pay[-\s]?per[-\s]?view|ppv|purchase|buy|rent|order|price|\$\s*\d|event\s+price|confirm\s+purchase)\b", re.I)
TIMER_RE = re.compile(r"\b(timer|reminder|remind|record\s+(?:this|episode|series|event)|recording\s+timer|set\s+timer|schedule)\b", re.I)
LOADING_TEXT_RE = re.compile(r"\b(loading|please\s+wait|processing|retrieving|starting|connecting|refreshing|initializing|searching)\b", re.I)
SEARCH_RE = re.compile(r"\b(search|keyboard|recent\s+searches|popular\s+searches|enter\s+text)\b", re.I)
GUIDE_RE = re.compile(r"\b(guide|showing:|all\s+channels|subscribed|today\s+\d{1,2}:\d{2}|channel\s+\d{1,4})\b", re.I)
SETTINGS_RE = re.compile(r"\b(settings|preferences|diagnostics|parental|locks?|display|audio|caption|accessibility|network|remote)\b", re.I)
CONTENT_RE = re.compile(r"\b(episode|season|movie|show|cast|summary|first\s+aired|sports|live\s+tv|dvr)\b", re.I)
PRICE_RE = re.compile(r"\$\s*\d+(?:\.\d{2})?")
CHANNEL_RE = re.compile(r"\b(?:ch(?:annel)?\s*)?(\d{2,4})\b", re.I)


def _clean(text: str, limit: int = 2400) -> str:
    text = str(text or "").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _tokens(text: str, limit: int = 120) -> List[str]:
    stop = {"the", "and", "for", "you", "your", "with", "that", "this", "dish", "press", "select"}
    out = []
    for w in re.findall(r"[A-Za-z0-9$.-]{2,}", str(text or "").lower()):
        if w not in stop and w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


def _entropy(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [128], [0, 256]).flatten()
    p = hist / max(1.0, float(hist.sum()))
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def _edge_density(gray: np.ndarray) -> float:
    small = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(small, 80, 160)
    return float(np.mean(edges > 0))


def _red_logo_present(frame: np.ndarray) -> bool:
    if frame is None or not getattr(frame, "size", 0):
        return False
    h, w = frame.shape[:2]
    roi = frame[: max(1, int(h * 0.13)), : max(1, int(w * 0.13))]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 70, 70), (10, 255, 255)) | cv2.inRange(hsv, (160, 70, 70), (180, 255, 255))
    return int(np.count_nonzero(red)) > max(12, int(roi.shape[0] * roi.shape[1] * 0.0025))


def _top_right_video_thumb(frame: np.ndarray) -> bool:
    h, w = frame.shape[:2]
    roi = frame[: int(h * 0.18), int(w * 0.72) :]
    if roi.size == 0:
        return False
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # A PiP/thumb has a visible rectangular border or high local contrast in the top right.
    return _edge_density(gray) > 0.035 or float(np.var(gray)) > 450.0


def _detect_progress_dots(frame: np.ndarray) -> Tuple[bool, Dict[str, Any]]:
    """Detect the DISH loading/progress dotted line in the center of the screen."""
    if frame is None or not getattr(frame, "size", 0):
        return False, {"confidence": 0.0}
    img = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x1, x2 = int(w * 0.25), int(w * 0.75)
    y1, y2 = int(h * 0.35), int(h * 0.64)
    crop = img[y1:y2, x1:x2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    components: List[Tuple[float, float, int, int, int]] = []

    # Cyan/teal active dots.
    cyan = cv2.inRange(hsv, (70, 45, 50), (105, 255, 255))
    n, _, stats, _ = cv2.connectedComponentsWithStats(cyan)
    for i in range(1, n):
        x, y, ww, hh, area = [int(v) for v in stats[i]]
        if 2 <= area <= 260 and 1 <= ww <= 28 and 1 <= hh <= 18 and 0.35 <= ww / max(1, hh) <= 5.0:
            components.append((x + x1 + ww / 2, y + y1 + hh / 2, ww, hh, area))

    # Dark inactive dots on grey/dark background.
    small = gray[y1:y2, x1:x2]
    blur = cv2.GaussianBlur(small, (21, 21), 0)
    diff = cv2.subtract(blur, small)
    _, dark = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
    n, _, stats, _ = cv2.connectedComponentsWithStats(dark)
    for i in range(1, n):
        x, y, ww, hh, area = [int(v) for v in stats[i]]
        if 4 <= area <= 210 and 2 <= ww <= 22 and 2 <= hh <= 16 and 0.45 <= ww / max(1, hh) <= 3.2:
            components.append((x + x1 + ww / 2, y + y1 + hh / 2, ww, hh, area))

    if len(components) < 3:
        return False, {"confidence": 0.0, "component_count": len(components)}

    ys = np.array([c[1] for c in components], dtype=np.float32)
    median_y = float(np.median(ys))
    aligned = [c for c in components if abs(c[1] - median_y) <= 14]
    if len(aligned) < 3:
        return False, {"confidence": 0.0, "component_count": len(components), "aligned_count": len(aligned)}
    # Video/noise can produce hundreds of small aligned components.  A real DISH
    # loader has a compact row of roughly 4-12 dots.
    if len(aligned) > 18 or len(components) > 140:
        return False, {"confidence": 0.0, "component_count": len(components), "aligned_count": len(aligned), "rejected": "too_many_components_for_progress_dots"}
    xs = sorted([c[0] for c in aligned])
    x_span = float(max(xs) - min(xs)) if xs else 0.0
    y_std = float(np.std([c[1] for c in aligned])) if aligned else 99.0
    gaps = np.diff(xs) if len(xs) >= 3 else np.array([])
    gap_cv = float(np.std(gaps) / max(1.0, np.mean(gaps))) if len(gaps) else 9.9
    count_score = min(1.0, len(aligned) / 8.0)
    align_score = max(0.0, 1.0 - y_std / 14.0)
    span_score = min(1.0, x_span / 70.0)
    regularity_score = max(0.0, 1.0 - gap_cv / 1.15)
    conf = 0.34 * count_score + 0.30 * align_score + 0.18 * span_score + 0.18 * regularity_score
    ok = conf >= 0.50
    return ok, {
        "confidence": round(float(conf), 4),
        "component_count": len(components),
        "aligned_count": len(aligned),
        "x_span": round(x_span, 1),
        "y_std": round(y_std, 2),
        "gap_cv": round(gap_cv, 3),
        "center_y": round(median_y / h, 3),
    }


def _detect_red_attention(frame: np.ndarray) -> Dict[str, Any]:
    """Fallback focus cue: find a large red outline/selection when the main
    focus detector did not return a usable box.  This is intentionally weaker
    than focus_detector, but it helps manual teaching and degraded captures.
    """
    if frame is None or not getattr(frame, "size", 0):
        return {"found": False, "confidence": 0.0}
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 90, 90), (12, 255, 255)) | cv2.inRange(hsv, (158, 90, 90), (180, 255, 255))
    # Mild close/dilate so outline fragments become one candidate.
    red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)
    cnts, _ = cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = 0.0
    frame_area = float(max(1, h * w))
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        mask_area = float(cv2.countNonZero(red[y:y+bh, x:x+bw]))
        box_area = float(max(1, bw * bh))
        contour_area = float(cv2.contourArea(c))
        aspect = bw / max(1.0, float(bh))
        box_frac = box_area / frame_area
        # Ignore tiny red logos/artwork and the DISH logo area.
        if box_frac < 0.006 or bw < 45 or bh < 24:
            continue
        if x < w * 0.17 and y < h * 0.16 and box_frac < 0.035:
            continue
        if not (0.35 <= aspect <= 6.5):
            continue
        # Selection outlines are red but not necessarily filled.  Reward moderate
        # red density and bigger rectangular boxes.
        density = mask_area / box_area
        rect_score = min(1.0, contour_area / box_area)
        size_score = min(1.0, box_frac / 0.06)
        density_score = 1.0 - min(1.0, abs(density - 0.18) / 0.32)
        score = 0.42 * size_score + 0.30 * density_score + 0.18 * rect_score + 0.10 * min(1.0, aspect / 2.0)
        if score > best_score:
            best_score = score
            best = (x, y, bw, bh, density, box_frac)
    if not best or best_score < 0.34:
        return {"found": False, "confidence": round(float(best_score), 4)}
    x, y, bw, bh, density, box_frac = best
    cx = (x + bw / 2.0) / max(1, w)
    cy = (y + bh / 2.0) / max(1, h)
    row = int(min(2, max(0, cy * 3))) + 1
    col = int(min(2, max(0, cx * 3))) + 1
    return {
        "found": True,
        "confidence": round(float(min(0.68, 0.34 + best_score * 0.46)), 4),
        "bbox": [int(x), int(y), int(bw), int(bh)],
        "center_norm": [round(float(cx), 4), round(float(cy), 4)],
        "row_guess": row,
        "col_guess": col,
        "region": "fallback_red_focus",
        "density": round(float(density), 4),
        "box_fraction": round(float(box_frac), 5),
        "tokens": ["visual_focus", f"focus_r{row}c{col}"],
    }


def _detect_loading(frame: np.ndarray, focus: Dict[str, Any], text: str) -> Tuple[bool, float, List[str], Dict[str, Any]]:
    reasons: List[str] = []
    extra: Dict[str, Any] = {}
    if LOADING_TEXT_RE.search(text):
        reasons.append("loading_text")
    dots, dot_info = _detect_progress_dots(frame)
    extra["progress_dots"] = dot_info
    logo = _red_logo_present(frame)
    thumb = _top_right_video_thumb(frame)
    extra["dish_logo_top_left"] = logo
    extra["top_right_thumbnail"] = thumb
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mid = gray[int(gray.shape[0] * 0.18) : int(gray.shape[0] * 0.90), int(gray.shape[1] * 0.06) : int(gray.shape[1] * 0.94)]
    ent = _entropy(mid)
    edges = _edge_density(mid)
    extra["mid_entropy"] = round(ent, 3)
    extra["mid_edge_density"] = round(edges, 5)
    # Low-confidence top-left logo "focus" + dark dotted center is the classic interstitial.
    bbox = focus.get("bbox") if isinstance(focus, dict) else None
    conf = float(focus.get("confidence") or 0.0) if isinstance(focus, dict) else 0.0
    if bbox and len(bbox) == 4 and bbox[0] < frame.shape[1] * 0.16 and bbox[1] < frame.shape[0] * 0.16 and conf < 0.18:
        reasons.append("logo_misread_as_focus")
    focus_conf = float(focus.get("confidence") or 0.0) if isinstance(focus, dict) else 0.0
    has_title = bool(focus.get("page_name") or focus.get("block_title") or focus.get("screen_title") or focus.get("menu_title")) if isinstance(focus, dict) else False
    # Only trust visual progress dots as a loading signal when they appear in a
    # DISH-style loading context.  Otherwise generic text/box geometry in tests or
    # broadcast graphics can look like aligned dots.
    if dots and (logo or "loading_text" in reasons):
        reasons.append("center_progress_dots")
    elif dots:
        extra["progress_dots"]["ignored_reason"] = "no_dish_loading_context"
    if logo and ent < 3.55 and edges < 0.035 and (not focus.get("found") or focus_conf < 0.18) and not has_title:
        reasons.append("low_information_dish_wait")
    confidence = 0.0
    if "loading_text" in reasons:
        confidence += 0.35
    if "center_progress_dots" in reasons:
        confidence += 0.50
    if "logo_misread_as_focus" in reasons:
        confidence += 0.22
    if "low_information_dish_wait" in reasons:
        confidence += 0.25
    if "logo_misread_as_focus" in reasons and "low_information_dish_wait" in reasons:
        confidence += 0.12
    if thumb and ("center_progress_dots" in reasons or "low_information_dish_wait" in reasons):
        confidence += 0.08
    return confidence >= 0.50, min(1.0, confidence), reasons, extra


def _detect_passive_video(frame: np.ndarray, focus: Dict[str, Any], text: str, loading: bool) -> Tuple[bool, float, List[str]]:
    if loading:
        return False, 0.0, []
    reasons: List[str] = []
    title = " ".join(str((focus or {}).get(k) or "") for k in ("page_name", "block_title", "screen_title", "menu_title")).strip()
    focus_found = bool((focus or {}).get("found"))
    focus_conf = float((focus or {}).get("confidence") or 0.0)
    focused_item = str((focus or {}).get("focused_item") or "").strip()
    if not focus_found or focus_conf < 0.18:
        reasons.append("no_reliable_focus")
    if not title or title.lower() in {"live tv", "unknown screen"}:
        reasons.append("no_actionable_title")
    if re.search(r"\blive\s+tv\b|\bmins?\s+left\b|\bnow\b|\bhd\b|\bcnn\b|\bcbs\b|\bfox\b|\bespn\b", text, re.I):
        reasons.append("video_content_text")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    variance = float(np.var(gray))
    edges = _edge_density(gray)
    ent = _entropy(gray)
    # Real video has texture/entropy.  Synthetic flat menus or simple test cards can
    # have high variance from a border/text but are not passive video.
    if variance > 850 and edges < 0.20 and ent > 3.8:
        reasons.append("video_like_visuals")
    # Avoid classifying clear menu/modal/focus states as passive video.
    if focus_conf >= 0.40 and focused_item and title and not re.search(r"\blive\s+tv\b", title, re.I):
        return False, 0.0, reasons
    conf = 0.22 * ("no_reliable_focus" in reasons) + 0.22 * ("no_actionable_title" in reasons) + 0.26 * ("video_content_text" in reasons) + 0.30 * ("video_like_visuals" in reasons)
    return conf >= 0.48, min(1.0, conf), reasons


def _extract_channel(text: str) -> Tuple[str, str]:
    # Prefer explicit channel/callsign snippets; do not trust every number in a news chyron.
    m = re.search(r"\b(?:ch(?:annel)?\s*)?(\d{2,4})\s+([A-Z][A-Z0-9&+.]{1,8})\b", text)
    if m:
        return m.group(1), m.group(2)
    # Fall back to a likely standalone 2-4 digit channel near DISH/Live TV contexts.
    if re.search(r"\blive\s+tv|guide|channel|recall\b", text, re.I):
        m = CHANNEL_RE.search(text)
        if m:
            return m.group(1), ""
    return "", ""


def _goal_cues(text: str) -> Tuple[List[str], List[Dict[str, Any]], List[str], List[str]]:
    tags: List[str] = []
    goals: List[Dict[str, Any]] = []
    risks: List[str] = []
    notes: List[str] = []
    price = PRICE_RE.search(text)
    if PIN_RE.search(text):
        tags.append("pin_prompt")
        goals.append({"goal": "enter_or_verify_pin", "safety": "requires_remembered_pin", "recommended_actions": ["digits", "select", "back"]})
        risks.append("pin_required")
        notes.append("Human would notice this is not a navigation menu; it is waiting for a PIN/code.")
    if RATING_BLOCK_RE.search(text):
        tags.append("rating_or_parental_block")
        goals.append({"goal": "verify_parental_block", "safety": "safe_to_verify_popup", "recommended_actions": ["enter_pin_if_prompt", "back"]})
    if PPV_RE.search(text):
        tags.append("ppv_or_purchase")
        price_text = price.group(0) if price else ""
        goals.append({"goal": "inspect_ppv_availability", "safety": "do_not_confirm_purchase_without_operator", "price": price_text, "recommended_actions": ["info", "back", "cancel"]})
        risks.append("purchase_flow")
        notes.append("Human would read title/price and avoid confirming purchase unless explicitly testing purchase flow.")
    if TIMER_RE.search(text):
        tags.append("timer_or_recording")
        goals.append({"goal": "set_or_verify_timer", "safety": "confirm_then_verify_timer_state", "recommended_actions": ["select", "options", "back"]})
        notes.append("Human would look for confirmation text after setting a timer/recording.")
    if SEARCH_RE.search(text):
        tags.append("search_entry")
        goals.append({"goal": "search_content", "safety": "safe", "recommended_actions": ["letters_or_digits", "select", "back"]})
    if GUIDE_RE.search(text):
        tags.append("guide_navigation")
    if SETTINGS_RE.search(text):
        tags.append("settings_or_controls")
    if CONTENT_RE.search(text):
        tags.append("content_details")
    return tags, goals, risks, notes


def observe_human_cues(
    frame: np.ndarray,
    focus: Optional[Dict[str, Any]] = None,
    ocr_text: str = "",
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return human-like interpretation of one screen observation."""
    focus = focus if isinstance(focus, dict) else {}
    parts = [ocr_text]
    for key in (
        "page_name", "block_title", "screen_title", "menu_title", "human_label", "focused_item",
        "focused_value", "label_text", "focus_text", "row_text", "context_text", "action_bar_text",
    ):
        val = focus.get(key)
        if val:
            parts.append(str(val))
    text = _clean(" ".join(parts))

    fallback_focus = _detect_red_attention(frame)
    if fallback_focus.get("found") and not focus.get("found"):
        # Do not pretend this is a full semantic focus read, but expose enough
        # geometry for state splitting and human-style attention tracking.
        focus = dict(focus)
        focus.update({
            "found": True,
            "confidence": fallback_focus.get("confidence", 0.0),
            "bbox": fallback_focus.get("bbox"),
            "center_norm": fallback_focus.get("center_norm"),
            "row_guess": fallback_focus.get("row_guess"),
            "col_guess": fallback_focus.get("col_guess"),
            "region": fallback_focus.get("region", "fallback_red_focus"),
            "tokens": list(set(list(focus.get("tokens") or []) + list(fallback_focus.get("tokens") or []))),
            "focus_role": "visual_focus_fallback",
        })

    loading, loading_conf, loading_reasons, visual = _detect_loading(frame, focus, text)
    passive, passive_conf, passive_reasons = _detect_passive_video(frame, focus, text, loading)
    tags, goals, risks, notes = _goal_cues(text)
    channel, channel_name = _extract_channel(text)

    screen_kind = "actionable_ui"
    confidence = 0.55
    is_actionable = True
    is_transient = False
    recommended_actions: List[str] = []
    avoid_actions: List[str] = []
    annoyance_flags: List[str] = []

    if loading:
        screen_kind = "loading_interstitial"
        confidence = max(0.70, loading_conf)
        is_actionable = False
        is_transient = True
        recommended_actions = ["wait"]
        avoid_actions = ["select", "up", "down", "left", "right"]
        annoyance_flags.append("waiting_for_menu_or_video_to_finish_loading")
        notes.append("Human would wait here instead of learning this as a destination screen.")
    elif "pin_prompt" in tags:
        screen_kind = "pin_prompt"
        confidence = 0.88
        recommended_actions = ["enter_pin_if_remembered", "back"]
        avoid_actions = ["random_navigation", "select_without_pin"]
    elif "ppv_or_purchase" in tags:
        screen_kind = "purchase_or_ppv"
        confidence = 0.86
        recommended_actions = ["read_title_price", "info", "back"]
        avoid_actions = ["select_confirm", "order", "purchase"]
    elif "timer_or_recording" in tags:
        screen_kind = "timer_or_recording_flow"
        confidence = 0.78
        recommended_actions = ["read_confirmation", "select", "options", "back"]
    elif passive:
        screen_kind = "passive_video"
        confidence = max(0.62, passive_conf)
        is_actionable = False
        recommended_actions = ["info", "guide", "options", "recall", "ch_up", "ch_down", "home"]
        avoid_actions = ["random_directional_spam"]
        notes.append("Human treats changing video frames as the same watching-TV state unless an overlay/menu appears.")
    elif focus.get("found") or focus.get("screen_title") or focus.get("block_title") or focus.get("page_name"):
        screen_kind = "actionable_ui"
        confidence = 0.74
        recommended_actions = ["read_focus", "up", "down", "left", "right", "select", "back"]
    else:
        screen_kind = "unknown_visual"
        confidence = 0.35
        recommended_actions = ["wait", "info", "back", "home"]
        annoyance_flags.append("unclear_screen_no_focus_or_title")

    if focus.get("confidence") is not None and float(focus.get("confidence") or 0) < 0.20 and screen_kind == "actionable_ui":
        annoyance_flags.append("weak_focus_detection")
    if screen_kind != "loading_interstitial" and LOADING_TEXT_RE.search(text):
        annoyance_flags.append("loading_text_but_screen_not_classified_loading")

    summary_parts = [screen_kind]
    title = focus.get("page_name") or focus.get("block_title") or focus.get("screen_title") or focus.get("menu_title")
    item = focus.get("focused_item") or focus.get("label_text") or focus.get("focus_text")
    if title:
        summary_parts.append(str(title)[:80])
    if item:
        summary_parts.append("focus=" + str(item)[:80])
    if channel:
        summary_parts.append("channel=" + channel)

    return {
        "schema": "human_observer_v1",
        "screen_kind": screen_kind,
        "confidence": round(float(confidence), 4),
        "is_actionable": bool(is_actionable),
        "is_transient": bool(is_transient),
        "loading_confidence": round(float(loading_conf), 4),
        "loading_reasons": loading_reasons,
        "passive_video_confidence": round(float(passive_conf), 4),
        "passive_video_reasons": passive_reasons,
        "feature_tags": sorted(set(tags)),
        "test_goals": goals,
        "risk_flags": sorted(set(risks)),
        "annoyance_flags": sorted(set(annoyance_flags)),
        "recommended_actions": recommended_actions,
        "avoid_actions": avoid_actions,
        "channel_number": channel,
        "channel_name": channel_name,
        "visible_affordances": {
            "focus_found": bool(focus.get("found")),
            "focus_confidence": float(focus.get("confidence") or 0.0),
            "title_present": bool(title),
            "focused_item_present": bool(item),
            "dish_logo_top_left": bool(visual.get("dish_logo_top_left")),
            "top_right_thumbnail": bool(visual.get("top_right_thumbnail")),
            "fallback_focus": fallback_focus,
        },
        "visual": visual,
        "human_notes": notes[:6],
        "summary": " · ".join(summary_parts),
        "tokens": _tokens(" ".join([text, screen_kind, " ".join(tags)]), limit=80),
    }


def screen_kind_from_focus(focus: Optional[Dict[str, Any]]) -> str:
    if not isinstance(focus, dict):
        return "unknown"
    human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
    return str(human.get("screen_kind") or "unknown")


def is_transient_focus(focus: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(focus, dict):
        return False
    human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
    return bool(human.get("is_transient")) or bool(focus.get("loading"))
