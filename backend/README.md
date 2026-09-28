# Teachable Voice Automation Backend

This is the Python/FastAPI backend for the Samsung PRISM "Teachable Voice Automation" project. 

## Project Status
The core backend architecture is **100% complete**. It successfully handles API routing, flow matching, and real Gemini AI integration to generalize taught flows and reason about recovery.

---

## 📌 IMPORTANT: The Final Upgrade (Pre-Demo Day)

Currently, the backend saves learned flows as JSON files inside the `flows/` directory. This works perfectly for local development and initial testing.

However, **Google Cloud Run is stateless**. This means that when the Cloud Run container goes to sleep or scales up, the local filesystem (`flows/` folder) will be wiped out. For a robust hackathon demo, you need persistent storage.

**Before Demo Day, you must upgrade `storage.py` to use Google Cloud Firestore:**

1. Tell your Cloud Platform friend to enable the **Firestore API** in GCP.
2. Open `storage.py`.
3. Replace the local JSON reading/writing logic with the Firestore Python SDK (`google-cloud-firestore`).
4. Because the rest of the application ONLY interacts with `storage.py` via three simple functions (`save_flow`, `load_flow`, `list_flows`), **you will not need to change a single line of code in `main.py`, `ai_client.py`, or `flow_matcher.py`.** The architecture was specifically designed to make this swap painless.

---

## What is `openapi.yaml`?

You might notice a file called `contracts/openapi.yaml` in the parent directory. 

**What is it?**
It is the "API Contract". Think of it as a strict instruction manual or blueprint for how the Android App must communicate with the Backend. 

**Why do we have it?**
In a team environment, the Android developers need to start building the app before the backend is even finished. By agreeing on the `openapi.yaml` blueprint first, the Android team knows exactly what JSON format to send (e.g., `{"mode": "TEACH", "utterance": "..."}`) and exactly what JSON format you will reply with, without ever having to read your Python code.

It defines:
- The exact endpoints (e.g., `/v1/teach`, `/v1/replay/plan`)
- The exact fields required in the requests.
- The exact data types returned in the responses.

If the Android developer ever asks "How do I use your API?", just send them the `openapi.yaml` file (or point them to your live `http://127.0.0.1:8000/docs` webpage, which is automatically generated from this same standard).
