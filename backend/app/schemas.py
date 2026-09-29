"""Android <-> Cloud JSON contract (roadmap section 6). Freeze and version this file."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0"


class ActionType(str, Enum):
    CLICK = "CLICK"
    TYPE = "TYPE"
    SEARCH = "SEARCH"
    SELECT = "SELECT"
    SCROLL = "SCROLL"
    BACK = "BACK"
    SET_QUANTITY = "SET_QUANTITY"
    ADD_TO_CART = "ADD_TO_CART"
    OPEN_CART = "OPEN_CART"
    SELECT_ADDRESS = "SELECT_ADDRESS"
    DISMISS = "DISMISS"
    WAIT = "WAIT"


class Target(BaseModel):
    """Semantic evidence about a UI element (roadmap phase A3). Never coordinates-only."""

    model_config = ConfigDict(extra="allow")

    resourceId: str | None = None
    text: str | None = None
    contentDescription: str | None = None
    className: str | None = None
    clickable: bool | None = None
    enabled: bool | None = None
    isPassword: bool = False
    bounds: list[float] | None = Field(default=None, description="Relative [l, t, r, b] in 0..1")
    parentText: str | None = None
    package: str | None = None
    screen: str | None = None
    screenFingerprint: str | None = None


class ObservedAction(BaseModel):
    """One user action recorded by the Android Teaching Recorder."""

    model_config = ConfigDict(extra="allow")

    action: ActionType
    value: str | None = None
    target: Target | None = None
    timestampMs: int | None = None


class Step(BaseModel):
    """A generalized (or resolved) flow step. `value` / `target.text` may hold {{slot}} templates."""

    action: ActionType
    value: str | None = None
    target: Target | None = None
    slotRefs: list[str] = Field(default_factory=list)
    taughtValue: str | None = None
    taughtTargetText: str | None = None


class Flow(BaseModel):
    flowId: str
    intent: str
    app: str | None = None
    utterances: list[str]
    slots: dict[str, Any]
    steps: list[Step]
    stopBefore: list[str] = Field(default_factory=lambda: ["PAYMENT", "OTP", "PASSWORD", "PIN", "AUTH"])
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    contractVersion: str = CONTRACT_VERSION


class ScreenSummary(BaseModel):
    """Compact description of the current screen, built by Android's UI Tree Reader."""

    package: str | None = None
    screenTitle: str | None = None
    nodes: list[Target] = Field(default_factory=list)


# ---- Requests ----------------------------------------------------------------

class TeachRequest(BaseModel):
    mode: Literal["TEACH"] = "TEACH"
    contractVersion: str = CONTRACT_VERSION
    utterance: str = Field(min_length=1)
    app: str | None = None
    actions: list[ObservedAction] = Field(min_length=1)


class ReplayRequest(BaseModel):
    mode: Literal["REPLAY"] = "REPLAY"
    contractVersion: str = CONTRACT_VERSION
    utterance: str = Field(min_length=1)
    currentApp: str | None = None
    uiSummary: ScreenSummary | None = None
    flowId: str | None = Field(default=None, description="Set after the user picks an ASK_USER option")


class RecoverRequest(BaseModel):
    contractVersion: str = CONTRACT_VERSION
    requestId: str | None = None
    flowId: str
    stepIndex: int = Field(ge=0)
    step: Step
    screen: ScreenSummary
    attempt: int = Field(default=1, ge=1)


class StepResult(BaseModel):
    contractVersion: str = CONTRACT_VERSION
    requestId: str | None = None
    flowId: str
    stepIndex: int = Field(ge=0)
    success: bool
    stateSummary: str | None = None
    failureReason: str | None = None


# ---- Responses ---------------------------------------------------------------

class Extraction(BaseModel):
    intent: str = "unknown_intent"
    slots: dict[str, Any] = Field(default_factory=dict)
    app: str | None = None


class TeachResponse(BaseModel):
    status: Literal["LEARNED", "REJECTED"]
    requestId: str
    flow: Flow | None = None
    droppedActions: int = 0
    warnings: list[str] = Field(default_factory=list)
    reason: str | None = None


class ReplayStatus(str, Enum):
    PLAN = "PLAN"
    ASK_USER = "ASK_USER"
    NOT_LEARNED = "NOT_LEARNED"
    STOP = "STOP"


class Option(BaseModel):
    flowId: str
    label: str


class ReplayResponse(BaseModel):
    status: ReplayStatus
    requestId: str
    intent: str | None = None
    slots: dict[str, Any] = Field(default_factory=dict)
    defaultedSlots: list[str] = Field(default_factory=list)
    flowId: str | None = None
    app: str | None = None
    actions: list[Step] = Field(default_factory=list)
    stopBefore: list[str] = Field(default_factory=list)
    question: str | None = None
    options: list[Option] = Field(default_factory=list)
    offerTeach: bool = False
    reason: str | None = None


class RecoveryDecision(str, Enum):
    RETRY_ALTERNATE = "RETRY_ALTERNATE"  # target found under slightly different evidence
    DISMISS_POPUP = "DISMISS_POPUP"      # harmless popup, dismiss it then retry the step
    SKIP_STEP = "SKIP_STEP"              # expected state already reached (e.g. already in cart)
    ASK_USER = "ASK_USER"                # specific clarification question
    STOP = "STOP"                        # sensitive screen, hand control to the user
    FAIL = "FAIL"                        # genuinely stuck, report the step


class RecoverResponse(BaseModel):
    requestId: str
    decision: RecoveryDecision
    action: Step | None = None
    question: str | None = None
    options: list[str] = Field(default_factory=list)
    reason: str
    confidence: float = Field(ge=0, le=1)
