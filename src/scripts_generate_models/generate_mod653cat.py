#!/usr/bin/env python3
"""
Genera un PDF del Modelo 653 de Catalunya rellenado dibujando los valores sobre la plantilla.

Uso:
    python src/scripts_generate_models/generate_mod653cat.py \
        --data tax_models/mod653cat/json_examples/mod653cat_example.json \
        --structure tax_models/mod653cat/data_models/mod653cat_data_structure.json \
        --mapping tax_models/mod653cat/data_models/mod653cat_field_mappings.json \
        --template tax_models/mod653cat/mod653cat.pdf \
        --output generated/mod653cat_output.pdf
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod653cat" / "json_examples" / "mod653cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod653cat" / "data_models" / "mod653cat_data_structure.json"
DEFAULT_MAPPING = BASE_DIR / "tax_models" / "mod653cat" / "data_models" / "mod653cat_field_mappings.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "mod653cat" / "mod653cat.pdf"
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
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_structure(structure_path: Path) -> List[Dict[str, Any]]:
    raw = load_json(structure_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Structure JSON must be an object in {structure_path}")
    if "model653cat" in raw:
        return raw["model653cat"]["structure"]
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
        raise ValueError("Invalid data for Model 653 Catalonia:\n- " + "\n- ".join(errors))


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


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip().replace(" ", "").replace(",", ".")
            if not text:
                return None
            return float(text)
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_bienes(bienes: List[Any]) -> float | None:
    total = 0.0
    has_value = False
    for bien in bienes:
        if not isinstance(bien, dict):
            continue
        value = _parse_number(bien.get("valor_total"))
        if value is None:
            continue
        total += value
        has_value = True
    return total if has_value else None


def _fallback(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    return value


def _split_date(value: Any) -> Tuple[str, str, str]:
    if isinstance(value, str):
        parts = value.split("-")
        if len(parts) == 3:
            year, month, day = parts
            if len(year) == 4 and len(month) == 2 and len(day) == 2:
                return day, month, year
    return "", "", ""


def build_pdf_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    encabezado = _as_dict(data.get("encabezado"))
    contribuyente = _as_dict(data.get("contribuyente"))
    contribuyente_adicional = _as_dict(data.get("contribuyente_adicional"))
    usufructuario = _as_dict(data.get("usufructuario"))
    usufructo = _as_dict(data.get("usufructo"))
    acto = _as_dict(data.get("acto"))
    causante = _as_dict(data.get("causante"))
    documento = _as_dict(data.get("documento"))
    resumen = _as_dict(data.get("resumen_autoliquidacion"))
    liquidacion_primera = _as_dict(data.get("liquidacion_primera"))
    liquidacion_segunda = _as_dict(data.get("liquidacion_segunda"))
    pago = _as_dict(data.get("pago"))
    tramitante = _as_dict(data.get("tramitante"))
    bienes = _as_list(data.get("bienes_consolidados"))
    total_bienes = _sum_bienes(bienes)

    form: Dict[str, Any] = {}

    form["Fecha_devengo"] = encabezado.get("fecha_devengo")
    form["Fecha_presentacio"] = encabezado.get("fecha_presentacion")
    form["txt_NumDarrera"] = encabezado.get("numero_ultima_autoliquidacion")
    form["txt_Codigo"] = encabezado.get("codigo_modelo")
    form["txt_Aleatorio"] = encabezado.get("codigo_aleatorio")
    form["txt_Aleatorio_Ref"] = encabezado.get("codigo_aleatorio_ref")
    form["chk_Nosubjecte"] = encabezado.get("no_sujeto")
    form["chk_Prescrit"] = encabezado.get("prescrito")
    form["chk_Liquidacio"] = encabezado.get("liquidacion_complementaria")

    form["Nif_contribuent"] = contribuyente.get("dni_nif")
    form["txt_Cognoms"] = contribuyente.get("nombre_completo_razon_social")
    form["Fecha_contribuent"] = contribuyente.get("fecha_nacimiento")
    form["txt_ViaPublica"] = contribuyente.get("nombre_via")
    form["txt_Numero"] = contribuyente.get("numero_via")
    form["txt_Escalera"] = contribuyente.get("escalera")
    form["txt_Pis"] = contribuyente.get("piso")
    form["txt_Porta"] = contribuyente.get("puerta")
    form["CP_contribuent"] = contribuyente.get("codigo_postal")
    form["txt_Municipi"] = contribuyente.get("municipio")
    form["txt_Provincia"] = contribuyente.get("provincia")
    form["txt_Pais"] = contribuyente.get("pais")
    form["txt_Tlfono_Contri"] = contribuyente.get("telefono")
    form["txt_Adreca_Contri"] = contribuyente.get("correo_electronico")

    form["txt_NIF_Altres"] = contribuyente_adicional.get("dni_nif")
    form["txt_Cognoms_altres"] = contribuyente_adicional.get("nombre_completo_razon_social")
    form["Nif_contribuent2"] = contribuyente_adicional.get("dni_nif")
    form["txt_Cognoms2"] = contribuyente_adicional.get("nombre_completo_razon_social")

    form["Nif_Usu"] = usufructuario.get("dni_nif")
    form["txt_Cognoms_Usu"] = usufructuario.get("nombre_completo_razon_social")
    form["Fecha_Usufructuari"] = usufructuario.get("fecha_nacimiento")
    form["txt_ViaPublica_Usu"] = usufructuario.get("nombre_via")
    form["txt_Numero_Usu"] = usufructuario.get("numero_via")
    form["txt_Escalera_Usu"] = usufructuario.get("escalera")
    form["txt_Pis_Usu"] = usufructuario.get("piso")
    form["txt_Porta_Usu"] = usufructuario.get("puerta")
    form["CP_Usu"] = usufructuario.get("codigo_postal")
    form["txt_Municipi_Usu"] = usufructuario.get("municipio")
    form["txt_Provincia_Usu"] = usufructuario.get("provincia")
    form["txt_Pais_Usu"] = usufructuario.get("pais")
    form["txt_Tlfono_Usu"] = usufructuario.get("telefono")
    form["txt_Adreca_Usu"] = usufructuario.get("correo_electronico")

    form["txt_Tipus"] = usufructo.get("tipo_usufructo")
    form["txt_Durada"] = usufructo.get("duracion")
    form["txt_Causade"] = usufructo.get("causa_extincion")
    form["Fecha_Usu"] = usufructo.get("fecha_constitucion")

    form["txt_Titol_Adq"] = acto.get("titulo_adquisicion")
    form["txt_Origen"] = acto.get("origen")
    form["txt_Num_Exp"] = acto.get("numero_expediente_acto")
    form["txt_NumExpe"] = acto.get("numero_expediente")

    form["txt_NIFCausant"] = causante.get("dni_nif")
    form["txt_Cognoms_Cau"] = causante.get("nombre_completo")

    form["txt_Tipus_Dades"] = documento.get("tipo_documento")
    form["txt_Notari"] = documento.get("notario_o_autoridad")
    form["Fecha_document"] = documento.get("fecha_documento")
    form["txt_N\u00famero"] = documento.get("numero_protocolo")

    signature_place = tramitante.get("lugar_firma") or documento.get("lugar_documento") or tramitante.get("municipio")
    form["txt_Lugar"] = signature_place

    signature_date = tramitante.get("fecha_firma") or encabezado.get("fecha_presentacion") or documento.get("fecha_documento")
    dia, mes, anyo = _split_date(signature_date)
    if len(anyo) == 4:
        anyo = anyo[2:]
    form["txt_Dia"] = dia
    form["txt_Mes"] = mes
    form["txt_Anio"] = anyo

    form["txt_Quota_Ingresada"] = resumen.get("cuota_ingresada")
    form["txt_Quota_Ingressar"] = resumen.get("cuota_ingresar")
    form["txt_Recarrec"] = resumen.get("recargo")
    form["txt_Interessos"] = resumen.get("intereses_demora")
    form["txt_Total"] = resumen.get("total_ingresar")

    if total_bienes is not None:
        form["txt_ValorTotal"] = total_bienes

    form["txt_ValorAuto"] = _fallback(liquidacion_primera.get("valor_total_bienes_consolidados"), total_bienes)
    form["txt_Percentatge"] = liquidacion_primera.get("porcentaje_usufructo")
    form["txt_BaseImposable"] = liquidacion_primera.get("base_imponible")
    form["txt_Reduccions"] = liquidacion_primera.get("reducciones_usufructo")
    form["txt_Exces"] = liquidacion_primera.get("exceso_reducciones_nuda_propiedad")
    form["txt_BaseLiq"] = liquidacion_primera.get("base_liquidable")
    form["txt_TipusMitja"] = liquidacion_primera.get("tipo_medio_efectivo")
    form["txt_QuotaTributaria"] = liquidacion_primera.get("cuota_tributaria")
    form["txt_BonificacioQuota"] = liquidacion_primera.get("bonificacion_cuota")
    form["txt_DeduccioQuotes"] = liquidacion_primera.get("deduccion_cuotas_anteriores")
    form["txt_QuotaIngressar"] = liquidacion_primera.get("cuota_ingresar")
    form["txt_PercentatgeAl"] = liquidacion_primera.get("resto_al_porcentaje")
    form["txt_Fins"] = liquidacion_primera.get("hasta")
    form["txt_Resta"] = liquidacion_primera.get("resta")

    form["txt_ValorTotalConso"] = _fallback(liquidacion_segunda.get("valor_total_bienes_consolidados"), total_bienes)
    form["txt_PercentatgeB"] = liquidacion_segunda.get("porcentaje_usufructo")
    form["txt_BaseImposableB"] = liquidacion_segunda.get("base_imponible")
    form["txt_FinsB"] = liquidacion_segunda.get("hasta")
    form["txt_RestaB"] = liquidacion_segunda.get("resta")
    form["txt_QuotaTrib"] = liquidacion_segunda.get("cuota_tributaria")
    form["txt_RecarrecB"] = liquidacion_segunda.get("recargo")
    form["txt_IngressosDemora"] = liquidacion_segunda.get("intereses_demora")
    form["txt_TotalIngressar"] = liquidacion_segunda.get("total_ingresar")

    form["Nif_presentador"] = tramitante.get("dni_nif")
    form["txt_Cognoms_Pre"] = tramitante.get("nombre_completo_firmante")
    form["txt_ViaPublica_Pre"] = tramitante.get("nombre_via")
    form["txt_Numero_Pre"] = tramitante.get("numero_via")
    form["txt_Escalera_Pre"] = tramitante.get("escalera")
    form["txt_Pis_Pre"] = tramitante.get("piso")
    form["txt_Porta_Pre"] = tramitante.get("puerta")
    form["CP_presentador"] = tramitante.get("codigo_postal")
    form["txt_Municipi_Pre"] = tramitante.get("municipio")
    form["txt_Provincia_Pre"] = tramitante.get("provincia")
    form["txt_Pais_Pre"] = tramitante.get("pais")
    form["txt_Tlfono_Contri_Pre"] = tramitante.get("telefono")
    form["txt_Adreca_Contri_Pre"] = tramitante.get("correo_electronico")

    form["Efectiu"] = pago.get("pago_efectivo")
    form["Carrec_compte"] = pago.get("cargo_en_cuenta")
    form["campoPais"] = pago.get("pais_banco")
    form["campoCodigo"] = pago.get("digitos_control_iban")
    form["entitat"] = pago.get("entidad_banco")
    form["sucursal"] = pago.get("sucursal_banco")
    form["dcontrol"] = pago.get("digitos_control_cuenta")
    form["compte"] = pago.get("numero_cuenta")
    form["Importe1"] = pago.get("importe")

    for index, bien in enumerate(bienes[:22], start=1):
        if not isinstance(bien, dict):
            continue
        form[f"txt_Tipus_Contribuent{index}"] = bien.get("tipo")
        form[f"txt_Descripcio{index}"] = bien.get("descripcion")
        form[f"txt_Identificacio{index}"] = bien.get("identificacion")
        form[f"txt_ValorTotal{index}"] = bien.get("valor_total")

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
    parser = argparse.ArgumentParser(description="Generate Catalan Model 653 PDF from JSON data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to the JSON input (defaults to tax_models/mod653cat/json_examples/mod653cat_example.json).",
    )
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE, help="Path to the structure JSON.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Path to the field mapping JSON.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod653cat_<timestamp>.pdf).",
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
        output_path = DEFAULT_OUTPUT_DIR / f"mod653cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
