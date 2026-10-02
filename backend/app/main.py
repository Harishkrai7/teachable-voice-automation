"""PRISM Theme 3 - Cloud engine (Engine B). Android is the eyes + hands; this is the brain.

Run locally:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import generalizer, matcher, recovery, safety, session_logger
from .intents import Extractor, build_extractor
from .schemas import (
    CONTRACT_VERSION, Flow, RecoverRequest, RecoverResponse, ReplayRequest, ReplayResponse,
    ReplayStatus, StepResultRequest, TeachRequest, TeachResponse,
)
from .store import JsonFlowStore
from .text import norm, tokens

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("prism")

app = FastAPI(
    title="PRISM Teachable Voice Automation - Cloud Engine",
    version=CONTRACT_VERSION,
    description="Intent + slots, flow generalization, flow matching and recovery reasoning. "
    "Returns structured plans; Android executes and verifies them.",
)

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
if EXAMPLES_DIR.is_dir():
    app.mount("/examples", StaticFiles(directory=EXAMPLES_DIR), name="examples")

_store = JsonFlowStore()
_extractor = build_extractor()


def get_store() -> JsonFlowStore:
    return _store


def get_extractor() -> Extractor:
    return _extractor


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s -> %s in %.1fms", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


# ---- health / contract -------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True, "contractVersion": CONTRACT_VERSION}


@app.get("/", include_in_schema=False)
def console():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


# ---- TEACH -------------------------------------------------------------------

@app.post("/v1/teach", response_model=TeachResponse)
def teach(req: TeachRequest, store: JsonFlowStore = Depends(get_store), ex: Extractor = Depends(get_extractor)):
    rid = new_request_id()
    extraction = ex.extract(req.utterance, [f.intent for f in store.list()])
    kept, dropped = generalizer.filter_noise(req.actions)
    steps, warnings, slots = generalizer.generalize(kept, extraction.slots)

    if not steps:
        store.log("teach", requestId=rid, status="REJECTED", utterance=req.utterance)
        return TeachResponse(status="REJECTED", requestId=rid, droppedActions=dropped, warnings=warnings,
                             reason="No usable actions before the sensitive/payment boundary.")

    intent = extraction.intent
    if intent == "unknown_intent":
        intent = "custom_" + "_".join(sorted(tokens(req.utterance), key=req.utterance.lower().find)[:3])

    flow = store.save_new(Flow(
        flowId="pending", intent=intent, app=req.app or extraction.app,
        utterances=[req.utterance], slots=slots, steps=steps,
    ))
    store.log("teach", requestId=rid, status="LEARNED", flowId=flow.flowId, intent=intent,
              steps=len(steps), dropped=dropped, slots=list(slots))
    session_logger.log_teach(
        request_id=rid, utterance=req.utterance, intent=intent,
        app=req.app or extraction.app, slots=slots, steps=steps,
        warnings=warnings, actions_recorded=len(req.actions),
        actions_dropped=dropped, flow_id=flow.flowId, status="LEARNED",
    )
    return TeachResponse(
        status="LEARNED", requestId=rid, flow=flow, droppedActions=dropped, warnings=warnings,
        reason="Successfully learned the command!"
    )


# ---- REPLAY ------------------------------------------------------------------

@app.post("/v1/replay", response_model=ReplayResponse, response_model_exclude_none=True)
def replay(req: ReplayRequest, store: JsonFlowStore = Depends(get_store), ex: Extractor = Depends(get_extractor)):
    rid = new_request_id()
    flows = store.list()
    extraction = ex.extract(req.utterance, [f.intent for f in flows])

    def done(resp: ReplayResponse, changed_slots: list[str] | None = None, **extra) -> ReplayResponse:
        store.log("replay", requestId=rid, status=resp.status.value, flowId=resp.flowId,
                  utterance=req.utterance, **extra)
        session_logger.log_replay(
            request_id=rid, utterance=req.utterance, intent=resp.intent or "?",
            app=resp.app, matched_flow_id=resp.flowId,
            slots_extracted=extraction.slots,
            slots_resolved=dict(resp.slots), defaulted_slots=list(resp.defaultedSlots),
            changed_slots=changed_slots or [],
            steps=list(resp.actions), status=resp.status.value, message=resp.reason,
        )
        return resp

    if cat := safety.classify_screen(req.uiSummary):
        return done(ReplayResponse(status=ReplayStatus.STOP, requestId=rid,
                                   reason=f"{cat} screen is open. Your turn - please complete it first."))

    if req.flowId:
        flow = store.get(req.flowId)
        if flow is None:
            raise HTTPException(404, f"Unknown flowId {req.flowId}")
    else:
        m = matcher.match(extraction, req.utterance, req.currentApp, flows)
        if m.ambiguous:
            return done(ReplayResponse(
                status=ReplayStatus.ASK_USER, requestId=rid, intent=extraction.intent, slots=extraction.slots,
                question="I know more than one way to do that. Which one did you mean: "
                         + " or ".join(matcher.label(f) for f in m.ambiguous) + "?",
                options=matcher.options(m.ambiguous), reason=m.reason,
            ))
        if m.flow is None:
            return done(ReplayResponse(
                status=ReplayStatus.NOT_LEARNED, requestId=rid, intent=extraction.intent, slots=extraction.slots,
                offerTeach=True, reason=m.reason,
                question=f"I haven't learned {req.utterance!r} yet. Want to teach me? "
                         "Say the command, then show me the taps once.",
            ))
        flow = m.flow

    referenced = {r for s in flow.steps for r in s.slotRefs}
    changed = [k for k, v in extraction.slots.items()
               if k in flow.slots and norm(str(v)) != norm(str(flow.slots[k]))]
    new_slots = [k for k in extraction.slots if k not in flow.slots]
    fixed = [k for k in changed + new_slots if k not in referenced and not (k == "quantity" and extraction.slots[k] == 1)]
    if fixed:
        k = fixed[0]
        return done(ReplayResponse(
            status=ReplayStatus.ASK_USER, requestId=rid, intent=flow.intent, flowId=flow.flowId, app=flow.app,
            slots=extraction.slots, offerTeach=True, reason="Requested value can't be changed in the learned flow.",
            question=f"When you taught me this, I didn't see where to set the {k}. "
                     f"Should I use the taught {k} ({flow.slots.get(k)!r}), or will you show me where to change it?",
        ))

    resolved = {**flow.slots, **extraction.slots, **req.slotAnswers}
    defaulted = [k for k in flow.slots if k not in extraction.slots and k not in req.slotAnswers and k in referenced]
    actions, missing = generalizer.resolve(flow.steps, resolved)
    if missing:
        k = missing[0]
        return done(ReplayResponse(
            status=ReplayStatus.ASK_USER, requestId=rid, intent=flow.intent, flowId=flow.flowId, app=flow.app,
            slots=resolved, question=f"Which {k} should I use?", reason=f"Missing required slot: {k}", missingSlot=k
        ))

    if req.utterance not in flow.utterances and len(flow.utterances) < 20:
        flow.utterances.append(req.utterance)  # remember paraphrases that matched
        store.save(flow)

    return done(ReplayResponse(
        status=ReplayStatus.PLAN, requestId=rid, intent=flow.intent, flowId=flow.flowId, app=flow.app,
        slots=resolved, defaultedSlots=defaulted, actions=actions, stopBefore=flow.stopBefore,
    ), changed_slots=changed)


# ---- RECOVER / STEP RESULT ---------------------------------------------------

@app.post("/v1/step-result", response_model=RecoverResponse, response_model_exclude_none=True)
def step_result(req: StepResultRequest, store: JsonFlowStore = Depends(get_store)):
    flow = store.get(req.flowId)
    if flow is None:
        raise HTTPException(404, f"Unknown flowId {req.flowId}")
        
    store.log("step_result", **req.model_dump())
    
    if req.success or not req.screen:
        return RecoverResponse(requestId=req.requestId or new_request_id(), decision="CONTINUE", reason="Success", confidence=1.0)
        
    rid = req.requestId or new_request_id()
    # Build a RecoverRequest dynamically for the recovery module
    step = flow.steps[req.stepIndex] if req.stepIndex < len(flow.steps) else None
    if not step:
        return RecoverResponse(requestId=rid, decision="ASK_USER", reason="Invalid step index", confidence=1.0)
        
    rec_req = RecoverRequest(
        requestId=rid, flowId=req.flowId, stepIndex=req.stepIndex,
        step=step, screen=req.screen, attempt=1
    )
    
    resp = RecoverResponse(requestId=rid, **recovery.decide(rec_req))
    store.log("recover", requestId=rid, flowId=req.flowId, stepIndex=req.stepIndex,
              attempt=1, decision=resp.decision.value, reason=resp.reason)
    session_logger.log_recovery(
        request_id=rid, flow_id=req.flowId,
        step_index=req.stepIndex,
        step_action=step.action.value,
        step_target_text=(step.target.text or step.target.contentDescription or step.taughtTargetText) if step.target else None,
        decision=resp.decision.value, confidence=resp.confidence, reason=resp.reason,
        screen_package=req.screen.package if req.screen else None,
        screen_title=req.screen.screenTitle if req.screen else None,
        screen_node_count=len(req.screen.nodes) if req.screen else 0,
        attempt=1,
    )
    return resp


# ---- flows / metrics ---------------------------------------------------------

@app.get("/v1/flows", response_model=list[Flow])
def list_flows(store: JsonFlowStore = Depends(get_store)):
    return store.list()


@app.get("/v1/flows/{flow_id}", response_model=Flow)
def get_flow(flow_id: str, store: JsonFlowStore = Depends(get_store)):
    if (flow := store.get(flow_id)) is None:
        raise HTTPException(404, f"Unknown flowId {flow_id}")
    return flow


@app.delete("/v1/flows/{flow_id}")
def delete_flow(flow_id: str, store: JsonFlowStore = Depends(get_store)):
    if not store.delete(flow_id):
        raise HTTPException(404, f"Unknown flowId {flow_id}")
    return {"deleted": flow_id}


@app.get("/v1/metrics")
def metrics(store: JsonFlowStore = Depends(get_store)):
    return store.metrics()


# ---- logs (for debug) --------------------------------------------------------

@app.get("/v1/logs")
def get_logs(
    limit: int = 50,
    type: str | None = None,  # TEACH | REPLAY | RECOVERY
):
    """
    Returns the last `limit` structured session log entries.
    Useful for feeding to AI for debugging — paste the output directly.
    Example: GET /v1/logs?limit=10&type=TEACH
    """
    return session_logger.read_recent(limit=min(limit, 200), event_type=type)
