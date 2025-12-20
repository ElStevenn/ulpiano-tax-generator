#!/usr/bin/env python3
"""
Generate a filled Catalan Model 620 PDF by drawing values on top of the template.

Usage:
    python src/scripts_generate_models/generate_mod620cat.py \
        --data tax_models/mod620cat/json_examples/mod620cat_example.json \
        --structure tax_models/mod620cat/data_models/mod620cat_data_structure.json \
        --mapping tax_models/mod620cat/data_models/mod620cat_field_mappings.json \
        --template tax_models/mod620cat/mod620cat.pdf \
        --output generated/mod620cat_output.pdf

The default arguments already point to the sample input JSON, structure
description, mapping and template inside this repository.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod620cat" / "json_examples" / "mod620cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod620cat" / "data_models" / "mod620cat_data_structure.json"
DEFAULT_MAPPING = BASE_DIR / "tax_models" / "mod620cat" / "data_models" / "mod620cat_field_mappings.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "mod620cat" / "mod620cat.pdf"
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
    formatter: str = "text"  # text | date | decimal | integer
    true_label: str = "X"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_structure(structure_path: Path) -> List[Dict[str, Any]]:
    raw = load_json(structure_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Structure JSON must be an object in {structure_path}")
    if "model620cat" in raw:
        return raw["model620cat"]["structure"]
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
                pages=entry["pages"],
                x=float(entry["x"]),
                y_from_top=float(entry["y_from_top"]),
                font_size=float(entry.get("font_size", 10)),
                field_type=str(entry.get("field_type", "text")),
                formatter=str(entry.get("formatter", "text")),
                true_label=str(entry.get("true_label", "X")),
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

        for field in section.get("fields", []):
            field_id = field["id"]
            required_field = field.get("required", False)
            value = section_data.get(field_id)
            if required_field and (value is None or value == ""):
                errors.append(f"Missing required field '{section_id}.{field_id}'.")

    if errors:
        raise ValueError("Invalid data for Model 620 Catalonia:\n- " + "\n- ".join(errors))


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


def split_spanish_iban(iban: str) -> Dict[str, str]:
    if not iban:
        return {}
    iban = iban.replace(" ", "")
    if len(iban) < 24 or not iban.startswith("ES"):
        return {}
    return {
        "pais_banco": iban[0:2],
        "dc_iban": iban[2:4],
        "entidad_banco": iban[4:8],
        "sucursal_banco": iban[8:12],
        "digitos_control_banco": iban[12:14],
        "numero_cuenta": iban[14:24],
    }


def derive_fields(data: Dict[str, Any]) -> None:
    bien = data.get("bien")
    if isinstance(bien, dict):
        tipo_bien = bien.get("tipo_bien")
        if tipo_bien and bien.get("es_vehiculo") is None:
            bien["es_vehiculo"] = tipo_bien == "vehiculo"
        if tipo_bien and bien.get("es_embarcacion") is None:
            bien["es_embarcacion"] = tipo_bien == "embarcacion"
        if tipo_bien and bien.get("es_aeronave") is None:
            bien["es_aeronave"] = tipo_bien == "aeronave"

    embarcacion = data.get("embarcacion")
    if isinstance(embarcacion, dict):
        tipo_motor = embarcacion.get("tipo_motor")
        if tipo_motor:
            if embarcacion.get("motor_diesel") is None:
                embarcacion["motor_diesel"] = tipo_motor == "diesel"
            if embarcacion.get("motor_gasolina") is None:
                embarcacion["motor_gasolina"] = tipo_motor == "gasolina"
            if embarcacion.get("motor_otros") is None:
                embarcacion["motor_otros"] = tipo_motor == "otros"

    presentacion = data.get("presentacion")
    if isinstance(presentacion, dict):
        fecha = presentacion.get("fecha_presentacion")
        if fecha and isinstance(fecha, str) and len(fecha.split("-")) == 3:
            year, month, day = fecha.split("-")
            year = year[-2:]
            presentacion.setdefault("dia_presentacion", day)
            presentacion.setdefault("mes_presentacion", month)
            presentacion.setdefault("anyo_presentacion", year)

    pago = data.get("pago")
    if isinstance(pago, dict):
        iban = pago.get("iban")
        if iban:
            iban_parts = split_spanish_iban(iban)
            for key, value in iban_parts.items():
                if pago.get(key) in (None, ""):
                    pago[key] = value
        if pago.get("cargo_en_cuenta") and pago.get("pago_efectivo"):
            pago["pago_efectivo"] = False

    if isinstance(embarcacion, dict):
        motor_fields = ["motor_diesel", "motor_gasolina", "motor_otros"]
        true_fields = [name for name in motor_fields if embarcacion.get(name)]
        if len(true_fields) > 1:
            keep = true_fields[0]
            for name in motor_fields:
                embarcacion[name] = name == keep


def prune_by_tipo_bien(data: Dict[str, Any]) -> None:
    bien = data.get("bien")
    if not isinstance(bien, dict):
        return
    tipo_bien = bien.get("tipo_bien")
    if tipo_bien == "vehiculo":
        data["embarcacion"] = {}
        data["aeronave"] = {}
    elif tipo_bien == "embarcacion":
        data["vehiculo"] = {}
        data["aeronave"] = {}
    elif tipo_bien == "aeronave":
        data["vehiculo"] = {}
        data["embarcacion"] = {}


def format_value(value: Any, fmt: str) -> str:
    if value is None:
        return ""
    if fmt == "decimal":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        formatted = f"{number:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    if fmt == "integer":
        try:
            return f"{int(value)}"
        except (TypeError, ValueError):
            return str(value)
    if fmt == "date":
        return str(value)
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
    parser = argparse.ArgumentParser(description="Generate Catalan Model 620 PDF from JSON data.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to the JSON input.")
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE, help="Path to the structure JSON.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Path to the field mapping JSON.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod620cat_<timestamp>.pdf).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_json(args.data)
    structure = load_structure(args.structure)
    derive_fields(data)
    prune_by_tipo_bien(data)
    validate_against_structure(data, structure)
    flat = flatten_data(data)
    mappings = FIELD_MAPPINGS if args.mapping == DEFAULT_MAPPING else load_field_mappings(args.mapping)

    page_sizes = collect_page_sizes(args.template)
    overlay_reader = build_overlay(flat, mappings, page_sizes)

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"mod620cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
