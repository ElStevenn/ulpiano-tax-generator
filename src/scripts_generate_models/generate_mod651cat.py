#!/usr/bin/env python3
"""
Genera un PDF del Modelo 651 de Cataluna rellenado dibujando los valores sobre la plantilla.

Uso:
    python src/scripts_generate_models/generate_mod651cat.py \
        --data tax_models/mod651cat/json_examples/mod651cat_example.json \
        --structure tax_models/mod651cat/data_models/mod651cat_data_structure.json \
        --mapping tax_models/mod651cat/data_models/mod651cat_field_mappings.json \
        --template tax_models/mod651cat/mod651cat.pdf \
        --output generated/mod651cat_output.pdf
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
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod651cat" / "json_examples" / "mod651cat_example_sin_discapacidad.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod651cat" / "data_models" / "mod651cat_data_structure.json"
DEFAULT_MAPPING = BASE_DIR / "tax_models" / "mod651cat" / "data_models" / "mod651cat_field_mappings.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "mod651cat" / "mod651cat.pdf"
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
    if "model651cat" in raw:
        return raw["model651cat"]["structure"]
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
        raise ValueError("Invalid data for Model 651 Catalonia:\n- " + "\n- ".join(errors))


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
    if fmt == "integer":
        try:
            return f"{int(value)}"
        except (TypeError, ValueError):
            return str(value)
    if fmt == "date":
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


def _protocol_number(causante: Dict[str, Any], encabezado: Dict[str, Any]) -> str:
    date_value = causante.get("fecha_acta_notarial") or encabezado.get("fecha_documento") or encabezado.get("fecha_devengo")
    if isinstance(date_value, str) and len(date_value) >= 4:
        year = date_value[:4]
    else:
        year = datetime.now().strftime("%Y")

    nif = str(causante.get("dni_nif") or "")
    digits = "".join(ch for ch in nif if ch.isdigit())
    suffix = digits[-3:] if digits else "000"
    return f"{year}/{suffix}"


def _compose_address_line(persona: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("nombre_via", "numero_via"):
        value = persona.get(key)
        if value:
            parts.append(str(value).strip())
    escalera = persona.get("escalera")
    if escalera:
        parts.append(f"Esc {str(escalera).strip()}")
    piso = persona.get("piso")
    if piso:
        parts.append(f"Piso {str(piso).strip()}")
    puerta = persona.get("puerta")
    if puerta:
        parts.append(f"Pta {str(puerta).strip()}")
    return " ".join(part for part in parts if part).strip()


def _compose_provincia_pais(persona: Dict[str, Any]) -> str:
    provincia = persona.get("provincia")
    pais = persona.get("pais")
    if provincia and pais:
        return f"{provincia} / {pais}"
    return str(provincia or pais or "").strip()


def _apply_bien_address(
    form: Dict[str, Any],
    index: int,
    persona: Dict[str, Any],
    label: str,
) -> None:
    if not isinstance(persona, dict):
        return
    address_line = _compose_address_line(persona)
    if address_line:
        form[f"via_bens_{index}"] = address_line
    codigo_postal = persona.get("codigo_postal")
    if codigo_postal:
        form[f"cp_bens_{index}"] = codigo_postal
    municipio = persona.get("municipio")
    if municipio:
        form[f"municipi_bens_{index}"] = municipio
    provincia_pais = _compose_provincia_pais(persona)
    if provincia_pais:
        form[f"provincia_pais_bens_{index}"] = provincia_pais
    if label:
        form[f"tipus_bens_{index}"] = "Domicilio"
        form[f"descripcio_bens_{index}"] = label
        form[f"numero_bens_{index}"] = str(index)


def build_pdf_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    encabezado = data.get("encabezado") if isinstance(data.get("encabezado"), dict) else {}
    causante = data.get("causante") if isinstance(data.get("causante"), dict) else {}
    beneficiario = data.get("beneficiario") if isinstance(data.get("beneficiario"), dict) else {}
    tramitante = data.get("tramitante") if isinstance(data.get("tramitante"), dict) else {}
    liquidacion = data.get("liquidacion") if isinstance(data.get("liquidacion"), dict) else {}
    pago = data.get("pago") if isinstance(data.get("pago"), dict) else {}

    form: Dict[str, Any] = {}

    form["fecha_devengo"] = encabezado.get("fecha_devengo")
    form["fecha_document"] = encabezado.get("fecha_documento")

    form["nif_contribuent"] = beneficiario.get("dni_nif")
    form["txt_cognoms"] = beneficiario.get("nombre_completo_razon_social")
    form["fecha_contribuent"] = beneficiario.get("fecha_nacimiento")
    form["txt_parentiu_contri"] = beneficiario.get("parentesco")
    form["txt_grup_contri"] = beneficiario.get("grupo_parentesco")
    form["txt_patrimonipree_contri"] = beneficiario.get("patrimonio_preexistente")
    form["txt_minusvalesa_contri"] = beneficiario.get("porcentaje_discapacidad")
    beneficiario_pct = _as_int(beneficiario.get("porcentaje_discapacidad"))
    beneficiario_flag = beneficiario.get("tiene_discapacidad")
    if beneficiario_flag is None:
        beneficiario_flag = beneficiario_pct >= 33 if beneficiario_pct is not None else False
    form["chk_minus_si"] = bool(beneficiario_flag)

    form["nif_usu"] = causante.get("dni_nif")
    form["txt_cognoms_usu"] = causante.get("nombre_completo")
    form["fecha_usu"] = causante.get("fecha_nacimiento")
    form["txt_incapacitat"] = causante.get("porcentaje_discapacidad")
    causante_pct = _as_int(causante.get("porcentaje_discapacidad"))
    causante_flag = causante.get("tiene_discapacidad")
    if causante_flag is None:
        causante_flag = causante_pct >= 33 if causante_pct is not None else False
    form["chk_minus_donant_si"] = bool(causante_flag)

    form["nif_presentador"] = tramitante.get("dni_nif")
    form["txt_cognoms_pre"] = tramitante.get("nombre_completo_firmante")
    form["fecha_presentacio"] = tramitante.get("fecha_firma")

    form["base_imposable"] = liquidacion.get("base_imposable")
    form["baseimposable_real"] = liquidacion.get("base_imposable_real")
    form["base_liquidable"] = liquidacion.get("base_liquidable")
    form["base_liquidablereal"] = liquidacion.get("base_liquidable_real")
    form["txt_baseliqreal"] = liquidacion.get("base_liquidable_real")

    form["quota_tributaria"] = liquidacion.get("cuota_tributaria")
    form["txt_quotatributaria"] = liquidacion.get("cuota_tributaria")
    form["quota_integra"] = liquidacion.get("cuota_integra")
    form["txt_quotaintegra"] = liquidacion.get("cuota_integra")
    form["quota_liquida"] = liquidacion.get("cuota_liquida")
    form["txt_quotaliquida"] = liquidacion.get("cuota_liquida")
    form["quota_liquidada_anterior"] = liquidacion.get("cuota_liquidada_anterior")
    form["txt_quotaliquidadaanteriorment"] = liquidacion.get("cuota_liquidada_anterior")
    form["quota_resultant"] = liquidacion.get("cuota_resultante")
    form["txt_quotaresultant"] = liquidacion.get("cuota_resultante")

    form["total_ingresar"] = liquidacion.get("total_ingresar")
    form["txt_total_ingresar"] = liquidacion.get("total_ingresar")
    form["txt_totalingresar"] = liquidacion.get("total_ingresar")
    form["txt_quota_ingressar"] = liquidacion.get("total_ingresar")

    form["interesos_demora"] = liquidacion.get("intereses_demora")
    form["interessos_demora"] = liquidacion.get("intereses_demora")
    form["txt_intereses_demora"] = liquidacion.get("intereses_demora")
    form["recarrec"] = liquidacion.get("recargo")
    form["txt_recarrec"] = liquidacion.get("recargo")

    notario = causante.get("notario_o_autoridad")
    if notario:
        form["txt_notari"] = notario
        form["txt_notari_1"] = notario
        form["txt_notari_8"] = notario
        form["txt_autoritat"] = notario
        form["txt_autoritat_7"] = notario
        form["txt_autoritat_8"] = notario

    fecha_acta = causante.get("fecha_acta_notarial") or encabezado.get("fecha_documento")
    form["fecha_document_1"] = fecha_acta
    form["fecha_document_8"] = fecha_acta

    lugar = causante.get("municipio") or tramitante.get("municipio")
    form["txt_lloc_atorgament"] = lugar
    form["txt_lloc_atorgament_7"] = lugar
    form["txt_lloc_atorgament_8"] = lugar

    causante_nombre = str(causante.get("nombre_completo") or "").strip()
    beneficiario_nombre = str(beneficiario.get("nombre_completo_razon_social") or "").strip()
    if causante_nombre and beneficiario_nombre:
        identificacion = f"Donacion de {causante_nombre} a {beneficiario_nombre}"
    elif causante_nombre:
        identificacion = f"Donacion de {causante_nombre}"
    elif beneficiario_nombre:
        identificacion = f"Donacion a {beneficiario_nombre}"
    else:
        identificacion = ""

    form["txt_identificacio"] = identificacion
    form["txt_identificacio_7"] = identificacion
    form["txt_identificacio_8"] = identificacion

    protocol_number = _protocol_number(causante, encabezado)
    protocol_bis = f"{protocol_number}-B"
    form["txt_num_protocol"] = protocol_number
    form["txt_numero_protocolo_7"] = protocol_number
    form["txt_numero_protocolo_8"] = protocol_number
    form["txt_num_protocol_bis"] = protocol_bis
    form["txt_numero_protocolobis_7"] = protocol_bis
    form["txt_numero_protocolobis_8"] = protocol_bis

    has_notarial = bool(notario or fecha_acta)
    form["chk_notarial"] = has_notarial
    form["chk_notarial_7"] = has_notarial
    form["chk_notarial_8"] = has_notarial
    form["aporta_document"] = bool(tramitante.get("acuerdo_declaracion"))

    form["txt_codigo"] = "651"
    form["txt_coeficient"] = beneficiario.get("coeficiente_multiplicador")
    form["nom_titols_4"] = beneficiario.get("titulo_sucesorio")
    form["txt_quota_ingresada"] = liquidacion.get("cuota_liquidada_anterior")
    form["txt_reca"] = liquidacion.get("recargo")
    form["txt_intdemora"] = liquidacion.get("intereses_demora")
    form["txt_intdemoraforatermini"] = liquidacion.get("intereses_demora")
    form["importe1"] = pago.get("importe")

    _apply_bien_address(form, 1, beneficiario, "Domicilio donatario")
    _apply_bien_address(form, 2, causante, "Domicilio donante")
    _apply_bien_address(form, 3, tramitante, "Domicilio tramitante")

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
                    canv.setFont("Helvetica-Bold", font_size)
                    x_offset = font_size * CHECKBOX_X_OFFSET_MULT
                    y_offset = font_size * CHECKBOX_Y_OFFSET_MULT
                    canv.drawString(
                        mapping.x + x_offset,
                        height - mapping.y_from_top + y_offset,
                        mapping.true_label,
                    )
                continue

            text = format_value(value, mapping.formatter)
            if not text:
                continue
            canv.setFont("Helvetica", font_size)
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
    parser = argparse.ArgumentParser(description="Generate Catalan Model 651 PDF from JSON data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to the JSON input (defaults to tax_models/mod651cat/json_examples/mod651cat_example.json).",
    )
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE, help="Path to the structure JSON.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Path to the field mapping JSON.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod651cat_<timestamp>.pdf).",
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
        output_path = DEFAULT_OUTPUT_DIR / f"mod651cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
