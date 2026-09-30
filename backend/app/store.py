"""Flow store + event log. JSON files to start (roadmap: 'keep the schema simple').

On Cloud Run the container filesystem is ephemeral; swap JsonFlowStore for a Firestore-backed
class with the same four methods when you deploy for real.
"""
from __future__ import annotations

import json
import os
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import Flow


class JsonFlowStore:
    def __init__(self, directory: str | os.PathLike | None = None):
        self.dir = Path(directory or os.getenv("DATA_DIR", "data"))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.flows_path = self.dir / "flows.json"
        self.events_path = self.dir / "events.jsonl"
        self._lock = threading.Lock()

    # ---- flows ----
    def _read(self) -> dict[str, dict]:
        if not self.flows_path.exists():
            return {}
        return json.loads(self.flows_path.read_text(encoding="utf-8") or "{}")

    def _write(self, data: dict[str, dict]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.flows_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.flows_path)

    def list(self) -> list[Flow]:
        with self._lock:
            return [Flow.model_validate(f) for f in self._read().values()]

    def get(self, flow_id: str) -> Flow | None:
        with self._lock:
            raw = self._read().get(flow_id)
        return Flow.model_validate(raw) if raw else None

    def save(self, flow: Flow) -> None:
        with self._lock:
            data = self._read()
            data[flow.flowId] = flow.model_dump(mode="json")
            self._write(data)

    def delete(self, flow_id: str) -> bool:
        with self._lock:
            data = self._read()
            found = data.pop(flow_id, None) is not None
            self._write(data)
        return found

    def save_new(self, flow: Flow) -> Flow:
        """Assign the next free id for the flow's intent (e.g. order_food_003) and save it."""
        with self._lock:
            data = self._read()
            nums = [int(k.rsplit("_", 1)[1]) for k in data if k.startswith(flow.intent + "_") and k.rsplit("_", 1)[1].isdigit()]
            flow.flowId = f"{flow.intent}_{max(nums, default=0) + 1:03d}"
            data[flow.flowId] = flow.model_dump(mode="json")
            self._write(data)
        return flow

    # ---- events (evaluation log; never contains credentials) ----
    def log(self, kind: str, **fields: Any) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, **fields}
        with self._lock, self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    def events(self) -> list[dict]:
        if not self.events_path.exists():
            return []
        with self._lock:
            return [json.loads(line) for line in self.events_path.read_text(encoding="utf-8").splitlines() if line]

    def metrics(self) -> dict[str, Any]:
        ev = self.events()
        replay = Counter(e.get("status") for e in ev if e["kind"] == "replay")
        steps = [e for e in ev if e["kind"] == "step_result"]
        failures = Counter(f"{e['flowId']}#step{e['stepIndex'] + 1}" for e in steps if not e.get("success"))
        return {
            "flows": len(self._read()),
            "teach": Counter(e.get("status") for e in ev if e["kind"] == "teach"),
            "replay": replay,
            "slotSubstitutions": sum(len(e.get("changedSlots", [])) for e in ev if e["kind"] == "replay"),
            "recovery": Counter(e.get("decision") for e in ev if e["kind"] == "recover"),
            "steps": {"ok": sum(1 for e in steps if e.get("success")), "failed": sum(failures.values())},
            "topFailingSteps": failures.most_common(5),
        }
