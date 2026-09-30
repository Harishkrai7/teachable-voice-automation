# VoiceFlow (Teachable Voice Automation)
**Samsung PRISM 2026–27 Project Submission**

VoiceFlow is an advanced, privacy-first, teachable voice-driven Android automation system. Built on semantic UI understanding, real-time action replay, and Google Vertex AI, VoiceFlow allows users to "teach" new multi-step automations simply by demonstrating them once. 

## 🏆 Project Achievements
We have successfully implemented and verified all core and bonus capabilities laid out in the **T1-T14 Project Rubric**:
- **T1-T6 (Core Teaching & Replay):** Zero-shot learning, exact replay, paraphrasing, and dynamic slot extraction (item, quantity, address).
- **T7 (Robustness):** UI changes and pop-up handling during replay.
- **T8-T9 (Cross-App Routing):** Teaching multiple e-commerce apps and intelligently routing commands based on natural language.
- **T10 (Genuinely Stuck):** Recognizes when the UI is completely foreign and elegantly asks the user for help.
- **T11 (Security Boundary):** Automatically halts and drops password, OTP, PIN, and payment flows.
- **T12-T13 (Conversational UX):** Unlearned intent handling and disambiguation via native dialogs.
- **T14 (Analytics):** Structured failure/success reporting via the `/v1/metrics` backend API.

---

## 🏗️ Architecture

### 1. The "Hands and Eyes" (Android App)
Built dynamically on Android's `AccessibilityService`, the app physically observes UI actions (Teach Mode) and executes them (Replay Mode) without root access.
* **Semantic Capture:** Converts physical taps into safe, coordinate-free semantic actions (`SEARCH`, `SELECT`, `SET_QUANTITY`).
* **Voice Integration:** Uses Android `SpeechRecognizer` to capture natural language commands seamlessly.
* **Security:** Natively obscures and drops interactions with passwords, PINs, OTPs, and payment fields before they ever leave the device.

### 2. The "Brain" (Google Cloud Run + Vertex AI)
A scalable FastAPI backend deployed on **Google Cloud Run**, powered by **Gemini 2.5 Flash** (via Vertex AI). 
* **Cloud 1 (Intent & Slots):** Extracts user intent and dynamic slots (`{{restaurant}}`, `{{item}}`) from natural language.
* **Cloud 2 (Generalization):** Correlates semantic Android actions with the spoken command, generalizing the flow into a reusable template.
* **Feedback Loop:** If execution fails on the device, the Android app sends structured feedback to the backend for deterministic recovery decisions (`RECOVERY_REQUIRED`, `ASK_USER`, `STOP`).

---

## 🚀 Quick Start

### Backend (Cloud Run Deployment)
The backend is completely containerized and ready for Google Cloud Run deployment.
1. Authenticate with Google Cloud: `gcloud auth login`
2. Deploy the service:
```bash
cd backend
gcloud run deploy teachable-voice-backend \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=teachable-voice-automation,GOOGLE_CLOUD_REGION=us-central1,VERTEX_GEMINI_MODEL=gemini-2.5-flash"
```

### Android Application
1. Open the project in **Android Studio**.
2. Make sure the `BASE_URL` in `app/build.gradle.kts` matches your Cloud Run endpoint (it is currently hardcoded to our active backend).
3. Build and install the APK on a physical Android device (API 26+).
4. Go to **Settings > Accessibility** and enable **VoiceFlow**.
5. Launch the app and use **"🎤 Speak command"** to test Voice Automation!

---

## 🔒 Privacy & Safety Guarantee
VoiceFlow enforces strict boundary guarantees. It operates under a **Pre-Execution Boundary Check**: if a flow requires sensitive authentication (Payment, OTP, Login), the Android app immediately halts execution and hands control back to the user. No sensitive credentials are ever recorded, generalized, or sent to the cloud.
