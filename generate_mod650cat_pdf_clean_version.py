#!/usr/bin/env python3
"""
Genera un PDF rellenado del Modelo 650 de Cataluña (ATC-650E-6) superponiendo datos
provenientes de un archivo JSON estructurado sobre la plantilla oficial.

El script realiza cuatro pasos principales:
1. Cargar y validar el payload JSON contra `mod650cat_data_structure.json`.
2. Aplanar el JSON para que cada campo pueda ser referenciado con una ruta con puntos
   (ej. `sujeto.nif`, `liquidacion.cuotaIntegraCaja16`).
3. Dibujar cada valor en una superposición PDF transparente, respetando las coordenadas
   proporcionadas en `FIELD_MAPPINGS`.
4. Fusionar la superposición con `tax_models/650_es-cat.pdf` y escribir el archivo final
   bajo `/generated`.

Uso:
    python scripts/generate_mod650cat_pdf.py \
        --data tax_models/mod650cat_example.json \
        --output generated/model650cat_overlay.pdf

Los argumentos por defecto ya apuntan al JSON de ejemplo, la descripción de estructura
y la plantilla dentro de este repositorio, por lo que ejecutar el script sin parámetros
generará un PDF rellenado en `generated/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod650cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod650cat_data_structure.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "650_es-cat.pdf"
DEFAULT_OUTPUT_DIR = BASE_DIR / "generated"
# Desplazamientos (multiplicadores) para centrar la "X" dibujada dentro de los widgets de casilla
CHECKBOX_X_OFFSET_MULT = -0.35  # desplazar a la izquierda relativo al tamaño de fuente
CHECKBOX_Y_OFFSET_MULT = -0.45  # desplazar hacia abajo relativo al tamaño de fuente


@dataclass(frozen=True)
class FieldMapping:
    """Configuración utilizada para colocar un valor JSON sobre el PDF."""

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
    FieldMapping("sujeto.nif", FIRST_COPY_PAGES, x=70, y_from_top=209, font_size=11),
    FieldMapping(
        "sujeto.nombreCompletoORazonSocial",
        FIRST_COPY_PAGES,
        x=138,
        y_from_top=222,
        font_size=10,
    ),
    FieldMapping("sujeto.nombreVia", FIRST_COPY_PAGES, x=33, y_from_top=242, font_size=8),
    FieldMapping("sujeto.numeroVia", FIRST_COPY_PAGES, x=230, y_from_top=242, font_size=9),
    FieldMapping("sujeto.escalera", FIRST_COPY_PAGES, x=266, y_from_top=242, font_size=9),
    FieldMapping("sujeto.piso", FIRST_COPY_PAGES, x=280, y_from_top=242, font_size=9),
    FieldMapping("sujeto.puerta", FIRST_COPY_PAGES, x=300, y_from_top=242, font_size=9),
    FieldMapping("sujeto.codigoPostal", FIRST_COPY_PAGES, x=34, y_from_top=263, font_size=10),
    FieldMapping("sujeto.municipio", FIRST_COPY_PAGES, x=100, y_from_top=263),
    FieldMapping("sujeto.provincia", FIRST_COPY_PAGES, x=230, y_from_top=263),
    FieldMapping("sujeto.pais", FIRST_COPY_PAGES, x=290, y_from_top=263),
    FieldMapping("sujeto.telefono", FIRST_COPY_PAGES, x=33, y_from_top=287),
    FieldMapping("sujeto.correoElectronico", FIRST_COPY_PAGES, x=126, y_from_top=287),
    FieldMapping(
        "sujeto.fechaNacimiento",
        FIRST_COPY_PAGES,
        x=105,
        y_from_top=301,
        formatter="date",
        font_size=9,
    ),
    FieldMapping("sujeto.patrimonioPreexistente", FIRST_COPY_PAGES, x=86, y_from_top=320, formatter="decimal"),
    FieldMapping("sujeto.parentesco", FIRST_COPY_PAGES, x=205, y_from_top=301),
    FieldMapping("sujeto.grupoParentesco", FIRST_COPY_PAGES, x=295, y_from_top=301),
    FieldMapping("sujeto.porcentajeDiscapacidad", FIRST_COPY_PAGES, x=278, y_from_top=320, formatter="integer"),
    FieldMapping("sujeto.tituloSucesorio", FIRST_COPY_PAGES, x=94, y_from_top=333),
    FieldMapping(
        "sujeto.tieneDiscapacidad",
        FIRST_COPY_PAGES,
        x=253.0,
        y_from_top=318.7,
        field_type="checkbox",
    ),
    # Causante (fallecido)
    FieldMapping("causante.nif", FIRST_COPY_PAGES, x=62, y_from_top=367, font_size=11),
    FieldMapping("causante.nombreCompleto", FIRST_COPY_PAGES, x=105, y_from_top=380, font_size=10),
    FieldMapping("causante.nombreVia", FIRST_COPY_PAGES, x=33, y_from_top=400, font_size=8),
    FieldMapping("causante.numeroVia", FIRST_COPY_PAGES, x=230, y_from_top=400, font_size=9),
    FieldMapping("causante.escalera", FIRST_COPY_PAGES, x=266, y_from_top=400, font_size=9),
    FieldMapping("causante.piso", FIRST_COPY_PAGES, x=280, y_from_top=400, font_size=9),
    FieldMapping("causante.puerta", FIRST_COPY_PAGES, x=300, y_from_top=400, font_size=9),
    FieldMapping("causante.codigoPostal", FIRST_COPY_PAGES, x=34, y_from_top=421, font_size=10),
    FieldMapping("causante.municipio", FIRST_COPY_PAGES, x=100, y_from_top=421, font_size=10),
    FieldMapping("causante.provincia", FIRST_COPY_PAGES, x=230, y_from_top=421, font_size=10),
    FieldMapping("causante.pais", FIRST_COPY_PAGES, x=290, y_from_top=421, font_size=10),
    FieldMapping(
        "causante.obligadoImpuestoPatrimonioUltimosCuatroAnos",
        FIRST_COPY_PAGES,
        x=515.8,
        y_from_top=376.5,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "causante.esTestada",
        FIRST_COPY_PAGES,
        x=455.6,
        y_from_top=395.1,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "causante.esIntestada",
        FIRST_COPY_PAGES,
        x=404.7,
        y_from_top=396.3,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "causante.numeroPersonasInteresadas",
        FIRST_COPY_PAGES,
        x=491,
        y_from_top=417,
        formatter="integer",
        font_size=10,
    ),
    FieldMapping("causante.notarioOAutoridad", FIRST_COPY_PAGES, x=124, y_from_top=463, font_size=10),
    FieldMapping(
        "causante.fechaActaNotarial",
        FIRST_COPY_PAGES,
        x=435,
        y_from_top=463,
        formatter="date_spanish",
        font_size=9,
    ),
    # Bloque de reconocimiento (Presentador/a)
    FieldMapping("reconocimiento.nifFirmante", FIRST_COPY_PAGES, x=65, y_from_top=607, font_size=11),
    FieldMapping("reconocimiento.nombreCompletoFirmante", FIRST_COPY_PAGES, x=136, y_from_top=622, font_size=10),
    FieldMapping("reconocimiento.nombreVia", FIRST_COPY_PAGES, x=33, y_from_top=642, font_size=8),
    FieldMapping("reconocimiento.numeroVia", FIRST_COPY_PAGES, x=230, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.escalera", FIRST_COPY_PAGES, x=266, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.piso", FIRST_COPY_PAGES, x=280, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.puerta", FIRST_COPY_PAGES, x=300, y_from_top=642, font_size=9),
    FieldMapping("reconocimiento.codigoPostal", FIRST_COPY_PAGES, x=34, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.municipio", FIRST_COPY_PAGES, x=100, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.provincia", FIRST_COPY_PAGES, x=230, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.pais", FIRST_COPY_PAGES, x=290, y_from_top=663, font_size=10),
    FieldMapping("reconocimiento.telefono", FIRST_COPY_PAGES, x=33, y_from_top=687, font_size=10),
    FieldMapping("reconocimiento.correoElectronico", FIRST_COPY_PAGES, x=126, y_from_top=687, font_size=10),
    FieldMapping(
        "reconocimiento.acuerdoDeclaracion",
        FIRST_COPY_PAGES,
        x=470,
        y_from_top=611,
        field_type="checkbox",
        true_label="",
        font_size=9,
    ),
    # Campos de fecha de firma (día, mes, año separados)
    FieldMapping("reconocimiento.fechaFirma", FIRST_COPY_PAGES, x=470, y_from_top=642, formatter="date_spanish", font_size=9),
    # Área de pago (Ingreso)

    FieldMapping("pago.paisBanco", FIRST_COPY_PAGES, x=50, y_from_top=745, font_size=10),
    FieldMapping("pago.digitosControlBanco", FIRST_COPY_PAGES, x=79, y_from_top=745, font_size=10),
    FieldMapping("pago.entidadBanco", FIRST_COPY_PAGES, x=115, y_from_top=745, font_size=10),
    FieldMapping("pago.sucursalBanco", FIRST_COPY_PAGES, x=165, y_from_top=745, font_size=10),
    FieldMapping("pago.digitosControlBanco2", FIRST_COPY_PAGES, x=222, y_from_top=745, font_size=10),
    FieldMapping("pago.numeroCuenta", FIRST_COPY_PAGES, x=255, y_from_top=745, font_size=10),
    # Métodos de pago (a la derecha, en la línea superior)
    FieldMapping(
        "pago.cargoEnCuenta",
        FIRST_COPY_PAGES,
        x=362.2,
        y_from_top=725.2,
        field_type="checkbox",
    ),
    FieldMapping(
        "pago.pagoEfectivo",
        FIRST_COPY_PAGES,
        x=439.2,
        y_from_top=726.6,
        field_type="checkbox",
    ),
    # Importe (debajo de "En efectivo", a la derecha)
    FieldMapping("pago.importe", FIRST_COPY_PAGES, x=450, y_from_top=748, formatter="decimal", font_size=9),
    # Liquidación (autoliquidación) - se aplica a las páginas de cálculo
    FieldMapping("liquidacion.prestacionDiscapacidad", SETTLEMENT_PAGES, x=200, y_from_top=207.5, formatter="decimal"),
    FieldMapping("liquidacion.cuotaTributariaCasoGeneral", SETTLEMENT_PAGES, x=189.6, y_from_top=506.4, formatter="decimal"),
    FieldMapping("liquidacion.cuotaTributariaTipoMedio", SETTLEMENT_PAGES, x=429.0, y_from_top=433.2, formatter="decimal"),
    # Base liquidable real: mostrar en página 4, en blanco en página 5
    FieldMapping("liquidacion.baseLiquidableRealCaja13", [4], x=230, y_from_top=486, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.baseLiquidableRealCaja13", [5], x=504, y_from_top=642.7, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.baseLiquidableTeoricaCaja14", SETTLEMENT_PAGES, x=500, y_from_top=486, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.cuotaIntegraCaja16", SETTLEMENT_PAGES, x=230, y_from_top=556, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.cuotaTributariaCaja605", SETTLEMENT_PAGES, x=203.8, y_from_top=575.6, formatter="blank", font_size=8.5),
    FieldMapping("liquidacion.reduccionExcesoCuotaCaja606", SETTLEMENT_PAGES, x=210.2, y_from_top=598.8, formatter="decimal"),
    FieldMapping("liquidacion.cuotaTributariaAjustadaCaja607", SETTLEMENT_PAGES, x=220, y_from_top=616.9, formatter="blank", font_size=8.0),
    FieldMapping("liquidacion.tipoMedioEfectivoCaja17", SETTLEMENT_PAGES, x=205, y_from_top=653.5, formatter="decimal", font_size=9.0),
    FieldMapping("liquidacion.cuotaTributariaAjustadaCaja18", [4], x=500, y_from_top=642.7, formatter="decimal", font_size=8.5),
    FieldMapping("liquidacion.cuotaTributariaAjustadaCaja18", [5], x=500, y_from_top=666, formatter="decimal", font_size=8.3),
    FieldMapping("liquidacion.bonificacionCuotaCaja19", SETTLEMENT_PAGES, x=199.3, y_from_top=710.5, formatter="decimal"),
    FieldMapping("liquidacion.deduccionDobleImposicionCaja20", SETTLEMENT_PAGES, x=198.6, y_from_top=729.3, formatter="decimal"),
    FieldMapping("liquidacion.deduccionCuotasAnterioresCaja21", SETTLEMENT_PAGES, x=198.6, y_from_top=749.1, formatter="decimal"),
    FieldMapping("liquidacion.cuotaIngresarCaja22", SETTLEMENT_PAGES, x=198.1, y_from_top=767.1, formatter="decimal"),
    FieldMapping("liquidacion.recargoCaja23", SETTLEMENT_PAGES, x=467.2, y_from_top=708.3, formatter="decimal"),
    FieldMapping("liquidacion.interesesDemoraCaja24", SETTLEMENT_PAGES, x=467.1, y_from_top=728.1, formatter="decimal"),
    FieldMapping("liquidacion.totalIngresarCaja25", SETTLEMENT_PAGES, x=466.7, y_from_top=746.1, formatter="decimal"),
    FieldMapping("liquidacion.cuotaTributariaAjustadaCaja607", SETTLEMENT_PAGES, x=461.6, y_from_top=606.1, formatter="blank"),
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_against_structure(data: Dict[str, Any], structure_path: Path) -> None:
    """Realiza una validación básica usando la descripción de estructura declarativa."""

    structure = load_json(structure_path)["model650cat"]["structure"]
    errors: List[str] = []

    for section in structure:
        section_id = section["id"]
        required_section = section.get("required", False)
        section_data = data.get(section_id)
        if required_section and section_data is None:
            errors.append(f"Falta la sección requerida '{section_id}'.")
            continue

        if not isinstance(section_data, dict):
            # Las secciones mapeadas a arrays no son parte del diseño PDF actual.
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
    """Crea un diccionario con rutas con puntos para búsquedas más fáciles."""

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
    Analiza un IBAN español en sus componentes.
    Formato: ES + 2 DC + 4 Entidad + 4 Sucursal + 2 DC + 10 Cuenta
    Ejemplo: ES1200491500052718123412
    Retorna: {
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
    
    # Remove spaces
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


def build_overlay(
    flattened_data: Dict[str, Any],
    mappings: Sequence[FieldMapping],
    page_sizes: Sequence[Sequence[float]],
) -> PdfReader:
    """Dibuja cada valor mapeado en la página de superposición apropiada."""

    # Auto-completar componentes IBAN desde IBAN si se proporciona
    # El IBAN siempre se divide en sus componentes para los campos del formulario
    iban = flattened_data.get("pago.iban", "")
    if iban:
        iban_parts = split_spanish_iban(iban)
        # Siempre completar componentes desde IBAN, incluso si existen (IBAN es la fuente de verdad)
        if iban_parts['country']:
            flattened_data["pago.paisBanco"] = iban_parts['country']
        if iban_parts['controlDigits']:
            flattened_data["pago.digitosControlBanco"] = iban_parts['controlDigits']
        if iban_parts['entity']:
            flattened_data["pago.entidadBanco"] = iban_parts['entity']
        if iban_parts['branch']:
            flattened_data["pago.sucursalBanco"] = iban_parts['branch']
        if iban_parts['controlDigits2']:
            flattened_data["pago.digitosControlBanco2"] = iban_parts['controlDigits2']
        if iban_parts['accountNumber']:
            flattened_data["pago.numeroCuenta"] = iban_parts['accountNumber']

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
    parser = argparse.ArgumentParser(description="Genera PDF del Modelo 650 de Cataluña a partir de datos JSON.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Ruta al JSON de entrada.")
    parser.add_argument(
        "--structure",
        type=Path,
        default=DEFAULT_STRUCTURE,
        help="Ruta al JSON de definición de estructura.",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Ruta a la plantilla PDF en blanco.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta del PDF de destino (por defecto generated/mod650cat_<timestamp>.pdf).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_json(args.data)
    validate_against_structure(data, args.structure)
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
