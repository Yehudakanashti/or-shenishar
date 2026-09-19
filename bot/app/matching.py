"""התאמת מוצר לפוסט לפי מילות מפתח. משמש כגיבוי ל-AI וכבדיקה שלו."""
import re
from typing import Any

PUNCT_RE = re.compile(r"[^\w֐-׿ ]+")
NIQQUD_RE = re.compile(r"[֑-ׇ]")


def normalize(text: str) -> str:
    text = NIQQUD_RE.sub("", text or "")
    text = PUNCT_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def score_product(post_text: str, product: dict[str, Any]) -> float:
    haystack = normalize(post_text)
    if not haystack:
        return 0.0
    score = 0.0
    for keyword in product.get("keywords") or []:
        needle = normalize(str(keyword))
        if needle and needle in haystack:
            score += 1.0 + 0.25 * len(needle.split())
    for field in ("name", "audience", "tagline"):
        for word in normalize(product.get(field, "")).split():
            if len(word) > 3 and word in haystack:
                score += 0.35
    return round(score, 3)


def rank_products(post_text: str, products: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    ranked = [(p, score_product(post_text, p)) for p in products if p.get("active")]
    return sorted(ranked, key=lambda pair: pair[1], reverse=True)


def best_product(post_text: str, products: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = rank_products(post_text, products)
    if ranked and ranked[0][1] > 0:
        return ranked[0][0]
    return ranked[0][0] if ranked else None
