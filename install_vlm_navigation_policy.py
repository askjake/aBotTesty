#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


PATCH_MARKER = "v38.7-vlm-navigation-policy-20260602"


def backup(path: Path, tag: str) -> Path:
    b = path.with_suffix(path.suffix + f".bak-{tag}-" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    b.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return b


def patch_auto_crawler(path: Path) -> dict:
    if not path.exists():
        return {"ok": False, "changed": False, "error": f"missing {path}"}
    text = path.read_text(encoding="utf-8")
    orig = text
    notes = []

    hook_line = "actions = self.apply_vlm_policy_order(state_id, actions)"
    pattern_line = "actions = self.apply_pattern_action_order(state_id, actions)"
    if hook_line not in text:
        if pattern_line not in text:
            return {"ok": False, "changed": False, "error": f"could not find action-order line in {path}"}
        text = text.replace(pattern_line, pattern_line + "\n                " + hook_line, 1)
        notes.append("inserted crawler action-order hook")

    if "def apply_vlm_policy_order(self, state_id" not in text:
        method = """
    def apply_vlm_policy_order(self, state_id: str, actions: List[str]) -> List[str]:
        # Guarded VLM policy callback hook. shadow logs only; assist reorders;
        # autonomous narrows action list to the accepted VLM action.
        cfg = self.config
        mode = str(getattr(cfg, "vlm_policy_mode", "shadow") or "shadow").lower()
        enabled = bool(getattr(cfg, "vlm_policy_enabled", False)) and mode != "off"
        if not enabled or not actions:
            return actions

        every = max(1, int(getattr(cfg, "vlm_policy_every_n_steps", 1) or 1))
        if getattr(self, "_steps", 0) % every != 0:
            return actions

        stats = getattr(self, "_vlm_policy_stats", None)
        if not isinstance(stats, dict):
            stats = {"calls": 0, "accepted": 0, "rejected": 0, "errors": 0, "shadow": 0, "assist": 0, "autonomous": 0}
            setattr(self, "_vlm_policy_stats", stats)

        cb = getattr(self, "vlm_policy_callback", None)
        if not callable(cb):
            stats["rejected"] = int(stats.get("rejected") or 0) + 1
            stats["last_decision"] = {"accepted": False, "reason": "no_vlm_policy_callback"}
            return actions

        node = self.graph.nodes.get(state_id)
        focus = node.representative.focus if node and isinstance(getattr(node.representative, "focus", {}), dict) else {}
        human = focus.get("human_cues") if isinstance(focus, dict) and isinstance(focus.get("human_cues"), dict) else {}

        context = {
            "state_id": state_id,
            "label": getattr(node, "label", state_id) if node else state_id,
            "ocr_text": getattr(node.representative, "ocr_text", "") if node else "",
            "focus": focus,
            "screen_kind": human.get("screen_kind") if isinstance(human, dict) else "",
            "allowed_actions": list(actions),
            "goal": getattr(cfg, "vlm_policy_goal", ""),
            "mode": mode,
            "min_confidence": float(getattr(cfg, "vlm_policy_min_confidence", 0.70)),
            "max_risk": float(getattr(cfg, "vlm_policy_max_risk", 0.25)),
            "allow_select": bool(getattr(cfg, "vlm_policy_allow_select", False)),
            "step": getattr(self, "_steps", 0),
        }

        try:
            decision = cb(context) or {}
            stats["calls"] = int(stats.get("calls") or 0) + 1
            stats["last_decision"] = decision
            accepted = bool(decision.get("accepted"))
            suggested = str(decision.get("suggested_action") or "").strip().lower()

            if accepted and suggested in actions:
                stats["accepted"] = int(stats.get("accepted") or 0) + 1
                if mode == "shadow":
                    stats["shadow"] = int(stats.get("shadow") or 0) + 1
                    self.event("info", "vlm policy shadow suggestion", state=state_id, suggested=suggested, confidence=decision.get("confidence"), risk=decision.get("risk"), reason=decision.get("reason"))
                    return actions
                if mode == "assist":
                    stats["assist"] = int(stats.get("assist") or 0) + 1
                    self.event("info", "vlm policy reordered action list", state=state_id, suggested=suggested, confidence=decision.get("confidence"), risk=decision.get("risk"))
                    return [suggested] + [a for a in actions if a != suggested]
                if mode == "autonomous":
                    stats["autonomous"] = int(stats.get("autonomous") or 0) + 1
                    self.event("warning", "vlm policy autonomous action selected", state=state_id, suggested=suggested, confidence=decision.get("confidence"), risk=decision.get("risk"))
                    return [suggested]

            stats["rejected"] = int(stats.get("rejected") or 0) + 1
            try:
                self.event("info", "vlm policy rejected/fallback", state=state_id, suggested=suggested, reason=decision.get("reason"), confidence=decision.get("confidence"), risk=decision.get("risk"))
            except Exception:
                pass
            return actions
        except Exception as exc:
            stats["errors"] = int(stats.get("errors") or 0) + 1
            stats["last_decision"] = {"accepted": False, "error": str(exc)}
            try:
                self.event("warning", "vlm policy call failed; using heuristic actions", state=state_id, error=str(exc))
            except Exception:
                pass
            return actions

    def vlm_policy_summary(self) -> Dict[str, Any]:
        stats = getattr(self, "_vlm_policy_stats", {})
        return {
            "config": {
                "enabled": bool(getattr(self.config, "vlm_policy_enabled", False)),
                "mode": str(getattr(self.config, "vlm_policy_mode", "shadow")),
                "min_confidence": float(getattr(self.config, "vlm_policy_min_confidence", 0.70)),
                "max_risk": float(getattr(self.config, "vlm_policy_max_risk", 0.25)),
                "allow_select": bool(getattr(self.config, "vlm_policy_allow_select", False)),
                "every_n_steps": int(getattr(self.config, "vlm_policy_every_n_steps", 1) or 1),
                "goal": str(getattr(self.config, "vlm_policy_goal", "")),
            },
            "stats": dict(stats) if isinstance(stats, dict) else {},
        }

"""
        anchor = "\n    def build_frontier(self)"
        if anchor not in text:
            return {"ok": False, "changed": False, "error": "could not find build_frontier insertion anchor"}
        text = text.replace(anchor, method + anchor, 1)
        notes.append("inserted crawler VLM policy methods")

    if text != orig:
        b = backup(path, "vlm-policy")
        path.write_text(text, encoding="utf-8")
        return {"ok": True, "changed": True, "backup": str(b), "notes": notes}
    return {"ok": True, "changed": False, "notes": ["auto_crawler already had VLM policy integration"]}


def patch_merged_app(path: Path) -> dict:
    if not path.exists():
        return {"ok": False, "changed": False, "error": f"missing {path}"}
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        return {"ok": True, "changed": False, "notes": ["merged_app already patched"]}

    block = """
# ---- aBotTesty VLM navigation policy integration: v38.7-vlm-navigation-policy-20260602 ----
VLM_NAV_POLICY_PATCH_VERSION = "v38.7-vlm-navigation-policy-20260602"

def _vlm_nav_policy_file() -> Path:
    return CRAWLER_DIR / "vlm_navigation_policy.json"


def _vlm_nav_default_policy() -> Dict[str, Any]:
    return {
        "enabled": True,
        "mode": "assist",
        "goal": "Explore the TV UI safely. Prefer actions that reveal new screens or useful information. Do not purchase, rent, subscribe, delete, reset, or confirm anything.",
        "min_confidence": 0.70,
        "max_risk": 0.25,
        "allow_select": False,
        "every_n_steps": 2,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "patch_version": VLM_NAV_POLICY_PATCH_VERSION,
    }


def _vlm_load_nav_policy() -> Dict[str, Any]:
    rec = _vlm_nav_default_policy()
    p = _vlm_nav_policy_file()
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                rec.update(loaded)
        except Exception:
            log.exception("failed reading VLM navigation policy config")
    return rec


def _vlm_save_nav_policy(rec: Dict[str, Any]) -> Dict[str, Any]:
    rec = dict(rec)
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    rec["patch_version"] = VLM_NAV_POLICY_PATCH_VERSION
    _vlm_nav_policy_file().parent.mkdir(parents=True, exist_ok=True)
    _vlm_nav_policy_file().write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    return rec


def _vlm_json_from_shadow_result(result: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize _vlm_call_shadow() output into the model JSON payload.
    if not isinstance(result, dict):
        return {}
    stdout = result.get("stdout")
    if isinstance(stdout, dict):
        if isinstance(stdout.get("json"), dict):
            return stdout["json"]
        text = stdout.get("text")
        if isinstance(text, str) and text.strip():
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return stdout
    if isinstance(stdout, str) and stdout.strip():
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                if isinstance(parsed.get("json"), dict):
                    return parsed["json"]
                return parsed
        except Exception:
            pass
    return {}


def _vlm_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _vlm_risk_ok(value: Any, max_risk: float) -> tuple[bool, str, float]:
    raw = str(value if value is not None else "unknown").strip().lower()
    if raw in {"safe", "low", "low_risk", "ok"}:
        return True, raw, 0.0
    if raw in {"medium", "moderate"}:
        return max_risk >= 0.5, raw, 0.5
    if raw in {"high", "unsafe", "danger", "dangerous", "blocked"}:
        return False, raw, 1.0
    try:
        numeric = float(raw)
        return numeric <= max_risk, raw, numeric
    except Exception:
        return False, raw or "unknown", 1.0


def _vlm_first_suggested_action(payload: Dict[str, Any]) -> str:
    candidates: List[Any] = []
    seq = payload.get("action_sequence")
    if isinstance(seq, list):
        candidates.extend(seq)
    elif isinstance(seq, str):
        candidates.extend([x.strip() for x in seq.split(",") if x.strip()])
    for key in ("suggested_action", "action", "next_action", "button"):
        if payload.get(key):
            candidates.append(payload.get(key))
    for item in candidates:
        try:
            return normalize_button(str(item))
        except Exception:
            return str(item).strip().lower()
    return ""


def _vlm_expected_result_is_noisy(payload: Dict[str, Any]) -> bool:
    text = " ".join(str(payload.get(k) or "") for k in ("expected_result", "focused_element", "screen_type"))
    lower = text.lower()
    noisy_tokens = ("screen_", "teach_burst_", "after_complete_", "before_", "after_", "unknown")
    return any(tok in lower for tok in noisy_tokens)


def _vlm_decide_navigation(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    nav_cfg = _vlm_load_nav_policy()
    allowed = [str(a).strip().lower() for a in (context.get("allowed_actions") or []) if str(a).strip()]
    allowed_set = set(allowed)
    suggested = _vlm_first_suggested_action(payload)
    confidence = _vlm_float(payload.get("confidence"), 0.0)
    min_conf = _vlm_float(context.get("min_confidence"), _vlm_float(nav_cfg.get("min_confidence"), 0.70))
    max_risk = _vlm_float(context.get("max_risk"), _vlm_float(nav_cfg.get("max_risk"), 0.25))
    allow_select = bool(context.get("allow_select", nav_cfg.get("allow_select", False)))
    risk_ok, risk_label, risk_score = _vlm_risk_ok(payload.get("risk", "unknown"), max_risk=max_risk)
    noisy = _vlm_expected_result_is_noisy(payload)

    reason = "accepted"
    accepted = True
    if not suggested:
        accepted, reason = False, "no_action_suggested"
    elif suggested not in allowed_set:
        accepted, reason = False, f"suggested_action_not_allowed:{suggested}"
    elif suggested == "select" and not allow_select:
        accepted, reason = False, "select_blocked_by_policy"
    elif not risk_ok:
        accepted, reason = False, f"risk_blocked:{risk_label}"
    elif confidence < min_conf:
        accepted, reason = False, f"confidence_below_gate:{confidence:.3f}<{min_conf:.3f}"

    return {
        "accepted": bool(accepted),
        "suggested_action": suggested,
        "confidence": confidence,
        "risk": risk_label,
        "risk_score": risk_score,
        "reason": reason,
        "payload": payload,
        "quality_flags": {"noisy_expected_result": bool(noisy)},
        "allowed_actions": allowed,
        "mode": str(nav_cfg.get("mode") or "assist"),
    }


def _vlm_log_navigation_decision(decision: Dict[str, Any], raw_result: Dict[str, Any] | None = None, context: Dict[str, Any] | None = None) -> None:
    try:
        path = CRAWLER_DIR / "vlm_navigation_decisions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "decision": decision,
            "context": context or {},
            "raw_ok": (raw_result or {}).get("ok"),
            "raw_returncode": (raw_result or {}).get("returncode"),
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\\n")
    except Exception:
        log.exception("failed writing VLM navigation decision log")


def _vlm_policy_callback_for_crawler(context: Dict[str, Any]) -> Dict[str, Any]:
    nav_cfg = _vlm_load_nav_policy()
    allowed = [str(a).strip().lower() for a in (context.get("allowed_actions") or []) if str(a).strip()]
    goal = str(nav_cfg.get("goal") or context.get("goal") or "Explore safely.")
    prompt = (
        goal.strip()
        + "\\n\\nYou are advising a TV/set-top-box UI crawler. "
        + "Choose exactly one next remote-control button from this allowed list: "
        + ", ".join(allowed)
        + ". Return JSON only with keys: action_sequence, expected_result, risk, confidence. "
        + "Use risk='safe' only if the action will not purchase, rent, subscribe, delete, reset, or confirm anything. "
        + "When unsure, prefer navigation keys like up/down/left/right/back/guide/home over select."
    )
    raw = _vlm_call_shadow("policy", goal=prompt)
    payload = _vlm_json_from_shadow_result(raw)
    ctx = dict(context)
    ctx["min_confidence"] = float(getattr(crawler.config, "vlm_policy_min_confidence", nav_cfg.get("min_confidence", 0.70)))
    ctx["max_risk"] = float(getattr(crawler.config, "vlm_policy_max_risk", nav_cfg.get("max_risk", 0.25)))
    ctx["allow_select"] = bool(getattr(crawler.config, "vlm_policy_allow_select", nav_cfg.get("allow_select", False)))
    decision = _vlm_decide_navigation(payload, ctx)
    _vlm_log_navigation_decision(decision, raw_result=raw, context=ctx)
    return decision


def _install_vlm_navigation_policy() -> Dict[str, Any]:
    nav_cfg = _vlm_load_nav_policy()
    setattr(crawler.config, "vlm_policy_enabled", bool(nav_cfg.get("enabled", True)))
    setattr(crawler.config, "vlm_policy_mode", str(nav_cfg.get("mode") or "assist"))
    setattr(crawler.config, "vlm_policy_goal", str(nav_cfg.get("goal") or "Explore safely."))
    setattr(crawler.config, "vlm_policy_min_confidence", float(nav_cfg.get("min_confidence", 0.70)))
    setattr(crawler.config, "vlm_policy_max_risk", float(nav_cfg.get("max_risk", 0.25)))
    setattr(crawler.config, "vlm_policy_allow_select", bool(nav_cfg.get("allow_select", False)))
    setattr(crawler.config, "vlm_policy_every_n_steps", int(nav_cfg.get("every_n_steps", 2) or 2))
    setattr(crawler, "vlm_policy_callback", _vlm_policy_callback_for_crawler)
    if not isinstance(getattr(crawler, "_vlm_policy_stats", None), dict):
        setattr(crawler, "_vlm_policy_stats", {"calls": 0, "accepted": 0, "rejected": 0, "errors": 0, "shadow": 0, "assist": 0, "autonomous": 0})
    return {"ok": True, "policy": nav_cfg}


_install_vlm_navigation_policy()


@app.route("/api/vlm/navigation/config", methods=["GET", "POST"])
def api_vlm_navigation_config():
    if request.method == "GET":
        _install_vlm_navigation_policy()
        summary = crawler.vlm_policy_summary() if callable(getattr(crawler, "vlm_policy_summary", None)) else {"config": {}, "stats": getattr(crawler, "_vlm_policy_stats", {})}
        return jsonify(ok=True, patch_version=VLM_NAV_POLICY_PATCH_VERSION, policy=_vlm_load_nav_policy(), crawler=summary)

    data = request.get_json(silent=True) or {}
    current = _vlm_load_nav_policy()
    if "enabled" in data:
        current["enabled"] = bool(data.get("enabled"))
    if "mode" in data:
        mode = str(data.get("mode") or "assist").strip().lower()
        allowed_modes = {"off", "shadow", "assist", "autonomous"}
        if mode not in allowed_modes:
            return jsonify(ok=False, error=f"unsupported mode {mode}", allowed=sorted(allowed_modes)), 400
        current["mode"] = mode
    if "goal" in data:
        current["goal"] = str(data.get("goal") or "")
    if "min_confidence" in data:
        current["min_confidence"] = max(0.0, min(1.0, float(data.get("min_confidence"))))
    if "max_risk" in data:
        current["max_risk"] = max(0.0, min(1.0, float(data.get("max_risk"))))
    if "allow_select" in data:
        current["allow_select"] = bool(data.get("allow_select"))
    if "every_n_steps" in data:
        current["every_n_steps"] = max(1, int(data.get("every_n_steps") or 1))
    saved = _vlm_save_nav_policy(current)
    installed = _install_vlm_navigation_policy()
    return jsonify(ok=True, saved=saved, installed=installed)


@app.route("/api/vlm/navigation/status", methods=["GET"])
def api_vlm_navigation_status():
    _install_vlm_navigation_policy()
    summary = crawler.vlm_policy_summary() if callable(getattr(crawler, "vlm_policy_summary", None)) else {"config": {}, "stats": getattr(crawler, "_vlm_policy_stats", {})}
    return jsonify(ok=True, patch_version=VLM_NAV_POLICY_PATCH_VERSION, policy=_vlm_load_nav_policy(), crawler=summary)


@app.route("/api/vlm/navigation/recommend", methods=["POST", "GET"])
def api_vlm_navigation_recommend():
    data = request.get_json(silent=True) or {}
    _install_vlm_navigation_policy()
    allowed = data.get("allowed_actions") or list(CFG.get("crawler_enabled_keys", [])) or ["up", "down", "left", "right", "back", "guide", "home", "info", "options", "select"]
    context = {
        "state_id": str(data.get("state_id") or "current"),
        "allowed_actions": allowed,
        "goal": str(data.get("goal") or _vlm_load_nav_policy().get("goal") or ""),
        "mode": str(data.get("mode") or getattr(crawler.config, "vlm_policy_mode", "assist")),
        "min_confidence": float(data.get("min_confidence") or getattr(crawler.config, "vlm_policy_min_confidence", 0.70)),
        "max_risk": float(data.get("max_risk") or getattr(crawler.config, "vlm_policy_max_risk", 0.25)),
        "allow_select": bool(data.get("allow_select", getattr(crawler.config, "vlm_policy_allow_select", False))),
        "step": int(getattr(crawler, "_steps", 0) or 0),
    }
    decision = _vlm_policy_callback_for_crawler(context)
    return jsonify(ok=True, decision=decision)


@app.route("/api/vlm/navigation/execute_next", methods=["POST"])
def api_vlm_navigation_execute_next():
    data = request.get_json(silent=True) or {}
    _install_vlm_navigation_policy()
    allowed = data.get("allowed_actions") or list(CFG.get("crawler_enabled_keys", [])) or ["up", "down", "left", "right", "back", "guide", "home", "info", "options"]
    context = {
        "state_id": str(data.get("state_id") or "manual_current"),
        "allowed_actions": allowed,
        "goal": str(data.get("goal") or _vlm_load_nav_policy().get("goal") or ""),
        "mode": str(data.get("mode") or "manual_execute"),
        "min_confidence": float(data.get("min_confidence") or max(0.75, float(getattr(crawler.config, "vlm_policy_min_confidence", 0.70)))),
        "max_risk": float(data.get("max_risk") or getattr(crawler.config, "vlm_policy_max_risk", 0.25)),
        "allow_select": bool(data.get("allow_select", False)),
        "step": int(getattr(crawler, "_steps", 0) or 0),
    }
    decision = _vlm_policy_callback_for_crawler(context)
    execute = bool(data.get("execute", False))
    result = None
    if execute and decision.get("accepted"):
        action = str(decision.get("suggested_action") or "")
        result = _record_or_send_operator_key(
            action,
            delay_ms=int(data.get("delay_ms") or CFG.get("default_delay_ms", 120)),
            gap_s=float(data.get("gap_s") or CFG.get("monitor_auto_learning_gap_s", 0.075)),
            learn_mode="vlm_manual_execute",
            note="VLM navigation execute_next accepted action",
        )
    return jsonify(ok=True, executed=bool(result), decision=decision, send=result)

# ---- end aBotTesty VLM navigation policy integration ----
"""

    idx = -1
    for anchor in ['if __name__ == "__main__":', "if __name__ == '__main__':"]:
        idx = text.find(anchor)
        if idx != -1:
            break
    if idx == -1:
        return {"ok": False, "changed": False, "error": "could not find __main__ guard in merged_app.py"}
    b = backup(path, "vlm-nav-policy")
    text = text[:idx].rstrip() + "\n\n" + block + "\n\n" + text[idx:]
    path.write_text(text, encoding="utf-8")
    return {"ok": True, "changed": True, "backup": str(b), "notes": ["inserted merged_app VLM navigation policy endpoints"]}


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    merged = root / "merged_app.py"
    auto = root / "auto_crawler.py"

    results = {
        "root": str(root),
        "auto_crawler": patch_auto_crawler(auto),
        "merged_app": patch_merged_app(merged),
    }

    ok = bool(results["auto_crawler"].get("ok")) and bool(results["merged_app"].get("ok"))
    print(json.dumps(results, indent=2, default=str))
    if not ok:
        return 1

    merged_text = merged.read_text(encoding="utf-8")
    auto_text = auto.read_text(encoding="utf-8")
    checks = {
        "merged_patch_marker": PATCH_MARKER in merged_text,
        "nav_config_route": "/api/vlm/navigation/config" in merged_text,
        "nav_recommend_route": "/api/vlm/navigation/recommend" in merged_text,
        "nav_execute_route": "/api/vlm/navigation/execute_next" in merged_text,
        "auto_hook": "actions = self.apply_vlm_policy_order(state_id, actions)" in auto_text,
        "auto_method": "def apply_vlm_policy_order" in auto_text,
    }
    for k, v in checks.items():
        print(f"check {k}: {'OK' if v else 'MISSING'}")
    if not all(checks.values()):
        return 2
    print("Next: python3 -m py_compile merged_app.py auto_crawler.py vlm_shadow_client.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

