# Núcleo científico del hackathon

Trabajar desde `.worktrees/NASA_hackathon`, rama `NASA_hackathon`. No requiere
claves, modelos, servidor ni frontend.

```bash
uv sync
uv run python scripts/search_science.py build
uv run python scripts/search_science.py verify
uv run python scripts/search_science.py ask "Saffire I airflow 20 cm/s" --limit 4
uv run python scripts/search_science.py ask "Compare Saffire I S1 and S2"
uv run python scripts/measure_hackathon.py --output /tmp/nasa-measurements.json
```

Los originales acotados y recibos se conservan en esta rama. Para verificar o
repetir su adquisición: `uv run python scripts/acquire_hackathon.py`. Descarga sólo
nueve tablas PSI, el estándar público y una selección de tablas/metadatos del
commit fijado del equipo. Rechaza contenido diferente en un archivo existente.
No ejecuta los descargadores masivos ni altera `data/raw/manifest.json`.

Interfaz interna: `ScientificSearchService(snapshot).search(question)` devuelve
`SearchResult`, serializable mediante `model_dump(mode="json")`. También admite
un `QueryIntentV2` explícito en `intent=`. Cerrar con `service.close()`.

Reutiliza SemanticRegistry, SemanticGraph, QueryIntentV2, execute_native,
EvidenceRegistry, FTS5/BM25, register_cells/round_trip y navigate. La opción
`schema_hierarchical` selecciona jerarquías aprobadas por llamada sin cambiar
flags globales. Hay navegación real entre investigación, corrida, descripción de
muestra y condiciones; las condiciones tipadas reutilizan FlowCondition,
AtmosphereCondition y PressureCondition. Una asociación no prueba equivalencia.
No existe una taxonomía revisada de materiales en la base; no se inventó una.

DIRECT indica coincidencia con todas las restricciones explícitas acreditadas.
El tipo, modalidad y evidencia del registro permanecen visibles: una condición
configurada no se convierte en observación. RELATED conserva la relación positiva,
matriz MATCH/DIFFER/UNKNOWN/NOT_COMPARABLE/CONFLICT, razones, diferencias y límites.
DOCUMENTARY mantiene documentos y normas; DISCOVERY conserva resultados textuales
y fichas de catálogo. Se ordenan las categorías por separado. El puntaje mide
pertinencia, nunca riesgo ni certificación de seguridad.

La interpretación es conservadora: palabras científicas sin resolución permanecen
en `unresolved_mentions` y bloquean DIRECT. Puede recuperar texto sin interpretar
un fenómeno nuevo; no ofrece comprensión científica irrestricta. Las expresiones
aproximadas no reciben tolerancias inventadas. No hay inferencia de gravedad ni
condiciones entre filas. FLEX-2 conserva alcance de campaña. Las notas y filas de
cámaras se conservan como texto, no como corridas. El oxígeno Saffire-II referido
a su nota de columna mantiene modalidad derivada.

El snapshot tiene hashes de originales, esquema, adaptador y normalizadores;
SQLite es de sólo lectura durante consulta. Un snapshot existente distinto se
rechaza: usar otro directorio con `--snapshot`. El manifiesto cuenta registros,
valores y documentos por separado. Las descripciones locales de muestra no
acreditan un recuento de especímenes físicos distintos. Los flags QC desconocidos
quedan explícitos; la limpieza del equipo se preserva y no se convierte en una
segunda autoridad experimental.

Los recibos históricos v1 están en `artifacts/hackathon/`. La validación actual
está en `artifacts/hackathon_v2/report.md` y sus recibos JSON. La base histórica
restaurada permite ejecutar las 28 pruebas de contexto; no existe ese bloqueo.

Corrección de corpus v2: construir en un directorio nuevo con
`--snapshot data/snapshots/hackathon-20261105-v9`; no migrar ni sobrescribir v1.
Los campos originales de duración y diámetro visible de extinción se conservan
como `Measurement`/`hasMeasurement`; el diámetro inicial permanece como
característica inicial. Las unidades originales, contexto y encabezado quedan en
los calificadores. Estas mediciones reportadas no establecen propagación ni
conclusiones de seguridad. La aserción antigua que exigía cero Measurement se
reemplazó por comprobaciones de esos roles contra las celdas originales.

Las rutas almacenadas en SQLite v2 son relativas. `EvidenceRegistry(...,
evidence_root=raiz)` resuelve las evidencias sin cambiar los bytes del snapshot.
`verify_snapshot(snapshot, raiz)` comprueba los hashes de entradas y artefactos.
Una copia de las fuentes autorizadas y contratos permite reconstruir desde otra
raíz; no se necesitan cambios manuales de rutas. Los identificadores documentales
con guiones no se interpretan como magnitudes físicas. Una coincidencia de campaña
sin respaldo para un fenómeno no resuelto se conserva como DISCOVERY.

La base histórica restaurada está disponible: las 28 pruebas de contexto fueron
reejecutadas correctamente; la ausencia descrita en el reporte v1 es histórica.


Consulta integrada de fases 3/4 (sin HTTP ni frontend):

```bash
uv run python scripts/search_science.py build
uv run python scripts/search_science.py verify
uv run python scripts/search_science.py ask "Saffire I measurements" --nemotron
uv run python scripts/search_science.py ask "Compare Saffire I S1 and S2" --nemotron
uv run python scripts/search_science.py ask "FLEX extinction" --research --offset 12
uv run python scripts/search_science.py scenario scenario.json --nemotron --research
uv run python scripts/measure_hackathon.py --cases evals/hackathon_search_cases_v2.json --assist-offline --output /tmp/nasa-evaluation.json
```

Configurar localmente `NVIDIA_API_KEY`, `NVIDIA_BASE_URL` y
`NVIDIA_PHASE3_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b`. El selector de consulta
es independiente de `NVIDIA_EXTRACTION_MODEL`. `--nemotron` solicita interpretación
y síntesis; sin clave informa UNAVAILABLE y mantiene recuperación y verificación
locales. DEGRADED identifica fallos o rechazo de la interpretación/síntesis; no se
oculta la recuperación determinista. Cada llamada tiene 40 s de timeout, cero
reintentos SDK y límites de salida de 1.000/1.200 tokens. No hay streaming, visión,
caché de respuestas ni proveedor alternativo en este flujo. La síntesis es
extractiva: la organización usa Nemotron; las paráfrasis libres se rechazan si no
son afirmaciones exactas suministradas. No se anuncia validación de entailment libre.

`ScientificSearchService(..., interpreter=..., selector=...).search(...,
assist=True, research=True)` usa los servicios existentes de investigación,
síntesis y verificación. La investigación adicional tiene dos rondas, dos acciones,
ocho candidatos por acción y presupuesto temporal de cinco segundos; no realiza
llamadas LLM adicionales. El presupuesto se comprueba entre acciones; una operación
local iniciada puede excederlo. No publica relaciones ni promueve categorías sin
pasar otra vez por el clasificador. `provider.calls`, `metrics`, `verification` e
`investigation` contienen recibos por etapa. El timeout del SDK no equivale a una
cota dura del tiempo total de la consulta.

La comparación nativa conserva los campos heredados y añade `matrix` y
`limitations`. Cada fila separa contexto inicial/final/reportado y devuelve
MATCH, DIFFER, UNKNOWN, NOT_COMPARABLE o CONFLICT con originales, normalización,
calificadores y evidencia específica. MATCH describe sólo esa dimensión. La matriz
incluye dimensiones solicitadas o propiedades registradas y relaciones materiales,
fenómeno y gravedad; su disponibilidad depende del corpus. Ausencia de mediciones,
instrumentos, geometría, conclusiones o gravedad no se completa mediante inferencia.
Una explicación comparativa lleva tipo `comparison_result`: es cálculo del motor,
no una observación NASA; el verificador recalcula la matriz antes de aceptarla.

Contrato interno de escenario, serializable mediante Pydantic:

```json
{
  "schema_version": "scientific-scenario-v1",
  "scenario_id": "habitat-study",
  "question": "PMMA oxygen 22.2 %",
  "provenance": "team_simulator",
  "entity_constraints": [{"relation": "hasGravityCondition", "entity_id": "lunar"}],
  "property_constraints": [],
  "unresolved_conditions": [],
  "simulator_results": [{"label": "team prediction", "value": 1}]
}
```

`analyze_scenario` devuelve condiciones proporcionadas y no especificadas,
DIRECT/RELATED/DISCOVERY/DOCUMENTARY, variables comparables, diferencias,
mediciones reportadas acreditadas, incertidumbres, límites de extrapolación,
fuentes y objetivos adicionales del asistente. La gravedad lunar desconocida queda
explícita y bloquea DIRECT. `simulator_results` se conserva sólo dentro del escenario:
no se incorpora al grafo NASA. No se calcula riesgo de incendio. Los campos son
contratos internos; autenticación, transporte, paginación HTTP y frontend siguen
fuera de este encargo.


Regresión completa por lotes sin solapamiento y con credenciales desactivadas:
`uv run python scripts/test_batches.py --output /tmp/nasa-tests-new-run`.
El directorio de salida debe ser nuevo. Los temporales se crean bajo `/dev/shm`,
se comprueba espacio entre lotes y sólo se retiran los temporales de cada lote.
Los fallos y omisiones permanecen en los recibos; no se suman reejecuciones como
pruebas nuevas. El resumen final v2 documenta las dos regresiones corregidas.


La evolución conversacional y HTTP se documenta en [PHASE56_CHAT_API.md](PHASE56_CHAT_API.md). El contrato extractivo descrito arriba corresponde a la etapa anterior; la evaluación de la evolución y sus límites están en [PHASE56_REPORT.md](PHASE56_REPORT.md).


## Scientific-engine release checkpoint

The current acceptance decision is **NOT YET ACCEPTED**. See the English
[release report](SCIENTIFIC_ENGINE_RELEASE.md) and
[dashboard API handoff](SCIENTIFIC_ENGINE_DASHBOARD_HANDOFF.md). The existing
backend API operates, but this is not evidence of sufficient scientific answer
coverage or conversational quality. No dashboard or external repository changed.
