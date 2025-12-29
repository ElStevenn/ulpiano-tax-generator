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

------------------------------------------------------------
6) Campos faltantes para mapear - Relacion de bienes
------------------------------------------------------------

PENDIENTE DE MAPEO: Los siguientes campos de la seccion "Relacion de bienes"
no estan actualmente mapeados en mod651cat_field_mappings.json y deben ser
agregados:

1. Usufructo/Uso/Habitacion:
   - tipo_usufructo_uso_habitacion (string, opcional)
     Tipo de usufructo, uso o habitacion
   - nif_usufructuario (string, opcional)
     NIF de la persona usufructuaria, usuaria o habitacionista
     Validacion: formato NIF/NIE espanol
   - fecha_nacimiento_usufructuario (string, opcional)
     Fecha de nacimiento del usufructuario
     Formato: YYYY-MM-DD

2. Checkboxes de estado del bien:
   - es_gananciales (boolean, opcional)
     Bien de gananciales (checkbox "Si")
   - tiene_cargas (boolean, opcional)
     Bien con cargas (checkbox "Si")
   - tiene_deudas (boolean, opcional)
     Bien con deudas (checkbox "Si")

3. Clave de beneficio fiscal:
   - clave_beneficio_fiscal (string, opcional)
     Codigo/clave del beneficio fiscal (ej: "BH01", "BH02")

4. Campos adicionales de direccion:
   - poligono (string, opcional)
     Poligono (campo dentro de "Numero/Km/Poligono")
   - parcela (string, opcional)
     Parcela (campo dentro de "Escalera, piso, puerta / Parcela")

5. Secciones especificas:
   Los bienes deben organizarse en tres arrays segun ubicacion:
   - bienes_cataluna (array, opcional)
     Bienes inmuebles situados en Cataluna
   - bienes_otras_comunidades (array, opcional)
     Bienes inmuebles situados en otras comunidades autonomas
   - bienes_fuera_espana (array, opcional)
     Bienes inmuebles situados fuera de Espana
     Nota: Ya existe campo form.inmobles_fora en paginas 12-13

Estructura propuesta para el JSON:

{
  "bienes": {
    "bienes_cataluna": [
      {
        "numero": 1,
        "tipo_bien": "Inmueble urbano",
        "descripcion": "Piso en Barcelona",
        "finca_registral": "12345",
        "subfinca_registral": "A",
        "referencia_catastral": "1234567890123456789A",
        "nombre_via": "Calle Gran Via",
        "numero_via": "123",
        "poligono": null,
        "escalera": "A",
        "piso": "3",
        "puerta": "2",
        "parcela": null,
        "codigo_postal": "08013",
        "municipio": "Barcelona",
        "provincia": "Barcelona",
        "pais": "Espana",
        "superficie_metros": 85.5,
        "superficie_hectareas": null,
        "tipo_derecho": "Propiedad",
        "tipo_usufructo_uso_habitacion": null,
        "nif_usufructuario": null,
        "fecha_nacimiento_usufructuario": null,
        "duracion_derecho": "Vitalicio",
        "valor_referencia": 250000.0,
        "valor_neto_total_declarado": 250000.0,
        "porcentaje_valor_derecho": 100,
        "porcentaje_adquisicion": 100,
        "valor_neto_donacion": 250000.0,
        "es_gananciales": false,
        "tiene_cargas": false,
        "tiene_deudas": false,
        "clave_beneficio_fiscal": "BH01",
        "descripcion_beneficio_fiscal": "Bonificacion por vivienda habitual"
      }
    ],
    "bienes_otras_comunidades": [],
    "bienes_fuera_espana": []
  }
}

Notas para el desarrollador:
- Los campos ya mapeados estan en mod651cat_field_mappings.json con patrones
  como form.*_bens_X donde X es el numero de bien (1-14).
- Los nuevos campos deben seguir el mismo patron de mapeo.
- Los checkboxes deben mapearse con field_type: "checkbox" y true_label: "X".
- Las paginas donde aparecen los bienes son:
  * 4-5: Bienes en Cataluna
  * 6-7: Bienes en otras comunidades autonomas
  * 8-9: Bienes fuera de Espana
  * 12-13: Totales y resumen
- El campo form.inmobles_fora ya existe en paginas 12-13 para bienes fuera
  de Espana.
