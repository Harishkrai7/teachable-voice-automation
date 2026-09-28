"""
main.py — The FastAPI application. All 6 endpoints wired together.

This is YOUR file (Cloud 2 / Backend Architect).
Each endpoint:
  1. Receives validated JSON from Android (Pydantic handles validation automatically)
  2. Calls storage / flow_matcher / ai_client
  3. Returns a strict JSON response

The LLM (Gemini) is NEVER given direct access to Android. It only sees
text descriptions and returns structured JSON. Android validates every
suggested action before executing it.
"""
import logging
import uuid
from datetime import datetime, UTC

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import config
import storage
import ai_client
import flow_matcher
from models import (
    TeachRequest, TeachResponse,
    ReplayPlanRequest, ReplayPlanResponse,
    RecoveryRequest, RecoveryResponse,
    StepResultRequest, StepResultResponse,
    FlowMatchRequest, FlowMatchResponse,
    HealthResponse,
    GeneralizedStep, SlotDefinition,
    ReplayDecision, RecoveryDecision
)

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Teachable Voice Automation API",
    description="Samsung PRISM 2026-27 — Theme 3 — Google Cloud Backend",
    version=config.APP_VERSION
)


# ═══════════════════════════════════════════════════════════════════════════
# Global error handler — always return clean JSON, never an HTML error page
# ═══════════════════════════════════════════════════════════════════════════
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ═══════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Returns service status and version. No secrets exposed."""
    return HealthResponse(
        status="ok",
        version=config.APP_VERSION,
        schemaVersion=config.SCHEMA_VERSION,
        flowsStored=storage.count_flows()
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/teach
# Android sends a spoken command + demonstration clicks.
# We extract intent/slots, generalize into a reusable flow, and save it.
# ═══════════════════════════════════════════════════════════════════════════
@app.post("/v1/teach", response_model=TeachResponse, tags=["Teaching"])
def teach_flow(request: TeachRequest):
    """
    Accept an Android teaching demonstration.
    Extract intent + slots, generalize the flow, and save it.
    """
    logger.info(f"[TEACH] requestId={request.requestId} utterance='{request.utterance}'")

    # Convert Pydantic models to plain dicts for AI functions
    demo_dicts = [step.model_dump(exclude_none=True) for step in request.demonstration]

    # Step 1: Extract intent and slots from the utterance + demonstration
    ai_result = ai_client.extract_intent_and_slots(request.utterance, demo_dicts)
    intent = ai_result.get("intent", "unknown_intent")
    slots = ai_result.get("slots", {})
    confidence = ai_result.get("confidence", 0.0)
    clarification = ai_result.get("clarification")

    # Step 2: If clarification is needed, don't save yet — ask first
    if clarification and confidence < config.MIN_CONFIDENCE_THRESHOLD:
        flow_id = storage.generate_flow_id()
        return TeachResponse(
            status="clarification_needed",
            flowId=flow_id,
            intent=intent,
            slots=slots,
            slotDefinitions=[],
            generalizedSteps=[],
            confidence=confidence,
            clarificationNeeded=True,
            clarificationQuestion=clarification,
            debugSummary="Low confidence — clarification required before saving."
        )

    # Step 3: Generalize the demonstration into a reusable flow
    gen_result = ai_client.generalize_demonstration(request.utterance, demo_dicts, ai_result)
    generalized_steps_raw = gen_result.get("generalizedSteps", [])
    slot_definitions_raw = gen_result.get("slotDefinitions", [])
    debug_summary = gen_result.get("debugSummary", "")

    # Step 4: Build the flow data to save
    flow_id = storage.generate_flow_id()
    flow_data = {
        "flowId": flow_id,
        "schemaVersion": config.SCHEMA_VERSION,
        "intent": intent,
        "appPackage": request.appPackage,
        "appName": request.appName,
        "originalUtterance": request.utterance,
        "slots": slots,
        "slotDefinitions": slot_definitions_raw,
        "generalizedSteps": generalized_steps_raw,
        "stopBefore": ["PAYMENT", "OTP", "PASSWORD", "PIN", "LOGIN", "AUTHENTICATION"],
        "confidence": confidence,
        "createdAt": datetime.now(UTC).isoformat(),
    }

    # Step 5: Save the flow
    saved_id = storage.save_flow(flow_data)
    logger.info(f"[TEACH] Saved flow {saved_id} for intent '{intent}'")

    # Step 6: Build response
    generalized_steps = [GeneralizedStep(**s) for s in generalized_steps_raw]
    slot_definitions = [SlotDefinition(**s) for s in slot_definitions_raw]

    return TeachResponse(
        status="success",
        flowId=saved_id,
        intent=intent,
        slots=slots,
        slotDefinitions=slot_definitions,
        generalizedSteps=generalized_steps,
        confidence=confidence,
        clarificationNeeded=False,
        clarificationQuestion=None,
        schemaVersion=config.SCHEMA_VERSION,
        debugSummary=debug_summary
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/replay/plan
# Android sends a new voice command. We find the matching flow and return
# a structured execution plan with resolved slot values.
# ═══════════════════════════════════════════════════════════════════════════
@app.post("/v1/replay/plan", response_model=ReplayPlanResponse, tags=["Replay"])
def replay_plan(request: ReplayPlanRequest):
    """
    Match the utterance to a saved flow and return an execution plan.
    """
    logger.info(f"[REPLAY] requestId={request.requestId} utterance='{request.utterance}'")

    # Delegate all matching logic to flow_matcher.py
    match_result = flow_matcher.match_utterance_to_flow(
        utterance=request.utterance,
        app_package=request.appPackage
    )

    decision_str = match_result["decision"]
    decision = ReplayDecision(decision_str)

    # Build generalized step objects if we have actions
    actions = None
    if match_result.get("actions"):
        actions = [GeneralizedStep(**s) for s in match_result["actions"]]

    return ReplayPlanResponse(
        decision=decision,
        flowId=match_result.get("flowId"),
        resolvedSlots=match_result.get("resolvedSlots"),
        actions=actions,
        clarificationQuestion=match_result.get("clarificationQuestion"),
        message=match_result["message"],
        confidence=match_result.get("confidence"),
        schemaVersion=config.SCHEMA_VERSION
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/recovery
# Android reports a failed step. We reason about what went wrong and
# return a constrained recovery decision. We NEVER return raw code.
# ═══════════════════════════════════════════════════════════════════════════
@app.post("/v1/recovery", response_model=RecoveryResponse, tags=["Recovery"])
def recovery(request: RecoveryRequest):
    """
    Reason about a failed step and return CONTINUE / RETRY / ASK_USER / STOP.
    """
    logger.info(f"[RECOVERY] flowId={request.flowId} step={request.currentStepIndex}")

    # Safety-first: check if the screen summary mentions sensitive keywords
    ui_lower = (request.currentUISummary or "").lower()
    for keyword in config.SENSITIVE_SCREEN_KEYWORDS:
        if keyword in ui_lower:
            logger.warning(f"[RECOVERY] Sensitive keyword '{keyword}' detected. Returning STOP.")
            return RecoveryResponse(
                decision=RecoveryDecision.STOP,
                suggestedAction=None,
                reason=f"Sensitive screen detected ({keyword}). Handing control to user for safety.",
                confidence=1.0,
                nextExpectedState=None,
                schemaVersion=config.SCHEMA_VERSION
            )

    # Delegate reasoning to ai_client (friend's Gemini or mock)
    expected_action_dict = request.expectedAction.model_dump(exclude_none=True)
    recovery_result = ai_client.reason_recovery(
        current_ui_summary=request.currentUISummary,
        expected_action=expected_action_dict,
        failure_reason=request.failureReason
    )

    decision = RecoveryDecision(recovery_result["decision"])
    suggested_action = None
    if recovery_result.get("suggestedAction"):
        suggested_action = GeneralizedStep(**recovery_result["suggestedAction"])

    return RecoveryResponse(
        decision=decision,
        suggestedAction=suggested_action,
        reason=recovery_result["reason"],
        confidence=recovery_result["confidence"],
        nextExpectedState=recovery_result.get("nextExpectedState"),
        schemaVersion=config.SCHEMA_VERSION
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/step-result
# Android reports the outcome of each step. We log it for evaluation.
# ═══════════════════════════════════════════════════════════════════════════
@app.post("/v1/step-result", response_model=StepResultResponse, tags=["Logging"])
def step_result(request: StepResultRequest):
    """
    Receive and log the outcome of each step from Android.
    Used for evaluation metrics (T14) and debugging.
    """
    outcome = "SUCCESS" if request.success else "FAILURE"
    logger.info(
        f"[STEP-RESULT] flowId={request.flowId} stepId={request.stepId} "
        f"action={request.action.action} outcome={outcome} "
        f"failureReason={request.failureReason}"
    )
    return StepResultResponse(
        acknowledged=True,
        message=f"Step {request.stepId} result recorded: {outcome}",
        schemaVersion=config.SCHEMA_VERSION
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/flows/match
# Standalone endpoint for the Android team to match a command to a flow
# without committing to execution. Useful for pre-checking.
# ═══════════════════════════════════════════════════════════════════════════
@app.post("/v1/flows/match", response_model=FlowMatchResponse, tags=["Flows"])
def flows_match(request: FlowMatchRequest):
    """
    Match a user command to a saved flow without starting execution.
    """
    logger.info(f"[MATCH] requestId={request.requestId} utterance='{request.utterance}'")

    match_result = flow_matcher.match_utterance_to_flow(
        utterance=request.utterance,
        app_package=request.appPackage
    )

    return FlowMatchResponse(
        matched=match_result["matched"],
        flowId=match_result.get("flowId"),
        extractedSlots=match_result.get("resolvedSlots"),
        confidence=match_result.get("confidence"),
        ambiguous=match_result["decision"] == "ASK_USER",
        clarificationQuestion=match_result.get("clarificationQuestion"),
        message=match_result["message"],
        schemaVersion=config.SCHEMA_VERSION
    )


# ═══════════════════════════════════════════════════════════════════════════
# GET /v1/flows
# List all saved flows — useful for debugging and demo inspection
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/v1/flows", tags=["Flows"])
def list_flows():
    """List all learned flows. Useful for debugging and demo day inspection."""
    flows = storage.list_flows()
    summaries = []
    for f in flows:
        summaries.append({
            "flowId": f.get("flowId"),
            "intent": f.get("intent"),
            "appName": f.get("appName"),
            "appPackage": f.get("appPackage"),
            "originalUtterance": f.get("originalUtterance"),
            "slotCount": len(f.get("slotDefinitions", [])),
            "stepCount": len(f.get("generalizedSteps", [])),
            "createdAt": f.get("createdAt"),
        })
    return {"totalFlows": len(summaries), "flows": summaries}


# ═══════════════════════════════════════════════════════════════════════════
# GET /v1/flows/{flow_id}
# Inspect a single saved flow in full detail
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/v1/flows/{flow_id}", tags=["Flows"])
def get_flow(flow_id: str):
    """
    Inspect the full detail of a saved learned flow.
    Useful for debugging generalization quality.
    """
    flow = storage.load_flow(flow_id)
    if not flow:
        return JSONResponse(
            status_code=404,
            content={"error": f"Flow '{flow_id}' not found"}
        )
    return flow


# ═══════════════════════════════════════════════════════════════════════════
# DELETE /v1/flows/{flow_id}
# Delete a flow — useful for clean demo resets
# ═══════════════════════════════════════════════════════════════════════════
@app.delete("/v1/flows/{flow_id}", tags=["Flows"])
def delete_flow(flow_id: str):
    """
    Delete a learned flow by ID.
    Use this to reset between demo runs or clean up test flows.
    """
    deleted = storage.delete_flow(flow_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"error": f"Flow '{flow_id}' not found"}
        )
    logger.info(f"[DELETE] Flow {flow_id} deleted")
    return {"deleted": True, "flowId": flow_id}
