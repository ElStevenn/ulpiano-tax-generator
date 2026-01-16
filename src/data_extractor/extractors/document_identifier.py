"""
Document identifier for automatic document type classification.
"""

from ..clients.openai_client import OpenAIVisionClient
from ..schemas.base import DocumentType
from ..config import config


class DocumentIdentifier:
    """
    Identifies the type of document from an image.
    
    Uses OpenAI Vision to classify documents into supported types
    (DNI, passport, driving license, etc.).
    """
    
    def __init__(self, client: OpenAIVisionClient | None = None):
        """
        Initialize the document identifier.
        
        Args:
            client: OpenAI Vision client (creates one if not provided)
        """
        self.client = client or OpenAIVisionClient()
        self.supported_types = config.SUPPORTED_DOCUMENT_TYPES
    
    def identify(self, image_bytes: bytes) -> DocumentType:
        """
        Identify the type of document in an image.
        
        Args:
            image_bytes: Raw image bytes of the document
            
        Returns:
            DocumentType enum value
        """
        result = self.client.classify_document(
            image_bytes, 
            self.supported_types
        )
        
        # Map string result to DocumentType enum
        type_mapping = {
            "dni": DocumentType.DNI,
            "passport": DocumentType.PASSPORT,
            "driving_license": DocumentType.DRIVING_LICENSE,
            "nie": DocumentType.NIE,
            "nota_simple": DocumentType.NOTA_SIMPLE,
            "escritura": DocumentType.ESCRITURA,
            "unknown": DocumentType.UNKNOWN,
        }
        
        return type_mapping.get(result, DocumentType.UNKNOWN)
    
    def identify_multiple(
        self, 
        images: list[bytes]
    ) -> list[tuple[int, DocumentType]]:
        """
        Identify the type of multiple documents.
        
        Args:
            images: List of raw image bytes
            
        Returns:
            List of (index, DocumentType) tuples
        """
        results = []
        for idx, image_bytes in enumerate(images):
            doc_type = self.identify(image_bytes)
            results.append((idx, doc_type))
        return results
    
    def group_by_type(
        self, 
        images: list[tuple[str, bytes]]
    ) -> dict[DocumentType, list[tuple[str, bytes]]]:
        """
        Group images by their identified document type.
        
        Args:
            images: List of (label, image_bytes) tuples
            
        Returns:
            Dictionary mapping DocumentType to list of (label, bytes) tuples
        """
        grouped: dict[DocumentType, list[tuple[str, bytes]]] = {}
        
        for label, image_bytes in images:
            doc_type = self.identify(image_bytes)
            
            if doc_type not in grouped:
                grouped[doc_type] = []
            grouped[doc_type].append((label, image_bytes))
        
        return grouped
    
    def is_same_document_type(self, images: list[bytes]) -> tuple[bool, DocumentType]:
        """
        Check if all images are of the same document type.
        
        Args:
            images: List of raw image bytes
            
        Returns:
            Tuple of (all_same, document_type)
            If not all same, document_type will be UNKNOWN
        """
        if not images:
            return True, DocumentType.UNKNOWN
        
        types = [self.identify(img) for img in images]
        
        # Filter out UNKNOWN types for comparison
        known_types = [t for t in types if t != DocumentType.UNKNOWN]
        
        if not known_types:
            return True, DocumentType.UNKNOWN
        
        first_type = known_types[0]
        all_same = all(t == first_type for t in known_types)
        
        return all_same, first_type if all_same else DocumentType.UNKNOWN
