from google import genai
import os

print("Testing Vertex AI...")
try:
    client = genai.Client(
        vertexai=True,
        project="teachable-voice-automation",
        location="asia-south1",
    )

    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Reply with exactly: TEST_OK"
    )
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
