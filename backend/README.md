# PRISM Theme 3 — Cloud Engine (FastAPI)

Engine B of the *Teachable Voice Automation* roadmap. **Android is the eyes + hands; this service is the brain.**
It never touches the phone: it turns demonstrations into parameterized flows, matches new voice
commands to them, and returns structured JSON plans / decisions that Android executes and verifies.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8765
```

- `http://localhost:8765/` — mock-Android console (teach / replay / recover without a phone)
- `http://localhost:8765/docs` — OpenAPI docs (share with the Android team)
- `pytest` — contract tests mapped to T1–T14

## Endpoints (contract v1.0 — `app/schemas.py`)

| Method | Path | Direction | Purpose |
|---|---|---|---|
| POST | `/v1/teach` | Android → Cloud | utterance + recorded semantic actions → `LEARNED` flow (or `REJECTED`) |
| POST | `/v1/replay` | Android → Cloud | utterance (+ current app / screen) → `PLAN` · `ASK_USER` · `NOT_LEARNED` · `STOP` |
| POST | `/v1/recover` | Android → Cloud | failed step + screen summary → `RETRY_ALTERNATE` · `DISMISS_POPUP` · `SKIP_STEP` · `ASK_USER` · `STOP` · `FAIL` |
| POST | `/v1/step-result` | Android → Cloud | success/failure per step (evaluation log) |
| GET/DELETE | `/v1/flows[/{id}]` | — | inspect / remove learned flows |
| GET | `/v1/metrics` | — | teach/replay/recovery counts, slot substitutions, top failing steps |

After an `ASK_USER` with `options`, Android re-sends the replay with the chosen `flowId`.

## How each module maps to the roadmap

| Module | Phase | What it does |
|---|---|---|
| `intents.py` | G2 | Intent (`order_food`, `add_to_cart`, `unknown_intent`) + slots (`restaurant`, `item`, `quantity`, `address`). Rule-based by default; `EXTRACTOR=gemini` uses Gemini structured output with rule fallback. |
| `generalizer.py` | A2/G3 | Drops noise (keystroke-by-keystroke typing, double taps, repeated scrolls, click-then-back), replaces slot values with `{{slot}}`, **cuts the flow at the first password/OTP/PIN/payment/login step**. |
| `matcher.py` | G4 | One match → plan; none → `NOT_LEARNED` + offer to teach; tie → `ASK_USER`. Never silently picks an unrelated flow. Custom taught intents (e.g. "book a cab") match by wording. |
| `recovery.py` | G5 | Constrained decisions only. Order: sensitive screen → changed label → popup → already done → report the exact step. |
| `safety.py` | A5 | Cloud-side sensitive-screen detector (Android's Safety Gate stays the first line). |
| `store.py` | — | JSON flow store + JSONL event log. No credentials are ever stored. |

Replay rules worth knowing:
- Slots not spoken at replay keep their taught values (reported in `defaultedSlots`).
- `SELECT_ADDRESS` / `SET_QUANTITY` are always parameterized, so an unspoken address becomes the one tapped while teaching.
- If a user changes a slot the demonstration never showed (e.g. quantity with no quantity step), the service asks instead of guessing.
- Resolved `target.text` is the *new* value; `taughtTargetText` keeps the original evidence. Android's resolver should match by resource ID → text (fuzzy) → content description, as in phase A3.

## Deploy to Cloud Run (G6)

```bash
gcloud run deploy prism-cloud --source . --region asia-south1 --allow-unauthenticated
```

Optional Gemini: add `--set-env-vars EXTRACTOR=gemini,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=<id>,GOOGLE_CLOUD_LOCATION=asia-south1`.
Do not put keys in the APK; use the Cloud Run service account for Vertex AI.

**Before a real deployment:** Cloud Run's filesystem is ephemeral, so replace `JsonFlowStore` with a
Firestore class that has the same methods (`list/get/save/save_new/delete/log/metrics`). Also drop
`--allow-unauthenticated` in favour of an auth mechanism once the Android client is ready.
