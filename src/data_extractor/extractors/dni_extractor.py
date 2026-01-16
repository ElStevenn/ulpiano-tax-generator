"""
DNI (Documento Nacional de Identidad) extractor.
"""

from ..clients.openai_client import OpenAIVisionClient
from ..schemas.base import DocumentType
from ..schemas.documents.dni import DNIRawData, DNIFrontData, DNIBackData
from .base import BaseExtractor, ExtractionError


class DNIExtractor(BaseExtractor[DNIRawData]):
    """
    Extractor for Spanish DNI (Documento Nacional de Identidad).
    
    Extracts data from both front and back sides of the DNI and
    combines them into a single DNIRawData record.
    """
    
    document_type = DocumentType.DNI
    required_images = ["frontal", "trasero"]
    
    def __init__(self, client: OpenAIVisionClient | None = None):
        super().__init__(client)
    
    def extract(self, images: dict[str, bytes]) -> DNIRawData:
        """
        Extract data from DNI front and back images.
        
        Args:
            images: Dictionary with "frontal" and "trasero" keys
                   containing the respective image bytes
            
        Returns:
            DNIRawData with all extracted information
            
        Raises:
            ValueError: If required images are missing
            ExtractionError: If extraction fails
        """
        self.validate_images(images)
        
        try:
            # Prepare images for multi-image extraction
            image_list = [
                ("DNI Frontal (anverso)", images["frontal"]),
                ("DNI Trasero (reverso)", images["trasero"]),
            ]
            
            # Extract all data at once using multiple images
            additional_instructions = self._get_dni_extraction_instructions()
            
            result = self.client.extract_structured_from_multiple(
                images=image_list,
                schema=DNIRawData,
                additional_instructions=additional_instructions
            )
            
            return result
            
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract DNI data: {str(e)}",
                document_type=self.document_type
            )
    
    def extract_front_only(self, image_bytes: bytes) -> DNIFrontData:
        """
        Extract data from only the front side of the DNI.
        
        Args:
            image_bytes: Image bytes of the DNI front side
            
        Returns:
            DNIFrontData with front-side information
        """
        additional_instructions = """
This is the FRONT (anverso) of a Spanish DNI. Extract:
- nombre: First name(s) shown after "NOMBRE/NOM"
- apellidos: Both surnames shown after "APELLIDOS/COGNOMS"
- dni_nif: The DNI number with letter (8 digits + 1 letter, e.g., "12345678A")
- sexo: "M" for male, "F" for female
- nacionalidad: Nationality code (usually "ESP" for Spanish)
- fecha_nacimiento: Birth date in YYYY-MM-DD format
- fecha_validez: Expiry date in YYYY-MM-DD format

Note: Spanish dates on DNI are in DD MM YYYY format.
"""
        
        return self.client.extract_structured(
            image_bytes=image_bytes,
            schema=DNIFrontData,
            additional_instructions=additional_instructions
        )
    
    def extract_back_only(self, image_bytes: bytes) -> DNIBackData:
        """
        Extract data from only the back side of the DNI.
        
        Args:
            image_bytes: Image bytes of the DNI back side
            
        Returns:
            DNIBackData with back-side information
        """
        additional_instructions = """
This is the BACK (reverso) of a Spanish DNI. Extract:
- domicilio: Street address (after "DOMICILIO/DOMICILI")
- municipio: City/town name
- provincia: Province name
- lugar_nacimiento: Place of birth (after "LUGAR DE NACIMIENTO/LLOC DE NAIXEMENT")
- nombre_padre: Father's first name (after "HIJO/A DE" or "FILL/A DE", first name)
- nombre_madre: Mother's first name (second name after the slash)
- mrz_line1, mrz_line2, mrz_line3: The three lines of machine-readable text at the bottom

Note: The MRZ lines are the ones with << symbols. Extract them exactly as shown.
The parents' names appear as "HIJO/A DE: FATHER_NAME / MOTHER_NAME"
"""
        
        return self.client.extract_structured(
            image_bytes=image_bytes,
            schema=DNIBackData,
            additional_instructions=additional_instructions
        )
    
    def extract_separate_and_merge(self, images: dict[str, bytes]) -> DNIRawData:
        """
        Extract front and back separately, then merge results.
        
        This is an alternative extraction method that processes each side
        independently. Useful when the combined extraction has issues.
        
        Args:
            images: Dictionary with "frontal" and "trasero" keys
            
        Returns:
            DNIRawData with merged information
        """
        self.validate_images(images)
        
        front_data = self.extract_front_only(images["frontal"])
        back_data = self.extract_back_only(images["trasero"])
        
        return DNIRawData(
            # Front data
            nombre=front_data.nombre,
            apellidos=front_data.apellidos,
            dni_nif=front_data.dni_nif,
            sexo=front_data.sexo,
            nacionalidad=front_data.nacionalidad,
            fecha_nacimiento=front_data.fecha_nacimiento,
            fecha_validez=front_data.fecha_validez,
            # Back data
            domicilio=back_data.domicilio,
            municipio=back_data.municipio,
            provincia=back_data.provincia,
            lugar_nacimiento=back_data.lugar_nacimiento,
            nombre_padre=back_data.nombre_padre,
            nombre_madre=back_data.nombre_madre,
            mrz_line1=back_data.mrz_line1,
            mrz_line2=back_data.mrz_line2,
            mrz_line3=back_data.mrz_line3,
        )
    
    def _get_dni_extraction_instructions(self) -> str:
        """Get detailed instructions for DNI extraction."""
        return """
You are extracting data from a Spanish DNI (Documento Nacional de Identidad).
You have been provided with TWO images: the FRONT (anverso) and BACK (reverso).

FROM THE FRONT (first image), extract:
- nombre: First name(s) - appears after "NOMBRE/NOM"
- apellidos: Both surnames - appears after "APELLIDOS/COGNOMS"
- dni_nif: DNI number with verification letter (format: 8 digits + 1 letter, e.g., "47262160N")
- sexo: "M" for male (masculino/home), "F" for female (femenino/dona)
- nacionalidad: Nationality code (usually "ESP" for Spanish citizens)
- fecha_nacimiento: Birth date - appears after "FECHA DE NACIMIENTO/DATA DE NAIXEMENT"
- fecha_validez: Document expiry date - appears after "VALIDEZ/VALIDESA"

FROM THE BACK (second image), extract:
- domicilio: Full street address - appears after "DOMICILIO/DOMICILI"
- municipio: City/municipality name (e.g., "L'HOSPITALET DE LLOBREGAT")
- provincia: Province (e.g., "BARCELONA")
- lugar_nacimiento: Birth place - appears after "LUGAR DE NACIMIENTO/LLOC DE NAIXEMENT"
- nombre_padre: Father's first name - from "HIJO/A DE / FILL/A DE:" line (first name before slash)
- nombre_madre: Mother's first name - from same line (name after slash)
- mrz_line1, mrz_line2, mrz_line3: The three machine-readable zone lines at the bottom (with << characters)

IMPORTANT:
- Spanish DNI dates are displayed as "DD MM YYYY" - convert to YYYY-MM-DD format
- The MRZ contains encoded data - extract exactly as shown including all < characters
- Names may appear in both Spanish and Catalan - extract as shown
- The DNI number appears multiple times - use the clearest one
"""
