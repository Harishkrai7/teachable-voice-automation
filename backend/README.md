# Teachable Voice Automation - Cloud 1 Backend

## Project Purpose
Cloud 1 is responsible for the Google Cloud / AI layer — Voice + Intent + Slot Extraction for the Teachable Voice Automation project. 

## Architecture & Cloud 1 Responsibility
The overarching architecture separates concerns between the Android app (eyes and hands) and Google Cloud (the brain). Cloud 1's responsibility is solely to expose robust endpoints for parsing the user's voice command and securely extracting intents and relevant slots using the Gemini GenAI model.

Cloud 2 builds upon this structured output to perform Flow Generalization, Flow Matching, Parameter Substitution, and Recovery/Clarification reasoning.
All sensitive boundaries are strictly managed through `stopBefore` logic.

## Folder Structure
```
backend/
├── app/
│   ├── main.py (FastAPI application and endpoints)
│   ├── config.py (Environment and settings loader)
│   ├── models/
│   │   └── schemas.py (Pydantic validation schemas)
│   ├── services/
│   │   ├── intent_service.py (Business logic layer)
│   │   └── gemini_service.py (Google GenAI integration)
│   ├── prompts/
│   │   └── intent_slot_prompt.txt (Gemini system prompt)
│   └── utils/
│       └── validation.py (JSON validation and error handlers)
├── tests/
│   ├── test_health.py (Healthcheck endpoint testing)
│   └── test_intent.py (Unit tests for intent extraction)
├── requirements.txt
├── .env.example
├── Dockerfile
├── API_CONTRACT.md (Detailed API documentation)
└── README.md
```

## Environment Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Populate the environment variables (e.g., `GEMINI_API_KEY`).

## Local Execution
Create a virtual environment and run the backend:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
# python -m venv .venv
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health test: [http://localhost:8000/health](http://localhost:8000/health)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Documentation & Example curl requests
See `API_CONTRACT.md` for full definitions.

**Example Request (Intent Extraction):**
```bash
curl -X POST http://localhost:8000/v1/intent/extract \
  -H "Content-Type: application/json" \
  -d '{"utterance": "Order a Margherita pizza from Dominos", "currentApp": "Zomato"}'
```

## Gemini Configuration
The application leverages the `google-genai` Python SDK to retrieve strict structured JSON output using Pydantic models. The temperature is set to `0.0` for deterministic outputs.

## Testing
Run the tests using pytest:
```bash
pytest
```
The Gemini API calls are fully mocked so unit tests do not require a live API key.

## Docker Usage
```bash
docker build -t teachable-voice-backend .
docker run -p 8000:8000 --env-file .env teachable-voice-backend
```

## Google Cloud Run Deployment
1. Enable required APIs: `gcloud services enable run.googleapis.com artifactregistry.googleapis.com`
2. Build and Push using Cloud Build or push to Artifact Registry.
3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy teachable-voice-backend \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
   ```

## Android Integration Contract
Refer to `API_CONTRACT.md`. Android must strictly send payloads conforming to the `TEACH` and `REPLAY` modes. 

## Security Notes
- Never hard-code API keys. Always use `.env` locally or Google Cloud Secret Manager in production.
- Do not store user passwords, OTPs, PINs, payment details, or authentication secrets.
- Logging intercepts requests but purposely avoids logging request payloads to prevent PII leakage.

## Troubleshooting
- **Model returns 500 / Invalid JSON**: Check your `.env` for the `GEMINI_API_KEY`.
- **Validation Error (422)**: Ensure your payload strictly matches the required parameters in `API_CONTRACT.md`.

## Testing Android Teach Mode
The Android app includes a debug panel in `MainActivity` to test real `AccessibilityService` observation.
1. Enable the **Teachable Voice Automation Service** in Android Accessibility Settings.
2. Tap **START TEACH** in the app.
3. Perform standard actions (Clicking, Typing) in a safe application.
4. Return to the app and observe the `Captured Actions` trace.
6. Check `flows.json` on the backend to verify the newly mapped generic template!

## Testing Android Replay Mode
1. Ensure you have a previously taught flow (or mock it using **MOCK TEACH FLOW**).
2. Type a relevant utterance (e.g., "Order 2 Margherita pizzas").
3. Tap **REPLAY CLOUD**. The backend handles flow matching and parameter substitution.
4. Tap **START REPLAY**. The app will safely locate nodes matching the plan, enter text, and perform clicks on the screen.
5. Tap **STOP REPLAY** to manually abort.
6. Observe the Debug panel to see exact reasons if Replay fails (e.g., `NODE_NOT_FOUND` or `ACTION_VERIFICATION_FAILED`).
