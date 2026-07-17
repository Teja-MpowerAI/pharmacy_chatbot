"""
Fuzzy medicine-name matching, alias correction, and basket price enrichment.

Ported from the hand-rolled JavaScript in the n8n workflow (Build Delivery
Summary / Calculate Pickup Total), with fixes:
  * inputs are trimmed before comparison,
  * alias correction runs before fuzzy matching,
  * a single implementation is shared by the prescription, pickup and delivery
    flows instead of three slightly different copies.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


def _norm(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def similarity(a: str, b: str) -> float:
    """0..1 similarity of two names, ignoring case/spacing/punctuation."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def fuzzy_match(name1: str, name2: str) -> bool:
    """
    Loose medicine-name match: substring either direction, shared 4-char prefix,
    or >70% character overlap. Intentionally forgiving to absorb OCR noise.
    """
    a, b = _norm(name1), _norm(name2)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    if len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4]:
        return True
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    matches = sum(1 for ch in shorter if ch in longer)
    return (matches / len(shorter)) > 0.7 if shorter else False


def correct_alias(name: str, aliases: List[Dict[str, Any]]) -> str:
    """Map a (possibly misspelled) name to its canonical name via the alias table."""
    low = (name or "").strip().lower()
    for a in aliases:
        alias = (a.get("alias") or "").strip().lower()
        if not alias:
            continue
        if alias == low or alias in low or low in alias:
            return a.get("correct_name") or name
    return name


def resolve_medicine(
    query: str,
    medicines: List[Dict[str, Any]],
    aliases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Resolve a user's (possibly misspelled / oddly-spaced / aliased) medicine
    text to a catalogue entry.

    Returns:
      {
        "match": <medicine dict or None>,   # best candidate, if good enough
        "quality": "exact" | "strong" | "weak" | "none",
        "score": float,                     # 0..1 best similarity
        "corrected": str,                   # alias-corrected query
        "alternatives": [<medicine dict>],  # up to 3 other plausible matches
      }

    quality guide:
      exact  -> normalized name equals the query/corrected query
      strong -> score >= 0.72 or a clean substring hit (safe to use directly)
      weak   -> 0.5 <= score < 0.72 (ask "did you mean ...?")
      none   -> below 0.5 (treat as not found)
    """
    q = (query or "").strip()
    corrected = correct_alias(q, aliases)
    nq, nc = _norm(q), _norm(corrected)

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for m in medicines:
        name = m.get("name", "")
        nm = _norm(name)
        if not nm:
            continue
        base = max(similarity(q, name), similarity(corrected, name))
        # Substring in either direction is a strong signal ("dolo" -> "Dolo 650").
        if nm and (nm in nq or nq in nm or nm in nc or nc in nm):
            base = max(base, 0.9)
        scored.append((base, m))

    if not scored:
        return {"match": None, "quality": "none", "score": 0.0,
                "corrected": corrected, "alternatives": []}

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best = scored[0]
    best_norm = _norm(best.get("name", ""))

    if best_norm and (best_norm == nq or best_norm == nc):
        quality = "exact"
    elif best_score >= 0.72:
        quality = "strong"
    elif best_score >= 0.5:
        quality = "weak"
    else:
        quality = "none"

    alternatives = [m for s, m in scored[1:4] if s >= 0.5]
    return {
        "match": best if quality != "none" else None,
        "quality": quality,
        "score": round(best_score, 3),
        "corrected": corrected,
        "alternatives": alternatives,
    }


def find_price(
    name: str, medicines: List[Dict[str, Any]], aliases: List[Dict[str, Any]]
) -> float:
    """Best-effort catalogue price for a medicine name (0.0 if not found)."""
    corrected = correct_alias(name, aliases)
    for m in medicines:
        if fuzzy_match(m.get("name", ""), corrected):
            try:
                return float(m.get("price") or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def has_preset_prices(basket: List[Dict[str, Any]]) -> bool:
    """
    True if any basket item already carries a real price. Typed orders do; raw
    prescription baskets do not. Used to decide whether the delivery minimum
    order rule applies (prescription orders only).
    """
    for item in basket:
        try:
            if float(item.get("price") or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def enrich_basket_prices(
    basket: List[Dict[str, Any]],
    medicines: List[Dict[str, Any]],
    aliases: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Return (enriched_basket, subtotal). Items that already have a price keep it;
    price-less (prescription) items get a catalogue lookup.
    """
    enriched: List[Dict[str, Any]] = []
    for item in basket:
        qty = int(item.get("quantity") or 1)
        try:
            existing = float(item.get("price") or 0)
        except (TypeError, ValueError):
            existing = 0.0
        price = existing if existing > 0 else find_price(item.get("name", ""), medicines, aliases)
        enriched.append(
            {
                "name": item.get("name", ""),
                "dosage": item.get("dosage", ""),
                "quantity": qty,
                "price": price,
            }
        )
    subtotal = sum(i["price"] * i["quantity"] for i in enriched)
    return enriched, subtotal
