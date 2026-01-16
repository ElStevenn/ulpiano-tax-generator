"""
Document-specific schemas for raw data extraction.
"""

from .dni import DNIRawData
from .nota_simple import NotaSimpleRawData, TitularRaw, CargaRaw, DerechoRealRaw

__all__ = [
    "DNIRawData",
    "NotaSimpleRawData",
    "TitularRaw",
    "CargaRaw",
    "DerechoRealRaw",
]
