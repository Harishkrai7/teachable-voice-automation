"""Sensitive-screen detection: payment / OTP / password / PIN / authentication boundary.

Android runs its own Safety Gate on-device; this is the Cloud-side second line of defence.
"""
import re

from .schemas import ObservedAction, ScreenSummary, Target

SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "OTP": re.compile(r"\b(otp|one[\s-]?time\s+pass(word|code)|verification\s+code)\b", re.I),
    "PASSWORD": re.compile(r"\b(password|passcode|passwd)\b", re.I),
    "PIN": re.compile(r"\b(pin|upi\s+pin|mpin)\b", re.I),
    "PAYMENT": re.compile(
        r"\b(pay(ment)?|pay\s+now|proceed\s+to\s+pay|place\s+order|cvv|card\s+number|expiry|"
        r"net\s*banking|upi|wallet\s+balance|credit\s+card|debit\s+card)\b",
        re.I,
    ),
    "AUTH": re.compile(r"\b(log\s?in|sign\s?in|sign\s?up|authenticat\w*|verify\s+(it'?s\s+)?you)\b", re.I),
}


def _target_blob(t: Target | None) -> str:
    if t is None:
        return ""
    return " ".join(filter(None, [t.text, t.contentDescription, t.resourceId, t.screen]))


def classify_text(text: str) -> str | None:
    for category, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(text.replace("_", " ")):
            return category
    return None


def classify_target(t: Target | None) -> str | None:
    if t is not None and t.isPassword:
        return "PASSWORD"
    return classify_text(_target_blob(t))


def classify_action(a: ObservedAction) -> str | None:
    return classify_target(a.target)


def classify_screen(screen: ScreenSummary | None) -> str | None:
    """A screen is sensitive if it has a password field, or its title / input fields look sensitive.

    Plain buttons mentioning 'pay' on an otherwise normal screen (e.g. a cart total) are not
    enough on their own; we look at the title and at editable/password fields.
    """
    if screen is None:
        return None
    if any(n.isPassword for n in screen.nodes):
        return "PASSWORD"
    if screen.screenTitle and (cat := classify_text(screen.screenTitle)):
        return cat
    for n in screen.nodes:
        if n.className and "EditText" in n.className and (cat := classify_target(n)):
            return cat
    return None
