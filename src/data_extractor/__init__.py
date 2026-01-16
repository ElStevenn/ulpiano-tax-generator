"""
Data Extractor Module for Ulpiano Tax Generator

This module extracts structured data from various document types (DNI, Nota Simple, etc.)
and maps them to Ulpiano schemas (PersonSchema, InmuebleSchema).

Usage:
    # DNI extraction
    from data_extractor import extract_dni, extract_from_files
    
    result = extract_from_files([
        ("frontal", "path/to/dni_frontal.jpeg"),
        ("trasero", "path/to/dni_trasero.jpeg"),
    ])
    
    if result.success:
        person = result.data
        print(person.nombre, person.apellidos)
    
    # Nota Simple extraction
    from data_extractor import extract_inmueble_from_nota_simple
    
    result = extract_inmueble_from_nota_simple("nota_simple.pdf")
    
    if result.success:
        inmueble = result.data
        print(inmueble.nombre)
        print(f"Titulares: {len(inmueble.titularidades)}")
"""

from .main import (
    extract_person_from_documents,
    extract_dni,
    extract_from_files,
    extract_inmueble_from_nota_simple,
    extract_nota_simple,
)
from .schemas.base import DocumentType, ExtractionResult
from .schemas.person import PersonSchema
from .schemas.inmueble import InmuebleSchema

__all__ = [
    # Person extraction
    "extract_person_from_documents",
    "extract_dni",
    "extract_from_files",
    # Inmueble extraction
    "extract_inmueble_from_nota_simple",
    "extract_nota_simple",
    # Types
    "DocumentType",
    "ExtractionResult",
    "PersonSchema",
    "InmuebleSchema",
]
