# Teachable Voice Automation - Demo Script

**Estimated Duration:** 5 Minutes

## 0:00–0:30: Problem Statement
"Voice assistants today are rigid. If they don't have an explicitly coded integration with an app like Dominos, they can't help you order food. Teachable Voice Automation solves this by allowing users to physically teach the assistant how to use any app just once. The 'Brain' in Google Cloud observes the actions, generalizes them, and remembers them for the future."

## 0:30–1:15: Explain TEACH Mode
"TEACH mode is where the magic happens. Android acts as the eyes and hands. Using an Accessibility Service, it monitors what the user is doing on the screen and translates coordinates into semantic actions—like SEARCH, SELECT, and SET_QUANTITY. It strips away all sensitive information like passwords or payments immediately."

## 1:15–2:00: Teach a New Flow
*Action: Tap START TEACH in the app.*
"Let's teach it how to order pizza. I'll open my shopping app, search for 'Dominos', select the 'Dominos Restaurant', search for 'Margherita Pizza', set the quantity to '1', and click 'Add to Cart'."
*Action: Tap STOP TEACH.*
"Android now packages this semantic sequence and securely sends it to Cloud 1."

## 2:00–2:30: Show Cloud 1 Intent & Slot Extraction
"Cloud 1 is powered by Gemini. It looks at the user's initial command and extracts the core Intent and Slots. In this case, Intent: `order_food`. Slots: `restaurant=Dominos`, `item=Margherita Pizza`, `quantity=1`."

## 2:30–3:15: Show Cloud 2 Generalized Flow
"Cloud 2 takes those extracted slots and maps them against the recorded UI actions. It realizes that when the user typed 'Dominos', they meant the `{{restaurant}}` slot. It generalizes the physical clicks into a reusable JSON template that can now accept any restaurant or item."

## 3:15–4:00: Replay using Changed Parameters
*Action: Type "Order me 2 Margherita pizzas from Pizza Hut" in the app.*
"Now for the real test. We taught it Dominos, but let's ask for Pizza Hut and change the quantity to 2. Let's see what happens."
*Action: Tap REPLAY CLOUD, then START REPLAY.*
"Cloud 2 successfully substitutes `Pizza Hut` and `2` into the generalized flow. Android receives this plan and begins executing it."

## 4:00–4:30: Show Verification
"Notice how the ReplayEngine doesn't just blindly click. After typing 'Pizza Hut', the `ActionVerifier` inspects the accessibility tree to confirm 'Pizza Hut' is actually on the screen before proceeding."

## 4:30–5:00: Show Safety Boundary / Failure Handling
"What if we try something malicious? Let's ask it to 'Enter my payment details'."
*Action: Type "Enter my payment details" and run Replay.*
"Cloud 2 immediately triggers the Safety Boundary because it touches payment. It sends a `STOP` command. Even if Cloud 2 missed it, the Android `ReplayEngine` has a native guard that refuses to interact with password fields. Finally, if a UI element goes missing, Android submits a Feedback Payload to `/v1/feedback`, and Cloud cleanly decides to request `RECOVERY_REQUIRED`. It's completely safe and deterministic."
