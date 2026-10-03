"""Flow matching (roadmap phase G4): new utterance -> exactly one learned flow, or a question.

Never silently picks an unrelated flow: 0 matches -> NOT_LEARNED, a tie -> ASK_USER.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import Extraction, Flow, Option
from .text import jaccard, norm, similar, tokens

SIMILARITY_THRESHOLD = 0.5  # for custom (non-controlled) intents matched on wording alone
TIE_MARGIN = 0.15


@dataclass
class MatchResult:
    flow: Flow | None = None
    ambiguous: list[Flow] = field(default_factory=list)
    reason: str | None = None


def _similarity(utterance: str, flow: Flow) -> float:
    u = tokens(utterance)
    return max((jaccard(u, tokens(t)) for t in flow.utterances), default=0.0)


def _score(ex: Extraction, utterance: str, flow: Flow) -> float:
    shared = set(ex.slots) & {k for k, v in flow.slots.items() if v is not None}
    slot_cov = len(shared) / max(len(ex.slots), 1)
    # restaurant/seller is a strong discriminator between two flows with the same intent
    same_place = any(
        k in ex.slots and flow.slots.get(k) and norm(str(ex.slots[k])) == norm(str(flow.slots[k]))
        for k in ("restaurant", "seller")
    )
    return 0.5 * slot_cov + 0.3 * _similarity(utterance, flow) + (0.2 if same_place else 0.0)


def label(flow: Flow) -> str:
    detail = ", ".join(f"{k}: {v}" for k, v in flow.slots.items() if v is not None and k != "quantity")
    return f"{flow.intent.replace('_', ' ')} on {flow.app or 'current app'}" + (f" ({detail})" if detail else "")


def match(ex: Extraction, utterance: str, current_app: str | None, flows: list[Flow]) -> MatchResult:
    if ex.intent != "unknown_intent":
        candidates = [f for f in flows if f.intent == ex.intent]
    else:
        candidates = [f for f in flows if _similarity(utterance, f) >= SIMILARITY_THRESHOLD]

    if not candidates:
        return MatchResult(reason="No learned flow for this request.")

    wanted_app = ex.app or None
    if wanted_app:
        on_app = [f for f in candidates if similar(f.app, wanted_app)]
        if not on_app:
            known = sorted({f.app or "?" for f in candidates})
            return MatchResult(
                reason=f"I know how to do this on {', '.join(known)} but haven't been taught on {wanted_app}."
            )
        candidates = on_app
    elif current_app:
        on_app = [f for f in candidates if similar(f.app, current_app)]
        candidates = on_app or candidates

    if len(candidates) == 1:
        return MatchResult(flow=candidates[0])

    ranked = sorted(candidates, key=lambda f: _score(ex, utterance, f), reverse=True)
    top, second = _score(ex, utterance, ranked[0]), _score(ex, utterance, ranked[1])
    if top - second > TIE_MARGIN:
        return MatchResult(flow=ranked[0])
    tied = [f for f in ranked if top - _score(ex, utterance, f) <= TIE_MARGIN]
    return MatchResult(ambiguous=tied, reason="More than one learned flow fits.")


def options(flows: list[Flow]) -> list[Option]:
    return [Option(flowId=f.flowId, label=label(f)) for f in flows]
