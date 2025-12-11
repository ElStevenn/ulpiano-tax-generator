INDEX
 1. Crear data model en base a un prompt
 2. Crear los example JSONs
 3. Crear el script

=======================

1. Crear data model en base a un prompt

Proporciona a la IA el siguiente prompt junto con el PDF del formulario oficial (asegurate de pasarle correctamente las variables):


---------------------------------------------
"Genera un data model JSON completo para el modelo de impuesto [NOMBRE_MODELO] basándote en el formulario oficial PDF y los campos de la base de datos.

REFERENCIAS OBLIGATORIAS:
- database_fields.md: Este archivo contiene el mapeo completo de todos los campos que existen en la base de datos. Documenta qué campos hay, en qué tablas están, y cómo acceder a ellos. SIEMPRE consulta este archivo antes de inventar nombres de campos porque muchos campos ya existen en BD con nombres específicos (ej: zip_code en lugar de codigo_postal, email en lugar de correo_electronico, patrimonio_valor en lugar de patrimonio_preexistente).
- tax_models/mod650cat/data_models/mod650cat_data_structure.json: Usa este archivo como referencia del formato y estructura JSON a seguir.

PROCESO:

1. Lee el PDF del formulario oficial del modelo [NOMBRE_MODELO] e identifica todas las secciones y campos que aparecen.

2. Para cada campo del formulario, consulta database_fields.md para verificar si existe en la base de datos:
   - Si existe en BD: usa el nombre exacto del campo de BD (ej: zip_code, email, dni_nif, patrimonio_valor)
   - Si no existe en BD: inventa el nombre siguiendo snake_case (ej: numero_via, escalera, acuerdo_declaracion)
   - Si requiere combinar campos: documenta en description cómo combinar (ej: nombre + apellidos de tabla persona)
   - Si requiere derivar valores: documenta en description cómo derivar (ej: es_testamentaria desde escenario_sucesorio.tipo == 'testada')

3. Organiza los campos en secciones según el formulario:
   - causante: consulta database_fields.md sección "1. CAUSANTE" para campos disponibles
   - beneficiario: consulta database_fields.md sección "2. BENEFICIARIO" para campos disponibles
   - tramitante: consulta database_fields.md sección "3. TRAMITANTE" para campos disponibles
   - pago: inventar campos siguiendo snake_case (no existen en BD excepto importe que puede venir de AtribucionReduccion.total_a_pagar)
   - liquidacion: inventar campos siguiendo snake_case (no existen en BD excepto algunos que pueden venir de AtribucionReduccion)
   - reducciones: array con estructura estándar (casillaReal, casillaTeorica, clave, etiqueta, importeReal, importeTeorico)
   - totalesReducciones: algunos pueden venir de AtribucionReduccion.total_reduccion

4. Nombres de campos:
   - NO usar prefijos de sección en los IDs (NO causanteNif, usar dni_nif)
   - El contexto viene de la sección padre (causante.dni_nif, beneficiario.dni_nif, tramitante.dni_nif)
   - Usar snake_case para todos los nombres
   - Los nombres deben coincidir exactamente con los campos de BD cuando existan

5. Agregar validaciones cuando corresponda: validationRegex para DNI/código postal/fechas, format para fechas ("YYYY-MM-DD") y números ("decimal", "integer"), boxNumber cuando corresponda al formulario, calculation cuando sea calculado, dependsOn cuando dependa de otro campo.

6. Incluir ejemplo JSON completo en la sección "example" usando los nombres correctos (sin prefijos).

7. Actualizar lastUpdated con fecha actual y documentar en notes.idNaming que los IDs no incluyen prefijos de sección."

Comprueba manualmente que los datos generados sean correctos comparándolos con el formulario PDF.

---------------------------------------------


=======================

2. Crear los example JSONs

Proporciona a la IA el data model creado y pide que genere varios JSONs de ejemplo con datos realistas. Estos JSONs servirán para probar el script de generación.

Puedes pedirle que cree diferentes escenarios: casos simples, casos complejos, casos con reducciones, casos sin reducciones, etc.

=======================

3. Crear el script

Usa los scripts existentes en src/scripts_generate_models/ como referencia (generate_mod650cat.py). El script debe:
- Leer el data model desde tax_models/[MODELO]/data_models/[MODELO]_data_structure.json
- Cargar los JSONs de datos de ejemplo (manualmente poner el que quieres el json que te generee)
- Generar el PDF rellenado usando PyPDF2 y reportlab
- Seguir la misma estructura y patrones que generate_mod650cat.py

