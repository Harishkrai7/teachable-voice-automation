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
- **Recovery/Clarification Reasoning**: Determining what to do if a step fails or if clarification is needed from the user.
- **APIs/Flow Intelligence**: Mapping the extracted slots against the execution plan for the specific Android App.

## How Android Will Communicate with this Service
Android acts as the "eyes and hands" and must not do the heavy reasoning, while Google Cloud is the "brain".
- **Communication Protocol**: Android will send HTTPS POST requests with JSON payloads (e.g., `TEACH` and `REPLAY` modes) to the Cloud Run endpoints (`/v1/intent/extract`, `/v1/process`).
- **Execution Contract**: The backend will process the utterance and return a structured JSON response (Intent and Slots). Android will receive this instruction plan and execute it via its Accessibility Service, subsequently verifying the state. 
- **Constraint**: The Cloud service will never directly control the phone, send screen coordinates, or instruct the app to bypass standard UI elements for sensitive actions (like payments).
