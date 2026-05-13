#!/usr/bin/env python3
"""Parental-control workflow assistant for the Jamboree autonomous crawler.

The agent does not hard-code one fragile button script. It uses the crawler's
learned graph, focus/context perception, OCR recovery, PIN-popup detection, and
safe key sending to run a human-style verify loop:

  navigate to settings -> inspect -> move/select -> inspect -> enter PIN when prompted
  tune blocked channel -> verify parental PIN popup -> unlock -> disable controls

It remembers only the PIN you explicitly ask it to set/use, stored locally in
crawler_data/parental_control_memory.json.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PIN_RE = re.compile(r"\b(pin|passcode|password|locked|unlock|enter.{0,20}(?:code|pin|password)|parental.{0,20}(?:code|pin|password))\b", re.I)
ON_OFF_RE = re.compile(r"\b(on|off|enabled|disabled|locked|unlocked)\b", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


@dataclass
class ParentalMemory:
    schema: str = "jamboree_parental_control_memory_v1"
    updated_at: str = ""
    pin: str = ""
    last_blocked_channel: Optional[int] = None
    last_verified_at: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)


class ParentalControlAgent:
    def __init__(self, crawler: Any, data_dir: Path) -> None:
        self.crawler = crawler
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "parental_control_memory.json"
        self.memory = self.load()

    def load(self) -> ParentalMemory:
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return ParentalMemory(**{k: v for k, v in data.items() if k in ParentalMemory.__dataclass_fields__})
            except Exception:
                pass
        return ParentalMemory(updated_at=_now())

    def save(self) -> None:
        self.memory.updated_at = _now()
        self.path.write_text(json.dumps(asdict(self.memory), indent=2), encoding="utf-8")

    def event(self, message: str, **data: Any) -> Dict[str, Any]:
        evt = {"ts": _now(), "message": message, **data}
        self.memory.events.append(evt)
        self.memory.events = self.memory.events[-120:]
        self.save()
        return evt

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "memory_file": str(self.path),
            "pin_set": bool(self.memory.pin),
            "pin_length": len(self.memory.pin or ""),
            "last_blocked_channel": self.memory.last_blocked_channel,
            "last_verified_at": self.memory.last_verified_at,
            "recent_events": self.memory.events[-20:],
        }

    def remember_pin(self, pin: str) -> Dict[str, Any]:
        pin = re.sub(r"\D+", "", str(pin or ""))
        if not (4 <= len(pin) <= 8):
            return {"ok": False, "error": "pin_must_be_4_to_8_digits"}
        self.memory.pin = pin
        self.event("remembered parental control PIN", pin_length=len(pin))
        return self.status()

    def _current_focus(self) -> Dict[str, Any]:
        try:
            return self.crawler.analyze_focus_current()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _focus_text(payload: Dict[str, Any]) -> str:
        f = payload.get("focus") or (payload.get("state") or {}).get("representative", {}).get("focus") or {}
        parts = []
        for key in ("human_label", "screen_title", "page_name", "block_title", "focused_item", "focused_value", "context_text", "row_text", "header_text", "action_bar_text", "recovery_text", "popup_type"):
            parts.append(str(f.get(key) or ""))
        ui = f.get("ui_context") or {}
        if isinstance(ui, dict):
            parts.extend(str(ui.get(k) or "") for k in ("context_summary", "screen_title", "focused_item", "focused_value"))
        return _norm(" ".join(parts))

    @staticmethod
    def _is_pin_prompt(payload: Dict[str, Any]) -> bool:
        f = payload.get("focus") or {}
        if f.get("pin_required") or str(f.get("popup_type") or "").endswith("pin_prompt"):
            return True
        return bool(PIN_RE.search(ParentalControlAgent._focus_text(payload)))

    def enter_pin(self, pin: Optional[str] = None, submit: bool = True, digit_gap_s: float = 0.09) -> Dict[str, Any]:
        pin = re.sub(r"\D+", "", str(pin or self.memory.pin or ""))
        if not pin:
            return {"ok": False, "error": "no_pin_available"}
        events = []
        for digit in pin:
            events.append({"key": digit, "result": self.crawler.safe_send(digit)})
            time.sleep(max(0.03, float(digit_gap_s)))
        if submit:
            # DISH screens vary: some submit automatically on final digit, some want SELECT.
            events.append({"key": "select", "result": self.crawler.safe_send("select")})
        self.event("entered PIN", pin_length=len(pin), submit=submit)
        time.sleep(0.8)
        after = self._current_focus()
        return {"ok": True, "entered_digits": len(pin), "submit": submit, "events": events, "after": after}

    def maybe_enter_pin(self, pin: Optional[str] = None) -> Dict[str, Any]:
        cur = self._current_focus()
        if not self._is_pin_prompt(cur):
            return {"ok": True, "pin_prompt": False, "current": cur}
        entered = self.enter_pin(pin=pin)
        return {"ok": bool(entered.get("ok")), "pin_prompt": True, "entered": entered}

    def navigate_to_parental_settings(self, dry_run: bool = False) -> Dict[str, Any]:
        # Try the most specific learned query first, then broader fallbacks.
        queries = ["Parental Control Settings", "parental controls", "locked channels", "TV Viewing Options", "settings"]
        plans = []
        for q in queries:
            plan = self.crawler.plan_route(query=q)
            plans.append({"query": q, "plan": plan})
            if plan.get("ok"):
                if dry_run:
                    return {"ok": True, "dry_run": True, "selected_query": q, "plan": plan, "plans": plans}
                nav = self.crawler.navigate_to_target(query=q, dry_run=False)
                self.event("navigated toward parental settings", query=q, ok=bool(nav.get("ok")))
                pin = self.maybe_enter_pin()
                return {"ok": bool(nav.get("ok")), "selected_query": q, "navigation": nav, "pin_check": pin, "plans": plans}
        return {"ok": False, "error": "no_learned_parental_settings_route", "plans": plans}

    def find_and_select_text(self, targets: List[str], max_moves: int = 24, dry_run: bool = False) -> Dict[str, Any]:
        targets_l = [t.lower() for t in targets if t]
        probe_actions = ["down", "right", "down", "left", "up", "right"]
        trace = []
        seen = set()
        for i in range(max(1, int(max_moves))):
            cur = self._current_focus()
            txt = self._focus_text(cur)
            label = (cur.get("focus") or {}).get("human_label") or txt[:80]
            trace.append({"step": i, "label": label, "text": txt[:220]})
            if any(t in txt.lower() for t in targets_l):
                if dry_run:
                    return {"ok": True, "dry_run": True, "matched": True, "targets": targets, "trace": trace}
                res = self.crawler.safe_send("select")
                time.sleep(0.8)
                self.event("selected target text", targets=targets, label=label)
                return {"ok": True, "matched": True, "targets": targets, "select": res, "after": self._current_focus(), "trace": trace}
            key = (label, txt[:80])
            if key in seen and i > 5:
                # Try Back then Down like a human stuck in a loop.
                action = "back" if i % 2 else "down"
            else:
                action = probe_actions[i % len(probe_actions)]
            seen.add(key)
            if dry_run:
                continue
            self.crawler.safe_send(action)
            time.sleep(self.crawler.brain.expected_settle_s(action, self.crawler.config))
        return {"ok": False, "error": "target_text_not_found", "targets": targets, "trace": trace}


    @staticmethod
    def _focus_primary_text(payload: Dict[str, Any]) -> str:
        """Text that appears to belong to the currently selected/focused item only.

        _focus_text() intentionally includes surrounding context. That is great for
        understanding a screen, but dangerous for selecting: if the current screen
        merely contains the word Settings somewhere, we must not press SELECT unless
        the red focus itself appears to be on Settings.
        """
        f = payload.get("focus") or (payload.get("state") or {}).get("representative", {}).get("focus") or {}
        parts = []
        for key in (
            "focused_item", "focused_value", "label_text", "focus_text", "human_label",
            "focus_ocr", "primary_text", "selected_text",
        ):
            v = str(f.get(key) or "").strip()
            if v:
                parts.append(v)
        ui = f.get("ui_context") or {}
        if isinstance(ui, dict):
            for key in ("focused_item", "focused_value", "human_label"):
                v = str(ui.get(key) or "").strip()
                if v:
                    parts.append(v)
        return _norm(" ".join(parts))

    def _send_sequence(self, sequence: List[str], label: str = "sequence", dry_run: bool = False, settle_extra_s: float = 0.0) -> Dict[str, Any]:
        steps = []
        for raw in sequence:
            key = str(raw or "").strip()
            if not key:
                continue
            if dry_run:
                steps.append({"key": key, "dry_run": True})
                continue
            before = self._current_focus()
            result = self.crawler.safe_send(key)
            wait_s = self.crawler.brain.expected_settle_s(key, self.crawler.config) + max(0.0, settle_extra_s)
            time.sleep(wait_s)
            after = self._current_focus()
            steps.append({
                "key": key,
                "result": result,
                "wait_s": round(wait_s, 3),
                "before_label": (before.get("focus") or {}).get("human_label") or before.get("focus_label"),
                "after_label": (after.get("focus") or {}).get("human_label") or after.get("focus_label"),
                "after_state": after.get("state_id"),
            })
        self.event("executed " + label, count=len(steps), dry_run=dry_run)
        return {"ok": True, "label": label, "dry_run": dry_run, "steps": steps}

    def find_and_select_focused_text(self, targets: List[str], max_moves: int = 36, dry_run: bool = False, prefer_actions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Move focus around until the selected/focused item itself matches a target.

        This is the active fallback that v11 was missing. It behaves more like a
        human scanning a menu: read current selection, move, read again, only press
        SELECT when the red focus is actually on the intended item.
        """
        targets_l = [str(t).lower() for t in targets if str(t or "").strip()]
        if not targets_l:
            return {"ok": False, "error": "no_targets"}
        actions = prefer_actions or ["right", "right", "right", "right", "right", "down", "left", "left", "left", "left", "left", "down", "right", "right", "right", "right", "right", "up", "up"]
        trace = []
        seen = set()
        for i in range(max(1, int(max_moves))):
            cur = self._current_focus()
            primary = self._focus_primary_text(cur)
            broad = self._focus_text(cur)
            focus = cur.get("focus") or {}
            label = focus.get("human_label") or cur.get("focus_label") or primary or broad[:80]
            matched_primary = any(t in primary.lower() for t in targets_l)
            matched_human_label = any(t in str(label).lower() for t in targets_l)
            trace.append({
                "step": i,
                "label": str(label)[:120],
                "primary_text": primary[:200],
                "context_text": broad[:240],
                "matched_primary": matched_primary,
            })
            if matched_primary or matched_human_label:
                if dry_run:
                    return {"ok": True, "dry_run": True, "matched": True, "targets": targets, "trace": trace, "would_select": label}
                res = self.crawler.safe_send("select")
                time.sleep(0.9)
                after = self._current_focus()
                self.event("selected focused target text", targets=targets, selected=str(label)[:120])
                return {"ok": True, "matched": True, "targets": targets, "select": res, "after": after, "trace": trace}
            signature = (str(label)[:80], primary[:80], (focus.get("bbox") or focus.get("focus_bbox") or ""))
            # If we are looping, use BACK once, then resume scanning. This helps escape popups/submenus.
            if signature in seen and i > 8:
                action = "back" if (i % 7 == 0) else actions[i % len(actions)]
            else:
                action = actions[i % len(actions)]
            seen.add(signature)
            if dry_run:
                continue
            self.crawler.safe_send(action)
            time.sleep(self.crawler.brain.expected_settle_s(action, self.crawler.config))
        return {"ok": False, "error": "focused_target_text_not_found", "targets": targets, "trace": trace}

    def active_discover_parental_settings(self, dry_run: bool = False) -> Dict[str, Any]:
        """Best-effort active fallback when no learned route exists.

        It starts from HOME, selects Settings when focus reaches it, then scans for
        Parental/Locks/TV Viewing options. It does not toggle anything by itself;
        it only navigates/selects toward the parental-control area.
        """
        result: Dict[str, Any] = {"ok": False, "dry_run": dry_run, "mode": "active_discovery", "stages": []}
        result["stages"].append({"name": "anchor_home", **self._send_sequence(["home"], label="anchor_home", dry_run=dry_run, settle_extra_s=0.5)})
        if dry_run:
            result["stages"].append({
                "name": "find_settings",
                "plan": "Scan focus with RIGHT/DOWN/LEFT until the focused item itself reads Settings, then SELECT.",
            })
            result["stages"].append({
                "name": "find_parental_area",
                "plan": "Inside Settings, scan for Parental / Locks / Locked Channels / TV Viewing Options, then SELECT.",
            })
            result["ok"] = True
            return result

        settings = self.find_and_select_focused_text(["Settings"], max_moves=32, dry_run=False,
                                                     prefer_actions=["right", "right", "right", "right", "right", "down", "left", "left", "left", "left", "left", "up"])
        result["stages"].append({"name": "find_settings", "result": settings})
        if not settings.get("ok"):
            self.event("active parental discovery could not select Settings", ok=False)
            return result
        pin = self.maybe_enter_pin()
        result["stages"].append({"name": "pin_check_after_settings", "result": pin})

        parental = self.find_and_select_focused_text(
            ["Parental", "Locks", "Locked Channels", "TV Viewing Options", "Control", "TV Activity"],
            max_moves=48,
            dry_run=False,
            prefer_actions=["down", "down", "right", "right", "left", "left", "down", "up", "right", "down"],
        )
        result["stages"].append({"name": "find_parental_area", "result": parental})
        result["ok"] = bool(parental.get("ok"))
        result["after"] = self._current_focus()
        self.event("active parental discovery completed", ok=result["ok"])
        return result

    def verify_blocked_channel(self, channel: int, pin: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        channel = int(channel)
        if dry_run:
            return {"ok": True, "dry_run": True, "plan": [f"tune {channel}", "detect PIN popup", "enter remembered PIN", "verify popup clears"]}
        tune = self.crawler.navigate_to_target(channel=channel, dry_run=False)
        time.sleep(max(1.0, self.crawler.config.channel_tune_settle_s))
        cur = self._current_focus()
        pin_prompt = self._is_pin_prompt(cur)
        unlock = None
        if pin_prompt:
            unlock = self.enter_pin(pin=pin)
        after = self._current_focus()
        self.memory.last_blocked_channel = channel
        self.memory.last_verified_at = _now()
        self.event("verified blocked channel workflow", channel=channel, pin_prompt=pin_prompt)
        return {"ok": True, "channel": channel, "tune": tune, "pin_prompt_detected": pin_prompt, "before_unlock": cur, "unlock": unlock, "after": after}

    def setup_parental_controls(self, pin: str, blocked_channel: Optional[int] = None, dry_run: bool = True, final_sequence: Optional[List[str]] = None) -> Dict[str, Any]:
        remembered = self.remember_pin(pin)
        if not remembered.get("ok"):
            return remembered
        nav = self.navigate_to_parental_settings(dry_run=dry_run)
        response: Dict[str, Any] = {"ok": bool(nav.get("ok")), "dry_run": dry_run, "navigation": nav, "pin_length": len(self.memory.pin)}
        if dry_run:
            response["active_discovery_plan"] = self.active_discover_parental_settings(dry_run=True)
            response["recommended_human_strategy"] = [
                "Navigate to Parental Control Settings",
                "If prompted, enter the stored PIN",
                "Select Parental Controls / Locks / Locked Channels",
                "Set the PIN when prompted, entering it twice if confirmation appears",
                "Tune the blocked channel and verify the PIN popup appears",
            ]
            return response
        if not nav.get("ok"):
            # v12: if learned-route navigation is unavailable, actively search like a human.
            active = self.active_discover_parental_settings(dry_run=False)
            response["active_discovery"] = active
            response["ok"] = bool(active.get("ok"))
            if not active.get("ok"):
                response["recommended_human_strategy"] = [
                    "Use /intelligence to learn the route to Settings/Parental Control Settings first, or provide a final sequence.",
                    "The active fallback tried HOME -> Settings -> Parental/Locks but did not confidently land there.",
                ]
                return response
        # If a setup/confirm PIN prompt appears, enter it. If a supplied final sequence
        # is available for this specific STB UI version, apply it after navigation.
        response["pin_prompt_1"] = self.maybe_enter_pin(pin)
        response["select_parental_or_locks"] = self.find_and_select_focused_text(["Parental", "Locks", "Locked Channels", "TV Activity", "Control"], max_moves=18, dry_run=False)
        response["pin_prompt_2"] = self.maybe_enter_pin(pin)
        applied = []
        for key in final_sequence or []:
            applied.append({"key": key, "result": self.crawler.safe_send(str(key))})
            time.sleep(self.crawler.brain.expected_settle_s(str(key), self.crawler.config))
            pin_check = self.maybe_enter_pin(pin)
            if pin_check.get("pin_prompt"):
                applied.append({"pin_check": pin_check})
        response["applied_final_sequence"] = applied
        if blocked_channel:
            response["verify"] = self.verify_blocked_channel(int(blocked_channel), pin=pin, dry_run=False)
        return response

    def disable_parental_controls(self, pin: Optional[str] = None, dry_run: bool = True, final_sequence: Optional[List[str]] = None) -> Dict[str, Any]:
        pin = pin or self.memory.pin
        nav = self.navigate_to_parental_settings(dry_run=dry_run)
        response: Dict[str, Any] = {"ok": bool(nav.get("ok")), "dry_run": dry_run, "navigation": nav}
        if dry_run:
            response["active_discovery_plan"] = self.active_discover_parental_settings(dry_run=True)
            response["recommended_human_strategy"] = ["Navigate to Parental Control Settings", "Enter stored PIN when prompted", "Select parental lock/control row", "Change value to Off/Unlocked", "Confirm"]
            return response
        if not nav.get("ok"):
            active = self.active_discover_parental_settings(dry_run=False)
            response["active_discovery"] = active
            response["ok"] = bool(active.get("ok"))
            if not active.get("ok"):
                response["recommended_human_strategy"] = ["Use /intelligence to learn the route first, or provide a final disable sequence."]
                return response
        response["pin_prompt"] = self.maybe_enter_pin(pin)
        response["select_control"] = self.find_and_select_focused_text(["Parental", "Controls", "Locks", "Off", "Disable", "Unlocked"], max_moves=20, dry_run=False)
        applied = []
        for key in final_sequence or []:
            applied.append({"key": key, "result": self.crawler.safe_send(str(key))})
            time.sleep(self.crawler.brain.expected_settle_s(str(key), self.crawler.config))
            pin_check = self.maybe_enter_pin(pin)
            if pin_check.get("pin_prompt"):
                applied.append({"pin_check": pin_check})
        response["applied_final_sequence"] = applied
        response["after"] = self._current_focus()
        return response
