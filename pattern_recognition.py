"""
UI Pattern Recognition Module for aBotTesty
Classifies UI screens into pattern types for adaptive exploration.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import re


class UIPattern(Enum):
    """UI pattern types for adaptive navigation strategy."""
    GRID_MENU = "grid_menu"          # Guide, apps, channel grid
    LINEAR_MENU = "linear_menu"       # Settings list, vertical menu
    FORM = "form"                     # Input fields, search
    VIDEO_PLAYER = "video_player"     # Live TV, DVR playback
    INFO_CARD = "info_card"           # Program details, diagnostics
    UNKNOWN = "unknown"
    
    def __str__(self) -> str:
        return self.value


@dataclass
class PatternConfidence:
    """Confidence scores for pattern classification."""
    pattern: UIPattern
    confidence: float
    reasons: List[str] = field(default_factory=list)


class PatternRecognizer:
    """Classifies UI screens into patterns for adaptive exploration."""
    
    # Pattern-specific keywords
    GRID_KEYWORDS = re.compile(
        r"\b(guide|grid|channel|browse|apps|gallery|library|catalog)\b", 
        re.IGNORECASE
    )
    LINEAR_MENU_KEYWORDS = re.compile(
        r"\b(settings|menu|options|preferences|list|setup|configure)\b",
        re.IGNORECASE
    )
    FORM_KEYWORDS = re.compile(
        r"\b(search|enter|input|type|keyboard|find|query)\b",
        re.IGNORECASE
    )
    VIDEO_KEYWORDS = re.compile(
        r"\b(live|watching|playing|dvr|recorded|playback|pause|resume)\b",
        re.IGNORECASE
    )
    INFO_KEYWORDS = re.compile(
        r"\b(info|details|description|synopsis|about|diagnostic|status)\b",
        re.IGNORECASE
    )
    
    def __init__(self):
        self.learned_patterns: Dict[str, UIPattern] = {}
        self.pattern_history: List[Dict[str, Any]] = []
    
    def classify_screen(self, fp: Any, focus: Optional[Dict[str, Any]] = None) -> PatternConfidence:
        """
        Classify UI pattern from screen fingerprint and focus data.
        
        Args:
            fp: ScreenFingerprint with visual and OCR features
            focus: Optional focus detection data
            
        Returns:
            PatternConfidence with pattern type and confidence score
        """
        if focus is None:
            focus = getattr(fp, 'focus', {}) or {}
        
        scores: Dict[UIPattern, float] = {
            UIPattern.GRID_MENU: 0.0,
            UIPattern.LINEAR_MENU: 0.0,
            UIPattern.FORM: 0.0,
            UIPattern.VIDEO_PLAYER: 0.0,
            UIPattern.INFO_CARD: 0.0,
        }
        reasons: Dict[UIPattern, List[str]] = {p: [] for p in scores.keys()}
        
        # Extract text for keyword matching
        text = self._get_all_text(fp, focus)
        
        # Score based on keywords
        if self.GRID_KEYWORDS.search(text):
            scores[UIPattern.GRID_MENU] += 0.30
            reasons[UIPattern.GRID_MENU].append("grid keywords detected")
        
        if self.LINEAR_MENU_KEYWORDS.search(text):
            scores[UIPattern.LINEAR_MENU] += 0.30
            reasons[UIPattern.LINEAR_MENU].append("menu keywords detected")
        
        if self.FORM_KEYWORDS.search(text):
            scores[UIPattern.FORM] += 0.35
            reasons[UIPattern.FORM].append("form keywords detected")
        
        if self.VIDEO_KEYWORDS.search(text):
            scores[UIPattern.VIDEO_PLAYER] += 0.25
            reasons[UIPattern.VIDEO_PLAYER].append("video keywords detected")
        
        if self.INFO_KEYWORDS.search(text):
            scores[UIPattern.INFO_CARD] += 0.25
            reasons[UIPattern.INFO_CARD].append("info keywords detected")
        
        # Score based on visual features
        self._score_visual_features(fp, scores, reasons)
        
        # Score based on focus behavior
        if isinstance(focus, dict) and focus.get('found'):
            self._score_focus_features(focus, scores, reasons)
        
        # Score based on layout hints
        self._score_layout_hints(fp, focus, scores, reasons)
        
        # Find highest scoring pattern
        if max(scores.values()) < 0.30:
            return PatternConfidence(
                pattern=UIPattern.UNKNOWN,
                confidence=0.0,
                reasons=["insufficient evidence"]
            )
        
        best_pattern = max(scores.items(), key=lambda x: x[1])
        confidence = min(1.0, max(0.0, best_pattern[1]))
        
        return PatternConfidence(
            pattern=best_pattern[0],
            confidence=confidence,
            reasons=reasons[best_pattern[0]]
        )
    
    def _get_all_text(self, fp: Any, focus: Optional[Dict[str, Any]]) -> str:
        """Combine all available text sources."""
        parts = []
        
        # OCR text from fingerprint
        if hasattr(fp, 'ocr_text') and fp.ocr_text:
            parts.append(fp.ocr_text)
        
        # Focus text
        if isinstance(focus, dict):
            for key in ['screen_title', 'menu_title', 'focused_item', 'label_text', 
                       'context_text', 'row_text']:
                val = focus.get(key)
                if val and isinstance(val, str):
                    parts.append(val)
        
        return " ".join(parts).lower()
    
    def _score_visual_features(self, fp: Any, scores: Dict[UIPattern, float], 
                               reasons: Dict[UIPattern, List[str]]) -> None:
        """Score patterns based on visual characteristics."""
        # Video player: high variance, low edge density (video content dominant)
        if hasattr(fp, 'variance') and hasattr(fp, 'edge_density'):
            if fp.variance > 1500 and fp.edge_density < 0.15:
                scores[UIPattern.VIDEO_PLAYER] += 0.25
                reasons[UIPattern.VIDEO_PLAYER].append(
                    f"high variance ({fp.variance:.0f}), low edges ({fp.edge_density:.2f})"
                )
        
        # Info card: high text token count, low variance
        if hasattr(fp, 'ocr_tokens') and hasattr(fp, 'variance'):
            if len(fp.ocr_tokens) > 30 and fp.variance < 800:
                scores[UIPattern.INFO_CARD] += 0.20
                reasons[UIPattern.INFO_CARD].append(
                    f"high text density ({len(fp.ocr_tokens)} tokens)"
                )
        
        # Grid/Menu: moderate edge density (structured UI)
        if hasattr(fp, 'edge_density'):
            if 0.20 < fp.edge_density < 0.40:
                scores[UIPattern.GRID_MENU] += 0.10
                scores[UIPattern.LINEAR_MENU] += 0.10
                reasons[UIPattern.GRID_MENU].append("structured layout (edges)")
                reasons[UIPattern.LINEAR_MENU].append("structured layout (edges)")
    
    def _score_focus_features(self, focus: Dict[str, Any], scores: Dict[UIPattern, float],
                             reasons: Dict[UIPattern, List[str]]) -> None:
        """Score patterns based on focus detection."""
        # Grid menu: focus can move in multiple directions
        layout_hint = focus.get('layout_hint') or ''
        if 'grid' in layout_hint.lower():
            scores[UIPattern.GRID_MENU] += 0.30
            reasons[UIPattern.GRID_MENU].append("grid layout from focus")
        
        # Linear menu: focus moves only vertically
        if 'vertical' in layout_hint.lower() or 'list' in layout_hint.lower():
            scores[UIPattern.LINEAR_MENU] += 0.30
            reasons[UIPattern.LINEAR_MENU].append("vertical list from focus")
        
        # Check focus region
        region = focus.get('region', '')
        if region == 'center' and focus.get('confidence', 0) < 0.40:
            # Weak focus in center suggests video content
            scores[UIPattern.VIDEO_PLAYER] += 0.15
            reasons[UIPattern.VIDEO_PLAYER].append("weak central focus")
    
    def _score_layout_hints(self, fp: Any, focus: Optional[Dict[str, Any]],
                           scores: Dict[UIPattern, float], 
                           reasons: Dict[UIPattern, List[str]]) -> None:
        """Score based on learned layout patterns."""
        # Check if we've seen this state pattern before
        state_id = getattr(fp, 'state_id', '')
        if state_id in self.learned_patterns:
            learned = self.learned_patterns[state_id]
            scores[learned] += 0.20
            reasons[learned].append(f"previously learned as {learned.value}")
    
    def learn_pattern(self, state_id: str, pattern: UIPattern) -> None:
        """Record learned pattern for this state."""
        self.learned_patterns[state_id] = pattern
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about pattern classifications."""
        from collections import Counter
        counts = Counter(self.learned_patterns.values())
        return {
            "total_classified": len(self.learned_patterns),
            "by_pattern": {str(k): v for k, v in counts.items()},
            "history_length": len(self.pattern_history)
        }


class AdaptiveThresholdModel:
    """
    Adaptive similarity thresholds based on UI pattern type.
    Different UI types require different matching strictness.
    """
    
    def __init__(self):
        # Base thresholds by pattern type
        self.thresholds: Dict[str, float] = {
            "grid_menu": 0.82,      # Lower - thumbnails/content changes
            "linear_menu": 0.94,    # Higher - very static structure
            "form": 0.88,           # Medium - some dynamic content
            "video_player": 0.75,   # Lowest - video content changes constantly
            "info_card": 0.91,      # High - text-based, stable
            "unknown": 0.86         # Default (original threshold)
        }
        
        # Track match statistics for learning
        self.stats: Dict[str, Dict[str, int]] = {}
        for pattern in self.thresholds.keys():
            self.stats[pattern] = {
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "total_comparisons": 0
            }
        
        # State stability tracking (for per-state threshold adjustment)
        self.state_stability: Dict[str, float] = {}
    
    def get_threshold(self, pattern: str, state_id: Optional[str] = None) -> float:
        """
        Get adaptive threshold for this pattern and state.
        
        Args:
            pattern: UI pattern type
            state_id: Optional state ID for per-state adjustment
            
        Returns:
            Threshold value (0.0 to 1.0)
        """
        # Get base threshold for pattern
        base = self.thresholds.get(pattern, 0.86)
        
        # If state has history, adjust based on stability
        if state_id and state_id in self.state_stability:
            stability = self.state_stability[state_id]
            # Stable states get stricter thresholds (fewer false matches)
            adjustment = stability * 0.08  # Up to +8% for very stable states
            return min(0.98, base + adjustment)
        
        return base
    
    def record_comparison(self, pattern: str, similarity: float, 
                         was_match: bool, should_match: bool) -> None:
        """
        Record a comparison result for learning.
        
        Args:
            pattern: UI pattern type
            similarity: Similarity score
            was_match: Whether it matched (similarity >= threshold)
            should_match: Ground truth (whether it should have matched)
        """
        if pattern not in self.stats:
            pattern = "unknown"
        
        stats = self.stats[pattern]
        stats["total_comparisons"] += 1
        
        if was_match and should_match:
            stats["true_positives"] += 1
        elif was_match and not should_match:
            stats["false_positives"] += 1
            # Too many false positives: increase threshold
            if stats["false_positives"] > 5:
                self.thresholds[pattern] = min(0.98, self.thresholds[pattern] + 0.01)
        elif not was_match and should_match:
            stats["false_negatives"] += 1
            # Too many false negatives: decrease threshold
            if stats["false_negatives"] > 5:
                self.thresholds[pattern] = max(0.70, self.thresholds[pattern] - 0.01)
    
    def update_state_stability(self, state_id: str, observations: int, 
                               variance: float) -> None:
        """
        Update stability score for a state.
        
        Args:
            state_id: State identifier
            observations: Number of times observed
            variance: Visual variance of the state
        """
        # Stability increases with observations and decreases with variance
        observation_factor = min(1.0, observations / 20.0)  # Max at 20 observations
        variance_factor = max(0.0, 1.0 - (variance / 2000.0))  # Normalize variance
        
        stability = (observation_factor * 0.6 + variance_factor * 0.4)
        self.state_stability[state_id] = stability
    
    def get_stats(self) -> Dict[str, Any]:
        """Get threshold statistics for monitoring."""
        return {
            "thresholds": self.thresholds.copy(),
            "stats": {k: v.copy() for k, v in self.stats.items()},
            "state_count": len(self.state_stability)
        }
    
    def get_threshold_summary(self) -> str:
        """Get human-readable threshold summary."""
        lines = ["Adaptive Thresholds:"]
        for pattern, threshold in sorted(self.thresholds.items()):
            stats = self.stats.get(pattern, {})
            total = stats.get("total_comparisons", 0)
            tp = stats.get("true_positives", 0)
            accuracy = (tp / max(1, total)) * 100 if total > 0 else 0
            lines.append(f"  {pattern:15} -> {threshold:.3f} (accuracy: {accuracy:.1f}%, n={total})")
        return "\n".join(lines)
