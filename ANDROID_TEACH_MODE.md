# Android Teach Mode (Phase 1 Integration)

This document describes the Android components responsible for observing user interactions, translating them into semantic actions, and constructing a TEACH session for Cloud 2.

## Components

### 1. ConcreteAction
A semantic data class representing a user action, decoupled from explicit screen coordinates.
```kotlin
data class ConcreteAction(
    val action: String, // SEARCH, SELECT, TYPE_TEXT, SET_QUANTITY, etc.
    val target: String?, // "Dominos", "input_field"
    val value: String?, // The typed value or quantity amount
    val packageName: String?, // Application package
    val timestamp: Long?
)
```

### 2. TeachSessionManager
A singleton object managing the lifecycle of the teaching phase.
- `startSession()`: Begins recording actions and clears previous ones.
- `recordAction(action)`: Adds an action. Contains deduplication logic (e.g. debouncing typing into a SEARCH field or multiple clicks on the same item). Also detects application package switches.
- `stopSession()`: Terminates recording and returns the final `ConcreteAction` list for transmission.

### 3. ActionInterpreter
Translates raw `AccessibilityEvent` and `UiNode` trees into `ConcreteAction`s.
- **Search Detection**: Triggers when an `EditText` is modified and context hints at searching.
- **Select Detection**: Triggers on `TYPE_VIEW_CLICKED`. Differentiated from `ADD_TO_CART` by analyzing keywords.
- **Quantity Detection**: Safely catches interactions matching `^[0-9]+$` or containing quantity-related keywords ("increase", "decrease").
- **Sensitive Data Protection**: Explicitly blocks and masks actions interacting with elements hinting at "password", "pin", "otp", "payment". Emits `SENSITIVE_ACTION_BLOCKED`.

### 4. TeachableVoiceService
Android's `AccessibilityService` subclass. During active teaching sessions, it listens to UI events, reads the accessibility hierarchy securely, passes them to `ActionInterpreter`, and ultimately routes the resultant semantic actions to `TeachSessionManager`.

### 5. Debug UI
The main Android application acts as a test bed to start, stop, and clear TEACH sessions, as well as visualizing the semantic actions recorded in real-time. Once teaching stops, the sequence is mapped into the `TeachRequest` and uploaded to the mock `v1/process` endpoint.
