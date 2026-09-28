import os
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import IntentExtractResponse

# Initialize GenAI client
# The SDK automatically looks for GEMINI_API_KEY environment variable.
if settings.gemini_api_key:
    client = genai.Client(api_key=settings.gemini_api_key)
else:
    # Let it default or fail if key is missing, depending on environment setup.
    client = genai.Client()

def get_intent_and_slots(utterance: str, current_app: str) -> IntentExtractResponse:
    prompt_file = os.path.join(os.path.dirname(__file__), "../prompts/intent_slot_prompt.txt")
    with open(prompt_file, "r") as f:
        system_prompt = f.read()
    
    # We pass currentApp just in case the model needs context, but primarily rely on utterance.
    user_prompt = f"User Utterance: {utterance}\nCurrent App: {current_app}"
    
    # Use Structured Output with GenAI SDK
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=IntentExtractResponse,
            temperature=0.0
        )
    )
    
    # response.parsed should contain the Pydantic object since we provided response_schema
    return response.parsed
