"""
PersonSchema - Ulpiano format for family member data.

This schema represents the complete structure of a person/family member
as used in the Ulpiano application.
"""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, EmailStr


# Sub-schemas for nested structures

class DatosLegales(BaseModel):
    """Legal data of the person."""
    residente_en_espana: bool = False
    vecindad_civil: str | None = None  # e.g., "ES-AND", "ES-CAT"
    estado_civil: Literal["soltero", "casado", "divorciado", "viudo", "separado"] | None = None
    regimen_economico: Literal["gananciales", "separacion", "participacion"] | None = None
    conyuge_id: str | None = None
    observaciones: str = ""


class Direccion(BaseModel):
    """Address information."""
    linea_direccion: str | None = None
    municipio: str | None = None
    provincia: str | None = None
    pais: str | None = None
    zip_code: str | None = None


class Discapacidad(BaseModel):
    """Disability information."""
    tipo: Literal["fisica", "psiquica", "sensorial"] | None = None
    grado: Literal["leve", "moderado", "severo"] | None = None
    nivel_dependencia: Literal["leve", "moderado", "severo"] | None = None
    necesitad_de_asistencia_permanente: bool = False
    observaciones: str | None = None
    porcentaje: int = 0


class PatrimonioPreexistente(BaseModel):
    """Pre-existing patrimony information."""
    patrimonio_valor: float = 0
    coeficiente_multiplicador: float = 1


class OtrosDatos(BaseModel):
    """Additional data."""
    titulo: str | None = None
    descripcion: str | None = None
    regimen_matrimonial: str | None = None


class SituacionEnExpediente(BaseModel):
    """Role in the case/file."""
    causante: bool = False
    heredero: bool = False
    tramitante: bool = False
    otro: bool = False
    testador: bool = False
    desheredado: bool = False


class RelacionCausantePersona(BaseModel):
    """Relationship with the deceased."""
    convivencia_ayuda_mutua: bool = False
    metadata: dict = Field(default_factory=dict)


class BienAfecto(BaseModel):
    """Asset linked to economic activity."""
    bien_id: str | None = None
    porcentaje_afectacion: int = 100
    indivisible: bool = False
    valor_bien_al_fecha: float = 0
    deuda_asociada: float = 0
    justificacion_afectacion: str | None = None


class ActividadEconomica(BaseModel):
    """Economic activity information."""
    tipo: Literal["autonomo_profesional", "vinculo_laboral"] | None = None
    persona_id: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    estado: Literal["aplica", "no_aplica"] | None = None
    porcentaje_reduccion_isd: float = 0
    cnae: str | None = None
    es_arrendamiento: bool = False
    empleado_ft: bool = False
    nombre_empleado: str | None = None
    valor_neto_afecto: float = 0
    rendimientos_anuales: float = 0
    tiene_contabilidad_formal: bool = True
    actividad_verificada: bool = True
    reducible_isd: bool = True
    porcentaje_reduccion: float = 0
    compromiso_mantenimiento_5a: bool = True
    fecha_inicio_mantenimiento: date | None = None
    fecha_alta_RETA: date | None = None
    empleados_count: int = 0
    empleado_ft_confirmado: bool = True
    rendimientos_trabajo_y_ae_total: float = 0
    remuneracion_direccion_anual: float = 0
    documentos_contabilidad: list[str] = Field(default_factory=list)
    peritaje_valor: str | None = None
    bienes_afectos: list[BienAfecto] = Field(default_factory=list)
    
    # Fields for vinculo_laboral type
    antiguedad_direccion_anos: int | None = None
    antiguedad_vinculo_anos: int | None = None
    entidad_no_patrimonial: bool = False
    entidad_sociedad: str | None = None
    es_sociedad_laboral: bool = False
    fecha_inicio_direccion: date | None = None
    fecha_inicio_vinculo: date | None = None
    participacion_adquirida: float | None = None
    participacion_previa: float | None = None
    participacion_resultante: float | None = None
    reference_person_id: str | None = None
    sociedad_id: str | None = None
    vinculo_subtype: str | None = None


class PersonSchema(BaseModel):
    """
    Complete person schema as used in Ulpiano application.
    
    This is the target format for all document extractions.
    Fields that cannot be extracted from a document will remain None/default.
    """
    
    model_config = {"extra": "allow", "protected_namespaces": ()}
    
    # Basic identification
    nombre: str | None = None
    apellidos: str | None = None
    dni_nif: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    tipo_documento: Literal["dni", "nie", "pasaporte", "otro"] | None = None
    nacionalidad: str | None = None
    
    # Family relationships
    padre_id: str | None = None
    madre_id: str | None = None
    
    # Status
    fecha_defuncion: date | None = None
    es_causante: bool = False
    
    # Fiscal residence
    residencia_fiscal_espana: bool = True
    residencia_fiscal: str | None = None
    
    # Observations
    observaciones: str | None = None
    
    # Nested objects
    datos_legales: DatosLegales = Field(default_factory=DatosLegales)
    direccion: Direccion = Field(default_factory=Direccion)
    discapacidad: Discapacidad | None = None
    patrimonio_preexistente: PatrimonioPreexistente = Field(default_factory=PatrimonioPreexistente)
    
    # Lists
    deudas: list = Field(default_factory=list)
    
    # Other data
    otros_datos: OtrosDatos = Field(default_factory=OtrosDatos)
    donaciones_previas: list = Field(default_factory=list)
    
    # Case situation
    situacion_en_expediente: SituacionEnExpediente = Field(default_factory=SituacionEnExpediente)
    rol_otro_descripcion: str | None = None
    
    # Relationship with deceased
    relacion_causante_persona: RelacionCausantePersona = Field(default_factory=RelacionCausantePersona)
    
    # Economic activities
    actividades_economicas: list[ActividadEconomica] = Field(default_factory=list)
    
    # Metadata for extraction tracking (using extra fields)
    extraction_source: str | None = None
    extraction_confidence: float = 0.0
    fields_extracted: list[str] = Field(default_factory=list)
