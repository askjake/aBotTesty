"""Action sequence learner for manual demos and autonomous crawl history."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
import json


@dataclass
class LearnedSequence:
    sequence: List[str]
    observations: int = 0
    success_rate: float = 0.0
    avg_reward: float = 0.0
    typical_context: List[str] = field(default_factory=list)
    leads_to: List[str] = field(default_factory=list)
    avg_time_s: float = 0.0
    last_used: Optional[str] = None
    confidence: float = 0.0
    source_counts: Dict[str, int] = field(default_factory=dict)
    demonstration_weight: float = 1.0


class SequenceLearner:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "learned_sequences.json"
        self.action_history: Deque[Dict[str, Any]] = deque(maxlen=1600)
        self.learned_sequences: Dict[str, LearnedSequence] = {}
        self.total_sequences_mined = 0
        self.total_suggestions_made = 0
        self.successful_suggestions = 0
        self.load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def record_action(self, from_state: str, action: str, to_state: str, reward: float, time_s: float = 0.0, source: str = "autonomous", weight: float = 1.0) -> None:
        self.action_history.append({
            "from": from_state,
            "action": str(action),
            "to": to_state,
            "reward": float(reward or 0.0),
            "time_s": float(time_s or 0.0),
            "source": str(source or "autonomous"),
            "weight": max(0.1, float(weight or 1.0)),
            "timestamp": self._now(),
        })

    def mine_sequences(self, min_length: int = 2, max_length: int = 5, min_occurrences: int = 3, min_avg_reward: float = 2.0) -> List[LearnedSequence]:
        hist = list(self.action_history)
        if len(hist) < min_length:
            return []
        actions = [h["action"] for h in hist]
        discovered: List[LearnedSequence] = []
        for length in range(min_length, min(max_length, len(actions)) + 1):
            counts = Counter(tuple(actions[i:i+length]) for i in range(0, len(actions)-length+1))
            for seq, count in counts.items():
                if count < min_occurrences:
                    continue
                key = ",".join(seq)
                rewards, contexts, dests, times, sources = [], [], [], [], []
                for i in range(0, len(actions)-length+1):
                    if tuple(actions[i:i+length]) == seq:
                        window = hist[i:i+length]
                        rewards.append(sum(float(x.get("reward", 0.0)) * max(0.1, float(x.get("weight", 1.0) or 1.0)) for x in window))
                        contexts.append(hist[i].get("from", ""))
                        dests.append(hist[i+length-1].get("to", ""))
                        times.append(sum(float(x.get("time_s", 0.0)) for x in window))
                        sources.extend(str(x.get("source") or "autonomous") for x in window)
                avg_reward = sum(rewards) / max(1, len(rewards))
                if avg_reward < min_avg_reward:
                    continue
                learned = self.learned_sequences.get(key) or LearnedSequence(sequence=list(seq))
                learned.observations = count
                learned.avg_reward = round(avg_reward, 3)
                learned.avg_time_s = round(sum(times)/max(1, len(times)), 3)
                learned.typical_context = list(dict.fromkeys(contexts))[:8]
                learned.leads_to = list(dict.fromkeys(dests))[:8]
                src_counts = Counter(sources)
                learned.source_counts = dict(src_counts)
                demo_obs = sum(v for k, v in src_counts.items() if k.startswith("manual") or "operator" in k)
                learned.demonstration_weight = round(1.0 + min(3.0, demo_obs / max(1, count)), 3)
                learned.confidence = round(min(1.0, (count / 8.0) * max(0.1, min(1.0, avg_reward / 10.0)) * learned.demonstration_weight), 4)
                self.learned_sequences[key] = learned
                discovered.append(learned)
        if discovered:
            self.total_sequences_mined += len(discovered)
            self.save()
        return discovered

    def suggest_next_action(self, recent_actions: List[str]) -> Optional[Tuple[str, float]]:
        if not recent_actions:
            return None
        best: Optional[Tuple[str, float]] = None
        for learned in self.learned_sequences.values():
            seq = learned.sequence
            for n in range(1, len(seq)):
                if len(recent_actions) >= n and recent_actions[-n:] == seq[:n]:
                    conf = learned.confidence * (n / len(seq))
                    if best is None or conf > best[1]:
                        best = (seq[n], conf)
        if best:
            self.total_suggestions_made += 1
        return best

    def record_suggestion_outcome(self, success: bool) -> None:
        if success:
            self.successful_suggestions += 1

    def get_top_sequences(self, limit: int = 12) -> List[Tuple[str, LearnedSequence]]:
        return sorted(self.learned_sequences.items(), key=lambda kv: kv[1].avg_reward * max(0.05, kv[1].confidence) * max(1.0, getattr(kv[1], "demonstration_weight", 1.0)), reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.learned_sequences)
        return {
            "total_sequences": total,
            "history_size": len(self.action_history),
            "total_mined": self.total_sequences_mined,
            "suggestions_made": self.total_suggestions_made,
            "successful_suggestions": self.successful_suggestions,
            "top_sequences": [{"key": k, **asdict(v)} for k, v in self.get_top_sequences(8)],
            "demonstration_sequences": sum(1 for v in self.learned_sequences.values() if any(str(k).startswith("manual") or "operator" in str(k) for k in (getattr(v, "source_counts", {}) or {}))),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": "sequence_learner_v2", "updated_at": self._now(), "learned_sequences": {k: asdict(v) for k, v in self.learned_sequences.items()}, "stats": self.get_stats()}

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for key, val in raw.get("learned_sequences", {}).items():
                self.learned_sequences[key] = LearnedSequence(**{k: v for k, v in val.items() if k in LearnedSequence.__dataclass_fields__})
            stats = raw.get("stats", {})
            self.total_sequences_mined = int(stats.get("total_mined", 0) or 0)
            self.total_suggestions_made = int(stats.get("suggestions_made", stats.get("total_suggestions", 0)) or 0)
            self.successful_suggestions = int(stats.get("successful_suggestions", 0) or 0)
        except Exception:
            self.learned_sequences = {}

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def reset(self) -> None:
        self.action_history.clear(); self.learned_sequences.clear(); self.total_sequences_mined = 0; self.total_suggestions_made = 0; self.successful_suggestions = 0; self.save()
