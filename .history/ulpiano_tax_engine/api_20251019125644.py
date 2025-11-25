from __future__ import annotations

import os
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .messages import build_error, build_warning, get_state_message
from .versions import MODEL_PDF_VERSION, MODEL_XSD_VERSION
from .xml_renderer import render_xml_650, render_xml_651
from .pdf_renderer import generate_pdf_from_template
from .validators650 import validate_model_650
from .validators651 import validate_model_651
from .io_utils import ensure_dir, write_text_file, compute_output_paths, sha256_text


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "tax_models")


def _select_validator(model_code: str) -> Callable[[dict], tuple[list[dict], list[dict]]]:
    if model_code == "650":
        return validate_model_650
    if model_code == "651":
        return validate_model_651
    raise ValueError(f"Unsupported model code: {model_code}")


def _select_xml_renderer(model_code: str) -> Callable[[dict, str, str], str]:
    if model_code == "650":
        return render_xml_650
    if model_code == "651":
        return render_xml_651
    raise ValueError(f"Unsupported model code: {model_code}")


def _select_pdf_template(model_code: str) -> str:
    filename = f"mod{model_code}.pdf"
    path = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF template not found for model {model_code}: {path}")
    return path


def generate_model(model_code: str, data: dict, output_dir: Optional[str] = None) -> dict:
    """
    Public API to generate official PDF and XML artifacts for a given model code.

    - model_code: "650" or "651"
    - data: dictionary payload containing the model data
    - output_dir: directory where the artifacts will be written (created if missing)
    """
    model_code = str(model_code)
    now = datetime.now(timezone.utc)
    timestamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    generation_id = uuid.uuid4().hex.upper()

    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "generated")
    ensure_dir(output_dir)

    pdf_version = MODEL_PDF_VERSION.get(model_code, "1.0.0")
    xsd_version = MODEL_XSD_VERSION.get(model_code, "1.0.0")

    # Validate input data
    validator = _select_validator(model_code)
    errors, warnings = validator(data)

    if errors:
        return {
            "status": "errores_de_validacion",
            "message": get_state_message("errores_de_validacion"),
            "files": {"pdfPath": None, "xmlPath": None},
            "summary": None,
            "warnings": warnings,
            "errors": errors,
            "generationId": generation_id,
            "timestampUTC": timestamp_iso,
            "meta": {
                "model": model_code,
                "versionPdf": pdf_version,
                "versionXsd": xsd_version,
            },
        }

    # Render XML
    xml_renderer = _select_xml_renderer(model_code)
    xml_text = xml_renderer(data, generation_id, timestamp_iso)
    xml_hash = sha256_text(xml_text)

    # Write files (file names follow convention)
    pdf_path, xml_path = compute_output_paths(model_code, generation_id, now, output_dir)
    write_text_file(xml_path, xml_text)

    # Generate PDF from template (copy + optional metadata)
    template_path = _select_pdf_template(model_code)
    generate_pdf_from_template(
        template_pdf_path=template_path,
        output_pdf_path=pdf_path,
        title=f"Modelo {model_code} - {generation_id}",
        subject="Autoliquidación",
        keywords=f"{model_code}, ISD",
    )

    # Summary (best-effort from input payload)
    summary = _compute_summary(data)

    status = "ok" if not warnings else "incompleto"

    return {
        "status": status,
        "message": get_state_message(status),
        "files": {"pdfPath": pdf_path, "xmlPath": xml_path},
        "summary": summary,
        "warnings": warnings,
        "errors": [],
        "generationId": generation_id,
        "timestampUTC": timestamp_iso,
        "meta": {
            "model": model_code,
            "versionPdf": pdf_version,
            "versionXsd": xsd_version,
            "xmlSha256": xml_hash,
        },
    }


def _compute_summary(data: dict) -> dict:
    # Best-effort computation using provided autoliquidation or assets/donations
    aut = data.get("autoliquidation") or {}

    def dflt(key: str) -> Optional[float]:
        value = aut.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    base_imponible = dflt("baseImponible")
    reducciones = dflt("reducciones")
    base_liquidable = dflt("baseLiquidable")
    cuota_integra = dflt("cuotaIntegra")
    bonificaciones = dflt("bonificaciones")
    cuota_liquida = dflt("cuotaLiquida")
    resultado = dflt("resultado")

    # If missing, try a basic computation from assets/donations
    if base_imponible is None:
        assets = data.get("assets") or data.get("donations") or []
        total = 0.0
        for item in assets:
            try:
                val = float(item.get("valor", 0) or 0)
                cargas = float(item.get("cargasODebenes", 0) or 0)
                total += max(0.0, val - max(0.0, cargas))
            except (TypeError, ValueError):
                continue
        base_imponible = total
        base_liquidable = total if base_liquidable is None else base_liquidable

    return {
        "baseImponible": base_imponible,
        "reducciones": reducciones,
        "baseLiquidable": base_liquidable,
        "cuotaIntegra": cuota_integra,
        "bonificaciones": bonificaciones,
        "cuotaLiquida": cuota_liquida,
        "resultado": resultado,
    }


