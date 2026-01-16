"""
Base extractor class that all document extractors inherit from.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

from ..clients.openai_client import OpenAIVisionClient
from ..schemas.base import DocumentType

T = TypeVar("T", bound=BaseModel)


class BaseExtractor(ABC, Generic[T]):
    """
    Abstract base class for document extractors.
    
    Each document type (DNI, passport, etc.) should have its own extractor
    that inherits from this class and implements the extract method.
    
    Attributes:
        document_type: The type of document this extractor handles
        required_images: List of image labels required for extraction
                        (e.g., ["frontal", "trasero"] for DNI)
    """
    
    document_type: DocumentType
    required_images: list[str]
    
    def __init__(self, client: OpenAIVisionClient | None = None):
        """
        Initialize the extractor.
        
        Args:
            client: OpenAI Vision client (creates one if not provided)
        """
        self.client = client or OpenAIVisionClient()
    
    @abstractmethod
    def extract(self, images: dict[str, bytes]) -> T:
        """
        Extract data from document images.
        
        Args:
            images: Dictionary mapping image labels to image bytes
                   (e.g., {"frontal": bytes, "trasero": bytes})
            
        Returns:
            Extracted data as a Pydantic model instance
            
        Raises:
            ValueError: If required images are missing
            ExtractionError: If extraction fails
        """
        pass
    
    def validate_images(self, images: dict[str, bytes]) -> None:
        """
        Validate that all required images are provided.
        
        Args:
            images: Dictionary of provided images
            
        Raises:
            ValueError: If any required images are missing
        """
        missing = set(self.required_images) - set(images.keys())
        if missing:
            raise ValueError(
                f"Missing required images for {self.document_type.value}: {missing}"
            )
    
    def get_extraction_prompt(self) -> str:
        """
        Get the base extraction prompt for this document type.
        
        Override this method in subclasses to provide document-specific
        extraction instructions.
        
        Returns:
            Prompt string for the AI model
        """
        return f"Extract all visible information from this {self.document_type.value} document."


class ExtractionError(Exception):
    """Exception raised when document extraction fails."""
    
    def __init__(self, message: str, document_type: DocumentType | None = None):
        self.message = message
        self.document_type = document_type
        super().__init__(self.message)
