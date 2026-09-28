# Android Replay Engine (Phase 2 Integration)

This document describes the Android components responsible for executing a Generalized Flow (Replay Plan) on the real Android UI, enforcing strict semantic checks, confidence scoring, and verifying actions.

## Components

### 1. ReplaySessionManager
Maintains the state machine of the replay execution.
- States: `IDLE`, `RUNNING`, `WAITING_FOR_UI`, `FAILED`, `COMPLETED`, `STOPPED`.
- Tracks the active `flowId`, the list of actions, the current index, and handles failure assignments.

### 2. NodeMatcher
Translates a semantic target (e.g., "Dominos Restaurant") into a physical `AccessibilityNodeInfo`.
- **Confidence Scoring**: Evaluates exact text, content description, normalized text, and resource IDs against the candidate node. Returns `HIGH`, `MODERATE`, `LOW`, or `NONE`.
- **Ambiguity Guard**: If multiple nodes tie with the exact same high score, it returns null (ambiguous match) rather than clicking blindly.
- **Normalization**: Safely strips whitespaces and normalizes case to ensure robust matching.

### 3. ReplayEngine
The core executor running on a background coroutine.
- **Pulls next action** from `ReplaySessionManager`.
- **Enforces Safety Bounds**: Halts on sensitive interactions (PAYMENT, OTP, PASSWORD).
- **Finds Target**: Polls the UI using `NodeMatcher` (up to a 5-second timeout).
- **Performs Action**: Translates semantic verbs (`SEARCH`, `SELECT`, `SET_QUANTITY`) into raw `AccessibilityNodeInfo` manipulations (`ACTION_CLICK`, `ACTION_SET_TEXT`).
- **Verifies**: After interacting, pauses and delegates to `ActionVerifier`.

### 4. ActionVerifier
Provides post-action verification to ensure the screen responded correctly.
- Ensures search text propagated correctly into editable fields.
- Verifies cart quantities changed.
- If verification fails, the replay terminates immediately rather than continuing a broken flow.

### 5. Failure Feedback Loop
When a replay fails (due to `NODE_NOT_FOUND`, `UI_STATE_TIMEOUT`, `ACTION_VERIFICATION_FAILED`, etc.), a JSON contract is prepared:
```json
{
    "flowId": "food_order_001",
    "actionIndex": 2,
    "failedAction": {
        "action": "SELECT",
        "target": "Margherita Pizza"
    },
    "reason": "NODE_NOT_FOUND",
    "currentApp": "com.example.app"
}
```
This payload is currently mapped locally, establishing the contract for future Cloud AI Recovery.
