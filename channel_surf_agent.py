#!/usr/bin/env python3
"""Channel surfing, channel-step discovery, and guide/info alignment learner.

This module deliberately behaves like a human channel-surfing tester:
  1. tune or step to a channel
  2. wait for video to become healthy
  3. read live banner / Info / Guide context
  4. capture displayed receiver clock and compare it to wall-clock time
  5. document tuning time, active video health, channel/program guesses
  6. flag black screens, PPV/purchase contexts, guide/info mismatches, skipped channels

It does not confirm PPV purchases. It documents availability/pricing cues only.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from focus_detector import detect_focus
from video_health import classify_frame_signal
from time_context import extract_display_clock
from channel_metadata import extract_channel_metadata, choose_best_metadata, is_plausible_program_title, sanitize_program_title, is_plausible_channel_code

log = logging.getLogger("merged.channel_surf")

FrameCallback = Callable[[], Optional[np.ndarray]]
StatusCallback = Callable[[], Dict[str, Any]]
SendKeyCallback = Callable[[str], Dict[str, Any]]


PPV_RX = re.compile(r"\b(ppv|pay per view|rent|rental|order|purchase|buy|price|\$\d+|\d+\.\d{2})\b", re.I)
BLACK_OR_BLOCK_RX = re.compile(r"\b(unavailable|not authorized|blackout|blocked|parental|locked|subscription)\b", re.I)
CHANNEL_RX = re.compile(r"\b(?:ch(?:annel)?\s*)?(\d{2,4})(?:[\-\s]?\d{1,3})?\b", re.I)
PHONEISH_RX = re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b")


@dataclass
class ChannelSurfConfig:
    channels: List[int] = field(default_factory=list)
    start_channel: Optional[int] = None
    stop_channel: Optional[int] = None
    max_channels: int = 0
    digit_gap_s: float = 0.075
    suffix_key: str = "select"
    tune_timeout_s: float = 9.0
    post_tune_settle_s: float = 2.2
    info_settle_s: float = 1.4
    guide_settle_s: float = 2.0
    collect_info: bool = True
    collect_guide: bool = True
    recover_black: bool = True
    black_recovery_sequence: List[str] = field(default_factory=lambda: ["ch_up", "ch_down", "live"])

    # v20: channel-up/down discovery mode.  direct mode uses numeric tuning;
    # channel_up/channel_down starts with one numeric tune then steps the remote.
    surf_mode: str = "direct"  # direct, channel_up, channel_down
    use_channel_up_down: bool = False
    channel_step_key: str = "ch_up"
    channel_step_settle_s: float = 2.0
    stop_on_repeated_channel: bool = False
    max_same_channel_steps: int = 3


@dataclass
class ChannelObservation:
    channel: int
    ts: str
    ok: bool
    requested_channel: Optional[int] = None
    actual_channel_guess: str = ""
    actual_channel_source: str = ""
    previous_channel_guess: str = ""
    input_method: str = "direct_digits"
    navigation_key: str = ""
    skipped_channel_detected: bool = False
    skipped_channel_note: str = ""
    tune_start_s: float = 0.0
    tune_complete_s: float = 0.0
    live_health: Dict[str, Any] = field(default_factory=dict)
    info_health: Dict[str, Any] = field(default_factory=dict)
    guide_health: Dict[str, Any] = field(default_factory=dict)
    live_focus: Dict[str, Any] = field(default_factory=dict)
    info_focus: Dict[str, Any] = field(default_factory=dict)
    guide_focus: Dict[str, Any] = field(default_factory=dict)
    live_time_context: Dict[str, Any] = field(default_factory=dict)
    info_time_context: Dict[str, Any] = field(default_factory=dict)
    guide_time_context: Dict[str, Any] = field(default_factory=dict)
    live_metadata: Dict[str, Any] = field(default_factory=dict)
    info_metadata: Dict[str, Any] = field(default_factory=dict)
    guide_metadata: Dict[str, Any] = field(default_factory=dict)
    best_metadata: Dict[str, Any] = field(default_factory=dict)
    time_discrepancy_flags: List[str] = field(default_factory=list)
    info_text: str = ""
    guide_text: str = ""
    channel_name_guess: str = ""
    channel_code_guess: str = ""
    program_guess: str = ""
    program_title_guess: str = ""
    program_description_guess: str = ""
    guide_channel_guess: str = ""
    ppv_available: bool = False
    ppv_cues: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)
    recovery: List[Dict[str, Any]] = field(default_factory=list)


class ChannelSurfAgent:
    def __init__(
        self,
        data_dir: Path,
        capture_frame: FrameCallback,
        capture_status: StatusCallback,
        send_key: SendKeyCallback,
        default_delay_s: float = 0.08,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "channel_surf_log.json"
        self.capture_frame = capture_frame
        self.capture_status = capture_status
        self.send_key = send_key
        self.default_delay_s = float(default_delay_s)
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.running = False
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.last_error = ""
        self.last_observation: Optional[Dict[str, Any]] = None
        self.history: List[Dict[str, Any]] = self._load_history()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _load_history(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return list(raw.get("observations") or [])
            if isinstance(raw, list):
                return raw
        except Exception:
            log.exception("unable to load channel surf history")
        return []

    def save(self) -> None:
        payload = {
            "schema": "channel_surf_log_v5_banner_validation",
            "updated_at": self.now(),
            "observations": self.history[-20000:],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            recent = self.history[-50:]
            drift = sum(1 for o in recent for f in o.get("time_discrepancy_flags", []) if "drift" in str(f))
            skipped = sum(1 for o in recent if o.get("skipped_channel_detected"))
            return {
                "ok": True,
                "running": self.running,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "last_error": self.last_error,
                "count": len(self.history),
                "recent_time_discrepancies": drift,
                "recent_skipped_channel_steps": skipped,
                "last_observation": self.last_observation,
                "log_file": str(self.path),
            }

    def start(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self.running:
                return self.status()
            cfg = self.parse_config(overrides or {})
            self._stop.clear()
            self.running = True
            self.started_at = self.now()
            self.finished_at = None
            self.last_error = ""
            self._thread = threading.Thread(target=self._run_safe, args=(cfg,), name="ChannelSurfAgent", daemon=True)
            self._thread.start()
            return self.status()

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        return self.status()

    def parse_config(self, raw: Dict[str, Any]) -> ChannelSurfConfig:
        cfg = ChannelSurfConfig()
        channels = raw.get("channels")
        if isinstance(channels, str):
            nums = [int(x) for x in re.findall(r"\d{2,4}", channels)]
            cfg.channels = nums
        elif isinstance(channels, list):
            cfg.channels = [int(x) for x in channels if str(x).strip().isdigit()]
        cfg.start_channel = int(raw["start_channel"]) if str(raw.get("start_channel", "")).isdigit() else None
        cfg.stop_channel = int(raw["stop_channel"]) if str(raw.get("stop_channel", "")).isdigit() else None
        if cfg.start_channel is not None and cfg.stop_channel is not None and not cfg.channels:
            lo, hi = sorted([cfg.start_channel, cfg.stop_channel])
            cfg.channels = list(range(lo, hi + 1))
        for field_name in ("max_channels", "max_same_channel_steps"):
            if field_name in raw and str(raw[field_name]).strip():
                setattr(cfg, field_name, int(raw[field_name]))
        for field_name in ("digit_gap_s", "tune_timeout_s", "post_tune_settle_s", "info_settle_s", "guide_settle_s", "channel_step_settle_s"):
            if field_name in raw and str(raw[field_name]).strip():
                setattr(cfg, field_name, float(raw[field_name]))
        for field_name in ("collect_info", "collect_guide", "recover_black", "use_channel_up_down", "stop_on_repeated_channel"):
            if field_name in raw:
                val = raw[field_name]
                setattr(cfg, field_name, str(val).lower() in {"1", "true", "yes", "on"} if isinstance(val, str) else bool(val))
        if isinstance(raw.get("black_recovery_sequence"), str):
            cfg.black_recovery_sequence = [x.strip() for x in re.split(r"[,\s]+", raw["black_recovery_sequence"]) if x.strip()]
        mode = str(raw.get("surf_mode") or cfg.surf_mode or "direct").strip().lower()
        if mode in {"channel_up", "ch_up", "up"}:
            cfg.surf_mode = "channel_up"; cfg.use_channel_up_down = True; cfg.channel_step_key = "ch_up"
        elif mode in {"channel_down", "ch_down", "down"}:
            cfg.surf_mode = "channel_down"; cfg.use_channel_up_down = True; cfg.channel_step_key = "ch_down"
        else:
            cfg.surf_mode = "direct"
        if str(raw.get("channel_step_key") or "").strip():
            cfg.channel_step_key = str(raw["channel_step_key"]).strip()
        return cfg

    def _run_safe(self, cfg: ChannelSurfConfig) -> None:
        try:
            self.run(cfg)
        except Exception as exc:
            log.exception("channel surf failed")
            with self._lock:
                self.last_error = str(exc)
        finally:
            with self._lock:
                self.running = False
                self.finished_at = self.now()
            self.save()

    def run(self, cfg: ChannelSurfConfig) -> None:
        channels = list(dict.fromkeys(int(c) for c in cfg.channels))
        if not channels and cfg.start_channel is not None:
            channels = [cfg.start_channel]
        if cfg.max_channels and cfg.max_channels > 0:
            channels = channels[: cfg.max_channels]
        if not channels:
            return
        if cfg.use_channel_up_down:
            self._run_channel_step_mode(cfg, channels[0])
            return
        for ch in channels:
            if self._stop.is_set():
                break
            self._record_observation(self.scan_channel(ch, cfg, input_method="direct_digits", requested_channel=ch))

    def _run_channel_step_mode(self, cfg: ChannelSurfConfig, first_channel: int) -> None:
        max_count = cfg.max_channels if cfg.max_channels and cfg.max_channels > 0 else max(1, len(cfg.channels) or 25)
        direction = 1 if cfg.channel_step_key == "ch_up" else -1
        previous_actual = ""
        same_count = 0
        first = self.scan_channel(first_channel, cfg, input_method="direct_digits", requested_channel=first_channel)
        previous_actual = first.actual_channel_guess or str(first.channel)
        self._record_observation(first)
        for idx in range(1, max_count):
            if self._stop.is_set():
                break
            start = time.time()
            self._send(cfg.channel_step_key)
            time.sleep(max(0.1, cfg.channel_step_settle_s))
            expected = _safe_int(previous_actual, first_channel) + direction
            obs = self.scan_current_channel(expected, cfg, started_at=start, input_method=cfg.channel_step_key, previous_actual_channel=previous_actual)
            actual = obs.actual_channel_guess or str(obs.channel)
            if actual == previous_actual:
                same_count += 1
                obs.warning_flags.append("channel_step_did_not_change_channel")
            else:
                same_count = 0
            previous_actual = actual
            self._record_observation(obs)
            if cfg.stop_on_repeated_channel and same_count >= max(1, cfg.max_same_channel_steps):
                break

    def _record_observation(self, obs: ChannelObservation) -> None:
        with self._lock:
            obs_dict = asdict(obs)
            self.history.append(obs_dict)
            self.last_observation = obs_dict
        self.save()

    def _send(self, key: str) -> Dict[str, Any]:
        result = self.send_key(str(key))
        time.sleep(self.default_delay_s)
        return result

    def tune_channel(self, channel: int, cfg: ChannelSurfConfig) -> None:
        for digit in str(int(channel)):
            self._send(digit)
            time.sleep(max(0.01, cfg.digit_gap_s))
        if cfg.suffix_key:
            self._send(cfg.suffix_key)

    def _frame_health_focus_text(self) -> tuple[Optional[np.ndarray], Dict[str, Any], Dict[str, Any], str]:
        frame = self.capture_frame()
        status = self.capture_status()
        if frame is None or not getattr(frame, "size", 0):
            return None, {"signal_class": "no_frame", "active": False, "status": status}, {}, ""
        motion = float(status.get("motion_score") or 0.0)
        health = classify_frame_signal(frame, motion_score=motion).to_dict()
        try:
            focus = detect_focus(frame, None)
        except Exception:
            focus = {}
        text_parts = []
        if isinstance(focus, dict):
            for key in (
                "header_text", "page_name", "block_title", "screen_title", "menu_title", "human_label",
                "focused_item", "focused_value", "context_text", "row_text", "label_text", "action_bar_text",
                "recovery_text", "channel_number", "channel_name"
            ):
                val = str(focus.get(key) or "").strip()
                if val:
                    text_parts.append(val)
        return frame, health, focus if isinstance(focus, dict) else {}, " ".join(text_parts)

    def _capture_health_focus(self) -> tuple[Dict[str, Any], Dict[str, Any], str]:
        _, health, focus, text = self._frame_health_focus_text()
        return health, focus, text

    def _capture_health_focus_meta(
        self,
        screen_hint: str = "unknown",
        requested_channel: Optional[int] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any], str, Dict[str, Any]]:
        frame, health, focus, text = self._frame_health_focus_text()
        meta: Dict[str, Any] = {}
        if frame is not None:
            try:
                meta = extract_channel_metadata(frame, text=text, focus=focus, screen_hint=screen_hint, requested_channel=requested_channel)
            except Exception as exc:
                log.debug("channel metadata extraction failed: %s", exc)
                meta = {"screen_type": screen_hint, "confidence": 0.0, "quality_flags": ["metadata_extraction_failed"]}
        return health, focus, text, meta

    def _wait_for_tune_complete(self, cfg: ChannelSurfConfig, requested_channel: Optional[int] = None) -> tuple[float, Dict[str, Any], Dict[str, Any], str, Dict[str, Any]]:
        start = time.time()
        last_health: Dict[str, Any] = {}
        last_focus: Dict[str, Any] = {}
        last_text = ""
        deadline = start + max(1.0, cfg.tune_timeout_s)
        # Fast phase: watch for active/non-black video without expensive OCR metadata.
        while time.time() < deadline and not self._stop.is_set():
            health, focus, text = self._capture_health_focus()
            last_health, last_focus, last_text = health, focus, text
            if health.get("active") and health.get("signal_class") != "black_screen":
                time.sleep(max(0.0, cfg.post_tune_settle_s))
                health, focus, text, meta = self._capture_health_focus_meta("live_banner", requested_channel=requested_channel)
                return time.time() - start, health, focus, text, meta
            time.sleep(0.25)
        # Timeout path: collect metadata once, not on every poll.
        health, focus, text, meta = self._capture_health_focus_meta("live_banner", requested_channel=requested_channel)
        return time.time() - start, health or last_health, focus or last_focus, text or last_text, meta

    @staticmethod
    def _guess_from_text(channel: int, text: str) -> tuple[str, str, str, bool, List[str], List[str]]:
        """Legacy fallback scanner.

        v24 intentionally stopped manufacturing channel/program names from the
        full OCR blob.  That was the source of bogus titles like "ee panes
        site".  Program and channel identity now come from trusted metadata
        regions only; this fallback is retained for PPV/blocking cues and very
        conservative guide-channel number extraction.
        """
        clean = " ".join(str(text or "").split())
        flags: List[str] = []
        ppv_cues: List[str] = []
        ppv = bool(PPV_RX.search(clean))
        if ppv:
            ppv_cues = [str(x) for x in PPV_RX.findall(clean)[:8]]
        if BLACK_OR_BLOCK_RX.search(clean):
            flags.append("blocked_or_unavailable_text")
        scrub = PHONEISH_RX.sub(" ", clean)
        m = CHANNEL_RX.search(scrub)
        guide_ch = m.group(1) if m else ""
        return "", "", guide_ch, ppv, ppv_cues, flags

    @staticmethod
    def _channel_guess_from_focus_text(focuses: List[Dict[str, Any]], text: str, requested: Optional[int] = None) -> tuple[str, str]:
        for idx, focus in enumerate(focuses):
            if isinstance(focus, dict):
                for key in ("channel_number", "channel"):
                    val = str(focus.get(key) or "").strip()
                    if val.isdigit() and 1 <= len(val) <= 4:
                        return val, f"focus[{idx}].{key}"
                ui = focus.get("ui_context") if isinstance(focus.get("ui_context"), dict) else {}
                val = str((ui or {}).get("channel_number") or "").strip()
                if val.isdigit() and 1 <= len(val) <= 4:
                    return val, f"focus[{idx}].ui_context.channel_number"
        clean = PHONEISH_RX.sub(" ", str(text or ""))
        if requested and re.search(rf"\b{int(requested)}\b", clean):
            return str(int(requested)), "requested_channel_seen_in_text"
        candidates = [m.group(1) for m in CHANNEL_RX.finditer(clean)]
        candidates = [c for c in candidates if 1 <= int(c) <= 9999]
        if candidates:
            return candidates[0], "text_regex"
        return "", ""

    def _recover_black(self, cfg: ChannelSurfConfig) -> List[Dict[str, Any]]:
        out = []
        if not cfg.recover_black:
            return out
        for key in cfg.black_recovery_sequence:
            if self._stop.is_set():
                break
            try:
                out.append({"key": key, "result": self._send(key)})
            except Exception as exc:
                out.append({"key": key, "error": str(exc)})
            time.sleep(max(0.2, cfg.post_tune_settle_s))
            health, _, _ = self._capture_health_focus()
            if health.get("active") and health.get("signal_class") != "black_screen":
                break
        return out

    def _add_time_context(self, obs: ChannelObservation, field_name: str, text: str, focus: Dict[str, Any]) -> None:
        ctx = extract_display_clock(text, focus, observed_at=self.now())
        setattr(obs, field_name, ctx)
        for flag in ctx.get("flags") or []:
            if flag not in obs.time_discrepancy_flags and "drift" in flag:
                obs.time_discrepancy_flags.append(flag)

    def scan_current_channel(
        self,
        expected_channel: int,
        cfg: ChannelSurfConfig,
        started_at: Optional[float] = None,
        input_method: str = "already_tuned",
        previous_actual_channel: str = "",
    ) -> ChannelObservation:
        start = started_at or time.time()
        return self._scan_after_tune(
            expected_channel,
            cfg,
            start=start,
            input_method=input_method,
            navigation_key=input_method if input_method.startswith("ch_") else "",
            previous_actual_channel=previous_actual_channel,
            requested_channel=expected_channel,
        )

    def scan_channel(
        self,
        channel: int,
        cfg: ChannelSurfConfig,
        input_method: str = "direct_digits",
        requested_channel: Optional[int] = None,
    ) -> ChannelObservation:
        start = time.time()
        self.tune_channel(channel, cfg)
        return self._scan_after_tune(channel, cfg, start=start, input_method=input_method, requested_channel=requested_channel or channel)

    def _scan_after_tune(
        self,
        channel: int,
        cfg: ChannelSurfConfig,
        start: float,
        input_method: str,
        requested_channel: Optional[int] = None,
        navigation_key: str = "",
        previous_actual_channel: str = "",
    ) -> ChannelObservation:
        obs = ChannelObservation(channel=int(channel), ts=self.now(), ok=False)
        obs.requested_channel = requested_channel
        obs.input_method = input_method
        obs.navigation_key = navigation_key
        obs.previous_channel_guess = previous_actual_channel
        obs.tune_start_s = round(time.time() - start, 3)
        complete_s, live_health, live_focus, live_text, live_meta = self._wait_for_tune_complete(cfg, requested_channel=requested_channel)
        obs.tune_complete_s = round(complete_s, 3)
        obs.live_health = live_health
        obs.live_focus = live_focus
        obs.live_metadata = live_meta
        self._add_time_context(obs, "live_time_context", " ".join([live_text, str(live_meta.get("displayed_datetime_text") or "")]), live_focus)

        if live_health.get("signal_class") == "black_screen":
            obs.warning_flags.append("black_screen_after_tune")
            obs.recovery = self._recover_black(cfg)
            live_health, live_focus, live_text, live_meta = self._capture_health_focus_meta("live_banner", requested_channel=requested_channel)
            obs.live_health = live_health
            obs.live_focus = live_focus
            obs.live_metadata = live_meta
            self._add_time_context(obs, "live_time_context", " ".join([live_text, str(live_meta.get("displayed_datetime_text") or "")]), live_focus)

        combined_text = live_text + " " + json.dumps(obs.live_metadata or {}, ensure_ascii=False)
        all_focuses = [live_focus]

        if cfg.collect_info:
            self._send("info")
            time.sleep(max(0.1, cfg.info_settle_s))
            info_health, info_focus, info_text, info_meta = self._capture_health_focus_meta("info", requested_channel=requested_channel)
            obs.info_health = info_health
            obs.info_focus = info_focus
            obs.info_text = info_text
            obs.info_metadata = info_meta
            self._add_time_context(obs, "info_time_context", " ".join([info_text, str(info_meta.get("displayed_datetime_text") or "")]), info_focus)
            combined_text += " " + info_text + " " + json.dumps(info_meta, ensure_ascii=False)
            all_focuses.append(info_focus)
            self._send("back")

        if cfg.collect_guide:
            self._send("guide")
            time.sleep(max(0.1, cfg.guide_settle_s))
            guide_health, guide_focus, guide_text, guide_meta = self._capture_health_focus_meta("guide", requested_channel=requested_channel)
            obs.guide_health = guide_health
            obs.guide_focus = guide_focus
            obs.guide_text = guide_text
            obs.guide_metadata = guide_meta
            self._add_time_context(obs, "guide_time_context", " ".join([guide_text, str(guide_meta.get("displayed_datetime_text") or "")]), guide_focus)
            combined_text += " " + guide_text + " " + json.dumps(guide_meta, ensure_ascii=False)
            all_focuses.append(guide_focus)
            self._send("back")

        obs.best_metadata = choose_best_metadata([obs.live_metadata, obs.info_metadata, obs.guide_metadata])
        meta_actual = str((obs.best_metadata or {}).get("channel_number") or "").strip()
        meta_code = str((obs.best_metadata or {}).get("channel_code") or "").strip()
        actual, actual_source = self._channel_guess_from_focus_text(all_focuses, combined_text, requested_channel)
        if meta_actual:
            actual, actual_source = meta_actual, "best_metadata.channel_number"
        obs.actual_channel_guess = actual
        obs.actual_channel_source = actual_source

        name, program, guide_ch, ppv, ppv_cues, flags = self._guess_from_text(channel, combined_text)
        trusted_meta = float((obs.best_metadata or {}).get("confidence") or 0.0) >= 0.45
        if meta_code and not is_plausible_channel_code(meta_code):
            meta_code = ""
            obs.warning_flags.append("metadata_rejected_noisy_channel_code")
        obs.channel_code_guess = meta_code
        obs.channel_name_guess = meta_code or (str((obs.best_metadata or {}).get("channel_name") or "").strip() if trusted_meta else "")
        raw_title = str((obs.best_metadata or {}).get("program_title") or "").strip()
        clean_title = sanitize_program_title(raw_title)
        if raw_title and not clean_title:
            obs.warning_flags.append("metadata_rejected_noisy_program_title")
        obs.program_title_guess = clean_title if trusted_meta else ""
        obs.program_description_guess = str((obs.best_metadata or {}).get("program_description") or "").strip() if trusted_meta and clean_title else ""
        obs.program_guess = obs.program_title_guess
        obs.guide_channel_guess = str((obs.guide_metadata or {}).get("channel_number") or guide_ch or "").strip()
        obs.ppv_available = ppv
        obs.ppv_cues = ppv_cues
        obs.warning_flags.extend(flags)
        if (obs.best_metadata or {}).get("quality_flags"):
            for qf in obs.best_metadata.get("quality_flags") or []:
                flag = f"metadata_{qf}"
                if flag not in obs.warning_flags:
                    obs.warning_flags.append(flag)
        if obs.live_metadata and not obs.live_metadata.get("banner_valid"):
            obs.warning_flags.append("live_banner_validation_failed")
            for bf in obs.live_metadata.get("banner_validation_flags") or []:
                flag = f"banner_{bf}" if not str(bf).startswith("banner_") else str(bf)
                if flag not in obs.warning_flags:
                    obs.warning_flags.append(flag)
        if float((obs.best_metadata or {}).get("confidence") or 0.0) < 0.45:
            obs.warning_flags.append("metadata_low_confidence")
        if guide_ch and actual and guide_ch != actual:
            obs.warning_flags.append("guide_actual_channel_mismatch")
        elif guide_ch and not actual and guide_ch != str(channel):
            obs.warning_flags.append("guide_channel_mismatch")
        if requested_channel and actual and str(requested_channel) != actual and input_method == "direct_digits":
            obs.warning_flags.append("direct_tune_requested_actual_mismatch")
        if input_method in {"ch_up", "ch_down"} and previous_actual_channel and actual:
            prev = _safe_int(previous_actual_channel, 0)
            cur = _safe_int(actual, 0)
            expected_delta = 1 if input_method == "ch_up" else -1
            if prev and cur and cur != prev + expected_delta:
                obs.skipped_channel_detected = True
                obs.skipped_channel_note = f"{input_method}: {prev} -> {cur} (delta {cur-prev:+d})"
                obs.warning_flags.append("channel_step_skipped_or_jump")
        if not obs.live_health.get("active"):
            obs.warning_flags.append("inactive_video_after_recovery")
        if obs.time_discrepancy_flags:
            obs.warning_flags.append("display_clock_discrepancy")
        obs.ok = bool(obs.live_health.get("active")) and not any(f in obs.warning_flags for f in ("guide_channel_mismatch", "guide_actual_channel_mismatch", "direct_tune_requested_actual_mismatch"))
        return obs


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default
