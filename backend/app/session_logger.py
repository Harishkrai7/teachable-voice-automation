"""Structured session logger for PRISM teach/replay debugging.

Writes one JSONL line per event to SESSION_LOG_DIR/sessions.jsonl (default /tmp/prism_logs).
Also exposed at GET /v1/logs so you can pull them without SSH.

Format per line:
  { "ts", "type": TEACH|REPLAY|RECOVERY|STEP, "requestId", ... }
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

_lock = Lock()
_log_dir = Path(os.getenv("SESSION_LOG_DIR", "/tmp/prism_logs"))
log = logging.getLogger(__name__)

# ── internal writer ──────────────────────────────────────────────────────────

def _write(record: dict) -> None:
    try:
        _log_dir.mkdir(parents=True, exist_ok=True)
        path = _log_dir / "sessions.jsonl"
        line = json.dumps(record, default=str)
        with _lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        # Also emit as a structured INFO line so Cloud Run / logcat captures it
        log.info("SESSION_LOG %s", line)
    except Exception as e:
        log.warning("session_logger write failed: %s", e)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── step formatter ───────────────────────────────────────────────────────────

def _fmt_step(s: Any) -> dict:
    """Turn a Step pydantic model into a compact, human-readable dict."""
    d = s.model_dump(by_alias=True) if hasattr(s, "model_dump") else dict(s)
    # Compact target → just the useful fields
    t = d.pop("target", None)
    if t:
        d["target"] = {
            k: t[k] for k in
            ("text", "contentDescription", "resourceId", "parentText", "clickable", "editable")
            if t.get(k) is not None
        }
    # Show template vs resolved value clearly
    tv = d.get("taughtValue")
    v  = d.get("value")
    if tv and v and tv != v:
        d["value_template"] = v        # e.g. "{{item}}"
        d["value_resolved"] = "n/a (teach step)"
    # Remove clutter
    for k in ("slotRefs", "taughtValue", "taughtTargetText", "targetIsSlotResolved"):
        d.pop(k, None)
    return d


def _fmt_resolved_step(s: Any) -> dict:
    """Format a resolved (replay) step — shows both template origin and final value."""
    d = s.model_dump(by_alias=True) if hasattr(s, "model_dump") else dict(s)
    t = d.pop("target", None)
    if t:
        d["target"] = {
            k: t[k] for k in
            ("text", "contentDescription", "resourceId", "parentText",
             "clickable", "editable", "taughtTargetText", "targetIsSlotResolved")
            if t.get(k) is not None
        }
    refs = d.get("slotRefs", [])
    if refs:
        d["usesSlots"] = refs
    for k in ("slotRefs", "taughtValue", "taughtTargetText", "targetIsSlotResolved"):
        d.pop(k, None)
    return d


# ── public logging functions ─────────────────────────────────────────────────

def log_teach(
    *,
    request_id: str,
    utterance: str,
    intent: str,
    app: str | None,
    slots: dict[str, Any],
    steps: list,
    warnings: list[str],
    actions_recorded: int,
    actions_dropped: int,
    flow_id: str | None,
    status: str,
) -> None:
    """Log a completed /v1/teach call."""
    _write({
        "ts": _ts(),
        "type": "TEACH",
        "requestId": request_id,
        "status": status,                      # LEARNED | REJECTED
        "utterance": utterance,
        "intent": intent,
        "app": app,
        "slots": slots,
        "flowId": flow_id,
        "actionsRecorded": actions_recorded,
        "actionsDropped": actions_dropped,
        "steps": [_fmt_step(s) for s in steps],
        "stepCount": len(steps),
        "warnings": warnings,
    })


def log_replay(
    *,
    request_id: str,
    utterance: str,
    intent: str,
    app: str | None,
    matched_flow_id: str | None,
    slots_extracted: dict[str, Any],
    slots_resolved: dict[str, Any],
    defaulted_slots: list[str],
    changed_slots: list[str],
    steps: list,
    status: str,
    message: str | None,
) -> None:
    """Log a completed /v1/replay call."""
    _write({
        "ts": _ts(),
        "type": "REPLAY",
        "requestId": request_id,
        "status": status,                      # PLAN | ASK_USER | NOT_LEARNED | STOP
        "utterance": utterance,
        "intent": intent,
        "app": app,
        "matchedFlowId": matched_flow_id,
        "slotsExtracted": slots_extracted,
        "slotsResolved": slots_resolved,
        "defaultedSlots": defaulted_slots,     # slots filled from the taught default, not the utterance
        "changedSlots": changed_slots,         # slots that differ from the taught value
        "steps": [_fmt_resolved_step(s) for s in steps],
        "stepCount": len(steps),
        "message": message,
    })


def log_recovery(
    *,
    request_id: str,
    flow_id: str,
    step_index: int,
    step_action: str,
    step_target_text: str | None,
    decision: str,
    confidence: float,
    reason: str,
    screen_package: str | None,
    screen_title: str | None,
    screen_node_count: int,
    attempt: int,
) -> None:
    """Log a recovery/step-result decision."""
    _write({
        "ts": _ts(),
        "type": "RECOVERY",
        "requestId": request_id,
        "flowId": flow_id,
        "stepIndex": step_index,
        "stepAction": step_action,
        "stepTargetText": step_target_text,
        "decision": decision,
        "confidence": confidence,
        "reason": reason,
        "attempt": attempt,
        "screen": {
            "package": screen_package,
            "title": screen_title,
            "nodeCount": screen_node_count,
        },
    })


# ── log reader (for /v1/logs endpoint) ───────────────────────────────────────

def read_recent(limit: int = 50, event_type: str | None = None) -> list[dict]:
    """Return the last `limit` log entries, optionally filtered by type."""
    path = _log_dir / "sessions.jsonl"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                if event_type is None or r.get("type") == event_type.upper():
                    records.append(r)
                    if len(records) >= limit:
                        break
            except json.JSONDecodeError:
                continue
        return list(reversed(records))
    except Exception as e:
        log.warning("session_logger read failed: %s", e)
        return []
