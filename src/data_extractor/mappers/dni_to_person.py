"""
Mapper to transform DNI raw data to Ulpiano PersonSchema.
"""

from ..schemas.documents.dni import DNIRawData
from ..schemas.person import (
    PersonSchema,
    DatosLegales,
    Direccion,
)


def _normalize_name(name: str) -> str:
    """
    Normalize a name from uppercase to proper title case.
    
    Handles Spanish/Catalan naming conventions like particles (de, del, la, etc.)
    that should remain lowercase, and apostrophe cases like L'Hospitalet.
    
    Args:
        name: Name string (possibly in uppercase)
        
    Returns:
        Properly capitalized name
    """
    if not name:
        return name
    
    # Particles that should remain lowercase (unless at start)
    particles = {"de", "del", "la", "las", "los", "el", "y", "e", "i"}
    
    words = name.lower().split()
    result = []
    
    for i, word in enumerate(words):
        # Handle apostrophe cases like L'Hospitalet, D'Andorra
        if "'" in word:
            parts = word.split("'")
            word = "'".join(p.capitalize() for p in parts)
            result.append(word)
        # First word or not a particle -> capitalize
        elif i == 0 or word not in particles:
            result.append(word.capitalize())
        else:
            result.append(word)
    
    return " ".join(result)


def _normalize_address(address: str) -> str:
    """
    Normalize an address string to proper case.
    
    Args:
        address: Address string (possibly in uppercase)
        
    Returns:
        Properly capitalized address
    """
    if not address:
        return address
    
    # Common address abbreviations to keep uppercase or handle specially
    abbreviations = {
        "crer": "Crer.",
        "c/": "C/",
        "av": "Av.",
        "av.": "Av.",
        "avda": "Avda.",
        "avda.": "Avda.",
        "pl": "Pl.",
        "pl.": "Pl.",
        "pza": "Pza.",
        "pza.": "Pza.",
        "po": "PO",
    }
    
    words = address.lower().split()
    result = []
    
    for word in words:
        word_lower = word.lower().rstrip(".")
        if word_lower in abbreviations:
            result.append(abbreviations[word_lower])
        else:
            result.append(word.capitalize())
    
    return " ".join(result)


def map_dni_to_person(dni_data: DNIRawData) -> PersonSchema:
    """
    Map DNI extracted data to Ulpiano PersonSchema format.
    
    This mapper transforms the raw data extracted from a Spanish DNI
    into the complete PersonSchema used by the Ulpiano application.
    
    Fields that cannot be determined from the DNI will use default values.
    
    Args:
        dni_data: Raw data extracted from a Spanish DNI
        
    Returns:
        PersonSchema populated with available data from the DNI
    """
    
    # Map nationality code to full name
    nationality_map = {
        "ESP": "España",
        "ESPAÑOLA": "España",
        "ES": "España",
    }
    nacionalidad = nationality_map.get(
        dni_data.nacionalidad.upper(), 
        dni_data.nacionalidad
    )
    
    # Determine if Spanish resident based on nationality
    is_spanish = dni_data.nacionalidad.upper() in ["ESP", "ESPAÑOLA", "ES"]
    
    # Build the address from DNI back side data (normalized)
    direccion = Direccion(
        linea_direccion=_normalize_address(dni_data.domicilio),
        municipio=_normalize_name(dni_data.municipio),
        provincia=_normalize_name(dni_data.provincia),
        pais="España" if is_spanish else None,
        zip_code=None,  # Not available on DNI
    )
    
    # Build datos_legales with Spanish residency
    datos_legales = DatosLegales(
        residente_en_espana=is_spanish,
        # vecindad_civil could be inferred from province but requires mapping
        vecindad_civil=_infer_vecindad_from_province(dni_data.provincia),
        estado_civil=None,  # Not available on DNI
        regimen_economico=None,  # Not available on DNI
        conyuge_id=None,
        observaciones="",
    )
    
    # Determine document type
    tipo_documento = "dni" if dni_data.dni_nif and dni_data.dni_nif[0].isdigit() else "nie"
    
    # Track which fields were extracted
    fields_extracted = [
        "nombre",
        "apellidos", 
        "dni_nif",
        "fecha_nacimiento",
        "nacionalidad",
        "direccion.linea_direccion",
        "direccion.municipio",
        "direccion.provincia",
    ]
    
    return PersonSchema(
        nombre=_normalize_name(dni_data.nombre),
        apellidos=_normalize_name(dni_data.apellidos),
        dni_nif=dni_data.dni_nif,
        email=None,  # Not available on DNI
        telefono=None,  # Not available on DNI
        fecha_nacimiento=dni_data.fecha_nacimiento,
        tipo_documento=tipo_documento,
        nacionalidad=nacionalidad,
        padre_id=None,  # Would need to be linked externally
        madre_id=None,  # Would need to be linked externally
        fecha_defuncion=None,
        es_causante=False,
        residencia_fiscal_espana=is_spanish,
        residencia_fiscal="España" if is_spanish else None,
        observaciones=_build_observations(dni_data),
        datos_legales=datos_legales,
        direccion=direccion,
        discapacidad=None,  # Not available on DNI
        extraction_source="dni",
        extraction_confidence=0.95,
        fields_extracted=fields_extracted,
    )


def _infer_vecindad_from_province(provincia: str | None) -> str | None:
    """
    Infer the vecindad civil code from the province.
    
    Spanish civil neighborhood (vecindad civil) determines which civil law
    regime applies to a person.
    
    Args:
        provincia: Province name
        
    Returns:
        Vecindad civil code (e.g., "ES-CAT", "ES-AND") or None
    """
    if not provincia:
        return None
    
    provincia_upper = provincia.upper().strip()
    
    # Catalonia provinces
    catalan_provinces = ["BARCELONA", "TARRAGONA", "LLEIDA", "GIRONA"]
    if provincia_upper in catalan_provinces:
        return "ES-CAT"
    
    # Basque Country provinces
    basque_provinces = ["VIZCAYA", "BIZKAIA", "GUIPUZCOA", "GIPUZKOA", "ALAVA", "ARABA"]
    if provincia_upper in basque_provinces:
        return "ES-PVA"
    
    # Galicia provinces
    galician_provinces = ["A CORUÑA", "LA CORUÑA", "LUGO", "OURENSE", "PONTEVEDRA"]
    if provincia_upper in galician_provinces:
        return "ES-GAL"
    
    # Navarra
    if provincia_upper in ["NAVARRA", "NAFARROA"]:
        return "ES-NAV"
    
    # Aragon
    aragonese_provinces = ["ZARAGOZA", "HUESCA", "TERUEL"]
    if provincia_upper in aragonese_provinces:
        return "ES-ARA"
    
    # Balearic Islands
    if provincia_upper in ["BALEARES", "ILLES BALEARS", "ISLAS BALEARES"]:
        return "ES-BAL"
    
    # Andalusia
    andalusian_provinces = [
        "ALMERIA", "CADIZ", "CORDOBA", "GRANADA", 
        "HUELVA", "JAEN", "MALAGA", "SEVILLA"
    ]
    if provincia_upper in andalusian_provinces:
        return "ES-AND"
    
    # Default to common civil code (derecho común)
    return "ES-COM"


def _build_observations(dni_data: DNIRawData) -> str:
    """
    Build observations field with additional context from DNI.
    
    Args:
        dni_data: Raw DNI data
        
    Returns:
        Observations string with relevant notes
    """
    observations = []
    
    # Add parents' names if available (normalized)
    if dni_data.nombre_padre or dni_data.nombre_madre:
        parents = []
        if dni_data.nombre_padre:
            parents.append(f"Padre: {_normalize_name(dni_data.nombre_padre)}")
        if dni_data.nombre_madre:
            parents.append(f"Madre: {_normalize_name(dni_data.nombre_madre)}")
        observations.append(" / ".join(parents))
    
    # Add place of birth (normalized)
    if dni_data.lugar_nacimiento:
        observations.append(f"Lugar de nacimiento: {_normalize_name(dni_data.lugar_nacimiento)}")
    
    # Add document validity
    if dni_data.fecha_validez:
        observations.append(f"DNI válido hasta: {dni_data.fecha_validez}")
    
    return " | ".join(observations) if observations else ""
