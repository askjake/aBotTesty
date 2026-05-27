#!/usr/bin/env python3
"""On Demand / PPV region and flow intelligence.

This module is deliberately text-first so it can be used from live captures,
operator-learning before/after fingerprints, and dashboard backfills without
requiring a Flask request context.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ppv_pricing import extract_purchase_pricing, clean_text as _clean
from time_context import extract_display_clock

ON_DEMAND_RX = re.compile(r"\b(on\s*demand|movie|tv\s*show|select\s+your\s+option|purchase\s+confirmation|watch\s+on\s+demand|free\s+on\s+demand|available\s+on\s+demand|rent|showtimes)\b", re.I)
CONFIRM_RX = re.compile(r"\b(purchase\s+confirmation|is\s+this\s+correct|you\s+have\s+indicated|yes\s+no|\byes\b|\bno\b)\b", re.I)
OPTION_RX = re.compile(r"\b(select\s+your\s+option|select\s+a\s+quality|available\s+for\s+48\s+hours|terms\s+and\s+conditions)\b", re.I)
ASSET_SUMMARY_RX = re.compile(r"\b(summary|episodes|cast|reviews|parental\s+guide|watch\s+now|watch\s+on\s+demand|record\s+this|rent|showtimes|available\s+on\s+demand)\b", re.I)
LANDING_RX = re.compile(r"\b(on\s*demand|free\s+top\s+movies|free\s+tv\s+shows|top\s+movies|new\s+releases|movies\s+for\s+you)\b", re.I)
FREE_RX = re.compile(r"\b(free\s+on\s+demand|free\b|available\s+on\s+demand)\b", re.I)

GENERIC_TITLES = {
    "watch", "watch now", "watch on demand", "rent", "showtimes", "select your option", "on demand",
    "movie", "tv show", "summary", "episodes", "cast", "reviews", "parental guide", "yes", "no",
    "available on demand", "free on demand", "options", "select", "demand", "showtimec",
}

STAGE_ORDER = {
    "unknown": 0,
    "on_demand_landing": 1,
    "asset_summary": 2,
    "episode_list": 3,
    "purchase_option": 4,
    "purchase_confirmation": 5,
    "playback_or_post_purchase": 6,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact_text(*parts: Any, limit: int = 6000) -> str:
    return _clean(" ".join(str(p or "") for p in parts), limit)


def focus_text_parts(focus: Optional[Dict[str, Any]]) -> List[str]:
    focus = focus if isinstance(focus, dict) else {}
    parts: List[str] = []
    for key in (
        "screen_title", "menu_title", "page_name", "block_title", "active_tab",
        "focused_item", "focused_value", "focus_text", "label_text", "row_text",
        "header_text", "context_text", "action_bar_text", "recovery_text",
    ):
        val = focus.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    ui = focus.get("ui_context") if isinstance(focus.get("ui_context"), dict) else {}
    for key in ("context_summary", "row_text"):
        val = ui.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
    for key in ("summary",):
        val = human.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return parts


def normalize_title(value: Any) -> str:
    s = _clean(value, 180)
    s = s.replace("|", " ").strip(" -_.,:;•\u2022\"'")
    s = re.sub(r"^(?:dish\s+)?(?:on\s*demand|movie|tv\s*show|summary|episodes|cast|reviews|parental\s+guide|select\s+your\s+option)\s+", "", s, flags=re.I).strip(" -_.,:;")
    s = re.sub(r"^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+\d{1,2}/\d{1,2}\s*(?:\|\s*)?\d{1,2}:\d{2}\s*[ap]m?\s+", "", s, flags=re.I).strip()
    s = re.sub(r"\b(?:HD|SD)\s*\$\s*\d+(?:\.\d{2})?\b", "", s, flags=re.I).strip()
    s = re.sub(r"\s+", " ", s).strip(" -_.,:;")
    if not s or s.lower() in GENERIC_TITLES:
        return ""
    if len(s) < 4 or sum(ch.isalpha() for ch in s) < 3:
        return ""
    # OCR garbage detector: too many punctuation/noise chars, or long words without vowels.
    letters = sum(ch.isalpha() for ch in s)
    noise = sum(1 for ch in s if not (ch.isalnum() or ch.isspace() or ch in "'’:-&!,."))
    if noise > max(2, letters // 3):
        return ""
    tokens = s.split()
    if len(tokens) >= 4:
        weird = sum(1 for t in tokens if len(t) > 4 and not re.search(r"[aeiouAEIOU]", t))
        if weird >= max(2, len(tokens) // 2):
            return ""
    if re.fullmatch(r"(?:[A-Z]{1,3}\s*){3,}", s):
        return ""
    if re.search(r"\b(?:watch now|watch on demand|record this|record series|showtimes|rent|yes|no)$", s, re.I) and len(s.split()) <= 4:
        return ""
    return s[:140]


def extract_title(text: str, focus: Optional[Dict[str, Any]] = None, stage: str = "") -> str:
    focus = focus if isinstance(focus, dict) else {}
    # 1) Strong known fields, but ignore action buttons.
    for key in ("asset_title", "program_title", "title", "screen_title", "menu_title", "page_name"):
        cand = normalize_title(focus.get(key))
        if cand:
            return cand
    # 2) Stage-specific text patterns.  These match the OnDemand screens Jake showed.
    patterns: List[str] = []
    if stage == "purchase_confirmation":
        patterns += [
            r"On Demand Purchase Confirmation\s+\d*\s+(.{4,110}?)\s+(?:You have indicated|Is this correct|Yes|No)",
        ]
    if stage == "purchase_option":
        patterns += [
            r"Select Your Option\s+(.{4,110}?)\s+Select a quality",
            r"Select Your Option\s+(.{4,110}?)\s+(?:Rent|HD|SD|\$\s*\d)",
        ]
    if stage in {"asset_summary", "episode_list", ""}:
        patterns += [
            r"(?:dish\s+)?Movie\s+(?:Summary\s+Cast\s+Reviews\s+Parental Guide\s+)?(.{4,110}?)\s+(?:\d{4}|PG|TV-|G\b|R\b|Animated|Comedy|Drama|Available|Rent|Showtimes|Watch Now)",
            r"(?:dish\s+)?TV Show\s+(?:Summary\s+Episodes\s+Cast\s+Parental Guide\s+)?(.{4,110}?)\s+(?:The\s+|First Aired|S\d|Season|episode|watched|availability)",
            r"(?:Summary\s+Episodes\s+Cast\s+Parental Guide\s+)(.{4,110}?)\s+(?:The\s+|First Aired|S\d|Season|episode)",
        ]
    patterns += [
        # On Demand landing often has the receiver clock before the hero title.
        r"(?:dish\s+)?On Demand\s+(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+\d{1,2}/\d{1,2}\s*(?:\|\s*)?\d{1,2}:\d{2}\s*[ap]m?\s+(.{4,120}?)\s+(?:FREE\s+TOP|FREE\s+TV|Free\s+On\s+Demand|Amateur|A\s+|The\s+|\d{4}|PG|TV-|Available)",
        r"(?:dish\s+)?On Demand\s+(.{4,110}?)\s+(?:FREE\s+TOP|FREE\s+TV|Free\s+On\s+Demand|Amateur|A\s+|The\s+|\d{4}|PG|TV-|Available)",
        r"(.{4,110}?)\s+(?:Available\s+On\s+Demand|Free\s+On\s+Demand|Available\s+for\s+48\s+hours|\$\s*\d)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            cand = normalize_title(m.group(1))
            if cand:
                return cand
    # 3) Fallback to a reasonable title-like line before action words.
    m = re.search(r"([A-Z][A-Za-z0-9 &'’:\-.!]{5,90})\s+(?:\$|rent|purchase|order|buy|available for|select a quality|watch on demand|free on demand)", text)
    return normalize_title(m.group(1)) if m else ""


def classify_stage(text: str, focus: Optional[Dict[str, Any]] = None) -> str:
    focus = focus if isinstance(focus, dict) else {}
    stage_hint = str(focus.get("popup_type") or "")
    if CONFIRM_RX.search(text) and re.search(r"\b(yes|no|is this correct|purchase confirmation)\b", text, re.I):
        return "purchase_confirmation"
    if OPTION_RX.search(text) and re.search(r"\b(rent|\$\s*\d|available\s+for\s+48\s+hours|select\s+a\s+quality)\b", text, re.I):
        return "purchase_option"
    if re.search(r"\b(episode\s+watched\s+availability|season\s+\d+|free\s+on\s+demand\s*$|episodes\b)", text, re.I):
        return "episode_list"
    if ASSET_SUMMARY_RX.search(text) and re.search(r"\b(summary|movie|tv\s*show|watch\s+now|watch\s+on\s+demand|rent|showtimes|available\s+on\s+demand)\b", text, re.I):
        return "asset_summary"
    if LANDING_RX.search(text):
        return "on_demand_landing"
    if "loading" in stage_hint.lower() or re.search(r"\b(loading|please wait)\b", text, re.I):
        return "loading"
    return "unknown"


def analyze_purchase_flow(screen_text: str = "", focus: Optional[Dict[str, Any]] = None, observed_at: Any = None) -> Dict[str, Any]:
    focus = focus if isinstance(focus, dict) else {}
    text = compact_text(screen_text, *focus_text_parts(focus), limit=7000)
    stage = classify_stage(text, focus)
    pricing = extract_purchase_pricing(text)
    title = extract_title(text, focus, stage=stage)
    clock = extract_display_clock(text, focus, observed_at=observed_at)
    is_ondemand = bool(ON_DEMAND_RX.search(text)) or stage not in {"unknown", "loading"}
    is_purchase_context = bool(is_ondemand or pricing.get("found") or stage in {"purchase_option", "purchase_confirmation"})
    availability = ""
    if FREE_RX.search(text):
        availability = "Free On Demand" if re.search(r"free\s+on\s+demand|free\b", text, re.I) else "Available On Demand"
    if re.search(r"available\s+for\s+48\s+hours", text, re.I):
        availability = "Available for 48 hours after purchase"
    flags: List[str] = []
    if pricing.get("category") == "free": flags.append("free_asset")
    if pricing.get("category") == "paid": flags.append("paid_asset")
    if not title and stage not in {"unknown", "loading"}: flags.append("asset_title_not_trusted")
    if clock.get("found"): flags.append("displayed_clock_captured")
    if stage == "purchase_confirmation": flags.append("final_confirmation_screen")
    if stage == "purchase_option": flags.append("purchase_option_screen")
    return {
        "schema": "purchase_flow_v2_region_time",
        "screen_stage": stage,
        "stage_order": STAGE_ORDER.get(stage, 0),
        "is_purchase_context": is_purchase_context,
        "asset_type": "on_demand" if is_ondemand else "",
        "asset_title": title,
        "episode_title": "",
        "displayed_time": clock.get("displayed") or "",
        "display_time_context": clock,
        "prices": [pricing.get("price_text")] if pricing.get("price_text") else [],
        "price": pricing.get("price_text") or "",
        "pricing": pricing,
        "purchase_price": pricing.get("amount"),
        "purchase_price_text": pricing.get("price_text") or "",
        "purchase_cost_category": pricing.get("category") or "unknown",
        "is_free": pricing.get("category") == "free",
        "is_paid": pricing.get("category") == "paid",
        "availability": availability,
        "confidence": stage_confidence(stage, title, pricing, clock),
        "confirm_like": stage == "purchase_confirmation" or bool(CONFIRM_RX.search(text)),
        "cancel_like": bool(re.search(r"\b(no|cancel|back)\b", text, re.I)),
        "flags": flags + list(pricing.get("flags") or []) + list(clock.get("flags") or []),
        "ocr_excerpt": text[:900],
    }


def stage_confidence(stage: str, title: str, pricing: Dict[str, Any], clock: Dict[str, Any]) -> float:
    score = {"unknown": 0.2, "loading": 0.25, "on_demand_landing": 0.65, "asset_summary": 0.72, "episode_list": 0.72, "purchase_option": 0.9, "purchase_confirmation": 0.94, "playback_or_post_purchase": 0.55}.get(stage, 0.4)
    if title: score += 0.08
    if pricing.get("found"): score += 0.08
    if clock.get("found"): score += 0.04
    return round(min(1.0, score), 3)


def summarize_ppv_log(raw_log: Dict[str, Any]) -> Dict[str, Any]:
    events = raw_log.get("events", []) if isinstance(raw_log, dict) else []
    stage_counts: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    titles: Counter[str] = Counter()
    prices: Counter[str] = Counter()
    final_confirms = 0
    operator_events = 0
    displayed_times: List[Dict[str, Any]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        key = ev.get("key") or ""
        before = ev.get("before_purchase_flow") or ev.get("before") or ev.get("analysis") or ev.get("result") or {}
        after = ev.get("purchase_flow") or ev.get("result") or ev.get("analysis") or {}
        if isinstance(after, dict):
            st = str(after.get("screen_stage") or "unknown")
            stage_counts[st] += 1
            title = normalize_title(after.get("asset_title") or after.get("title_guess"))
            if title: titles[title] += 1
            price = after.get("price") or after.get("purchase_price_text") or ((after.get("pricing") or {}) if isinstance(after.get("pricing"), dict) else {}).get("price_text")
            if price: prices[str(price)] += 1
            ctx = after.get("display_time_context") if isinstance(after.get("display_time_context"), dict) else None
            displayed = after.get("displayed_time") or (ctx or {}).get("displayed")
            if displayed:
                displayed_times.append({"ts": ev.get("ts", ""), "displayed_time": displayed, "stage": st, "asset_title": title, "drift_minutes": (ctx or {}).get("drift_minutes", ""), "source": (ctx or {}).get("source", "")})
        if isinstance(before, dict) and isinstance(after, dict) and key:
            transitions[f"{before.get('screen_stage','unknown')} --{key}--> {after.get('screen_stage','unknown')}"] += 1
        if ev.get("type") == "operator_purchase_observation":
            operator_events += 1
        if str(after.get("screen_stage") if isinstance(after, dict) else "") == "purchase_confirmation" or str(before.get("screen_stage") if isinstance(before, dict) else "") == "purchase_confirmation":
            final_confirms += 1
    return {
        "schema": "on_demand_flow_summary_v1",
        "events": len(events),
        "operator_purchase_events": operator_events,
        "stage_counts": dict(stage_counts),
        "top_transitions": [{"transition": k, "count": v} for k, v in transitions.most_common(20)],
        "titles_seen": [{"title": k, "count": v} for k, v in titles.most_common(20)],
        "prices_seen": [{"price": k, "count": v} for k, v in prices.most_common(20)],
        "final_confirmation_observations": final_confirms,
        "displayed_times": displayed_times[-50:],
        "replication_readiness": readiness_score(stage_counts, transitions, prices, final_confirms),
    }


def readiness_score(stage_counts: Counter[str], transitions: Counter[str], prices: Counter[str], final_confirms: int) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []
    for st in ["on_demand_landing", "asset_summary", "purchase_option", "purchase_confirmation"]:
        if stage_counts.get(st, 0) > 0:
            score += 20; reasons.append(f"saw_{st}")
    if prices:
        score += 10; reasons.append("saw_price")
    if final_confirms:
        score += 10; reasons.append("saw_final_confirmation")
    if any("purchase_option --select-->" in k for k in transitions):
        score += 10; reasons.append("saw_select_from_purchase_option")
    score = min(100, score)
    return {"score": score, "level": "high" if score >= 80 else "medium" if score >= 45 else "low", "reasons": reasons}
