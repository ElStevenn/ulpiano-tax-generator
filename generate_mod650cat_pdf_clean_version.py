#!/usr/bin/env python3
"""
Generate a filled Catalan Model 650 (ATC-650E-6) PDF by overlaying data coming
from a structured JSON file on top of the official template.

The script performs four major steps:
1. Load and validate the JSON payload against `mod650cat_data_structure.json`.
2. Flatten the JSON so every field can be referenced with a dotted path
   (e.g. `subject.nif`, `settlement.cuotaIntegraBox16`).
3. Draw each value on a transparent PDF overlay, respecting the coordinates
   provided in `FIELD_MAPPINGS`.
4. Merge the overlay with `tax_models/650_es-cat.pdf` and write the final file
   under `/generated`.

Usage:
    python scripts/generate_mod650cat_pdf.py \
        --data tax_models/mod650cat_example.json \
        --output generated/model650cat_overlay.pdf

The default arguments already point to the sample JSON, structure description
and template inside this repository, so running the script without parameters
will generate a filled PDF in `generated/`.
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
# Offsets (multipliers) to center the drawn "X" inside checkbox widgets
CHECKBOX_X_OFFSET_MULT = -0.35  # shift left relative to font size
CHECKBOX_Y_OFFSET_MULT = -0.45  # shift down relative to font size


@dataclass(frozen=True)
class FieldMapping:
    """Configuration used to place one JSON value on top of the PDF."""

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
    # Header
    FieldMapping("header.cpr", ALL_PAGES, x=170, y_from_top=95, font_size=11),
    # Subject / presenter
    FieldMapping("subject.nif", FIRST_COPY_PAGES, x=70, y_from_top=209, font_size=11),
    FieldMapping(
        "subject.fullNameOrBusinessName",
        FIRST_COPY_PAGES,
        x=138,
        y_from_top=222,
        font_size=10,
    ),
    FieldMapping("subject.streetName", FIRST_COPY_PAGES, x=33, y_from_top=242, font_size=8),
    FieldMapping("subject.streetNumber", FIRST_COPY_PAGES, x=230, y_from_top=242, font_size=9),
    FieldMapping("subject.stair", FIRST_COPY_PAGES, x=266, y_from_top=242, font_size=9),
    FieldMapping("subject.floor", FIRST_COPY_PAGES, x=280, y_from_top=242, font_size=9),
    FieldMapping("subject.door", FIRST_COPY_PAGES, x=300, y_from_top=242, font_size=9),
    FieldMapping("subject.postalCode", FIRST_COPY_PAGES, x=34, y_from_top=263, font_size=10),
    FieldMapping("subject.municipality", FIRST_COPY_PAGES, x=100, y_from_top=263),
    FieldMapping("subject.province", FIRST_COPY_PAGES, x=230, y_from_top=263),
    FieldMapping("subject.country", FIRST_COPY_PAGES, x=290, y_from_top=263),
    FieldMapping("subject.phone", FIRST_COPY_PAGES, x=33, y_from_top=287),
    FieldMapping("subject.email", FIRST_COPY_PAGES, x=126, y_from_top=287),
    FieldMapping(
        "subject.birthDate",
        FIRST_COPY_PAGES,
        x=105,
        y_from_top=301,
        formatter="date",
        font_size=9,
    ),
    FieldMapping("subject.preExistingNetWorth", FIRST_COPY_PAGES, x=86, y_from_top=320, formatter="decimal"),
    FieldMapping("subject.kinship", FIRST_COPY_PAGES, x=205, y_from_top=301),
    FieldMapping("subject.kinshipGroup", FIRST_COPY_PAGES, x=295, y_from_top=301),
    FieldMapping("subject.disabilityPercentage", FIRST_COPY_PAGES, x=278, y_from_top=320, formatter="integer"),
    FieldMapping("subject.successionTitle", FIRST_COPY_PAGES, x=94, y_from_top=333),
    FieldMapping(
        "subject.hasDisability",
        FIRST_COPY_PAGES,
        x=253.0,
        y_from_top=318.7,
        field_type="checkbox",
    ),
    # Deceased (causante)
    FieldMapping("deceased.nif", FIRST_COPY_PAGES, x=62, y_from_top=367, font_size=11),
    FieldMapping("deceased.fullName", FIRST_COPY_PAGES, x=105, y_from_top=380, font_size=10),
    FieldMapping("deceased.streetName", FIRST_COPY_PAGES, x=33, y_from_top=400, font_size=8),
    FieldMapping("deceased.streetNumber", FIRST_COPY_PAGES, x=230, y_from_top=400, font_size=9),
    FieldMapping("deceased.stair", FIRST_COPY_PAGES, x=266, y_from_top=400, font_size=9),
    FieldMapping("deceased.floor", FIRST_COPY_PAGES, x=280, y_from_top=400, font_size=9),
    FieldMapping("deceased.door", FIRST_COPY_PAGES, x=300, y_from_top=400, font_size=9),
    FieldMapping("deceased.postalCode", FIRST_COPY_PAGES, x=34, y_from_top=421, font_size=10),
    FieldMapping("deceased.municipality", FIRST_COPY_PAGES, x=100, y_from_top=421, font_size=10),
    FieldMapping("deceased.province", FIRST_COPY_PAGES, x=230, y_from_top=421, font_size=10),
    FieldMapping("deceased.country", FIRST_COPY_PAGES, x=290, y_from_top=421, font_size=10),
    FieldMapping(
        "deceased.obligatedToWealthTaxInLastFourYears",
        FIRST_COPY_PAGES,
        x=515.8,
        y_from_top=376.5,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "deceased.isTestate",
        FIRST_COPY_PAGES,
        x=455.6,
        y_from_top=395.1,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "deceased.isIntestate",
        FIRST_COPY_PAGES,
        x=404.7,
        y_from_top=396.3,
        field_type="checkbox",
        font_size=9,
    ),
    FieldMapping(
        "deceased.numberOfInterestedParties",
        FIRST_COPY_PAGES,
        x=491,
        y_from_top=417,
        formatter="integer",
        font_size=10,
    ),
    FieldMapping("deceased.notaryOrAuthority", FIRST_COPY_PAGES, x=124, y_from_top=463, font_size=10),
    FieldMapping(
        "deceased.notarialActDate",
        FIRST_COPY_PAGES,
        x=435,
        y_from_top=463,
        formatter="date_spanish",
        font_size=9,
    ),
    # Acknowledgement block (Presentador/a)
    FieldMapping("acknowledgement.signatoryNif", FIRST_COPY_PAGES, x=65, y_from_top=607, font_size=11),
    FieldMapping("acknowledgement.signatoryFullName", FIRST_COPY_PAGES, x=136, y_from_top=622, font_size=10),
    FieldMapping("acknowledgement.streetName", FIRST_COPY_PAGES, x=33, y_from_top=642, font_size=8),
    FieldMapping("acknowledgement.streetNumber", FIRST_COPY_PAGES, x=230, y_from_top=642, font_size=9),
    FieldMapping("acknowledgement.stair", FIRST_COPY_PAGES, x=266, y_from_top=642, font_size=9),
    FieldMapping("acknowledgement.floor", FIRST_COPY_PAGES, x=280, y_from_top=642, font_size=9),
    FieldMapping("acknowledgement.door", FIRST_COPY_PAGES, x=300, y_from_top=642, font_size=9),
    FieldMapping("acknowledgement.postalCode", FIRST_COPY_PAGES, x=34, y_from_top=663, font_size=10),
    FieldMapping("acknowledgement.municipality", FIRST_COPY_PAGES, x=100, y_from_top=663, font_size=10),
    FieldMapping("acknowledgement.province", FIRST_COPY_PAGES, x=230, y_from_top=663, font_size=10),
    FieldMapping("acknowledgement.country", FIRST_COPY_PAGES, x=290, y_from_top=663, font_size=10),
    FieldMapping("acknowledgement.phone", FIRST_COPY_PAGES, x=33, y_from_top=687, font_size=10),
    FieldMapping("acknowledgement.email", FIRST_COPY_PAGES, x=126, y_from_top=687, font_size=10),
    FieldMapping(
        "acknowledgement.statementAgreement",
        FIRST_COPY_PAGES,
        x=470,
        y_from_top=611,
        field_type="checkbox",
        true_label="",
        font_size=9,
    ),
    # Signature date fields (day, month, year separated)
    FieldMapping("acknowledgement.signatureDate", FIRST_COPY_PAGES, x=470, y_from_top=642, formatter="date_spanish", font_size=9),
    # Payment area (Ingreso)

    FieldMapping("payment.bankCountry", FIRST_COPY_PAGES, x=50, y_from_top=745, font_size=10),
    FieldMapping("payment.bankControlDigits", FIRST_COPY_PAGES, x=79, y_from_top=745, font_size=10),
    FieldMapping("payment.bankEntity", FIRST_COPY_PAGES, x=115, y_from_top=745, font_size=10),
    FieldMapping("payment.bankBranch", FIRST_COPY_PAGES, x=165, y_from_top=745, font_size=10),
    FieldMapping("payment.bankControlDigits2", FIRST_COPY_PAGES, x=222, y_from_top=745, font_size=10),
    FieldMapping("payment.accountNumber", FIRST_COPY_PAGES, x=255, y_from_top=745, font_size=10),
    # Métodos de pago (a la derecha, en la línea superior)
    FieldMapping(
        "payment.chargeInAccount",
        FIRST_COPY_PAGES,
        x=362.2,
        y_from_top=725.2,
        field_type="checkbox",
    ),
    FieldMapping(
        "payment.cashPayment",
        FIRST_COPY_PAGES,
        x=439.2,
        y_from_top=726.6,
        field_type="checkbox",
    ),
    # Importe (debajo de "En efectivo", a la derecha)
    FieldMapping("payment.amount", FIRST_COPY_PAGES, x=450, y_from_top=748, formatter="decimal", font_size=9),
    # Settlement (autoliquidación) - applies to calculation pages
    FieldMapping("settlement.disabilityAllowance", SETTLEMENT_PAGES, x=200, y_from_top=207.5, formatter="decimal"),
    FieldMapping("settlement.taxLiabilityCaseGeneral", SETTLEMENT_PAGES, x=189.6, y_from_top=506.4, formatter="decimal"),
    FieldMapping("settlement.taxLiabilityAverageRate", SETTLEMENT_PAGES, x=429.0, y_from_top=433.2, formatter="decimal"),
    # Base liquidable real: show on page 4, blank on page 5
    FieldMapping("settlement.baseLiquidableRealBox13", [4], x=230, y_from_top=486, formatter="decimal", font_size=8.5),
    FieldMapping("settlement.baseLiquidableRealBox13", [5], x=504, y_from_top=642.7, formatter="decimal", font_size=8.5),
    FieldMapping("settlement.baseLiquidableTeoricaBox14", SETTLEMENT_PAGES, x=500, y_from_top=486, formatter="decimal", font_size=8.5),
    FieldMapping("settlement.cuotaIntegraBox16", SETTLEMENT_PAGES, x=230, y_from_top=556, formatter="decimal", font_size=8.5),
    FieldMapping("settlement.taxLiabilityBox605", SETTLEMENT_PAGES, x=203.8, y_from_top=575.6, formatter="blank", font_size=8.5),
    FieldMapping("settlement.excessTaxReductionBox606", SETTLEMENT_PAGES, x=210.2, y_from_top=598.8, formatter="decimal"),
    FieldMapping("settlement.adjustedTaxLiabilityBox607", SETTLEMENT_PAGES, x=220, y_from_top=616.9, formatter="blank", font_size=8.0),
    FieldMapping("settlement.tipoMedioEfectivoBox17", SETTLEMENT_PAGES, x=205, y_from_top=653.5, formatter="decimal", font_size=9.0),
    FieldMapping("settlement.cuotaTributariaAjustadaBox18", [4], x=500, y_from_top=642.7, formatter="decimal", font_size=8.5),
    FieldMapping("settlement.cuotaTributariaAjustadaBox18", [5], x=500, y_from_top=666, formatter="decimal", font_size=8.3),
    FieldMapping("settlement.bonificacionCuotaBox19", SETTLEMENT_PAGES, x=199.3, y_from_top=710.5, formatter="decimal"),
    FieldMapping("settlement.deduccionDobleImposicionBox20", SETTLEMENT_PAGES, x=198.6, y_from_top=729.3, formatter="decimal"),
    FieldMapping("settlement.deduccionCuotasAnterioresBox21", SETTLEMENT_PAGES, x=198.6, y_from_top=749.1, formatter="decimal"),
    FieldMapping("settlement.cuotaIngresarBox22", SETTLEMENT_PAGES, x=198.1, y_from_top=767.1, formatter="decimal"),
    FieldMapping("settlement.recargoBox23", SETTLEMENT_PAGES, x=467.2, y_from_top=708.3, formatter="decimal"),
    FieldMapping("settlement.interesesDemoraBox24", SETTLEMENT_PAGES, x=467.1, y_from_top=728.1, formatter="decimal"),
    FieldMapping("settlement.totalIngresarBox25", SETTLEMENT_PAGES, x=466.7, y_from_top=746.1, formatter="decimal"),
    FieldMapping("settlement.adjustedTaxLiabilityBox607", SETTLEMENT_PAGES, x=461.6, y_from_top=606.1, formatter="blank"),
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_against_structure(data: Dict[str, Any], structure_path: Path) -> None:
    """Perform a basic validation using the declarative structure description."""

    structure = load_json(structure_path)["model650cat"]["structure"]
    errors: List[str] = []

    for section in structure:
        section_id = section["id"]
        required_section = section.get("required", False)
        section_data = data.get(section_id)
        if required_section and section_data is None:
            errors.append(f"Missing required section '{section_id}'.")
            continue

        if not isinstance(section_data, dict):
            # Sections mapped to arrays are not part of the current PDF layout.
            continue

        for field in section.get("fields", []):
            field_id = field["id"]
            required_field = field.get("required", False)
            value = section_data.get(field_id)
            if required_field and (value is None or value == ""):
                errors.append(f"Missing required field '{section_id}.{field_id}'.")

    if errors:
        raise ValueError("Invalid data for Model 650 Catalonia:\n- " + "\n- ".join(errors))


def flatten_data(payload: Any, prefix: str = "") -> Dict[str, Any]:
    """Create a dotted-path dictionary for easier lookups."""

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
    Parse a Spanish IBAN into its components.
    Format: ES + 2 DC + 4 Entity + 4 Branch + 2 DC + 10 Account
    Example: ES1200491500052718123412
    Returns: {
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
    """Draw every mapped value on the appropriate overlay page."""

    # Auto-populate IBAN components from IBAN if provided
    # The IBAN is always split into its components for the form fields
    iban = flattened_data.get("payment.iban", "")
    if iban:
        iban_parts = split_spanish_iban(iban)
        # Always populate components from IBAN, even if they exist (IBAN is the source of truth)
        if iban_parts['country']:
            flattened_data["payment.bankCountry"] = iban_parts['country']
        if iban_parts['controlDigits']:
            flattened_data["payment.bankControlDigits"] = iban_parts['controlDigits']
        if iban_parts['entity']:
            flattened_data["payment.bankEntity"] = iban_parts['entity']
        if iban_parts['branch']:
            flattened_data["payment.bankBranch"] = iban_parts['branch']
        if iban_parts['controlDigits2']:
            flattened_data["payment.bankControlDigits2"] = iban_parts['controlDigits2']
        if iban_parts['accountNumber']:
            flattened_data["payment.accountNumber"] = iban_parts['accountNumber']

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
    parser = argparse.ArgumentParser(description="Generate Catalan Model 650 PDF from JSON data.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to the JSON input.")
    parser.add_argument(
        "--structure",
        type=Path,
        default=DEFAULT_STRUCTURE,
        help="Path to the structure definition JSON.",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the blank PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod650cat_<timestamp>.pdf).",
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
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
