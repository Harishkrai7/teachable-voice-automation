import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.models.schemas import IntentExtractResponse, Slots
import os
import json

client = TestClient(app)

# Helper mock for Gemini
def mock_gemini_extract(request):
    utterance = request.utterance.lower()
    if "margherita pizza" in utterance:
        if "pizza hut" in utterance:
            return IntentExtractResponse(
                intent="order_food",
                slots=Slots(restaurant="Pizza Hut", item="Margherita Pizza", quantity=1 if "one" in utterance or " a " in utterance else 2 if "2" in utterance else None, address=None)
            )
        return IntentExtractResponse(
            intent="order_food",
            slots=Slots(restaurant="Dominos", item="Margherita Pizza", quantity=1 if "one" in utterance or " a " in utterance else 2 if "2" in utterance else None, address=None)
        )
    elif "flight" in utterance:
        return IntentExtractResponse(
            intent="unknown_intent",
            slots=Slots()
        )
    elif "something" in utterance:
        return IntentExtractResponse(
            intent="order_food",
            slots=Slots(restaurant="Dominos", item=None, quantity=None, address=None)
        )
    raise Exception("Mock error")

@pytest.fixture(autouse=True)
def clean_storage():
    storage_file = os.path.join(os.path.dirname(__file__), "../app/services/flows.json")
    if os.path.exists(storage_file):
        os.remove(storage_file)
    yield
    if os.path.exists(storage_file):
        os.remove(storage_file)

def do_teach():
    req = {
        "mode": "TEACH",
        "utterance": "Order a Margherita pizza from Dominos on Zomato",
        "actions": [
            {"action": "SEARCH", "target": "Dominos"},
            {"action": "CLICK", "target": "Dominos Restaurant"},
            {"action": "SEARCH", "target": "Margherita Pizza"},
            {"action": "SET_QUANTITY", "value": "1"},
            {"action": "ADD_TO_CART"}
        ],
        "app": "Zomato"
    }
    
    resp = client.post("/v1/process", json=req)
    assert resp.status_code == 200
    data = resp.json()
    return data

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_teach_and_store_flow(mock_extract):
    data = do_teach()
    assert data["success"] is True
    assert data["mode"] == "TEACH"
    assert data["flow"]["intent"] == "order_food"
    
    # Verify generalization
    steps = data["flow"]["steps"]
    assert steps[0]["target"] == "{{restaurant}}"
    assert steps[2]["target"] == "{{item}}"
    assert steps[3]["value"] == "{{quantity}}"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_replay_exact_flow(mock_extract):
    # Setup flow first
    do_teach()
    
    # Replay
    req = {
        "mode": "REPLAY",
        "utterance": "Get me a Margherita pizza from Dominos",
        "currentApp": "Zomato"
    }
    resp = client.post("/v1/process", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "REPLAY"
    
    actions = data["actions"]
    assert actions[0]["target"] == "Dominos"
    assert actions[2]["target"] == "Margherita Pizza"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_replay_changed_quantity(mock_extract):
    do_teach()
    
    req = {
        "mode": "REPLAY",
        "utterance": "Get me 2 Margherita pizzas from Dominos",
        "currentApp": "Zomato"
    }
    resp = client.post("/v1/process", json=req)
    assert resp.status_code == 200
    data = resp.json()
    actions = data["actions"]
    assert actions[3]["value"] == "2"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_replay_changed_restaurant(mock_extract):
    do_teach()
    
    req = {
        "mode": "REPLAY",
        "utterance": "Get me a Margherita pizza from Pizza Hut",
        "currentApp": "Zomato"
    }
    resp = client.post("/v1/process", json=req)
    assert resp.status_code == 200
    data = resp.json()
    actions = data["actions"]
    assert actions[0]["target"] == "Pizza Hut"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_unknown_intent(mock_extract):
    req = {
        "mode": "REPLAY",
        "utterance": "Book me a flight to Delhi",
        "currentApp": "MakeMyTrip"
    }
    resp = client.post("/v1/process", json=req)
    data = resp.json()
    assert data["type"] == "NOT_LEARNED"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_missing_slot_ask_user(mock_extract):
    do_teach()
    
    req = {
        "mode": "REPLAY",
        "utterance": "Order something from Dominos",
        "currentApp": "Zomato"
    }
    resp = client.post("/v1/process", json=req)
    data = resp.json()
    assert data["type"] == "ASK_USER"
    assert "item" in data["question"]

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_safety_boundary(mock_extract):
    req = {
        "mode": "TEACH",
        "utterance": "Order a Margherita pizza from Dominos on Zomato",
        "actions": [
            {"action": "SEARCH", "target": "Dominos"},
            {"action": "PAYMENT", "target": "Credit Card"}
        ],
        "app": "Zomato"
    }
    
    resp = client.post("/v1/process", json=req)
    data = resp.json()
    assert data["type"] == "STOP"
    assert data["reason"] == "SENSITIVE_ACTION"
