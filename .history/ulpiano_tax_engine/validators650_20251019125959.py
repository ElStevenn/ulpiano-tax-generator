from __future__ import annotations

from typing import List, Tuple

from .messages import build_error, build_warning
from .normalization import normalize_date
from .validation_utils import (
    validate_common_presenter,
    date_not_after_now,
    sum_percentages,
    validate_payment,
)


def validate_model_650(data: dict) -> Tuple[List[dict], List[dict]]:
    errors: List[dict] = []
    warnings: List[dict] = []

    e, w = validate_common_presenter(data)
    errors.extend(e)
    warnings.extend(w)

    # Decujus date
    dec = data.get("decedent") or {}
    fecha = normalize_date(dec.get("fechaFallecimiento"))
    if not fecha:
        errors.append(build_error("E-650-DEC-001", field="decedent.fechaFallecimiento"))
    elif not date_not_after_now(fecha):
        errors.append(build_error("E-COM-DATE-001", field="decedent.fechaFallecimiento"))

    # Heirs
    heirs = data.get("heirs") or []
    if len(heirs) < 1:
        errors.append(build_error("E-650-HEI-001", field="heirs"))
    else:
        total_pct = sum_percentages(heirs, "porcentajeParticipacionPct")
        if abs(total_pct - 100.0) > 0.01:
            errors.append(build_error("E-650-HEI-002", field="heirs[].porcentajeParticipacionPct"))
        # Missing addresses warnings
        for idx, h in enumerate(heirs, start=1):
            if not (h.get("domicilio") or {}).get("via"):
                warnings.append(build_warning("W-650-HEI-001", params={"n": idx}))

    # Assets
    assets = data.get("assets") or []
    if len(assets) < 1:
        errors.append(build_error("E-650-AST-001", field="assets"))
    else:
        for a in assets:
            if a.get("fechaValoracion") in (None, ""):
                warnings.append(build_warning("W-AST-VAL-001"))

    # Payment validations
    e, w = validate_payment(data.get("autoliquidation") or {})
    errors.extend(e)
    warnings.extend(w)

    return errors, warnings


