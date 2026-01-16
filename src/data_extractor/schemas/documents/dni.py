"""
Schema for raw DNI (Documento Nacional de Identidad) data extraction.
"""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class DNIRawData(BaseModel):
    """
    Raw data extracted from a Spanish DNI document.
    
    This schema represents the data that can be directly extracted
    from the front and back sides of a DNI.
    """
    
    # Front side data
    nombre: str = Field(..., description="First name(s) of the person")
    apellidos: str = Field(..., description="Surnames (apellido1 apellido2)")
    dni_nif: str = Field(..., description="DNI number with letter (e.g., 12345678A)")
    sexo: Literal["M", "F"] = Field(..., description="Sex: M (male) or F (female)")
    nacionalidad: str = Field(..., description="Nationality code (e.g., ESP)")
    fecha_nacimiento: date = Field(..., description="Date of birth")
    fecha_validez: date = Field(..., description="Document expiry date")
    
    # Back side data
    domicilio: str = Field(..., description="Street address line")
    municipio: str = Field(..., description="City/Municipality")
    provincia: str = Field(..., description="Province")
    lugar_nacimiento: str = Field(..., description="Place of birth")
    nombre_padre: str | None = Field(None, description="Father's first name")
    nombre_madre: str | None = Field(None, description="Mother's first name")
    
    # MRZ data (optional, for validation)
    mrz_line1: str | None = Field(None, description="First MRZ line")
    mrz_line2: str | None = Field(None, description="Second MRZ line")
    mrz_line3: str | None = Field(None, description="Third MRZ line")


class DNIFrontData(BaseModel):
    """Data extracted specifically from the front of the DNI."""
    
    nombre: str
    apellidos: str
    dni_nif: str
    sexo: Literal["M", "F"]
    nacionalidad: str
    fecha_nacimiento: date
    fecha_validez: date


class DNIBackData(BaseModel):
    """Data extracted specifically from the back of the DNI."""
    
    domicilio: str
    municipio: str
    provincia: str
    lugar_nacimiento: str
    nombre_padre: str | None = None
    nombre_madre: str | None = None
    mrz_line1: str | None = None
    mrz_line2: str | None = None
    mrz_line3: str | None = None
