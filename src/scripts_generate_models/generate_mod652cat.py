#!/usr/bin/env python3
"""
Genera un PDF del Modelo 652 de Catalunya rellenado dibujando los valores sobre la plantilla.

Uso:
    python src/scripts_generate_models/generate_mod652cat.py \
        --data tax_models/mod652cat/json_examples/mod652cat_example.json \
        --structure tax_models/mod652cat/data_models/mod652cat_data_structure.json \
        --mapping tax_models/mod652cat/data_models/mod652cat_field_mappings.json \
        --template tax_models/mod652cat/mod652cat.pdf \
        --output generated/mod652cat_output.pdf
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod652cat" / "json_examples" / "mod652cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod652cat" / "data_models" / "mod652cat_data_structure.json"
DEFAULT_MAPPING = BASE_DIR / "tax_models" / "mod652cat" / "data_models" / "mod652cat_field_mappings.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "mod652cat" / "mod652cat.pdf"
DEFAULT_OUTPUT_DIR = BASE_DIR / "generated"

# Offsets (multipliers) to center the drawn "X" inside checkbox widgets
CHECKBOX_X_OFFSET_MULT = -0.35
CHECKBOX_Y_OFFSET_MULT = -0.45


# Per-field tweaks to keep checkbox marks centered
CHECKBOX_FIELD_OFFSETS = {
    "form.chk_Minus_Si": (4.5, 1.5),
    "form.chk_Mutua_Si": (4.5, 1.5),
    "form.Presenta_autoliquidacio": (4.5, 1.5),
}

CHECKBOX_FIELD_FONT_BONUS = {
    "form.chk_Minus_Si": 2.5,
    "form.chk_Mutua_Si": 2.5,
    "form.Presenta_autoliquidacio": 2.5,
}


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
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_structure(structure_path: Path) -> List[Dict[str, Any]]:
    raw = load_json(structure_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Structure JSON must be an object in {structure_path}")
    if "model652cat" in raw:
        return raw["model652cat"]["structure"]
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
        raise ValueError("Invalid data for Model 652 Catalonia:\n- " + "\n- ".join(errors))


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
    if fmt == "decimal_no_comma":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{number:.2f}"
    if fmt == "integer":
        try:
            return f"{int(value)}"
        except (TypeError, ValueError):
            return str(value)
    if fmt == "date":
        if isinstance(value, str):
            parts = value.split("-")
            if len(parts) == 3:
                year, month, day = parts
                if len(year) == 4 and len(month) == 2 and len(day) == 2:
                    return f"{day}-{month}-{year}"
        return str(value)
    return str(value)


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


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            text = value.strip().replace(" ", "").replace("%", "").replace(",", ".")
            if not text:
                return None
            return int(float(text))
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _apply_seguro_row(form: Dict[str, Any], index: int, seguro: Dict[str, Any]) -> None:
    if not isinstance(seguro, dict):
        return

    numero_poliza = seguro.get("numero_poliza")
    entidad = seguro.get("entidad_aseguradora")
    fecha = seguro.get("fecha_contratacion")
    valor_total = seguro.get("valor_total")
    valor_declarado = seguro.get("valor_declarado")
    numero_beneficiarios = seguro.get("numero_beneficiarios")

    if index <= 4:
        form[f"ENTIDAD_ASEGURADORA_{index}"] = entidad
        form[f"NUMERO_POLIZA_{index}"] = numero_poliza
        form[f"FECHA_CONTRATACION_{index}"] = fecha
        form[f"VALOR_TOTAL_{index}"] = valor_total
        form[f"VALOR_DECLARADO_{index}"] = valor_declarado
        form[f"NB_{index}"] = numero_beneficiarios

    suffix_with_alt = f"{index}_2" if index <= 4 else str(index)
    suffix = str(index)

    entitat_prefix = "Entitat asseguradoraRow"
    numero_polissa_prefix = "N\u00famero de p\u00f2lissaRow"
    data_contratacio_prefix = "Data_contractaci\u00f3Row"
    valor_total_prefix = "Valor totalRow"
    valor_declara_prefix = "Valor declaratRow"
    beneficiaris_prefix = "Nombre de beneficiarisRow"

    form[f"{entitat_prefix}{suffix_with_alt}"] = entidad
    form[f"{numero_polissa_prefix}{suffix_with_alt}"] = numero_poliza
    form[f"{data_contratacio_prefix}{suffix_with_alt}"] = fecha
    form[f"{valor_total_prefix}{suffix}"] = valor_total
    form[f"{valor_declara_prefix}{suffix}"] = valor_declarado
    form[f"{beneficiaris_prefix}{suffix}"] = numero_beneficiarios


def build_pdf_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    encabezado = _as_dict(data.get("encabezado"))
    beneficiario = _as_dict(data.get("beneficiario"))
    causante = _as_dict(data.get("causante"))
    tramitante = _as_dict(data.get("tramitante"))
    liquidacion = _as_dict(data.get("liquidacion"))
    pago = _as_dict(data.get("pago"))
    seguros = _as_list(data.get("seguros"))

    form: Dict[str, Any] = {}

    form["Fecha_devengo"] = encabezado.get("fecha_devengo")
    form["FECHA_PRESENTACION"] = encabezado.get("fecha_presentacion")
    form["NUMERO_AUTOLIQUIDACION"] = encabezado.get("numero_autoliquidacion")
    form["NumJust"] = encabezado.get("numero_justificante")
    form["txt_Codigo"] = encabezado.get("codigo_modelo")
    form["txt_Aleatorio"] = encabezado.get("codigo_aleatorio")
    form["txt_Aleatorio_Ref"] = encabezado.get("codigo_aleatorio_ref")
    form["chk_Nosubjecte"] = encabezado.get("no_sujeto")
    form["chk_Prescrit"] = encabezado.get("prescrito")
    form["chk_CondicioSusp"] = encabezado.get("condicion_suspensiva")
    form["chk_Mutua_Si"] = encabezado.get("relacion_convivencial_ayuda_mutua")
    form["Observacions"] = encabezado.get("observaciones")
    form["Pag_num"] = encabezado.get("pagina_num")
    form["Pag_de"] = encabezado.get("pagina_de")

    form["Nif_contribuent"] = beneficiario.get("dni_nif")
    form["txt_Cognoms"] = beneficiario.get("nombre_completo_razon_social")
    form["Fecha_contribuent"] = beneficiario.get("fecha_nacimiento")
    form["txt_Parentiu_Contri"] = beneficiario.get("parentesco")
    form["txt_Grup_Contri"] = beneficiario.get("grupo_parentesco")
    form["txt_PatrimoniPree_Contri"] = beneficiario.get("patrimonio_preexistente")
    form["Per_discapacitat"] = beneficiario.get("porcentaje_discapacidad")

    beneficiario_pct = _as_int(beneficiario.get("porcentaje_discapacidad"))
    beneficiario_flag = beneficiario.get("tiene_discapacidad")
    if beneficiario_flag is None:
        beneficiario_flag = beneficiario_pct >= 33 if beneficiario_pct is not None else False
    form["chk_Minus_Si"] = bool(beneficiario_flag)

    form["NIF"] = beneficiario.get("dni_nif")
    form["Nom"] = beneficiario.get("nombre_completo_razon_social")

    form["Nif_Usu"] = causante.get("dni_nif")
    form["txt_Cognoms_Usu"] = causante.get("nombre_completo")
    form["Fecha_defuncio"] = causante.get("fecha_defuncion")

    form["Nif_presentador"] = tramitante.get("dni_nif")
    form["txt_Cognoms_Pre"] = tramitante.get("nombre_completo_firmante")
    form["Presenta_autoliquidacio"] = tramitante.get("aporta_documento_original")

    form["Importe1"] = pago.get("importe")

    liquidacion_map = {
        "valor_1": "VALOR_1",
        "valor_2": "VALOR_2",
        "valor_3": "VALOR_3",
        "valor_4a": "VALOR_4A",
        "valor_4b": "VALOR_4B",
        "valor_4c": "VALOR_4C",
        "valor_4d": "VALOR_4D",
        "valor_5": "VALOR_5",
        "valor_6": "VALOR_6",
        "valor_7": "VALOR_7",
        "valor_8": "VALOR_8",
        "valor_9": "VALOR_9",
        "valor_10": "VALOR_10",
        "valor_11": "VALOR_11",
        "valor_12": "VALOR_12",
        "valor_13": "VALOR_13",
        "valor_14": "VALOR_14",
        "valor_15": "VALOR_15",
        "valor_16": "VALOR_16",
        "valor_17": "VALOR_17",
        "valor_18": "VALOR_18",
        "valor_101": "VALOR_101",
        "valor_102": "VALOR_102",
        "valor_103": "VALOR_103",
        "valor_porcentaje": "VALOR_PORCIEN",
        "valor_resta": "VALOR_RESTA",
        "valor_encuentra": "VALOR_ENCUENTRA",
        "cuota_ingresada": "QUOTA_INGRESADA",
    }

    for field_id, pdf_key in liquidacion_map.items():
        if field_id in liquidacion:
            form[pdf_key] = liquidacion.get(field_id)

    for index, seguro in enumerate(seguros[:51], start=1):
        _apply_seguro_row(form, index, seguro)

    return {"form": form}


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
            font_size = max(mapping.font_size - 1, 1)
            if mapping.field_type == "checkbox":
                if is_checked(value):
                    bonus = CHECKBOX_FIELD_FONT_BONUS.get(mapping.key, 0.0)
                    checkbox_size = max(font_size + bonus, 1)
                    canv.setFont("Helvetica-Bold", checkbox_size)
                    x_offset = checkbox_size * CHECKBOX_X_OFFSET_MULT
                    y_offset = checkbox_size * CHECKBOX_Y_OFFSET_MULT
                    extra_x, extra_y = CHECKBOX_FIELD_OFFSETS.get(mapping.key, (0.0, 0.0))
                    canv.drawString(
                        mapping.x + x_offset + extra_x,
                        height - mapping.y_from_top + y_offset + extra_y,
                        mapping.true_label,
                    )
                continue

            text = format_value(value, mapping.formatter)
            if not text:
                continue
            canv.setFont("Helvetica", font_size)
            if mapping.key == "form.VALOR_PORCIEN" and "." in text:
                int_part, _, _ = text.partition(".")
                int_width = pdfmetrics.stringWidth(int_part, "Helvetica", font_size)
                text_width = pdfmetrics.stringWidth(text, "Helvetica", font_size)
                comma_w = max(font_size * 0.7, 3.0)
                comma_h = font_size * 1.2
                comma_y = height - mapping.y_from_top - (font_size * 0.6)
                comma_x = mapping.x + int_width + (font_size * 0.2)
                tail_x = mapping.x + text_width + (font_size * 0.3)
                canv.setFillColorRGB(1, 1, 1)
                canv.rect(comma_x - (comma_w / 2), comma_y, comma_w, comma_h, stroke=0, fill=1)
                canv.rect(tail_x - (comma_w / 2), comma_y, comma_w, comma_h, stroke=0, fill=1)
                canv.setFillColorRGB(0, 0, 0)
            canv.drawString(mapping.x, height - mapping.y_from_top, text)
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
    parser = argparse.ArgumentParser(description="Generate Catalan Model 652 PDF from JSON data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to the JSON input (defaults to tax_models/mod652cat/json_examples/mod652cat_example.json).",
    )
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE, help="Path to the structure JSON.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Path to the field mapping JSON.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod652cat_<timestamp>.pdf).",
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
        output_path = DEFAULT_OUTPUT_DIR / f"mod652cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
