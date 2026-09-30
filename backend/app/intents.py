"""Intent + slot extraction (roadmap phase G2).

`RuleExtractor` is deterministic and works offline, so the service and tests run with no keys.
`GeminiExtractor` uses Gemini structured output; any failure falls back to the rules.
Select with EXTRACTOR=rules|gemini.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Protocol

from .schemas import Extraction

log = logging.getLogger(__name__)

CONTROLLED_INTENTS = ["order_food", "add_to_cart", "unknown_intent"]
SLOT_NAMES = ["restaurant", "item", "quantity", "address"]

FOOD_APPS = {"zomato", "swiggy", "eatsure", "magicpin"}
SHOP_APPS = {"amazon", "flipkart", "myntra", "meesho", "blinkit", "zepto", "bigbasket", "jiomart", "nykaa"}
KNOWN_APPS = FOOD_APPS | SHOP_APPS
APP_DISPLAY = {a: a.capitalize() for a in KNOWN_APPS} | {"bigbasket": "BigBasket", "jiomart": "JioMart"}

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "single": 1, "two": 2, "couple of": 2, "a couple of": 2, "three": 3,
    "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "a dozen": 12,
    "dozen": 12,
}
_NUM_RE = "|".join(sorted((re.escape(k) for k in NUMBER_WORDS), key=len, reverse=True))

_LEAD_RE = re.compile(
    r"^\s*(?:hey\s+\w+[,\s]+)?(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?"
    r"(?:i\s+(?:want|need|would\s+like|'d\s+like)\s+(?:to\s+)?)?"
    r"(?:order|get\s+me|get|buy|add|purchase|bring\s+me|fetch|grab|put)\s+",
    re.I,
)


def _cut(text: str, m: re.Match[str]) -> str:
    return (text[: m.start()] + " " + text[m.end():]).strip()


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = re.sub(r"^(?:some|the|my)\s+", "", v.strip(" .,!?;:"), flags=re.I)
    v = re.sub(r"\s+(?:and|with|then|please|now)$", "", v.strip(" .,!?;:"), flags=re.I).strip(" .,!?;:")
    return v or None


class Extractor(Protocol):
    def extract(self, utterance: str, known_intents: list[str] | None = None) -> Extraction: ...


class RuleExtractor:
    def extract(self, utterance: str, known_intents: list[str] | None = None) -> Extraction:
        text = " " + utterance.strip() + " "
        low = text.lower()
        slots: dict[str, object] = {}

        # app: "on Zomato", "using Amazon", "from Swiggy"
        app = None
        m = re.search(r"\b(?:on|in|using|via|from|through)\s+(" + "|".join(KNOWN_APPS) + r")\b", text, re.I)
        if m:
            app = APP_DISPLAY[m.group(1).lower()]
            text = _cut(text, m)
        else:
            m = re.search(r"\b(" + "|".join(KNOWN_APPS) + r")\b", text, re.I)
            if m:
                app = APP_DISPLAY[m.group(1).lower()]
                text = _cut(text, m)

        has_cart = bool(re.search(r"\b(cart|basket|bag)\b", low))
        text = re.sub(r"\b(?:to|into|in)\s+(?:my\s+|the\s+)?(?:cart|basket|bag)\b", " ", text, flags=re.I)

        # address: "deliver to home", "to my office", "at my work address"
        m = re.search(
            r"\b(?:deliver(?:ed|y)?\s+(?:it\s+)?(?:to|at)|send\s+(?:it\s+)?to|to\s+my|at\s+my|address\s*[:=]?)\s+"
            r"(?:my\s+)?(.+?)(?:\s+address)?(?=\s+(?:from|with|and|please)\b|[,.!?]|\s*$)",
            text,
            re.I,
        ) or re.search(r"\b(?:to|at)\s+(home|work|office)\b", text, re.I)
        if m:
            slots["address"] = _clean(m.group(1))
            text = _cut(text, m)

        # restaurant: "from Dominos"
        m = re.search(r"\bfrom\s+(.+?)(?=\s+(?:with|and|for|please|to)\b|[,.!?]|\s*$)", text, re.I)
        if m:
            slots["restaurant"] = _clean(m.group(1))
            text = _cut(text, m)

        # explicit quantity: "quantity 3", "qty: 2", "x2", "3 of"
        m = re.search(r"\b(?:quantity|qty)\s*[:=]?\s*(\d+)\b|\bx\s?(\d+)\b", text, re.I)
        if m:
            slots["quantity"] = int(m.group(1) or m.group(2))
            text = _cut(text, m)

        text = _LEAD_RE.sub("", text.strip() + " ").strip()

        # leading quantity: "2 margherita", "two packs of", "a large pizza"
        m = re.match(rf"^(\d+|{_NUM_RE})\s+(?:(?:x|packs?|pieces?|boxes?|units?|plates?|bottles?)\s+(?:of\s+)?|of\s+)?", text, re.I)
        if m:
            q = m.group(1).lower()
            slots.setdefault("quantity", int(q) if q.isdigit() else NUMBER_WORDS[q])
            text = text[m.end():]

        item = _clean(re.sub(r"\s+", " ", text))
        if item and not re.fullmatch(r"(it|that|this|something|food|stuff)", item, re.I):
            slots["item"] = item

        # intent
        app_l = (app or "").lower()
        if app_l in SHOP_APPS or has_cart or re.search(r"\b(buy|purchase)\b", low):
            intent = "add_to_cart"
        elif app_l in FOOD_APPS or "restaurant" in slots or re.search(r"\b(order|deliver|hungry|eat)\b", low):
            intent = "order_food" if slots.get("item") or slots.get("restaurant") else "unknown_intent"
        else:
            intent = "unknown_intent"
        if intent == "unknown_intent":
            slots = {}  # custom (taught) flows are matched by utterance similarity instead

        if intent == "add_to_cart" and "restaurant" in slots:
            # "buy a charger from Amazon Basics" - a seller/brand, not a restaurant
            slots["seller"] = slots.pop("restaurant")
        return Extraction(intent=intent, slots={k: v for k, v in slots.items() if v is not None}, app=app)


class GeminiExtractor:
    """Structured-output extraction via Gemini (google-genai SDK; Vertex AI or API key)."""

    def __init__(self, model: str | None = None):
        from google import genai  # optional dependency: pip install -r requirements-llm.txt

        self.client = genai.Client()
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.fallback = RuleExtractor()

    def extract(self, utterance: str, known_intents: list[str] | None = None) -> Extraction:
        intents = sorted(set(CONTROLLED_INTENTS) | set(known_intents or []))
        prompt = (
            "Extract the user's intent and slots from a voice command for a phone-automation assistant.\n"
            f"Allowed intents (choose exactly one, never invent): {intents}\n"
            f"Slots: {SLOT_NAMES}. quantity is an integer. Omit slots that are not stated. "
            f"app is one of {sorted(APP_DISPLAY.values())} or null.\n"
            'Reply only with JSON: {"intent": str, "slots": {..}, "app": str|null}\n'
            f"Command: {json.dumps(utterance)}"
        )
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0},
            )
            ex = Extraction.model_validate_json(resp.text)
            if ex.intent not in intents:
                ex.intent = "unknown_intent"
            ex.slots = {k: v for k, v in ex.slots.items() if k in SLOT_NAMES and v not in (None, "")}
            return ex
        except Exception:  # network, quota, schema - never break the request path
            log.exception("Gemini extraction failed; using rule extractor")
            return self.fallback.extract(utterance, known_intents)


def build_extractor() -> Extractor:
    if os.getenv("EXTRACTOR", "rules").lower() == "gemini":
        return GeminiExtractor()
    return RuleExtractor()
