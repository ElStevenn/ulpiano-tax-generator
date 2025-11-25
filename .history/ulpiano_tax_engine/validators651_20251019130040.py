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


def validate_model_651(data: dict) -> Tuple[List[dict], List[dict]]:
    errors: List[dict] = []
    warnings: List[dict] = []

    e, w = validate_common_presenter(data)
    errors.extend(e)
    warnings.extend(w)

    # Donaciones
    dons = data.get("donations") or []
    if len(dons) < 1:
        errors.append(build_error("E-651-DON-002", field="donations"))
    else:
        has_any_date = False
        for dn in dons:
            fecha = normalize_date(dn.get("fechaDonacion"))
            if fecha:
                has_any_date = True
                if not date_not_after_now(fecha):
                    errors.append(build_error("E-COM-DATE-001", field="donations[].fechaDonacion"))
        if not has_any_date:
            errors.append(build_error("E-651-DON-001", field="donations[].fechaDonacion"))

    # Donatarios
    donees = data.get("donees") or []
    if len(donees) < 1:
        # Not explicitly specified as blocking, but required for distribution → treat as error via percentages rule
        errors.append(build_error("E-651-DON-002", field="donees"))
    else:
        total_pct = sum_percentages(donees, "porcentajeParticipacionPct")
        if abs(total_pct - 100.0) > 0.01:
            # Reuse coherent message from 650 context not defined for 651 → define locally
            errors.append({
                "code": "E-651-DON-PCT-001",
                "message": "La suma de participaciones de donatarios debe ser 100%.",
                "field": "donees[].porcentajeParticipacionPct",
            })

    # Documento notarial warnings
    doc = data.get("documentacionNotarial") or {}
    if (doc.get("tipoDocumento") or "").lower() == "privado":
        # If private, warn no notary
        warnings.append(build_warning("W-651-DON-001"))

    # Payment validations
    e, w = validate_payment(data.get("autoliquidation") or {})
    errors.extend(e)
    warnings.extend(w)

    return errors, warnings


