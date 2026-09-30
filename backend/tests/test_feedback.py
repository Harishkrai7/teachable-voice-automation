from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_valid_feedback():
    payload = {
        "flowId": "food_order_001",
        "actionIndex": 2,
        "failedAction": {
            "action": "SELECT",
            "target": "Margherita Pizza"
        },
        "reason": "NODE_NOT_FOUND",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RECOVERY_REQUIRED"
    assert data["flowId"] == "food_order_001"
    assert data["actionIndex"] == 2
    assert data["reason"] == "NODE_NOT_FOUND"

def test_missing_flow_id():
    payload = {
        "actionIndex": 2,
        "failedAction": {
            "action": "SELECT"
        },
        "reason": "NODE_NOT_FOUND",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 422

def test_invalid_action_index():
    payload = {
        "flowId": "food_order_001",
        "actionIndex": "not_an_int",
        "failedAction": {
            "action": "SELECT"
        },
        "reason": "NODE_NOT_FOUND",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 422

def test_ambiguous_node_match():
    payload = {
        "flowId": "food_order_001",
        "actionIndex": 2,
        "failedAction": {"action": "SELECT"},
        "reason": "AMBIGUOUS_NODE_MATCH",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ASK_USER"

def test_wrong_application():
    payload = {
        "flowId": "food_order_001",
        "actionIndex": 0,
        "failedAction": {"action": "SEARCH"},
        "reason": "WRONG_APPLICATION",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "STOP"

def test_sensitive_action():
    payload = {
        "flowId": "food_order_001",
        "actionIndex": 3,
        "failedAction": {"action": "TYPE_TEXT", "target": "password"},
        "reason": "SENSITIVE_ACTION",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "STOP"

def test_ui_state_timeout():
    payload = {
        "flowId": "food_order_001",
        "actionIndex": 2,
        "failedAction": {"action": "SELECT"},
        "reason": "UI_STATE_TIMEOUT",
        "currentApp": "com.example.app"
    }
    response = client.post("/v1/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "RECOVERY_REQUIRED"
