"""
Schema for raw Nota Simple (Property Registry Document) data extraction.
"""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class TitularRaw(BaseModel):
    """
    Raw data for a property owner/holder extracted from Nota Simple.
    """
    nombre_completo: str = Field(..., description="Full name of the owner")
    dni_nif: str | None = Field(None, description="DNI/NIF/CIF of the owner")
    tipo_dominio: Literal[
        "pleno_dominio", 
        "nuda_propiedad", 
        "usufructo",
        "propiedad_concreta"
    ] = Field("pleno_dominio", description="Type of ownership")
    porcentaje: float = Field(100.0, description="Ownership percentage (0-100)")
    caracter: str | None = Field(None, description="Character of ownership: privativo, ganancial, etc.")
    titulo_adquisicion: str | None = Field(None, description="Title of acquisition: compraventa, herencia, etc.")
    fecha_adquisicion: date | None = Field(None, description="Date of acquisition")


class CargaRaw(BaseModel):
    """
    Raw data for a charge/encumbrance extracted from Nota Simple.
    """
    tipo: Literal[
        "hipoteca",
        "embargo",
        "anotacion_preventiva",
        "condicion_resolutoria",
        "afeccion_fiscal",
        "servidumbre",
        "arrendamiento",
        "otra",
        "otros"  # Alternative spelling
    ] = Field(..., description="Type of charge")
    descripcion: str = Field(..., description="Description of the charge")
    importe: float | None = Field(None, description="Amount if applicable (e.g., mortgage principal)")
    acreedor: str | None = Field(None, description="Creditor name (e.g., bank for mortgage)")
    fecha_inscripcion: date | None = Field(None, description="Registration date")
    fecha_vencimiento: date | None = Field(None, description="Expiration date if applicable")
    cancelada: bool = Field(False, description="Whether the charge has been cancelled")


class DerechoRealRaw(BaseModel):
    """
    Raw data for a real right extracted from Nota Simple.
    """
    tipo: Literal[
        "usufructo",
        "uso",
        "habitacion",
        "servidumbre",
        "superficie",
        "vuelo",
        "opcion_compra",
        "tanteo_retracto",
        "arrendamiento",
        "otro"
    ] = Field(..., description="Type of real right")
    titular_nombre: str = Field(..., description="Name of the right holder")
    titular_dni: str | None = Field(None, description="DNI/NIF of the right holder")
    clase: Literal["vitalicio", "temporal"] | None = Field(None, description="Class: lifetime or temporary")
    duracion_anos: int | None = Field(None, description="Duration in years if temporal")
    fecha_inicio: date | None = Field(None, description="Start date")
    fecha_fin: date | None = Field(None, description="End date if applicable")
    descripcion: str | None = Field(None, description="Additional description")
    porcentaje_afectacion: float = Field(100.0, description="Percentage of property affected")


class NotaSimpleRawData(BaseModel):
    """
    Raw data extracted from a Spanish Nota Simple (Property Registry Extract).
    
    This schema represents all the data that can be extracted from a Nota Simple
    document issued by the Registro de la Propiedad.
    """
    
    # Finca identification
    numero_finca: str = Field(..., description="Property number in the registry")
    idufir: str | None = Field(None, description="Unique property identifier (IDUFIR/CRU)")
    registro: str = Field(..., description="Name of the Property Registry")
    tomo: str | None = Field(None, description="Volume number")
    libro: str | None = Field(None, description="Book number")
    folio: str | None = Field(None, description="Page number")
    inscripcion: str | None = Field(None, description="Registration number")
    
    # Property description
    tipo_finca: Literal["urbana", "rustica"] = Field(..., description="Property type: urban or rural")
    descripcion: str = Field(..., description="Full property description from the document")
    uso: str | None = Field(None, description="Property use: vivienda, local, garaje, etc.")
    
    # Areas
    superficie_construida_m2: float | None = Field(None, description="Built area in square meters")
    superficie_util_m2: float | None = Field(None, description="Usable area in square meters")
    superficie_suelo_m2: float | None = Field(None, description="Land area in square meters")
    superficie_parcela_m2: float | None = Field(None, description="Plot area in square meters (for rustic)")
    
    # Location
    direccion: str = Field(..., description="Full street address")
    municipio: str = Field(..., description="Municipality/City")
    provincia: str = Field(..., description="Province")
    codigo_postal: str | None = Field(None, description="Postal code")
    
    # Cadastral reference
    referencia_catastral: str | None = Field(None, description="Cadastral reference number")
    
    # Owners
    titulares: list[TitularRaw] = Field(default_factory=list, description="List of property owners")
    
    # Charges and encumbrances
    cargas: list[CargaRaw] = Field(default_factory=list, description="List of charges/encumbrances")
    tiene_cargas: bool = Field(False, description="Whether the property has any charges")
    
    # Real rights
    derechos_reales: list[DerechoRealRaw] = Field(default_factory=list, description="List of real rights")
    
    # Document metadata
    fecha_emision: date | None = Field(None, description="Date the Nota Simple was issued")
    csv: str | None = Field(None, description="Secure Verification Code of the document")
    
    # Additional info
    notas_marginales: str | None = Field(None, description="Marginal notes if any")
    observaciones: str | None = Field(None, description="Additional observations")
