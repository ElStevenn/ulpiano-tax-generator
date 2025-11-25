from typing import Optional


STATE_MESSAGES: dict[str, str] = {
    "ok": "Generación completada correctamente.",
    "incompleto": "Generación completada con advertencias.",
    "errores_de_validacion": "No se han podido generar los artefactos por errores de validación.",
}


ERROR_MESSAGES: dict[str, str] = {
    "E-COM-001": "Falta el NIF del presentador.",
    "E-COM-002": "NIF/NIE del presentador no tiene un formato válido.",
    "E-650-DEC-001": "Falta la fecha de fallecimiento.",
    "E-650-HEI-001": "Debe incluir al menos un heredero.",
    "E-650-HEI-002": "La suma de participaciones de herederos debe ser 100%.",
    "E-650-AST-001": "Debe incluir al menos un bien o derecho.",
    "E-651-DON-001": "Falta la fecha de donación.",
    "E-651-DON-002": "Debe incluir al menos una donación.",
    "E-COM-IBAN-001": "IBAN requerido para domiciliación.",
    "E-COM-IBAN-002": "El IBAN no es válido.",
    "E-COM-NRC-001": "NRC requerido cuando la forma de pago es NRC.",
    "E-COM-DATE-001": "La fecha de devengo no puede ser posterior a la fecha de presentación.",
    "E-COM-ADDR-001": "Código postal inválido.",
    "E-COM-ID-001": "Falta el identificador mínimo del obligado tributario (NIF y nombre).",
    "E-COM-XML-001": "Datos no cumplen el esquema XSD de la AEAT para el modelo.",
}


WARNING_MESSAGES: dict[str, str] = {
    "W-COM-EMAIL-001": "Falta correo electrónico del presentador.",
    "W-COM-PHONE-001": "Falta teléfono de contacto.",
    "W-650-HEI-001": "Falta domicilio del heredero {n}.",
    "W-651-DON-001": "No se ha informado notario y el documento es privado.",
    "W-AST-VAL-001": "Fecha de valoración no informada; se usará fecha de devengo.",
    "W-COM-LOC-001": "País no informado; se asume ES.",
    "W-COM-NAME-001": "Nombre o apellidos contienen caracteres no estándar; se normalizarán.",
    "W-PAY-001": "Forma de pago no informada; se marcará como ‘otras’.",
    "W-RED-EMP-001": "Reducción por empresa familiar sin documentación adjunta.",
}


def build_error(code: str, field: Optional[str] = None) -> dict:
    message = ERROR_MESSAGES.get(code, code)
    payload: dict = {"code": code, "message": message}
    if field:
        payload["field"] = field
    return payload


def build_warning(code: str, params: Optional[dict] = None) -> dict:
    text = WARNING_MESSAGES.get(code, code)
    if params:
        try:
            text = text.format(**params)
        except Exception:
            # If formatting fails, keep as-is
            pass
    return {"code": code, "message": text}


def get_state_message(state: str) -> str:
    return STATE_MESSAGES.get(state, state)


