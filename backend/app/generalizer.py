"""Flow generalization (roadmap phase G3): concrete demonstration -> parameterized semantic steps.

    SEARCH 'Margherita Pizza'  ->  SEARCH '{{item}}'
    SELECT 'Dominos'           ->  SELECT '{{restaurant}}'

Only evidence Android observed is used; nothing about the UI is invented here.
"""
from __future__ import annotations

import re
from typing import Any

from . import safety
from .schemas import ActionType, ObservedAction, Step, Target
from .text import norm, similar

TEXT_ENTRY = {ActionType.TYPE, ActionType.SEARCH}
SLOT_RE = re.compile(r"\{\{(\w+)\}\}")


def _identity(t: Target | None) -> tuple:
    if t is None:
        return ()
    return (t.resourceId, norm(t.text), norm(t.contentDescription), t.className, t.screen)


def filter_noise(actions: list[ObservedAction]) -> tuple[list[ObservedAction], int]:
    """Drop actions that don't contribute to the flow. Returns (kept, dropped_count)."""
    kept: list[ObservedAction] = []
    for a in actions:
        if a.action == ActionType.WAIT:
            continue
        prev = kept[-1] if kept else None
        if prev is not None:
            # keystroke-by-keystroke typing into the same field: keep only the final value
            if a.action in TEXT_ENTRY and prev.action in TEXT_ENTRY and _identity(a.target) == _identity(prev.target):
                kept[-1] = a
                continue
            # repeated scrolls collapse into one
            if a.action == prev.action == ActionType.SCROLL:
                continue
            # accidental double tap
            if a.action == prev.action == ActionType.CLICK and _identity(a.target) == _identity(prev.target) and a.target:
                continue
            # explored a screen and came straight back: CLICK x, BACK -> nothing
            if a.action == ActionType.BACK and prev.action in (ActionType.CLICK, ActionType.SELECT):
                kept.pop()
                continue
        kept.append(a)
    return kept, len(actions) - len(kept)


def _slot_for(value: str | None, slots: dict[str, Any], action: ActionType) -> str | None:
    """Best-matching slot for an observed value, or None. Exact beats containment beats fuzzy."""
    if value is None:
        return None
    best, best_score = None, 0.0
    for name, sv in slots.items():
        if sv is None:
            continue
        nv, ns = norm(value), norm(str(sv))
        if name == "quantity":
            # numbers are too generic to template anywhere but quantity-shaped steps
            if action in (ActionType.SET_QUANTITY, ActionType.TYPE) and nv == ns:
                return name
            continue
        if len(ns) < 1:
            continue
        # Check both similar() and direct substring containment
        if not similar(value, str(sv)) and ns not in nv and nv not in ns:
            continue
        score = 2.0 if nv == ns else min(len(nv), len(ns)) / max(len(nv), len(ns))
        if score > best_score:
            best, best_score = name, score
    return best


IMPLIED_SLOT = {ActionType.SELECT_ADDRESS: "address", ActionType.SET_QUANTITY: "quantity"}


def generalize(
    actions: list[ObservedAction], slots: dict[str, Any]
) -> tuple[list[Step], list[str], dict[str, Any]]:
    """Turn observed actions into template steps. Stops at the first sensitive step.

    Returns (steps, warnings, slots) - slots gains defaults for slots implied by the action type
    (e.g. an unspoken address becomes whatever address the user tapped while teaching).
    """
    slots = dict(slots)
    steps: list[Step] = []
    warnings: list[str] = []
    for i, a in enumerate(actions):
        if cat := safety.classify_action(a):
            warnings.append(
                f"Demonstration reached a {cat} screen at action {i + 1}; flow ends there and "
                "control is handed to the user at replay time. Nothing from that point was stored."
            )
            break
        step = Step(index=len(steps), action=a.action, value=a.value, target=a.target.model_copy() if a.target else None)
        step.taughtValue = a.value
        refs: list[str] = []

        if (name := _slot_for(a.value, slots, a.action)) is not None:
            step.value = "{{%s}}" % name
            refs.append(name)
        if step.target is not None:
            step.taughtTargetText = step.target.text
            for field in ("text", "contentDescription", "parentText"):
                if (name := _slot_for(getattr(step.target, field), slots, a.action)) is not None:
                    setattr(step.target, field, "{{%s}}" % name)
                    refs.append(name)
        # SELECT_ADDRESS / SET_QUANTITY always depend on their slot, spoken or not
        implied = IMPLIED_SLOT.get(a.action)
        if implied and implied not in refs:
            taught = a.value or (a.target.text or a.target.contentDescription if a.target else None)
            if slots.get(implied) is None and taught is not None:
                slots[implied] = int(taught) if implied == "quantity" and taught.isdigit() else taught
            if slots.get(implied) is not None:
                step.value = "{{%s}}" % implied
                refs.append(implied)
                if implied == "address" and step.target is not None and step.target.text == taught:
                    step.target.text = "{{address}}"

        step.slotRefs = sorted(set(refs))
        steps.append(step)
    return steps, warnings, slots


def resolve(steps: list[Step], slots: dict[str, Any]) -> tuple[list[Step], list[str]]:
    """Substitute slot values into template steps. Returns (resolved_steps, missing_slot_names)."""
    missing: list[str] = []

    def sub(s: str | None) -> str | None:
        if s is None:
            return None

        def repl(m: re.Match[str]) -> str:
            v = slots.get(m.group(1))
            if v is None:
                missing.append(m.group(1))
                return m.group(0)
            return str(v)

        return SLOT_RE.sub(repl, s)

    out = []
    for st in steps:
        r = st.model_copy(deep=True)
        r.value = sub(r.value)
        if r.target is not None:
            r.target.text = sub(r.target.text)
            r.target.contentDescription = sub(r.target.contentDescription)
            r.target.parentText = sub(r.target.parentText)
        out.append(r)
    return out, sorted(set(missing))
