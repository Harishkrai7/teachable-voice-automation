"""Contract tests mapped to the roadmap's Definition of Done (T1-T14, Cloud side)."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.intents import RuleExtractor
from app.main import app, get_extractor, get_store
from app.store import JsonFlowStore

EXAMPLES = Path(__file__).parent.parent / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path):
    store = JsonFlowStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_extractor] = lambda: RuleExtractor()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def zomato(client):
    r = client.post("/v1/teach", json=load("teach_zomato.json"))
    assert r.status_code == 200, r.text
    return r.json()


def by_action(actions, name):
    return [a for a in actions if a["type"] == name]


# T1 - teach a new food flow; noise dropped; payment boundary respected
def test_teach_food_flow(zomato):
    assert zomato["status"] == "LEARNED"
    flow = zomato["flow"]
    assert flow["flowId"] == "order_food_001"
    assert flow["intent"] == "order_food"
    # 3 keystroke TYPEs collapse to 1, CLICK Offers + BACK removed, Proceed to Pay truncated
    assert zomato["droppedActions"] == 4
    assert any("PAYMENT" in w for w in zomato["warnings"])
    steps = flow["steps"]
    assert all("Pay" not in ((s.get("target") or {}).get("text") or "") for s in steps)
    assert by_action(steps, "SEARCH")[0]["value"] == "{{restaurant}}"
    assert by_action(steps, "SEARCH")[1]["value"] == "{{item}}"
    selects = by_action(steps, "SELECT")
    assert [s["target"]["text"] for s in selects] == ["{{restaurant}}", "{{item}}"]
    assert selects[0]["taughtTargetText"] == "Domino's Pizza"
    assert by_action(steps, "SET_QUANTITY")[0]["value"] == "{{quantity}}"


# T2 - exact replay
def test_exact_replay(client, zomato):
    r = client.post("/v1/replay", json={"utterance": "Order a Margherita pizza from Dominos on Zomato"}).json()
    assert r["status"] == "PLAN"
    assert r["flowId"] == "order_food_001"
    assert by_action(r["steps"], "SEARCH")[1]["value"] == "Margherita pizza"
    assert "PAYMENT" in r["stopBefore"]


# T3 - paraphrase replay
def test_paraphrase_replay(client, zomato):
    r = client.post("/v1/replay", json={"utterance": "Get me a margherita from dominos", "currentApp": "Zomato"}).json()
    assert r["status"] == "PLAN"
    assert r["flowId"] == "order_food_001"


# T4 / T5 / T6 - changed item, quantity, address
def test_changed_slots(client, zomato):
    r = client.post("/v1/replay", json={
        "utterance": "Order 2 Farmhouse pizzas from Dominos and deliver to office", "currentApp": "Zomato"}).json()
    assert r["status"] == "PLAN", r
    acts = r["steps"]
    assert by_action(acts, "SEARCH")[1]["value"] == "Farmhouse pizzas"
    assert by_action(acts, "SELECT")[1]["target"]["text"] == "Farmhouse pizzas"
    assert by_action(acts, "SET_QUANTITY")[0]["value"] == "2"
    assert by_action(acts, "SELECT_ADDRESS")[0]["value"] == "office"


def test_unspoken_address_defaults_to_taught_tap(client, zomato):
    # address was never spoken while teaching; the address the user tapped becomes the default
    assert zomato["flow"]["slots"]["address"] == "Home"
    r = client.post("/v1/replay", json={"utterance": "Order a Margherita pizza from Dominos on Zomato"}).json()
    assert by_action(r["steps"], "SELECT_ADDRESS")[0]["value"] == "Home"
    assert "address" in r["defaultedSlots"]


# T8 / T9 - second app, cross-app routing by intent and app name
def test_second_app_and_cross_app(client, zomato):
    t = client.post("/v1/teach", json=load("teach_amazon.json")).json()
    assert t["status"] == "LEARNED" and t["flow"]["intent"] == "add_to_cart"
    assert t["droppedActions"] == 1  # double scroll collapsed
    r = client.post("/v1/replay", json={"utterance": "Buy 3 AA batteries on Amazon"}).json()
    assert r["status"] == "PLAN" and r["app"] == "Amazon"
    assert by_action(r["steps"], "SEARCH")[0]["value"] == "AA batteries"
    assert by_action(r["steps"], "SET_QUANTITY")[0]["value"] == "3"
    r = client.post("/v1/replay", json={"utterance": "Order a burger from McDonalds on Swiggy"}).json()
    assert r["status"] == "NOT_LEARNED" and "Swiggy" in r["message"]


# T11 - payment / auth boundary during replay
def test_sensitive_screen_stops(client, zomato):
    r = client.post("/v1/replay", json={
        "utterance": "Order a Margherita pizza from Dominos",
        "uiSummary": {"screenTitle": "Enter OTP", "nodes": [{"className": "android.widget.EditText", "text": ""}]},
    }).json()
    assert r["status"] == "STOP"


def test_password_field_never_stored(client):
    body = load("teach_zomato.json")
    body["actions"].insert(1, {"action": "TYPE", "value": "hunter2",
                               "target": {"isPassword": True, "className": "android.widget.EditText"}})
    t = client.post("/v1/teach", json=body).json()
    assert "hunter2" not in json.dumps(t)
    assert len(t["flow"]["steps"]) == 1


# T12 - unknown intent -> not learned + offer teaching
def test_unknown_intent(client, zomato):
    r = client.post("/v1/replay", json={"utterance": "Book a cab to the airport"}).json()
    assert r["status"] == "NOT_LEARNED" and r["offerTeach"] is True


def test_custom_flow_can_be_taught_live(client):
    t = client.post("/v1/teach", json={"utterance": "Book a cab to the airport", "app": "Uber", "actions": [
        {"action": "CLICK", "target": {"text": "Where to?"}},
        {"action": "TYPE", "value": "Airport", "target": {"resourceId": "destination"}},
        {"action": "SELECT", "target": {"text": "Kempegowda International Airport"}}]}).json()
    assert t["status"] == "LEARNED" and t["flow"]["intent"].startswith("custom_")
    r = client.post("/v1/replay", json={"utterance": "book me a cab to the airport"}).json()
    assert r["status"] == "PLAN" and r["flowId"] == t["flow"]["flowId"]


# T13 - ambiguity -> clarification, then the user's pick is honoured
def test_ambiguity(client, zomato):
    swiggy = load("teach_zomato.json") | {"app": "Swiggy", "utterance": "Order a Margherita pizza from Dominos on Swiggy"}
    client.post("/v1/teach", json=swiggy)
    r = client.post("/v1/replay", json={"utterance": "Get me a margherita from Dominos"}).json()
    assert r["status"] == "ASK_USER" and len(r["options"]) == 2
    pick = r["options"][1]["flowId"]
    r = client.post("/v1/replay", json={"utterance": "Get me a margherita from Dominos", "flowId": pick}).json()
    assert r["status"] == "PLAN" and r["flowId"] == pick


def test_changing_an_untaught_slot_asks(client):
    body = load("teach_amazon.json")
    body["actions"] = [a for a in body["actions"] if a["action"] != "SET_QUANTITY"]
    client.post("/v1/teach", json=body)
    r = client.post("/v1/replay", json={"utterance": "Buy 4 USB-C cables on Amazon"}).json()
    assert r["status"] == "ASK_USER" and "quantity" in r["question"]


from app import recovery
from app.schemas import RecoverRequest, Step, Target, ScreenSummary

def recover(client, flow_id, screen, attempt=1, step=None):
    step = step or {"action": "SELECT", "target": {"text": "Margherita", "clickable": True}}
    req = RecoverRequest(
        flowId=flow_id, stepIndex=4, attempt=attempt,
        step=Step(**step), screen=ScreenSummary(**screen)
    )
    return recovery.decide(req)


def test_recover_popup(client, zomato):
    r = recover(client, "order_food_001", {"screenTitle": "Restaurant", "nodes": [
        {"text": "Get 50% off!", "className": "android.app.Dialog", "clickable": True}, {"text": "Not now", "clickable": True}]})
    assert r["decision"] == "DISMISS_POPUP" and r["action"].target.text == "Not now" and r["action"].action == "DISMISS"


def test_recover_changed_label(client, zomato):
    r = recover(client, "order_food_001", {"nodes": [
        {"text": "Margherita Pizza (Regular)", "clickable": True}, {"text": "Farmhouse", "clickable": True}]})
    assert r["decision"] == "RETRY_WITH_TARGET"
    assert r["action"].target.text == "Margherita Pizza (Regular)"


def test_recover_already_in_cart(client, zomato):
    r = recover(client, "order_food_001", {"nodes": [{"text": "View Cart"}, {"text": "1 item added"}]},
                step={"action": "ADD_TO_CART", "target": {"text": "ADD"}})
    assert r["decision"] == "CONTINUE"


def test_recover_ambiguous_asks(client, zomato):
    r = recover(client, "order_food_001", {"nodes": [
        {"text": "Margherita Regular", "clickable": True}, {"text": "Margherita Large", "clickable": True}]})
    assert r["decision"] == "ASK_USER" and len(r["options"]) == 2


def test_recover_genuinely_stuck_reports_step(client, zomato):
    screen = {"screenTitle": "Restaurant", "nodes": [{"text": "Menu"}]}
    r = recover(client, "order_food_001", screen)
    assert r["decision"] == "ASK_USER" and "step 5" in r["question"]
    r = recover(client, "order_food_001", screen, attempt=3)
    assert r["decision"] == "ASK_USER" and "step 5" in r["reason"]


def test_recover_sensitive(client, zomato):
    r = recover(client, "order_food_001", {"nodes": [{"className": "android.widget.EditText", "isPassword": True}]})
    assert r["decision"] == "STOP"


def test_metrics_and_step_results(client, zomato):
    client.post("/v1/replay", json={"utterance": "Order a Margherita pizza from Dominos on Zomato"})
    client.post("/v1/step-result", json={"flowId": "order_food_001", "stepIndex": 3, "success": False,
                                         "failureReason": "target not found"})
    m = client.get("/v1/metrics").json()
    assert m["flows"] == 1 and m["replay"]["PLAN"] == 1
    assert m["topFailingSteps"][0][0] == "order_food_001#step4"
