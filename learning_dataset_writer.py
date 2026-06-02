#!/usr/bin/env python3
"""Phase-1 learning dataset exporter for aBotTesty/STB navigation.

This module converts the app's existing crawler/teacher/channel-surf artifacts into
portable multimodal training data.  It is intentionally dependency-light so it can
run on the capture machine, on the 2x3090 trainer, or in CI without GPU packages.

Outputs per export:
  learning_datasets/<run_id>/
    manifest.json
    episodes.jsonl
    sft/screen_perception.jsonl
    sft/action_policy.jsonl
    sft/outcome_verifier.jsonl
    images/*.jpg

The SFT files use a simple JSONL conversation format with optional image/images
fields, which can be adapted to LLaMA-Factory, TRL, Axolotl, or a custom trainer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

try:  # Optional: resize copied images to keep datasets sane.
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore


REMOTE_KEYS = {
    "up", "down", "left", "right", "select", "back", "home", "guide", "info",
    "live", "recall", "input", "options", "dvr", "ch_up", "ch_down", "play",
    "pause", "stop", "fwd", "rwd", "0", "1", "2", "3", "4", "5", "6", "7",
    "8", "9",
}
RISK_TEXT_RX = re.compile(
    r"\b(purchase|buy|rent|order|subscribe|unsubscribe|delete|erase|factory|reset|format|payment|pin|password|adult|parental|confirm purchase|record series)\b",
    re.I,
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(text: Any, limit: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(text or "").strip())
    s = s.strip("._-") or "item"
    return s[:limit]


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def first_present(*values: Any) -> Any:
    for v in values:
        if v not in (None, "", [], {}):
            return v
    return ""


def normalize_action(action: Any) -> str:
    text = str(action or "").strip().lower()
    aliases = {
        "ok": "select", "enter": "select", "key_ok": "select", "key_up": "up",
        "key_down": "down", "key_left": "left", "key_right": "right", "exit": "back",
        "live tv": "live", "channel_up": "ch_up", "channel_down": "ch_down",
        "ch+": "ch_up", "ch-": "ch_down",
    }
    return aliases.get(text, text)


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


@dataclass
class LearningEpisode:
    episode_id: str
    source: str
    step_index: int = 0
    task: str = "stb_navigation"
    goal: str = ""
    before_state_id: str = ""
    after_state_id: str = ""
    action: str = ""
    action_sequence: List[str] = field(default_factory=list)
    before_image: str = ""
    after_image: str = ""
    before_label: str = ""
    after_label: str = ""
    ocr_text: str = ""
    focus: Dict[str, Any] = field(default_factory=dict)
    guide_grid: Dict[str, Any] = field(default_factory=dict)
    channel_metadata: Dict[str, Any] = field(default_factory=dict)
    video_health: Dict[str, Any] = field(default_factory=dict)
    timing: Dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    confidence: float = 0.0
    changed: bool = False
    success_label: bool = False
    risk_flags: List[str] = field(default_factory=list)
    quality_flags: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LearningDatasetWriter:
    def __init__(
        self,
        root_dir: str | Path = ".",
        crawler_dir: str | Path | None = None,
        out_dir: str | Path | None = None,
        image_max_width: int = 960,
        include_raw: bool = False,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.crawler_dir = Path(crawler_dir).resolve() if crawler_dir else (self.root_dir / "crawler_data").resolve()
        self.out_root = Path(out_dir).resolve() if out_dir else (self.root_dir / "learning_datasets").resolve()
        self.image_max_width = int(image_max_width or 0)
        self.include_raw = bool(include_raw)
        self._copied: Dict[str, str] = {}

    def discover_artifacts(self) -> Dict[str, List[str]]:
        search_roots = [self.root_dir, self.crawler_dir]
        patterns = {
            "nav_graph": ["nav_graph*.json"],
            "crawler_brain": ["crawler_brain*.json"],
            "teacher": ["teach_*.json", "manual_teaching*.json"],
            "channel_surf": ["channel_surf_log*.json"],
            "sysdiag": ["sysdiag_bootstrap_history*.json"],
            "sequences": ["learned_sequences*.json"],
        }
        found: Dict[str, List[str]] = {k: [] for k in patterns}
        seen: set[Path] = set()
        for base in search_roots:
            if not base.exists():
                continue
            for kind, pats in patterns.items():
                for pat in pats:
                    for p in base.rglob(pat):
                        rp = p.resolve()
                        if rp not in seen and p.is_file():
                            found[kind].append(str(rp))
                            seen.add(rp)
        for k in found:
            found[k].sort(key=lambda x: Path(x).stat().st_mtime if Path(x).exists() else 0, reverse=True)
        return found

    def stats(self) -> Dict[str, Any]:
        artifacts = self.discover_artifacts()
        counts: Dict[str, int] = {k: len(v) for k, v in artifacts.items()}
        transitions = 0
        teacher_events = 0
        channel_observations = 0
        image_refs = 0
        for p in artifacts.get("nav_graph", [])[:3]:
            data = read_json(Path(p), {}) or {}
            transitions += len(as_list(data.get("transitions"))) + len(as_list(data.get("edges")))
            for n in as_list(data.get("nodes")):
                if any(n.get(k) for k in ("screenshot", "image", "image_path")):
                    image_refs += 1
        for p in artifacts.get("teacher", []):
            data = read_json(Path(p), {}) or {}
            teacher_events += len(as_list(data.get("events")))
        for p in artifacts.get("channel_surf", []):
            data = read_json(Path(p), {}) or {}
            channel_observations += len(as_list(data.get("observations")))
        return {
            "ok": True,
            "root_dir": str(self.root_dir),
            "crawler_dir": str(self.crawler_dir),
            "out_root": str(self.out_root),
            "artifact_counts": counts,
            "transition_like_records": transitions,
            "teacher_events": teacher_events,
            "channel_surf_observations": channel_observations,
            "image_references_seen": image_refs,
            "artifacts": artifacts,
        }

    def export(self, run_id: str | None = None, max_records: int = 0, include_raw: Optional[bool] = None) -> Dict[str, Any]:
        run_id = run_id or datetime.now().strftime("v37_%Y%m%d_%H%M%S")
        out_dir = self.out_root / slug(run_id, 80)
        if out_dir.exists():
            raise FileExistsError(f"dataset export already exists: {out_dir}")
        (out_dir / "images").mkdir(parents=True, exist_ok=True)
        (out_dir / "sft").mkdir(parents=True, exist_ok=True)
        include_raw_old = self.include_raw
        if include_raw is not None:
            self.include_raw = bool(include_raw)
        try:
            artifacts = self.discover_artifacts()
            episodes = list(self._iter_episodes(artifacts, out_dir=out_dir, max_records=max_records))
            ep_path = out_dir / "episodes.jsonl"
            append_jsonl(ep_path, [e.to_dict() for e in episodes])
            sft_counts = self._write_sft(out_dir, episodes)
            manifest = {
                "schema": "abot_learning_dataset_v37_phase1",
                "run_id": run_id,
                "created_at": utc_now(),
                "root_dir": str(self.root_dir),
                "crawler_dir": str(self.crawler_dir),
                "episode_count": len(episodes),
                "image_count": len(list((out_dir / "images").glob("*"))),
                "sft_counts": sft_counts,
                "artifacts": artifacts,
                "model_targets": [
                    "screen_perception",
                    "action_policy_shadow_mode",
                    "outcome_verifier",
                ],
                "safety_note": "Phase 1 only exports data. It does not allow a model to press remote keys.",
            }
            manifest["trainable"] = bool(
                int(sft_counts.get("screen_perception") or 0) > 0
                and int(manifest.get("image_count") or 0) > 0
            )
            manifest["ok"] = bool(manifest["trainable"])
            if not manifest["trainable"]:
                manifest["export_warning"] = "Export produced no trainable screen/image rows; learning_datasets/latest was not updated."

            write_json(out_dir / "manifest.json", manifest)

            latest = self.out_root / "latest"
            if manifest["trainable"]:
                try:
                    if latest.exists() or latest.is_symlink():
                        if latest.is_symlink() or latest.is_file():
                            latest.unlink()
                        else:
                            shutil.rmtree(latest)
                    # Windows may require copy instead of symlink.
                    try:
                        latest.symlink_to(out_dir, target_is_directory=True)
                    except Exception:
                        write_json(self.out_root / "latest_manifest_pointer.json", {"latest": str(out_dir)})
                except Exception:
                    pass
            else:
                write_json(self.out_root / "latest_rejected_export.json", {"rejected": str(out_dir), "reason": manifest.get("export_warning")})

            return {"ok": bool(manifest["trainable"]), "dataset_dir": str(out_dir), **manifest}
        finally:
            self.include_raw = include_raw_old

    def _iter_episodes(self, artifacts: Dict[str, List[str]], out_dir: Path, max_records: int = 0) -> Iterator[LearningEpisode]:
        emitted = 0
        for ep in self._episodes_from_nav_graphs(artifacts.get("nav_graph", []), out_dir):
            yield ep
            emitted += 1
            if max_records and emitted >= max_records:
                return
        for ep in self._episodes_from_teacher(artifacts.get("teacher", []), out_dir, offset=emitted):
            yield ep
            emitted += 1
            if max_records and emitted >= max_records:
                return
        for ep in self._episodes_from_channel_surf(artifacts.get("channel_surf", []), out_dir, offset=emitted):
            yield ep
            emitted += 1
            if max_records and emitted >= max_records:
                return
        for ep in self._episodes_from_state_images(out_dir, offset=emitted):
            yield ep
            emitted += 1
            if max_records and emitted >= max_records:
                return

    def _state_index(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        idx: Dict[str, Dict[str, Any]] = {}
        nodes = data.get("nodes") or data.get("states") or []
        if isinstance(nodes, dict):
            nodes = list(nodes.values())
        for n in as_list(nodes):
            if not isinstance(n, dict):
                continue
            sid = str(first_present(n.get("id"), n.get("state_id"), n.get("key")))
            if sid:
                idx[sid] = n
        # Some nav graphs save state records under a dict key.
        for key in ("state_details", "state_map"):
            m = data.get(key)
            if isinstance(m, dict):
                for sid, n in m.items():
                    if isinstance(n, dict):
                        idx.setdefault(str(sid), n)
        return idx

    def _episodes_from_nav_graphs(self, paths: List[str], out_dir: Path) -> Iterator[LearningEpisode]:
        for path in paths:
            data = read_json(Path(path), {}) or {}
            state_idx = self._state_index(data)
            records = []
            for key in ("transitions", "edges", "links"):
                v = data.get(key)
                if isinstance(v, dict):
                    records.extend(v.values())
                elif isinstance(v, list):
                    records.extend(v)
            for i, rec in enumerate(records):
                if not isinstance(rec, dict):
                    continue
                before_id = str(first_present(rec.get("before_state"), rec.get("from"), rec.get("source"), rec.get("from_state")))
                after_id = str(first_present(rec.get("after_state"), rec.get("to"), rec.get("target"), rec.get("to_state")))
                action = normalize_action(first_present(rec.get("button"), rec.get("action"), rec.get("key"), rec.get("sequence")))
                if not action:
                    continue
                before_node = state_idx.get(before_id, {})
                after_node = state_idx.get(after_id, {})
                before_img = self._copy_image(
                    first_present(rec.get("before_screenshot"), rec.get("before_image"), before_node.get("screenshot"), before_node.get("image"), before_node.get("image_path")),
                    out_dir,
                    prefix=f"nav_{i:06d}_before",
                )
                after_img = self._copy_image(
                    first_present(rec.get("after_screenshot"), rec.get("after_image"), after_node.get("screenshot"), after_node.get("image"), after_node.get("image_path")),
                    out_dir,
                    prefix=f"nav_{i:06d}_after",
                )
                if not before_img:
                    before_img = self._copy_state_image(before_id, out_dir, prefix=f"nav_{i:06d}_before_state")
                if not after_img:
                    after_img = self._copy_state_image(after_id, out_dir, prefix=f"nav_{i:06d}_after_state")
                text_blob = " ".join(str(x or "") for x in [
                    rec.get("ocr_text"), rec.get("before_ocr"), rec.get("after_ocr"), before_node.get("ocr_text"), after_node.get("ocr_text"),
                    before_node.get("label"), after_node.get("label"), rec.get("label")
                ])
                risk_flags = list(rec.get("risk_flags") or [])
                if RISK_TEXT_RX.search(text_blob):
                    risk_flags.append("risk_text_seen")
                reward = self._float(first_present(rec.get("reward"), rec.get("avg_reward"), rec.get("total_reward")), 0.0)
                changed = bool(first_present(rec.get("changed"), before_id != after_id))
                confidence = self._float(first_present(rec.get("confidence"), rec.get("match_confidence")), 0.0)
                success = bool(rec.get("success") or (changed and reward >= 0 and action in REMOTE_KEYS))
                raw = rec if self.include_raw else {}
                yield LearningEpisode(
                    episode_id=f"nav_{Path(path).stem}_{i:06d}",
                    source="nav_graph",
                    step_index=i,
                    before_state_id=before_id,
                    after_state_id=after_id,
                    action=action,
                    action_sequence=[normalize_action(x) for x in as_list(rec.get("sequence") or action)],
                    before_image=before_img,
                    after_image=after_img,
                    before_label=str(first_present(before_node.get("human_label"), before_node.get("label"), rec.get("before_label"))),
                    after_label=str(first_present(after_node.get("human_label"), after_node.get("label"), rec.get("after_label"))),
                    ocr_text=str(first_present(rec.get("ocr_text"), rec.get("after_ocr"), after_node.get("ocr_text"), before_node.get("ocr_text"))),
                    focus=dict(first_present(rec.get("focus"), rec.get("after_focus"), after_node.get("focus"), {}) or {}),
                    guide_grid=dict(first_present(rec.get("guide_grid"), after_node.get("guide_grid"), {}) or {}),
                    channel_metadata=dict(first_present(rec.get("channel_metadata"), rec.get("metadata"), after_node.get("channel_metadata"), {}) or {}),
                    timing=dict(first_present(rec.get("timing"), rec.get("action_timing"), {}) or {}),
                    reward=reward,
                    confidence=confidence,
                    changed=changed,
                    success_label=success,
                    risk_flags=sorted(set(risk_flags)),
                    quality_flags=list(rec.get("quality_flags") or []),
                    raw=raw,
                )

    def _episodes_from_teacher(self, paths: List[str], out_dir: Path, offset: int = 0) -> Iterator[LearningEpisode]:
        for path in paths:
            data = read_json(Path(path), {}) or {}
            events = as_list(data.get("events"))
            pending: Optional[Dict[str, Any]] = None
            local_step = 0
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                typ = str(ev.get("type") or "")
                if typ in {"button_sent_pending", "button", "button_sent"}:
                    pending = ev
                if typ in {"transition", "button_result", "transition_recorded"} or (pending and ev.get("after_state")):
                    rec = {**(pending or {}), **ev}
                    action = normalize_action(first_present(rec.get("button"), rec.get("key"), rec.get("action")))
                    if not action:
                        continue
                    before_id = str(first_present(rec.get("before_state"), rec.get("from_state")))
                    after_id = str(first_present(rec.get("after_state"), rec.get("to_state")))
                    text_blob = " ".join(str(rec.get(k) or "") for k in ("before_label", "after_label", "ocr_text", "focus_text", "note"))
                    risk_flags = []
                    if RISK_TEXT_RX.search(text_blob):
                        risk_flags.append("risk_text_seen")
                    yield LearningEpisode(
                        episode_id=f"teach_{Path(path).stem}_{local_step:06d}",
                        source=str(first_present(data.get("operator"), rec.get("source"), "teacher")),
                        step_index=offset + local_step,
                        goal=str(first_present(data.get("name"), data.get("notes"))),
                        before_state_id=before_id,
                        after_state_id=after_id,
                        action=action,
                        action_sequence=[action],
                        before_image=(self._copy_image(first_present(rec.get("before_screenshot"), rec.get("before_image")), out_dir, f"teach_{local_step:06d}_before") or self._copy_state_image(before_id, out_dir, f"teach_{local_step:06d}_before_state")),
                        after_image=(self._copy_image(first_present(rec.get("after_screenshot"), rec.get("after_image")), out_dir, f"teach_{local_step:06d}_after") or self._copy_state_image(after_id, out_dir, f"teach_{local_step:06d}_after_state")),
                        before_label=str(rec.get("before_label") or ""),
                        after_label=str(rec.get("after_label") or ""),
                        ocr_text=str(first_present(rec.get("ocr_text"), rec.get("after_ocr"))),
                        reward=self._float(rec.get("reward"), 0.0),
                        confidence=self._float(rec.get("confidence"), 0.0),
                        changed=bool(first_present(rec.get("changed"), before_id != after_id)),
                        success_label=bool(first_present(rec.get("success"), before_id != after_id)),
                        risk_flags=risk_flags,
                        raw=rec if self.include_raw else {},
                    )
                    local_step += 1
                    pending = None

    def _episodes_from_channel_surf(self, paths: List[str], out_dir: Path, offset: int = 0) -> Iterator[LearningEpisode]:
        for path in paths:
            data = read_json(Path(path), {}) or {}
            for i, obs in enumerate(as_list(data.get("observations"))):
                if not isinstance(obs, dict):
                    continue
                channel = first_present(obs.get("channel"), obs.get("channel_number"))
                action_seq = [x for x in str(channel).strip() if x.isdigit()]
                if action_seq:
                    action_seq.append("select")
                metadata = {
                    "live_focus": obs.get("live_focus") or {},
                    "info_focus": obs.get("info_focus") or {},
                    "guide_focus": obs.get("guide_focus") or {},
                    "channel_name_guess": obs.get("channel_name_guess") or "",
                    "program_guess": obs.get("program_guess") or "",
                    "guide_channel_guess": obs.get("guide_channel_guess") or "",
                }
                risk_flags = list(obs.get("warning_flags") or [])
                ok = bool(obs.get("ok"))
                yield LearningEpisode(
                    episode_id=f"surf_{Path(path).stem}_{i:06d}",
                    source="channel_surf",
                    step_index=offset + i,
                    goal=f"tune channel {channel}",
                    action="channel_tune",
                    action_sequence=action_seq,
                    channel_metadata=metadata,
                    video_health=dict(obs.get("live_health") or {}),
                    timing={"tune_start_s": obs.get("tune_start_s"), "tune_complete_s": obs.get("tune_complete_s")},
                    reward=1.0 if ok else -1.0,
                    confidence=1.0 if ok else 0.0,
                    changed=ok,
                    success_label=ok,
                    risk_flags=risk_flags,
                    quality_flags=list(obs.get("quality_flags") or []),
                    raw=obs if self.include_raw else {},
                )


    def _state_image_roots(self) -> List[Path]:
        roots: List[Path] = []
        seen: set[str] = set()
        for base in (
            self.crawler_dir / "states",
            self.root_dir / "crawler_data" / "states",
            self.root_dir / "states",
        ):
            try:
                resolved = base.resolve()
            except Exception:
                resolved = base
            key = str(resolved)
            if base.exists() and key not in seen:
                roots.append(resolved)
                seen.add(key)
        return roots

    @staticmethod
    def _state_lookup_keys_from_stem(stem: str) -> List[str]:
        """Return lookup keys for crawler screenshot filename stems."""
        raw = str(stem or "").strip()
        if not raw:
            return []

        keys = {raw, slug(raw, 140)}

        # Strip timestamp suffix: stateid_YYYYMMDD_HHMMSS_microseconds.
        m = re.match(r"^(?P<sid>.+?)_\d{8}_\d{6}(?:_\d+)?$", raw)
        if m:
            sid = m.group("sid")
            keys.add(sid)
            keys.add(slug(sid, 140))

        # Also index progressive prefixes.
        parts = raw.split("_")
        for n in range(2, min(len(parts), 8) + 1):
            prefix = "_".join(parts[:n])
            if len(prefix) >= 8:
                keys.add(prefix)
                keys.add(slug(prefix, 140))

        return [k for k in keys if k]

    def _build_state_image_index(self) -> Dict[str, List[Path]]:
        """Scan live crawler screenshots once and build fast lookup indexes."""
        cached = getattr(self, "_state_image_index", None)
        cached_files = getattr(self, "_state_image_files_cache", None)
        if isinstance(cached, dict) and isinstance(cached_files, list):
            return cached

        idx: Dict[str, List[Path]] = {}
        files: List[Path] = []
        seen: set[str] = set()

        for root in self._state_image_roots():
            try:
                candidates = [
                    x for x in root.rglob("*")
                    if x.is_file() and x.suffix.lower() in IMAGE_EXTS
                ]
            except Exception:
                candidates = []

            for fp in candidates:
                try:
                    file_key = str(fp.resolve())
                except Exception:
                    file_key = str(fp)
                if file_key in seen:
                    continue
                seen.add(file_key)
                files.append(fp)

                for lookup in self._state_lookup_keys_from_stem(fp.stem):
                    idx.setdefault(lookup, []).append(fp)

        def mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except Exception:
                return 0.0

        files.sort(key=mtime, reverse=True)
        for key in list(idx.keys()):
            idx[key].sort(key=mtime, reverse=True)

        self._state_image_index = idx
        self._state_image_files_cache = files
        self._state_image_index_stats = {
            "roots": [str(x) for x in self._state_image_roots()],
            "files": len(files),
            "keys": len(idx),
        }
        return idx

    def _state_image_candidates(self, state_id: Any) -> List[Path]:
        sid = str(state_id or "").strip()
        if not sid:
            return []

        m = re.search(r"/api/crawl/state/([^/]+)/image", sid)
        if m:
            sid = m.group(1)

        index = self._build_state_image_index()
        keys = [sid, slug(sid, 140)]

        out: List[Path] = []
        seen: set[str] = set()

        def add_many(items: List[Path]) -> None:
            for path in items:
                try:
                    k = str(path.resolve())
                except Exception:
                    k = str(path)
                if k not in seen:
                    out.append(path)
                    seen.add(k)

        for key in keys:
            add_many(index.get(key, []))

        # Fast in-memory fuzzy fallback. No filesystem globbing.
        if not out and sid:
            sid_slug = slug(sid, 140)
            for key, paths in index.items():
                if sid in key or sid_slug in key or key in sid or key in sid_slug:
                    add_many(paths)
                    if len(out) >= 8:
                        break

        return out

    def _copy_state_image(self, state_id: Any, out_dir: Path, prefix: str) -> str:
        for cand in self._state_image_candidates(state_id):
            rel = self._copy_image(str(cand), out_dir, prefix)
            if rel:
                return rel
        return ""

    def _episodes_from_state_images(self, out_dir: Path, offset: int = 0) -> Iterator[LearningEpisode]:
        """Harvest live crawler screenshots as screen-perception examples.

        Uses the one-time state image index instead of repeatedly walking
        crawler_data/states.
        """
        self._build_state_image_index()
        files: List[Path] = list(getattr(self, "_state_image_files_cache", []) or [])

        def mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except Exception:
                return 0.0

        files.sort(key=mtime)

        seen: set[str] = set()
        step = 0

        for fp in files:
            try:
                key = str(fp.resolve())
            except Exception:
                key = str(fp)

            if key in seen:
                continue
            seen.add(key)

            state_id = fp.stem
            rel = self._copy_image(str(fp), out_dir, f"state_{step:06d}_{slug(state_id, 60)}")
            if not rel:
                continue

            yield LearningEpisode(
                episode_id=f"state_image_{step:06d}_{slug(state_id, 40)}",
                source="state_image",
                step_index=offset + step,
                task="screen_perception",
                goal="understand the current STB/TV screen",
                after_state_id=state_id,
                after_image=rel,
                after_label=state_id,
                confidence=0.45,
                changed=False,
                success_label=True,
                quality_flags=["state_image_harvest", "indexed_state_image_export"],
            )
            step += 1

    def _write_sft(self, out_dir: Path, episodes: List[LearningEpisode]) -> Dict[str, int]:
        screen_rows: List[Dict[str, Any]] = []
        policy_rows: List[Dict[str, Any]] = []
        verifier_rows: List[Dict[str, Any]] = []
        for ep in episodes:
            screen_img = ep.after_image or ep.before_image
            if screen_img:
                screen_rows.append({
                    "id": f"{ep.episode_id}:screen",
                    "image": screen_img,
                    "messages": [
                        {"role": "user", "content": "<image>\nAnalyze this DISH/STB screen. Return compact JSON with screen_type, focused_element, selectable_options, risk_flags, and confidence."},
                        {"role": "assistant", "content": json.dumps(self._screen_completion(ep), ensure_ascii=False, separators=(",", ":"))},
                    ],
                })
            if ep.before_image and ep.action:
                policy_rows.append({
                    "id": f"{ep.episode_id}:policy",
                    "image": ep.before_image,
                    "messages": [
                        {"role": "user", "content": f"<image>\nGoal: {ep.goal or 'explore the TV UI safely'}. Given the current screen, choose the next safe remote action as JSON with action_sequence, expected_result, risk, and confidence."},
                        {"role": "assistant", "content": json.dumps(self._policy_completion(ep), ensure_ascii=False, separators=(",", ":"))},
                    ],
                })
            if ep.before_image and ep.after_image:
                verifier_rows.append({
                    "id": f"{ep.episode_id}:verify",
                    "images": [ep.before_image, ep.after_image],
                    "messages": [
                        {"role": "user", "content": f"<image>\n<image>\nThe remote action was {ep.action_sequence or [ep.action]}. Did the after-screen satisfy the expected transition? Return JSON with success, evidence, correction, and confidence."},
                        {"role": "assistant", "content": json.dumps(self._verify_completion(ep), ensure_ascii=False, separators=(",", ":"))},
                    ],
                })
        return {
            "screen_perception": append_jsonl(out_dir / "sft" / "screen_perception.jsonl", screen_rows),
            "action_policy": append_jsonl(out_dir / "sft" / "action_policy.jsonl", policy_rows),
            "outcome_verifier": append_jsonl(out_dir / "sft" / "outcome_verifier.jsonl", verifier_rows),
        }

    def _screen_completion(self, ep: LearningEpisode) -> Dict[str, Any]:
        screen_type = first_present(
            ep.guide_grid.get("screen_type") if isinstance(ep.guide_grid, dict) else "",
            ep.channel_metadata.get("screen_type") if isinstance(ep.channel_metadata, dict) else "",
            ep.focus.get("focus_role") if isinstance(ep.focus, dict) else "",
            "unknown",
        )
        focused = first_present(
            ep.focus.get("human_label") if isinstance(ep.focus, dict) else "",
            ep.focus.get("focused_item") if isinstance(ep.focus, dict) else "",
            ep.after_label,
            ep.before_label,
        )
        options: List[Dict[str, Any]] = []
        if isinstance(ep.guide_grid, dict):
            for row in as_list(ep.guide_grid.get("rows"))[:8]:
                if not isinstance(row, dict):
                    continue
                for p in as_list(row.get("programs"))[:8]:
                    if isinstance(p, dict):
                        options.append({
                            "title": p.get("title") or p.get("raw_text") or "",
                            "channel_number": first_present(p.get("channel_number"), row.get("channel_number")),
                            "channel_code": first_present(p.get("channel_code"), row.get("channel_code")),
                            "button_sequence": p.get("button_sequence") or [],
                        })
        return {
            "screen_type": screen_type,
            "focused_element": focused,
            "selectable_options": options[:20],
            "risk_flags": ep.risk_flags,
            "confidence": round(float(ep.confidence or 0.0), 4),
        }

    def _policy_completion(self, ep: LearningEpisode) -> Dict[str, Any]:
        risk = "blocked" if ep.risk_flags and ep.action == "select" else "safe"
        expected = "screen changes" if ep.changed else "focus or screen may remain similar"
        if ep.after_label:
            expected = f"arrive at or focus {ep.after_label[:120]}"
        return {
            "action_sequence": ep.action_sequence or ([ep.action] if ep.action else []),
            "expected_result": expected,
            "risk": risk,
            "confidence": round(max(float(ep.confidence or 0.0), 0.25 if ep.success_label else 0.1), 4),
        }

    def _verify_completion(self, ep: LearningEpisode) -> Dict[str, Any]:
        evidence = ep.after_label or ep.after_state_id or ("state changed" if ep.changed else "state did not visibly change")
        correction = None if ep.success_label else "re-anchor with back/home/guide and retry only after the screen is stable"
        return {
            "success": bool(ep.success_label),
            "evidence": evidence,
            "correction": correction,
            "confidence": round(max(float(ep.confidence or 0.0), 0.35 if ep.success_label else 0.2), 4),
        }

    def _float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, ""):
                return default
            return float(value)
        except Exception:
            return default

    def _copy_image(self, value: Any, out_dir: Path, prefix: str) -> str:
        if not value:
            return ""
        text = str(value)
        m = re.search(r"/api/crawl/state/([^/]+)/image", text)
        if m:
            return self._copy_state_image(m.group(1), out_dir, prefix)
        if text.startswith("/api/") or text.startswith("http://") or text.startswith("https://"):
            return ""
        path = Path(text.replace("\\", os.sep))
        candidates = []
        if path.is_absolute():
            candidates.append(path)
        else:
            candidates.extend([
                self.root_dir / path,
                self.crawler_dir / path,
                self.root_dir / "crawler_data" / path,
                self.root_dir / "states" / path,
                self.crawler_dir / "states" / path,
            ])
        src = next((p for p in candidates if p.is_file()), None)
        if not src:
            return ""
        key = str(src.resolve())
        if key in self._copied:
            return self._copied[key]
        suffix = src.suffix.lower() if src.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        dest_rel = f"images/{slug(prefix)}_{digest}{suffix}"
        dest = out_dir / dest_rel
        try:
            if Image is not None and self.image_max_width > 0:
                img = Image.open(src)
                if img.width > self.image_max_width:
                    ratio = self.image_max_width / float(img.width)
                    img = img.resize((self.image_max_width, max(1, int(img.height * ratio))))
                if img.mode not in {"RGB", "RGBA"}:
                    img = img.convert("RGB")
                img.save(dest, quality=88)
            else:
                shutil.copy2(src, dest)
            self._copied[key] = dest_rel
            return dest_rel
        except Exception:
            return ""


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Export aBotTesty phase-1 multimodal learning dataset")
    p.add_argument("--root", default=".", help="Repo/app root directory")
    p.add_argument("--crawler-dir", default="", help="Crawler data directory, defaults to <root>/crawler_data")
    p.add_argument("--out", default="", help="Output root, defaults to <root>/learning_datasets")
    p.add_argument("--run-id", default="", help="Optional export run id")
    p.add_argument("--max-records", type=int, default=0, help="Limit exported episodes for smoke tests")
    p.add_argument("--include-raw", action="store_true", help="Keep raw source records in JSONL")
    p.add_argument("--stats", action="store_true", help="Only print source stats")
    args = p.parse_args(argv)
    writer = LearningDatasetWriter(
        root_dir=args.root,
        crawler_dir=args.crawler_dir or None,
        out_dir=args.out or None,
        include_raw=args.include_raw,
    )
    result = writer.stats() if args.stats else writer.export(run_id=args.run_id or None, max_records=args.max_records, include_raw=args.include_raw)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
