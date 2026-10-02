"""Small text-normalization helpers shared by the extractor, generalizer and matcher."""
import re
from difflib import SequenceMatcher

STOPWORDS = {
    "a", "an", "the", "me", "my", "i", "please", "some", "to", "of", "for", "on", "in", "from",
    "get", "want", "would", "like", "can", "you", "could", "it", "and", "with", "order", "add",
    "buy", "cart", "just", "now", "quickly",
}


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str | None) -> set[str]:
    return {t for t in norm(s).split() if t not in STOPWORDS}


def similar(a: str | None, b: str | None, threshold: float = 0.6) -> bool:
    """True if a and b refer to the same thing: equal, one contains the other, or fuzzy-close.

    Length-ratio guards prevent incidental substring matches, e.g. we don't want
    'large' (typed to select a size) to match the item slot 'large black shirt',
    nor 'black shirt' (searched) to match 'large black shirt' and then get replaced
    by the full slot value during replay.
    """
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = sorted((na, nb), key=len)
    len_ratio = len(short) / len(long_)  # always <= 1.0
    # word-boundary substring match (e.g. "margherita" in "margherita pizza (regular)")
    # Guard at 0.40 so a brand/item name matches even when the app appends variant info
    # like "(Regular)" or "30 mins away". Still blocks single-char noise.
    if len(short) >= 3 and len_ratio >= 0.40 and re.search(rf"\b{re.escape(short)}\b", long_):
        return True
    # relaxed substring match without word boundaries (e.g. "dominos" in "dominos pizza")
    # Stricter 0.65 guard: blocks "large" (0.29) matching "large black shirt".
    if len(short) >= 4 and len_ratio >= 0.65 and short in long_:
        return True
    # token overlap: if most tokens from the shorter string appear in the longer one.
    # Guard: strings must also be close in word-count (within 1 word of each other)
    # so "black shirt" (2 words) doesn't fully match "large black shirt" (3 words).
    short_tok = set(short.split())
    long_tok = set(long_.split())
    tok_ratio = len(short_tok) / max(len(long_tok), 1)
    if (len(short_tok) >= 2 and short_tok
            and len(short_tok & long_tok) / len(short_tok) >= 0.75
            and tok_ratio >= 0.70):
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
