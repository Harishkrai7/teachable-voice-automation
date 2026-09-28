# Flow Model (Cloud 2 Semantic Reasoning)

This document outlines the core concepts of the "teachable" flow representation inside Cloud 2. The Cloud 2 layer converts concrete physical demonstrations on Android into abstract, semantic, and reusable execution plans.

## 1. Concrete Demonstration
When a user manually demonstrates a task on Android, the Accessibility Service observes a series of **Concrete Actions**. 
These actions represent exact strings interacted with on the screen.
Example:
- `SEARCH "Dominos"`
- `SEARCH "Margherita Pizza"`
- `SET_QUANTITY "1"`

## 2. Parameterized Slot
Cloud 1 extracts structured semantic slots from the user's voice command:
`utterance`: "Order a Margherita pizza from Dominos"
- `restaurant`: "Dominos"
- `item`: "Margherita Pizza"
- `quantity`: 1

## 3. Generalized Flow
Cloud 2 takes the Concrete Actions and the Parameterized Slots, and replaces exact occurrences with `{{slot_name}}` templates. This creates a reusable **Generalized Flow**.
Example:
- `SEARCH "{{restaurant}}"`
- `SEARCH "{{item}}"`
- `SET_QUANTITY "{{quantity}}"`

## 4. Flow Matching
When a new voice command (e.g. "Get me a Margherita from Pizza Hut") is received:
1. Cloud 1 extracts the intent (`order_food`) and the slots (`restaurant=Pizza Hut`, `item=Margherita`).
2. Cloud 2 searches its database for a stored flow with the matching `intent` and `app`.
3. If exactly one flow matches, it proceeds to substitution.
4. If multiple match, the system must return `ASK_USER` to disambiguate.
5. If none match, it returns `NOT_LEARNED`.

## 5. Parameter Substitution
Cloud 2 takes the Generalized Flow and injects the newly extracted slots:
- `SEARCH "{{restaurant}}"` -> `SEARCH "Pizza Hut"`
- `SEARCH "{{item}}"` -> `SEARCH "Margherita"`

## 6. Clarification
If the Generalized Flow requires a slot (e.g. `{{quantity}}`) but the new voice command did not provide one, Cloud 2 aborts the execution and returns an `ASK_USER` response requesting the missing information.

## 7. Safety Boundary
To prevent malicious automation, every generalized flow enforces a strict `stopBefore` safety boundary. 
The system automatically halts and returns a `STOP` instruction if any action involves:
- `PAYMENT`
- `OTP`
- `PASSWORD`
- `PIN`
In these instances, control is immediately handed back to the user to manually complete the sensitive action.
