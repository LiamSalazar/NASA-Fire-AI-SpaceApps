# Entrega de fases 5 y 6: implementación, evaluación y límites

Se implementó el servicio conversacional y HTTP en el worktree `NASA_hackathon`.
La fase 6 incluye evaluación real, adversarios y estabilización. **La aceptación
científica y conversacional general permanece abierta**: las pruebas nuevas
mostraron respuestas incompletas y errores semánticos/contextuales que no se
pueden ocultar detrás de HTTP 200 o de un score NLI. No se declara certificación
científica ni capacidad de inferir resultados nuevos.

## 1. Componentes reutilizados

ScientificSearchService, QueryIntentV2, ejecución nativa RDF, navegación de
relaciones aprobadas, investigación acotada, EvidenceRegistry, snapshots con
hashes, matrices de comparación, ScenarioInput/analyze_scenario, selección de
afirmaciones y verificación de procedencia. No se creó otro buscador, grafo,
base vectorial ni RAG. No se modificaron fuentes bajo `data/raw/`.

## 2. Cambio de síntesis

Nemotron recibe la pregunta, historial pertinente, foco documental, información
experimental y documental, pasajes originales, condiciones, diferencias,
comparación, candidatos y límites. Produce párrafos libres con identificadores
de respaldo. El servidor asigna las citas después de verificar. No se exige
copiar frases, seleccionar cuatro afirmaciones ni usar secciones fijas.

El selector NVIDIA heredado admite reformulaciones con un verificador
independiente configurado. La ruta local extractiva se conserva por compatibilidad
y consulta sin proveedor; no se presenta como una explicación de Nemotron.
La ruta HTTP usa el inventario completo disponible dentro del presupuesto de
contexto, evitando el antiguo máximo de ocho afirmaciones seleccionadas.

## 3. Verificación de paráfrasis

Los controles existentes comprueban sujetos, referencias, valores, unidades,
condiciones, modalidades, procedencia y comparación recalculada. El generador no
puede asignar autoridad ni promover una categoría. Los pasajes deben resolver en
el registro y coincidir con las fuentes suministradas.

Se añadió NLI multilingüe local, independiente de Nemotron, y controles de
números/unidades, negaciones introducidas, posibilidades y objetivos frente a
resultados. El NLI no se considera suficiente por sí solo. La revisión directa
reveló que podía aceptar «radiactiva» como paráfrasis de «radiative». Para español
se añadió traducción inversa independiente, sin mostrarle la fuente al traductor,
y contraste de identidad de términos parecidos derivados del texto original.
Esto no añade aliases a la ontología ni convierte la traducción en evidencia.

Una formulación rechazada puede reformularse una vez; otras partes válidas se
conservan. Los localizadores documentales propuestos pueden reexaminarse contra
oraciones completas de la misma página ya recuperada, con los mismos controles.
No se busca en otro estudio un valor que permita justificar la frase. Hay un
presupuesto explícito de 96 comprobaciones adicionales por turno.

El NLI también rechazó paráfrasis fieles. Se conserva ese resultado como límite
de utilidad; no se bajó el umbral para hacer pasar las preguntas. La identidad
completa de una proposición puede comprobarse determinísticamente, sin inventar
un score del modelo. La revisión de relevancia de Nemotron selecciona texto ya
comprobado, pero no acredita su corrección científica.

## 4. DIRECT, RELATED, DOCUMENTARY y DISCOVERY

DIRECT conserva las restricciones y la procedencia experimental. RELATED
incluye matrices de coincidencias, diferencias, incógnitas y límites; comparar
campos no establece equivalencia experimental. Las consultas ampliadas no
relajan la elegibilidad DIRECT de la pregunta original.

DOCUMENTARY permite explicar métodos, requisitos y conclusiones atribuidas sin
convertirlos en mediciones. DISCOVERY separa una fuente recuperada todavía no
acreditada (`retrieved_unaccredited_source`) de una idea de búsqueda generada
(`unverified_search_idea`). No se publicaron relaciones ni vocabulario nuevos.
Las sugerencias se presentan como búsquedas pendientes, no como estudios que
confirmen una conexión ni recomendaciones NASA.

## 5. Chat y contexto

Sesiones en memoria con UUID, 12 mensajes pertinentes, ventana de 24.000
caracteres, expiración de una hora y máximo de 200 sesiones. Cada turno vuelve a
recuperar evidencia. El historial resuelve referentes; no prueba condiciones.

Una prueba nueva encontró una definición óptica de «extinction coefficient» en
un seguimiento de combustión de gotas. La frase tenía fuente, pero la relación
con la pregunta era incorrecta. Se añadió foco documental persistente a partir
de las fuentes realmente citadas. Un seguimiento consulta de nuevo esas fuentes,
aun tras un turno degradado, y después puede ampliar la búsqueda. No hay una
regla especial para «extinción», FLEX ni otra investigación.

La regresión posterior conservó el foco en `ntrs-20150023456`; sus trazas contienen
el alcance de fuentes de cada consulta. Esa medida mejoró la continuidad, pero
no demuestra resolución universal de referentes ni elimina todos los errores
semánticos. La evaluación original fallida permanece versionada.

## 6. Endpoints y contrato

FastAPI expone POST `/api/v1/chat`, `/search`, `/comparisons`, `/scenarios` y GET
`/api/v1/catalog`, `/ontology`, `/evidence/{evidence_id}`,
`/sources/{source_id}`, `/health`, `/capabilities`. OpenAPI se entrega en
`PHASE56_OPENAPI.json`. No se ejecuta Streamlit.

El contrato `scientific-chat-v1` contiene conversation_id, message_id, answer,
citations, evidence_groups, comparison, discovery_suggestions, limitations,
provider_status, trace_id y snapshot_id. Una cita puede reunir varias filas de
una tabla, conservando cada evidencia, pasaje y condición en `supports`.

Se verificaron validación y tamaños, CORS restringido por defecto, paginación,
errores coherentes, rutas por ID sin lectura arbitraria de archivos, fallos de
proveedor y saturación con 429. Un trabajador posee SQLite/RDF y evita colas
ilimitadas. Los errores no devuelven credenciales, rutas privadas ni mensajes
internos del proveedor. El streaming del proveedor se almacena en el backend;
sólo segmentos completos comprobados pueden llegar a la respuesta final.

## 7. Pruebas ejecutadas

Los recibos versionados están en `artifacts/phase56/`. La regresión completa de
la primera implementación estable registró **3.534 pruebas aprobadas, 40 omitidas,
0 fallos**, con credenciales desactivadas y temporales por lotes. Las suites
anteriores se conservaron. La base histórica mantiene el mismo SHA-256 antes y
después. El cierre reconciliado de entrega registra **3.541 aprobadas y 40 omitidas**, con cero fallos pendientes. La primera ejecución de entrega tuvo un fallo por una clave técnica que coincidía con un rol reservado; se renombró la clave y se repitió íntegramente el lote 7, sin modificar la prueba. El lote 1 se reejecutó después de añadir la protección de valores reportados, con 378 pruebas aprobadas. Ambos recibos permanecen versionados y no se suman reejecuciones como pruebas nuevas.

También se ejecutaron HTTP sobre ASGI con Nemotron real, HTTP TCP real con
uvicorn con Nemotron y sin claves, pruebas de conversación y foco documental, comparación,
escenarios, proveedor fallido, JSON parcial, fuentes originales y controles
adversariales. El modelo servido y su consumo figuran en los recibos reales.
La batería semántica final contiene **19 casos sintéticos**, incluidos dos casos
bilingües contrastados; no representan resultados NASA ni una medición general
de precisión científica.

## 8. Resultados observados y revisión de originales

`original-source-checks.json` contrastó 65 respaldos contra el registro y contra
los PDF/CSV físicos: 65 coincidencias en ambos controles. Eso acredita citas y
localizadores, no que todas las frases sean pertinentes o científicamente
correctas. La revisión semántica fue realizada por este agente de software; no
hubo adjudicación independiente por un científico.

La comparación real conservó los campos de las filas S1/S2 de PSI-98: flujo de
20 cm/s en ambas; Concurrent frente a Opposed; Burn Time de 420 s frente a 70 s.
La presión no está disponible en esa comparación del snapshot. Son valores de
la tabla original, no una inferencia causal ni una ausencia global de datos NASA.
Los respaldos y el DOI original figuran en las citas de `live-final.json` y en
`original-source-checks.json`.

Los informes FLEX permitieron explicar instrumental y limitaciones de registro,
con localizadores de páginas físicas del PDF `20150023456`. Los documentos
normativos se explicaron como requisitos y métodos, sin convertirlos en
observaciones ni emitir una nueva recomendación de seguridad.

La revisión de originales identificó dos riesgos que las comprobaciones
iniciales no resolvían: convertir un objetivo «possibly» en una capacidad
establecida, y confundir radiative/radiactiva. Ambos motivaron controles generales
adicionales; sus versiones fallidas se conservan para auditoría.

## 9. Preguntas nuevas y utilidad real

La batería de 30 preguntas cubre sólidos, gotas, propagación, extinción,
detección, materiales, oxígeno, presión, flujo, gravedad, instrumentos,
comparación, normas, hábitats, ambigüedad y ataques. Recuperó 30 IDs de fuente;
los ocho controles negativos no recibieron DIRECT. Se añadió otra batería de
12 preguntas y conversaciones nuevas; no se importan ejemplos desde producción.

En la demostración diagnóstica de siete turnos, los siete respondieron HTTP 200:
cinco produjeron texto científico con citas y otros dos conservaron rutas de
búsqueda explícitamente no acreditadas. Hubo explicación y seguimiento sobre
instrumentos, comparación entre corridas, requisitos y exploración sin DIRECT.
La mediana fue 15,9 s y el máximo 49,4 s en esa medición, con 349.464 tokens de
entrada y 15.263 de salida contabilizados. No son metas de calidad ni estimación
de coste. Los límites operativos posteriores se documentan en la guía de API.

El conjunto inicialmente no utilizado para desarrollo tuvo seis consultas reales:
cuatro devolvieron citas, pero se detectó la confusión contextual descrita y hubo
respuestas sin explicación utilizable. Por ello **HTTP 200, citas resolubles y
scores NLI no equivalen a aceptación científica**. Tras detectar los fallos,
esos casos se consideran expuestos y las reejecuciones son regresiones, no una
nueva evaluación independiente. `operational-metrics.json` no les asigna una
precisión científica artificial.

## 10. Cobertura y límites del corpus

El snapshot contiene 39 entradas: ocho A, siete B y 24 C. Hay fuentes B duplicadas
de un mismo documento; esas cifras no significan 39 investigaciones distintas.
Los conteos de corridas y muestras representan registros, no una verificación de
sujetos físicos únicos. Sólo dos entidades Material están proyectadas en el
snapshot; esto limita la elegibilidad estructurada de preguntas abiertas.

Task Book no está ingerido; ACME tiene cobertura de catálogo; FLEX-2 tiene alcance
de campaña sin corridas inventadas. No se hereda gravedad de encabezados ni del
nombre de una misión. El clasificador conserva menciones no resueltas, lo que
reduce recall DIRECT; las fuentes documentales permiten conservar información.
No hay evidencia experimental acreditada para todas las condiciones de hábitats
lunares o gravedad parcial. Esto describe el corpus, no un vacío de NASA.

`coverage-audit.json` identifica originales locales fuera del snapshot como
candidatos pendientes. `coverage-candidates.json` propone revisar entidades o
aliases instrumentales respaldados por pasajes reales. No se incorporaron
hechos o relaciones sin revisar ni se publicaron ampliaciones ontológicas.

## 11. Integración y pendientes

El servidor del equipo inspeccionado en `02d00164e3baf3c594c749972c51944dce5b492e`
usa otro motor IVF/OLAP/Gemma. Se entrega una API independiente y su contrato;
no se modificó el laboratorio ni se construyó un frontend alternativo.

El dashboard debe enviar message/conversation_id, mostrar answer y etiquetas,
abrir las referencias y presentar la degradación cuando afecte a la respuesta.
Quedan la conexión real del frontend, configuración de orígenes/despliegue y,
si se requieren múltiples procesos, sesiones compartidas o afinidad de sesión.

En calidad científica quedan calibración independiente del verificador con
expertos, mejor evaluación de pertinencia y ambigüedad, revisión de falsos
negativos y ampliación revisada del corpus. La traducción inversa y el control de
términos son filtros adicionales, no una garantía universal de equivalencia.
No se cerró la aceptación general exigida por la misión con pruebas automáticas.

## 12. Commits y reproducción

- `ba9a58a`: API conversacional, generación fundamentada y comprobaciones semánticas.
- `8a8f510`: continuidad de fuentes, controles bilingües y transporte HTTP.
- `bf34731`: preservación de cantidades reportadas frente a valores normalizados.
- Los recibos y contratos se entregan en un commit documental adicional.

No hubo push, merge ni cambios en main o diego/research.

La comprobación TCP final está en `real-http-nemotron.json`: HTTP 200, respuesta de Nemotron, una referencia agrupada y seis respaldos resueltos correctamente.

La guía `PHASE56_CHAT_API.md` contiene comandos, contratos, límites, modelos
aprovisionados y modos de fallo. Las mediciones son reproducibles desde las
preguntas versionadas, el snapshot verificado y los recibos de modelos locales.
