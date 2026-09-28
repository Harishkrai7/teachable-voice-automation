import json
import os
from typing import List, Optional
from app.models.schemas import Flow

STORAGE_FILE = os.path.join(os.path.dirname(__file__), "flows.json")

def load_flows() -> List[Flow]:
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r") as f:
            data = json.load(f)
            return [Flow(**item) for item in data]
    except Exception:
        return []

def save_flows(flows: List[Flow]):
    with open(STORAGE_FILE, "w") as f:
        json.dump([flow.model_dump() for flow in flows], f, indent=2)

def save_flow(flow: Flow):
    flows = load_flows()
    # Replace if exists
    flows = [f for f in flows if f.flowId != flow.flowId]
    flows.append(flow)
    save_flows(flows)

def get_flow(flow_id: str) -> Optional[Flow]:
    flows = load_flows()
    for f in flows:
        if f.flowId == flow_id:
            return f
    return None

def list_flows() -> List[Flow]:
    return load_flows()

def find_matching_flows(intent: str, app: str) -> List[Flow]:
    flows = load_flows()
    return [f for f in flows if f.intent == intent and f.app == app]
