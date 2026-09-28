# Architecture Overview: Teachable Voice Automation

## Current Project Structure & Existing Files
Based on the repository inspection, the project currently consists entirely of a frontend Android application built using Kotlin/Java and Gradle. The root directory contains:
- `app/` (Android application source code)
- `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties` (Gradle build configuration files)
- `.gitignore` (Git ignore rules)
- `README.md` (Basic project description)

## What Already Exists
- **Programming Language/Framework**: Kotlin/Java with Android SDK.
- **Backend**: None exists yet.
- **Environment/Configuration**: None for the backend.
- **Google Cloud / AI Integrations**: None implemented.
- **API Schemas & Tests**: None exist.

## What Cloud 1 Needs to Implement (Phase 2-19)
Cloud 1 is responsible for the Python-based backend that handles:
- **Speech Input Contract**: Exposing `/v1/intent/extract` and `/v1/process` endpoints.
- **Intent Classification**: Classifying intents into a strict set (`order_food`, `add_to_cart`, `unknown_intent`).
- **Slot Extraction**: Extracting variables (`restaurant`, `item`, `quantity`, `address`) robustly using Google Gen AI SDK (Gemini API) and Pydantic validation.
- **Error Handling & Security**: Proper API contracts, JSON schema validation, graceful error messaging, logging (without sensitive data), and environment secret management.
- **Dockerization & Testing**: Creating a Dockerfile and unit tests (mocked Gemini calls) to ensure production-readiness for Google Cloud Run.

## What Should Remain Reserved for Cloud 2
Cloud 2's responsibilities must NOT be implemented in this phase. The backend must provide a clean interface to hand off structured JSON to Cloud 2, which will later handle:
- **Flow Generalization**: Understanding how a taught flow applies to a new intent.
- **Flow Matching**: Identifying which pre-taught flow to use based on the extracted intent and slots.
## Cloud 2: Flow Generalization & Intelligence
Cloud 2 takes the output of Cloud 1 and transforms it into reusable execution logic.
- **Flow Generalization (TEACH)**: Replaces hardcoded values in Android demonstration actions with `{{slots}}`.
- **Flow Storage**: Stores learned flows safely in a backend storage system (e.g. JSON/SQLite).
- **Flow Matching**: Deterministically matches incoming intents/apps to stored flows.
- **Parameter Substitution (REPLAY)**: Injects newly extracted slots into generalized flows safely.
- **Recovery/Clarification Reasoning**: Detects missing variables and returns `ASK_USER` instructions.
- **Safety Boundary**: Halts any flows touching `PAYMENT`, `OTP`, `PASSWORD`, or `PIN`.

## How Android Will Communicate with this Service
Android acts as the "eyes and hands" and must not do the heavy reasoning, while Google Cloud is the "brain".

### TEACH Phase (Observation)
1. **TeachSessionManager**: Starts/stops recording semantic user actions via Android `AccessibilityService`.
2. **ActionInterpreter**: Safely maps physical `AccessibilityEvent`s into semantic operations (e.g. text input -> `SEARCH`). Drops sensitive operations natively.
3. Android constructs a semantic `TEACH` JSON request and ships it to Cloud 1/2 for Flow Generalization.

### REPLAY Phase (Execution)
1. **Voice Input**: User speaks an utterance, Android fetches the Replay Plan from `/v1/process`.
2. **ReplayEngine**: Systematically processes semantic steps locally using `AccessibilityService`.
3. **NodeMatcher**: Implements robust confidence scoring against exact, normalized, and descriptive texts to locate the target node safely without guessing.
4. **ActionVerifier**: Verifies every action immediately post-execution (e.g. text populated).
5. **Failure & Safety Boundary**: Instantly halts upon any verification mismatch, missing node, or sensitive field detection, generating structured JSON feedback.
## Final System Architecture
```text
ANDROID
│
├── AccessibilityService
├── TeachSessionManager
├── ActionInterpreter
├── NodeMatcher
├── ReplayEngine
├── ActionVerifier
└── ReplaySessionManager
│
▼
CLOUD 1
│
├── Gemini
└── Intent + Slots
│
▼
CLOUD 2
│
├── Flow Generalization
├── Flow Storage
├── Flow Matching
├── Parameter Substitution
├── Safety
└── Recovery Decision
│
▼
ANDROID
│
▼
UI EXECUTION
```
