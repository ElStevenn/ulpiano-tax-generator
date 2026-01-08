# Mapeo de Campos: Modelo de Impuestos → Base de Datos

Este documento mapea los nombres de campos del modelo de datos de impuestos con los nombres reales de campos en la base de datos. Cuando se genere un data model, **siempre usar los nombres de la base de datos si existen**, en lugar de inventar nuevos nombres.

---

## Convenciones

- **Campo en Modelo de Impuestos**: Nombre usado en el JSON del modelo de impuestos
- **Campo en BD**: Nombre real del campo en la base de datos
- **Tabla**: Nombre de la tabla en la base de datos
- **Ruta de Acceso**: Cómo acceder al campo desde la entidad principal
- **Notas**: Información adicional sobre el campo

---

## 1. CAUSANTE

### Datos Personales

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Ruta de Acceso | Notas |
|------------------------------|-------------|-------|----------------|-------|
| `dni_nif` | `dni_nif` | `persona` | `causante.miembro_familiar.persona.dni_nif` | ✅ Existe |
| `nombre_completo` | `nombre` + `apellidos` | `persona` | `causante.miembro_familiar.persona.nombre` + `causante.miembro_familiar.persona.apellidos` | ⚠️ Combinar dos campos |
| `nombre_via` | `linea_direccion` | `addresses` | `causante.miembro_familiar.address.linea_direccion` | ✅ Existe (puede contener calle completa) |
| `numero_via` | N/A | - | - | ❌ No existe - extraer de `linea_direccion` o inventar |
| `escalera` | N/A | - | - | ❌ No existe - inventar |
| `piso` | N/A | - | - | ❌ No existe - inventar |
| `puerta` | N/A | - | - | ❌ No existe - inventar |
| `codigo_postal` | `zip_code` | `addresses` | `causante.miembro_familiar.address.zip_code` | ✅ Existe |
| `municipio` | `municipio` | `addresses` | `causante.miembro_familiar.address.municipio` | ✅ Existe |
| `provincia` | `provincia` | `addresses` | `causante.miembro_familiar.address.provincia` | ✅ Existe |
| `pais` | `pais` | `addresses` | `causante.miembro_familiar.address.pais` | ✅ Existe (default: "España") |
| `obligado_impuesto_patrimonio_ultimos_cuatro_anos` | N/A | - | - | ❌ No existe - inventar |
| `es_testamentaria` | `tipo` (en escenario) | `escenario_sucesorio` | `escenario.tipo == 'testada'` | ⚠️ Derivar de escenario |
| `es_intestada` | `tipo` (en escenario) | `escenario_sucesorio` | `escenario.tipo == 'intestada'` | ⚠️ Derivar de escenario |
| `numero_personas_interesadas` | `count(atribuciones)` | `atribuciones` | `count(escenario.atribuciones)` | ⚠️ Contar atribuciones |
| `notario_o_autoridad` | N/A | - | - | ❌ No existe - inventar |
| `fecha_acta_notarial` | N/A | - | - | ❌ No existe - inventar |

### Campos Adicionales del Causante (disponibles en BD pero no en modelo)

| Campo en BD | Tabla | Ruta de Acceso | Descripción |
|-------------|-------|----------------|-------------|
| `fecha_defuncion` | `miembro_familiar` | `causante.miembro_familiar.fecha_defuncion` | Fecha de defunción |
| `nacionalidad` | `miembro_familiar` | `causante.miembro_familiar.nacionalidad` | Nacionalidad |
| `vecindad_civil` | `persona` | `causante.miembro_familiar.persona.vecindad_civil` | Vecindad civil |
| `estado_civil` | `persona` | `causante.miembro_familiar.persona.estado_civil` | Estado civil |
| `telefono` | `persona` | `causante.miembro_familiar.persona.telefono` | Teléfono |
| `email` | `persona` | `causante.miembro_familiar.persona.email` | Email |

---

## 2. BENEFICIARIO

### Datos Personales

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Ruta de Acceso | Notas |
|------------------------------|-------------|-------|----------------|-------|
| `dni_nif` | `dni_nif` | `persona` | `atribucion.party.persona.dni_nif` | ✅ Existe |
| `nombre_completo_razon_social` | `nombre` + `apellidos` | `persona` | `atribucion.party.persona.nombre` + `atribucion.party.persona.apellidos` | ⚠️ Combinar dos campos |
| `nombre_via` | `linea_direccion` | `addresses` | `atribucion.party.persona.miembro_familiar.address.linea_direccion` | ✅ Existe (si es miembro_familiar) |
| `numero_via` | N/A | - | - | ❌ No existe - extraer de `linea_direccion` o inventar |
| `escalera` | N/A | - | - | ❌ No existe - inventar |
| `piso` | N/A | - | - | ❌ No existe - inventar |
| `puerta` | N/A | - | - | ❌ No existe - inventar |
| `codigo_postal` | `zip_code` | `addresses` | `atribucion.party.persona.miembro_familiar.address.zip_code` | ✅ Existe (si es miembro_familiar) |
| `municipio` | `municipio` | `addresses` | `atribucion.party.persona.miembro_familiar.address.municipio` | ✅ Existe (si es miembro_familiar) |
| `provincia` | `provincia` | `addresses` | `atribucion.party.persona.miembro_familiar.address.provincia` | ✅ Existe (si es miembro_familiar) |
| `pais` | `pais` | `addresses` | `atribucion.party.persona.miembro_familiar.address.pais` | ✅ Existe (si es miembro_familiar) |
| `telefono` | `telefono` | `persona` | `atribucion.party.persona.telefono` | ✅ Existe |
| `correo_electronico` | `email` | `persona` | `atribucion.party.persona.email` | ✅ Existe |
| `fecha_nacimiento` | `fecha_nacimiento` | `persona` | `atribucion.party.persona.fecha_nacimiento` | ✅ Existe |
| `parentesco` | `relacion_personal` | `relacion_causante_familiar` | `atribucion.party.persona.miembro_familiar.relaciones_con_causante.relacion_personal` | ✅ Existe |
| `grupo_parentesco` | N/A | - | - | ❌ No existe - calcular según parentesco |
| `patrimonio_preexistente` | `patrimonio_valor` | `patrimonio_preexistente` | `atribucion.party.persona.patrimonio_preexistente.patrimonio_valor` | ✅ Existe |
| `tiene_discapacidad` | `porcentaje IS NOT NULL` | `info_discapacidad` | `atribucion.party.persona.info_discapacidad IS NOT NULL` | ⚠️ Derivar de existencia |
| `porcentaje_discapacidad` | `porcentaje` | `info_discapacidad` | `atribucion.party.persona.info_discapacidad.porcentaje` | ✅ Existe |
| `titulo_sucesorio` | `titulo` | `atribuciones` | `atribucion.titulo` | ✅ Existe |

### Campos Adicionales del Beneficiario (disponibles en BD pero no en modelo)

| Campo en BD | Tabla | Ruta de Acceso | Descripción |
|-------------|-------|----------------|-------------|
| `cuota_porcentaje` | `atribuciones` | `atribucion.cuota_porcentaje` | Porcentaje de cuota hereditaria |
| `cuota_tipo` | `atribuciones` | `atribucion.cuota_tipo` | Tipo de cuota (universal, parcial, etc.) |
| `relacion` | `personas_beneficiarias` | `atribucion.party.persona.relacion` | Relación (si es PersonaBeneficiaria) |
| `grado` | `info_discapacidad` | `atribucion.party.persona.info_discapacidad.grado` | Grado de discapacidad |
| `nivel_dependencia` | `info_discapacidad` | `atribucion.party.persona.info_discapacidad.nivel_dependencia` | Nivel de dependencia |
| `coeficiente_multiplicador` | `patrimonio_preexistente` | `atribucion.party.persona.patrimonio_preexistente.coeficiente_multiplicador` | Coeficiente multiplicador |

---

## 3. TRAMITANTE

### Datos Personales

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Ruta de Acceso | Notas |
|------------------------------|-------------|-------|----------------|-------|
| `dni_nif` | `dni_nif` | `persona` | `tramitante.persona.dni_nif` | ✅ Existe (donde `tramitante` es RelacionPersonaExpediente con `es_tramitante=true`) |
| `nombre_completo_firmante` | `nombre` + `apellidos` | `persona` | `tramitante.persona.nombre` + `tramitante.persona.apellidos` | ⚠️ Combinar dos campos |
| `nombre_via` | `linea_direccion` | `addresses` | `tramitante.persona.miembro_familiar.address.linea_direccion` | ✅ Existe (si es miembro_familiar) |
| `numero_via` | N/A | - | - | ❌ No existe - extraer de `linea_direccion` o inventar |
| `escalera` | N/A | - | - | ❌ No existe - inventar |
| `piso` | N/A | - | - | ❌ No existe - inventar |
| `puerta` | N/A | - | - | ❌ No existe - inventar |
| `codigo_postal` | `zip_code` | `addresses` | `tramitante.persona.miembro_familiar.address.zip_code` | ✅ Existe (si es miembro_familiar) |
| `municipio` | `municipio` | `addresses` | `tramitante.persona.miembro_familiar.address.municipio` | ✅ Existe (si es miembro_familiar) |
| `provincia` | `provincia` | `addresses` | `tramitante.persona.miembro_familiar.address.provincia` | ✅ Existe (si es miembro_familiar) |
| `pais` | `pais` | `addresses` | `tramitante.persona.miembro_familiar.address.pais` | ✅ Existe (si es miembro_familiar) |
| `telefono` | `telefono` | `persona` | `tramitante.persona.telefono` | ✅ Existe |
| `correo_electronico` | `email` | `persona` | `tramitante.persona.email` | ✅ Existe |
| `acuerdo_declaracion` | N/A | - | - | ❌ No existe - inventar (default: true) |
| `fecha_firma` | N/A | - | - | ❌ No existe - usar fecha actual (`.today()`) |

### Cómo Obtener el Tramitante

```python
# El tramitante se obtiene desde RelacionPersonaExpediente
tramitante = expediente.roles_personas.filter(
    RelacionPersonaExpediente.es_tramitante == True
).first()
```

---

## 4. DIRECCIONES (ADDRESS)

### Estructura de Address en BD

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `linea_direccion` | `linea_direccion` | `addresses` | String(255) | ✅ Contiene dirección completa (ej: "C/ Mayor 17, 2º B") |
| `municipio` | `municipio` | `addresses` | String(80) | ✅ Existe |
| `provincia` | `provincia` | `addresses` | String(80) | ✅ Existe |
| `pais` | `pais` | `addresses` | String(50) | ✅ Existe (default: "España") |
| `codigo_postal` | `zip_code` | `addresses` | String(15) | ✅ Existe |

**Nota**: Los campos `numero_via`, `escalera`, `piso`, `puerta` **NO existen** en la BD. Están almacenados en `linea_direccion` como texto completo. Si se necesitan por separado, habría que:
1. Parsear `linea_direccion` para extraerlos
2. O inventar estos campos siguiendo la topografía snake_case

---

## 5. DISCAPACIDAD (InfoDiscapacidad)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `tiene_discapacidad` | `porcentaje IS NOT NULL` | `info_discapacidad` | Boolean | ⚠️ Derivar de existencia del registro |
| `porcentaje_discapacidad` | `porcentaje` | `info_discapacidad` | Integer | ✅ Existe (0-100) |
| `grado` | `grado` | `info_discapacidad` | String(50) | ✅ Existe (disponible pero no en modelo) |
| `nivel_dependencia` | `nivel_dependencia` | `info_discapacidad` | String(50) | ✅ Existe (disponible pero no en modelo) |

**Ruta de Acceso**: `persona.info_discapacidad.porcentaje`

---

## 6. PATRIMONIO PREEXISTENTE (PatrimonioPreexistente)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `patrimonio_preexistente` | `patrimonio_valor` | `patrimonio_preexistente` | Numeric(15,2) | ✅ Existe |

**Ruta de Acceso**: `persona.patrimonio_preexistente.patrimonio_valor`

**Campo Adicional Disponible**:
- `coeficiente_multiplicador` (Numeric(3,2)) - No está en el modelo pero existe en BD

---

## 7. RELACIÓN CON CAUSANTE (RelacionCausanteFamiliar)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `parentesco` | `relacion_personal` | `relacion_causante_familiar` | String | ✅ Existe |

**Ruta de Acceso**: `persona.miembro_familiar.relaciones_con_causante.relacion_personal`

**Campos Adicionales Disponibles**:
- `desheredado` (Boolean)
- `motivo_desheredacion` (String)
- `notas_adicionales` (Text)

---

## 8. DONACIONES PREVIAS (DonacionesPreviasFamiliar)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `importe` | `importe` | `donaciones_previas_familiar` | Numeric(15,2) | ✅ Existe |
| `fecha` | `fecha` | `donaciones_previas_familiar` | DateTime | ✅ Existe |

**Ruta de Acceso**: `persona.miembro_familiar.donaciones_previas`

**Nota**: Es una colección (puede haber múltiples donaciones)

---

## 9. ATRIBUCIONES (Atribucion)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `titulo_sucesorio` | `titulo` | `atribuciones` | Enum | ✅ Existe. Valores: `heredero`, `legatario`, `donatario_por_causa_de_muerte`, `fiduciario`, `fideicomisario`, `sustituto_vulgar`, `usufructuario`, `nudo_propietario`, `conyuge_viudo_con_derecho_vidual`, `beneficiario_de_seguro_de_vida`, `prelegado` |
| `cuota_porcentaje` | `cuota_porcentaje` | `atribuciones` | Numeric(5,2) | ✅ Existe (disponible pero no en modelo) |
| `cuota_tipo` | `cuota_tipo` | `atribuciones` | Enum | ✅ Existe (disponible pero no en modelo) |
| `relacion` | **calculado dinámicamente** (familiares) o `relacion` (persona_beneficiaria) | — | Enum/String | ⚠️ Para MiembroFamiliar se deriva del árbol familiar. Valores Enum soportados: `Padre`, `Madre`, `Hijo`, `Nieto`, `Bisnieto`, `Abuelo`, `Bisabuelo`, `Hermano`, `Tío`, `Sobrino`, `Primo`, `Tío abuelo`, `Sobrino nieto`, `Primo segundo`, `Primo tercero`, `Cónyuge`, `Suegro`, `Yerno`, `Nuera`, `Cuñado`, `Pareja de hecho`, `Adoptante`, `Adoptado`, `Tutor`, `Curador`, `Sin vínculo familiar`. Para PersonaBeneficiaria se usa su campo `relacion` (string libre) |
| `grupo_parentesco` | **calculado dinámicamente** | — | Enum | ⚠️ Derivar de la relación con el causante y edad (<21) según lógica de `_calcular_grupo_parentesco_causante`. Valores: `grupo_i`, `grupo_ii`, `grupo_iii`, `grupo_iv` |
| `bienes_asignados` | `atribucion_metadata.bienes_asignados` + tabla `bienes_atribuidos` | `atribuciones` / `bienes_atribuidos` | Lista de objetos | ✅ Estructura en schema (`BienAsignadoCreate`): `bien_id`, `porcentaje_asignado`, `derecho_transmitido`, `valor_estimado`, `metadatos`, `condiciones`, `sustituciones` |
| `valor_disponible_bien_asignado` | **calculado** (`valor_estimado * porcentaje_asignado/100`) | — | Numeric | ⚠️ Solo en respuestas de bienes asignados (legatario/prelegado) |
| `bienes_residuales` (herederos) | **calculado** desde remanentes del escenario | — | Lista de objetos | ⚠️ Campos en respuesta: `bien_id`, `nombre`, `tipo_bien`, `descripcion_general`, `valor_estimado`, `valor_disponible`, `valor_heredero`, `porcentaje_disponible_total`, `porcentaje_heredero`, `tipo_titularidad`, `cuota`, `titularidad`, `derecho_real`, `titularidad_sociedad`, `cargas` |

### Bienes Atribuidos (tabla `bienes_asignados`)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `bien_atribuido_id` | `id` | `bienes_asignados` | UUID | ✅ Identificador del bien asignado a la atribución |
| `atribucion_id` | `atribucion_id` | `bienes_asignados` | UUID (FK) | ✅ Referencia a `atribuciones.id` |
| `bien_id` | `bien_id` | `bienes_asignados` | UUID (FK) | ✅ Referencia a `inventario_bienes.id` |
| `porcentaje_asignado` | `porcentaje_asignado` | `bienes_asignados` | Numeric | ✅ 0–100, opcional |
| `derecho_transmitido` | `derecho_transmitido` | `bienes_asignados` | String | ✅ Texto libre (pleno, nuda_propiedad, usufructo, etc.) |
| `valor_estimado` | `valor_estimado` | `bienes_asignados` | Numeric | ✅ Estimación opcional |
| `metadatos` | `metadatos` | `bienes_asignados` | JSONB | ✅ Metadatos del derecho transmitido |
| `condiciones` | `condiciones` | `bienes_asignados` | JSONB | ✅ Condiciones aplicables al bien asignado |
| `sustituciones` | `sustituciones` | `bienes_asignados` | JSONB | ✅ Sustituciones específicas del bien |
| `cargas_gravamenes` (respuesta) | — (se carga de `inventario_bienes.cargas` activas) | `cargas` | Lista de objetos | ⚠️ Solo en respuesta; incluye `id`, `tipo`, `importe`, `deuda_pendiente`, `interes`, `vencimiento`, `acreedor_o_titular_derecho`, `descripcion`, `asiento`, `rango`, `estado`, `fechas`, `activa` |
| `valor_disponible` (respuesta) | **calculado** | — | Numeric | ⚠️ Si hay `porcentaje_asignado`, se multiplica por `valor_estimado`; si no, usa `valor_estimado` |

---

## 10. ESCENARIO (EscenarioSucesorio)

| Campo en Modelo de Impuestos | Campo en BD | Tabla | Tipo | Notas |
|------------------------------|-------------|-------|------|-------|
| `es_testamentaria` | `tipo == 'testada'` | `escenario_sucesorio` | Enum | ⚠️ Derivar de `tipo` |
| `es_intestada` | `tipo == 'intestada'` | `escenario_sucesorio` | Enum | ⚠️ Derivar de `tipo` |

---

## 11. CAMPOS QUE NO EXISTEN EN BD (Inventar siguiendo snake_case)

Los siguientes campos **NO existen** en la base de datos y deben inventarse siguiendo la topografía snake_case:

### Causante
- `numero_via` → `numero_via`
- `escalera` → `escalera`
- `piso` → `piso`
- `puerta` → `puerta`
- `obligado_impuesto_patrimonio_ultimos_cuatro_anos` → `obligado_impuesto_patrimonio_ultimos_cuatro_anos`
- `notario_o_autoridad` → `notario_o_autoridad`
- `fecha_acta_notarial` → `fecha_acta_notarial`

### Beneficiario
- `numero_via` → `numero_via`
- `escalera` → `escalera`
- `piso` → `piso`
- `puerta` → `puerta`
- `grupo_parentesco` → `grupo_parentesco` (calcular según parentesco)

### Tramitante
- `numero_via` → `numero_via`
- `escalera` → `escalera`
- `piso` → `piso`
- `puerta` → `puerta`
- `acuerdo_declaracion` → `acuerdo_declaracion`
- `fecha_firma` → `fecha_firma` (usar fecha actual)

### Pago
- Todos los campos de pago → Inventar siguiendo snake_case

### Liquidación
- Todos los campos de liquidación → Inventar siguiendo snake_case

### Reducciones
- Todos los campos de reducciones → Inventar siguiendo snake_case

---

## Reglas de Mapeo

### ✅ SIEMPRE usar nombres de BD cuando existan

```json
{
  "dni_nif": "persona.dni_nif",  // ✅ Usar dni_nif (existe en BD)
  "codigo_postal": "addresses.zip_code",  // ⚠️ Mapear a zip_code (existe en BD)
  "patrimonio_preexistente": "patrimonio_preexistente.patrimonio_valor"  // ✅ Usar patrimonio_valor
}
```

### ⚠️ Combinar campos cuando sea necesario

```json
{
  "nombre_completo": {
    "source": ["persona.nombre", "persona.apellidos"],
    "combine": "concat"
  }
}
```

### ❌ Inventar campos siguiendo snake_case cuando NO existan

```json
{
  "numero_via": "numero_via",  // ❌ No existe - inventar
  "escalera": "escalera",  // ❌ No existe - inventar
  "acuerdo_declaracion": "acuerdo_declaracion"  // ❌ No existe - inventar
}
```

### 🔄 Derivar valores cuando sea necesario

```json
{
  "es_testamentaria": {
    "source": "escenario_sucesorio.tipo",
    "derive": "tipo == 'testada'"
  },
  "tiene_discapacidad": {
    "source": "info_discapacidad.porcentaje",
    "derive": "porcentaje IS NOT NULL"
  }
}
```

---

## Ejemplo de Mapeo Completo

```json
{
  "causante": {
    "dni_nif": "miembro_familiar.persona.dni_nif",  // ✅ Existe
    "nombre_completo": ["miembro_familiar.persona.nombre", "miembro_familiar.persona.apellidos"],  // ⚠️ Combinar
    "codigo_postal": "miembro_familiar.address.zip_code",  // ✅ Existe
    "numero_via": "numero_via",  // ❌ Inventar
    "escalera": "escalera"  // ❌ Inventar
  },
  "beneficiario": {
    "dni_nif": "atribucion.party.persona.dni_nif",  // ✅ Existe
    "patrimonio_preexistente": "atribucion.party.persona.patrimonio_preexistente.patrimonio_valor",  // ✅ Existe
    "porcentaje_discapacidad": "atribucion.party.persona.info_discapacidad.porcentaje",  // ✅ Existe
    "parentesco": "atribucion.party.persona.miembro_familiar.relaciones_con_causante.relacion_personal"  // ✅ Existe
  }
}
```

---

## Tablas Principales Referenciadas

| Tabla | Descripción | Uso Principal |
|-------|-------------|---------------|
| `persona` | Datos personales básicos | Causante, Beneficiario, Tramitante |
| `miembro_familiar` | Extensión de Persona para familiares | Causante, Beneficiario |
| `addresses` | Direcciones | Causante, Beneficiario, Tramitante |
| `atribuciones` | Atribuciones hereditarias | Beneficiario |
| `party` | Entidad genérica (Persona o Sociedad) | Beneficiario |
| `relacion_persona_expediente` | Roles en expediente | Tramitante |
| `relacion_causante_familiar` | Relación con causante | Beneficiario |
| `patrimonio_preexistente` | Patrimonio preexistente | Beneficiario |
| `info_discapacidad` | Información de discapacidad | Beneficiario |
| `donaciones_previas_familiar` | Donaciones previas | Beneficiario |
| `escenario_sucesorio` | Escenario de sucesión | Contexto general |

---

**Versión**: 1.0  
**Última Actualización**: 2024  
**Modelo de Base de Datos**: `models.py` (líneas 1-2488)

