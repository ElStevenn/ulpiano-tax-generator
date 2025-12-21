README.txt — MOD620CAT (Cataluña) | Añadidos/Actualizados

Este repositorio incluye soporte para generar el PDF del modelo MOD620CAT (Cataluña)
mediante una superposición (overlay) de datos JSON sobre la plantilla oficial.

Además, el mapeo de campos (coordenadas y configuración de renderizado) ha sido
revisado y ajustado cuidadosamente para asegurar que los valores se colocan en las
casillas correctas de forma precisa. Esta calibración del mapeo forma parte del
trabajo realizado en esta actualización.

------------------------------------------------------------
1) Archivos añadidos / actualizados
------------------------------------------------------------

1. Script generador
   - src/scripts_generate_models/generate_mod620cat.py
   Descripción:
   Genera un PDF rellenado creando una capa transparente (overlay) con los valores
   del JSON y fusionándola con la plantilla oficial.

2. Estructura de datos (validación del JSON)
   - tax_models/mod620cat/data_models/mod620cat_data_structure.json
   Descripción:
   Define el esquema/estructura esperada del JSON de entrada (campos, tipos, etc.)
   para validar el payload antes de generar el PDF.

3. Mapeo de campos a coordenadas (posicionamiento en el PDF)
   - tax_models/mod620cat/data_models/mod620cat_field_mappings.json
   Descripción:
   Contiene las coordenadas (x, y) y configuración de cada campo para dibujarlo
   sobre la plantilla PDF (qué valor va en qué casilla).
   Estado:
   - Mapeo verificado y calibrado: los campos quedan correctamente alineados y
     posicionados sobre la plantilla.

4. Ejemplo de datos
   - tax_models/mod620cat/json_examples/mod620cat_example.json
   Descripción:
   Ejemplo funcional de payload JSON para probar la generación del PDF.

5. Plantilla PDF (requerida)
   - tax_models/mod620cat/mod620cat.pdf
   Descripción:
   Plantilla oficial/base sobre la que se superpone el overlay.
   (Debe existir en esta ruta o ajustarse el parámetro --template).

------------------------------------------------------------
2) Instalación
------------------------------------------------------------

Recomendado: usar un entorno virtual (venv).

1) Instalar dependencias
   python -m pip install -r requirements.txt

------------------------------------------------------------
3) Uso (generación del PDF)
------------------------------------------------------------

Desde la raíz del repositorio:

python src/scripts_generate_models/generate_mod620cat.py \
  --data tax_models/mod620cat/json_examples/mod620cat_example.json \
  --structure tax_models/mod620cat/data_models/mod620cat_data_structure.json \
  --mapping tax_models/mod620cat/data_models/mod620cat_field_mappings.json \
  --template tax_models/mod620cat/mod620cat.pdf \
  --output generated/mod620cat_output.pdf

Salida esperada:
- generated/mod620cat_output.pdf

------------------------------------------------------------
4) Notas importantes
------------------------------------------------------------

- Si el PDF sale desalineado, se corrige ajustando coordenadas en:
  tax_models/mod620cat/data_models/mod620cat_field_mappings.json

- Si faltan campos o el JSON cambia, se actualiza:
  tax_models/mod620cat/data_models/mod620cat_data_structure.json
  y/o el ejemplo:
  tax_models/mod620cat/json_examples/mod620cat_example.json

- Recomendación: no commitear PDFs generados.
  El directorio "generated/" debería estar ignorado por git en .gitignore.

------------------------------------------------------------
5) Checklist rápido de verificación
------------------------------------------------------------

- Existe la plantilla:
  tax_models/mod620cat/mod620cat.pdf

- El ejemplo valida y el script genera el output:
  generated/mod620cat_output.pdf

- El mapeo queda correctamente posicionado (casillas correctas):
  tax_models/mod620cat/data_models/mod620cat_field_mappings.json
