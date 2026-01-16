#!/usr/bin/env python3
"""
Generate a filled Catalan Model 650 PDF by overlaying data from a structured JSON.

Usage:
    python src/scripts_generate_models/generate_mod650cat.py \
        --data tax_models/mod650cat/json_examples/mod650cat_example.json \
        --structure tax_models/mod650cat/data_models/mod650cat_data_structure.json \
        --mapping tax_models/mod650cat/data_models/mod650cat_field_mappings.json \
        --template tax_models/mod650cat/mod650cat.pdf \
        --output generated/mod650cat_output.pdf
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod650cat" / "json_examples" / "mod650cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod650cat" / "data_models" / "mod650cat_data_structure.json"
DEFAULT_MAPPING = BASE_DIR / "tax_models" / "mod650cat" / "data_models" / "mod650cat_field_mappings.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "models" / "mod650cat.pdf"
DEFAULT_OUTPUT_DIR = BASE_DIR / "generated"

# Offsets (multipliers) to center the drawn "X" inside checkbox widgets
CHECKBOX_X_OFFSET_MULT = -0.35
CHECKBOX_Y_OFFSET_MULT = -0.45


@dataclass(frozen=True)
class FieldMapping:
    key: str
    pages: Sequence[int]
    x: float
    y_from_top: float
    font_size: float = 10
    field_type: str = "text"  # text | checkbox
    formatter: str = "text"  # text | date | decimal | integer | blank
    true_label: str = "X"
    align: str = "left"  # left | center | right


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_structure(structure_path: Path) -> List[Dict[str, Any]]:
    raw = load_json(structure_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Structure JSON must be an object in {structure_path}")
    if "model650cat" in raw:
        return raw["model650cat"]["structure"]
    if "structure" in raw:
        return raw["structure"]
    raise ValueError(f"Unsupported structure format in {structure_path}")


def load_field_mappings(mapping_path: Path) -> List[FieldMapping]:
    raw = load_json(mapping_path)
    if not isinstance(raw, list):
        raise ValueError(f"Field mapping JSON must be a list in {mapping_path}")
    mappings: List[FieldMapping] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid mapping entry in {mapping_path}")
        mappings.append(
            FieldMapping(
                key=str(entry["key"]),
                pages=[int(page) for page in entry["pages"]],
                x=float(entry["x"]),
                y_from_top=float(entry["y_from_top"]),
                font_size=float(entry.get("font_size", 10)),
                field_type=str(entry.get("field_type", "text")),
                formatter=str(entry.get("formatter", "text")),
                true_label=str(entry.get("true_label", "X")),
                align=str(entry.get("align", "left")),
            )
        )
    return mappings


FIELD_MAPPINGS = load_field_mappings(DEFAULT_MAPPING)


def validate_against_structure(data: Dict[str, Any], structure: List[Dict[str, Any]]) -> None:
    errors: List[str] = []
    for section in structure:
        section_id = section["id"]
        required_section = section.get("required", False)
        section_data = data.get(section_id)
        if required_section and section_data is None:
            errors.append(f"Missing required section '{section_id}'.")
            continue

        if not isinstance(section_data, dict):
            if required_section and section_data is not None:
                errors.append(f"Section '{section_id}' must be an object.")
            continue

        fields = section.get("fields", [])
        if not isinstance(fields, list):
            continue
        for field in fields:
            field_id = field["id"]
            required_field = field.get("required", False)
            value = section_data.get(field_id)
            if required_field and (value is None or value == ""):
                errors.append(f"Missing required field '{section_id}.{field_id}'.")

    if errors:
        raise ValueError("Invalid data for Model 650 Catalonia:\n- " + "\n- ".join(errors))


def flatten_data(payload: Any, prefix: str = "") -> Dict[str, Any]:
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


def is_checked(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "t", "yes", "y", "si", "s", "x"}:
            return True
        if text in {"0", "false", "f", "no", "n", ""}:
            return False
    return bool(value)


def split_spanish_iban(iban: str) -> Dict[str, str]:
    """
    Parse a Spanish IBAN into its components.
    Format: ES + 2 DC + 4 Entity + 4 Branch + 2 DC + 10 Account
    Example: ES1200491500052718123412
    """
    if not iban or len(iban) < 24:
        return {
            "country": "",
            "controlDigits": "",
            "entity": "",
            "branch": "",
            "controlDigits2": "",
            "accountNumber": "",
        }

    iban = iban.replace(" ", "")

    if len(iban) >= 24 and iban[:2] == "ES":
        return {
            "country": iban[0:2],
            "controlDigits": iban[2:4],
            "entity": iban[4:8],
            "branch": iban[8:12],
            "controlDigits2": iban[12:14],
            "accountNumber": iban[14:24],
        }

    return {
        "country": "",
        "controlDigits": "",
        "entity": "",
        "branch": "",
        "controlDigits2": "",
        "accountNumber": "",
    }


def _parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip().replace(" ", "")
            if not text:
                return None
            if "." in text and "," in text and text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", ".")
            return float(text)
        return float(value)
    except (TypeError, ValueError):
        return None


def _set_default(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    if key not in target or target.get(key) in (None, ""):
        target[key] = value


def _set_total_value(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    current = target.get(key)
    if current in (None, ""):
        target[key] = value
        return
    current_num = _parse_number(current)
    value_num = _parse_number(value)
    if current_num is None or value_num is None:
        return
    if current_num == 0 and value_num != 0:
        target[key] = value


def _sum_reducciones(reducciones: List[Any], key: str) -> float | None:
    total = 0.0
    has_value = False
    for entry in reducciones:
        if not isinstance(entry, dict):
            continue
        value = _parse_number(entry.get(key))
        if value is None:
            continue
        total += value
        has_value = True
    return total if has_value else None


def _has_discapacidad(beneficiario: Any) -> bool:
    if not isinstance(beneficiario, dict):
        return False
    if is_checked(beneficiario.get("tiene_discapacidad")):
        return True
    porcentaje = _parse_number(beneficiario.get("porcentaje_discapacidad"))
    return porcentaje is not None and porcentaje >= 33


def _apply_iban_fields(form: Dict[str, Any]) -> None:
    beneficiario = form.get("beneficiario")
    if not isinstance(beneficiario, dict):
        return
    ingreso = beneficiario.get("ingreso")
    if not isinstance(ingreso, dict):
        return
    iban = ingreso.get("iban")
    if not iban:
        return

    iban_parts = split_spanish_iban(str(iban))
    if iban_parts["country"]:
        ingreso["pais"] = iban_parts["country"]
    if iban_parts["controlDigits"]:
        ingreso["dc"] = iban_parts["controlDigits"]
    if iban_parts["entity"]:
        ingreso["entidad"] = iban_parts["entity"]
    if iban_parts["branch"]:
        ingreso["sucursal"] = iban_parts["branch"]
    if iban_parts["controlDigits2"]:
        ingreso["dc2"] = iban_parts["controlDigits2"]
    if iban_parts["accountNumber"]:
        ingreso["numero_cuenta"] = iban_parts["accountNumber"]


def _split_date_parts(value: Any) -> tuple[str, str, str]:
    if isinstance(value, str):
        parts = value.split("-")
        if len(parts) == 3:
            year, month, day = parts
            if len(year) == 4 and len(month) == 2 and len(day) == 2:
                return day, month, year
    return "", "", ""


def _apply_reduccion_totals(form: Dict[str, Any]) -> None:
    reducciones = form.get("reducciones")
    if not isinstance(reducciones, list):
        reducciones = []

    totales = form.get("totalesReducciones")
    if not isinstance(totales, dict):
        totales = {}
        form["totalesReducciones"] = totales

    total_real = _sum_reducciones(reducciones, "importeReal")
    total_teor = _sum_reducciones(reducciones, "importeTeorico")
    if total_real is None:
        total_real = 0.0
    if total_teor is None:
        total_teor = 0.0
    _set_total_value(totales, "total_reducciones_real_caja_11", total_real)
    _set_total_value(totales, "total_reducciones_teorica_caja_12", total_teor)

    applied = None
    if total_real is not None and total_real > 0:
        applied = total_real
    elif total_teor is not None:
        applied = total_teor
    _set_total_value(totales, "total_reducciones_aplicadas", applied)


def _normalize_reducciones(reducciones: Any) -> List[Dict[str, Any]]:
    if not isinstance(reducciones, list):
        reducciones = []

    by_casilla: Dict[int, Dict[str, Any]] = {}
    for entry in reducciones:
        if not isinstance(entry, dict):
            continue
        casilla = entry.get("casillaReal")
        if casilla is None:
            continue
        try:
            casilla_int = int(casilla)
        except (TypeError, ValueError):
            continue
        by_casilla[casilla_int] = entry

    normalized: List[Dict[str, Any]] = []
    for casilla in range(301, 313):
        entry = by_casilla.get(casilla, {})
        normalized.append(
            {
                "casillaReal": casilla,
                "casillaTeorica": entry.get("casillaTeorica") or casilla + 100,
                "tipo_reduccion": entry.get("tipo_reduccion"),
                "importeReal": entry.get("importeReal", 0),
                "importeTeorico": entry.get("importeTeorico", 0),
            }
        )
    return normalized


def _apply_resto_porcentajes(form: Dict[str, Any]) -> None:
    liquidacion = form.get("liquidacion")
    if not isinstance(liquidacion, dict):
        return
    _set_default(liquidacion, "porcentaje_resto_caja_502", 0)


def _apply_discapacidad_reduccion(form: Dict[str, Any]) -> None:
    beneficiario = form.get("beneficiario")
    liquidacion = form.get("liquidacion")
    if not isinstance(liquidacion, dict):
        return

    if not _has_discapacidad(beneficiario):
        liquidacion["bonificacion_discapacidad"] = 0
        return
    reducciones = form.get("reducciones")
    if not isinstance(reducciones, list):
        return

    porcentaje = _parse_number(beneficiario.get("porcentaje_discapacidad"))
    target_casilla = 303 if porcentaje is not None and porcentaje >= 65 else 302
    target_tipo = "para_personas_mayores" if target_casilla == 303 else "por_discapacidad"

    bonificacion = _parse_number(liquidacion.get("bonificacion_discapacidad"))
    if not bonificacion:
        for entry in reducciones:
            if not isinstance(entry, dict):
                continue
            if entry.get("casillaReal") == target_casilla:
                existing = _parse_number(entry.get("importeReal"))
                if existing:
                    bonificacion = existing
                    liquidacion["bonificacion_discapacidad"] = existing
                break
    if bonificacion is None or bonificacion <= 0:
        return

    for entry in reducciones:
        if not isinstance(entry, dict):
            continue
        if entry.get("casillaReal") == target_casilla:
            current = _parse_number(entry.get("importeReal"))
            if current is None or current == 0:
                entry["importeReal"] = bonificacion
                entry.setdefault("tipo_reduccion", target_tipo)
            break


def _apply_liquidacion_calculations(form: Dict[str, Any]) -> None:
    liquidacion = form.get("liquidacion")
    if not isinstance(liquidacion, dict):
        return

    totales = form.get("totalesReducciones") if isinstance(form.get("totalesReducciones"), dict) else {}

    comp_caja_2 = _parse_number(liquidacion.get("participacion_caudal"))
    comp_caja_3 = _parse_number(liquidacion.get("percepcion_seguro_vida"))
    comp_caja_4 = _parse_number(liquidacion.get("bienes_adicionales_base_imponible"))
    if any(value is not None for value in (comp_caja_2, comp_caja_3, comp_caja_4)):
        base_real_calc = (comp_caja_2 or 0.0) + (comp_caja_3 or 0.0) + (comp_caja_4 or 0.0)
        _set_default(liquidacion, "base_imponible_real_caja_5", base_real_calc)

    base_real = _parse_number(liquidacion.get("base_imponible_real_caja_5"))
    if base_real is not None:
        comp_caja_6 = _parse_number(liquidacion.get("titularidad_total_pleno_dominio")) or 0.0
        comp_caja_7 = _parse_number(liquidacion.get("titularidad_total_nuda_propiedad")) or 0.0
        comp_caja_8 = _parse_number(liquidacion.get("donaciones_causante_beneficiario")) or 0.0
        comp_caja_9 = _parse_number(liquidacion.get("suma_bienes_internacionales")) or 0.0
        base_teor_calc = base_real + comp_caja_6 - comp_caja_7 + comp_caja_8 + comp_caja_9
        _set_default(liquidacion, "base_imponible_teorica_caja_10", base_teor_calc)

    total_real = _parse_number(totales.get("total_reducciones_real_caja_11"))
    total_teor = _parse_number(totales.get("total_reducciones_teorica_caja_12"))
    base_real = _parse_number(liquidacion.get("base_imponible_real_caja_5"))
    base_teor = _parse_number(liquidacion.get("base_imponible_teorica_caja_10"))

    if base_real is not None and total_real is not None:
        _set_default(liquidacion, "base_liquidable_real_caja_13", base_real - total_real)
    if base_teor is not None and total_teor is not None:
        _set_default(liquidacion, "base_liquidable_teorica_caja_14", base_teor - total_teor)

    cuota_605 = _parse_number(liquidacion.get("cuota_tributaria_caja_605"))
    reduccion_606 = _parse_number(liquidacion.get("reduccion_exceso_cuota_caja_606"))
    if cuota_605 is not None and reduccion_606 is not None:
        _set_default(liquidacion, "cuota_tributaria_ajustada_caja_607", cuota_605 - reduccion_606)

    cuota_607 = _parse_number(liquidacion.get("cuota_tributaria_ajustada_caja_607"))
    base_liquidable_teor = _parse_number(liquidacion.get("base_liquidable_teorica_caja_14"))
    if cuota_607 is not None and base_liquidable_teor not in (None, 0):
        _set_default(
            liquidacion,
            "tipo_medio_efectivo_caja_17",
            (cuota_607 / base_liquidable_teor) * 100,
        )

    tipo_medio = _parse_number(liquidacion.get("tipo_medio_efectivo_caja_17"))
    base_liquidable_real = _parse_number(liquidacion.get("base_liquidable_real_caja_13"))
    if tipo_medio is not None and base_liquidable_real is not None:
        _set_default(
            liquidacion,
            "cuota_tributaria_ajustada_caja_18",
            base_liquidable_real * (tipo_medio / 100),
        )

    cuota_18 = _parse_number(liquidacion.get("cuota_tributaria_ajustada_caja_18"))
    if cuota_18 is not None and base_liquidable_real not in (None, 0):
        _set_default(
            liquidacion,
            "tipo_medio_efectivo_cuota_tributaria",
            (cuota_18 / base_liquidable_real) * 100,
        )
    bonificacion = _parse_number(liquidacion.get("bonificacion_cuota_caja_19")) or 0.0
    deduccion_doble = _parse_number(liquidacion.get("deduccion_doble_imposicion_caja_20")) or 0.0
    deduccion_previas = _parse_number(liquidacion.get("deduccion_cuotas_anteriores_caja_21")) or 0.0

    resumen = liquidacion.get("resumen_autoliquidacion")
    if not isinstance(resumen, dict):
        resumen = {}
        liquidacion["resumen_autoliquidacion"] = resumen

    if cuota_18 is not None:
        _set_default(
            resumen,
            "importe_pagar_base",
            cuota_18 - bonificacion - deduccion_doble - deduccion_previas,
        )

    cuota_22 = _parse_number(resumen.get("importe_pagar_base"))
    recargo = _parse_number(resumen.get("recargo")) or 0.0
    intereses = _parse_number(resumen.get("intereses_demora")) or 0.0
    if cuota_22 is not None:
        _set_default(resumen, "total_ingresar", cuota_22 + recargo + intereses)


def _apply_apellidos_nombre(form: Dict[str, Any]) -> None:
    """Create 'apellidos_nombre' field as 'Apellidos, Nombre' for beneficiario."""
    beneficiario = form.get("beneficiario")
    if not isinstance(beneficiario, dict):
        return
    apellidos = beneficiario.get("apellidos", "")
    nombre = beneficiario.get("nombre", "")
    if apellidos and nombre:
        beneficiario["apellidos_nombre"] = f"{apellidos}, {nombre}"
    elif apellidos:
        beneficiario["apellidos_nombre"] = apellidos
    elif nombre:
        beneficiario["apellidos_nombre"] = nombre
    else:
        # Fallback to nombre_completo_razon_social if no separate fields
        beneficiario["apellidos_nombre"] = beneficiario.get("nombre_completo_razon_social", "")


def build_pdf_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    form = copy.deepcopy(data) if isinstance(data, dict) else {}
    form["reducciones"] = _normalize_reducciones(form.get("reducciones"))
    _apply_discapacidad_reduccion(form)
    _apply_apellidos_nombre(form)
    tramitante = form.get("tramitante")
    if isinstance(tramitante, dict):
        dia, mes, anio = _split_date_parts(tramitante.get("fecha_firma"))
        tramitante["fecha_firma_dia"] = dia
        tramitante["fecha_firma_mes"] = mes
        tramitante["fecha_firma_anio"] = anio
    _apply_iban_fields(form)
    _apply_reduccion_totals(form)
    _apply_resto_porcentajes(form)
    _apply_liquidacion_calculations(form)
    return {"form": form}


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
        formatted = f"{number:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    if formatter == "decimal_plain":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{number:.2f}".replace(".", ",")
    if formatter == "decimal_no_decimals":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        # Render only the integer part with thousand separator using dot.
        integer = int(round(number))
        return f"{integer:,}".replace(",", ".")
    if formatter == "decimal_split_space":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        integer = int(number)
        decimals = int(round(abs(number - integer) * 100)) % 100
        integer_txt = f"{integer:,}".replace(",", ".")
        padded = integer_txt.rjust(6)  # pad to align with thousands (e.g., "10.000")
        return f"{padded} {decimals:02d}"
    if formatter == "integer":
        try:
            return f"{int(value)}"
        except (TypeError, ValueError):
            return str(value)
    if formatter == "boolean_text":
        return "Si" if bool(value) else "No"
    return str(value)


def build_overlay(
    flattened_data: Dict[str, Any],
    mappings: Sequence[FieldMapping],
    page_sizes: Sequence[Sequence[float]],
) -> PdfReader:
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
                if is_checked(value):
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
            y_pos = height - mapping.y_from_top
            if mapping.align == "center":
                canv.drawCentredString(mapping.x, y_pos, text)
            elif mapping.align == "right":
                canv.drawRightString(mapping.x, y_pos, text)
            else:
                canv.drawString(mapping.x, y_pos, text)
        canv.showPage()

    canv.save()
    buffer.seek(0)
    return PdfReader(buffer)


def _load_pdf_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt("")
    return reader


def merge_with_template(template_path: Path, overlay_reader: PdfReader, output_path: Path) -> None:
    template_reader = _load_pdf_reader(template_path)
    writer = PdfWriter()

    for index, template_page in enumerate(template_reader.pages):
        overlay_page = overlay_reader.pages[index]
        template_page.merge_page(overlay_page)
        writer.add_page(template_page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)


def collect_page_sizes(template_path: Path) -> List[Sequence[float]]:
    reader = _load_pdf_reader(template_path)
    return [
        (
            float(page.mediabox.right) - float(page.mediabox.left),
            float(page.mediabox.top) - float(page.mediabox.bottom),
        )
        for page in reader.pages
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Catalan Model 650 PDF from JSON data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to the JSON input (defaults to tax_models/mod650cat/json_examples/mod650cat_example.json).",
    )
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE, help="Path to the structure JSON.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Path to the field mapping JSON.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod650cat_<timestamp>.pdf).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = args.data or DEFAULT_DATA
    data = load_json(data_path)
    structure = load_structure(args.structure)
    validate_against_structure(data, structure)
    payload = build_pdf_payload(data)
    flat = flatten_data(payload)
    mappings = FIELD_MAPPINGS if args.mapping == DEFAULT_MAPPING else load_field_mappings(args.mapping)

    page_sizes = collect_page_sizes(args.template)
    overlay_reader = build_overlay(flat, mappings, page_sizes)

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"mod650cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
