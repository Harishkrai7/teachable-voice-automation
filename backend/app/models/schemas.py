from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Action(BaseModel):
    action: str
    target: Optional[str] = None
    value: Optional[str] = None

class TeachRequest(BaseModel):
    mode: str
    utterance: str
    actions: List[Action]
    app: str

class ReplayRequest(BaseModel):
    mode: str
    utterance: str
    currentApp: str

class IntentExtractRequest(BaseModel):
    utterance: str
    currentApp: str

class Slots(BaseModel):
    restaurant: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[int] = None
    address: Optional[str] = None

class IntentExtractResponse(BaseModel):
    intent: str = Field(description="The extracted intent: order_food, add_to_cart, or unknown_intent")
    slots: Slots = Field(description="Extracted slots for the intent")

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail

class Flow(BaseModel):
    flowId: str
    intent: str
    app: str
    slots: Dict[str, Optional[Any]]
    steps: List[Action]
    stopBefore: List[str]

class ProcessResponse(BaseModel):
    success: bool
    type: Optional[str] = None
    mode: Optional[str] = None
    flow: Optional[Flow] = None
    flowId: Optional[str] = None
    intent: Optional[str] = None
    slots: Optional[Dict[str, Optional[Any]]] = None
    actions: Optional[List[Action]] = None
    question: Optional[str] = None
    message: Optional[str] = None
    reason: Optional[str] = None

class FeedbackRequest(BaseModel):
    flowId: str
    actionIndex: int
    failedAction: Action
    reason: str
    currentApp: str

class FeedbackResponse(BaseModel):
    status: str
    flowId: str
    actionIndex: int
    reason: str
