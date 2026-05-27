#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

log = logging.getLogger("merged.ppv")

PPV_CONTEXT_RX = re.compile(r"\b(ppv|pay[-\s]?per[-\s]?view|on\s+demand|rent|rental|order|purchase|buy|event price|price|free|free\s+on\s+demand|available\s+on\s+demand|\$\s*\d|watch now|confirm purchase|confirm order)\b", re.I)
CONFIRM_RX = re.compile(r"\b(confirm|are you sure|purchase|order|rent|buy|yes|submit|accept|charge|bill|authorize)\b", re.I)
CANCEL_RX = re.compile(r"\b(cancel|back|no|do not|exit)\b", re.I)
PRICE_RX = re.compile(r"\$\s*\d+(?:\.\d{2})?")

from ppv_pricing import extract_purchase_pricing, parse_limit_value, format_limit, check_purchase_limits, clean_text as _ppv_clean_text
from ondemand_flow_intelligence import analyze_purchase_flow, summarize_ppv_log, normalize_title as _od_normalize_title


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text_from_focus(focus: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "screen_title", "menu_title", "page_name", "block_title", "focused_item", "focused_value",
        "focus_text", "label_text", "row_text", "context_text", "action_bar_text", "recovery_text",
    ):
        val = focus.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
    for key in ("summary",):
        val = human.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    for item in human.get("risk_flags", []) or []:
        parts.append(str(item))
    for item in human.get("feature_tags", []) or []:
        parts.append(str(item))
    return " ".join(parts)

GENERIC_TITLE_WORDS = {"movie", "tv show", "summary", "episodes", "cast", "parental guide", "rent", "watch", "yes", "no", "select your option", "on demand", "options"}


def _clean_title_candidate(value: Any) -> str:
    title = _ppv_clean_text(value, 140).strip(" -_|.:;,")
    # Remove leading tab chrome that sometimes precedes the actual title.
    title = re.sub(r"^(?:summary|episodes|cast|reviews|parental guide|movie|tv show|on demand|select your option)\s+", "", title, flags=re.I).strip(" -_|.:;,")
    title = re.sub(r"^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}\s*[ap]m?\s+", "", title, flags=re.I).strip(" -_|.:;,")
    if not title or title.lower() in GENERIC_TITLE_WORDS:
        return ""
    if len(title) < 4 or sum(ch.isalpha() for ch in title) < 3:
        return ""
    if re.search(r"\b(?:rent|watch|record this|record series|showtimes|yes|no)\b$", title, re.I) and len(title.split()) <= 3:
        return ""
    return title[:120]


def _extract_asset_title(clean_text: str, focus: Dict[str, Any]) -> str:
    # Prefer explicit title-like focus fields, but ignore focused action buttons.
    for key in ("program_title", "asset_title", "title", "screen_title", "menu_title", "page_name"):
        val = _clean_title_candidate((focus or {}).get(key))
        if val:
            return val
    text = _ppv_clean_text(clean_text, 2400)
    patterns = [
        r"Select Your Option\s+(.{4,90}?)\s+Select a quality",
        r"Movie\s+(?:Summary\s+Cast\s+Reviews\s+Parental Guide\s+)?(.{4,90}?)\s+(?:\d{4}|PG|TV-|Animated|Comedy|Available|Rent|Showtimes)",
        r"TV Show\s+(?:Summary\s+Episodes\s+Cast\s+Parental Guide\s+)?(.{4,90}?)\s+(?:The real|First Aired|S\d|Season|episode|watched|availability)",
        r"On Demand\s+(.{4,90}?)\s+(?:Amateur|FREE|FREE TOP|Jodie|\d{4}|PG|TV-|Available)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = _clean_title_candidate(m.group(1))
            if val:
                return val
    # Fallback before common purchase words.
    m = re.search(r"([A-Z][A-Za-z0-9 &'’:\-.]{5,90})\s+(?:\$|rent|purchase|order|buy|available for|select a quality)", text)
    return _clean_title_candidate(m.group(1)) if m else ""


class PPVPurchaseAgent:
    """Explicitly armed PPV purchase-test helper.

    Earlier app versions intentionally observed PPV only. This agent keeps that
    default, but supports a supervised test-account purchase flow when explicitly
    armed by the operator and requested with confirm_purchase=true.
    """

    def __init__(
        self,
        data_dir: Path,
        crawler: Any,
        capture_frame: Callable[[], Optional[np.ndarray]],
        send_requested_key: Callable[[str, Optional[int], float], Dict[str, Any]],
        default_gap_s: float = 0.15,
        default_delay_ms: int = 120,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.crawler = crawler
        self.capture_frame = capture_frame
        self.send_requested_key = send_requested_key
        self.default_gap_s = float(default_gap_s)
        self.default_delay_ms = int(default_delay_ms)
        self.log_path = self.data_dir / "ppv_purchase_test_log.json"
        self.limits_path = self.data_dir / "ppv_purchase_limits.json"
        self._armed_until = 0.0
        self._armed_reason = ""

    def _load_log(self) -> Dict[str, Any]:
        if self.log_path.is_file():
            try:
                return json.loads(self.log_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"schema": "ppv_purchase_test_log_v1", "updated_at": _now(), "events": []}

    def _default_limits(self) -> Dict[str, Any]:
        # Safe default: no dollar cap once the PPV workflow is explicitly armed; operators can set 0 for free-only from /ppv.
        return {
            "schema": "ppv_purchase_limits_v1",
            "updated_at": _now(),
            "individual_limit": None,
            "session_limit": None,
            "session_spent": 0.0,
            "pending_purchase": {},
        }

    def _load_limits(self) -> Dict[str, Any]:
        if self.limits_path.is_file():
            try:
                raw = json.loads(self.limits_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    base = self._default_limits()
                    base.update(raw)
                    return base
            except Exception:
                pass
        return self._default_limits()

    def _save_limits(self, limits: Dict[str, Any]) -> Dict[str, Any]:
        limits["updated_at"] = _now()
        tmp = self.limits_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(limits, indent=2), encoding="utf-8")
        tmp.replace(self.limits_path)
        return limits

    def set_limits(self, individual_limit: Any = None, session_limit: Any = None) -> Dict[str, Any]:
        limits = self._load_limits()
        if individual_limit is not None:
            limits["individual_limit"] = parse_limit_value(individual_limit)
        if session_limit is not None:
            limits["session_limit"] = parse_limit_value(session_limit)
        self._save_limits(limits)
        event = {"ts": _now(), "type": "limits_changed", "limits": self.limits_status()}
        self._append(event)
        return {"ok": True, "limits": self.limits_status()}

    def reset_session_spend(self) -> Dict[str, Any]:
        limits = self._load_limits()
        limits["session_spent"] = 0.0
        limits["pending_purchase"] = {}
        self._save_limits(limits)
        event = {"ts": _now(), "type": "session_spend_reset", "limits": self.limits_status()}
        self._append(event)
        return {"ok": True, "limits": self.limits_status()}

    def limits_status(self) -> Dict[str, Any]:
        limits = self._load_limits()
        individual = limits.get("individual_limit")
        session = limits.get("session_limit")
        spent = float(limits.get("session_spent") or 0.0)
        return {
            "individual_limit": individual,
            "individual_limit_label": format_limit(individual),
            "session_limit": session,
            "session_limit_label": format_limit(session),
            "session_spent": round(spent, 2),
            "session_spent_label": f"${spent:.2f}",
            "session_remaining": None if session is None else round(max(0.0, float(session) - spent), 2),
            "session_remaining_label": "unlimited" if session is None else f"${max(0.0, float(session) - spent):.2f}",
            "pending_purchase": limits.get("pending_purchase") or {},
            "limits_file": str(self.limits_path),
        }

    def _remember_pending_from_analysis(self, analysis: Dict[str, Any]) -> None:
        pricing = analysis.get("pricing") or {}
        amount = pricing.get("amount")
        title = str(analysis.get("title_guess") or "").strip()
        if amount is None and not title:
            return
        limits = self._load_limits()
        pending = dict(limits.get("pending_purchase") or {})
        if amount is not None:
            pending["amount"] = round(float(amount), 2)
            pending["price_text"] = pricing.get("price_text") or f"${float(amount):.2f}"
            pending["category"] = pricing.get("category") or ("free" if float(amount) == 0 else "paid")
        if title:
            pending["title"] = title
        pending["updated_at"] = _now()
        limits["pending_purchase"] = pending
        self._save_limits(limits)

    def _effective_purchase_amount(self, analysis: Dict[str, Any]) -> Optional[float]:
        pricing = analysis.get("pricing") or {}
        amount = pricing.get("amount")
        if amount is not None:
            try:
                return round(float(amount), 2)
            except Exception:
                pass
        pending = (self._load_limits().get("pending_purchase") or {})
        amount = pending.get("amount")
        if amount is not None:
            try:
                return round(float(amount), 2)
            except Exception:
                pass
        return None

    def _authorize_price(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        limits = self._load_limits()
        amount = self._effective_purchase_amount(analysis)
        allowed, reason, details = check_purchase_limits(
            amount,
            limits.get("individual_limit"),
            limits.get("session_limit"),
            float(limits.get("session_spent") or 0.0),
        )
        return {"allowed": allowed, "reason": reason, "details": details, "limits": self.limits_status()}

    def _record_purchase_spend(self, analysis: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        amount = self._effective_purchase_amount(analysis)
        limits = self._load_limits()
        if amount is not None:
            limits["session_spent"] = round(float(limits.get("session_spent") or 0.0) + float(amount), 2)
        purchase_record = {
            "ts": _now(),
            "type": "purchase_recorded",
            "title": analysis.get("title_guess") or (limits.get("pending_purchase") or {}).get("title") or "",
            "amount": amount,
            "price_text": (analysis.get("pricing") or {}).get("price_text") or (limits.get("pending_purchase") or {}).get("price_text") or "",
            "session_spent_after": limits.get("session_spent", 0.0),
            "event_ref": event.get("ts"),
        }
        limits["pending_purchase"] = {}
        self._save_limits(limits)
        self._append(purchase_record)
        return purchase_record

    def _append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        raw = self._load_log()
        raw.setdefault("events", []).append(event)
        raw["updated_at"] = _now()
        tmp = self.log_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        tmp.replace(self.log_path)
        return event

    def arm(self, ttl_s: int = 300, reason: str = "") -> Dict[str, Any]:
        ttl = max(30, min(int(ttl_s or 300), 3600))
        self._armed_until = time.time() + ttl
        self._armed_reason = reason or "operator armed PPV purchase test"
        event = {"ts": _now(), "type": "armed", "ttl_s": ttl, "reason": self._armed_reason}
        self._append(event)
        return {"ok": True, "armed": True, "armed_until_epoch": self._armed_until, "ttl_s": ttl, "reason": self._armed_reason}

    def disarm(self) -> Dict[str, Any]:
        self._armed_until = 0.0
        event = {"ts": _now(), "type": "disarmed"}
        self._append(event)
        return {"ok": True, "armed": False}

    def armed(self) -> bool:
        return time.time() < float(self._armed_until or 0.0)

    def status(self) -> Dict[str, Any]:
        raw = self._load_log()
        return {
            "ok": True,
            "armed": self.armed(),
            "armed_until_epoch": self._armed_until,
            "armed_reason": self._armed_reason,
            "log_file": str(self.log_path),
            "event_count": len(raw.get("events", []) or []),
            "latest_events": (raw.get("events", []) or [])[-10:],
            "default_mode": "observe_only_until_explicitly_armed",
            "limits": self.limits_status(),
            "learned_flow": self.learned_flow_summary(),
        }

    def analyze_fingerprint(self, fp: Any, source: str = "fingerprint", append: bool = False) -> Dict[str, Any]:
        """Analyze an existing crawler fingerprint for On Demand/PPV semantics.

        This is intentionally reusable by monitor-learning.  A human button press
        can be learned as a normal before→button→after edge *and* as a purchase
        workflow stage transition without blocking the /monitor request path.
        """
        focus = fp.focus if isinstance(getattr(fp, "focus", None), dict) else {}
        text = " ".join([getattr(fp, "ocr_text", "") or "", _text_from_focus(focus)])
        flow = analyze_purchase_flow(text, focus, observed_at=_now())
        clean = re.sub(r"\s+", " ", text).strip()
        # Backward-compatible field names used by older dashboards/tests.
        flow.update({
            "ok": True,
            "ts": _now(),
            "source": source,
            "is_ppv_context": bool(flow.get("is_purchase_context")),
            "title_guess": flow.get("asset_title", ""),
            "focus": focus,
            "ocr_excerpt": flow.get("ocr_excerpt") or clean[:900],
            "screenshot": getattr(fp, "screenshot", ""),
            "armed": self.armed(),
        })
        self._remember_pending_from_analysis(flow)
        if append:
            self._append({"ts": _now(), "type": "analyze", "purchase_flow": {k: v for k, v in flow.items() if k != "focus"}, "result": {k: v for k, v in flow.items() if k != "focus"}, "limits": self.limits_status()})
        return flow

    def analyze_current(self) -> Dict[str, Any]:
        fp = self.crawler.capture_fingerprint("ppv_probe", perception="full")
        return self.analyze_fingerprint(fp, source="live_ppv_probe", append=True)

    def record_operator_observation(self, key: str, before_fp: Any, after_fp: Any, source: str = "operator_monitor_async") -> Optional[Dict[str, Any]]:
        """Record PPV/OnDemand stage transitions observed during normal /monitor use."""
        before = self.analyze_fingerprint(before_fp, source=f"{source}:before", append=False)
        after = self.analyze_fingerprint(after_fp, source=f"{source}:after", append=False)
        if not (before.get("is_purchase_context") or after.get("is_purchase_context")):
            return None
        event = {
            "ts": _now(),
            "type": "operator_purchase_observation",
            "source": source,
            "key": str(key),
            "before_purchase_flow": {k: v for k, v in before.items() if k != "focus"},
            "purchase_flow": {k: v for k, v in after.items() if k != "focus"},
            "screenshot": getattr(after_fp, "screenshot", ""),
            "limits": self.limits_status(),
        }
        self._append(event)
        return event

    def learned_flow_summary(self) -> Dict[str, Any]:
        return summarize_ppv_log(self._load_log())

    def navigate_ondemand(self, sequence: Optional[List[str]] = None, dry_run: bool = True, settle_s: float = 1.0) -> Dict[str, Any]:
        seq = [str(x).strip() for x in (sequence or []) if str(x).strip()]
        if not seq:
            # Jake observed that tuning channel 1 lands in On Demand on this STB.
            # This is faster and more reliable than walking Home top tabs, while
            # still remaining operator-editable from /ppv.
            seq = ["channel:1"]
        plan = {"sequence": seq, "settle_s": settle_s, "dry_run": dry_run}
        if dry_run:
            return {"ok": True, "dry_run": True, "plan": plan}
        sent = []
        for key in seq:
            sent.append({"key": key, "send": self.send_requested_key(key, self.default_delay_ms, self.default_gap_s)})
            time.sleep(max(0.05, float(settle_s)))
        analysis = self.analyze_current()
        event = {"ts": _now(), "type": "navigate_ondemand", "plan": plan, "sent": sent, "analysis": {k: v for k, v in analysis.items() if k != "focus"}}
        self._append(event)
        return {"ok": True, "dry_run": False, "event": event, "status": self.status()}

    def run_current_purchase_test(self, confirm_purchase: bool = False, final_confirm: bool = False, max_steps: int = 3, dry_run: bool = True) -> Dict[str, Any]:
        analysis = self.analyze_current()
        if not analysis.get("is_ppv_context"):
            return {"ok": False, "error": "current screen does not look like a PPV/purchase context", "analysis": analysis}
        already_confirmation = bool(analysis.get("confirm_like")) and bool(re.search(r"\b(is this correct|purchase confirmation|confirmation|yes|no)\b", str(analysis.get("ocr_excerpt") or ""), re.I))
        if already_confirmation and not final_confirm and not dry_run:
            return {"ok": False, "error": "current screen already looks like a purchase confirmation; final_confirm=true is required to press SELECT here", "analysis": analysis, "limits": self.limits_status()}

        plan = ["select"]
        if final_confirm and not already_confirmation:
            plan.append("select")
        plan = plan[: max(1, min(int(max_steps or 3), 5))]
        auth = self._authorize_price(analysis)
        if dry_run:
            return {"ok": True, "dry_run": True, "plan": plan, "analysis": analysis, "price_authorization": auth, "note": "No buttons sent."}
        if not confirm_purchase:
            return {"ok": False, "error": "confirm_purchase=true is required for PPV test ordering", "plan": plan, "analysis": analysis, "price_authorization": auth}
        if not self.armed():
            return {"ok": False, "error": "PPV purchase test is not armed. Call /api/ppv/arm first.", "plan": plan, "analysis": analysis, "price_authorization": auth}
        if not auth.get("allowed"):
            event = {"ts": _now(), "type": "purchase_blocked_by_limit", "authorization": auth, "analysis": {k: v for k, v in analysis.items() if k != "focus"}}
            self._append(event)
            return {"ok": False, "error": auth.get("reason"), "plan": plan, "analysis": analysis, "price_authorization": auth, "status": self.status()}

        sent: List[Dict[str, Any]] = []
        before = analysis
        for idx, key in enumerate(plan):
            sent.append({"idx": idx, "key": key, "send": self.send_requested_key(key, self.default_delay_ms, self.default_gap_s)})
            time.sleep(1.2)
            after = self.analyze_current()
            sent[-1]["after"] = {k: v for k, v in after.items() if k not in {"focus"}}
            if idx == 0 and after.get("confirm_like") and not final_confirm:
                break
        event = {"ts": _now(), "type": "purchase_test_run", "confirm_purchase": confirm_purchase, "final_confirm": final_confirm, "plan": plan, "price_authorization": auth, "before": {k: v for k, v in before.items() if k != "focus"}, "sent": sent}
        self._append(event)
        purchase_record = None
        if final_confirm:
            purchase_record = self._record_purchase_spend(before, event)
        return {"ok": True, "ordered_or_advanced": True, "event": event, "purchase_record": purchase_record, "status": self.status()}
