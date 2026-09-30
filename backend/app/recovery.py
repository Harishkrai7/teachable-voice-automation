"""Recovery / clarification reasoning (roadmap phase G5).

Returns a constrained decision - never arbitrary code. Android must still verify that any
proposed target exists in its live tree before acting on it.
"""
from __future__ import annotations

import re

from . import safety
from .schemas import ActionType, RecoverRequest, RecoveryDecision, Step, Target
from .text import norm, similar

MAX_ATTEMPTS = 3
DISMISS_RE = re.compile(
    r"^(close|dismiss|not now|no thanks|no,? thanks|skip|later|maybe later|cancel|got it|ok|okay|"
    r"x|×|✕|✖|close dialog|close popup|deny|don'?t allow)$",
    re.I,
)
POPUP_HINT_RE = re.compile(r"(dialog|popup|sheet|modal|offer|promo|coupon|rate us|notification|allow)", re.I)
ALREADY_DONE = {
    ActionType.ADD_TO_CART: re.compile(r"\b(go to cart|view cart|in (your )?cart|added|item added|remove)\b", re.I),
    ActionType.OPEN_CART: re.compile(r"\b(your cart|cart total|bill details|item total|subtotal)\b", re.I),
}


def _label(t: Target) -> str:
    return t.text or t.contentDescription or t.parentText or t.resourceId or "?"


def _expected(step: Step) -> str | None:
    t = step.target
    if t:
        return t.text or t.contentDescription or t.parentText
    return step.value


def decide(req: RecoverRequest) -> dict:
    step, screen = req.step, req.screen
    where = screen.screenTitle or screen.package or "current"
    expected = _expected(step)
    human_step = f"step {req.stepIndex + 1} ({step.action.value}{f' {expected!r}' if expected else ''})"

    # 1. Safety first: sensitive screen -> hand control to the user.
    if cat := safety.classify_screen(screen):
        return dict(
            decision=RecoveryDecision.STOP, confidence=1.0,
            reason=f"{cat} screen detected. Your turn - please complete it, then I'll check whether I can continue.",
        )

    usable = [n for n in screen.nodes if n.enabled is not False]

    # 2. Expected target visible under slightly different evidence (renamed id, changed label).
    hits = []
    if expected:
        hits = [n for n in usable if similar(n.text, expected) or similar(n.contentDescription, expected) or similar(n.parentText, expected)]
    if step.target and step.target.resourceId:
        hits += [n for n in usable if n.resourceId == step.target.resourceId and n not in hits]
    
    if hits:
        clickable = [n for n in hits if n.clickable is not False]
        hits = clickable or hits
        if len(hits) == 1:
            return dict(
                decision=RecoveryDecision.RETRY_WITH_TARGET, confidence=0.8,
                action=step.model_copy(update={"target": hits[0]}),
                reason=f"Found {_label(hits[0])!r} matching {expected or step.target.resourceId!r}; retry with this target.",
            )
        if len(hits) > 1:
            labels = list(dict.fromkeys(_label(h) for h in hits))[:5]
            return dict(
                decision=RecoveryDecision.ASK_USER, confidence=0.5, options=labels,
                question=f"At {human_step} I see several matches for {expected or step.target.resourceId!r}: {', '.join(labels)}. Which one?",
                reason="Ambiguous target on screen.",
            )

    # 3. Harmless popup covering the screen: dismiss it, then Android retries the same step.
    closers = [n for n in usable if DISMISS_RE.match(norm(_label(n)) or "")]
    popup_hint = POPUP_HINT_RE.search(" ".join(filter(None, [screen.screenTitle] + [n.className or "" for n in usable])))
    if closers and (popup_hint or len(closers) == 1) and req.attempt < MAX_ATTEMPTS:
        return dict(
            decision=RecoveryDecision.DISMISS_POPUP, confidence=0.75,
            action=Step(action=ActionType.DISMISS, target=closers[0]),
            reason=f"A popup is covering the screen; tap {_label(closers[0])!r} then retry {human_step}.",
        )

    # 4. The step's goal is already true (e.g. item already in cart).
    blob = " ".join(_label(n) for n in screen.nodes) + " " + (screen.screenTitle or "")
    if (pat := ALREADY_DONE.get(step.action)) and pat.search(blob):
        return dict(
            decision=RecoveryDecision.CONTINUE, confidence=0.7,
            reason=f"The goal of {human_step} already appears to be reached; skip to the next step.",
        )

    # 5. Genuinely stuck: report the exact step instead of looping.
    if req.attempt >= MAX_ATTEMPTS:
        return dict(
            decision=RecoveryDecision.ASK_USER, confidence=0.9,
            reason=f"Stopped at {human_step}: could not find {expected or 'the target'!r} on the {where} screen "
                   f"after {req.attempt} attempts.",
        )
    return dict(
        decision=RecoveryDecision.ASK_USER, confidence=0.6,
        question=f"I'm stuck at {human_step}. I couldn't find {expected or 'the next control'!r} on the {where} "
                 "screen. Could you tap it for me, or tell me what to do?",
        reason="Target not found and no safe alternative.",
    )
