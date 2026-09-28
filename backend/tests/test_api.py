"""
tests/test_api.py — Automated tests for all 6 endpoints.

IMPORTANT: These tests run in MOCK mode — they NEVER call real Gemini.
This means:
  - Tests are fast (< 1 second total)
  - Tests never burn your API quota
  - Tests work even when offline or when quota is exhausted
  - For real AI testing, use: python test_gemini_live.py

Run with:  pytest tests/ -v
"""
import sys, os

# Force mock mode BEFORE importing anything else.
# This sets GEMINI_API_KEY to empty so ai_client uses mock responses.
os.environ["GEMINI_API_KEY"] = ""

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "flowsStored" in body
    print("✅ /health passed")


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/teach — valid food order
# ═══════════════════════════════════════════════════════════════════════════
def test_teach_food_order():
    payload = {
        "mode": "TEACH",
        "requestId": "test-req-001",
        "appPackage": "com.zomato.android",
        "appName": "Zomato",
        "utterance": "Order a Margherita pizza from Dominos",
        "demonstration": [
            {"action": "SEARCH", "targetText": "Dominos", "success": True},
            {"action": "CLICK", "targetText": "Dominos Restaurant", "success": True},
            {"action": "SEARCH", "targetText": "Margherita pizza", "success": True},
            {"action": "SET_QUANTITY", "value": "1", "success": True}
        ]
    }
    resp = client.post("/v1/teach", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "success"
    assert body["flowId"].startswith("flow_")
    assert body["intent"] == "order_food"
    assert "restaurant" in body["slots"] or "item" in body["slots"]
    print(f"✅ /v1/teach passed. Flow ID: {body['flowId']}")
    return body["flowId"]


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/teach — missing required fields should return 422
# ═══════════════════════════════════════════════════════════════════════════
def test_teach_missing_fields():
    resp = client.post("/v1/teach", json={"utterance": "Order pizza"})
    assert resp.status_code == 422
    print("✅ /v1/teach invalid payload correctly rejected with 422")


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/replay/plan — known food flow
# ═══════════════════════════════════════════════════════════════════════════
def test_replay_known_flow():
    # First teach a flow so matching has something to find
    test_teach_food_order()

    payload = {
        "requestId": "test-req-002",
        "utterance": "Order a Margherita pizza from Dominos",
        "appPackage": "com.zomato.android"
    }
    resp = client.post("/v1/replay/plan", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ["EXECUTE_PLAN", "ASK_USER", "UNKNOWN_INTENT", "STOP"]
    print(f"✅ /v1/replay/plan passed. Decision: {body['decision']}")


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/replay/plan — completely unknown intent (T12)
# ═══════════════════════════════════════════════════════════════════════════
def test_replay_unknown_intent():
    payload = {
        "requestId": "test-req-003",
        "utterance": "Set an alarm for 7am tomorrow",
        "appPackage": "com.android.clock"
    }
    resp = client.post("/v1/replay/plan", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "UNKNOWN_INTENT"
    assert body["flowId"] is None
    print("✅ /v1/replay/plan unknown intent correctly returns UNKNOWN_INTENT (T12)")


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/recovery — sensitive screen triggers STOP (T11)
# ═══════════════════════════════════════════════════════════════════════════
def test_recovery_payment_screen():
    payload = {
        "requestId": "test-req-004",
        "flowId": "flow_abc123",
        "currentStepIndex": 5,
        "expectedAction": {"action": "CLICK", "targetText": "Proceed"},
        "currentUISummary": "Screen shows: Payment page, Enter UPI PIN, Pay Now button",
        "lastActionResult": "navigated to payment screen",
        "failureReason": None
    }
    resp = client.post("/v1/recovery", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "STOP"
    assert body["confidence"] == 1.0
    print("✅ /v1/recovery payment screen returns STOP with confidence 1.0 (T11)")


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/step-result — logging endpoint
# ═══════════════════════════════════════════════════════════════════════════
def test_step_result():
    payload = {
        "requestId": "test-req-005",
        "flowId": "flow_abc123",
        "stepId": 2,
        "action": {"action": "CLICK", "targetText": "Dominos Restaurant"},
        "success": True,
        "observedState": "restaurant menu page loaded"
    }
    resp = client.post("/v1/step-result", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["acknowledged"] is True
    print("✅ /v1/step-result passed")


# ═══════════════════════════════════════════════════════════════════════════
# POST /v1/flows/match — standalone matching
# ═══════════════════════════════════════════════════════════════════════════
def test_flows_match():
    test_teach_food_order()  # ensure a flow exists
    payload = {
        "requestId": "test-req-006",
        "utterance": "I want to order some pizza from Dominos"
    }
    resp = client.post("/v1/flows/match", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "matched" in body
    assert "decision" not in body  # flows/match returns its own schema
    print(f"✅ /v1/flows/match passed. Matched: {body['matched']}")
