"""Track hard-to-reach states and prioritize retries."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json


@dataclass
class UnreachableState:
    state_id: str
    first_attempt: str
    last_attempt: str
    failed_routes: List[List[str]] = field(default_factory=list)
    attempts: int = 0
    priority: float = 1.0
    reason: str = ""
    last_error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class PersistenceTracker:
    IMPORTANT = ("settings", "parental", "diagnostics", "network", "system", "security", "control", "advanced", "locked")

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "unreachable_states.json"
        self.unreachable: Dict[str, UnreachableState] = {}
        self.total_failures_tracked = 0
        self.total_retries_attempted = 0
        self.successful_retries = 0
        self.load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _priority(self, context: Dict[str, Any]) -> float:
        text = " ".join(str(context.get(k, "")) for k in ("label", "pattern", "reason", "title")).lower()
        p = 0.45 + (0.35 if any(k in text for k in self.IMPORTANT) else 0.0)
        depth = int(context.get("depth", 0) or 0)
        if depth >= 5:
            p += 0.12
        return round(min(1.0, p), 4)

    def mark_navigation_failed(self, state_id: str, route: List[str], reason: str, error: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> None:
        now = self._now(); context = context or {}
        st = self.unreachable.get(state_id)
        if not st:
            st = UnreachableState(state_id=state_id, first_attempt=now, last_attempt=now, reason=reason, last_error=error, context=context)
            self.unreachable[state_id] = st
        st.last_attempt = now; st.attempts += 1; st.last_error = error or st.last_error; st.context.update(context); st.reason = reason or st.reason
        st.failed_routes.append(list(route or [])); st.failed_routes = st.failed_routes[-12:]
        st.priority = self._priority(st.context | {"reason": reason})
        self.total_failures_tracked += 1
        self.save()

    def mark_navigation_succeeded(self, state_id: str) -> None:
        if state_id in self.unreachable:
            self.successful_retries += 1
            del self.unreachable[state_id]
            self.save()

    def record_retry_attempt(self, state_id: str) -> None:
        self.total_retries_attempted += 1

    def get_retry_candidates(self, max_attempts: int = 5, min_priority: float = 0.35) -> List[Tuple[str, float]]:
        rows = [(sid, st.priority) for sid, st in self.unreachable.items() if st.attempts < max_attempts and st.priority >= min_priority]
        return sorted(rows, key=lambda x: x[1], reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_unreachable": len(self.unreachable),
            "total_failures_tracked": self.total_failures_tracked,
            "total_retries_attempted": self.total_retries_attempted,
            "successful_retries": self.successful_retries,
            "top_unreachable": [{"state_id": sid, **asdict(st)} for sid, st in sorted(self.unreachable.items(), key=lambda kv: kv[1].priority, reverse=True)[:8]],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": "persistence_tracker_v2", "updated_at": self._now(), "unreachable_states": {k: asdict(v) for k, v in self.unreachable.items()}, "stats": self.get_stats()}

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for sid, data in raw.get("unreachable_states", {}).items():
                self.unreachable[sid] = UnreachableState(**{k: v for k, v in data.items() if k in UnreachableState.__dataclass_fields__})
            stats = raw.get("stats", {})
            self.total_failures_tracked = int(stats.get("total_failures_tracked", 0) or 0)
            self.total_retries_attempted = int(stats.get("total_retries_attempted", 0) or 0)
            self.successful_retries = int(stats.get("successful_retries", 0) or 0)
        except Exception:
            self.unreachable = {}

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def reset(self) -> None:
        self.unreachable.clear(); self.total_failures_tracked = 0; self.total_retries_attempted = 0; self.successful_retries = 0; self.save()
