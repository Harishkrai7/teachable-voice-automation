"""
storage.py — JSON file-based flow storage.

This module is YOUR responsibility (Cloud 2 / Backend Architect).

Design rules:
- Flows are saved as individual JSON files in the `flows/` directory.
- Each file is named by flowId, e.g.  flows/flow_abc12345.json
- This is intentionally simple for development.
- When your friend deploys to Cloud Run, he will plug in a Firestore
  implementation behind the same interface (save_flow / load_flow / list_flows).
- NEVER store passwords, OTPs, PINs, payment info, or full UI trees.
"""
import json
import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC

import config

logger = logging.getLogger(__name__)


def _ensure_flows_dir() -> None:
    """Create the flows directory if it doesn't already exist."""
    os.makedirs(config.FLOWS_DIR, exist_ok=True)


def _flow_path(flow_id: str) -> str:
    """Return the full file path for a given flow ID."""
    return os.path.join(config.FLOWS_DIR, f"{flow_id}.json")


def generate_flow_id() -> str:
    """Generate a unique flow ID."""
    return f"flow_{uuid.uuid4().hex[:10]}"


def save_flow(flow_data: Dict[str, Any]) -> str:
    """
    Save a learned flow to disk.
    Returns the flowId that was saved.
    """
    _ensure_flows_dir()

    flow_id = flow_data.get("flowId") or generate_flow_id()
    flow_data["flowId"] = flow_id
    flow_data["updatedAt"] = datetime.now(UTC).isoformat()

    if "createdAt" not in flow_data:
        flow_data["createdAt"] = flow_data["updatedAt"]

    path = _flow_path(flow_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flow_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved flow {flow_id} to {path}")
    return flow_id


def load_flow(flow_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a single flow by its ID.
    Returns None if the flow does not exist.
    """
    path = _flow_path(flow_id)
    if not os.path.exists(path):
        logger.warning(f"Flow {flow_id} not found at {path}")
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_flows() -> List[Dict[str, Any]]:
    """
    Return a list of all saved flows.
    """
    _ensure_flows_dir()
    flows = []

    for filename in os.listdir(config.FLOWS_DIR):
        if filename.endswith(".json"):
            path = os.path.join(config.FLOWS_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    flows.append(json.load(f))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Could not read flow file {filename}: {e}")

    return flows


def delete_flow(flow_id: str) -> bool:
    """
    Delete a flow by its ID.
    Returns True if deleted, False if it didn't exist.
    """
    path = _flow_path(flow_id)
    if not os.path.exists(path):
        return False
    os.remove(path)
    logger.info(f"Deleted flow {flow_id}")
    return True


def count_flows() -> int:
    """Return the number of saved flows."""
    _ensure_flows_dir()
    return len([f for f in os.listdir(config.FLOWS_DIR) if f.endswith(".json")])
