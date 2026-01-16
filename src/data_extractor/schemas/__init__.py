"""
Schemas module for data validation and structure definitions.
"""

from .base import DocumentType, ExtractionResult
from .person import PersonSchema
from .inmueble import InmuebleSchema

__all__ = ["DocumentType", "ExtractionResult", "PersonSchema", "InmuebleSchema"]
