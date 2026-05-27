#!/usr/bin/env python3
from __future__ import annotations

import json, logging, threading, time, uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from auto_crawler import AutonomousCrawler, SimilarityModel, ScreenFingerprint

log = logging.getLogger("merged.teacher")
SendRequestedKey = Callable[[str, Optional[int], float], Dict[str, Any]]


class ManualTeachingRecorder:
    """Records human-driven remote sessions as crawler graph transitions."""
    def __init__(self, data_dir: Path, crawler: AutonomousCrawler, capture_frame: Callable[[], Optional[np.ndarray]], capture_status: Callable[[], Dict[str, Any]], send_requested_key: SendRequestedKey) -> None:
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "manual_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.crawler = crawler
        self.capture_frame = capture_frame
        self.capture_status = capture_status
        self.send_requested_key = send_requested_key
        self._lock = threading.RLock()
        self._active: Optional[Dict[str, Any]] = None
        self._latest_session_file: Optional[Path] = None
        self._last_error = ""
        # v14: fast manual teaching. Button sends return immediately and learning
        # is flushed as a burst after the operator pauses briefly. This preserves
        # fast human-like sequences while still teaching before→sequence→after.
        self.fast_recording_enabled = True
        self.burst_idle_s = 0.75
        self._burst_lock = threading.RLock()
        self._burst_timer: Optional[threading.Timer] = None
        self._burst: Optional[Dict[str, Any]] = None

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @property
    def active(self) -> bool:
        with self._lock:
            return bool(self._active)

    def _path(self, sid: str) -> Path:
        return self.sessions_dir / f"{sid}.json"

    def _save_active(self) -> None:
        with self._lock:
            if not self._active:
                return
            path = self._path(self._active["session_id"])
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._active, indent=2), encoding="utf-8")
            tmp.replace(path)
            self._latest_session_file = path

    def start(self, name: str = "", notes: str = "", operator: str = "human") -> Dict[str, Any]:
        with self._lock:
            if self._active:
                return self.status()
            sid = f"teach_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            self._active = {
                "schema": "jamboree_manual_teaching_session_v1",
                "session_id": sid,
                "name": name or "Manual teaching session",
                "notes": notes or "",
                "operator": operator or "human",
                "started_at": self.now(),
                "stopped_at": None,
                "active": True,
                "events": [],
                "summary": {"button_count": 0, "transition_count": 0, "created_state_count": 0, "new_edge_count": 0, "noop_count": 0, "total_reward": 0.0, "start_state": "", "last_state": "", "buttons": []},
            }
        try:
            fp = self._capture_fingerprint("teach_start")
            state_id, created, cmp = self.crawler.graph.upsert_state(fp, self.crawler.config.state_similarity_threshold)
            self.crawler.graph.root_state = self.crawler.graph.root_state or state_id
            with self._lock:
                self._active["summary"]["start_state"] = state_id
                self._active["summary"]["last_state"] = state_id
                self._active["events"].append({"ts": self.now(), "type": "session_start_state", "state_id": state_id, "created": created, "similarity": cmp, "state": self.crawler._state_summary(state_id)})
            self.crawler.graph.save(); self.crawler.brain.save(); self._save_active()
        except Exception as exc:
            self._last_error = str(exc); log.exception("manual teaching start context failed")
        return self.status()

    def stop(self) -> Dict[str, Any]:
        # Finish any pending fast burst before closing the session.
        self._flush_burst_safe()
        with self._lock:
            if not self._active:
                return self.status()
            self._active["active"] = False
            self._active["stopped_at"] = self.now()
            path = self._path(self._active["session_id"])
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._active, indent=2), encoding="utf-8")
            tmp.replace(path)
            self._latest_session_file = path
            session = self._active
            self._active = None
        return {"ok": True, "active": False, "session": session, "session_file": str(path)}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            active = self._active
            latest = self._latest_session_file
        latest_summary = None
        if latest and latest.is_file():
            try:
                raw = json.loads(latest.read_text(encoding="utf-8"))
                latest_summary = {"session_id": raw.get("session_id"), "name": raw.get("name"), "started_at": raw.get("started_at"), "stopped_at": raw.get("stopped_at"), "summary": raw.get("summary", {}), "file": str(latest)}
            except Exception as exc:
                latest_summary = {"file": str(latest), "error": str(exc)}
        with self._burst_lock:
            pending = dict(self._burst or {})
            if pending.get("before_fp") is not None:
                pending["before_fp"] = "<ScreenFingerprint>"
        return {"ok": True, "active": bool(active), "active_session": active, "latest_session": latest_summary, "sessions_dir": str(self.sessions_dir), "last_error": self._last_error, "fast_recording_enabled": self.fast_recording_enabled, "pending_burst": pending}

    def list_sessions(self, limit: int = 20) -> Dict[str, Any]:
        rows = []
        for path in sorted(self.sessions_dir.glob("teach_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:max(1, int(limit))]:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                rows.append({"session_id": raw.get("session_id"), "name": raw.get("name"), "started_at": raw.get("started_at"), "stopped_at": raw.get("stopped_at"), "active": raw.get("active"), "summary": raw.get("summary", {}), "file": str(path)})
            except Exception as exc:
                rows.append({"file": str(path), "error": str(exc)})
        return {"ok": True, "count": len(rows), "sessions": rows}

    def _capture_frame_or_raise(self) -> np.ndarray:
        frame = self.capture_frame()
        if frame is None or not getattr(frame, "size", 0):
            raise RuntimeError("no capture frame available")
        return frame.copy()

    def _capture_fingerprint(self, hint_prefix: str) -> ScreenFingerprint:
        return self.crawler.extractor.extract(self._capture_frame_or_raise(), hint_id=f"{hint_prefix}_{uuid.uuid4().hex[:10]}")

    def _state_fp_for_last_state(self) -> tuple[str, ScreenFingerprint]:
        with self._lock:
            if not self._active:
                raise RuntimeError("manual teaching session is not active")
            sid = str((self._active.get("summary") or {}).get("last_state") or "")
        node = self.crawler.graph.nodes.get(sid)
        if node:
            return sid, node.representative
        fp = self.crawler.capture_fingerprint("teach_fast_before", perception="fast")
        sid, _, _ = self.crawler.graph.upsert_state(fp, self.crawler.config.state_similarity_threshold)
        return sid, fp

    def _make_transition_sample(self, session_id: str, requested_key: str, before_id: str, before_fp: ScreenFingerprint, after_id: str, after_fp: ScreenFingerprint, send_result: Dict[str, Any], note: str, t0: float, created: bool, cmp_to_known: Dict[str, Any], edge_existed: bool, reward: float, reward_details: Dict[str, Any], timing_debug: Dict[str, Any]) -> Dict[str, Any]:
        before_summary = self.crawler._state_summary(before_id)
        after_summary = self.crawler._state_summary(after_id)
        return {
            "source": timing_debug.get("source") or ("manual_teaching_fast" if timing_debug.get("mode") == "burst_checkpoint" else "manual_teaching"),
            "operator_auto": bool(timing_debug.get("operator_auto", False)),
            "session_id": session_id, "note": note or "",
            "before_state": before_id, "after_state": after_id, "button": str(requested_key), "button_sequence": self.crawler._action_sequence_for_display(str(requested_key)),
            "before": {**before_summary, "screenshot": before_fp.screenshot, "ocr_text": before_fp.ocr_text, "ocr_tokens": before_fp.ocr_tokens, "focus": before_fp.focus, "focus_label": self.crawler.focus_label(before_fp), "phash": before_fp.phash, "brightness": before_fp.brightness, "entropy": before_fp.entropy},
            "after": {**after_summary, "screenshot": after_fp.screenshot, "ocr_text": after_fp.ocr_text, "ocr_tokens": after_fp.ocr_tokens, "focus": after_fp.focus, "focus_label": self.crawler.focus_label(after_fp), "phash": after_fp.phash, "brightness": after_fp.brightness, "entropy": after_fp.entropy},
            "ocr_delta": {"new_tokens": sorted(set(after_fp.ocr_tokens)-set(before_fp.ocr_tokens))[:50], "lost_tokens": sorted(set(before_fp.ocr_tokens)-set(after_fp.ocr_tokens))[:50], "before_focus": self.crawler.focus_label(before_fp), "after_focus": self.crawler.focus_label(after_fp), "focus_changed": self.crawler.focus_label(before_fp) != self.crawler.focus_label(after_fp)},
            "before_after_similarity": SimilarityModel.compare(before_fp, after_fp), "known_similarity": cmp_to_known, "send": send_result, "created_state": created, "changed": (after_id != before_id or SimilarityModel.compare(before_fp, after_fp)["score"] < self.crawler.config.changed_similarity_threshold), "reward": round(float(reward),4), "reward_details": reward_details, "timing": timing_debug, "elapsed_s": round(time.time()-t0,3), "edge_existed": edge_existed,
        }

    def _learn_transition(self, session_id: str, requested_key: str, before_id: str, before_fp: ScreenFingerprint, after_fp: ScreenFingerprint, send_result: Dict[str, Any], note: str, t0: float, timing_debug: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cfg = self.crawler.config
        after_id, created, cmp_to_known = self.crawler.graph.upsert_state(after_fp, cfg.state_similarity_threshold)
        cmp_before_after = SimilarityModel.compare(before_fp, after_fp)
        changed = cmp_before_after["score"] < cfg.changed_similarity_threshold or after_id != before_id
        confidence = max(0.70, 1.0 - cmp_before_after["score"]) if changed else max(0.30, cmp_before_after["score"])
        if after_id != before_id:
            confidence = max(confidence, cmp_to_known.get("score", 0.5))
        confidence = max(0.05, min(1.0, float(confidence)))
        edge_key = self.crawler.graph.edge_key(before_id, str(requested_key), after_id)
        edge_existed = edge_key in self.crawler.graph.edges
        reward, reward_details = self.crawler.brain.score_observation(cfg, str(requested_key), before_fp, after_fp, created=created, changed=changed)
        demonstration_bonus = 12.0 if timing_debug.get("operator_auto") else 8.0
        reward += demonstration_bonus
        reward_details["manual_demonstration_reward"] = demonstration_bonus
        if timing_debug.get("operator_auto"):
            reward_details["operator_customer_path_weight"] = demonstration_bonus
        if changed and not edge_existed:
            reward += cfg.reward_new_edge
            reward_details["new_edge_reward"] = cfg.reward_new_edge
        if after_id != before_id and self.crawler.remaining_actions_for_state(after_id):
            reward += cfg.reward_leads_to_unexplored
            reward_details["leads_to_unexplored_reward"] = cfg.reward_leads_to_unexplored
        sample = self._make_transition_sample(session_id, requested_key, before_id, before_fp, after_id, after_fp, send_result, note, t0, created, cmp_to_known, edge_existed, reward, reward_details, timing_debug or {})
        edge = self.crawler.graph.record_edge(before_id, str(requested_key), after_id, changed=changed, success=True, confidence=confidence, sample=sample)
        stat = self.crawler.brain.update_state_action(before_id, str(requested_key), after_id, reward, True, not changed, bool(created or not edge_existed or reward_details.get("new_tokens") or reward_details.get("new_screen_title") or reward_details.get("new_setting_pairs")))
        self.crawler.brain.update_reward(str(requested_key), 8.0)
        try:
            src = str((timing_debug or {}).get("source") or "manual_teaching")
            weight = 3.5 if (timing_debug or {}).get("operator_auto") else 2.5
            self.crawler.sequence_learner.record_action(before_id, str(requested_key), after_id, reward=reward, time_s=float((timing_debug or {}).get("response_s") or 0.0), source=src, weight=weight)
            self.crawler.sequence_learner.mine_sequences(min_occurrences=2, min_avg_reward=2.0)
        except Exception:
            log.debug("manual demonstration sequence learner update failed", exc_info=True)
        self.crawler.graph.save(); self.crawler.brain.save()
        before_summary = self.crawler._state_summary(before_id); after_summary = self.crawler._state_summary(after_id)
        event = {"ts": self.now(), "type": "button_transition", "button": str(requested_key), "before_state": before_id, "after_state": after_id, "before_label": before_summary.get("label"), "after_label": after_summary.get("label"), "before_focus": self.crawler.focus_label(before_fp), "after_focus": self.crawler.focus_label(after_fp), "changed": changed, "created_state": created, "new_edge": not edge_existed, "confidence": round(float(edge.confidence),4), "reward": round(float(reward),4), "response_s": round(float((timing_debug or {}).get("response_s", 0.0)),3), "note": note or ""}
        with self._lock:
            if self._active:
                self._active["events"].append(event)
                s = self._active["summary"]
                s["button_count"] += len(self.crawler._action_sequence_for_display(str(requested_key)))
                s["transition_count"] += 1; s["created_state_count"] += 1 if created else 0; s["new_edge_count"] += 1 if not edge_existed else 0; s["noop_count"] += 0 if changed else 1; s["total_reward"] = round(float(s.get("total_reward",0.0)) + float(reward),4); s["last_state"] = after_id; s.setdefault("buttons", []).append(str(requested_key)); s["buttons"] = s["buttons"][-200:]
        self._save_active()
        log.info("manual teaching transition learned %s", event)
        return {"ok": True, "recorded": True, "session_id": session_id, "event": event, "edge": asdict(edge), "state_action": asdict(stat), "sample": sample}

    def record_button_fast(self, requested_key: str, delay_ms: Optional[int] = None, gap_s: float = 0.075, note: str = "", operator_auto: bool = False, source: str = "manual_teaching_fast") -> Dict[str, Any]:
        """Send immediately and learn a burst transition after the operator pauses.

        This is the v14 teacher mode: button pressing stays human-fast, while
        perception/graph learning happens at checkpoint boundaries.
        """
        with self._lock:
            if not self._active:
                raise RuntimeError("manual teaching session is not active")
            session_id = self._active["session_id"]
        before_id, before_fp = self._state_fp_for_last_state()
        t0 = time.time()
        send_result = self.send_requested_key(str(requested_key), delay_ms, float(gap_s))
        with self._lock:
            if self._active:
                self._active["events"].append({"ts": self.now(), "type": "button_sent_pending", "button": str(requested_key), "before_state": before_id, "fast": True})
        with self._burst_lock:
            if self._burst is None:
                self._burst = {"session_id": session_id, "before_id": before_id, "before_fp": before_fp, "keys": [], "send_results": [], "note": note or "", "t0": t0, "operator_auto": bool(operator_auto), "source": source}
            self._burst["keys"].append(str(requested_key))
            self._burst["send_results"].append(send_result)
            if note:
                self._burst["note"] = (self._burst.get("note", "") + " " + note).strip()
            if self._burst_timer:
                self._burst_timer.cancel()
            self._burst_timer = threading.Timer(self.burst_idle_s, self._flush_burst_safe)
            self._burst_timer.daemon = True
            self._burst_timer.start()
        self._save_active()
        return {"ok": True, "sent": True, "recording": "pending_burst", "session_id": session_id, "button": str(requested_key), "before_state": before_id, "gap_s": gap_s, "send": send_result}

    def flush_pending(self) -> Dict[str, Any]:
        return self._flush_burst_safe()

    def _flush_burst_safe(self) -> Dict[str, Any]:
        with self._burst_lock:
            burst = self._burst
            self._burst = None
            self._burst_timer = None
        if not burst:
            return {"ok": True, "flushed": False}
        try:
            # Let the last screen settle slightly, then perform one deep checkpoint.
            time.sleep(0.15)
            after_fp = self.crawler.capture_fingerprint("teach_burst_after", perception="full")
            keys = [str(k) for k in burst.get("keys", [])]
            action = keys[0] if len(keys) == 1 else ",".join(keys)
            send_result = {"ok": True, "burst": True, "sent": burst.get("send_results", []), "count": len(keys)}
            timing_debug = {"mode": "burst_checkpoint", "response_s": round(time.time() - float(burst.get("t0") or time.time()), 3), "keys": keys, "operator_auto": bool(burst.get("operator_auto", False)), "source": str(burst.get("source") or "manual_teaching_fast")}
            return self._learn_transition(str(burst["session_id"]), action, str(burst["before_id"]), burst["before_fp"], after_fp, send_result, str(burst.get("note") or ""), float(burst.get("t0") or time.time()), timing_debug)
        except Exception as exc:
            self._last_error = str(exc)
            log.exception("manual teaching burst flush failed")
            return {"ok": False, "error": str(exc)}

    def record_button(self, requested_key: str, delay_ms: Optional[int] = None, gap_s: float = 0.2, note: str = "") -> Dict[str, Any]:
        with self._lock:
            if not self._active:
                raise RuntimeError("manual teaching session is not active")
            session_id = self._active["session_id"]
        cfg = self.crawler.config
        before_fp = self._capture_fingerprint("teach_before")
        before_id, _, _ = self.crawler.graph.upsert_state(before_fp, cfg.state_similarity_threshold)
        t0 = time.time()
        send_result = self.send_requested_key(str(requested_key), delay_ms, float(gap_s))
        after_fp, response_s, timing_debug = self.crawler.wait_after_action(str(requested_key), before_fp)
        after_id, created, cmp_to_known = self.crawler.graph.upsert_state(after_fp, cfg.state_similarity_threshold)
        cmp_before_after = SimilarityModel.compare(before_fp, after_fp)
        changed = cmp_before_after["score"] < cfg.changed_similarity_threshold or after_id != before_id
        confidence = max(0.70, 1.0 - cmp_before_after["score"]) if changed else max(0.30, cmp_before_after["score"])
        if after_id != before_id:
            confidence = max(confidence, cmp_to_known.get("score", 0.5))
        confidence = max(0.05, min(1.0, float(confidence)))
        edge_key = self.crawler.graph.edge_key(before_id, str(requested_key), after_id)
        edge_existed = edge_key in self.crawler.graph.edges
        reward, reward_details = self.crawler.brain.score_observation(cfg, str(requested_key), before_fp, after_fp, created=created, changed=changed)
        demonstration_bonus = 12.0 if timing_debug.get("operator_auto") else 8.0
        reward += demonstration_bonus
        reward_details["manual_demonstration_reward"] = demonstration_bonus
        if timing_debug.get("operator_auto"):
            reward_details["operator_customer_path_weight"] = demonstration_bonus
        if changed and not edge_existed:
            reward += cfg.reward_new_edge
            reward_details["new_edge_reward"] = cfg.reward_new_edge
        if after_id != before_id and self.crawler.remaining_actions_for_state(after_id):
            reward += cfg.reward_leads_to_unexplored
            reward_details["leads_to_unexplored_reward"] = cfg.reward_leads_to_unexplored
        channel = self.crawler.brain.parse_channel_action(str(requested_key))
        channel_record = None
        if channel is not None:
            channel_record = self.crawler.brain.learn_channel(channel, after_id, after_fp, confidence)
            reward_details["channel_learning"] = asdict(channel_record)
        before_summary = self.crawler._state_summary(before_id)
        after_summary = self.crawler._state_summary(after_id)
        sample = {
            "source": "manual_teaching", "session_id": session_id, "note": note or "",
            "before_state": before_id, "after_state": after_id, "button": str(requested_key), "button_sequence": self.crawler._action_sequence_for_display(str(requested_key)),
            "before": {**before_summary, "screenshot": before_fp.screenshot, "ocr_text": before_fp.ocr_text, "ocr_tokens": before_fp.ocr_tokens, "focus": before_fp.focus, "focus_label": self.crawler.focus_label(before_fp), "phash": before_fp.phash, "brightness": before_fp.brightness, "entropy": before_fp.entropy},
            "after": {**after_summary, "screenshot": after_fp.screenshot, "ocr_text": after_fp.ocr_text, "ocr_tokens": after_fp.ocr_tokens, "focus": after_fp.focus, "focus_label": self.crawler.focus_label(after_fp), "phash": after_fp.phash, "brightness": after_fp.brightness, "entropy": after_fp.entropy},
            "ocr_delta": {"new_tokens": sorted(set(after_fp.ocr_tokens)-set(before_fp.ocr_tokens))[:50], "lost_tokens": sorted(set(before_fp.ocr_tokens)-set(after_fp.ocr_tokens))[:50], "before_focus": self.crawler.focus_label(before_fp), "after_focus": self.crawler.focus_label(after_fp), "focus_changed": self.crawler.focus_label(before_fp) != self.crawler.focus_label(after_fp)},
            "before_after_similarity": cmp_before_after, "known_similarity": cmp_to_known, "send": send_result, "created_state": created, "changed": changed, "reward": round(float(reward),4), "reward_details": reward_details, "timing": timing_debug, "response_s": round(float(response_s),3), "elapsed_s": round(time.time()-t0,3), "edge_existed": edge_existed, "channel": asdict(channel_record) if channel_record else None,
        }
        edge = self.crawler.graph.record_edge(before_id, str(requested_key), after_id, changed=changed, success=True, confidence=confidence, sample=sample)
        stat = self.crawler.brain.update_state_action(before_id, str(requested_key), after_id, reward, True, not changed, bool(created or not edge_existed or reward_details.get("new_tokens") or reward_details.get("new_screen_title") or reward_details.get("new_setting_pairs")))
        self.crawler.brain.update_reward(str(requested_key), 8.0)
        try:
            src = str((timing_debug or {}).get("source") or "manual_teaching")
            weight = 3.5 if (timing_debug or {}).get("operator_auto") else 2.5
            self.crawler.sequence_learner.record_action(before_id, str(requested_key), after_id, reward=reward, time_s=float((timing_debug or {}).get("response_s") or 0.0), source=src, weight=weight)
            self.crawler.sequence_learner.mine_sequences(min_occurrences=2, min_avg_reward=2.0)
        except Exception:
            log.debug("manual demonstration sequence learner update failed", exc_info=True)
        self.crawler.graph.save(); self.crawler.brain.save()
        event = {"ts": self.now(), "type": "button_transition", "button": str(requested_key), "before_state": before_id, "after_state": after_id, "before_label": before_summary.get("label"), "after_label": after_summary.get("label"), "before_focus": self.crawler.focus_label(before_fp), "after_focus": self.crawler.focus_label(after_fp), "changed": changed, "created_state": created, "new_edge": not edge_existed, "confidence": round(float(edge.confidence),4), "reward": round(float(reward),4), "response_s": round(float(response_s),3), "note": note or ""}
        with self._lock:
            if self._active:
                self._active["events"].append(event)
                s = self._active["summary"]
                s["button_count"] += 1; s["transition_count"] += 1; s["created_state_count"] += 1 if created else 0; s["new_edge_count"] += 1 if not edge_existed else 0; s["noop_count"] += 0 if changed else 1; s["total_reward"] = round(float(s.get("total_reward",0.0)) + float(reward),4); s["last_state"] = after_id; s.setdefault("buttons", []).append(str(requested_key)); s["buttons"] = s["buttons"][-200:]
        self._save_active()
        log.info("manual teaching transition learned %s", event)
        return {"ok": True, "recorded": True, "session_id": session_id, "event": event, "edge": asdict(edge), "state_action": asdict(stat), "sample": sample}

    def annotate(self, text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        with self._lock:
            if not self._active:
                raise RuntimeError("manual teaching session is not active")
            event = {"ts": self.now(), "type": "annotation", "text": text, "tags": tags or []}
            self._active["events"].append(event)
        self._save_active()
        return {"ok": True, "event": event}

    def start_autonomous_from_current(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.crawler.status().get("running"):
            return {"ok": False, "error": "crawler is already running", "status": self.crawler.status()}
        base = {"home_first": False, "start_sequence": [], "continuous_exploration_enabled": True, "reseed_when_idle": True, "max_steps": 0, "max_states": 0, "max_depth": 18, "max_action_attempts_per_state": 3, "self_explore_enabled": True, "adaptive_timing_enabled": True}
        if overrides:
            base.update(overrides)
        return self.crawler.start(base)
