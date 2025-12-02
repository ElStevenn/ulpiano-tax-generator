#!/usr/bin/env python3
"""
Genera un PDF relleno del Modelo 650 (ATC-650E-6) de Cataluña superponiendo datos
procedentes de un fichero JSON estructurado sobre la plantilla oficial.

El script realiza cuatro pasos principales:
1. Cargar y validar el payload JSON contra `tax_models/data_models/mod650cat_data_structure.json`.
2. Aplanar el JSON para que cada campo pueda referenciarse con una ruta punteada
   (ej. `subject.nif`, `settlement.cuotaIntegraBox16`).
3. Dibujar cada valor en una capa PDF transparente respetando las coordenadas
   definidas en `FIELD_MAPPINGS`.
4. Combinar la capa con `tax_models/models/650_es-cat.pdf` y escribir el fichero final
   en `generated/`.

Uso:
    python scripts/generate_mod650cat_pdf_clean_version.py \
        --data tax_models/json_examples/mod650cat_example.json \
        --output generated/model650cat_overlay.pdf

Los argumentos por defecto ya apuntan al JSON de muestra, la definición de estructura
y la plantilla dentro de este repositorio, así que ejecutar el script sin parámetros
generará un PDF relleno en `generated/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Añadido para aritmética decimal precisa en campos financieros
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BASE_DIR / "tax_models" / "json_examples" / "mod650cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "data_models" / "mod650cat_data_structure.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "models" / "650_es-cat.pdf"
DEFAULT_OUTPUT_DIR = BASE_DIR / "generated"
# Desplazamientos (multiplicadores) para centrar la "X" dibujada dentro de checkboxes
CHECKBOX_X_OFFSET_MULT = -0.35  # desplazamiento a la izquierda relativo al tamaño de fuente
CHECKBOX_Y_OFFSET_MULT = -0.45  # desplazamiento hacia abajo relativo al tamaño de fuente


@dataclass(frozen=True)
class FieldMapping:
    """Configuración usada para colocar un valor JSON sobre el PDF."""

    key: str
    pages: Sequence[int]
    x: float
    y_from_top: float
    font_size: float = 10
    field_type: str = "text"  # text | checkbox
    formatter: str = "text"  # text | date | decimal | integer
    true_label: str = "X"


FIRST_COPY_PAGES = [0, 1, 2, 3]
SETTLEMENT_PAGES = [4, 5]
ALL_PAGES = [0, 1, 2, 3, 4, 5]

FIELD_MAPPINGS: List[FieldMapping] = [
    # Encabezado
    FieldMapping("encabezado.cpr", ALL_PAGES, x=170, y_from_top=95, font_size=11),
    # Sujeto / presentador
    FieldMapping("sujeto.sujetoNif", FIRST_COPY_PAGES, x=70, y_from_top=209, font_size=11),
    FieldMapping(
        "sujeto.sujetoNombreCompletoRazonSocial",
        FIRST_COPY_PAGES,
        x=138,
        y_from_top=222,
        font_size=10,
    ),
    FieldMapping("sujeto.sujetoNombreVia", FIRST_COPY_PAGES, x=33, y_from_top=242, font_size=8),
    FieldMapping("sujeto.sujetoNumeroVia", FIRST_COPY_PAGES, x=230, y_from_top=242, font_size=9),
    FieldMapping("sujeto.sujetoEscalera", FIRST_COPY_PAGES, x=266, y_from_top=242, font_size=9),
    FieldMapping("sujeto.sujetoPiso", FIRST_COPY_PAGES, x=280, y_from_top=242, font_size=9),
    FieldMapping("sujeto.sujetoPuerta", FIRST_COPY_PAGES, x=300, y_from_top=242, font_size=9),
    FieldMapping("sujeto.sujetoCodigoPostal", FIRST_COPY_PAGES, x=34, y_from_top=263, font_size=10),
    FieldMapping("sujeto.sujetoMunicipio", FIRST_COPY_PAGES, x=100, y_from_top=263),
    FieldMapping("sujeto.sujetoProvincia", FIRST_COPY_PAGES, x=230, y_from_top=263),
    FieldMapping("sujeto.sujetoPais", FIRST_COPY_PAGES, x=290, y_from_top=263),
    FieldMapping("sujeto.sujetoTelefono", FIRST_COPY_PAGES, x=33, y_from_top=287),
    FieldMapping("sujeto.sujetoCorreoElectronico", FIRST_COPY_PAGES, x=126, y_from_top=287),
    FieldMapping(
        "sujeto.sujetoFechaNacimiento",
        FIRST_COPY_PAGES,
        x=105,
        y_from_top=301,
        formatter="date",
        font_size=9,
    ),
    FieldMapping("sujeto.sujetoPatrimonioPreexistente", FIRST_COPY_PAGES, x=86, y_from_top=320, formatter="decimal"),
    FieldMapping("sujeto.sujetoParentesco", FIRST_COPY_PAGES, x=205, y_from_top=301),
    FieldMapping("sujeto.sujetoGrupoParentesco", FIRST_COPY_PAGES, x=295, y_from_top=301),
    FieldMapping("sujeto.sujetoPorcentajeDiscapacidad", FIRST_COPY_PAGES, x=278, y_from_top=320, formatter="integer"),
    FieldMapping("sujeto.sujetoTituloSucesorio", FIRST_COPY_PAGES, x=94, y_from_top=333),
    FieldMapping(
        "sujeto.sujetoTieneDiscapacidad",
        FIRST_COPY_PAGES,
        x=253.0,
        y_from_top=318.7,
        field_type="checkbox",
    ),
    # Fallecido (causante)
    FieldMapping("fallecido.fallecidoNif", FIRST_COPY_PAGES, x=62, y_from_top=367, font_size=11),
    FieldMapping("fallecido.fallecidoNombreCompleto", FIRST_COPY_PAGES, x=105, y_from_top=380, font_size=10),
    FieldMapping("fallecido.fallecidoNombreVia", FIRST_COPY_PAGES, x=33, y_from_top=400, font_size=8),
    FieldMapping("fallecido.fallecidoNumeroVia", FIRST_COPY_PAGES, x=230, y_from_top=400, font_size=9),
    FieldMapping("fallecido.fallecidoEscalera", FIRST_COPY_PAGES, x=266, y_from_top=400, font_size=9),
    FieldMapping("fallecido.fallecidoPiso", FIRST_COPY_PAGES, x=280, y_from_top=400, font_size=9),
    FieldMapping("fallecido.fallecidoPuerta", FIRST_COPY_PAGES, x=300, y_from_top=400, font_size=9),
    FieldMapping("fallecido.fallecidoCodigoPostal", FIRST_COPY_PAGES, x=34, y_from_top=421, font_size=10),
    FieldMapping("fallecido.fallecidoMunicipio", FIRST_COPY_PAGES, x=100, y_from_top=421, font_size=10),
    FieldMapping("fallecido.fallecidoProvincia", FIRST_COPY_PAGES, x=230, y_from_top=421, font_size=10),
    FieldMapping("fallecido.fallecidoPais", FIRST_COPY_PAGES, x=290, y_from_top=421, font_size=10),
    FieldMapping(
        "fallecido.fallecidoObligadoImpuestoPatrimonioUltimosCuatroAnos",
        FIRST_COPY_PAGES,
        x=515.8,
        y_from_top=376.5,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "fallecido.fallecidoEsTestamentaria",
        FIRST_COPY_PAGES,
        x=455.6,
        y_from_top=395.1,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "fallecido.fallecidoEsIntestada",
        FIRST_COPY_PAGES,
        x=404.7,
        y_from_top=396.3,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "fallecido.fallecidoNumeroPersonasInteresadas",
        FIRST_COPY_PAGES,
        x=491,
        y_from_top=417,
        formatter="integer",
        font_size=10,
    ),
    FieldMapping("fallecido.fallecidoNotarioOAutoridad", FIRST_COPY_PAGES, x=124, y_from_top=463, font_size=10),
    FieldMapping(
        "fallecido.fallecidoFechaActaNotarial",
        FIRST_COPY_PAGES,
        x=435,
        y_from_top=463,
        formatter="date_spanish",
        font_size=9,
    ),
    # Bloque de reconocimiento (Presentador/a)
    FieldMapping("reconocimiento.reconocimientoNifFirmante", FIRST_COPY_PAGES, x=65, y_from_top=607, font_size=11),
    FieldMapping("reconocimiento.reconocimientoNombreCompletoFirmante", FIRST_COPY_PAGES, x=136, y_from_top=622, font_size=10),
    FieldMapping("reconocimiento.reconocimientoNombreVia", FIRST_COPY_PAGES, x=33, y_from_top=642, font_size=8),
    FieldMapping("reconocimiento.reconocimientoNumeroVia", FIRST_COPY_PAGES, x=230, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.reconocimientoEscalera", FIRST_COPY_PAGES, x=266, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.reconocimientoPiso", FIRST_COPY_PAGES, x=280, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.reconocimientoPuerta", FIRST_COPY_PAGES, x=300, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.reconocimientoCodigoPostal", FIRST_COPY_PAGES, x=34, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.reconocimientoMunicipio", FIRST_COPY_PAGES, x=100, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.reconocimientoProvincia", FIRST_COPY_PAGES, x=230, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.reconocimientoPais", FIRST_COPY_PAGES, x=290, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.reconocimientoTelefono", FIRST_COPY_PAGES, x=33, y_from_top=687, font_size=10),
    FieldMapping("reconocimiento.reconocimientoCorreoElectronico", FIRST_COPY_PAGES, x=126, y_from_top=687, font_size=10),
    FieldMapping(
        "reconocimiento.reconocimientoAcuerdoDeclaracion",
        FIRST_COPY_PAGES,
        x=470,
        y_from_top=611,
        field_type="checkbox",
        true_label="",
        font_size=9,
    ),
    # Campos de fecha de firma (día, mes, año separados)
    FieldMapping("reconocimiento.reconocimientoFechaFirma", FIRST_COPY_PAGES, x=470, y_from_top=642, formatter="date_spanish", font_size=9),
    # Área de pago (Ingreso)

    FieldMapping("pago.pagoPaisBanco", FIRST_COPY_PAGES, x=50, y_from_top=745, font_size=10),
    FieldMapping("pago.pagoDigitosControlBanco", FIRST_COPY_PAGES, x=79, y_from_top=745, font_size=10),
    FieldMapping("pago.pagoEntidadBanco", FIRST_COPY_PAGES, x=115, y_from_top=745, font_size=10),
    FieldMapping("pago.pagoSucursalBanco", FIRST_COPY_PAGES, x=165, y_from_top=745, font_size=10),
    FieldMapping("pago.pagoDigitosControlBanco2", FIRST_COPY_PAGES, x=222, y_from_top=745, font_size=10),
    FieldMapping("pago.pagoNumeroCuenta", FIRST_COPY_PAGES, x=255, y_from_top=745, font_size=10),
    # Métodos de pago (a la derecha, en la línea superior)
    FieldMapping(
        "pago.pagoCargoEnCuenta",
        FIRST_COPY_PAGES,
        x=362.2,
        y_from_top=725.2,
        field_type="checkbox",
    ),
    FieldMapping(
        "pago.pagoPagoEfectivo",
        FIRST_COPY_PAGES,
        x=439.2,
        y_from_top=726.6,
        field_type="checkbox",
    ),
    # Importe (debajo de "En efectivo", a la derecha)
    FieldMapping("pago.pagoImporte", FIRST_COPY_PAGES, x=450, y_from_top=748, formatter="decimal", font_size=9),
    # Liquidación (autoliquidación) - se aplica a las páginas de cálculo
    FieldMapping("liquidacion.liquidacionBonificacionDiscapacidad", SETTLEMENT_PAGES, x=200, y_from_top=207.5, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionCuotaTributariaCasoGeneral", SETTLEMENT_PAGES, x=189.6, y_from_top=506.4, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionTipoMedioEfectivoCuotaTributaria", SETTLEMENT_PAGES, x=429.0, y_from_top=433.2, formatter="decimal"),
    # Base liquidable real: mostrar en página 4, en blanco en página 5
    FieldMapping("liquidacion.liquidacionBaseLiquidableRealCaja13", [4], x=230, y_from_top=486, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.liquidacionBaseLiquidableRealCaja13", [5], x=504, y_from_top=642.7, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.liquidacionBaseLiquidableTeoricaCaja14", SETTLEMENT_PAGES, x=500, y_from_top=486, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.liquidacionCuotaIntegraCaja16", SETTLEMENT_PAGES, x=230, y_from_top=556, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.liquidacionCuotaTributariaCaja605", SETTLEMENT_PAGES, x=203.8, y_from_top=575.6, formatter="blank", font_size=8.5),
    FieldMapping("liquidacion.liquidacionReduccionExcesoCuotaCaja606", SETTLEMENT_PAGES, x=210.2, y_from_top=598.8, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionCuotaTributariaAjustadaCaja607", SETTLEMENT_PAGES, x=220, y_from_top=616.9, formatter="blank", font_size=8.0),
    FieldMapping("liquidacion.liquidacionTipoMedioEfectivoCaja17", SETTLEMENT_PAGES, x=205, y_from_top=653.5, formatter="decimal", font_size=9.0),
    FieldMapping("liquidacion.liquidacionCuotaTributariaAjustadaCaja18", [4], x=500, y_from_top=642.7, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.liquidacionCuotaTributariaAjustadaCaja18", [5], x=500, y_from_top=666, formatter="decimal", font_size=8.3),
    FieldMapping("liquidacion.liquidacionBonificacionCuotaCaja19", SETTLEMENT_PAGES, x=199.3, y_from_top=710.5, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionDeduccionDobleImposicionCaja20", SETTLEMENT_PAGES, x=198.6, y_from_top=729.3, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionDeduccionCuotasAnterioresCaja21", SETTLEMENT_PAGES, x=198.6, y_from_top=749.1, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionCuotaIngresarCaja22", SETTLEMENT_PAGES, x=198.1, y_from_top=767.1, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionRecargoCaja23", SETTLEMENT_PAGES, x=467.2, y_from_top=708.3, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionInteresesDemoraCaja24", SETTLEMENT_PAGES, x=467.1, y_from_top=728.1, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionTotalIngresarCaja25", SETTLEMENT_PAGES, x=466.7, y_from_top=746.1, formatter="decimal"),
    FieldMapping("liquidacion.liquidacionCuotaTributariaAjustadaCaja607", SETTLEMENT_PAGES, x=461.6, y_from_top=606.1, formatter="blank"),
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_against_structure(data: Dict[str, Any], structure_path: Path) -> None:
    """Realiza una validación básica usando la descripción declarativa de la estructura."""

    structure = load_json(structure_path)["model650cat"]["structure"]
    errors: List[str] = []

    for section in structure:
        section_id = section["id"]
        required_section = section.get("required", False)
        section_data = data.get(section_id)
        if required_section and section_data is None:
            errors.append(f"Falta la sección obligatoria '{section_id}'.")
            continue

        if not isinstance(section_data, dict):
            # Las secciones mapeadas a arrays no forman parte del layout PDF actual.
            continue

        for field in section.get("fields", []):
            field_id = field["id"]
            required_field = field.get("required", False)
            value = section_data.get(field_id)
            if required_field and (value is None or value == ""):
                errors.append(f"Falta el campo requerido '{section_id}.{field_id}'.")

    if errors:
        raise ValueError("Datos inválidos para el Modelo 650 Cataluña:\n- " + "\n- ".join(errors))


def flatten_data(payload: Any, prefix: str = "") -> Dict[str, Any]:
    """Crea un diccionario con rutas punteadas para búsquedas más sencillas."""

    flat: Dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            flat.update(flatten_data(value, new_prefix))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            new_prefix = f"{prefix}[{index}]"
            flat.update(flatten_data(item, new_prefix))
    else:
        flat[prefix] = payload
    return flat


def split_spanish_iban(iban: str) -> Dict[str, str]:
    """
    Parsea un IBAN español en sus componentes.
    Formato: ES + 2 DC + 4 Entidad + 4 Oficina + 2 DC + 10 Cuenta
    Ejemplo: ES1200491500052718123412
    Devuelve: {
        'country': 'ES',
        'controlDigits': '12',
        'entity': '0049',
        'branch': '1500',
        'controlDigits2': '05',
        'accountNumber': '2718123412'
    }
    """
    if not iban or len(iban) < 24:
        return {
            'country': '',
            'controlDigits': '',
            'entity': '',
            'branch': '',
            'controlDigits2': '',
            'accountNumber': ''
        }

    # Eliminar espacios
    iban = iban.replace(' ', '')

    if len(iban) >= 24 and iban[:2] == 'ES':
        return {
            'country': iban[0:2],
            'controlDigits': iban[2:4],
            'entity': iban[4:8],
            'branch': iban[8:12],
            'controlDigits2': iban[12:14],
            'accountNumber': iban[14:24]
        }

    return {
        'country': '',
        'controlDigits': '',
        'entity': '',
        'branch': '',
        'controlDigits2': '',
        'accountNumber': ''
    }


def format_value(value: Any, formatter: str) -> str:
    if value is None:
        return ""
    if formatter == "blank":
        return ""
    if formatter == "text":
        return str(value)
    if formatter == "date":
        if isinstance(value, str) and len(value.split("-")) == 3:
            year, month, day = value.split("-")
            return f"{year} {month} {day}"
        return str(value)
    if formatter == "date_spanish":
        if isinstance(value, str) and len(value.split("-")) == 3:
            year, month, day = value.split("-")
            return f"{day}/{month}/{year}"
        return str(value)
    if formatter == "decimal":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if number == 0:
            return ""
        formatted = f"{number:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    if formatter == "integer":
        try:
            return f"{int(value)}"
        except (TypeError, ValueError):
            return str(value)
    if formatter == "boolean_text":
        return "Sí" if bool(value) else "No"
    return str(value)


# ------------------ ADAPTADOR + VALIDACIÓN Y APLICACIÓN DE REDUCCIONES ------------------

def adapt_old_reducciones_format(data: Dict[str, Any]) -> None:
    """
    Convierte el formato antiguo de 'liquidacion.reducciones' (objeto con campos tipo
    'reduccionParentesco': 1234.0) en la lista de objetos que Pau pide:
    [{casillaReal, casillaTeorica, clave, etiqueta, importeReal, importeTeorico}, ...].
    Si ya está en lista o no existe, no hace nada.
    """
    liquid = data.setdefault("liquidacion", {})
    red = liquid.get("reducciones")
    if red is None or isinstance(red, list):
        return

    if isinstance(red, dict):
        nueva = []
        for clave, valor in red.items():
            if valor is None:
                continue
            try:
                importe = float(valor)
            except Exception:
                importe = 0.0
            entry = {
                "casillaReal": None,
                "casillaTeorica": None,
                "clave": str(clave),
                "etiqueta": str(clave),
                "importeReal": importe,
                "importeTeorico": importe,
            }
            nueva.append(entry)
        liquid["reducciones"] = nueva


def validate_reducciones_section(data: Dict[str, Any]) -> None:
    """
    Valida la estructura mínima en data['liquidacion']['reducciones'].
    Requisitos por entrada: casillaReal, casillaTeorica, clave, etiqueta, importeReal, importeTeorico.
    Lanza ValueError con lista de errores en caso de inconsistencias graves.
    """
    liquid = data.get("liquidacion")
    if liquid is None:
        return

    reducciones = liquid.get("reducciones")
    if reducciones is None:
        return

    if not isinstance(reducciones, list):
        raise ValueError("liquidacion.reducciones debe ser una lista (array) de objetos.")

    required_fields = {"casillaReal", "casillaTeorica", "clave", "etiqueta", "importeReal", "importeTeorico"}
    errors: List[str] = []
    sum_real = Decimal("0")
    sum_teo = Decimal("0")

    for idx, r in enumerate(reducciones):
        if not isinstance(r, dict):
            errors.append(f"reducciones[{idx}] no es un objeto.")
            continue
        missing = required_fields - set(r.keys())
        if missing:
            errors.append(f"reducciones[{idx}] falta(s): {', '.join(sorted(missing))}")
        try:
            imr = Decimal(str(r.get("importeReal", 0) or "0"))
        except (InvalidOperation, TypeError):
            errors.append(f"reducciones[{idx}].importeReal no es numérico: {r.get('importeReal')}")
            imr = Decimal("0")
        try:
            imt = Decimal(str(r.get("importeTeorico", 0) or "0"))
        except (InvalidOperation, TypeError):
            errors.append(f"reducciones[{idx}].importeTeorico no es numérico: {r.get('importeTeorico')}")
            imt = Decimal("0")

        sum_real += imr
        sum_teo += imt

    totales = liquid.get("totalesReducciones")
    if totales:
        try:
            total_real_reported = Decimal(str(totales.get("totalReal", 0) or "0"))
            total_teo_reported = Decimal(str(totales.get("totalTeorico", 0) or "0"))
        except (InvalidOperation, TypeError):
            errors.append("totalesReducciones contiene valores no numéricos.")
            total_real_reported = None
            total_teo_reported = None

        if total_real_reported is not None and total_real_reported != sum_real:
            errors.append(f"totalesReducciones.totalReal ({total_real_reported}) != suma importes reales ({sum_real}).")
        if total_teo_reported is not None and total_teo_reported != sum_teo:
            errors.append(f"totalesReducciones.totalTeorico ({total_teo_reported}) != suma importes teoricos ({sum_teo}).")

    if errors:
        raise ValueError("Errores en reducciones:\n- " + "\n- ".join(errors))


def apply_reducciones_and_recalculate(data: Dict[str, Any]) -> None:
    """
    Calcula totalesReducciones (si faltan o para garantizar coherencia),
    y recalcula bases y casillas dependientes (Caja13/Caja14 y 605-607) usando
    una aproximación proporcional cuando no hay fórmula fiscal explícita.
    Modifica `data` in-place.
    """
    liquid = data.setdefault("liquidacion", {})
    reducciones = liquid.get("reducciones", []) or []
    sum_real = Decimal("0")
    sum_teo = Decimal("0")

    for r in reducciones:
        try:
            imr = Decimal(str(r.get("importeReal", 0) or "0"))
        except Exception:
            imr = Decimal("0")
        try:
            imt = Decimal(str(r.get("importeTeorico", 0) or "0"))
        except Exception:
            imt = Decimal("0")
        sum_real += imr
        sum_teo += imt

    totales = liquid.setdefault("totalesReducciones", {})
    totales["totalReal"] = float(sum_real.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    totales["totalTeorico"] = float(sum_teo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def to_decimal(v):
        try:
            return Decimal(str(v))
        except Exception:
            return None

    base_pre_real = to_decimal(liquid.get("liquidacionBaseLiquidableAntesReducciones"))
    base_pre_teo = to_decimal(liquid.get("liquidacionBaseLiquidableTeoricaAntesReducciones"))

    if base_pre_real is None:
        base_pre_real = to_decimal(liquid.get("liquidacionBaseLiquidableRealCaja13"))
    if base_pre_real is None:
        base_pre_real = to_decimal(data.get("autoliquidacion", {}).get("baseImponible"))
    if base_pre_real is None:
        base_pre_real = Decimal("0")

    if base_pre_teo is None:
        base_pre_teo = to_decimal(liquid.get("liquidacionBaseLiquidableTeoricaCaja14"))
    if base_pre_teo is None:
        base_pre_teo = to_decimal(data.get("autoliquidacion", {}).get("baseImponible"))
    if base_pre_teo is None:
        base_pre_teo = Decimal("0")

    nueva_base_real = (base_pre_real - sum_real).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    nueva_base_teo = (base_pre_teo - sum_teo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    liquid["liquidacionBaseLiquidableAntesReducciones"] = float(base_pre_real)
    liquid["liquidacionBaseLiquidableRealCaja13"] = float(nueva_base_real)
    liquid["liquidacionBaseLiquidableTeoricaCaja14"] = float(nueva_base_teo)

    factor = None
    try:
        if base_pre_real and base_pre_real != Decimal("0"):
            factor = (nueva_base_real / base_pre_real)
    except Exception:
        factor = None

    casillas = [
        "liquidacionCuotaTributariaCaja605",
        "liquidacionReduccionExcesoCuotaCaja606",
        "liquidacionCuotaTributariaAjustadaCaja607",
    ]
    for key in casillas:
        val = to_decimal(liquid.get(key))
        if val is None:
            continue
        if factor is not None:
            liquid[key] = float((val * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    cuota_val = to_decimal(liquid.get("liquidacionCuotaIntegraCaja16")) or to_decimal(data.get("autoliquidacion", {}).get("cuotaIntegra"))
    if cuota_val is not None and factor is not None:
        liquid["liquidacionCuotaIntegraCaja16"] = float((cuota_val * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def validate_and_apply_reducciones(data: Dict[str, Any]) -> None:
    """
    Orquesta la conversión (si viene en formato antiguo), la validación y la aplicación.
    """
    adapt_old_reducciones_format(data)
    validate_reducciones_section(data)
    apply_reducciones_and_recalculate(data)

# ------------------ FIN ADAPTADOR + VALIDACIÓN Y APLICACIÓN ------------------


def build_overlay(
    flattened_data: Dict[str, Any],
    mappings: Sequence[FieldMapping],
    page_sizes: Sequence[Sequence[float]],
) -> PdfReader:
    """Dibuja cada valor mapeado en la página de overlay correspondiente."""

    # Autopoblar componentes del IBAN si se proporciona
    # El IBAN siempre se divide en sus componentes para los campos del formulario
    iban = flattened_data.get("pago.pagoIban", "")
    if iban:
        iban_parts = split_spanish_iban(iban)
        # Siempre poblar componentes desde el IBAN, aunque ya existan (el IBAN es la fuente de verdad)
        if iban_parts['country']:
            flattened_data["pago.pagoPaisBanco"] = iban_parts['country']
        if iban_parts['controlDigits']:
            flattened_data["pago.pagoDigitosControlBanco"] = iban_parts['controlDigits']
        if iban_parts['entity']:
            flattened_data["pago.pagoEntidadBanco"] = iban_parts['entity']
        if iban_parts['branch']:
            flattened_data["pago.pagoSucursalBanco"] = iban_parts['branch']
        if iban_parts['controlDigits2']:
            flattened_data["pago.pagoDigitosControlBanco2"] = iban_parts['controlDigits2']
        if iban_parts['accountNumber']:
            flattened_data["pago.pagoNumeroCuenta"] = iban_parts['accountNumber']

    buffer = BytesIO()
    canv = canvas.Canvas(buffer)

    num_pages = len(page_sizes)
    pages_by_index: Dict[int, List[FieldMapping]] = {i: [] for i in range(num_pages)}
    for mapping in mappings:
        for page in mapping.pages:
            if page < num_pages:
                pages_by_index[page].append(mapping)

    for page_index in range(num_pages):
        width, height = page_sizes[page_index]
        canv.setPageSize((width, height))
        for mapping in pages_by_index.get(page_index, []):
            value = flattened_data.get(mapping.key)
            if mapping.field_type == "checkbox":
                if bool(value):
                    canv.setFont("Helvetica-Bold", mapping.font_size)
                    x_offset = mapping.font_size * CHECKBOX_X_OFFSET_MULT
                    y_offset = mapping.font_size * CHECKBOX_Y_OFFSET_MULT
                    canv.drawString(
                        mapping.x + x_offset,
                        height - mapping.y_from_top + y_offset,
                        mapping.true_label,
                    )
                continue

            text = format_value(value, mapping.formatter)
            if not text:
                continue
            canv.setFont("Helvetica", mapping.font_size)
            canv.drawString(mapping.x, height - mapping.y_from_top, text)
        canv.showPage()

    canv.save()
    buffer.seek(0)
    return PdfReader(buffer)


def merge_with_template(template_path: Path, overlay_reader: PdfReader, output_path: Path) -> None:
    template_reader = PdfReader(template_path)
    writer = PdfWriter()

    for index, template_page in enumerate(template_reader.pages):
        overlay_page = overlay_reader.pages[index]
        template_page.merge_page(overlay_page)
        writer.add_page(template_page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)


def collect_page_sizes(template_path: Path) -> List[Sequence[float]]:
    reader = PdfReader(template_path)
    return [
        (
            float(page.mediabox.right) - float(page.mediabox.left),
            float(page.mediabox.top) - float(page.mediabox.bottom),
        )
        for page in reader.pages
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generar PDF del Modelo 650 (Cataluña) a partir de datos JSON.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Ruta al JSON de entrada.")
    parser.add_argument(
        "--structure",
        type=Path,
        default=DEFAULT_STRUCTURE,
        help="Ruta a la definición de la estructura JSON.",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Ruta a la plantilla PDF en blanco.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta destino del PDF (por defecto generated/mod650cat_<timestamp>.pdf).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_json(args.data)
    validate_against_structure(data, args.structure)

    # --- NUEVO: adaptar/validar y aplicar reducciones antes de aplanar ---
    validate_and_apply_reducciones(data)
    # ------------------------------------------------------------

    flat = flatten_data(data)

    page_sizes = collect_page_sizes(args.template)
    overlay_reader = build_overlay(flat, FIELD_MAPPINGS, page_sizes)

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"mod650cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"PDF generado en {output_path}")


if __name__ == "__main__":
    main()
