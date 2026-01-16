# Data Extractor - Ulpiano Tax Generator

Python module for extracting structured data from identity documents and mapping them to the Ulpiano PersonSchema format.

## Features

- **Automatic document type identification** using OpenAI Vision
- **DNI extraction** from front and back images
- **Extensible architecture** for adding new document types
- **Direct mapping** to Ulpiano PersonSchema format

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
Create or edit `.env` file:
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o  # optional, defaults to gpt-4o
```

## Usage

### Quick Test

Run the test script with the example DNI:
```bash
python test_dni.py
```

### As a Module

From the parent directory (`src/`):
```bash
cd /home/paumateu/Desktop/Ulpiano/ulpiano-tax-generator/src
python -c "from data_extractor import extract_from_files; print(extract_from_files([('frontal', 'data_extractor/example_docs/dni_frontal.jpeg'), ('trasero', 'data_extractor/example_docs/dni_trasero.jpeg')]))"
```

### In Your Code

```python
from data_extractor import extract_from_files, extract_dni, DocumentType

# Option 1: From file paths (auto-detect document type)
result = extract_from_files([
    ("frontal", "path/to/dni_frontal.jpeg"),
    ("trasero", "path/to/dni_trasero.jpeg"),
])

# Option 2: From bytes
with open("dni_frontal.jpeg", "rb") as f1, open("dni_trasero.jpeg", "rb") as f2:
    frontal_bytes = f1.read()
    trasero_bytes = f2.read()
    result = extract_dni(frontal_bytes, trasero_bytes)

# Check result
if result.success:
    person = result.data
    print(f"Name: {person.nombre} {person.apellidos}")
    print(f"DNI: {person.dni_nif}")
    print(f"Address: {person.direccion.linea_direccion}")
    
    # Export to JSON
    json_data = person.model_dump_json(indent=2, exclude_none=True)
else:
    print(f"Error: {result.error}")
```

## Project Structure

```
data_extractor/
├── __init__.py                 # Main exports
├── main.py                     # Entry point functions
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── test_dni.py                 # Test script
├── schemas/
│   ├── base.py                 # Base types
│   ├── person.py               # PersonSchema (Ulpiano)
│   └── documents/
│       └── dni.py              # DNI raw schema
├── extractors/
│   ├── base.py                 # BaseExtractor
│   ├── document_identifier.py # Auto classification
│   └── dni_extractor.py        # DNI extractor
├── mappers/
│   └── dni_to_person.py        # DNI → PersonSchema
├── clients/
│   └── openai_client.py        # OpenAI Vision API
└── utils/
    └── image_utils.py          # Image helpers
```

## Adding New Document Types

1. **Create a schema** in `schemas/documents/`:
```python
# schemas/documents/passport.py
class PassportRawData(BaseModel):
    nombre: str
    # ... other fields
```

2. **Create an extractor** in `extractors/`:
```python
# extractors/passport_extractor.py
class PassportExtractor(BaseExtractor[PassportRawData]):
    document_type = DocumentType.PASSPORT
    required_images = ["main"]
    
    def extract(self, images: dict[str, bytes]) -> PassportRawData:
        # ... extraction logic
```

3. **Create a mapper** in `mappers/`:
```python
# mappers/passport_to_person.py
def map_passport_to_person(passport_data: PassportRawData) -> PersonSchema:
    # ... mapping logic
```

4. **Register in main.py**:
```python
EXTRACTORS = {
    DocumentType.DNI: DNIExtractor,
    DocumentType.PASSPORT: PassportExtractor,  # Add this
}

MAPPERS = {
    DocumentType.DNI: map_dni_to_person,
    DocumentType.PASSPORT: map_passport_to_person,  # Add this
}
```

## Supported Documents

- ✅ **DNI** (Documento Nacional de Identidad) - Spanish ID
- 🔜 **NIE** (Número de Identidad de Extranjero)
- 🔜 **Passport**
- 🔜 **Driving License**

## Output Format

The extracted data follows the Ulpiano `PersonSchema` format with fields like:
- Basic info: `nombre`, `apellidos`, `dni_nif`, `fecha_nacimiento`
- Address: `direccion` (linea_direccion, municipio, provincia, pais)
- Legal data: `datos_legales` (residente_en_espana, vecindad_civil, estado_civil)
- And many more fields for comprehensive person data management

## Notes

- Fields not available in the source document will be `None` or default values
- Extraction confidence score is provided in the result
- Parent names from DNI are included in the `observaciones` field
- Vecindad civil is automatically inferred from the province
