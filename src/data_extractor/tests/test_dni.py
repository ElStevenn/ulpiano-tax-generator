#!/usr/bin/env python3
"""
Simple test script for DNI extraction.
"""

import sys
from pathlib import Path

# Add parent directory to path to enable imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_extractor.main import extract_from_files

# Define paths to example documents
base_dir = Path(__file__).parent
example_dir = base_dir / "example_docs"

frontal_path = example_dir / "dni_frontal.jpeg"
trasero_path = example_dir / "dni_trasero.jpeg"

print("=" * 60)
print("DNI EXTRACTION TEST")
print("=" * 60)
print(f"\nFrontal: {frontal_path.name}")
print(f"Trasero: {trasero_path.name}")
print("\nExtracting data...")
print("-" * 60)

# Extract data
result = extract_from_files([
    ("frontal", frontal_path),
    ("trasero", trasero_path),
])

# Display results
if result.success:
    print("\n✅ Extraction successful!")
    print(f"Document type: {result.document_type.value}")
    print(f"Confidence: {result.confidence * 100:.1f}%")
    
    person = result.data
    
    print("\n" + "=" * 60)
    print("EXTRACTED PERSON DATA")
    print("=" * 60)
    
    print(f"\n📋 Basic Information:")
    print(f"  • Name: {person.nombre}")
    print(f"  • Surnames: {person.apellidos}")
    print(f"  • DNI/NIF: {person.dni_nif}")
    print(f"  • Birth date: {person.fecha_nacimiento}")
    print(f"  • Nationality: {person.nacionalidad}")
    print(f"  • Document type: {person.tipo_documento}")
    
    print(f"\n🏠 Address:")
    print(f"  • Street: {person.direccion.linea_direccion}")
    print(f"  • City: {person.direccion.municipio}")
    print(f"  • Province: {person.direccion.provincia}")
    print(f"  • Country: {person.direccion.pais}")
    
    print(f"\n⚖️  Legal Data:")
    print(f"  • Spanish resident: {person.datos_legales.residente_en_espana}")
    print(f"  • Civil neighborhood: {person.datos_legales.vecindad_civil}")
    
    if person.observaciones:
        print(f"\n📝 Observations:")
        print(f"  {person.observaciones}")
    
    print(f"\n🔍 Extraction Metadata:")
    print(f"  • Source: {person.extraction_source}")
    print(f"  • Confidence: {person.extraction_confidence * 100:.1f}%")
    print(f"  • Fields extracted: {len(person.fields_extracted)}")
    
    print("\n" + "=" * 60)
    print("COMPLETE JSON OUTPUT")
    print("=" * 60)
    print(person.model_dump_json(indent=2, exclude_none=True))
    
else:
    print("\n❌ Extraction failed!")
    print(f"Document type: {result.document_type.value}")
    print(f"Error: {result.error}")
    
    if result.raw_response:
        print(f"\nRaw response:")
        print(result.raw_response)

print("\n" + "=" * 60)
