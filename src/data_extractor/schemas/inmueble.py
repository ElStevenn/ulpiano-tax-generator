"""
InmuebleSchema - Ulpiano format for real estate asset data.

This schema represents the complete structure of a real estate property (inmueble)
as used in the Ulpiano application.
"""

from datetime import date, datetime
from typing import Literal, Any
from pydantic import BaseModel, Field
import uuid


# Sub-schemas for nested structures

class UbicacionInmueble(BaseModel):
    """Location information for a property."""
    direccion: str | None = None
    municipio: str | None = None
    provincia: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None


class Identificador(BaseModel):
    """Key-value identifier pair."""
    key: str
    value: str | None = None


class Titularidad(BaseModel):
    """Ownership information for a property."""
    party_id: str | None = None
    persona_id: str | None = None
    sociedad_id: str | None = None
    tipo_dominio: Literal["pleno_dominio", "nuda_propiedad", "propiedad_concreta"] = "pleno_dominio"
    porcentaje: float = Field(100.0, ge=0, le=100)
    porcentaje_cuota: float | None = None
    coverage: dict[str, Any] | None = None
    display_name: str | None = None
    titulo_adquisicion: str | None = None
    titulo_adquisicion_otro: str | None = None
    caracter: str | None = None
    fecha_adquisicion: date | None = None
    fecha_nuda_propiedad: date | None = None
    valor_derecho: float | None = None
    valor_economico: float | None = None
    otros_datos: list[Identificador] | None = None


class CoberturaDerechoReal(BaseModel):
    """Coverage for a real right."""
    kind: Literal["total", "porcentaje", "titularidad"] = "total"
    porcentaje: float | None = None
    index: int | None = None


class DerechoReal(BaseModel):
    """Real right on a property."""
    tipo: Literal[
        "usufructo",
        "uso",
        "habitacion",
        "servidumbres",
        "fideicomiso_o_residuo",
        "reversion_o_condicion_resolutoria",
        "donacion_mortis_causa",
        "mandas_beneficas_o_caridad",
        "prestaciones_concretas",
        "patrimonios_protegidos",
        "derecho_a_la_legitima",
        "pago_legitima_bienes_o_rentas",
        "derecho_superficie",
        "derecho_vuelo",
        "opcion_compra",
        "tanteo_retracto_convencional",
        "retracto_comuneros",
        "retracto_colindantes_rustico",
        "aprovechamiento_por_turnos",
        "arrendamiento_inscrito",
        "usufructo_viudal_comun",
        "definicion"
    ]
    persona_id: str | None = None
    sociedad_id: str | None = None
    display_name: str | None = None
    clase: Literal["vitalicio", "temporal"] | None = None
    anios: int | None = None
    fecha_ini: date | None = None
    fecha_fin: date | None = None
    valor_economico: float | None = None
    cobertura: CoberturaDerechoReal | None = None
    origen: str | None = None
    notas: str | None = None
    valor_estimado_derecho: float | None = None


class Carga(BaseModel):
    """Charge/encumbrance on a property."""
    tipo: Literal[
        "hipoteca",
        "prenda",
        "embargo",
        "leasing",
        "reserva_dominio",
        "hipoteca_mobiliaria",
        "condicion_resolutoria",
        "afeccion_fiscal",
        "arrendamiento",
        "otra"
    ]
    importe: float | None = None
    descripcion: str | None = None
    fecha_ini: date | None = None
    fecha_fin: date | None = None
    acreedor: dict[str, Any] | None = None
    referencias: list[Identificador] | None = None


class MetadatosInmueble(BaseModel):
    """Metadata for a property."""
    fuente: Literal["manual", "importado", "integracion", "otro"] | None = None
    etiquetas: list[str] | None = None
    notas_internas: str | None = None
    version: int = 1
    creado_por: str | None = None
    actualizado_por: str | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None


class InmuebleSchema(BaseModel):
    """
    Complete property schema as used in Ulpiano application.
    
    This is the target format for Nota Simple extractions.
    Fields that cannot be extracted will remain None/default.
    """
    
    model_config = {"extra": "allow"}
    
    # Category (for inmueble it's typically a specific type)
    categoria: Literal[
        "inmueble_urbano",
        "inmueble_rustico",
        "vivienda",
        "local_comercial",
        "garaje",
        "trastero",
        "terreno",
        "nave_industrial",
        "oficina",
        "otro_inmueble"
    ] = "inmueble_urbano"
    
    # Basic info
    nombre: str | None = None
    valor_estimado: float = 0
    descripcion: str | None = None
    moneda: str = "EUR"
    
    # Location
    ubicacion: UbicacionInmueble = Field(default_factory=UbicacionInmueble)
    
    # Additional details (flexible dict for extra info)
    detalles: dict[str, Any] = Field(default_factory=dict)
    
    # Identifiers (numero finca, IDUFIR, referencia catastral, etc.)
    identificadores: list[Identificador] = Field(default_factory=list)
    
    # Ownership
    titularidades: list[Titularidad] = Field(default_factory=list)
    
    # Real rights (usufruct, etc.)
    derechos_reales: list[DerechoReal] = Field(default_factory=list)
    
    # Charges (mortgage, embargo, etc.)
    cargas: list[Carga] = Field(default_factory=list)
    
    # Documents status
    docs: dict[str, Literal["pendiente", "adjuntado"]] | None = None
    
    # Metadata
    metadatos: MetadatosInmueble = Field(default_factory=MetadatosInmueble)
    
    # Extra flexible data
    extras: dict[str, Any] | None = None
    
    # Economic activity link
    es_actividad_economica: bool = False
    actividad_economica_id: str | None = None
    
    # Extraction tracking
    extraction_source: str | None = None
    extraction_confidence: float = 0.0
    fields_extracted: list[str] = Field(default_factory=list)


def generate_temp_id() -> str:
    """Generate a temporary UUID for entities that need linking."""
    return str(uuid.uuid4())
