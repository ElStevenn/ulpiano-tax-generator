from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Optional


def normalize_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def format_date_for_pdf(date_iso: Optional[str]) -> Optional[str]:
    if not date_iso:
        return None
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return None


def normalize_decimal(value: Any, digits: int = 2) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip().replace(" ", "")
    if "," in text and "." in text:
        # Remove thousands sep and keep decimal sep
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        q = Decimal("1." + ("0" * digits))
        return Decimal(text).quantize(q, rounding=ROUND_HALF_EVEN)
    except Exception:
        return None


def decimal_to_xml_text(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    return f"{value:.2f}"


def normalize_percentage(value: Any) -> Optional[Decimal]:
    return normalize_decimal(value, digits=2)


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    # Collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def normalize_iban(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).replace(" ", "").replace("-", "").upper()


