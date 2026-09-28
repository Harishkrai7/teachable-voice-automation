# Teachable Voice Automation

Teachable voice-driven Android automation powered by semantic UI understanding, action replay, and Gemini AI.

This repository holds the code for a Samsung PRISM 2026–27 project: an advanced, safe voice-automation pipeline that can be "taught" new flows dynamically simply by demonstrating them once.

## Project Structure
- **/app**: The Android application containing the `AccessibilityService` that acts as the "eyes and hands". It observes UI actions (Teach Mode) and executes them (Replay Mode).
- **/backend**: The FastAPI Google Cloud backend that acts as the "brain". It extracts intents and slots from voice commands (Cloud 1), generalizes recorded UI flows, and maps learned flows to new voice instructions (Cloud 2).

## Key Capabilities

1. **Teach Mode**: Open an app and demonstrate an action (e.g., searching for a restaurant and ordering food). The Android `AccessibilityService` intercepts physical clicks and typing and converts them into safe, coordinate-free semantic actions (e.g. `SEARCH`, `SELECT`, `SET_QUANTITY`).
2. **AI Flow Generalization (Cloud 2)**: The backend correlates the semantic actions with a spoken command, substituting literal names with variable slots (`{{restaurant}}`, `{{item}}`). 
3. **Replay Engine**: Ask the assistant a newly paraphrased command. The system pulls the matching learned flow, injects new slot variables, and executes the sequence dynamically on Android, verifying each UI state shift natively using `ActionVerifier`.
4. **Strict Safety Boundary**: 
   - Android natively drops and obscures interactions with passwords, PINs, OTPs, and payment fields.
   - Cloud AI also enforces a pre-execution boundary, actively returning `STOP` if a flow triggers a sensitive domain.
5. **Deterministic AI Feedback Loop**: If an execution physically fails on the device (e.g., `NODE_NOT_FOUND`), Android immediately halts the sequence and returns structured feedback to the Cloud (`/v1/feedback`) for deterministic recovery decisions like `RECOVERY_REQUIRED` or `ASK_USER`.

## Documentation
- [Architecture Details](ARCHITECTURE.md)
- [Android Teach Mode](ANDROID_TEACH_MODE.md)
- [Android Replay Engine](ANDROID_REPLAY.md)
- [Backend API Contract](backend/API_CONTRACT.md)
- [Flow Model Rules](FLOW_MODEL.md)
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md)
- [Demo Script](DEMO_SCRIPT.md)

## Quick Start

### Backend
1. Navigate to `backend/`.
2. Configure `.env` with your `GEMINI_API_KEY`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Run locally: `fastapi dev app/main.py`.

### Android
1. Open the project in Android Studio.
2. Build and run on an Emulator or Device.
3. Enable the **Teachable Voice Automation Service** in your Android Accessibility Settings.
4. Use the in-app debug controls to `START TEACH`, `STOP TEACH`, and test `REPLAY`.
