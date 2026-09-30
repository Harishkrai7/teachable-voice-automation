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
    """True if a and b refer to the same thing: equal, one contains the other, or fuzzy-close."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = sorted((na, nb), key=len)
    # word-boundary substring match (e.g. "margherita" in "margherita pizza")
    if len(short) >= 3 and re.search(rf"\b{re.escape(short)}\b", long_):
        return True
    # relaxed substring match without word boundaries (e.g. "dominos" in "dominos pizza")
    if len(short) >= 4 and short in long_:
        return True
    # token overlap: if most tokens from the shorter string appear in the longer one
    short_tok = set(short.split())
    long_tok = set(long_.split())
    if len(short_tok) >= 2 and short_tok and len(short_tok & long_tok) / len(short_tok) >= 0.75:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
