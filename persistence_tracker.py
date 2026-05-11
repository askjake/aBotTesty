"""
Unreachable State Tracking Module for aBotTesty
Tracks states that can't be reached and retries them with priority.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json


@dataclass
class UnreachableState:
    """Represents a state that navigation failed to reach."""
    state_id: str
    first_attempt: str
    last_attempt: str
    failed_routes: List[List[str]] = field(default_factory=list)
    attempts: int = 0
    priority: float = 1.0  # 0-1, based on importance signals
    reason: str = ""  # Why we think it exists or why it failed
    last_error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)  # Additional metadata


class PersistenceTracker:
    """
    Tracks states that are difficult to reach and manages retry strategies.
    
    Maintains a list of "wanted" states that couldn't be navigated to,
    scores them by priority, and suggests retry attempts.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "unreachable_states.json"
        
        # Unreachable states keyed by state_id
        self.unreachable: Dict[str, UnreachableState] = {}
        
        # Statistics
        self.total_failures_tracked: int = 0
        self.total_retries_attempted: int = 0
        self.successful_retries: int = 0
        
        # Priority keywords for importance detection
        self.important_keywords = [
            "settings", "parental", "admin", "diagnostics",
            "network", "system", "security", "control",
            "preferences", "configuration", "advanced"
        ]
        
        self.load()
    
    @staticmethod
    def _now() -> str:
        """Get current timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    def mark_navigation_failed(self, state_id: str, route: List[str], 
                               reason: str, error: Optional[str] = None,
                               context: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a failed navigation attempt.
        
        Args:
            state_id: State that couldn't be reached
            route: Actions attempted to reach it
            reason: Why we tried to reach it
            error: Optional error message
            context: Additional context (state label, pattern, etc.)
        """
        now = self._now()
        
        if state_id not in self.unreachable:
            # New unreachable state
            self.unreachable[state_id] = UnreachableState(
                state_id=state_id,
                first_attempt=now,
                last_attempt=now,
                reason=reason,
                last_error=error,
                context=context or {}
            )
        else:
            # Update existing
            state = self.unreachable[state_id]
            state.last_attempt = now
            state.attempts += 1
            if error:
                state.last_error = error
            if context:
                state.context.update(context)
        
        # Record the failed route (keep last 10)
        state = self.unreachable[state_id]
        state.failed_routes.append(route)
        state.failed_routes = state.failed_routes[-10:]
        
        # Calculate priority based on importance signals
        state.priority = self._calculate_priority(state_id, state.context)
        
        self.total_failures_tracked += 1
        self.save()
    
    def _calculate_priority(self, state_id: str, context: Dict[str, Any]) -> float:
        """
        Calculate priority for a state (0.0 to 1.0).
        
        Higher priority for states that look important based on:
        - State label contains important keywords
        - Depth in navigation (deeper = potentially more important)
        - Pattern type (settings menus = high priority)
        
        Args:
            state_id: State identifier
            context: Context metadata
            
        Returns:
            Priority score (0.0 to 1.0)
        """
        priority = 0.5  # Base priority
        
        # Check label for important keywords
        label = context.get("label", "").lower()
        if any(kw in label for kw in self.important_keywords):
            priority += 0.3
        
        # Check pattern type
        pattern = context.get("pattern", "").lower()
        if pattern in ["linear_menu", "form"]:
            # Menus and forms often contain settings
            priority += 0.1
        
        # Check depth (deeper navigation is often more important)
        depth = context.get("depth", 0)
        if depth > 5:
            priority += 0.1
        
        # Cap at 1.0
        return min(1.0, priority)
    
    def mark_navigation_succeeded(self, state_id: str) -> None:
        """
        Mark a previously unreachable state as now reachable.
        
        Args:
            state_id: State that was successfully reached
        """
        if state_id in self.unreachable:
            self.successful_retries += 1
            del self.unreachable[state_id]
            self.save()
    
    def get_retry_candidates(self, max_attempts: int = 5, 
                            min_priority: float = 0.3) -> List[Tuple[str, float]]:
        """
        Get states worth retrying, sorted by priority.
        
        Args:
            max_attempts: Don't retry states attempted more than this
            min_priority: Minimum priority threshold
            
        Returns:
            List of (state_id, priority) tuples, sorted by priority descending
        """
        candidates = [
            (state_id, state.priority)
            for state_id, state in self.unreachable.items()
            if state.attempts < max_attempts and state.priority >= min_priority
        ]
        
        # Sort by priority (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    def get_state_info(self, state_id: str) -> Optional[UnreachableState]:
        """Get information about an unreachable state."""
        return self.unreachable.get(state_id)
    
    def record_retry_attempt(self, state_id: str) -> None:
        """Record that we're attempting to retry this state."""
        self.total_retries_attempted += 1
        if state_id in self.unreachable:
            # Don't increment attempts here - will be incremented if it fails again
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracking statistics."""
        total_unreachable = len(self.unreachable)
        avg_priority = sum(s.priority for s in self.unreachable.values()) / max(1, total_unreachable)
        avg_attempts = sum(s.attempts for s in self.unreachable.values()) / max(1, total_unreachable)
        
        retry_success_rate = (self.successful_retries / max(1, self.total_retries_attempted)) * 100
        
        # Priority distribution
        high_priority = sum(1 for s in self.unreachable.values() if s.priority >= 0.7)
        medium_priority = sum(1 for s in self.unreachable.values() if 0.4 <= s.priority < 0.7)
        low_priority = sum(1 for s in self.unreachable.values() if s.priority < 0.4)
        
        return {
            "total_unreachable": total_unreachable,
            "avg_priority": round(avg_priority, 2),
            "avg_attempts": round(avg_attempts, 1),
            "total_failures_tracked": self.total_failures_tracked,
            "total_retries_attempted": self.total_retries_attempted,
            "successful_retries": self.successful_retries,
            "retry_success_rate": round(retry_success_rate, 1),
            "priority_distribution": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority
            }
        }
    
    def get_top_unreachable(self, limit: int = 10) -> List[Tuple[str, UnreachableState]]:
        """Get top unreachable states by priority."""
        sorted_states = sorted(
            self.unreachable.items(),
            key=lambda x: (x[1].priority, -x[1].attempts),
            reverse=True
        )
        return sorted_states[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "schema": "persistence_tracker_v1",
            "updated_at": self._now(),
            "unreachable_states": {
                state_id: {
                    "state_id": state.state_id,
                    "first_attempt": state.first_attempt,
                    "last_attempt": state.last_attempt,
                    "failed_routes": state.failed_routes,
                    "attempts": state.attempts,
                    "priority": state.priority,
                    "reason": state.reason,
                    "last_error": state.last_error,
                    "context": state.context
                }
                for state_id, state in self.unreachable.items()
            },
            "stats": {
                "total_failures_tracked": self.total_failures_tracked,
                "total_retries_attempted": self.total_retries_attempted,
                "successful_retries": self.successful_retries
            }
        }
    
    def load(self) -> None:
        """Load unreachable states from disk."""
        if not self.path.exists():
            return
        
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            
            # Load unreachable states
            for state_id, state_data in data.get("unreachable_states", {}).items():
                self.unreachable[state_id] = UnreachableState(
                    state_id=state_data["state_id"],
                    first_attempt=state_data["first_attempt"],
                    last_attempt=state_data["last_attempt"],
                    failed_routes=state_data.get("failed_routes", []),
                    attempts=state_data.get("attempts", 0),
                    priority=state_data.get("priority", 1.0),
                    reason=state_data.get("reason", ""),
                    last_error=state_data.get("last_error"),
                    context=state_data.get("context", {})
                )
            
            # Load stats
            stats = data.get("stats", {})
            self.total_failures_tracked = stats.get("total_failures_tracked", 0)
            self.total_retries_attempted = stats.get("total_retries_attempted", 0)
            self.successful_retries = stats.get("successful_retries", 0)
            
        except Exception as e:
            print(f"Warning: Could not load persistence tracker: {e}")
    
    def save(self) -> None:
        """Save unreachable states to disk."""
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.path)
    
    def reset(self) -> None:
        """Clear all tracked states."""
        self.unreachable.clear()
        self.total_failures_tracked = 0
        self.total_retries_attempted = 0
        self.successful_retries = 0
        self.save()
