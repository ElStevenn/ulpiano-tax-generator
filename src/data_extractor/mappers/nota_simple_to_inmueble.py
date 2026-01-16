"""
Mapper to transform Nota Simple raw data to Ulpiano InmuebleSchema.
"""

from ..schemas.documents.nota_simple import NotaSimpleRawData, TitularRaw, CargaRaw, DerechoRealRaw
from ..schemas.inmueble import (
    InmuebleSchema,
    UbicacionInmueble,
    Identificador,
    Titularidad,
    DerechoReal,
    CoberturaDerechoReal,
    Carga,
    MetadatosInmueble,
    generate_temp_id,
)


def map_nota_simple_to_inmueble(nota_simple: NotaSimpleRawData) -> InmuebleSchema:
    """
    Map Nota Simple extracted data to Ulpiano InmuebleSchema format.
    
    This mapper transforms the raw data extracted from a Nota Simple
    into the complete InmuebleSchema used by the Ulpiano application.
    
    Args:
        nota_simple: Raw data extracted from a Nota Simple
        
    Returns:
        InmuebleSchema populated with available data
    """
    
    # Determine category based on property type
    categoria = _determine_category(nota_simple)
    
    # Build property name from description or address
    nombre = _build_property_name(nota_simple)
    
    # Build location
    ubicacion = UbicacionInmueble(
        direccion=_normalize_text(nota_simple.direccion),
        municipio=_normalize_text(nota_simple.municipio),
        provincia=_normalize_text(nota_simple.provincia),
        pais="España",
        codigo_postal=nota_simple.codigo_postal,
    )
    
    # Build identifiers
    identificadores = _build_identifiers(nota_simple)
    
    # Build ownership records
    titularidades = [
        _map_titular(t) for t in nota_simple.titulares
    ]
    
    # Build real rights
    derechos_reales = [
        _map_derecho_real(d) for d in nota_simple.derechos_reales
    ]
    
    # Build charges
    cargas = [
        _map_carga(c) for c in nota_simple.cargas
        if not c.cancelada  # Only include active charges
    ]
    
    # Build details dict with additional info
    detalles = _build_detalles(nota_simple)
    
    # Track extracted fields
    fields_extracted = _get_extracted_fields(nota_simple)
    
    # Build metadata
    metadatos = MetadatosInmueble(
        fuente="importado",
        notas_internas=f"Extraído de Nota Simple - {nota_simple.registro}",
    )
    
    return InmuebleSchema(
        categoria=categoria,
        nombre=nombre,
        valor_estimado=0,  # Not available in Nota Simple
        descripcion=nota_simple.descripcion,
        moneda="EUR",
        ubicacion=ubicacion,
        detalles=detalles,
        identificadores=identificadores,
        titularidades=titularidades,
        derechos_reales=derechos_reales,
        cargas=cargas,
        metadatos=metadatos,
        extraction_source="nota_simple",
        extraction_confidence=0.9,
        fields_extracted=fields_extracted,
    )


def _determine_category(nota_simple: NotaSimpleRawData) -> str:
    """Determine the property category based on type and use."""
    if nota_simple.tipo_finca == "rustica":
        return "inmueble_rustico"
    
    uso = (nota_simple.uso or "").lower()
    
    if "vivienda" in uso or "piso" in uso or "apartamento" in uso:
        return "vivienda"
    elif "local" in uso or "comercial" in uso:
        return "local_comercial"
    elif "garaje" in uso or "parking" in uso or "aparcamiento" in uso:
        return "garaje"
    elif "trastero" in uso or "almacen" in uso:
        return "trastero"
    elif "terreno" in uso or "solar" in uso:
        return "terreno"
    elif "nave" in uso or "industrial" in uso:
        return "nave_industrial"
    elif "oficina" in uso:
        return "oficina"
    
    return "inmueble_urbano"


def _build_property_name(nota_simple: NotaSimpleRawData) -> str:
    """Build a descriptive name for the property."""
    parts = []
    
    # Start with property type
    if nota_simple.tipo_finca == "rustica":
        parts.append("Finca Rústica")
    else:
        uso = nota_simple.uso or "Inmueble"
        parts.append(_normalize_text(uso))
    
    # Add address
    if nota_simple.direccion:
        parts.append(f"en {_normalize_text(nota_simple.direccion)}")
    
    # Add municipality if different from address
    if nota_simple.municipio and nota_simple.municipio.lower() not in (nota_simple.direccion or "").lower():
        parts.append(f"({_normalize_text(nota_simple.municipio)})")
    
    return " ".join(parts)


def _build_identifiers(nota_simple: NotaSimpleRawData) -> list[Identificador]:
    """Build the list of property identifiers."""
    identifiers = []
    
    if nota_simple.numero_finca:
        identifiers.append(Identificador(
            key="numero_finca",
            value=nota_simple.numero_finca
        ))
    
    if nota_simple.idufir:
        identifiers.append(Identificador(
            key="idufir",
            value=nota_simple.idufir
        ))
    
    if nota_simple.referencia_catastral:
        identifiers.append(Identificador(
            key="referencia_catastral",
            value=nota_simple.referencia_catastral
        ))
    
    # Registry data
    registry_ref = []
    if nota_simple.tomo:
        registry_ref.append(f"Tomo {nota_simple.tomo}")
    if nota_simple.libro:
        registry_ref.append(f"Libro {nota_simple.libro}")
    if nota_simple.folio:
        registry_ref.append(f"Folio {nota_simple.folio}")
    if nota_simple.inscripcion:
        registry_ref.append(f"Inscripción {nota_simple.inscripcion}")
    
    if registry_ref:
        identifiers.append(Identificador(
            key="datos_registrales",
            value=", ".join(registry_ref)
        ))
    
    if nota_simple.registro:
        identifiers.append(Identificador(
            key="registro",
            value=nota_simple.registro
        ))
    
    return identifiers


def _map_titular(titular: TitularRaw) -> Titularidad:
    """Map a raw titular to Titularidad schema."""
    # Generate temporary ID for linking
    temp_id = generate_temp_id()
    
    # Map tipo_dominio
    tipo_dominio_map = {
        "pleno_dominio": "pleno_dominio",
        "nuda_propiedad": "nuda_propiedad",
        "usufructo": "pleno_dominio",  # Usufructo goes to derechos_reales
        "propiedad_concreta": "propiedad_concreta",
    }
    tipo_dominio = tipo_dominio_map.get(titular.tipo_dominio, "pleno_dominio")
    
    return Titularidad(
        party_id=temp_id,
        persona_id=temp_id,  # Temporary, needs to be linked to actual person
        sociedad_id=None,
        tipo_dominio=tipo_dominio,
        porcentaje=titular.porcentaje,
        display_name=_normalize_text(titular.nombre_completo),
        titulo_adquisicion=titular.titulo_adquisicion,
        caracter=titular.caracter,
        fecha_adquisicion=titular.fecha_adquisicion,
        otros_datos=[
            Identificador(key="dni_nif", value=titular.dni_nif)
        ] if titular.dni_nif else None,
    )


def _map_derecho_real(derecho: DerechoRealRaw) -> DerechoReal:
    """Map a raw derecho real to DerechoReal schema."""
    temp_id = generate_temp_id()
    
    # Map tipo
    tipo_map = {
        "usufructo": "usufructo",
        "uso": "uso",
        "habitacion": "habitacion",
        "servidumbre": "servidumbres",
        "superficie": "derecho_superficie",
        "vuelo": "derecho_vuelo",
        "opcion_compra": "opcion_compra",
        "tanteo_retracto": "tanteo_retracto_convencional",
        "arrendamiento": "arrendamiento_inscrito",
        "otro": "usufructo",  # Default
    }
    tipo = tipo_map.get(derecho.tipo, "usufructo")
    
    # Build coverage
    cobertura = CoberturaDerechoReal(
        kind="porcentaje" if derecho.porcentaje_afectacion < 100 else "total",
        porcentaje=derecho.porcentaje_afectacion if derecho.porcentaje_afectacion < 100 else None,
    )
    
    return DerechoReal(
        tipo=tipo,
        persona_id=temp_id,
        display_name=_normalize_text(derecho.titular_nombre),
        clase=derecho.clase,
        anios=derecho.duracion_anos,
        fecha_ini=derecho.fecha_inicio,
        fecha_fin=derecho.fecha_fin,
        cobertura=cobertura,
        notas=derecho.descripcion,
    )


def _map_carga(carga: CargaRaw) -> Carga:
    """Map a raw carga to Carga schema."""
    # Map tipo
    tipo_map = {
        "hipoteca": "hipoteca",
        "embargo": "embargo",
        "anotacion_preventiva": "embargo",
        "condicion_resolutoria": "condicion_resolutoria",
        "afeccion_fiscal": "afeccion_fiscal",
        "servidumbre": "otra",
        "arrendamiento": "arrendamiento",
        "otra": "otra",
        "otros": "otra",  # Alternative spelling
    }
    tipo = tipo_map.get(carga.tipo, "otra")
    
    # Build acreedor dict if available
    acreedor = {"nombre": carga.acreedor} if carga.acreedor else None
    
    return Carga(
        tipo=tipo,
        importe=carga.importe,
        descripcion=carga.descripcion,
        fecha_ini=carga.fecha_inscripcion,
        fecha_fin=carga.fecha_vencimiento,
        acreedor=acreedor,
    )


def _build_detalles(nota_simple: NotaSimpleRawData) -> dict:
    """Build the detalles dict with additional property info."""
    detalles = {}
    
    if nota_simple.superficie_construida_m2:
        detalles["superficie_construida_m2"] = nota_simple.superficie_construida_m2
    
    if nota_simple.superficie_util_m2:
        detalles["superficie_util_m2"] = nota_simple.superficie_util_m2
    
    if nota_simple.superficie_suelo_m2:
        detalles["superficie_suelo_m2"] = nota_simple.superficie_suelo_m2
    
    if nota_simple.superficie_parcela_m2:
        detalles["superficie_parcela_m2"] = nota_simple.superficie_parcela_m2
    
    if nota_simple.uso:
        detalles["uso"] = nota_simple.uso
    
    if nota_simple.tiene_cargas:
        detalles["tiene_cargas"] = True
    else:
        detalles["libre_de_cargas"] = True
    
    if nota_simple.fecha_emision:
        detalles["fecha_nota_simple"] = str(nota_simple.fecha_emision)
    
    if nota_simple.csv:
        detalles["csv_nota_simple"] = nota_simple.csv
    
    if nota_simple.notas_marginales:
        detalles["notas_marginales"] = nota_simple.notas_marginales
    
    return detalles


def _get_extracted_fields(nota_simple: NotaSimpleRawData) -> list[str]:
    """Get list of fields that were extracted."""
    fields = []
    
    if nota_simple.numero_finca:
        fields.append("numero_finca")
    if nota_simple.idufir:
        fields.append("idufir")
    if nota_simple.registro:
        fields.append("registro")
    if nota_simple.descripcion:
        fields.append("descripcion")
    if nota_simple.direccion:
        fields.append("ubicacion.direccion")
    if nota_simple.municipio:
        fields.append("ubicacion.municipio")
    if nota_simple.provincia:
        fields.append("ubicacion.provincia")
    if nota_simple.referencia_catastral:
        fields.append("referencia_catastral")
    if nota_simple.titulares:
        fields.append("titularidades")
    if nota_simple.cargas:
        fields.append("cargas")
    if nota_simple.derechos_reales:
        fields.append("derechos_reales")
    
    return fields


def _normalize_text(text: str | None) -> str | None:
    """Normalize text to proper case."""
    if not text:
        return text
    
    # Particles that should remain lowercase
    particles = {"de", "del", "la", "las", "los", "el", "y", "e", "i", "en", "a"}
    
    words = text.lower().split()
    result = []
    
    for i, word in enumerate(words):
        # Handle apostrophes (L'Hospitalet, etc.)
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
