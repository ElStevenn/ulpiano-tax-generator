"""
Nota Simple (Property Registry Document) extractor.
"""

from pathlib import Path

from ..clients.openai_client import OpenAIVisionClient
from ..schemas.base import DocumentType
from ..schemas.documents.nota_simple import NotaSimpleRawData
from ..utils.pdf_utils import pdf_to_images, is_valid_pdf
from .base import BaseExtractor, ExtractionError


class NotaSimpleExtractor(BaseExtractor[NotaSimpleRawData]):
    """
    Extractor for Spanish Nota Simple (Property Registry Extract).
    
    Extracts property data from PDF documents including:
    - Property identification (finca number, IDUFIR)
    - Property description and area
    - Location
    - Owners and ownership percentages
    - Charges and encumbrances (mortgages, embargos)
    - Real rights (usufruct, etc.)
    """
    
    document_type = DocumentType.NOTA_SIMPLE
    required_images = ["pdf"]  # Single PDF input
    
    def __init__(self, client: OpenAIVisionClient | None = None):
        super().__init__(client)
    
    def extract(self, images: dict[str, bytes]) -> NotaSimpleRawData:
        """
        Extract data from a Nota Simple PDF.
        
        Args:
            images: Dictionary with "pdf" key containing PDF bytes,
                   or multiple page images labeled "page_1", "page_2", etc.
            
        Returns:
            NotaSimpleRawData with all extracted information
            
        Raises:
            ValueError: If no valid input provided
            ExtractionError: If extraction fails
        """
        try:
            # Determine input type and convert to images
            if "pdf" in images:
                # Convert PDF to images
                pdf_bytes = images["pdf"]
                if not is_valid_pdf(pdf_bytes):
                    raise ValueError("Invalid PDF file provided")
                
                page_images = pdf_to_images(pdf_bytes, dpi=150)
                image_list = [
                    (f"Página {i+1}", img) for i, img in enumerate(page_images)
                ]
            else:
                # Already have page images
                image_list = [
                    (label, data) for label, data in images.items()
                    if label.startswith("page_") or label.startswith("pagina_")
                ]
                if not image_list:
                    raise ValueError("No PDF or page images provided")
            
            # Extract data using multi-image analysis
            additional_instructions = self._get_nota_simple_extraction_instructions()
            
            result = self.client.extract_structured_from_multiple(
                images=image_list,
                schema=NotaSimpleRawData,
                additional_instructions=additional_instructions
            )
            
            return result
            
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract Nota Simple data: {str(e)}",
                document_type=self.document_type
            )
    
    def extract_from_file(self, pdf_path: str | Path) -> NotaSimpleRawData:
        """
        Extract data from a Nota Simple PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            NotaSimpleRawData with all extracted information
        """
        path = Path(pdf_path)
        if not path.exists():
            raise ValueError(f"File not found: {pdf_path}")
        
        pdf_bytes = path.read_bytes()
        return self.extract({"pdf": pdf_bytes})
    
    def _get_nota_simple_extraction_instructions(self) -> str:
        """Get detailed instructions for Nota Simple extraction."""
        return """
You are extracting data from a Spanish NOTA SIMPLE (Property Registry Extract).
This is an official document from the Registro de la Propiedad that contains information about a real estate property.

EXTRACT THE FOLLOWING INFORMATION:

## 1. PROPERTY IDENTIFICATION (usually at the top)
- numero_finca: The "FINCA" number (e.g., "FINCA N.º 1234")
- idufir: The IDUFIR or CRU code (unique identifier, usually 14 digits)
- registro: Name of the Property Registry (e.g., "REGISTRO DE LA PROPIEDAD DE BANYOLES")
- tomo, libro, folio, inscripcion: Registry volume, book, page, and inscription numbers

## 2. PROPERTY DESCRIPTION
- tipo_finca: "urbana" or "rustica"
- descripcion: Full property description from the document
- uso: Type of use (vivienda, local, garaje, trastero, etc.)
- superficie_construida_m2: Built area in square meters
- superficie_util_m2: Usable area in square meters
- superficie_suelo_m2: Land area in square meters
- superficie_parcela_m2: Plot area (for rural properties)

## 3. LOCATION
- direccion: Full street address
- municipio: Municipality/City
- provincia: Province
- codigo_postal: Postal code if mentioned
- referencia_catastral: Cadastral reference number (usually starts with numbers, contains letters)

## 4. OWNERS (TITULARIDAD section)
For each owner, extract:
- nombre_completo: Full name
- dni_nif: ID number (DNI, NIF, NIE)
- tipo_dominio: pleno_dominio, nuda_propiedad, usufructo, or propiedad_concreta
- porcentaje: Ownership percentage (e.g., "50%" = 50.0)
- caracter: privativo, ganancial, proindiviso, etc.
- titulo_adquisicion: How they acquired it (compraventa, herencia, donación, etc.)
- fecha_adquisicion: Date of acquisition

## 5. CHARGES (CARGAS section)
For each charge, extract:
- tipo: hipoteca, embargo, anotacion_preventiva, condicion_resolutoria, afeccion_fiscal, servidumbre, arrendamiento, otra
- descripcion: Description of the charge
- importe: Amount (for mortgages, the principal amount)
- acreedor: Creditor name (bank for mortgages)
- fecha_inscripcion: Registration date
- fecha_vencimiento: Expiration date if applicable
- cancelada: true if cancelled, false otherwise

Look for text like "LIBRE DE CARGAS" (no charges) or "CARGAS:" followed by charge details.

## 6. REAL RIGHTS (DERECHOS REALES)
For usufruct, use, habitación, etc.:
- tipo: usufructo, uso, habitacion, servidumbre, etc.
- titular_nombre: Name of the right holder
- titular_dni: ID number
- clase: vitalicio (lifetime) or temporal
- duracion_anos: Duration in years if temporal
- fecha_inicio, fecha_fin: Start and end dates

## 7. DOCUMENT METADATA
- fecha_emision: Date the Nota Simple was issued
- csv: Secure Verification Code if present

IMPORTANT RULES:
- Extract ACTUAL values from the document, not placeholders
- Use null for fields that are not present in the document
- Dates must be in YYYY-MM-DD format
- Percentages should be numeric (50.0 for 50%)
- For "tiene_cargas": true if there are any active charges, false if "LIBRE DE CARGAS"
- Names should be extracted exactly as they appear
- If multiple pages, combine information from all pages
"""
