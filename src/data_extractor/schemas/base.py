"""
Base schemas and types used across the data extractor.
"""

from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel


class DocumentType(str, Enum):
    """Supported document types for extraction."""
    # Identity documents
    DNI = "dni"
    PASSPORT = "passport"
    DRIVING_LICENSE = "driving_license"
    NIE = "nie"
    # Property documents
    NOTA_SIMPLE = "nota_simple"
    ESCRITURA = "escritura"
    # Other
    UNKNOWN = "unknown"


T = TypeVar("T", bound=BaseModel)


class ExtractionResult(BaseModel, Generic[T]):
    """
    Result of a document extraction operation.
    
    Attributes:
        success: Whether the extraction was successful
        document_type: The identified document type
        data: The extracted data (if successful)
        error: Error message (if failed)
        confidence: Confidence score of the extraction (0-1)
        raw_response: Raw response from the AI model (for debugging)
    """
    success: bool
    document_type: DocumentType
    data: T | None = None
    error: str | None = None
    confidence: float = 0.0
    raw_response: dict[str, Any] | None = None


class DocumentImage(BaseModel):
    """
    Represents a document image input.
    
    Attributes:
        label: Label identifying the image (e.g., "frontal", "trasero")
        content: Raw image bytes
    """
    label: str
    content: bytes
    
    class Config:
        arbitrary_types_allowed = True
