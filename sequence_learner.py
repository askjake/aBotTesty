"""
Action Sequence Learning Module for aBotTesty
Discovers and learns useful action patterns through n-gram mining.
"""

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import json


@dataclass
class LearnedSequence:
    """Represents a learned action sequence with statistics."""
    sequence: List[str]
    observations: int = 0
    success_rate: float = 0.0
    avg_reward: float = 0.0
    typical_context: List[str] = field(default_factory=list)  # From which states
    leads_to: List[str] = field(default_factory=list)  # To which states
    avg_time_s: float = 0.0
    last_used: Optional[str] = None
    confidence: float = 0.0


class SequenceLearner:
    """
    Learns useful action sequences through exploration.
    
    Discovers patterns like "guide,down,select" that frequently lead to
    useful outcomes, then suggests completing them when detected.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "learned_sequences.json"
        
        # Recent action history for mining
        self.action_history: deque = deque(maxlen=1000)
        
        # Learned sequences keyed by sequence string
        self.learned_sequences: Dict[str, LearnedSequence] = {}
        
        # Statistics
        self.total_sequences_mined: int = 0
        self.total_suggestions_made: int = 0
        self.successful_suggestions: int = 0
        
        self.load()
    
    @staticmethod
    def _now() -> str:
        """Get current timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    def record_action(self, from_state: str, action: str, to_state: str, 
                     reward: float, time_s: float = 0.0) -> None:
        """
        Record an action for sequence mining.
        
        Args:
            from_state: State before action
            action: Action taken
            to_state: State after action
            reward: Reward received
            time_s: Time taken for action
        """
        self.action_history.append({
            "from": from_state,
            "action": action,
            "to": to_state,
            "reward": reward,
            "time_s": time_s,
            "timestamp": self._now()
        })
    
    def mine_sequences(self, min_length: int = 2, max_length: int = 5,
                      min_occurrences: int = 3, min_avg_reward: float = 2.0) -> List[LearnedSequence]:
        """
        Mine frequent action patterns from history.
        
        Args:
            min_length: Minimum sequence length
            max_length: Maximum sequence length
            min_occurrences: Minimum times sequence must appear
            min_avg_reward: Minimum average reward to be useful
            
        Returns:
            List of newly discovered sequences
        """
        if len(self.action_history) < min_length:
            return []
        
        # Extract action sequences
        action_seq = [h["action"] for h in self.action_history]
        
        # Find all candidate subsequences
        candidates = []
        for length in range(min_length, min(max_length + 1, len(action_seq) + 1)):
            for i in range(len(action_seq) - length + 1):
                subseq = tuple(action_seq[i:i+length])
                candidates.append(subseq)
        
        # Count occurrences
        counter = Counter(candidates)
        
        # Evaluate each candidate
        new_sequences = []
        for seq_tuple, count in counter.items():
            if count < min_occurrences:
                continue
            
            # Skip if already learned
            seq_key = ",".join(seq_tuple)
            if seq_key in self.learned_sequences:
                # Update existing sequence stats
                self._update_sequence_stats(seq_key, seq_tuple)
                continue
            
            # Calculate average reward for this sequence
            rewards = self._get_sequence_rewards(seq_tuple)
            if not rewards:
                continue
            
            avg_reward = sum(rewards) / len(rewards)
            
            # Only keep useful sequences
            if avg_reward < min_avg_reward:
                continue
            
            # Get context (which states it appears in)
            contexts = self._get_sequence_contexts(seq_tuple)
            
            # Get destinations
            destinations = self._get_sequence_destinations(seq_tuple)
            
            # Calculate average time
            avg_time = self._get_sequence_avg_time(seq_tuple)
            
            # Calculate confidence based on consistency
            confidence = min(1.0, (count / 10.0) * (avg_reward / 10.0))
            
            # Create learned sequence
            new_seq = LearnedSequence(
                sequence=list(seq_tuple),
                observations=count,
                avg_reward=round(avg_reward, 2),
                typical_context=contexts[:5],  # Top 5 contexts
                leads_to=destinations[:5],  # Top 5 destinations
                avg_time_s=round(avg_time, 2),
                confidence=round(confidence, 3)
            )
            
            self.learned_sequences[seq_key] = new_seq
            new_sequences.append(new_seq)
            self.total_sequences_mined += 1
        
        if new_sequences:
            self.save()
        
        return new_sequences
    
    def _get_sequence_rewards(self, seq: Tuple[str, ...]) -> List[float]:
        """Get rewards for all occurrences of this sequence."""
        rewards = []
        action_list = [h["action"] for h in self.action_history]
        reward_list = [h["reward"] for h in self.action_history]
        
        seq_len = len(seq)
        for i in range(len(action_list) - seq_len + 1):
            if tuple(action_list[i:i+seq_len]) == seq:
                # Sum rewards for this sequence occurrence
                seq_reward = sum(reward_list[i:i+seq_len])
                rewards.append(seq_reward)
        
        return rewards
    
    def _get_sequence_contexts(self, seq: Tuple[str, ...]) -> List[str]:
        """Get states where this sequence appeared."""
        contexts = []
        action_list = [h["action"] for h in self.action_history]
        from_list = [h["from"] for h in self.action_history]
        
        seq_len = len(seq)
        for i in range(len(action_list) - seq_len + 1):
            if tuple(action_list[i:i+seq_len]) == seq:
                if from_list[i] not in contexts:
                    contexts.append(from_list[i])
        
        return contexts
    
    def _get_sequence_destinations(self, seq: Tuple[str, ...]) -> List[str]:
        """Get states where this sequence leads."""
        destinations = []
        action_list = [h["action"] for h in self.action_history]
        to_list = [h["to"] for h in self.action_history]
        
        seq_len = len(seq)
        for i in range(len(action_list) - seq_len + 1):
            if tuple(action_list[i:i+seq_len]) == seq:
                # Get destination of last action in sequence
                dest = to_list[min(i + seq_len - 1, len(to_list) - 1)]
                if dest not in destinations:
                    destinations.append(dest)
        
        return destinations
    
    def _get_sequence_avg_time(self, seq: Tuple[str, ...]) -> float:
        """Get average time for this sequence."""
        times = []
        action_list = [h["action"] for h in self.action_history]
        time_list = [h.get("time_s", 0.0) for h in self.action_history]
        
        seq_len = len(seq)
        for i in range(len(action_list) - seq_len + 1):
            if tuple(action_list[i:i+seq_len]) == seq:
                seq_time = sum(time_list[i:i+seq_len])
                times.append(seq_time)
        
        return sum(times) / len(times) if times else 0.0
    
    def _update_sequence_stats(self, seq_key: str, seq_tuple: Tuple[str, ...]) -> None:
        """Update statistics for an existing sequence."""
        if seq_key not in self.learned_sequences:
            return
        
        learned = self.learned_sequences[seq_key]
        
        # Recount occurrences
        action_list = [h["action"] for h in self.action_history]
        count = sum(1 for i in range(len(action_list) - len(seq_tuple) + 1)
                   if tuple(action_list[i:i+len(seq_tuple)]) == seq_tuple)
        
        learned.observations = count
        
        # Update reward
        rewards = self._get_sequence_rewards(seq_tuple)
        if rewards:
            learned.avg_reward = round(sum(rewards) / len(rewards), 2)
        
        # Update time
        learned.avg_time_s = round(self._get_sequence_avg_time(seq_tuple), 2)
        
        # Update confidence
        learned.confidence = round(min(1.0, (count / 10.0) * (learned.avg_reward / 10.0)), 3)
    
    def suggest_next_action(self, recent_actions: List[str]) -> Optional[Tuple[str, float]]:
        """
        Suggest next action based on learned sequences.
        
        Args:
            recent_actions: Recent action history (most recent last)
            
        Returns:
            Tuple of (suggested_action, confidence) or None
        """
        if not recent_actions or not self.learned_sequences:
            return None
        
        best_suggestion = None
        best_confidence = 0.0
        
        # Check all learned sequences
        for seq_key, learned in self.learned_sequences.items():
            sequence = learned.sequence
            
            # Check if recent actions match the beginning of this sequence
            for match_len in range(1, len(sequence)):
                if len(recent_actions) >= match_len:
                    if recent_actions[-match_len:] == sequence[:match_len]:
                        # Found a match! Suggest completing the sequence
                        suggested_action = sequence[match_len]
                        confidence = learned.confidence * (match_len / len(sequence))
                        
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_suggestion = suggested_action
        
        if best_suggestion:
            self.total_suggestions_made += 1
            return (best_suggestion, best_confidence)
        
        return None
    
    def record_suggestion_outcome(self, success: bool) -> None:
        """Record whether a suggestion was successful."""
        if success:
            self.successful_suggestions += 1
    
    def get_sequence_by_key(self, seq_key: str) -> Optional[LearnedSequence]:
        """Get a learned sequence by its key."""
        return self.learned_sequences.get(seq_key)
    
    def get_top_sequences(self, limit: int = 10) -> List[Tuple[str, LearnedSequence]]:
        """Get top sequences by reward."""
        sorted_seqs = sorted(
            self.learned_sequences.items(),
            key=lambda x: x[1].avg_reward * x[1].confidence,
            reverse=True
        )
        return sorted_seqs[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        total_seqs = len(self.learned_sequences)
        avg_length = sum(len(s.sequence) for s in self.learned_sequences.values()) / max(1, total_seqs)
        avg_reward = sum(s.avg_reward for s in self.learned_sequences.values()) / max(1, total_seqs)
        
        suggestion_success_rate = (self.successful_suggestions / max(1, self.total_suggestions_made)) * 100
        
        return {
            "total_sequences": total_seqs,
            "avg_sequence_length": round(avg_length, 1),
            "avg_reward": round(avg_reward, 2),
            "total_mined": self.total_sequences_mined,
            "suggestions_made": self.total_suggestions_made,
            "successful_suggestions": self.successful_suggestions,
            "suggestion_success_rate": round(suggestion_success_rate, 1),
            "history_size": len(self.action_history)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "schema": "sequence_learner_v1",
            "updated_at": self._now(),
            "learned_sequences": {
                k: {
                    "sequence": v.sequence,
                    "observations": v.observations,
                    "success_rate": v.success_rate,
                    "avg_reward": v.avg_reward,
                    "typical_context": v.typical_context,
                    "leads_to": v.leads_to,
                    "avg_time_s": v.avg_time_s,
                    "last_used": v.last_used,
                    "confidence": v.confidence
                }
                for k, v in self.learned_sequences.items()
            },
            "stats": {
                "total_mined": self.total_sequences_mined,
                "total_suggestions": self.total_suggestions_made,
                "successful_suggestions": self.successful_suggestions
            }
        }
    
    def load(self) -> None:
        """Load learned sequences from disk."""
        if not self.path.exists():
            return
        
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            
            # Load sequences
            for seq_key, seq_data in data.get("learned_sequences", {}).items():
                self.learned_sequences[seq_key] = LearnedSequence(
                    sequence=seq_data["sequence"],
                    observations=seq_data.get("observations", 0),
                    success_rate=seq_data.get("success_rate", 0.0),
                    avg_reward=seq_data.get("avg_reward", 0.0),
                    typical_context=seq_data.get("typical_context", []),
                    leads_to=seq_data.get("leads_to", []),
                    avg_time_s=seq_data.get("avg_time_s", 0.0),
                    last_used=seq_data.get("last_used"),
                    confidence=seq_data.get("confidence", 0.0)
                )
            
            # Load stats
            stats = data.get("stats", {})
            self.total_sequences_mined = stats.get("total_mined", 0)
            self.total_suggestions_made = stats.get("total_suggestions", 0)
            self.successful_suggestions = stats.get("successful_suggestions", 0)
            
        except Exception as e:
            print(f"Warning: Could not load sequences: {e}")
    
    def save(self) -> None:
        """Save learned sequences to disk."""
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.path)
    
    def reset(self) -> None:
        """Clear all learned sequences."""
        self.learned_sequences.clear()
        self.action_history.clear()
        self.total_sequences_mined = 0
        self.total_suggestions_made = 0
        self.successful_suggestions = 0
        self.save()
