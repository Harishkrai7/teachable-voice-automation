# API Contract

## Cloud 1 -> Cloud 2 API

### POST `/v1/process`
Unified endpoint for Cloud 2 reasoning (TEACH and REPLAY).

#### Teach Request
```json
{
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
```

#### Teach Response (Success)
```json
{
  "success": true,
  "mode": "TEACH",
  "flow": {
    "flowId": "a1b2c3d4",
    "intent": "order_food",
    "slots": {
      "restaurant": "Dominos",
      "item": "Margherita Pizza",
      "quantity": 1
    },
    "steps": [
      {"action": "SEARCH", "target": "{{restaurant}}"},
      {"action": "CLICK", "target": "Dominos Restaurant"},
      {"action": "SEARCH", "target": "{{item}}"},
      {"action": "SET_QUANTITY", "value": "{{quantity}}"},
      {"action": "ADD_TO_CART"}
    ],
    "stopBefore": ["PAYMENT", "OTP", "PASSWORD", "PIN"]
  }
}
```

#### Replay Request
```json
{
  "mode": "REPLAY",
  "utterance": "Get me a Margherita from Pizza Hut",
  "currentApp": "Zomato"
}
```

#### Replay Response (Success)
```json
{
  "success": true,
  "mode": "REPLAY",
  "flowId": "a1b2c3d4",
  "intent": "order_food",
  "slots": {
    "restaurant": "Pizza Hut",
    "item": "Margherita",
    "quantity": null
  },
  "actions": [
    {"action": "SEARCH", "target": "Pizza Hut"},
    {"action": "CLICK", "target": "Dominos Restaurant"},
    {"action": "SEARCH", "target": "Margherita"},
    {"action": "SET_QUANTITY", "value": null},
    {"action": "ADD_TO_CART"}
  ]
}
```

#### Other Responses
**Clarification (`ASK_USER`):**
```json
{
  "success": true,
  "type": "ASK_USER",
  "question": "What quantity would you like?"
}
```

**Not Learned (`NOT_LEARNED`):**
```json
{
  "success": true,
  "type": "NOT_LEARNED",
  "message": "I have not learned a flow for this task yet."
}
```

**Safety Boundary (`STOP`):**
```json
{
  "success": true,
  "type": "STOP",
  "reason": "SENSITIVE_ACTION"
}
```

### POST `/v1/feedback` (Future Contract)
Android will send structured feedback when a Replay execution fails physically.
```json
{
  "flowId": "food_order_001",
  "actionIndex": 2,
  "failedAction": {
    "action": "SELECT",
    "target": "Margherita Pizza"
  },
  "reason": "NODE_NOT_FOUND",
  "currentApp": "com.example.app"
}
```
