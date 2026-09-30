from google import genai
from google.genai import types
import os

print("Testing Vertex AI...")
try:
    client = genai.Client(
        vertexai=True,
        project="teachable-voice-automation",
        location="asia-south1",
        http_options=types.HttpOptions(api_version="v1"),
    )

    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Reply with exactly: TEST_OK"
    )
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
