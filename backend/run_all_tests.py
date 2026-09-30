import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"

def wait_rate_limit():
    print("Waiting 15 seconds to respect free-tier rate limit (5 req/min)...")
    time.sleep(15)

def run_tests():
    print("--- Phase 3: Test Real API ---")
    # Health
    resp = requests.get(f"{BASE_URL}/health")
    print("GET /health:", resp.status_code, resp.json())
    assert resp.status_code == 200

    tests = [
        {"utt": "Order a Margherita pizza from Dominos", "app": "Zomato", "exp_intent": "order_food"},
        {"utt": "Buy two burgers from McDonald's", "app": "Zomato", "exp_intent": "order_food"},
        {"utt": "Add Nike Air Max shoes to my Amazon cart", "app": "Amazon", "exp_intent": "add_to_cart"},
        {"utt": "Get me one large pizza from Dominos", "app": "Zomato", "exp_intent": "order_food"},
        {"utt": "Book me a flight to Delhi", "app": "MakeMyTrip", "exp_intent": "unknown_intent"},
        {"utt": "Order pizza", "app": "Zomato", "exp_intent": "order_food"}
    ]

    for t in tests:
        wait_rate_limit()
        print(f"\nTesting: {t['utt']}")
        resp = requests.post(f"{BASE_URL}/v1/intent/extract", json={"utterance": t["utt"], "currentApp": t["app"]})
        data = resp.json()
        print(json.dumps(data, indent=2))
        if resp.status_code != 200:
            print("FAILED! Expected 200, got", resp.status_code)
            sys.exit(1)
        if data.get("intent") != t["exp_intent"]:
            print(f"FAILED! Expected intent {t['exp_intent']} but got {data.get('intent')}")
            sys.exit(1)

    print("\n--- Phase 4: Test TEACH Contract ---")
    wait_rate_limit()
    teach_req = {
        "mode": "TEACH",
        "utterance": "Order a Margherita pizza from Dominos on Zomato",
        "actions": [{"action": "SEARCH", "target": "Dominos"}],
        "app": "Zomato"
    }
    resp = requests.post(f"{BASE_URL}/v1/process", json=teach_req)
    data = resp.json()
    print("TEACH Response:", json.dumps(data, indent=2))
    assert data["cloud1_output"]["intent"] == "order_food"

    print("\n--- Phase 5: Test REPLAY Contract ---")
    wait_rate_limit()
    replay_req = {
        "mode": "REPLAY",
        "utterance": "Get me a margherita from dominos",
        "currentApp": "Zomato"
    }
    resp = requests.post(f"{BASE_URL}/v1/process", json=replay_req)
    data = resp.json()
    print("REPLAY Response:", json.dumps(data, indent=2))
    assert data["cloud1_output"]["intent"] == "order_food"

    print("\n--- Phase 6: Verify Safety ---")
    wait_rate_limit()
    safety_req = {
        "utterance": "Enter my password and click login",
        "currentApp": "BankApp"
    }
    resp = requests.post(f"{BASE_URL}/v1/intent/extract", json=safety_req)
    data = resp.json()
    print("Safety Response:", json.dumps(data, indent=2))
    # Should not extract any valid flow, likely unknown_intent
    assert data.get("intent") == "unknown_intent"

    print("\nALL REAL API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
