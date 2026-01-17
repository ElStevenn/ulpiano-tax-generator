#!/usr/bin/env python3
"""
Genera un PDF del Modelo 660 de Catalunya rellenado dibujando los valores sobre la plantilla.

Uso:
    python src/scripts_generate_models/generate_mod660cat.py \
        --data tax_models/mod660cat/json_examples/mod660cat_example.json \
        --structure tax_models/mod660cat/data_models/mod660cat_data_structure.json \
        --mapping tax_models/mod660cat/data_models/mod660cat_field_mappings.json \
        --template tax_models/mod660cat/660_es.pdf \
        --output generated/mod660cat_output.pdf
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
DEFAULT_DATA = BASE_DIR / "tax_models" / "mod660cat" / "json_examples" / "mod660cat_example.json"
DEFAULT_STRUCTURE = BASE_DIR / "tax_models" / "mod660cat" / "data_models" / "mod660cat_data_structure.json"
DEFAULT_MAPPING = BASE_DIR / "tax_models" / "mod660cat" / "data_models" / "mod660cat_field_mappings.json"
DEFAULT_TEMPLATE = BASE_DIR / "tax_models" / "mod660cat" / "660_es.pdf"
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
    if "model660cat" in raw:
        return raw["model660cat"]["structure"]
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

        if section.get("type") == "array":
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
        raise ValueError("Invalid data for Model 660 Catalonia:\n- " + "\n- ".join(errors))


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
    if fmt in {"date", "date_right", "date_year_right"}:
        if isinstance(value, str):
            parts = value.split("-")
            if len(parts) == 3:
                year, month, day = parts
                if len(year) == 4 and len(month) == 2 and len(day) == 2:
                    prefix = " " if fmt == "date_right" else ""
                    gap = "   " if fmt == "date_year_right" else "  "
                    return f"{prefix}{day} {month}{gap}{year}"
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


def _split_date(value: Any) -> Tuple[str, str, str]:
    if isinstance(value, str):
        parts = value.split("-")
        if len(parts) == 3:
            year, month, day = parts
            if len(year) == 4 and len(month) == 2 and len(day) == 2:
                return day, month, year
    return "", "", ""


def _apply_clave(form: Dict[str, Any], fields: Sequence[str], value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    if len(text) < 3:
        text = text.ljust(3)
    for index, field in enumerate(fields):
        if index < len(text):
            form[field] = text[index]


def _set_if(form: Dict[str, Any], key: str | None, value: Any) -> None:
    if key is None:
        return
    if value is None:
        return
    form[key] = value

def build_pdf_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    encabezado = _as_dict(data.get("encabezado"))
    causante = _as_dict(data.get("causante"))
    documento = _as_dict(data.get("documento"))
    presentador = _as_dict(data.get("presentador"))
    personas = _as_list(data.get("personas_interesadas"))
    paginacion = _as_dict(data.get("paginacion"))
    bienes_urbanos = _as_list(data.get("bienes_urbanos"))
    bienes_rusticos = _as_list(data.get("bienes_rusticos"))
    actividades = _as_list(data.get("actividades_no_inmuebles"))
    bienes_afectos = _as_list(data.get("bienes_afectos_actividades"))
    depositos = _as_list(data.get("depositos"))
    valores_mercado = _as_list(data.get("valores_cesion_mercado"))
    valores_no_mercado = _as_list(data.get("valores_cesion_no_mercado"))
    participaciones_mercado = _as_list(data.get("participaciones_mercado"))
    participaciones_no = _as_list(data.get("participaciones_no_mercado"))
    vehiculos = _as_list(data.get("vehiculos"))
    otros_bienes = _as_list(data.get("otros_bienes"))
    cargas = _as_list(data.get("cargas_deducibles"))
    ajuar = _as_dict(data.get("ajuar_domestico"))
    deudas = _as_list(data.get("deudas_deducibles"))
    gastos = _as_list(data.get("gastos_deducibles"))
    adicion_caudal = _as_dict(data.get("adicion_caudal"))
    adicion_personas = _as_dict(data.get("adicion_personas"))
    seguros = _as_list(data.get("seguros"))
    otros = _as_dict(data.get("otros"))
    resumen = _as_dict(data.get("resumen_caudal"))

    form: Dict[str, Any] = {}

    form["Fecha_devengo"] = encabezado.get("fecha_devengo")
    form["Fecha_mort"] = encabezado.get("fecha_defuncion")
    form["txt_Codigo"] = encabezado.get("codigo_modelo")
    form["txt_String"] = encabezado.get("codigo_modelo") or "660"
    form["txt_Aleatorio"] = encabezado.get("codigo_aleatorio")
    form["txt_Aleatorio_Ref"] = encabezado.get("codigo_aleatorio_ref")
    form["NOM_INTERESADO"] = encabezado.get("numero_personas_interesadas")

    form["Nif_contribuent"] = causante.get("dni_nif")
    form["txt_Cognoms"] = causante.get("nombre_completo")
    form["txt_ViaPublica"] = causante.get("linea_direccion")
    form["txt_Numero"] = causante.get("numero_via")
    form["txt_Escalera"] = causante.get("escalera")
    form["txt_Pis"] = causante.get("piso")
    form["txt_Porta"] = causante.get("puerta")
    form["CP_contribuent"] = causante.get("zip_code")
    form["txt_Municipi"] = causante.get("municipio")
    form["txt_Provincia"] = causante.get("provincia")
    form["txt_Pais"] = causante.get("pais")
    form["CHK_CAUSANTE"] = causante.get("obligado_impuesto_patrimonio_ultimos_cuatro_anos")
    form["Nif_contribuent2"] = causante.get("dni_nif")
    form["NOM_CAUSANTE_CABECERA"] = causante.get("nombre_completo")

    form["txt_Tipus_Dades"] = documento.get("tipo_documento")
    form["txt_Notari"] = documento.get("notario_o_autoridad")
    form["Fecha_document"] = documento.get("fecha_documento")
    form["txt_N\u00famero"] = documento.get("numero_protocolo")

    form["Nif_presentador"] = presentador.get("dni_nif")
    form["txt_Cognoms_Pre"] = presentador.get("nombre_completo")
    form["txt_ViaPublica_Pre"] = presentador.get("linea_direccion")
    form["txt_Numero_Pre"] = presentador.get("numero_via")
    form["txt_Escalera_Pre"] = presentador.get("escalera")
    form["txt_Pis_Pre"] = presentador.get("piso")
    form["txt_Porta_Pre"] = presentador.get("puerta")
    form["CP_presentador"] = presentador.get("zip_code")
    form["txt_Municipi_Pre"] = presentador.get("municipio")
    form["txt_Provincia_Pre"] = presentador.get("provincia")
    form["txt_Pais_Pre"] = presentador.get("pais")
    form["txt_Tlfono_Contri_Pre"] = presentador.get("telefono")
    form["txt_Adreca_Contri_Pre"] = presentador.get("email")

    signature_place = presentador.get("lugar_firma") or presentador.get("municipio")
    form["txt_Lugar"] = signature_place
    signature_date = presentador.get("fecha_firma") or encabezado.get("fecha_devengo") or documento.get("fecha_documento")
    dia, mes, anyo = _split_date(signature_date)
    if len(anyo) == 4:
        anyo = anyo[2:]
    form["txt_Dia"] = dia
    form["txt_Mes"] = mes
    form["txt_Anio"] = anyo

    letters = "abcdefghij"
    for idx, persona in enumerate(personas[:10]):
        if not isinstance(persona, dict):
            continue
        letter = letters[idx]
        index = idx + 1
        form[f"Nif_{letter}"] = persona.get("dni_nif")
        form[f"txt_Cognoms_{letter}"] = persona.get("nombre_completo")
        form[f"txt_ViaPublica_{letter}"] = persona.get("linea_direccion")
        form[f"txt_Numero_{letter}"] = persona.get("numero_via")
        form[f"txt_Escalera_{letter}"] = persona.get("escalera")
        form[f"txt_Pis_{letter}"] = persona.get("piso")
        form[f"txt_Porta_{letter}"] = persona.get("puerta")
        form[f"CP_{letter}"] = persona.get("zip_code")
        form[f"txt_Municipi_{letter}"] = persona.get("municipio")
        form[f"txt_Provincia_{letter}"] = persona.get("provincia")
        form[f"txt_Pais_{letter}"] = persona.get("pais")
        form[f"txt_Tlfono_{letter}"] = persona.get("telefono")
        form[f"txt_Adreca_{letter}"] = persona.get("email")
        form[f"Fecha_{letter}"] = persona.get("fecha_nacimiento")
        form[f"GRUPO{index}_INTERESADO"] = persona.get("grupo_parentesco")
        form[f"PARENTESCO{index}_INTERESADO"] = persona.get("parentesco")
        form[f"PATROMONIO{index}_INTERESADO"] = persona.get("patrimonio_valor")
        form[f"TITULO{index}_INTERESADO"] = persona.get("titulo_sucesorio")
        form[f"MINUSVALIA{index}_INTERESADO"] = persona.get("porcentaje_discapacidad")
        form[f"CHK_INTERESADA{index}"] = persona.get("tiene_discapacidad")

    form["NUM_PAGINA_INTERESADOS"] = paginacion.get("pagina_interesados")
    form["NUM_PAGINAS_INTERESADOS"] = paginacion.get("paginas_interesados")
    form["NUM_PAGINA_A"] = paginacion.get("pagina_a")
    form["NUM_PAGINAS_A"] = paginacion.get("paginas_a")
    form["NUM_PAGINA_B"] = paginacion.get("pagina_b")
    form["NUM_PAGINAS_B"] = paginacion.get("paginas_b")
    form["NUM_PAGINA_D"] = paginacion.get("pagina_d")
    form["NUM_PAGINAS_D"] = paginacion.get("paginas_d")
    form["NUM_PAGINA_F"] = paginacion.get("pagina_f")
    form["NUM_PAGINAS_F"] = paginacion.get("paginas_f")
    form["NUM_PAGINA_G"] = paginacion.get("pagina_g")
    form["NUM_PAGINAS_G"] = paginacion.get("paginas_g")
    form["NUM_PAGINA_M"] = paginacion.get("pagina_m")
    form["NUM_PAGINAS_M"] = paginacion.get("paginas_m")

    address_fields_a = {
        1: {
            "numero": "txt_Numero_1",
            "escalera": "txt_Escalera_1",
            "piso": "txt_Pis_1",
            "puerta": "txt_Porta_1",
            "cp": "CP_1",
        },
        2: {
            "numero": "txt_Numero_1_A2",
            "escalera": "txt_Escalera_1_A2",
            "piso": "txt_Pis_1_A2",
            "puerta": "txt_Porta_1_A2",
            "cp": "CP_2",
        },
        3: {
            "numero": "txt_Numero_1_A3",
            "escalera": "txt_Escalera_1_A3",
            "piso": "txt_Pis_1_A3",
            "puerta": "txt_Porta_1_A3",
            "cp": "CP_3",
        },
        4: {
            "numero": None,
            "escalera": "txt_Escalera_1_A4",
            "piso": "txt_Pis_1_A4",
            "puerta": "txt_Porta_1_A4",
            "cp": "CP_4",
        },
        5: {
            "numero": "txt_Numero_1_A5",
            "escalera": "txt_Escalera_1_A5",
            "piso": "txt_Pis_1_A5",
            "puerta": "txt_Porta_1_A5",
            "cp": "CP_5",
        },
        6: {
            "numero": "txt_Numero_1_A6",
            "escalera": "txt_Escalera_1_A6",
            "piso": "txt_Pis_1_A6",
            "puerta": "txt_Porta_1_A6",
            "cp": "CP_6",
        },
        7: {
            "numero": "txt_Numero_1_A7",
            "escalera": "txt_Escalera_1_A7",
            "piso": "txt_Pis_1_A7",
            "puerta": "txt_Porta_1_A7",
            "cp": "CP_7",
        },
        8: {
            "numero": "txt_Numero_1_A8",
            "escalera": "txt_Escalera_1_A8",
            "piso": "txt_Pis_1_A8",
            "puerta": "txt_Porta_1_A8",
            "cp": "CP_8",
        },
    }
    b_cp_fields = {1: "CP_9", 2: "CP_10"}

    for idx, bien in enumerate(bienes_urbanos[:8], start=1):
        if not isinstance(bien, dict):
            continue
        form[f"TIPO_A{idx}"] = bien.get("tipo")
        form[f"DRET_A{idx}"] = bien.get("derecho")
        form[f"VIA_PUBLICA_A{idx}"] = bien.get("via_publica")
        form[f"MUNICIPIO_A{idx}"] = bien.get("municipio")
        form[f"PROVINCIA_A{idx}"] = bien.get("provincia")
        form[f"REFERENCIA_CATASTRAL_A{idx}"] = bien.get("referencia_catastral")
        form[f"FINCA_REGISTRAL_A{idx}"] = bien.get("finca_registral")
        form[f"SUBFINCA_REGISTRAL_A{idx}"] = bien.get("subfinca_registral")
        form[f"SUPERFICIE_A{idx}"] = bien.get("superficie")
        form[f"VALOR_CATASTRAL_A{idx}"] = bien.get("valor_catastral")
        form[f"VALOR_REFERENCIA_A{idx}"] = bien.get("valor_referencia")
        form[f"VALOR_PARTICIPACION_A{idx}"] = bien.get("valor_participacion")
        form[f"VALOR_TOTAL_A{idx}"] = bien.get("valor_total")
        form[f"CHK_PARAMENT_A{idx}"] = bien.get("marca_parament")
        address = address_fields_a.get(idx, {})
        _set_if(form, address.get("numero"), bien.get("numero"))
        _set_if(form, address.get("escalera"), bien.get("escalera"))
        _set_if(form, address.get("piso"), bien.get("piso"))
        _set_if(form, address.get("puerta"), bien.get("puerta"))
        _set_if(form, address.get("cp"), bien.get("zip_code"))
        if idx in (1, 2):
            _apply_clave(form, [f"CLAU_A{idx}_1", f"CLAU_A{idx}_2", f"CLAU_A{idx}_3"], bien.get("clave_beneficio_fiscal"))
        else:
            _apply_clave(form, [f"CLAU_1_A{idx}", f"CLAU_2_A{idx}", f"CLAU_3_A{idx}"], bien.get("clave_beneficio_fiscal"))

    for idx, bien in enumerate(bienes_rusticos[:4], start=1):
        if not isinstance(bien, dict):
            continue
        form[f"TIPO_B{idx}"] = bien.get("tipo")
        form[f"DRET_B{idx}"] = bien.get("derecho")
        form[f"POLIGONO_B{idx}"] = bien.get("poligono")
        form[f"PARCELA_B{idx}"] = bien.get("parcela")
        form[f"PARAJE_B{idx}"] = bien.get("paraje")
        form[f"MUNICIPIO_B{idx}"] = bien.get("municipio")
        form[f"PROVINCIA_B{idx}"] = bien.get("provincia")
        form[f"REFERENCIA_B{idx}"] = bien.get("referencia_catastral")
        form[f"FINCA_REGISTRAL_B{idx}"] = bien.get("finca_registral")
        form[f"SUBFINCA_REGISTRAL_B{idx}"] = bien.get("subfinca_registral")
        form[f"SUPERFICIE_B{idx}"] = bien.get("superficie")
        form[f"VALOR_CATASTRAL_B{idx}"] = bien.get("valor_catastral")
        form[f"VALOR_REFERENCIA_B{idx}"] = bien.get("valor_referencia")
        form[f"VALOR_PARTICIPACION_B{idx}"] = bien.get("valor_participacion")
        form[f"VALOR_TOTAL_B{idx}"] = bien.get("valor_total")
        form[f"CHK_PARAMENT_B{idx}"] = bien.get("marca_parament")
        _set_if(form, b_cp_fields.get(idx), bien.get("zip_code"))
        _apply_clave(form, [f"CLAU_B{idx}_1", f"CLAU_B{idx}_2", f"CLAU_B{idx}_3"], bien.get("clave_beneficio_fiscal"))

    for idx, act in enumerate(actividades[:2], start=1):
        if not isinstance(act, dict):
            continue
        form[f"ACTIVIDAD_C1_{idx}"] = act.get("actividad")
        form[f"IAE_C1_{idx}"] = act.get("iae")
        form[f"DESCRIPCION_C1_{idx}"] = act.get("descripcion")
        form[f"VALOR_PARTICIPACION_C1_{idx}"] = act.get("valor_participacion")
        form[f"VALOR_TOTAL_C1_{idx}"] = act.get("valor_total")
        _apply_clave(form, [f"CLAU_C1_{idx}_1", f"CLAU_C1_{idx}_2", f"CLAU_C1_{idx}_3"], act.get("clave_beneficio_fiscal"))

    for idx, bien in enumerate(bienes_afectos[:2], start=1):
        if not isinstance(bien, dict):
            continue
        form[f"TIPO_BIEN_C2_{idx}"] = bien.get("tipo_bien")
        form[f"VIA_PUBLICA_C2_{idx}"] = bien.get("via_publica")
        form[f"MUNICIPIO_C2_{idx}"] = bien.get("municipio")
        form[f"PROVINCIA_C2_{idx}"] = bien.get("provincia")
        form[f"POLIGONO_C2_{idx}"] = bien.get("poligono")
        form[f"PARCELA_C2_{idx}"] = bien.get("parcela")
        form[f"REFERENCIA_CATASTRAL_C2_{idx}"] = bien.get("referencia_catastral")
        form[f"FINCA_REGISTRAL_C2_{idx}"] = bien.get("finca_registral")
        form[f"SUBFINCA_REGISTRAL_C2_{idx}"] = bien.get("subfinca_registral")
        form[f"SUPERFICIE_C2_{idx}"] = bien.get("superficie")
        form[f"VALOR_CATASTRAL_C2_{idx}"] = bien.get("valor_catastral")
        form[f"VALOR_REFERENCIA_C2_{idx}"] = bien.get("valor_referencia")
        form[f"VALOR_PARTICIPACION_C2_{idx}"] = bien.get("valor_participacion")
        form[f"VALOR_TOTAL_C2_{idx}"] = bien.get("valor_total")
        form[f"IAE_C2_{idx}"] = bien.get("iae")
        _apply_clave(form, [f"CLAU_C2_{idx}_1", f"CLAU_C2_{idx}_2", f"CLAU_C2_{idx}_3"], bien.get("clave_beneficio_fiscal"))
    for idx, dep in enumerate(depositos[:6], start=1):
        if not isinstance(dep, dict):
            continue
        form[f"TIPO_BIEN_D{idx}"] = dep.get("tipo_bien")
        form[f"DESCRIPCION_D{idx}"] = dep.get("descripcion")
        form[f"IAE_D{idx}"] = dep.get("iae")
        form[f"VALOR_PARTICIPACION_D{idx}"] = dep.get("valor_participacion")
        form[f"VALOR_TOTAL_D{idx}"] = dep.get("valor_total")
        _apply_clave(form, [f"CLAU_D{idx}_1", f"CLAU_D{idx}_2", f"CLAU_D{idx}_3"], dep.get("clave_beneficio_fiscal"))

    for idx, val in enumerate(valores_mercado[:2], start=1):
        if not isinstance(val, dict):
            continue
        form[f"TIPO_BIEN_E1_{idx}"] = val.get("tipo_bien")
        form[f"ENTIDAD_E1_{idx}"] = val.get("entidad")
        form[f"NIF_E1_{idx}"] = val.get("nif_emisor")
        form[f"EMISOR_E1_{idx}"] = val.get("emisor")
        form[f"IAE_E1_{idx}"] = val.get("iae")
        form[f"DESCRIPCION_E1_{idx}"] = val.get("descripcion")
        form[f"TITULOS_E1_{idx}"] = val.get("titulos")
        form[f"VALOR_COTIZACION_E1_{idx}"] = val.get("valor_cotizacion")
        form[f"VALOR_PARTICIPACION_E1_{idx}"] = val.get("valor_participacion")
        form[f"VALOR_TOTAL_E1_{idx}"] = val.get("valor_total")
        _apply_clave(form, [f"CLAU_E1_{idx}_1", f"CLAU_E1_{idx}_2", f"CLAU_E1_{idx}_3"], val.get("clave_beneficio_fiscal"))

    for idx, val in enumerate(valores_no_mercado[:2], start=1):
        if not isinstance(val, dict):
            continue
        form[f"TIPO_BIEN_E2_{idx}"] = val.get("tipo_bien")
        form[f"ENTIDAD_E2_{idx}"] = val.get("entidad")
        form[f"NIF_E2_{idx}"] = val.get("nif_emisor")
        form[f"EMISOR_E2_{idx}"] = val.get("emisor")
        form[f"NOMBRE_E2_{idx}"] = val.get("nombre")
        form[f"IAE_E2_{idx}"] = val.get("iae")
        form[f"DESCRIPCION_E2_{idx}"] = val.get("descripcion")
        form[f"VALOR_PARTICIPACION_E2_{idx}"] = val.get("valor_participacion")
        form[f"VALOR_TOTAL_E2_{idx}"] = val.get("valor_total")
        _apply_clave(form, [f"CLAU_E2_{idx}_1", f"CLAU_E2_{idx}_2", f"CLAU_E2_{idx}_3"], val.get("clave_beneficio_fiscal"))

    for idx, val in enumerate(participaciones_mercado[:4], start=1):
        if not isinstance(val, dict):
            continue
        form[f"TIPO_BIEN_F1_{idx}"] = val.get("tipo_bien")
        form[f"ENTIDAD_F1_{idx}"] = val.get("entidad")
        form[f"NIF_F1_{idx}"] = val.get("nif_emisor")
        form[f"EMISOR_F1_{idx}"] = val.get("emisor")
        form[f"NOMBRE_F1_{idx}"] = val.get("nombre")
        form[f"IAE_F1_{idx}"] = val.get("iae")
        form[f"DESCRIPCION_F1_{idx}"] = val.get("descripcion")
        form[f"VALOR_COTIZACION_F1_{idx}"] = val.get("valor_cotizacion")
        form[f"VALOR_PARTICIPACION_F1_{idx}"] = val.get("valor_participacion")
        form[f"VALOR_TOTAL_F1_{idx}"] = val.get("valor_total")
        _apply_clave(form, [f"CLAU_F1_{idx}_1", f"CLAU_F1_{idx}_2", f"CLAU_F1_{idx}_3"], val.get("clave_beneficio_fiscal"))

    for idx, val in enumerate(participaciones_no[:5], start=1):
        if not isinstance(val, dict):
            continue
        form[f"TIPO_BIEN_F2_{idx}"] = val.get("tipo_bien")
        form[f"NOMBRE_F2_{idx}"] = val.get("nombre")
        form[f"NIF_EMISOR_F2_{idx}"] = val.get("nif_emisor")
        form[f"NOMBRE_EMISOR_F2_{idx}"] = val.get("nombre_emisor")
        form[f"IAE_F2_{idx}"] = val.get("iae")
        form[f"DESCRIPCION_F2_{idx}"] = val.get("descripcion")
        form[f"VALOR_PARTICIPACION_F2_{idx}"] = val.get("valor_participacion")
        form[f"VALOR_TOTAL_F2_{idx}"] = val.get("valor_total")
        _apply_clave(form, [f"CLAU_F2_{idx}_1", f"CLAU_F2_{idx}_2", f"CLAU_F2_{idx}_3"], val.get("clave_beneficio_fiscal"))

    for idx, veh in enumerate(vehiculos[:4], start=1):
        if not isinstance(veh, dict):
            continue
        form[f"TIPO_BIEN_G_{idx}"] = veh.get("tipo_bien")
        form[f"MARCA_G_{idx}"] = veh.get("marca")
        form[f"MODELO_G_{idx}"] = veh.get("modelo")
        form[f"MATRICULA_G_{idx}"] = veh.get("matricula")
        form[f"FECHA_PRIMERAMATRICULA_G_{idx}"] = veh.get("fecha_primera_matricula")
        form[f"IAE_G_{idx}"] = veh.get("iae")
        form[f"VALOR_PARTICIPACION_G_{idx}"] = veh.get("valor_participacion")
        form[f"VALOR_TOTAL_G_{idx}"] = veh.get("valor_total")
        _apply_clave(form, [f"CLAU_G_{idx}_1", f"CLAU_G_{idx}_2", f"CLAU_G_{idx}_3"], veh.get("clave_beneficio_fiscal"))

    for idx, bien in enumerate(otros_bienes[:4], start=1):
        if not isinstance(bien, dict):
            continue
        form[f"TIPO_BIEN_H_{idx}"] = bien.get("tipo_bien")
        form[f"DESCRIPCION_H_{idx}"] = bien.get("descripcion")
        form[f"IAE_H_{idx}"] = bien.get("iae")
        form[f"VALOR_PARTICIPACION_H_{idx}"] = bien.get("valor_participacion")
        form[f"VALOR_TOTAL_H_{idx}"] = bien.get("valor_total")
        _apply_clave(form, [f"CLAU_H_{idx}_1", f"CLAU_H_{idx}_2", f"CLAU_H_{idx}_3"], bien.get("clave_beneficio_fiscal"))

    for idx, carga in enumerate(cargas[:4], start=1):
        if not isinstance(carga, dict):
            continue
        form[f"DESCRIPCION_I_{idx}"] = carga.get("descripcion")
        form[f"VALOR_PARTICIPACION_I_{idx}"] = carga.get("valor_participacion")
        form[f"VALOR_TOTAL_I_{idx}"] = carga.get("valor_total")

    form["DESCRIPCION_J_1"] = ajuar.get("descripcion")
    form["VALOR_DECLARADO_J_1"] = ajuar.get("valor_declarado")

    for idx, deuda in enumerate(deudas[:5], start=1):
        if not isinstance(deuda, dict):
            continue
        form[f"DESCRIPCION_K_{idx}"] = deuda.get("descripcion")
        form[f"VALOR_PARTICIPACION_K_{idx}"] = deuda.get("valor_participacion")
        form[f"VALOR_TOTAL_K_{idx}"] = deuda.get("valor_total")

    for idx, gasto in enumerate(gastos[:3], start=1):
        if not isinstance(gasto, dict):
            continue
        form[f"TIPO_BIEN_L_{idx}"] = gasto.get("tipo_bien")
        form[f"DESCRIPCION_L_{idx}"] = gasto.get("descripcion")
        form[f"VALOR_PARTICIPACION_L_{idx}"] = gasto.get("valor_participacion")

    form["DESCRIPCION_M1_1"] = adicion_caudal.get("descripcion")
    form["CATASTRO_M1_1"] = adicion_caudal.get("referencia_catastral")
    form["VALOR_PARTICIPACION_M1_1"] = adicion_caudal.get("valor_participacion")
    form["VALOR_TOTAL_M1_1"] = adicion_caudal.get("valor_total")
    form["VALOR_INGRESAR_M1_1"] = adicion_caudal.get("valor_ingresar")

    form["DESCRIPCION_M2_1"] = adicion_personas.get("descripcion")
    form["CATASTRO_M2_1"] = adicion_personas.get("referencia_catastral")
    form["NIF_M2_1"] = adicion_personas.get("dni_nif")
    form["NOMBRE_M2_1"] = adicion_personas.get("nombre")
    form["VALOR_PARTICIPACION_M2_1"] = adicion_personas.get("valor_participacion")
    form["VALOR_TOTAL_M2_1"] = adicion_personas.get("valor_total")
    form["VALOR_INGRESAR_M2_1"] = adicion_personas.get("valor_ingresar")

    for idx, seguro in enumerate(seguros[:4], start=1):
        if not isinstance(seguro, dict):
            continue
        form[f"ENTIDAD_N_{idx}"] = seguro.get("entidad")
        form[f"POLIZA_N_{idx}"] = seguro.get("numero_poliza")
        form[f"BENEFICIARIO_N_{idx}"] = seguro.get("beneficiario")
        form[f"CONTRASTADO_N_{idx}"] = seguro.get("contratante")
        form[f"FECHA_N_{idx}"] = seguro.get("fecha_contratacion")
        form[f"VALOR_DECLARADO_N_{idx}"] = seguro.get("valor_declarado")
        form[f"VALOR_TOTAL_N_{idx}"] = seguro.get("valor_total")
        form[f"DESCRIPCION_N{idx}"] = seguro.get("descripcion")
        _apply_clave(form, [f"CLAU_N_{idx}_1", f"CLAU_N_{idx}_2", f"CLAU_N_{idx}_3"], seguro.get("clave_beneficio_fiscal"))

    form["TIPO_BIEN_O_1"] = otros.get("tipo_bien")
    form["DESCRIPCION_O_1"] = otros.get("descripcion")
    form["REFERENCIA_O_1"] = otros.get("referencia_catastral")
    form["NIF_O_1"] = otros.get("dni_nif")
    form["NOMBRE_O_1"] = otros.get("nombre")
    form["ESCRITURA_O_1"] = otros.get("datos_escritura")
    form["VALOR_O_1"] = otros.get("valor")
    _apply_clave(form, ["CLAU_O_1_1", "CLAU_O_1_2", "CLAU_O_1_3"], otros.get("clave_beneficio_fiscal"))

    form["VALUE_A"] = resumen.get("value_a")
    form["VALUE_B"] = resumen.get("value_b")
    form["VALUE_C"] = resumen.get("value_c")
    form["VALUE_D"] = resumen.get("value_d")
    form["VALUE_E"] = resumen.get("value_e")
    form["VALUE_F"] = resumen.get("value_f")
    form["VALUE_G"] = resumen.get("value_g")
    form["VALUE_H"] = resumen.get("value_h")
    form["VALUE_100"] = resumen.get("value_100")
    form["VALUE_I"] = resumen.get("value_i")
    form["VALUE_200"] = resumen.get("value_200")
    form["VALUE_201"] = resumen.get("value_201")
    form["VALUE_202"] = resumen.get("value_202")
    form["VALUE_203"] = resumen.get("value_203")
    form["VALUE_204"] = resumen.get("value_204")
    form["VALUE_J"] = resumen.get("value_j")
    form["VALUE_Z"] = resumen.get("value_z")
    form["VALUE_K"] = resumen.get("value_k")
    form["VALUE_L"] = resumen.get("value_l")
    form["VALUE_101"] = resumen.get("value_101")
    form["VALUE_M1"] = resumen.get("value_m1")
    form["VALUE_P"] = resumen.get("value_p")
    form["VALUE_01"] = resumen.get("value_01")

    extra_form = data.get("form")
    if isinstance(extra_form, dict):
        form.update(extra_form)

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
    parser = argparse.ArgumentParser(description="Generate Catalan Model 660 PDF from JSON data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to the JSON input (defaults to tax_models/mod660cat/json_examples/mod660cat_example.json).",
    )
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE, help="Path to the structure JSON.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Path to the field mapping JSON.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Path to the PDF template.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination PDF path (defaults to generated/mod660cat_<timestamp>.pdf).",
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
        output_path = DEFAULT_OUTPUT_DIR / f"mod660cat_{timestamp}.pdf"

    merge_with_template(args.template, overlay_reader, output_path)
    print(f"Generated PDF at {output_path}")


if __name__ == "__main__":
    main()
