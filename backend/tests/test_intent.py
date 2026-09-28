import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.models.schemas import IntentExtractResponse, Slots

client = TestClient(app)

def mock_gemini_extract(request):
    utterance = request.utterance
    if "Margherita pizza" in utterance:
        return IntentExtractResponse(
            intent="order_food",
            slots=Slots(restaurant="Dominos", item="Margherita Pizza", quantity=1, address=None)
        )
    elif "2 burgers" in utterance:
        return IntentExtractResponse(
            intent="order_food",
            slots=Slots(restaurant="McDonald's", item="burgers", quantity=2, address=None)
        )
    elif "Nike Air Max" in utterance:
        return IntentExtractResponse(
            intent="add_to_cart",
            slots=Slots(restaurant=None, item="Nike Air Max", quantity=1, address=None)
        )
    elif "flight" in utterance:
        return IntentExtractResponse(
            intent="unknown_intent",
            slots=Slots()
        )
    elif "pizza" in utterance:
        return IntentExtractResponse(
            intent="order_food",
            slots=Slots(restaurant=None, item="pizza", quantity=None, address=None)
        )
    raise Exception("Mock error")

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_order_pizza_intent(mock_process):
    response = client.post("/v1/intent/extract", json={"utterance": "Order a Margherita pizza from Dominos", "currentApp": "Zomato"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "order_food"
    assert data["slots"]["restaurant"] == "Dominos"
    assert data["slots"]["item"] == "Margherita Pizza"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_buy_burgers_intent(mock_process):
    response = client.post("/v1/intent/extract", json={"utterance": "Buy 2 burgers from McDonald's", "currentApp": "Zomato"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "order_food"
    assert data["slots"]["quantity"] == 2

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_add_to_cart_intent(mock_process):
    response = client.post("/v1/intent/extract", json={"utterance": "Add Nike Air Max to my Amazon cart", "currentApp": "Amazon"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "add_to_cart"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_unknown_intent(mock_process):
    response = client.post("/v1/intent/extract", json={"utterance": "Book me a flight to Delhi", "currentApp": "MakeMyTrip"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "unknown_intent"

@patch("app.main.process_intent_extraction", side_effect=mock_gemini_extract)
def test_missing_slot_intent(mock_process):
    response = client.post("/v1/intent/extract", json={"utterance": "Order pizza", "currentApp": "Zomato"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "order_food"
    assert data["slots"]["restaurant"] is None
    assert data["slots"]["item"] == "pizza"

def test_empty_utterance():
    response = client.post("/v1/intent/extract", json={"utterance": "", "currentApp": "Zomato"})
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "EMPTY_UTTERANCE"

def test_malformed_json():
    # Sending string instead of JSON object
    response = client.post("/v1/intent/extract", data="invalid json")
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"
