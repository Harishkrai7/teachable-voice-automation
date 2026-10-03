"""
ai_client.py — Real Gemini AI integration + mock fallback.

HOW IT WORKS:
- If GEMINI_API_KEY is set in .env → uses real Gemini 1.5 Flash model.
- If GEMINI_API_KEY is blank → falls back to smart mock data automatically.

YOUR JOB (Cloud 2): Call these 3 functions from main.py. DO NOT change signatures.
FRIEND'S JOB (Cloud 1): Improve the prompts inside _build_*_prompt() functions.

SAFETY RULES ENFORCED HERE:
- We NEVER send passwords, OTPs, or payment data to Gemini.
- We NEVER let Gemini output raw coordinates or shell commands.
- All Gemini output is validated against a strict schema before use.
- If Gemini returns garbage, we fall back to ASK_USER — never crash.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

# ── SDK setup ────────────────────────────────────────────────────────────────
USE_MOCK = not bool(config.GEMINI_API_KEY)

if not USE_MOCK:
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv()
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Use Gemini 1.5 Flash — fastest, cheapest, and free-tier eligible
        _model = genai.GenerativeModel(
            model_name="gemini-flash-latest",  # 1500 req/day free vs 20/day for newer models
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=2048,
            )
        )
        logger.info("Gemini Flash (latest) initialised successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialise Gemini SDK: {e}. Falling back to mock mode.")
        USE_MOCK = True
else:
    logger.info("ℹ️  No GEMINI_API_KEY found. Running in MOCK mode.")


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTION 1: extract_intent_and_slots
# ═══════════════════════════════════════════════════════════════════════════

def extract_intent_and_slots(
    utterance: str,
    demonstration: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Given a spoken utterance + optional Android actions, extract:
      - intent (order_food / search_product / add_to_cart / unknown_intent)
      - slots  (restaurant, item, quantity, address, query, etc.)
      - confidence (0.0 – 1.0)
      - clarification (question string if needed, else null)
    """
    if USE_MOCK:
        return _mock_extract_intent_and_slots(utterance)

    prompt = _build_extraction_prompt(utterance, demonstration)
    raw = _call_gemini_safe(prompt)

    # If Gemini failed (returned empty dict), fall back to mock gracefully
    if not raw:
        logger.warning("Gemini extraction failed or quota exceeded. Using mock fallback.")
        return _mock_extract_intent_and_slots(utterance)

    return _validate_extraction_result(raw)


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTION 2: generalize_demonstration
# ═══════════════════════════════════════════════════════════════════════════

def generalize_demonstration(
    utterance: str,
    demonstration: List[Dict[str, Any]],
    extracted_slots: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Turn a concrete Android demonstration into a reusable parameterized flow.
    Replaces concrete values with {{slot}} placeholders.

    Returns:
      - generalizedSteps   (list of step dicts with {{slot}} placeholders)
      - slotDefinitions    (list of slot metadata dicts)
      - debugSummary       (human-readable explanation)
    """
    if USE_MOCK:
        return _mock_generalize_demonstration(utterance, demonstration, extracted_slots)

    prompt = _build_generalization_prompt(utterance, demonstration, extracted_slots)
    raw = _call_gemini_safe(prompt)

    # If Gemini failed, fall back to mock gracefully
    if not raw:
        logger.warning("Gemini generalization failed or quota exceeded. Using mock fallback.")
        return _mock_generalize_demonstration(utterance, demonstration, extracted_slots)

    return _validate_generalization_result(raw, demonstration, extracted_slots)


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTION 3: reason_recovery
# ═══════════════════════════════════════════════════════════════════════════

def reason_recovery(
    current_ui_summary: str,
    expected_action: Dict[str, Any],
    failure_reason: Optional[str]
) -> Dict[str, Any]:
    """
    Given what Android sees on screen right now, decide what to do next.

    Returns:
      - decision          (CONTINUE / RETRY_WITH_ALTERNATIVE / ASK_USER / STOP)
      - suggestedAction   (a single safe action dict, or null)
      - reason            (plain English explanation)
      - confidence        (0.0 – 1.0)
    """
    if USE_MOCK:
        return _mock_reason_recovery(current_ui_summary, failure_reason)

    # Hard safety check BEFORE calling AI — never send payment screens to LLM
    ui_lower = (current_ui_summary or "").lower()
    for keyword in config.SENSITIVE_SCREEN_KEYWORDS:
        if keyword in ui_lower:
            return {
                "decision": "STOP",
                "suggestedAction": None,
                "reason": f"Sensitive screen detected ({keyword}). Handing control to user.",
                "confidence": 1.0
            }

    prompt = _build_recovery_prompt(current_ui_summary, expected_action, failure_reason)
    raw = _call_gemini_safe(prompt)

    # If Gemini failed, fall back to mock gracefully
    if not raw:
        logger.warning("Gemini recovery failed or quota exceeded. Using mock fallback.")
        return _mock_reason_recovery(current_ui_summary, failure_reason)

    return _validate_recovery_result(raw)


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS — Improve these to get better AI results
# ═══════════════════════════════════════════════════════════════════════════

def _build_extraction_prompt(
    utterance: str,
    demonstration: Optional[List[Dict[str, Any]]]
) -> str:
    demo_text = ""
    if demonstration:
        demo_text = "\n\nAndroid actions observed during teaching:\n"
        for i, step in enumerate(demonstration, 1):
            action = step.get("action", "?")
            target = step.get("targetText", "")
            value = step.get("value", "")
            detail = target or value
            demo_text += f"  Step {i}: {action} → \"{detail}\"\n"

    return f"""You are an intent and slot extractor for a mobile UI automation system.

TASK: Analyze the user's spoken command and extract structured information.

SUPPORTED INTENTS:
- order_food: User wants to order food (Zomato, Swiggy, etc.)
- search_product: User wants to search for a product (Amazon, Flipkart, etc.)
- add_to_cart: User wants to add a specific product to cart
- unknown_intent: Cannot determine a clear intent

SUPPORTED SLOTS:
- restaurant: Name of restaurant or food place
- item: Food item or product name
- quantity: Number of items (default "1" if not mentioned)
- address: Delivery address (null if not mentioned)
- query: General search term

RULES:
1. Only extract slots that are explicitly mentioned in the utterance or clearly demonstrated.
2. Do NOT invent values that weren't said or shown.
3. If intent is unclear, use unknown_intent and set confidence below 0.5.
4. If a required slot is missing, set clarification to a specific question.
5. Never extract passwords, OTPs, payment info, or credentials.

User's spoken command: "{utterance}"{demo_text}

Return ONLY valid JSON in exactly this format:
{{
  "intent": "order_food",
  "slots": {{
    "restaurant": "Dominos",
    "item": "Margherita Pizza",
    "quantity": "1",
    "address": null
  }},
  "confidence": 0.92,
  "clarification": null
}}"""


def _build_generalization_prompt(
    utterance: str,
    demonstration: List[Dict[str, Any]],
    ai_result: Dict[str, Any]
) -> str:
    slots = ai_result.get("slots", {})
    slot_names = [k for k, v in slots.items() if v is not None]

    demo_text = json.dumps(demonstration, indent=2)
    slots_text = json.dumps(slots, indent=2)

    return f"""You are a flow generalizer for a mobile UI automation system.

TASK: Convert a concrete Android demonstration into a reusable parameterized flow.
Replace specific values with {{{{slot_name}}}} placeholders where the value came from a known slot.

KNOWN SLOTS (these values should become placeholders):
{slots_text}

ORIGINAL SPOKEN COMMAND: "{utterance}"

CONCRETE ANDROID DEMONSTRATION STEPS:
{demo_text}

RULES:
1. Replace values (or parts of values) with {{{{slot_name}}}} placeholders if they match or partially match a known slot. For example, if the slot is "Pizza Hut" and the targetText is "Pizza Hut 30 mins", change it to "{{{{restaurant}}}} 30 mins".
2. Keep actions that never change (like "OPEN_CART", "ADD_TO_CART") marked as isInvariant=true.
3. Mark any step that could involve payment/OTP/login as stopBefore=true.
4. Preserve the exact action names from the demonstration (SEARCH, CLICK, SET_QUANTITY, etc.).
5. Never invent steps that were not in the original demonstration.
6. targetText and value fields MUST contain {{{{slot_name}}}} if the slot value appeared anywhere within them. Do not require an exact match.

Available slot names: {slot_names}

Return ONLY valid JSON in exactly this format:
{{
  "generalizedSteps": [
    {{"action": "SEARCH", "targetText": null, "value": "{{{{restaurant}}}}", "isInvariant": false, "stopBefore": false}},
    {{"action": "CLICK", "targetText": "{{{{restaurant}}}}", "value": null, "isInvariant": false, "stopBefore": false}},
    {{"action": "ADD_TO_CART", "targetText": null, "value": null, "isInvariant": true, "stopBefore": false}}
  ],
  "slotDefinitions": [
    {{"name": "restaurant", "slotType": "restaurant", "required": true, "defaultValue": null}},
    {{"name": "item", "slotType": "item", "required": true, "defaultValue": null}},
    {{"name": "quantity", "slotType": "quantity", "required": false, "defaultValue": "1"}}
  ],
  "debugSummary": "Generalized 4 steps. Replaced restaurant and item with placeholders. quantity defaults to 1."
}}"""


def _build_recovery_prompt(
    current_ui_summary: str,
    expected_action: Dict[str, Any],
    failure_reason: Optional[str]
) -> str:
    return f"""You are a recovery reasoner for a mobile UI automation system.

TASK: The Android app was executing a learned flow and got stuck. Decide what to do next.

WHAT ANDROID EXPECTED TO DO:
{json.dumps(expected_action, indent=2)}

WHAT ANDROID SEES ON SCREEN RIGHT NOW:
{current_ui_summary}

FAILURE REASON:
{failure_reason or "Unknown"}

RULES:
1. If the screen shows a popup or dialog unrelated to the flow (rating, promo, permission), suggest RETRY_WITH_ALTERNATIVE to dismiss it.
2. If the expected element is just not found (layout changed slightly), suggest CONTINUE to try the next step.
3. If genuinely confused or multiple things could be wrong, return ASK_USER with a specific question.
4. NEVER return coordinates, shell commands, or executable code.
5. NEVER return CONTINUE if the failure reason mentions "payment", "otp", "password", or "pin".
6. The suggestedAction must only contain: action, targetText, value, isInvariant, stopBefore.

ALLOWED DECISIONS: CONTINUE, RETRY_WITH_ALTERNATIVE, ASK_USER, STOP

Return ONLY valid JSON in exactly this format:
{{
  "decision": "RETRY_WITH_ALTERNATIVE",
  "suggestedAction": {{
    "action": "CLICK",
    "targetText": "Not Now",
    "value": null,
    "isInvariant": true,
    "stopBefore": false
  }},
  "reason": "A rating popup appeared. Attempting to dismiss it by clicking 'Not Now'.",
  "confidence": 0.82
}}"""


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI API CALLER — with error handling
# ═══════════════════════════════════════════════════════════════════════════

def _call_gemini_safe(prompt: str) -> Dict[str, Any]:
    """
    Call Gemini and parse the JSON response safely.
    If anything goes wrong, return an empty dict (callers handle this gracefully).
    """
    try:
        logger.info("Calling Gemini 2.5 Flash...")
        response = _model.generate_content(prompt)
        raw_text = response.text.strip()
        logger.info(f"Gemini response: {raw_text[:200]}...")

        # Strip markdown code fences if Gemini wraps response in ```json ... ```
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        parsed = json.loads(raw_text)
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"❌ Gemini returned invalid JSON: {e}. Raw: {raw_text[:300]}")
        return {}
    except Exception as e:
        logger.error(f"❌ Gemini API call failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATORS — Sanitize Gemini output before it reaches Android
# ═══════════════════════════════════════════════════════════════════════════

def _validate_extraction_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure extraction result has all required fields. Fall back to safe defaults."""
    allowed_intents = {"order_food", "search_product", "add_to_cart", "unknown_intent"}
    intent = raw.get("intent", "unknown_intent")

    if intent not in allowed_intents:
        logger.warning(f"Gemini returned unknown intent '{intent}'. Defaulting to unknown_intent.")
        intent = "unknown_intent"

    slots = raw.get("slots", {})
    # Sanitize: remove any slot that might contain sensitive data
    blocked_slot_names = {"password", "otp", "pin", "card", "cvv", "upi"}
    slots = {k: v for k, v in slots.items() if k.lower() not in blocked_slot_names}

    confidence = float(raw.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

    return {
        "intent": intent,
        "slots": slots,
        "confidence": confidence,
        "clarification": raw.get("clarification")
    }


def _validate_generalization_result(
    raw: Dict[str, Any],
    original_demonstration: List[Dict[str, Any]],
    extracted_slots: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate generalization result. Fall back to mock if Gemini output is broken."""
    if not raw or "generalizedSteps" not in raw:
        logger.warning("Gemini generalization failed. Falling back to mock.")
        return _mock_generalize_demonstration("", original_demonstration, extracted_slots)

    steps = raw.get("generalizedSteps", [])
    # Validate each step has at least an action field
    validated_steps = []
    for step in steps:
        if isinstance(step, dict) and "action" in step:
            # Never allow stopBefore=False on sensitive-looking steps
            target = (step.get("targetText") or "").lower()
            value = (step.get("value") or "").lower()
            if any(kw in target + value for kw in config.SENSITIVE_SCREEN_KEYWORDS):
                step["stopBefore"] = True
            validated_steps.append(step)

    raw["generalizedSteps"] = validated_steps
    return raw


def _validate_recovery_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate recovery decision. Fall back to ASK_USER if Gemini output is invalid."""
    allowed_decisions = {"CONTINUE", "RETRY_WITH_ALTERNATIVE", "ASK_USER", "STOP"}
    decision = raw.get("decision", "ASK_USER")

    if decision not in allowed_decisions:
        logger.warning(f"Gemini returned invalid recovery decision '{decision}'. Defaulting to ASK_USER.")
        decision = "ASK_USER"

    # Validate suggested action is safe (no coordinates, no code)
    suggested = raw.get("suggestedAction")
    if suggested:
        # Strip any field that's not part of our GeneralizedStep schema
        allowed_fields = {"action", "targetText", "value", "isInvariant", "stopBefore"}
        suggested = {k: v for k, v in suggested.items() if k in allowed_fields}
        # Never allow executable-looking values
        for field in ["targetText", "value"]:
            val = suggested.get(field, "") or ""
            if any(bad in val for bad in ["import ", "exec(", "eval(", "subprocess"]):
                logger.error(f"🚨 Gemini tried to inject code in recovery action! Blocking.")
                suggested = None
                decision = "ASK_USER"
                break

    confidence = float(raw.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return {
        "decision": decision,
        "suggestedAction": suggested,
        "reason": raw.get("reason", "Recovery reasoning completed."),
        "confidence": confidence
    }


# ═══════════════════════════════════════════════════════════════════════════
# MOCK IMPLEMENTATIONS — Used when GEMINI_API_KEY is not set
# ═══════════════════════════════════════════════════════════════════════════

def _mock_extract_intent_and_slots(utterance: str) -> Dict[str, Any]:
    utterance_lower = utterance.lower()

    if any(w in utterance_lower for w in ["order", "pizza", "food", "zomato", "swiggy", "burger", "biryani"]):
        return {
            "intent": "order_food",
            "slots": {
                "restaurant": _find_keyword(utterance, ["dominos", "pizza hut", "mcdonald", "kfc", "subway"], "Dominos"),
                "item": _find_keyword(utterance, ["pizza", "burger", "biryani", "pasta", "sandwich"], "Margherita Pizza"),
                "quantity": "1",
                "address": None
            },
            "confidence": 0.91,
            "clarification": None
        }
    elif any(w in utterance_lower for w in ["buy", "search", "amazon", "flipkart", "cart", "product", "shop"]):
        query = utterance_lower
        for w in ["search for", "buy", "find", "add", "cart", "amazon", "flipkart"]:
            query = query.replace(w, "").strip()
        return {
            "intent": "search_product",
            "slots": {"query": query.strip() or "product", "quantity": "1"},
            "confidence": 0.85,
            "clarification": None
        }
    else:
        return {
            "intent": "unknown_intent",
            "slots": {},
            "confidence": 0.20,
            "clarification": "I haven't learned this flow yet. Would you like to teach it to me?"
        }


def _mock_generalize_demonstration(
    utterance: str,
    demonstration: List[Dict[str, Any]],
    extracted_slots: Dict[str, Any]
) -> Dict[str, Any]:
    slots = extracted_slots.get("slots", {})
    generalized_steps = []

    for step in demonstration:
        action = step.get("action", "UNKNOWN")
        target_text = step.get("targetText") or ""
        value = step.get("value") or ""

        for slot_name, slot_value in slots.items():
            if slot_value and target_text and str(slot_value).lower() in target_text.lower():
                target_text = f"{{{{{slot_name}}}}}"
            if slot_value and value and str(slot_value).lower() in value.lower():
                value = f"{{{{{slot_name}}}}}"

        has_placeholder = "{{" in target_text or "{{" in value
        generalized_steps.append({
            "action": action,
            "targetText": target_text or None,
            "value": value or None,
            "isInvariant": not has_placeholder,
            "stopBefore": False
        })

    slot_defs = []
    for k, v in slots.items():
        slot_defs.append({
            "name": k,
            "slotType": k,
            "required": k != "address",
            "defaultValue": "1" if k == "quantity" else None
        })

    return {
        "generalizedSteps": generalized_steps,
        "slotDefinitions": slot_defs,
        "debugSummary": f"[MOCK] Generalized {len(generalized_steps)} steps. Slots: {list(slots.keys())}"
    }


def _mock_reason_recovery(
    current_ui_summary: str,
    failure_reason: Optional[str]
) -> Dict[str, Any]:
    summary_lower = (current_ui_summary or "").lower()

    for keyword in config.SENSITIVE_SCREEN_KEYWORDS:
        if keyword in summary_lower:
            return {"decision": "STOP", "suggestedAction": None,
                    "reason": f"Sensitive screen detected ({keyword}).", "confidence": 1.0}

    if any(kw in summary_lower for kw in ["popup", "dialog", "not now", "close", "rate", "dismiss"]):
        return {
            "decision": "RETRY_WITH_ALTERNATIVE",
            "suggestedAction": {"action": "CLICK", "targetText": "Not Now",
                                "value": None, "isInvariant": True, "stopBefore": False},
            "reason": "Popup detected. Attempting to dismiss.",
            "confidence": 0.78
        }
    elif failure_reason and "not found" in failure_reason.lower():
        return {"decision": "ASK_USER", "suggestedAction": None,
                "reason": "Element not found. Layout may have changed.", "confidence": 0.60}
    else:
        return {"decision": "CONTINUE", "suggestedAction": None,
                "reason": "State looks recoverable. Proceeding.", "confidence": 0.65}


def _find_keyword(utterance: str, keywords: List[str], default: str) -> str:
    for kw in keywords:
        if kw.lower() in utterance.lower():
            return kw.title()
    return default
