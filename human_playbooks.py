#!/usr/bin/env python3
"""Human-style testing playbooks for STB feature exploration.

These are not blind automation scripts.  They are goal templates that tell the
operator/crawler what a human would intentionally verify once the observer sees
PIN, PPV, timer/recording, guide, settings, or blocked-content screens.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PLAYBOOKS: List[Dict[str, Any]] = [
    {
        "id": "verify_parental_block_unlock",
        "title": "Verify parental-control block and PIN unlock",
        "triggers": ["pin_prompt", "rating_or_parental_block"],
        "safety": "Uses remembered PIN only; never guesses PINs. Safe to back out if prompt is unexpected.",
        "human_checks": [
            "Notice that the UI is asking for a PIN/code, not offering normal navigation.",
            "Confirm the content/channel should be blocked for the configured rating/channel rule.",
            "Enter the remembered PIN and verify the program unlocks or returns to a clear state.",
        ],
        "suggested_actions": ["enter_pin_if_remembered", "verify_unlock_result", "back_or_live"],
        "avoid_actions": ["random_digits", "select_without_pin_context"],
    },
    {
        "id": "block_unblock_channel_or_rating",
        "title": "Block/unblock a channel or rating",
        "triggers": ["settings_or_controls", "parental", "locked", "rating"],
        "safety": "Requires explicit operator/test PIN and final confirmation sequence.",
        "human_checks": [
            "Read page title and grey-box title to confirm this is parental/channel/rating control.",
            "Track current focused row and value before changing it.",
            "After toggling, return to viewing and verify the actual blocking behavior.",
        ],
        "suggested_actions": ["read_focus", "toggle_explicit_sequence", "verify_on_blocked_channel"],
        "avoid_actions": ["factory_reset", "purchase", "unknown_select_spam"],
    },
    {
        "id": "set_or_verify_timer_recording",
        "title": "Set or verify timer / recording",
        "triggers": ["timer_or_recording", "record", "recording", "reminder"],
        "safety": "Safe if the operator expects a recording/timer test; verify confirmation text.",
        "human_checks": [
            "Read the content title, channel, start time, and action label before selecting.",
            "After selecting, wait for confirmation, toast, checkmark, or changed button text.",
            "Re-open the item or DVR/timers list to verify the scheduled state persisted.",
        ],
        "suggested_actions": ["info", "select", "wait_for_confirmation", "verify_timer_state"],
        "avoid_actions": ["delete_recording", "cancel_series_without_operator"],
    },
    {
        "id": "inspect_ppv_availability",
        "title": "Inspect PPV availability and pricing",
        "triggers": ["ppv_or_purchase", "purchase_flow"],
        "safety": "Never confirms purchase unless the operator explicitly enables a purchase test.",
        "human_checks": [
            "Read event title, price, start time, and purchase/cancel affordances.",
            "Record whether PPV is available and what the screen offers.",
            "Back out before any confirm-purchase action unless explicit test mode is enabled.",
        ],
        "suggested_actions": ["read_title_price", "info", "back"],
        "avoid_actions": ["select_confirm", "order", "purchase"],
    },
    {
        "id": "search_content_flow",
        "title": "Search content and verify results",
        "triggers": ["search_entry"],
        "safety": "Safe; use fast digit/letter entry and checkpoint OCR after results load.",
        "human_checks": [
            "Notice keyboard/search mode and enter text quickly enough that the UI does not time out.",
            "Wait for results to finish loading before judging success.",
            "Verify result title/source and whether selecting it opens details, playback, or purchase flow.",
        ],
        "suggested_actions": ["enter_search_text_fast", "wait_for_results", "inspect_result"],
        "avoid_actions": ["treat_loading_results_as_final_state"],
    },
]


def all_playbooks() -> List[Dict[str, Any]]:
    return PLAYBOOKS


def playbooks_for_cues(cues: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(cues, dict):
        return []
    hay = " ".join([
        str(cues.get("screen_kind") or ""),
        " ".join(cues.get("feature_tags") or []),
        " ".join(cues.get("risk_flags") or []),
        " ".join(str(g.get("goal") or "") for g in cues.get("test_goals") or [] if isinstance(g, dict)),
        str(cues.get("summary") or ""),
    ]).lower()
    out = []
    for pb in PLAYBOOKS:
        triggers = [str(t).lower() for t in pb.get("triggers", [])]
        if any(t and t in hay for t in triggers):
            out.append(pb)
    return out


def backlog_from_graph(data_dir: Path, limit: int = 100) -> List[Dict[str, Any]]:
    graph_path = Path(data_dir) / "nav_graph.json"
    if not graph_path.is_file():
        return []
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for sid, node in (graph.get("nodes") or {}).items():
        rep = node.get("representative") or {}
        focus = rep.get("focus") or {}
        cues = focus.get("human_cues") or {}
        pbs = playbooks_for_cues(cues)
        if not pbs and not cues.get("test_goals") and not cues.get("risk_flags"):
            continue
        rows.append({
            "state_id": sid,
            "label": node.get("label") or "",
            "screen_kind": cues.get("screen_kind") or "",
            "confidence": cues.get("confidence") or 0.0,
            "feature_tags": cues.get("feature_tags") or [],
            "risk_flags": cues.get("risk_flags") or [],
            "annoyance_flags": cues.get("annoyance_flags") or [],
            "test_goals": cues.get("test_goals") or [],
            "playbooks": [{"id": p.get("id"), "title": p.get("title")} for p in pbs],
            "screenshot": rep.get("screenshot"),
        })
    rows.sort(key=lambda r: (len(r.get("risk_flags") or []) + len(r.get("test_goals") or []), float(r.get("confidence") or 0)), reverse=True)
    return rows[: max(1, int(limit))]
