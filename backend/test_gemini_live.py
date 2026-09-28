"""
Full end-to-end test of real Gemini AI integration.
Run with: .\venv\Scripts\python.exe test_gemini_live.py
"""
from dotenv import load_dotenv
load_dotenv()
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import ai_client

print("=" * 60)
print("TEST 1: Food order intent extraction (Zomato)")
print("=" * 60)
result = ai_client.extract_intent_and_slots(
    utterance="Order a Farmhouse pizza from Dominos, quantity 2",
    demonstration=[
        {"action": "SEARCH", "targetText": "Dominos", "success": True},
        {"action": "CLICK", "targetText": "Dominos Restaurant", "success": True},
        {"action": "SEARCH", "targetText": "Farmhouse pizza", "success": True},
        {"action": "SET_QUANTITY", "value": "2", "success": True},
    ]
)
print(f"  Intent    : {result.get('intent')}")
print(f"  Slots     : {result.get('slots')}")
print(f"  Confidence: {result.get('confidence')}")
print(f"  Clarify   : {result.get('clarification')}")
assert result.get("intent") == "order_food", f"Expected order_food, got {result.get('intent')}"
print("  PASSED")

print()
print("=" * 60)
print("TEST 2: Unknown intent (T12 - must NOT run a random flow)")
print("=" * 60)
result2 = ai_client.extract_intent_and_slots(
    utterance="Set an alarm for 7am tomorrow"
)
print(f"  Intent    : {result2.get('intent')}")
print(f"  Confidence: {result2.get('confidence')}")
assert result2.get("intent") == "unknown_intent", f"Expected unknown_intent, got {result2.get('intent')}"
print("  PASSED")

print()
print("=" * 60)
print("TEST 3: Flow generalization")
print("=" * 60)
extraction = {"intent": "order_food", "slots": {"restaurant": "Dominos", "item": "Farmhouse pizza", "quantity": "2"}, "confidence": 0.95}
demo = [
    {"action": "SEARCH", "targetText": "Dominos", "success": True},
    {"action": "CLICK", "targetText": "Dominos Restaurant", "success": True},
    {"action": "SEARCH", "targetText": "Farmhouse pizza", "success": True},
    {"action": "SET_QUANTITY", "value": "2", "success": True},
    {"action": "ADD_TO_CART", "success": True},
]
gen = ai_client.generalize_demonstration("Order Farmhouse pizza from Dominos quantity 2", demo, extraction)
print(f"  Steps     : {len(gen.get('generalizedSteps', []))}")
print(f"  Slots def : {[s['name'] for s in gen.get('slotDefinitions', [])]}")
print(f"  Debug     : {gen.get('debugSummary', '')}")
for s in gen.get("generalizedSteps", []):
    print(f"    {s.get('action')}: target={s.get('targetText')} value={s.get('value')} invariant={s.get('isInvariant')}")
print("  PASSED")

print()
print("=" * 60)
print("TEST 4: Recovery - payment screen STOP (T11)")
print("=" * 60)
rec = ai_client.reason_recovery(
    current_ui_summary="Screen shows: Pay Now button, Enter UPI PIN, payment page",
    expected_action={"action": "CLICK", "targetText": "Proceed"},
    failure_reason=None
)
print(f"  Decision  : {rec.get('decision')}")
print(f"  Reason    : {rec.get('reason')}")
assert rec.get("decision") == "STOP", f"Expected STOP, got {rec.get('decision')}"
print("  PASSED")

print()
print("=" * 60)
mode = "REAL GEMINI AI" if not ai_client.USE_MOCK else "MOCK MODE"
print(f"ALL TESTS PASSED - Running in {mode}")
print("=" * 60)
