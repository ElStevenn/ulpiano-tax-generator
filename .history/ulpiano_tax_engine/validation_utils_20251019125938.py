from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, List, Tuple

from .messages import build_error, build_warning


_DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def is_valid_cp(cp: Any) -> bool:
    s = str(cp or "").strip()
    return len(s) == 5 and s.isdigit()


def is_valid_nif(nif: Any) -> bool:
    s = str(nif or "").strip().upper()
    if not s:
        return False
    # DNI: 8 digits + letter
    m = re.fullmatch(r"(\d{8})([A-Z])", s)
    if m:
        number = int(m.group(1))
        letter = m.group(2)
        return _DNI_LETTERS[number % 23] == letter
    # NIE: starts with X/Y/Z + 7 digits + letter
    m = re.fullmatch(r"([XYZ])(\d{7})([A-Z])", s)
    if m:
        prefix = {"X": "0", "Y": "1", "Z": "2"}[m.group(1)]
        num = int(prefix + m.group(2))
        letter = m.group(3)
        return _DNI_LETTERS[num % 23] == letter
    # Fallback minimal CIF pattern
    if re.fullmatch(r"[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]", s):
        return True
    return False


def is_valid_iban(iban: Any) -> bool:
    s = str(iban or "").replace(" ", "").replace("-", "").upper()
    if len(s) < 15 or len(s) > 34:
        return False
    if not re.fullmatch(r"[A-Z0-9]+", s):
        return False
    # Move first four chars to end, convert letters to numbers (A=10...Z=35)
    rearranged = s[4:] + s[:4]
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    # Mod-97 check
    remainder = 0
    for ch in digits:
        remainder = (remainder * 10 + int(ch)) % 97
    return remainder == 1


def date_not_after_now(date_iso: str) -> bool:
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%d")
        now = datetime.now(timezone.utc).date()
        return dt.date() <= now
    except Exception:
        return False


def sum_percentages(items: list, key: str) -> float:
    total = 0.0
    for it in items:
        try:
            total += float(it.get(key) or 0)
        except Exception:
            continue
    return total


def validate_common_presenter(data: dict) -> Tuple[list, list]:
    errors: List[dict] = []
    warnings: List[dict] = []
    presenter = data.get("presenter") or {}
    nif = presenter.get("nif")
    nombre = presenter.get("nombre") or presenter.get("razonSocial") or presenter.get("primerApellido")
    if not nif:
        errors.append(build_error("E-COM-001", field="presenter.nif"))
    elif not is_valid_nif(nif):
        errors.append(build_error("E-COM-002", field="presenter.nif"))
    if not nombre:
        errors.append(build_error("E-COM-ID-001", field="presenter"))

    dom = presenter.get("domicilio") or {}
    cp = dom.get("cp")
    if cp is not None and not is_valid_cp(cp):
        errors.append(build_error("E-COM-ADDR-001", field="presenter.domicilio.cp"))

    if not presenter.get("email"):
        warnings.append(build_warning("W-COM-EMAIL-001"))
    if not presenter.get("telefono"):
        warnings.append(build_warning("W-COM-PHONE-001"))
    if not dom.get("pais"):
        warnings.append(build_warning("W-COM-LOC-001"))

    return errors, warnings


def validate_payment(autoliquidation: dict) -> Tuple[list, list]:
    errors: List[dict] = []
    warnings: List[dict] = []
    forma = (autoliquidation or {}).get("formaPago")
    if not forma:
        warnings.append(build_warning("W-PAY-001"))
    if forma == "domiciliacion":
        iban = (autoliquidation or {}).get("iban")
        if not iban:
            errors.append(build_error("E-COM-IBAN-001", field="autoliquidation.iban"))
        elif not is_valid_iban(iban):
            errors.append(build_error("E-COM-IBAN-002", field="autoliquidation.iban"))
    if forma == "nrc":
        nrc = (autoliquidation or {}).get("nrc")
        if not nrc:
            errors.append(build_error("E-COM-NRC-001", field="autoliquidation.nrc"))
    return errors, warnings


