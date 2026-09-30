import logging
import uuid
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.models.schemas import IntentExtractRequest, IntentExtractResponse, ErrorResponse, ErrorDetail, TeachRequest, ReplayRequest, ProcessResponse
from app.services.intent_service import process_intent_extraction
from app.utils.validation import validation_exception_handler
from typing import Union

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Teachable Voice Automation - Cloud 1 Backend", version="1.0.0")

# Register custom validation handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

@app.middleware("http")
async def add_process_time_and_log(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Safe logging (no bodies logged to prevent PII/creds leak)
    logger.info(f"Request started: {request.method} {request.url.path} - ID: {request_id}")
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Latency: {process_time:.2f}ms - ID: {request_id}")
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Latency: {process_time:.2f}ms - ID: {request_id}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="INTERNAL_ERROR", message="An unexpected internal error occurred.")
            ).model_dump()
        )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/v1/intent/extract", response_model=IntentExtractResponse)
async def extract_intent(request: IntentExtractRequest):
    if not request.utterance.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="EMPTY_UTTERANCE", message="Utterance cannot be empty.")
            ).model_dump()
        )
    
    try:
        # Calls the Gemini service
        response = process_intent_extraction(request)
        logger.info(f"Successfully extracted intent: {response.intent}")
        return response
    except Exception as e:
        # Determine if it's a model issue or generic issue
        logger.error(f"Model error during intent extraction: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="MODEL_ERROR", message="Failed to extract intent and slots from the utterance.")
            ).model_dump()
        )

from app.services.cloud2_service import generalize_flow, replay_flow

@app.post("/v1/process", response_model=ProcessResponse)
async def process(request: Union[TeachRequest, ReplayRequest]):
    """
    Accepts the TEACH and REPLAY contracts.
    Delegates to intent/slot extraction (Cloud 1), then runs Cloud 2 matching/generalization.
    """
    if not request.utterance.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="EMPTY_UTTERANCE", message="Utterance cannot be empty.")
            ).model_dump()
        )

    try:
        current_app = request.app if isinstance(request, TeachRequest) else request.currentApp
        extracted = process_intent_extraction(IntentExtractRequest(
            utterance=request.utterance,
            currentApp=current_app
        ))
        
        if extracted.intent == "unknown_intent":
            return ProcessResponse(
                success=True,
                type="NOT_LEARNED",
                message="Intent is unknown or unsupported."
            )

        if isinstance(request, TeachRequest):
            return generalize_flow(extracted.intent, current_app, extracted.slots, request.actions)
        else:
            return replay_flow(extracted.intent, current_app, extracted.slots)
            
    except Exception as e:
        logger.error(f"Error in process: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="INTERNAL_ERROR", message="Failed to process utterance.")
            ).model_dump()
        )

from app.models.schemas import FeedbackRequest, FeedbackResponse
from app.services.recovery_service import process_feedback

@app.post("/v1/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest):
    try:
        return process_feedback(request)
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="INTERNAL_ERROR", message="Failed to process feedback.")
            ).model_dump()
        )
