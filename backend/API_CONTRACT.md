# API Contract

## Error Contract (Consistent across all endpoints)
If a request fails, you will receive an HTTP error code (e.g., 400, 422, 500) and the following structured JSON:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Validation failed..."
  }
}
```

Possible `code` values:
- `INVALID_REQUEST` (Malformed JSON or missing fields)
- `EMPTY_UTTERANCE` (Utterance is empty or whitespace)
- `UNKNOWN_INTENT` (Used when intent is unsupported)
- `MODEL_ERROR` (Gemini failed to generate response)
- `INTERNAL_ERROR` (Server error)

---

## 1. Extract Intent
**Endpoint:** `POST /v1/intent/extract`

**Request Body:**
```json
{
  "utterance": "Order a Margherita pizza from Dominos",
  "currentApp": "Zomato"
}
```

**Success Response (200 OK):**
```json
{
  "intent": "order_food",
  "slots": {
    "restaurant": "Dominos",
    "item": "Margherita Pizza",
    "quantity": 1,
    "address": null
  }
}
```

---

## 2. Process (TEACH Mode)
**Endpoint:** `POST /v1/process`

**Request Body:**
```json
{
  "mode": "TEACH",
  "utterance": "Order a Margherita pizza from Dominos on Zomato",
  "actions": [
    {
      "action": "SEARCH",
      "target": "Dominos"
    },
    {
      "action": "CLICK",
      "target": "Dominos Restaurant"
    },
    {
      "action": "SEARCH",
      "target": "Margherita Pizza"
    },
    {
      "action": "SET_QUANTITY",
      "value": "1"
    }
  ],
  "app": "Zomato"
}
```

---

## 3. Process (REPLAY Mode)
**Endpoint:** `POST /v1/process`

**Request Body:**
```json
{
  "mode": "REPLAY",
  "utterance": "Get me a margherita from dominos",
  "currentApp": "Zomato"
}
```

**Success Response (200 OK) [Temporary placeholder until Cloud 2 is built]:**
```json
{
  "success": true,
  "mode": "REPLAY",
  "cloud1_output": {
    "intent": "order_food",
    "slots": {
      "restaurant": "Dominos",
      "item": "Margherita Pizza",
      "quantity": 1,
      "address": null
    }
  },
  "message": "Processed by Cloud 1. Hand-off to Cloud 2 available."
}
```
