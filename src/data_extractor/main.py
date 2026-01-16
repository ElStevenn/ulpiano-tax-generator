"""
Main entry point for the Data Extractor module.

This module provides high-level functions for extracting data
from various document types and mapping them to Ulpiano schemas.
"""

from pathlib import Path
from typing import Callable, Any

from .clients.openai_client import OpenAIVisionClient
from .extractors.document_identifier import DocumentIdentifier
from .extractors.dni_extractor import DNIExtractor
from .extractors.nota_simple_extractor import NotaSimpleExtractor
from .extractors.base import ExtractionError
from .mappers.dni_to_person import map_dni_to_person
from .mappers.nota_simple_to_inmueble import map_nota_simple_to_inmueble
from .schemas.base import DocumentType, ExtractionResult
from .schemas.person import PersonSchema
from .schemas.inmueble import InmuebleSchema


# Registry of extractors by document type
EXTRACTORS: dict[DocumentType, type] = {
    DocumentType.DNI: DNIExtractor,
    DocumentType.NOTA_SIMPLE: NotaSimpleExtractor,
}

# Registry of mappers by document type
MAPPERS: dict[DocumentType, Callable] = {
    DocumentType.DNI: map_dni_to_person,
    DocumentType.NOTA_SIMPLE: map_nota_simple_to_inmueble,
}


def extract_person_from_documents(
    images: list[tuple[str, bytes]],
    auto_identify: bool = True,
    document_type: DocumentType | None = None,
) -> ExtractionResult[PersonSchema]:
    """
    Extract person data from document images.
    
    This is the main entry point for the data extractor. It takes a list
    of document images, identifies the document type, extracts the data,
    and maps it to the Ulpiano PersonSchema format.
    
    Args:
        images: List of (label, image_bytes) tuples
               For DNI: [("frontal", bytes), ("trasero", bytes)]
        auto_identify: If True, automatically identify document type from images
        document_type: Explicit document type (used if auto_identify=False)
        
    Returns:
        ExtractionResult containing the PersonSchema or error information
        
    Example:
        >>> result = extract_person_from_documents([
        ...     ("frontal", open("dni_frontal.jpeg", "rb").read()),
        ...     ("trasero", open("dni_trasero.jpeg", "rb").read()),
        ... ])
        >>> if result.success:
        ...     print(result.data.nombre, result.data.apellidos)
    """
    try:
        # Create shared client
        client = OpenAIVisionClient()
        
        # Identify document type if needed
        if auto_identify:
            identifier = DocumentIdentifier(client=client)
            # Use first image for identification
            first_image = images[0][1]
            doc_type = identifier.identify(first_image)
        else:
            doc_type = document_type or DocumentType.UNKNOWN
        
        # Check if we support this document type
        if doc_type == DocumentType.UNKNOWN:
            return ExtractionResult(
                success=False,
                document_type=doc_type,
                error="Could not identify document type",
                confidence=0.0
            )
        
        if doc_type not in EXTRACTORS:
            return ExtractionResult(
                success=False,
                document_type=doc_type,
                error=f"Document type '{doc_type.value}' is not yet supported",
                confidence=0.0
            )
        
        # Create extractor and extract raw data
        extractor_class = EXTRACTORS[doc_type]
        extractor = extractor_class(client=client)
        
        # Convert list of tuples to dict
        images_dict = {label: data for label, data in images}
        raw_data = extractor.extract(images_dict)
        
        # Map to PersonSchema
        mapper = MAPPERS[doc_type]
        person = mapper(raw_data)
        
        return ExtractionResult(
            success=True,
            document_type=doc_type,
            data=person,
            confidence=0.95,
            raw_response=raw_data.model_dump()
        )
        
    except ExtractionError as e:
        return ExtractionResult(
            success=False,
            document_type=e.document_type or DocumentType.UNKNOWN,
            error=str(e),
            confidence=0.0
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            document_type=DocumentType.UNKNOWN,
            error=f"Unexpected error: {str(e)}",
            confidence=0.0
        )


def extract_dni(
    frontal_image: bytes,
    trasero_image: bytes,
) -> ExtractionResult[PersonSchema]:
    """
    Convenience function to extract person data from a Spanish DNI.
    
    Args:
        frontal_image: Image bytes of the DNI front side
        trasero_image: Image bytes of the DNI back side
        
    Returns:
        ExtractionResult containing the PersonSchema or error information
    """
    return extract_person_from_documents(
        images=[("frontal", frontal_image), ("trasero", trasero_image)],
        auto_identify=False,
        document_type=DocumentType.DNI,
    )


def extract_from_files(
    file_paths: list[tuple[str, str | Path]],
    auto_identify: bool = True,
    document_type: DocumentType | None = None,
) -> ExtractionResult[PersonSchema]:
    """
    Extract person data from document image files.
    
    Convenience function that reads files from disk and processes them.
    
    Args:
        file_paths: List of (label, file_path) tuples
        auto_identify: If True, automatically identify document type
        document_type: Explicit document type (used if auto_identify=False)
        
    Returns:
        ExtractionResult containing the PersonSchema or error information
        
    Example:
        >>> result = extract_from_files([
        ...     ("frontal", "dni_frontal.jpeg"),
        ...     ("trasero", "dni_trasero.jpeg"),
        ... ])
    """
    images = []
    for label, file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            return ExtractionResult(
                success=False,
                document_type=DocumentType.UNKNOWN,
                error=f"File not found: {file_path}",
                confidence=0.0
            )
        images.append((label, path.read_bytes()))
    
    return extract_person_from_documents(
        images=images,
        auto_identify=auto_identify,
        document_type=document_type,
    )


def extract_inmueble_from_nota_simple(
    pdf_path: str | Path,
) -> ExtractionResult[InmuebleSchema]:
    """
    Extract real estate data from a Nota Simple PDF.
    
    Args:
        pdf_path: Path to the Nota Simple PDF file
        
    Returns:
        ExtractionResult containing the InmuebleSchema or error information
        
    Example:
        >>> result = extract_inmueble_from_nota_simple("nota_simple.pdf")
        >>> if result.success:
        ...     print(result.data.nombre)
        ...     print(f"Titulares: {len(result.data.titularidades)}")
    """
    try:
        path = Path(pdf_path)
        if not path.exists():
            return ExtractionResult(
                success=False,
                document_type=DocumentType.NOTA_SIMPLE,
                error=f"File not found: {pdf_path}",
                confidence=0.0
            )
        
        # Create client and extractor
        client = OpenAIVisionClient()
        extractor = NotaSimpleExtractor(client=client)
        
        # Extract raw data
        pdf_bytes = path.read_bytes()
        raw_data = extractor.extract({"pdf": pdf_bytes})
        
        # Map to InmuebleSchema
        inmueble = map_nota_simple_to_inmueble(raw_data)
        
        return ExtractionResult(
            success=True,
            document_type=DocumentType.NOTA_SIMPLE,
            data=inmueble,
            confidence=0.9,
            raw_response=raw_data.model_dump()
        )
        
    except ExtractionError as e:
        return ExtractionResult(
            success=False,
            document_type=DocumentType.NOTA_SIMPLE,
            error=str(e),
            confidence=0.0
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            document_type=DocumentType.NOTA_SIMPLE,
            error=f"Unexpected error: {str(e)}",
            confidence=0.0
        )


def extract_nota_simple(
    pdf_bytes: bytes,
) -> ExtractionResult[InmuebleSchema]:
    """
    Extract real estate data from Nota Simple PDF bytes.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        ExtractionResult containing the InmuebleSchema or error information
    """
    try:
        client = OpenAIVisionClient()
        extractor = NotaSimpleExtractor(client=client)
        
        raw_data = extractor.extract({"pdf": pdf_bytes})
        inmueble = map_nota_simple_to_inmueble(raw_data)
        
        return ExtractionResult(
            success=True,
            document_type=DocumentType.NOTA_SIMPLE,
            data=inmueble,
            confidence=0.9,
            raw_response=raw_data.model_dump()
        )
        
    except ExtractionError as e:
        return ExtractionResult(
            success=False,
            document_type=DocumentType.NOTA_SIMPLE,
            error=str(e),
            confidence=0.0
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            document_type=DocumentType.NOTA_SIMPLE,
            error=f"Unexpected error: {str(e)}",
            confidence=0.0
        )


# Example usage (only runs when executed directly)
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Default to example docs if no args provided
    base_dir = Path(__file__).parent
    example_dir = base_dir / "example_docs"
    
    frontal_path = example_dir / "dni_frontal.jpeg"
    trasero_path = example_dir / "dni_trasero.jpeg"
    
    if len(sys.argv) >= 3:
        frontal_path = Path(sys.argv[1])
        trasero_path = Path(sys.argv[2])
    
    print(f"Extracting data from:")
    print(f"  Frontal: {frontal_path}")
    print(f"  Trasero: {trasero_path}")
    print()
    
    result = extract_from_files([
        ("frontal", frontal_path),
        ("trasero", trasero_path),
    ])
    
    if result.success:
        print("✅ Extraction successful!")
        print(f"Document type: {result.document_type.value}")
        print(f"Confidence: {result.confidence}")
        print()
        print("Extracted person data:")
        print(result.data.model_dump_json(indent=2, exclude_none=True))
    else:
        print("❌ Extraction failed!")
        print(f"Error: {result.error}")
