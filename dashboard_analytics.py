#!/usr/bin/env python3
"""Learning dashboard analytics for the merged STB crawler app.

This module reads the crawler's persistent artifacts and emits two views:
- executive: progress, confidence, risk, learning maturity
- engineering: state/action coverage, OCR/focus quality, timings, rewards, frontiers

It is intentionally Superset-friendly: every panel can be exported as JSON/CSV/SQL
without requiring Superset at runtime.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ISO_ZONES = ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z")
DEFAULT_ACTIONS = ["up", "down", "left", "right", "guide", "back", "home", "info", "select"]
IMPORTANT_WORDS = re.compile(r"\b(parental|lock|locked|settings|diagnostics|network|audio|caption|dvr|guide|apps|search|pin|password|control|receiver|signal|system)\b", re.I)
RISK_WORDS = re.compile(r"\b(pin|password|purchase|rent|adult|parental|delete|reset|factory|locked|unlock|payment|subscribe)\b", re.I)
OCR_SOUP = re.compile(r"\b([a-z]{1,2}|[a-z]*[0-9][a-z0-9]*|[bcdfghjklmnpqrstvwxyz]{4,})\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default
    return default


def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    # Some artifacts have compact timestamp fragments in screenshot file names.
    m = re.search(r"(20\d{6})[_-](\d{6})", s)
    if m:
        try:
            return datetime.strptime("".join(m.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def iso_bucket(value: Any, granularity: str = "hour") -> str:
    dt = parse_ts(value)
    if not dt:
        return "unknown"
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d %H:00")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def pct(part: float, total: float) -> float:
    return round((part / total * 100.0), 2) if total else 0.0


def clean_text(s: Any, max_len: int = 140) -> str:
    return " ".join(str(s or "").replace("\n", " ").split())[:max_len]


def get_focus(rep: Dict[str, Any]) -> Dict[str, Any]:
    focus = rep.get("focus") or {}
    return focus if isinstance(focus, dict) else {}


def ui_context(focus: Dict[str, Any]) -> Dict[str, Any]:
    ui = focus.get("ui_context") or {}
    return ui if isinstance(ui, dict) else {}


def focus_title(focus: Dict[str, Any]) -> str:
    ui = ui_context(focus)
    for key in ("page_name", "block_title", "screen_title", "menu_title", "active_tab", "human_label"):
        val = clean_text(focus.get(key) or ui.get(key), 100)
        if val:
            return val
    return ""


def focus_item(focus: Dict[str, Any]) -> str:
    ui = ui_context(focus)
    for key in ("focused_item", "label_text", "focus_text"):
        val = clean_text(focus.get(key) or ui.get(key), 100)
        if val:
            return val
    return ""


def node_label(node: Dict[str, Any]) -> str:
    rep = node.get("representative", {})
    focus = get_focus(rep)
    title = focus_title(focus)
    item = focus_item(focus)
    if title and item and item.lower() not in title.lower():
        return f"{title} → {item}"[:160]
    if title:
        return title[:160]
    return clean_text(node.get("label") or rep.get("ocr_text") or node.get("state_id"), 160)


def classify_quality(node: Dict[str, Any]) -> Tuple[str, List[str]]:
    rep = node.get("representative", {})
    focus = get_focus(rep)
    ocr_text = clean_text(rep.get("ocr_text"), 400)
    title = focus_title(focus)
    item = focus_item(focus)
    reasons: List[str] = []
    score = 100
    if not focus.get("found"):
        score -= 35
        reasons.append("no focus")
    if safe_float(focus.get("confidence"), 0) < 0.45 and focus.get("found"):
        score -= 25
        reasons.append("low focus confidence")
    if not title:
        score -= 20
        reasons.append("missing page/menu title")
    if not item:
        score -= 10
        reasons.append("weak focused item")
    if len(ocr_text) < 8:
        score -= 15
        reasons.append("little OCR text")
    soup_hits = len(OCR_SOUP.findall(ocr_text[:800]))
    if soup_hits > 18:
        score -= 10
        reasons.append("OCR noise")
    if score >= 75:
        return "good", reasons
    if score >= 45:
        return "questionable", reasons
    return "bad", reasons


@dataclass
class DashboardDataset:
    crawler_dir: Path
    graph: Dict[str, Any]
    brain: Dict[str, Any]
    sequences: Dict[str, Any]
    unreachable: Dict[str, Any]

    @classmethod
    def load(cls, crawler_dir: Path) -> "DashboardDataset":
        crawler_dir = Path(crawler_dir)
        return cls(
            crawler_dir=crawler_dir,
            graph=read_json(crawler_dir / "nav_graph.json", {}),
            brain=read_json(crawler_dir / "crawler_brain.json", {}),
            sequences=read_json(crawler_dir / "learned_sequences.json", {}),
            unreachable=read_json(crawler_dir / "unreachable_states.json", {}),
        )

    @property
    def nodes(self) -> Dict[str, Dict[str, Any]]:
        return self.graph.get("nodes", {}) if isinstance(self.graph.get("nodes", {}), dict) else {}

    @property
    def edges(self) -> Dict[str, Dict[str, Any]]:
        return self.graph.get("edges", {}) if isinstance(self.graph.get("edges", {}), dict) else {}

    @property
    def action_rewards(self) -> Dict[str, Dict[str, Any]]:
        return self.brain.get("action_rewards", {}) if isinstance(self.brain.get("action_rewards", {}), dict) else {}

    @property
    def action_timing(self) -> Dict[str, Dict[str, Any]]:
        return self.brain.get("action_timing", {}) if isinstance(self.brain.get("action_timing", {}), dict) else {}

    @property
    def state_actions(self) -> Dict[str, Dict[str, Any]]:
        return self.brain.get("state_actions", {}) if isinstance(self.brain.get("state_actions", {}), dict) else {}

    def node_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for sid, node in self.nodes.items():
            rep = node.get("representative", {})
            focus = get_focus(rep)
            ui = ui_context(focus)
            human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
            quality, reasons = classify_quality(node)
            text = clean_text(rep.get("ocr_text"), 500)
            risk = bool(RISK_WORDS.search(text) or RISK_WORDS.search(json.dumps(focus)[:1500]) or human.get("risk_flags"))
            rows.append({
                "state_id": sid,
                "label": node_label(node),
                "first_seen": node.get("first_seen") or rep.get("timestamp"),
                "last_seen": node.get("last_seen") or rep.get("timestamp"),
                "first_bucket": iso_bucket(node.get("first_seen") or rep.get("timestamp")),
                "observation_count": int(node.get("observation_count", 0) or 0),
                "page_name": clean_text(focus.get("page_name") or ui.get("page_name"), 100),
                "block_title": clean_text(focus.get("block_title") or ui.get("block_title"), 100),
                "screen_title": clean_text(focus.get("screen_title") or ui.get("screen_title"), 100),
                "focused_item": focus_item(focus),
                "focused_value": clean_text(focus.get("focused_value") or ui.get("focused_value"), 100),
                "focus_found": bool(focus.get("found")),
                "focus_confidence": round(safe_float(focus.get("confidence"), 0), 4),
                "context_confidence": round(safe_float(focus.get("context_confidence") or ui.get("context_confidence"), 0), 4),
                "quality": quality,
                "quality_reasons": ", ".join(reasons),
                "risk_flag": risk,
                "human_screen_kind": human.get("screen_kind") or "",
                "human_confidence": round(safe_float(human.get("confidence"), 0), 4) if human else 0.0,
                "human_feature_tags": ", ".join(human.get("feature_tags", [])[:12]) if human else "",
                "human_test_goals": ", ".join(g.get("goal", "") for g in human.get("test_goals", [])[:6]) if human else "",
                "human_annoyance_flags": ", ".join(human.get("annoyance_flags", [])[:12]) if human else "",
                "ui_pattern": rep.get("ui_pattern") or "unknown",
                "pattern_confidence": round(safe_float(rep.get("pattern_confidence"), 0), 4),
                "brightness": safe_float(rep.get("brightness"), 0),
                "variance": safe_float(rep.get("variance"), 0),
                "entropy": safe_float(rep.get("entropy"), 0),
                "edge_density": safe_float(rep.get("edge_density"), 0),
                "ocr_token_count": len(rep.get("ocr_tokens") or []),
                "screenshot": rep.get("screenshot") or "",
            })
        return rows

    def edge_rows(self) -> List[Dict[str, Any]]:
        labels = {sid: node_label(n) for sid, n in self.nodes.items()}
        rows = []
        for eid, edge in self.edges.items():
            attempts = int(edge.get("attempts", 0) or 0)
            successes = int(edge.get("successes", 0) or 0)
            rows.append({
                "edge_id": eid,
                "from_state": edge.get("from_state", ""),
                "from_label": labels.get(edge.get("from_state", ""), edge.get("from_state", "")),
                "action": edge.get("action", ""),
                "to_state": edge.get("to_state", ""),
                "to_label": labels.get(edge.get("to_state", ""), edge.get("to_state", "")),
                "attempts": attempts,
                "successes": successes,
                "failures": int(edge.get("failures", 0) or 0),
                "noops": int(edge.get("noops", 0) or 0),
                "success_rate": round(successes / attempts, 4) if attempts else 0,
                "confidence": round(safe_float(edge.get("confidence"), 0), 4),
                "last_seen": edge.get("last_seen", ""),
                "last_bucket": iso_bucket(edge.get("last_seen")),
                "sample_count": len(edge.get("samples") or []),
                "transition_type": "self_loop" if edge.get("from_state") == edge.get("to_state") else "transition",
            })
        return rows

    def action_rows(self) -> List[Dict[str, Any]]:
        actions = sorted(set(self.action_rewards.keys()) | set(self.action_timing.keys()))
        rows = []
        for action in actions:
            r = self.action_rewards.get(action, {})
            t = self.action_timing.get(action, {})
            rows.append({
                "action": action,
                "reward_attempts": int(r.get("attempts", 0) or 0),
                "total_reward": safe_float(r.get("total_reward"), 0),
                "avg_reward": round(safe_float(r.get("avg_reward"), 0), 4),
                "timing_attempts": int(t.get("attempts", 0) or 0),
                # Legacy response fields now represent first visible action start.
                "avg_response_s": round(safe_float(t.get("avg_response_s"), 0), 4),
                "last_response_s": round(safe_float(t.get("last_response_s"), 0), 4),
                "min_response_s": round(safe_float(t.get("min_response_s"), 0), 4),
                "max_response_s": round(safe_float(t.get("max_response_s"), 0), 4),
                "avg_start_s": round(safe_float(t.get("avg_start_s", t.get("avg_response_s")), 0), 4),
                "last_start_s": round(safe_float(t.get("last_start_s", t.get("last_response_s")), 0), 4),
                "avg_complete_s": round(safe_float(t.get("avg_complete_s"), 0), 4),
                "last_complete_s": round(safe_float(t.get("last_complete_s"), 0), 4),
                "max_complete_s": round(safe_float(t.get("max_complete_s"), 0), 4),
                "avg_stable_s": round(safe_float(t.get("avg_stable_s"), 0), 4),
                "remarkable_count": int(t.get("remarkable_count", 0) or 0),
                "last_flags": ",".join(t.get("last_flags", []) if isinstance(t.get("last_flags", []), list) else []),
            })
        return rows

    def coverage_rows(self, actions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        actions = actions or DEFAULT_ACTIONS
        rows = []
        for sid, node in self.nodes.items():
            label = node_label(node)
            for action in actions:
                stat = self.state_actions.get(f"{sid}|{action}", {})
                rows.append({
                    "state_id": sid,
                    "label": label,
                    "action": action,
                    "attempts": int(stat.get("attempts", 0) or 0),
                    "successes": int(stat.get("successes", 0) or 0),
                    "discoveries": int(stat.get("discoveries", 0) or 0),
                    "avg_reward": round(safe_float(stat.get("avg_reward"), 0), 4),
                    "last_to_state": stat.get("last_to_state", ""),
                    "last_seen": stat.get("last_seen", ""),
                    "coverage_state": "tried" if int(stat.get("attempts", 0) or 0) else "untested",
                })
        return rows

    def timeline_rows(self) -> List[Dict[str, Any]]:
        buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: {"new_states": 0, "edge_seen": 0, "observations": 0})
        for row in self.node_rows():
            b = row["first_bucket"]
            buckets[b]["new_states"] += 1
            buckets[b]["observations"] += row["observation_count"]
        for row in self.edge_rows():
            b = row["last_bucket"]
            buckets[b]["edge_seen"] += 1
        out = []
        for b in sorted(buckets):
            if b == "unknown":
                continue
            item = {"bucket": b}
            item.update(buckets[b])
            out.append(item)
        return out

    def known_unknown_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for r in self.coverage_rows():
            if r["coverage_state"] == "untested":
                rows.append({**r, "unknown_type": "untested_state_action", "priority": 0.4 + (0.2 if IMPORTANT_WORDS.search(r["label"]) else 0.0)})
        for row in self.node_rows():
            if row["quality"] != "good":
                rows.append({
                    "state_id": row["state_id"],
                    "label": row["label"],
                    "action": "reprocess_context",
                    "attempts": 0,
                    "successes": 0,
                    "discoveries": 0,
                    "avg_reward": 0,
                    "last_to_state": "",
                    "last_seen": row["last_seen"],
                    "coverage_state": row["quality"],
                    "unknown_type": "questionable_perception",
                    "priority": 0.85 if row["quality"] == "bad" else 0.65,
                })
        unreach = self.unreachable.get("unreachable_states", {}) if isinstance(self.unreachable.get("unreachable_states", {}), dict) else {}
        for sid, u in unreach.items():
            rows.append({
                "state_id": sid,
                "label": clean_text((u.get("context") or {}).get("label") or sid, 160),
                "action": "retry_route",
                "attempts": int(u.get("attempts", 0) or 0),
                "successes": 0,
                "discoveries": 0,
                "avg_reward": 0,
                "last_to_state": "",
                "last_seen": u.get("last_attempt", ""),
                "coverage_state": "unreachable",
                "unknown_type": "route_recovery",
                "priority": safe_float(u.get("priority"), 0.8),
            })
        rows.sort(key=lambda r: (safe_float(r.get("priority"), 0), r.get("unknown_type", "")), reverse=True)
        return rows[:5000]

    def executive(self) -> Dict[str, Any]:
        nodes = self.node_rows()
        edges = self.edge_rows()
        actions = self.action_rows()
        coverage = self.coverage_rows()
        ku = self.known_unknown_rows()
        state_count = len(nodes)
        edge_count = len(edges)
        tried = sum(1 for r in coverage if r["attempts"] > 0)
        total_state_actions = len(coverage)
        good = sum(1 for r in nodes if r["quality"] == "good")
        risky = sum(1 for r in nodes if r["risk_flag"])
        avg_edge_conf = round(sum(r["confidence"] for r in edges) / max(1, edge_count), 4)
        avg_focus_conf = round(sum(r["focus_confidence"] for r in nodes if r["focus_found"]) / max(1, sum(1 for r in nodes if r["focus_found"])), 4)
        channels = self.brain.get("channels", {}) if isinstance(self.brain.get("channels", {}), dict) else {}
        sequences = self.sequences.get("learned_sequences", {}) if isinstance(self.sequences.get("learned_sequences", {}), dict) else {}
        maturity = round((0.35 * min(100, pct(tried, total_state_actions)) + 0.25 * pct(good, state_count) + 0.20 * min(100, edge_count / max(1, state_count) * 100) + 0.20 * min(100, len(channels) * 4)), 2)
        return {
            "generated_at": now_iso(),
            "schema": "stb_learning_exec_v1",
            "headline": {
                "learning_maturity_pct": maturity,
                "states": state_count,
                "transitions": edge_count,
                "coverage_pct": pct(tried, total_state_actions),
                "perception_quality_pct": pct(good, state_count),
                "avg_transition_confidence": avg_edge_conf,
                "avg_focus_confidence": avg_focus_conf,
                "known_channels": len(channels),
                "known_menu_titles": len(self.brain.get("known_menu_titles", []) or []),
                "known_focus_items": len(self.brain.get("known_focus_items", []) or []),
                "known_unknowns": len(ku),
                "risk_flagged_states": risky,
                "learned_sequences": len(sequences),
            },
            "timeline": self.timeline_rows(),
            "top_actions": sorted(actions, key=lambda r: (r["avg_reward"], r["reward_attempts"]), reverse=True)[:12],
            "top_known_menus": Counter([r["page_name"] or r["screen_title"] or r["block_title"] for r in nodes if r["page_name"] or r["screen_title"] or r["block_title"]]).most_common(20),
            "known_unknowns": ku[:30],
            "channels": sorted(({"channel": k, **v} for k, v in channels.items()), key=lambda r: int(r.get("channel", 0)))[:100],
            "narrative": self.exec_narrative(maturity, state_count, edge_count, len(ku), risky),
        }

    def exec_narrative(self, maturity: float, states: int, edges: int, unknowns: int, risks: int) -> List[str]:
        lines = []
        if states == 0:
            return ["No crawler learning data has been collected yet."]
        lines.append(f"The agent has mapped {states} distinct UI states and {edges} observed transitions.")
        if maturity >= 70:
            lines.append("Learning maturity is strong; the system is ready for targeted workflow validation and regression-style reruns.")
        elif maturity >= 35:
            lines.append("Learning maturity is improving; the next value is filling state/action gaps and stabilizing perception quality.")
        else:
            lines.append("Learning maturity is early; prioritize teacher-mode demonstrations and focused exploration around settings/guide/DVR flows.")
        if unknowns:
            lines.append(f"There are {unknowns} known-unknown items: untested actions, questionable OCR/focus captures, or retry-worthy routes.")
        if risks:
            lines.append(f"{risks} states are risk-flagged because they mention PIN, parental, purchase, reset, or similar guarded flows.")
        return lines

    def engineering(self) -> Dict[str, Any]:
        nodes = self.node_rows()
        edges = self.edge_rows()
        actions = self.action_rows()
        coverage = self.coverage_rows()
        qualities = Counter(r["quality"] for r in nodes)
        patterns = Counter(r["ui_pattern"] for r in nodes)
        human_kinds = Counter(r.get("human_screen_kind") or "unknown" for r in nodes)
        per_action_coverage = defaultdict(lambda: {"tried": 0, "total": 0})
        for r in coverage:
            per_action_coverage[r["action"]]["total"] += 1
            if r["attempts"]:
                per_action_coverage[r["action"]]["tried"] += 1
        return {
            "generated_at": now_iso(),
            "schema": "stb_learning_eng_v1",
            "headline": self.executive()["headline"],
            "quality_breakdown": [{"quality": k, "count": v} for k, v in qualities.items()],
            "pattern_breakdown": [{"pattern": k, "count": v} for k, v in patterns.items()],
            "per_action_coverage": [{"action": a, "tried": v["tried"], "total": v["total"], "coverage_pct": pct(v["tried"], v["total"])} for a, v in sorted(per_action_coverage.items())],
            "actions": actions,
            "slow_actions": sorted(actions, key=lambda r: r.get("avg_complete_s") or r.get("avg_response_s") or 0, reverse=True)[:20],
            "remarkable_timing_actions": [a for a in sorted(actions, key=lambda r: r.get("remarkable_count", 0), reverse=True) if a.get("remarkable_count", 0) > 0][:40],
            "edges_low_confidence": [e for e in sorted(edges, key=lambda r: r["confidence"]) if e["confidence"] < 0.45][:80],
            "state_quality": sorted(nodes, key=lambda r: ({"bad": 0, "questionable": 1, "good": 2}.get(r["quality"], 3), -r["observation_count"]))[:200],
            "known_unknowns": self.known_unknown_rows()[:200],
            "timeline": self.timeline_rows(),
            "top_edges": sorted(edges, key=lambda r: (r["successes"], r["confidence"]), reverse=True)[:100],
            "state_table": nodes[:1000],
        }

    def superset_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "stb_learning_states": self.node_rows(),
            "stb_learning_edges": self.edge_rows(),
            "stb_learning_actions": self.action_rows(),
            "stb_learning_coverage": self.coverage_rows(),
            "stb_learning_known_unknowns": self.known_unknown_rows(),
            "stb_learning_timeline": self.timeline_rows(),
        }

    def export_zip_bytes(self) -> bytes:
        tables = self.superset_tables()
        manifest = self.superset_manifest()
        sql = self.superset_sql()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README_SUPERSET_DASHBOARDS.md", self.superset_readme())
            zf.writestr("superset_manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("superset_sql_views.sql", sql)
            zf.writestr("exec_dashboard_payload.json", json.dumps(self.executive(), indent=2))
            zf.writestr("eng_dashboard_payload.json", json.dumps(self.engineering(), indent=2))
            for name, rows in tables.items():
                zf.writestr(f"datasets/{name}.csv", rows_to_csv(rows))
        return buf.getvalue()

    def superset_manifest(self) -> Dict[str, Any]:
        return {
            "generated_at": now_iso(),
            "dashboards": [
                {
                    "name": "STB Autonomous Learning - Executive",
                    "slug": "stb-autonomous-learning-exec",
                    "audience": "leadership",
                    "datasets": ["stb_learning_timeline", "stb_learning_states", "stb_learning_edges", "stb_learning_known_unknowns"],
                    "recommended_charts": [
                        "Big Number: Learning Maturity %",
                        "Big Number: States / Transitions / Coverage",
                        "Line: new states over time",
                        "Bar: top learned menus",
                        "Table: highest-priority known unknowns",
                        "Table: channel catalog",
                    ],
                },
                {
                    "name": "STB Autonomous Learning - Engineering",
                    "slug": "stb-autonomous-learning-eng",
                    "audience": "engineering",
                    "datasets": list(self.superset_tables().keys()),
                    "recommended_charts": [
                        "Heatmap: state/action coverage",
                        "Table: low-confidence transitions",
                        "Bar: action start vs completion timing by action",
                        "Table: remarkable timing flags",
                        "Bar: reward by action",
                        "Table: questionable OCR/focus states",
                        "Line: exploration history",
                    ],
                },
            ],
        }

    def superset_sql(self) -> str:
        return """-- STB Autonomous Learning Superset helper views\n-- Load the exported CSVs into tables named exactly as below, then create these views.\n\nCREATE OR REPLACE VIEW v_stb_exec_learning_summary AS\nSELECT\n  COUNT(*) AS states,\n  SUM(CASE WHEN quality = 'good' THEN 1 ELSE 0 END) AS good_states,\n  SUM(CASE WHEN risk_flag THEN 1 ELSE 0 END) AS risk_states,\n  AVG(focus_confidence) AS avg_focus_confidence,\n  AVG(context_confidence) AS avg_context_confidence\nFROM stb_learning_states;\n\nCREATE OR REPLACE VIEW v_stb_eng_transition_quality AS\nSELECT\n  action,\n  COUNT(*) AS transitions,\n  SUM(attempts) AS attempts,\n  SUM(successes) AS successes,\n  AVG(confidence) AS avg_confidence,\n  AVG(success_rate) AS avg_success_rate\nFROM stb_learning_edges\nGROUP BY action;\n\nCREATE OR REPLACE VIEW v_stb_known_unknown_priority AS\nSELECT *\nFROM stb_learning_known_unknowns\nORDER BY priority DESC, unknown_type;\n\nCREATE OR REPLACE VIEW v_stb_state_action_coverage AS\nSELECT\n  action,\n  COUNT(*) AS total_state_actions,\n  SUM(CASE WHEN attempts > 0 THEN 1 ELSE 0 END) AS tried_state_actions,\n  100.0 * SUM(CASE WHEN attempts > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS coverage_pct\nFROM stb_learning_coverage\nGROUP BY action;\n"""

    def superset_readme(self) -> str:
        return """# STB Autonomous Learning Dashboards\n\nThis export contains two Superset-oriented dashboard packages:\n\n1. **STB Autonomous Learning - Executive**\n   Leadership-ready summary of progress, confidence, coverage, risk, known channels, and remaining known-unknowns.\n\n2. **STB Autonomous Learning - Engineering**\n   Debug-oriented dashboard for state/action coverage, OCR/focus quality, timing, rewards, low-confidence edges, unreachable routes, and training history.\n\n## Import pattern\n\nLoad each CSV in `datasets/` into Superset as a dataset/table with the same base name.\nThen run `superset_sql_views.sql` if you want convenience views for summary charts.\n\nThe live app also serves built-in dashboard pages:\n\n- `/dashboards`\n- `/dashboard/exec`\n- `/dashboard/eng`\n- `/api/dashboards/exec`\n- `/api/dashboards/eng`\n- `/api/dashboards/superset.zip`\n"""


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    keys: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        clean = {}
        for k in keys:
            v = row.get(k, "")
            if isinstance(v, (list, dict)):
                clean[k] = json.dumps(v, ensure_ascii=False)
            else:
                clean[k] = v
        writer.writerow(clean)
    return buf.getvalue()


def build_dashboard_payload(crawler_dir: Path) -> Dict[str, Any]:
    ds = DashboardDataset.load(crawler_dir)
    return {"generated_at": now_iso(), "exec": ds.executive(), "eng": ds.engineering()}
