import logging
import uuid
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.models.schemas import IntentExtractRequest, IntentExtractResponse, ErrorResponse, ErrorDetail, TeachRequest, ReplayRequest
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

@app.post("/v1/process")
async def process(request: Union[TeachRequest, ReplayRequest]):
    """
    Accepts the TEACH and REPLAY contracts.
    Currently delegates to intent/slot extraction for Cloud 1 representation,
    providing a clean structured response ready for Cloud 2 to implement matching logic.
    """
    if not request.utterance.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="EMPTY_UTTERANCE", message="Utterance cannot be empty.")
            ).model_dump()
        )

    # Cloud 1 responsibilities: extract intent and slots based on utterance.
    # Cloud 2 will later take this extracted structure and process learning/execution logic.
    try:
        extracted = process_intent_extraction(IntentExtractRequest(
            utterance=request.utterance,
            currentApp=request.app if isinstance(request, TeachRequest) else request.currentApp
        ))
        
        return {
            "success": True,
            "mode": request.mode,
            "cloud1_output": extracted.model_dump(),
            "message": "Processed by Cloud 1. Hand-off to Cloud 2 available."
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="MODEL_ERROR", message="Failed to process utterance.")
            ).model_dump()
        )
