from app.models.schemas import IntentExtractRequest, IntentExtractResponse
from app.services.gemini_service import get_intent_and_slots
import logging

logger = logging.getLogger(__name__)

def process_intent_extraction(request: IntentExtractRequest) -> IntentExtractResponse:
    try:
        response = get_intent_and_slots(request.utterance, request.currentApp)
        return response
    except Exception as e:
        logger.error(f"Error extracting intent: {str(e)}")
        raise
