"""
flow_matcher.py — Match a new utterance to a previously saved flow.

This is YOUR module (Cloud 2 / Backend Architect).
It is intentionally deterministic (no AI needed for clear cases).
AI (your friend's Gemini) is only called when keyword matching is ambiguous.

Matching priority:
1. Exact intent match from AI extraction
2. Intent + app package match
3. If multiple flows match the same intent → ASK_USER
4. If no flows match → UNKNOWN_INTENT
"""
import logging
from typing import List, Dict, Any, Optional, Tuple

import storage
import ai_client
import config

logger = logging.getLogger(__name__)


def match_utterance_to_flow(
    utterance: str,
    app_package: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point. Given a user's utterance, find the best matching
    saved flow and resolve its slot values.

    Returns a dict with keys:
        matched            : bool
        flowId             : str or None
        resolvedSlots      : dict or None
        actions            : list or None
        decision           : str (EXECUTE_PLAN / ASK_USER / UNKNOWN_INTENT)
        confidence         : float
        clarificationQuestion : str or None
        message            : str
    """
    # Step 1: Extract intent and slots from the utterance using AI
    ai_result = ai_client.extract_intent_and_slots(utterance)
    intent = ai_result.get("intent", "unknown_intent")
    extracted_slots = ai_result.get("slots", {})
    confidence = ai_result.get("confidence", 0.0)
    clarification = ai_result.get("clarification")

    logger.info(f"Utterance '{utterance}' → intent={intent}, confidence={confidence}")

    # Step 2: If intent is unknown, offer teaching immediately
    if intent == "unknown_intent" or confidence < config.MIN_CONFIDENCE_THRESHOLD:
        return {
            "matched": False,
            "flowId": None,
            "resolvedSlots": None,
            "actions": None,
            "decision": "UNKNOWN_INTENT",
            "confidence": confidence,
            "clarificationQuestion": clarification or "I haven't learned this flow yet. Would you like to teach it to me?",
            "message": "No matching flow found. Please teach this flow first."
        }

    # Step 3: Load all saved flows and find ones matching this intent
    all_flows = storage.list_flows()
    matching_flows = _filter_by_intent(all_flows, intent, app_package)

    logger.info(f"Found {len(matching_flows)} flows matching intent={intent}")

    # Step 4: No matching flow found — offer teaching
    if len(matching_flows) == 0:
        return {
            "matched": False,
            "flowId": None,
            "resolvedSlots": None,
            "actions": None,
            "decision": "UNKNOWN_INTENT",
            "confidence": confidence,
            "clarificationQuestion": f"I know about '{intent}' but haven't learned a specific flow for it yet. Want to teach me?",
            "message": f"No saved flow found for intent: {intent}"
        }

    # Step 5: Exactly one flow matches — use it
    if len(matching_flows) == 1:
        flow = matching_flows[0]
        resolved = _resolve_slots(flow, extracted_slots)
        missing = _find_missing_required_slots(flow, resolved)

        # If required slots are missing, ask for them
        if missing:
            return {
                "matched": True,
                "flowId": flow["flowId"],
                "resolvedSlots": resolved,
                "actions": None,
                "decision": "ASK_USER",
                "confidence": confidence,
                "clarificationQuestion": f"Please provide: {', '.join(missing)}",
                "message": f"Flow found but missing required slots: {missing}"
            }

        return {
            "matched": True,
            "flowId": flow["flowId"],
            "resolvedSlots": resolved,
            "actions": flow.get("generalizedSteps", []),
            "decision": "EXECUTE_PLAN",
            "confidence": confidence,
            "clarificationQuestion": None,
            "message": f"Matched flow '{flow['flowId']}' for intent '{intent}'"
        }

    # Step 6: Multiple flows match — ask for clarification
    flow_names = [f.get("appName", f.get("appPackage", f["flowId"])) for f in matching_flows]
    return {
        "matched": False,
        "flowId": None,
        "resolvedSlots": None,
        "actions": None,
        "decision": "ASK_USER",
        "confidence": confidence,
        "clarificationQuestion": f"I found {len(matching_flows)} possible flows: {', '.join(flow_names)}. Which app do you want to use?",
        "message": "Multiple flows match. Disambiguation required."
    }


def _filter_by_intent(
    flows: List[Dict[str, Any]],
    intent: str,
    app_package: Optional[str]
) -> List[Dict[str, Any]]:
    """Filter saved flows by intent, and optionally by app package."""
    matches = [f for f in flows if f.get("intent") == intent]

    # If app_package is specified, prefer flows for that specific app
    if app_package:
        app_matches = [f for f in matches if f.get("appPackage") == app_package]
        if app_matches:
            return app_matches

    return matches


def _resolve_slots(
    flow: Dict[str, Any],
    extracted_slots: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge the flow's default slot values with the newly extracted slot values.
    Newly extracted values always win over defaults.
    """
    resolved = {}

    # Start with flow defaults
    for slot_def in flow.get("slotDefinitions", []):
        name = slot_def.get("name")
        default = slot_def.get("defaultValue")
        resolved[name] = default

    # Override with freshly extracted values
    for slot_name, slot_value in extracted_slots.items():
        if slot_value is not None:
            resolved[slot_name] = slot_value

    return resolved


def _find_missing_required_slots(
    flow: Dict[str, Any],
    resolved_slots: Dict[str, Any]
) -> List[str]:
    """Return names of required slots that have no value."""
    missing = []
    for slot_def in flow.get("slotDefinitions", []):
        if slot_def.get("required", True):
            name = slot_def.get("name")
            if not resolved_slots.get(name):
                missing.append(name)
    return missing
