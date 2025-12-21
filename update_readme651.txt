README.txt - MOD651CAT (Cataluna) | Anadidos/Actualizados

Este repositorio incluye soporte para generar el PDF del modelo MOD651CAT (Cataluna)
mediante una superposicion (overlay) de datos JSON sobre la plantilla oficial.

Ademas, el mapeo de campos (coordenadas y configuracion de renderizado) ha sido
revisado y ajustado cuidadosamente para asegurar que los valores se colocan en las
casillas correctas de forma precisa. Esta calibracion del mapeo forma parte del
trabajo realizado en esta actualizacion.

------------------------------------------------------------
1) Archivos anadidos / actualizados
------------------------------------------------------------

1. Script generador
   - src/scripts_generate_models/generate_mod651cat.py
   Descripcion:
   Genera un PDF rellenado creando una capa transparente (overlay) con los valores
   del JSON y fusionandola con la plantilla oficial.

2. Estructura de datos (validacion del JSON)
   - tax_models/mod651cat/data_models/mod651cat_data_structure.json
   Descripcion:
   Define el esquema/estructura esperada del JSON de entrada (campos, tipos, etc.)
   para validar el payload antes de generar el PDF.

3. Mapeo de campos a coordenadas (posicionamiento en el PDF)
   - tax_models/mod651cat/data_models/mod651cat_field_mappings.json
   Descripcion:
   Contiene las coordenadas (x, y) y configuracion de cada campo para dibujarlo
   sobre la plantilla PDF (que valor va en que casilla).
   Estado:
   - Mapeo verificado y calibrado: los campos quedan correctamente alineados y
     posicionados sobre la plantilla.

4. Ejemplo de datos
   - tax_models/mod651cat/json_examples/mod651cat_example.json
   Descripcion:
   Ejemplo funcional de payload JSON para probar la generacion del PDF.

5. Plantilla PDF (requerida)
   - tax_models/mod651cat/mod651cat.pdf
   Descripcion:
   Plantilla oficial/base sobre la que se superpone el overlay.
   (Debe existir en esta ruta o ajustarse el parametro --template).

------------------------------------------------------------
2) Instalacion
------------------------------------------------------------

Recomendado: usar un entorno virtual (venv).

1) Instalar dependencias
   python -m pip install -r requirements.txt

------------------------------------------------------------
3) Uso (generacion del PDF)
------------------------------------------------------------

Desde la raiz del repositorio:

python src/scripts_generate_models/generate_mod651cat.py \
  --data tax_models/mod651cat/json_examples/mod651cat_example.json \
  --structure tax_models/mod651cat/data_models/mod651cat_data_structure.json \
  --mapping tax_models/mod651cat/data_models/mod651cat_field_mappings.json \
  --template tax_models/mod651cat/mod651cat.pdf \
  --output generated/mod651cat_output.pdf

Salida esperada:
- generated/mod651cat_output.pdf

------------------------------------------------------------
4) Notas importantes
------------------------------------------------------------

- Si el PDF sale desalineado, se corrige ajustando coordenadas en:
  tax_models/mod651cat/data_models/mod651cat_field_mappings.json

- Si faltan campos o el JSON cambia, se actualiza:
  tax_models/mod651cat/data_models/mod651cat_data_structure.json
  y/o el ejemplo:
  tax_models/mod651cat/json_examples/mod651cat_example.json

- Recomendacion: no commitear PDFs generados.
  El directorio "generated/" deberia estar ignorado por git en .gitignore.

------------------------------------------------------------
5) Checklist rapido de verificacion
------------------------------------------------------------

- Existe la plantilla:
  tax_models/mod651cat/mod651cat.pdf

- El ejemplo valida y el script genera el output:
  generated/mod651cat_output.pdf

- El mapeo queda correctamente posicionado (casillas correctas):
  tax_models/mod651cat/data_models/mod651cat_field_mappings.json
