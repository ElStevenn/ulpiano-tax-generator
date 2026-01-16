#!/usr/bin/env python3
"""
Test script for Nota Simple extraction.
"""

import sys
from pathlib import Path

# Add parent directory to path to enable imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_extractor.main import extract_inmueble_from_nota_simple

# Define paths to example documents
base_dir = Path(__file__).parent
example_dir = base_dir / "example_docs"

# Available Nota Simple files
nota_simple_files = [
    "Nota SImple 3.pdf",
    "NOTA SIMPLE FINCA BANYOLES.pdf",
    "NOTA SIMPLE FINCA SANT PERE PESCADOR.pdf",
]


def test_nota_simple(file_name: str):
    """Test extraction from a single Nota Simple file."""
    file_path = example_dir / file_name
    
    print("=" * 70)
    print(f"NOTA SIMPLE EXTRACTION TEST: {file_name}")
    print("=" * 70)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"\nExtracting data from: {file_path.name}")
    print("-" * 70)
    
    # Extract data
    result = extract_inmueble_from_nota_simple(file_path)
    
    # Display results
    if result.success:
        print("\n✅ Extraction successful!")
        print(f"Document type: {result.document_type.value}")
        print(f"Confidence: {result.confidence * 100:.1f}%")
        
        inmueble = result.data
        
        print("\n" + "=" * 70)
        print("EXTRACTED PROPERTY DATA")
        print("=" * 70)
        
        print(f"\n🏠 Basic Information:")
        print(f"  • Name: {inmueble.nombre}")
        print(f"  • Category: {inmueble.categoria}")
        print(f"  • Description: {(inmueble.descripcion or '')[:100]}...")
        
        print(f"\n📍 Location:")
        print(f"  • Address: {inmueble.ubicacion.direccion}")
        print(f"  • City: {inmueble.ubicacion.municipio}")
        print(f"  • Province: {inmueble.ubicacion.provincia}")
        print(f"  • Country: {inmueble.ubicacion.pais}")
        if inmueble.ubicacion.codigo_postal:
            print(f"  • Postal Code: {inmueble.ubicacion.codigo_postal}")
        
        print(f"\n🔑 Identifiers:")
        for ident in inmueble.identificadores:
            print(f"  • {ident.key}: {ident.value}")
        
        if inmueble.titularidades:
            print(f"\n👥 Owners ({len(inmueble.titularidades)}):")
            for i, titular in enumerate(inmueble.titularidades, 1):
                print(f"  {i}. {titular.display_name}")
                print(f"     - Type: {titular.tipo_dominio}")
                print(f"     - Percentage: {titular.porcentaje}%")
                if titular.titulo_adquisicion:
                    print(f"     - Title: {titular.titulo_adquisicion}")
                if titular.fecha_adquisicion:
                    print(f"     - Acquisition date: {titular.fecha_adquisicion}")
        
        if inmueble.cargas:
            print(f"\n⚠️  Charges ({len(inmueble.cargas)}):")
            for i, carga in enumerate(inmueble.cargas, 1):
                print(f"  {i}. {carga.tipo}: {carga.descripcion or 'N/A'}")
                if carga.importe:
                    print(f"     - Amount: {carga.importe:,.2f} EUR")
        else:
            print(f"\n✓ No active charges (libre de cargas)")
        
        if inmueble.derechos_reales:
            print(f"\n📜 Real Rights ({len(inmueble.derechos_reales)}):")
            for i, derecho in enumerate(inmueble.derechos_reales, 1):
                print(f"  {i}. {derecho.tipo}: {derecho.display_name}")
                if derecho.clase:
                    print(f"     - Class: {derecho.clase}")
        
        if inmueble.detalles:
            print(f"\n📊 Additional Details:")
            for key, value in inmueble.detalles.items():
                print(f"  • {key}: {value}")
        
        print(f"\n🔍 Extraction Metadata:")
        print(f"  • Source: {inmueble.extraction_source}")
        print(f"  • Confidence: {inmueble.extraction_confidence * 100:.1f}%")
        print(f"  • Fields extracted: {len(inmueble.fields_extracted)}")
        
        print("\n" + "=" * 70)
        print("COMPLETE JSON OUTPUT")
        print("=" * 70)
        print(inmueble.model_dump_json(indent=2, exclude_none=True))
        
    else:
        print("\n❌ Extraction failed!")
        print(f"Document type: {result.document_type.value}")
        print(f"Error: {result.error}")
        
        if result.raw_response:
            print(f"\nRaw response:")
            print(result.raw_response)
    
    print("\n" + "=" * 70 + "\n")


def main():
    """Run tests on all available Nota Simple files or a specific one."""
    if len(sys.argv) > 1:
        # Test specific file
        file_name = sys.argv[1]
        test_nota_simple(file_name)
    else:
        # Test first available file by default
        print("Available Nota Simple files:")
        for i, f in enumerate(nota_simple_files, 1):
            print(f"  {i}. {f}")
        print(f"\nTesting: {nota_simple_files[0]}")
        print("(Pass filename as argument to test a specific file)\n")
        
        test_nota_simple(nota_simple_files[0])


if __name__ == "__main__":
    main()
