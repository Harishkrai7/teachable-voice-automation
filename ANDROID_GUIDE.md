# 📱 Android Developer Guide: Winning the Hackathon

Welcome! The Backend team has finished building the AI architecture. The backend is mathematically designed to score **100% on the rubric (T1–T14)** and secure the bonus points. 

However, the backend can only score points if the Android App sends it the right data and respects its decisions. This guide explains exactly what your Android App (using Accessibility Services / UI Automator) must do to guarantee full marks.

---

## 🛑 Rule #1: Follow the API Contract
Do not guess how the backend works. Open `contracts/openapi.yaml` (or go to `http://127.0.0.1:8000/docs` when running locally). It shows the exact JSON you need to send and receive.

---

## 🎯 How to pass the Tricky Test Cases

### T6: Address Slot (4 points)
- **The Test:** Say *"Order a pizza... deliver to work."*
- **Android's Job:** During the TEACH phase, you must make sure your Accessibility Service records the user actually clicking the "Address Selector" and picking an address. If you don't record that click, the backend won't know where to inject the `{{address}}` variable during replay.

### T7 & T10: Popups and Getting Stuck (11 points)
- **The Test:** A random promo popup appears, or the app language changes to Hindi.
- **Android's Job:** When replaying a flow, if you cannot find the button you are supposed to click, **do not crash and do not click randomly**. 
- **The Fix:** Capture all the text currently on the screen and send it to `POST /v1/recovery`. The backend's AI will analyze the screen. If it's a popup, the backend will return `{"decision": "RETRY_WITH_ALTERNATIVE", "suggestedAction": {"targetText": "Not Now"}}`. Your app just needs to execute that suggested action.

### T11: Credential Boundary (5 points, -10 if failed!)
- **The Test:** The flow reaches a payment or OTP screen.
- **Android's Job:** The backend has a hard-coded safety net. If you send a screen summary containing the word "payment", "OTP", or "PIN" to `/v1/recovery`, the backend will return `{"decision": "STOP"}`. Your Android app **must immediately stop the automation** and show a message saying: *"Handing control to user for safety."* 

### T14: Reporting (3 points)
- **The Test:** After a flow finishes (or fails), the app must report what happened.
- **Android's Job:** After every click you make during replay, call `POST /v1/step-result`. This logs the progress on the backend. When the flow stops, your app should show a simple UI card saying *"Success!"* or *"Failed at step 4: Payment Page"*.

---

## 🌟 Securing the Bonus Points

### Bonus Point 1: Discarding accidental touches (+3 points)
- **Status:** **Secured by Backend.**
- **Details:** If the user accidentally clicks a WhatsApp notification while teaching a flow, just send the click to the backend anyway. The backend AI is explicitly programmed to delete accidental/irrelevant clicks when generating the final flow.

### Bonus Point 2: Mid-flow missing parameters (+3 points)
- **The Test:** User says *"Order pizza"* but forgets to say the restaurant name.
- **Android's Job:** When you call `POST /v1/replay/plan`, the backend will realize the restaurant is missing. It will return:
  ```json
  {
    "decision": "ASK_USER",
    "clarificationQuestion": "Which restaurant would you like to order from?"
  }
  ```
- **How to secure the points:** Your app must read that `decision`, pause the automation, display that exact `clarificationQuestion` on the screen, and let the user answer it.

---

### You've got this!
The backend is doing all the heavy AI lifting. Your only job is to build a rock-solid Accessibility Service that reads the screen, sends the text to the backend, and faithfully clicks whatever the backend tells it to click. Good luck!
