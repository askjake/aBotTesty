#!/usr/bin/env python3
"""PPV / On Demand price extraction and purchase-limit helpers."""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional, Tuple

PRICE_RX = re.compile(r"\$\s*(\d{1,4}(?:[\.,]\d{2})?)")
FREE_RX = re.compile(r"\b(?:free|no\s+cost|included|complimentary|available\s+on\s+demand|free\s+on\s+demand)\b", re.I)
PAID_WORD_RX = re.compile(r"\b(?:rent|rental|buy|purchase|order|charge|price|event)\b", re.I)
UNLIMITED_RX = re.compile(r"^\s*(?:unlimited|unlimited\s*\$?|none|null|all|∞|inf|infinite|no\s*limit|)\s*$", re.I)


def clean_text(value: Any, limit: int = 1200) -> str:
    s = str(value or "")
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = s.replace("–", "-").replace("—", "-").replace("•", " ")
    return re.sub(r"\s+", " ", s).strip()[:limit]


def parse_money(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = clean_text(value, 80).replace(",", ".")
    if not s:
        return None
    m = PRICE_RX.search(s)
    if m:
        s = m.group(1).replace(",", ".")
    else:
        m2 = re.search(r"\b(\d{1,4}(?:\.\d{2})?)\b", s)
        if not m2:
            return None
        s = m2.group(1)
    try:
        amount = float(s)
    except Exception:
        return None
    if not math.isfinite(amount) or amount < 0:
        return None
    return round(amount, 2)


def parse_limit_value(value: Any) -> Optional[float]:
    """Return None for unlimited, otherwise a non-negative dollar limit."""
    if value is None:
        return None
    s = clean_text(value, 80)
    if UNLIMITED_RX.match(s):
        return None
    amount = parse_money(s)
    if amount is None:
        return None
    return max(0.0, round(amount, 2))


def format_limit(value: Optional[float]) -> str:
    return "unlimited" if value is None else f"${value:.2f}"


def extract_purchase_pricing(*texts: Any) -> Dict[str, Any]:
    """Extract PPV/On Demand price from OCR/focus text.

    A paid price wins over free text because screens may say both "available on
    demand" and "$24.99".  If no dollar amount appears but FREE-like language is
    present, the asset is treated as $0.00.
    """
    text = clean_text(" ".join(clean_text(t, 2000) for t in texts if t is not None), 4000)
    amounts = [parse_money(m.group(0)) for m in PRICE_RX.finditer(text)]
    amounts = [a for a in amounts if a is not None]
    flags = []
    if amounts:
        # Use the highest amount on purchase-option screens; repeated OCR of the
        # same price is normal.  A zero/free token should not hide a paid rent price.
        amount = max(amounts)
        return {
            "found": True,
            "amount": round(float(amount), 2),
            "price_text": f"${float(amount):.2f}",
            "currency": "USD",
            "category": "paid" if amount > 0 else "free",
            "all_amounts": [round(float(a), 2) for a in amounts],
            "confidence": 0.95,
            "flags": flags,
        }
    if FREE_RX.search(text):
        return {
            "found": True,
            "amount": 0.0,
            "price_text": "$0.00",
            "currency": "USD",
            "category": "free",
            "all_amounts": [],
            "confidence": 0.8,
            "flags": ["free_text_no_dollar_amount"],
        }
    if PAID_WORD_RX.search(text):
        flags.append("purchase_words_without_price")
    return {
        "found": False,
        "amount": None,
        "price_text": "",
        "currency": "USD",
        "category": "unknown",
        "all_amounts": [],
        "confidence": 0.0,
        "flags": flags,
    }


def check_purchase_limits(amount: Optional[float], individual_limit: Optional[float], session_limit: Optional[float], session_spent: float) -> Tuple[bool, str, Dict[str, Any]]:
    """Return allow, reason, diagnostics."""
    spent = float(session_spent or 0.0)
    diagnostics = {
        "amount": amount,
        "individual_limit": individual_limit,
        "session_limit": session_limit,
        "session_spent": round(spent, 2),
        "session_remaining": None if session_limit is None else round(max(0.0, session_limit - spent), 2),
    }
    if amount is None:
        # Unknown price is allowed only when both limits are unlimited.
        if individual_limit is None and session_limit is None:
            return True, "price_unknown_but_limits_unlimited", diagnostics
        return False, "price_unknown_under_limited_session", diagnostics
    amount = round(float(amount), 2)
    if individual_limit is not None and amount > float(individual_limit) + 1e-9:
        return False, "price_exceeds_individual_limit", diagnostics
    if session_limit is not None and spent + amount > float(session_limit) + 1e-9:
        return False, "price_exceeds_session_limit", diagnostics
    return True, "within_limits", diagnostics
