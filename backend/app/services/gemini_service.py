import os
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import IntentExtractResponse

# Initialize GenAI client using Vertex AI and Application Default Credentials
# This runs in Cloud Run as the attached service account.
client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_region,
)

def get_intent_and_slots(utterance: str, current_app: str) -> IntentExtractResponse:
    prompt_file = os.path.join(os.path.dirname(__file__), "../prompts/intent_slot_prompt.txt")
    with open(prompt_file, "r") as f:
        system_prompt = f.read()
    
    # We pass currentApp just in case the model needs context, but primarily rely on utterance.
    user_prompt = f"User Utterance: {utterance}\nCurrent App: {current_app}"
    
    # Use Structured Output with GenAI SDK on Vertex AI
    response = client.models.generate_content(
        model=settings.vertex_gemini_model,
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
