# Auditoría independiente preliminar — NASA Phase 3C (20 consultas)

**Naturaleza de este documento:** revisión analítica técnica y preliminar del asistente basada en archivos aportados. No constituye evaluación humana independiente de seguridad contra incendios ni reemplaza revisión NASA/experta. No modifica gold, resultados o etiquetas del repositorio.

## Archivos inspeccionados
- `phase3c_final_repair_baseline.json`
- `phase3c_final_repair_e2e_cases_v6.jsonl`
- `phase3c_final_repair_interpreter_cases_v6.jsonl`
- `phase3c_final_repair_objective_retrieval_v2.jsonl`
- `phase3c_final_repair_scientific_relevance_review_v2.json`

## Hallazgos transversales

1. **Contrato del gold desalineado:** las 16 clases `requested_information` omitidas en los 101 casos son exactamente 8 `ExperimentalRun` (clase objetivo) y 8 `SafetyImplication` (no necesariamente solicitada por pregunta). Los cuatro casos qi14/16/17/18 muestran ejemplos claros. Revisión requerida antes de usar esta métrica para optimización.
2. **Recuperación ≠ relevancia:** 11/11 identificadores exigidos fueron encontrados en el benchmark objetivo, pero 3 consultas incluyeron evidencia adicional no necesariamente pertinente. En el servicio integrado hay literatura espacial no relacionada y tablas SIBAL ante filtros PMMA. No se puede reportar precisión científica sin etiquetas independientes.
3. **Comparación ausente:** qi12 recupera ambos experimentos, pero no ejecuta una comparación comprensible de sus diferencias.
4. **Riesgo de procedencia por página:** en el paquete de revisión, 46 de 53 pasajes no PSI muestran `page=1`; al menos el pasaje `E-0b143c5fb89f5e13` contiene marcas internas NASA/TM-20210011385 de páginas 100–101 mientras el metadata fija page=1. Verificar contra PDF y etapa de segmentación antes de usar esas páginas como citas precisas.
5. **Fuente potencialmente pertinente omitida por otra consulta:** `qi24` sí recupera el informe *CO2 Suppression of PMMA Flames In Low-Gravity* (`E-382165f1a4516fa8`), mientras `qi27` —sobre supresión de PMMA en microgravedad— no lo selecciona. Es un caso cruzado específico para depurar retrieval.
6. **No-answer no es respuesta completa:** `corrective-unseen-document` devuelve error de interpretación ante un ID documental explícito; `qi24` no entrega los ensayos solicitados; consultas compuestas sí preservan operadores pero devuelven distractores.
7. **Clasificación de OpenQuestion insuficiente sin contexto:** la frase “Additional focused tests may be required to develop guidance on these questions” requiere el antecedente de “these questions”; no identifica por sí sola una pregunta de investigación concreta.
8. **Alcance de evaluación:** el paquete contiene 20 casos, 8 marcados REVIEW_REQUIRED, sin etiquetas humanas. Los juicios a continuación son diagnósticos preliminares y conservan esas 8 etiquetas sin inventar gold.

## Matriz completa de los 20 casos

| ID | Consulta | Dictamen técnico preliminar |
|---|---|---|
| `qi03` | SIBAL Fabric microgravity | CANDIDATOS DIRECTOS CORRECTOS; EXCESO DOCUMENTAL |
| `qi11` | SIBAL Fabric microgravity flow velocity >= 20 cm/s | DIRECT CORRECTO; FILTRO DOCUMENTAL DEFICIENTE |
| `qi12` | Compare Saffire-I S1 and S2 | RECUPERA LOS DOS RUNS; NO COMPARA |
| `qi14` | What did NASA observe about suppression? | OBSERVACIÓN ADECUADA; GOLD CUESTIONABLE |
| `qi16` | Find NASA requirements | REQUISITO ADECUADO; GOLD CUESTIONABLE |
| `qi17` | Find NASA guidance | GUIDANCE ADECUADA; GOLD CUESTIONABLE |
| `qi18` | NASA open questions | OPEN QUESTION: FALTA ANTECEDENTE |
| `qi19` | What about acrylic fires? | ABSTENCIÓN SEGURA |
| `qi20` | velocity effects | ABSTENCIÓN SEGURA |
| `qi22` | xenon combustion | NO DIRECT SEGURO; DETALLE DE INTENCIÓN MEJORABLE |
| `qi24` | Show PMMA tests | RECUPERACIÓN PARCIAL DE DOCUMENTOS; NO MUESTRA TESTS |
| `qi27` | What has NASA reported about suppressing PMMA fires in microgravity? | INFORMACIÓN SOLICITADA PERDIDA; EVIDENCIA CRUZADA OMITIDA |
| `qi31` | PMMA requirement | NO DIRECT NO DEMOSTRADO; GOLD CUESTIONABLE |
| `qi32` | PMMA guidance | GUIDANCE NO RECUPERADA; OPERACIÓN DISTINTA |
| `qi33` | suppression open question | OPEN QUESTION: CITA INCOMPLETA |
| `qi42` | PMMA and SIBAL under microgravity | CONSULTA SUBESPECIFICADA; AND/OR ERRÓNEAMENTE FIJADO |
| `qi45` | NASA conclusions | CONCLUSIÓN RESPALDADA CON MODALIDAD CONDICIONAL |
| `comp01` | Find experiments using PMMA in microgravity with airflow between 0.01 and 0.11 m/s | NUMÉRICO BIEN INTERPRETADO; EVIDENCIA IRRELEVANTE |
| `comp11` | Find experiments using PMMA in microgravity with airflow about 0.01 +/- 0.005 m/s | APROXIMACIÓN CONSERVADA; EVIDENCIA IRRELEVANTE |
| `corrective-unseen-document` | Find Document from source 20140011119 | FALLO END-TO-END VERIFICABLE |

## Diagnóstico y acciones por caso

### `qi03` — SIBAL Fabric microgravity
**Diagnóstico:** CANDIDATOS DIRECTOS CORRECTOS; EXCESO DOCUMENTAL.
**Evidencia del diagnóstico:** S1/S2 satisfacen material y gravedad según las filas PSI. Ocho documentos adicionales incluyen BASS-II y otros contextos: no constituyen pruebas DIRECT de esos dos runs.
**Acción recomendada:** Separar evidencia estructurada obligatoria de contexto documental; no afirmar que los ocho pasajes sean igualmente aplicables.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** 2. **Recuperada:** 10. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi11` — SIBAL Fabric microgravity flow velocity >= 20 cm/s
**Diagnóstico:** DIRECT CORRECTO; FILTRO DOCUMENTAL DEFICIENTE.
**Evidencia del diagnóstico:** S1/S2 figuran en la fuente con 20 cm/s. Pasajes de extinción BASS a 1–5 cm/s u otros materiales no prueban el filtro >=20 cm/s.
**Acción recomendada:** Exigir coincidencia de la restricción numérica/contexto antes de presentar documentos como prueba; si son contexto, etiquetarlos.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** 2. **Recuperada:** 10. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi12` — Compare Saffire-I S1 and S2
**Diagnóstico:** RECUPERA LOS DOS RUNS; NO COMPARA.
**Evidencia del diagnóstico:** Recupera S1 y S2, pero la respuesta muestra filas y coincidencias genéricas en lugar de una comparación lado a lado. El gold exige ExperimentalRun en requested_information, a pesar de que es un target.
**Acción recomendada:** Auditar gold y construir respuesta comparativa con diferencias verificables (dirección del flujo cuando el esquema lo permita).
**Gold:** ExperimentalRun. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** 2. **Recuperada:** 9. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi14` — What did NASA observe about suppression?
**Diagnóstico:** OBSERVACIÓN ADECUADA; GOLD CUESTIONABLE.
**Evidencia del diagnóstico:** La cita documenta que el fuego no se extinguió y creció al restaurar el flujo. El usuario solicita observación, no explícitamente SafetyImplication.
**Acción recomendada:** Mantener ReportedObservation; revisar la segunda etiqueta del gold sin sobrescribirlo.
**Gold:** ReportedObservation, SafetyImplication. **Interpretación actual:** ReportedObservation. **Identidad de evidencia exigida:** 1. **Recuperada:** 1. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi16` — Find NASA requirements
**Diagnóstico:** REQUISITO ADECUADO; GOLD CUESTIONABLE.
**Evidencia del diagnóstico:** El pasaje NASA-STD dice shall meet the requirements. Responde directamente a un pedido de requisitos.
**Acción recomendada:** Mantener Requirement; no introducir SafetyImplication por inferencia de dominio.
**Gold:** SafetyImplication, Requirement. **Interpretación actual:** Requirement. **Identidad de evidencia exigida:** 1. **Recuperada:** 1. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi17` — Find NASA guidance
**Diagnóstico:** GUIDANCE ADECUADA; GOLD CUESTIONABLE.
**Evidencia del diagnóstico:** El pasaje indica explícitamente que la fuente proporciona guidance para assessments.
**Acción recomendada:** Mantener Guidance; revisar si SafetyImplication pertenece a otra capa taxonómica.
**Gold:** SafetyImplication, Guidance. **Interpretación actual:** Guidance. **Identidad de evidencia exigida:** 1. **Recuperada:** 1. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi18` — NASA open questions
**Diagnóstico:** OPEN QUESTION: FALTA ANTECEDENTE.
**Evidencia del diagnóstico:** La frase "Additional focused tests may be required to develop guidance on these questions" no formula por sí sola qué preguntas científicas están abiertas.
**Acción recomendada:** Recuperar antecedente y contexto contiguo antes de mostrarla como pregunta NASA explícita.
**Gold:** SafetyImplication, OpenQuestion. **Interpretación actual:** OpenQuestion. **Identidad de evidencia exigida:** 1. **Recuperada:** 1. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi19` — What about acrylic fires?
**Diagnóstico:** ABSTENCIÓN SEGURA.
**Evidencia del diagnóstico:** Acrylic no se canonizó automáticamente como PMMA. El sistema pide aclaración. El gold no esperaba unresolved_mentions aunque retiene ambigüedad.
**Acción recomendada:** Precisar contrato entre ambiguities y unresolved_mentions; conservar abstención.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 0. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi20` — velocity effects
**Diagnóstico:** ABSTENCIÓN SEGURA.
**Evidencia del diagnóstico:** Velocity es insuficiente para escoger velocidad de flujo o propagación de llama. Se solicita aclaración.
**Acción recomendada:** No forzar AirflowVelocity; reconciliar definición de ambigüedad frente a unresolved.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 0. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi22` — xenon combustion
**Diagnóstico:** NO DIRECT SEGURO; DETALLE DE INTENCIÓN MEJORABLE.
**Evidencia del diagnóstico:** Xenon es no reconocido y no se inventan resultados. Sin embargo, combustion aparece como otro término unresolved pese a su papel general.
**Acción recomendada:** Mantener desconocido xenon; mejorar límites de las menciones lingüísticas.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 0. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `qi24` — Show PMMA tests
**Diagnóstico:** RECUPERACIÓN PARCIAL DE DOCUMENTOS; NO MUESTRA TESTS.
**Evidencia del diagnóstico:** Entre las fuentes existe CO2 Suppression of PMMA Flames In Low-Gravity, pertinente para explorar PMMA, pero la respuesta es esencialmente una lista de citas sin runs caracterizados.
**Acción recomendada:** Distinguir documentos de experimentos indexados; ofrecer publicaciones relevantes y reconocer falta de runs estructurados si corresponde.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 8. **Estatus heredado:** `REVIEW_REQUIRED`.

### `qi27` — What has NASA reported about suppressing PMMA fires in microgravity?
**Diagnóstico:** INFORMACIÓN SOLICITADA PERDIDA; EVIDENCIA CRUZADA OMITIDA.
**Evidencia del diagnóstico:** La consulta solicita qué reportó NASA sobre supresión de PMMA. El intent pierde SafetyImplication; los resultados incluyen tablas SIBAL. El pasaje específico CO2 Suppression of PMMA Flames In Low-Gravity recuperado en qi24 no aparece aquí.
**Acción recomendada:** Tratar "reported" como petición de información respaldada, sin forzar una sola clase; mejorar selección por tema y material, comparar contra fuente recuperada en qi24.
**Gold:** SafetyImplication. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 10. **Estatus heredado:** `REVIEW_REQUIRED`.

### `qi31` — PMMA requirement
**Diagnóstico:** NO DIRECT NO DEMOSTRADO; GOLD CUESTIONABLE.
**Evidencia del diagnóstico:** Se pide un requisito sobre PMMA; no se devuelve texto aplicable. Un requisito general de materiales no debe etiquetarse sin más como requisito específico de PMMA.
**Acción recomendada:** Aclarar alcance de la norma y distinguir requisito general vs requisito material-específico; revisar SafetyImplication del gold.
**Gold:** SafetyImplication, Requirement. **Interpretación actual:** Requirement. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 0. **Estatus heredado:** `REVIEW_REQUIRED`.

### `qi32` — PMMA guidance
**Diagnóstico:** GUIDANCE NO RECUPERADA; OPERACIÓN DISTINTA.
**Evidencia del diagnóstico:** El intent obtiene Guidance pero cambia SEARCH a EXPLAIN; no hay evidencia vinculada al material.
**Acción recomendada:** Distinguir texto general sobre flammabilidad vs guidance específicamente aplicable a PMMA; evaluar si EXPLAIN es diferencia sustantiva.
**Gold:** SafetyImplication, Guidance. **Interpretación actual:** Guidance. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 0. **Estatus heredado:** `REVIEW_REQUIRED`.

### `qi33` — suppression open question
**Diagnóstico:** OPEN QUESTION: CITA INCOMPLETA.
**Evidencia del diagnóstico:** Recupera "Additional focused tests may be required ..." sin identificar las preguntas a las que se refiere. La etiqueta adicional SafetyImplication del gold no se desprende directamente de la consulta.
**Acción recomendada:** Exigir antecedente y pregunta concreta antes de clasificar como OpenQuestion respondida.
**Gold:** SafetyImplication, OpenQuestion. **Interpretación actual:** OpenQuestion. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 1. **Estatus heredado:** `REVIEW_REQUIRED`.

### `qi42` — PMMA and SIBAL under microgravity
**Diagnóstico:** CONSULTA SUBESPECIFICADA; AND/OR ERRÓNEAMENTE FIJADO.
**Evidencia del diagnóstico:** "PMMA and SIBAL under microgravity" puede significar ambos grupos o comparación, no dos materiales obligatorios en un solo run. El gold fija dos hasMaterial como conjunción.
**Acción recomendada:** Representar unión de conjuntos / comparación o pedir aclaración, no imponer un AND imposible por defecto.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 10. **Estatus heredado:** `REVIEW_REQUIRED`.

### `qi45` — NASA conclusions
**Diagnóstico:** CONCLUSIÓN RESPALDADA CON MODALIDAD CONDICIONAL.
**Evidencia del diagnóstico:** La cita atribuye una evaluación condicional sobre supresor y enfriamiento; no es una medición ni una norma.
**Acción recomendada:** Mostrarla como conclusión condicionada con fuente, sin afirmar eficacia experimental verificada.
**Gold:** NASAConclusion. **Interpretación actual:** NASAConclusion. **Identidad de evidencia exigida:** 1. **Recuperada:** 1. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

### `comp01` — Find experiments using PMMA in microgravity with airflow between 0.01 and 0.11 m/s
**Diagnóstico:** NUMÉRICO BIEN INTERPRETADO; EVIDENCIA IRRELEVANTE.
**Evidencia del diagnóstico:** La consulta PMMA/microgravedad/0.01–0.11 m/s recupera material SIBAL que difiere y documentos de antenas/sensores que no satisfacen las condiciones.
**Acción recomendada:** Aplicar filtro semántico a pasajes o separarlos de elegibles; no elevar BM25 irrelevante a fuente científica de la consulta.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 10. **Estatus heredado:** `REVIEW_REQUIRED`.

### `comp11` — Find experiments using PMMA in microgravity with airflow about 0.01 +/- 0.005 m/s
**Diagnóstico:** APROXIMACIÓN CONSERVADA; EVIDENCIA IRRELEVANTE.
**Evidencia del diagnóstico:** Se conserva tolerancia 0.01±0.005 m/s; los resultados contienen instrumentación espacial sin relación y SIBAL diferente de PMMA.
**Acción recomendada:** Conservar el parse correcto, corregir selección documental y respuesta NO_DIRECT con contexto justificado.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 10. **Estatus heredado:** `REVIEW_REQUIRED`.

### `corrective-unseen-document` — Find Document from source 20140011119
**Diagnóstico:** FALLO END-TO-END VERIFICABLE.
**Evidencia del diagnóstico:** Una consulta de documento por ID 20140011119 termina con "query interpretation unavailable" y no ejecuta recuperación por identificador.
**Acción recomendada:** Crear fallback determinista de consulta documental por ID de fuente reconocido, sin inventar datos ni cambiar gold.
**Gold:** sin clase epistémica explícita. **Interpretación actual:** sin clase epistémica explícita. **Identidad de evidencia exigida:** NO EVALUABLE. **Recuperada:** 0. **Estatus heredado:** `OBJECTIVE_SCOREABLE`.

## Priorización propuesta

**Bloqueante 1: revisar y versionar el contrato semántico de gold**, distinguiendo `target` de `requested_information`, clases supuestas por jerarquía y etiquetas inequívocas, con protocolo de doble etiquetado y registro de desacuerdos. No editar retroactivamente el gold histórico.

**Bloqueante 2: depurar selección de evidencia documental**, con negativos duros tomados de `comp01`, `comp11`, `qi27` y `qi03`. La coincidencia léxica es candidata de descubrimiento, no prueba de satisfacer todas las restricciones.

**Bloqueante 3: validar procedencia de páginas**, reparar o distinguir `page` del archivo segmentado frente a página impresa/real, y evitar afirmar ubicaciones falsamente precisas.

**Bloqueante 4: comparar de verdad y responder a la pregunta**, particularmente `qi12` y `qi24`; separar `no DIRECT en KG` de `existe evidencia documental pertinente` y presentar razones.

**Bloqueante 5: revisar fuentes y conceptos dependientes del contexto**, incluyendo OpenQuestion, NASAConclusion, Guidance, Requirement y AND/OR de múltiples materiales.

**Bloqueante 6: completar revisión disciplinar independiente**, principalmente los ocho REVIEW_REQUIRED y los tres casos de recuperación objetiva con evidencias extra. Este informe es preauditoría técnica, no sustitución del revisor científico.

## Protocolo recomendado para un evaluador científico

Para cada evidencia: (i) fuente y fragmento original, (ii) coincidencia de material/gravedad/flujo/contexto, (iii) clase epistémica respaldada, (iv) DIRECT, RELATED, IRRELEVANT o UNDETERMINED, (v) si responde la pregunta, (vi) comentarios y grado de certeza. Conservar dos opiniones independientes cuando el alcance sea ambiguo. No evaluar sólo por igualdad de IDs.

## Integridad del paquete recibido

- Casos integrales: 20; revisión: 20; casos de retrieval objetivo: 12; predicciones de interpretación: 101.
- La bandera `human_review_performed` permanece en false. No se han alterado archivos aportados ni gold.
- El benchmark `corrective-unseen-document` carece de evidencia recuperada y falla la interpretación del identificador: distinguir fallo de servicio de ausencia real de documento.
- Para auditar con certeza la ubicación exacta en PDF se necesitan los documentos originales y su paginado, que no forman parte de estos cinco archivos.
