"""
Extractors module for document data extraction.
"""

from .base import BaseExtractor
from .document_identifier import DocumentIdentifier
from .dni_extractor import DNIExtractor
from .nota_simple_extractor import NotaSimpleExtractor

__all__ = ["BaseExtractor", "DocumentIdentifier", "DNIExtractor", "NotaSimpleExtractor"]
