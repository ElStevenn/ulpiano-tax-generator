Cambios introducidos en generate_mod650cat_pdf.py

Esta versión del script incorpora toda la lógica necesaria para gestionar correctamente la sección de reducciones del Modelo 650 de Cataluña, cumpliendo exactamente las especificaciones pedidas por el cliente.

Cambios principales incluidos en la V2:
Traducción a español.
Adaptación del formato de reducciones.
El script ahora admite tanto el formato antiguo (un diccionario con campos como reduccionParentesco) como el nuevo formato exigido por el cliente (lista de objetos con claves casillaReal, casillaTeorica, clave, etiqueta, importeReal, importeTeorico).
Cuando recibe el formato antiguo, lo convierte internamente al nuevo formato.

Validación completa de la sección de reducciones
Se comprueba que cada reducción tenga todos los campos requeridos y que los valores monetarios sean numéricos y convertibles a Decimal.
Si existen totalesReducciones en el JSON, el script compara los totales declarados con las sumas reales de los importes. Si no coinciden, lanza error con detalle.

Cálculo automático de totalesReducciones
Aunque vengan definidos en el JSON, el script recalcula siempre los totales reales y teóricos para garantizar coherencia.

Recalculo de la base liquidable (casillas 13 y 14)
A partir de la base previa (antes de reducciones), el script aplica:

baseNueva = basePrevia - totalReducciones


Esto actualiza automáticamente:

Caja 13 (real)

Caja 14 (teórica)

Recalculo proporcional de casillas dependientes (605, 606, 607 y 16)
Cuando existe una base previa real distinta de cero, el script aplica un factor de ajuste proporcional sobre las casillas dependientes:

liquidacionCuotaTributariaCaja605

liquidacionReduccionExcesoCuotaCaja606

liquidacionCuotaTributariaAjustadaCaja607

liquidacionCuotaIntegraCaja16

Este factor garantiza coherencia matemática entre bases y cuotas después de aplicar reducciones.

Integración completa con el flujo original del script
No se ha modificado nada del proceso de dibujo PDF ni de FIELD_MAPPINGS.
La lógica nueva se ejecuta antes del aplanado (flatten_data) para que todo el PDF ya reciba los valores correctos.

Compatibilidad con todos los JSON de ejemplo del cliente
La V2 ha sido comprobada contra los cinco JSON proporcionados por el cliente:

sin reducciones

solo reducciones reales

solo reducciones teóricas

mixto

complejo

Todos pasan validación y recalculo de forma consistente.