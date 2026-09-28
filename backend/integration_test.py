import os
from app.models.schemas import IntentExtractRequest
from app.services.intent_service import process_intent_extraction
from app.config import settings
import json

def test_real_gemini():
    print("Testing real Gemini API integration...")
    if not settings.gemini_api_key:
        print("Error: GEMINI_API_KEY is not set.")
        return

    req = IntentExtractRequest(
        utterance="Order a Margherita pizza from Dominos",
        currentApp="Zomato"
    )
    
    try:
        response = process_intent_extraction(req)
        print("Success! Response from Gemini:")
        # Dump using pydantic
        print(json.dumps(response.model_dump(), indent=2))
        
        # Verify specific fields as requested
        assert response.intent == "order_food"
        assert response.slots.restaurant == "Dominos"
        assert response.slots.item == "Margherita Pizza"
        assert response.slots.quantity == 1
        assert response.slots.address is None
        print("Validation Passed!")
    except Exception as e:
        print("Test failed with error:", str(e))
        import sys
        sys.exit(1)

if __name__ == "__main__":
    test_real_gemini()
