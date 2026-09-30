from app.models.schemas import FeedbackRequest, FeedbackResponse

def process_feedback(request: FeedbackRequest) -> FeedbackResponse:
    # Deterministic recovery decisions based on Android reasons
    status = "RECOVERY_REQUIRED"
    
    if request.reason == "NODE_NOT_FOUND":
        status = "RECOVERY_REQUIRED"
    elif request.reason == "AMBIGUOUS_NODE_MATCH":
        status = "ASK_USER"
    elif request.reason == "WRONG_APPLICATION":
        status = "STOP"
    elif request.reason == "SENSITIVE_ACTION":
        status = "STOP"
    elif request.reason == "UI_STATE_TIMEOUT":
        status = "RECOVERY_REQUIRED"
    elif request.reason == "ACTION_VERIFICATION_FAILED":
        status = "RECOVERY_REQUIRED"
    else:
        status = "STOP"

    return FeedbackResponse(
        status=status,
        flowId=request.flowId,
        actionIndex=request.actionIndex,
        reason=request.reason
    )
