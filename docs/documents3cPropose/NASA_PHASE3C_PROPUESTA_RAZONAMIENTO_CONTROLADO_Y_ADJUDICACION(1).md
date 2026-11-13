# NASA Fire-Safety Evidence Assistant — Corrección del gold y razonamiento controlado

**Estado:** propuesta técnica de revisión, versión 1. No modifica el repositorio, los resultados históricos ni el gold. No constituye certificación de pertinencia realizada por un científico independiente.

## 1. Decisión recomendada

Introducir **recuperación semántica asistida por Nemotron con libertad en el descubrimiento, pero no en la publicación de hechos científicos**. Conservar QueryIntentV2, SemanticRegistry, KG/RDF, FTS5/BM25, Evidence Registry y controles de procedencia. Jev permanece opcional para priorización de fragmentos durante ingesta y revisión, no como autoridad científica.

No se debe confundir precisión científica con exact match de QueryIntent ni con coincidencia de IDs. Proponer como hipótesis de evaluación Precision@5 de documentos realmente relevantes >=0.90 con gold independiente, y sin falsos DIRECT científicos ni afirmaciones visibles no soportadas; no declarar ese rendimiento alcanzado antes de medirlo. Deben medirse recall, abstención, cobertura, p95 de latencia, coste y errores por clase.

## 2. Evidencia de los problemas

- 101 predicciones: las 16 omisiones de `requested_information` se descomponen exactamente en 8 `ExperimentalRun` y 8 `SafetyImplication`. `ExperimentalRun` es un target y no necesariamente un tipo de evidencia solicitado. Varias etiquetas `SafetyImplication` se añadieron a preguntas de observación, requisito, guía y preguntas abiertas.
- El gold histórico NO debe editarse. Se entrega un JSON auxiliar con 16 propuestas: **15 propuestas para retirar una etiqueta no solicitada y un caso para deliberación semántica (`qi27`)**. Todas quedan pendientes de ratificación; otros campos pueden seguir fallando.
- `qi03` y `qi11`: PSI S1/S2 pueden estar estructuralmente respaldados, pero documentos BASS/SIBAL con flujos distintos o contextos distintos no deben presentarse como prueba de la condición numérica pedida.
- `qi12`: recuperar S1/S2 no sustituye una comparación de atributos fuente-respaldados.
- `qi18` y `qi33`: un texto como “these questions” exige recuperar el antecedente antes de presentarlo como pregunta de investigación NASA específica.
- `qi24` encuentra un documento sobre supresión de PMMA, mientras `qi27` no lo incluye; debe diagnosticarse expansión temática y elegibilidad documental, no crear una regla `if qi27`.
- `qi42` solicita PMMA y SIBAL, pero no es seguro traducirlo a un único run que satisfaga simultáneamente ambos materiales. Posibles interpretaciones: lista de ambos grupos, comparación, o aclaración.
- `comp01` y `comp11`: tolerancias/intervalos pueden interpretarse correctamente y aun así devolver documentos irrelevantes por BM25. Descubrimiento documental y evidencia de las restricciones no son lo mismo.
- `corrective-unseen-document`: la recuperación por ID documental debe funcionar por índice exacto incluso si el LLM falla.
- Posible falla de procedencia: fragmentos de informes muestran `page=1` mientras el texto contiene marcas NASA/TM de páginas impresas 100–101; auditar página PDF, página impresa y pasaje fuente sin afirmar ubicación falsa.

## 3. Política de tres espacios: flexibilidad donde ayuda

**Espacio A — Interpretación de pregunta.** Nemotron propone hasta tres hipótesis tipadas de intención, distingue explícito vs inferido, detecta ambigüedad y permite reformulaciones. Sólo los conceptos permitidos por el registry entran como canónicos. Para AND/OR ambiguo y comparaciones el sistema puede aclarar o buscar por ramas sin confundir unión de resultados con un run que satisfaga todos los materiales.

**Espacio B — Búsqueda de candidatos.** Ejecutar en paralelo (a) constraints exactos de KG y (b) BM25 con 1–3 reformulaciones semánticamente acotadas. Se pueden descubrir documentos relacionados, incluso si no son pruebas DIRECT. Opcionalmente habilitar sólo experimentos acotados de candidate reranking semántico; no reactivar búsqueda vectorial global por defecto porque sus resultados previos fueron inferiores a BM25.

**Espacio C — Evaluación de evidencia.** Para cada candidato, Nemotron puede proponer etiqueta `POTENTIAL_DIRECT`, `POTENTIAL_RELATED`, `CONTEXTUAL`, `IRRELEVANT`, `UNCERTAIN` y una ubicación textual. El código determina finalmente si las restricciones canónicas están verificadas y qué autoridad tiene el fragmento. La clasificación del modelo es **propuesta, no verdad**. No permitir que un pasaje temáticamente parecido se convierta en DIRECT sin comprobar material, gravedad, unidades, contexto experimental y procedencia.

## 4. Flujo técnico recomendado

```text
Pregunta libre
  -> detector exacto de IDs/cifras/unidades y nivel de ambigüedad
  -> Nemotron: extracción mínima + hipótesis/estrategias limitadas
  -> SemanticRegistry: validación de clases, entidades y relaciones
  -> QueryIntentV2 (con explícito / inferido / desconocido)
      -> KG/SPARQL + matching determinista
      -> BM25 FTS5 con query expansion controlada
  -> conjunto amplio de candidatos (sin autoridad)
  -> evaluador/reranker Nemotron (evidence_id + fragmento + match/differ/unknown por restricción)
  -> controles deterministas de identidad, valores, unidades, alcance, fuente y tipado epistémico
  -> EvidenceBundle: DIRECT / RELATED / CONTEXTUAL / UNRESOLVED / NO_DIRECT
  -> redacción extractiva; paráfrasis sólo tras benchmark de fidelidad revisado
  -> respuesta con fuente, pasaje, página validada, diferencias y limitaciones
```

**Importantísimo:** `CONTEXTUAL` no es DIRECT ni RELATED. Puede ser útil explicar por qué un documento trata sobre el mismo tema, pero nunca usarlo como prueba de un experimento incompatible.

## 5. Decisiones de razonamiento y seguridad

1. Nemotron puede sugerir consultas, sinónimos no canónicos para descubrimiento y candidatos de relevancia.
2. Nemotron no puede aprobar aliases científicos, insertar hechos KG, asignar niveles NASA de autoridad o cambiar el resultado de una comparación numérica canónica.
3. El plan debe preservar cada filtro del usuario: material, gravedad, experimental run, flujo, unidades, intervalo, contexto y tipo epistémico. Si una expansión relaja un filtro, debe registrarlo y marcar su resultado CONTEXTUAL/RELATED, nunca DIRECT.
4. Para afirmaciones, registrar `claim`, `evidence_id`, `supported_span`, `authority`, `modality`, `negation`, `quantities`, `context`, `verifier_outcome`. Una cita existente no garantiza que una paráfrasis esté apoyada por esa cita.
5. Toda decisión tentativa debe tener rastreo de versiones de modelo, prompt, QueryIntent, registry, documentos candidatos, verificaciones de descarte y respuesta final. No registrar razonamiento interno oculto; registrar justificaciones explícitas basadas en los pasajes.
6. Para una consulta con ID de documento reconocido, usar recuperación exacta de metadata/registro antes de intentar interpretaciones generativas.
7. Si no hay evidencia adecuada, responder NO_DIRECT y explicar cobertura. Nunca inferir que NASA desconoce la respuesta ni que se requiere investigación futura salvo fuente explícita.

## 6. Riesgos que debemos medir separadamente

| Error | Impacto | Protección |
|---|---|---|
| Pasaje irrelevante presentado como prueba | Alto | Rerank estructurado, contexto por restricción, etiquetas separadas |
| Condición científica incompatibles (material/flujo/gravedad) | Crítico para DIRECT | Comparación KG determinista, UNKNOWN si falta evidencia |
| Observación atribuida como conclusión o guidance | Alto | Epistemic type review + fuentes/autoridad |
| Valor, unidad o intervalo inventado | Crítico | Parser dimensional/intervalos, match exacto, no LLM para cálculo |
| Documento real con conclusión inventada | Crítico | Span-level entailment y validación de negación, modalidad y alcance |
| Cita de página incorrecta | Alto | Offsets del PDF original; diferencia página física vs impresa |
| Falso NO_DIRECT por interpretación incompleta | Medio/alto | Multi-hypothesis retrieval + señales de cobertura + clarificación |
| Afirmación causal por combinar dos documentos | Crítico | Prohibir síntesis causal no documentada; claim granularity |
| Identidad errónea de material/sinónimo | Alto | Aliases aprobados; staging para otros; no canonizar por similitud |

La trazabilidad permite **auditar algunos errores después**, pero no hace que el error sea automáticamente visible: si una afirmación falsa cita un documento real, hace falta contrastar la afirmación con el fragmento y su contexto.

## 7. Jev — función complementaria

- Mantener `KEEP_OPTIONAL` y deshabilitado por defecto.
- Usarlo para priorizar fragmentos que parezcan contener observaciones, conclusiones, intervención, norma o pregunta expresa; no para filtrar irreversiblemente el corpus.
- Nemotron debe tratar relevancia para la pregunta; Jev trata indicios de tipo retórico en el fragmento. Son problemas distintos.
- Comparar con ablations: reglas, reglas+Nemotron, reglas+Jev y reglas+Nemotron+Jev sólo cuando existe gold revisado, y medir la latencia/coste adicional.
- Los 30 casos anteriores son evidencia sugerente, no una garantía de precisión futura.

## 8. Propuesta de reconciliación semántica del gold (no aprobación final)

Hay 16 omisiones `requested_information` entre las 101 consultas: ocho `ExperimentalRun` (ya target) y ocho `SafetyImplication` (implícito dudoso). En el JSON anexo se conservan query, etiquetas históricas, resultado del intérprete, corrección propuesta y otros campos que todavía discrepan.

- **Propuesta directa para revisión formal:** retirar la duplicación `ExperimentalRun` de `requested_information` en qi05/06/07/08/12/13/25/50, conservándolo en `targets`.
- **Propuesta directa para revisión formal:** no exigir `SafetyImplication` en qi14, qi16, qi17, qi18, qi31, qi32 y qi33 salvo que se añada a la consulta o exista una especificación epistemológica legítima que lo exija.
- **Disputa abierta:** qi27 (“What has NASA reported about suppressing PMMA fires in microgravity?”). `SafetyImplication` puede ser parte de una respuesta, pero no debe imponerse como la única clase solicitada. Considerar búsqueda amplia de reported findings y clasificar pasajes al recuperar evidencia, con revisión del contrato antes de cambiar etiquetas.
- **Otras decisiones:** qi42 necesita política de enumeración/comparación y aclaración. qi12 necesita salida de comparación. qi18/33 necesitan antecedente. qi31/32 necesitan alcance del material.

Nunca cambiar el gold original ni presentar un F1 recalculado post hoc como evaluación independiente. Un gold revisado exige nueva versión, justificación y aprobación de responsable disciplinar/metodológico. Los casos ya usados para diagnosticar son pruebas de regresión; la mejora real se valida en nuevas preguntas congeladas antes de probar el modelo.

## 9. Plan experimental A/B/C/D

- **A — Baseline:** V2 exact KG + BM25 actual.
- **B — Discovery:** A + Nemotron para hasta tres reformulaciones controladas (no rerank).
- **C — Rerank:** B + relevancia de pasajes evaluada por Nemotron con evidencia textual; clases canónicas/numéricas siguen verificadas por código.
- **D — Jev:** C + triaje Jev opcional de candidatos de ingesta, no duro.

Gold del benchmark debe incluir relevancia por pasaje, material/gravedad/flujo/fase, tipo de afirmación, autoridad NASA, pregunta realmente contestada y no-answer. Debe ser independiente de predicciones de los sistemas comparados. Estratificar consultas conocidas y nuevas, terminología exacta, paráfrasis, distractores del mismo dominio, consultas numéricas, múltiples materiales, comparaciones y NO_DIRECT.

Métricas separadas: Candidate Recall@10, Precision@5 y Recall@5 de evidencia realmente relevante, MRR, precisión DIRECT, tasa de falso DIRECT, correct no-answer, fidelidad de afirmaciones visibles, citation accuracy y cobertura/abstención selectiva; mediana/p95 de latencia y coste. Objetivo de investigación: Precision@5 >=0.90 en casos evaluados por revisores, sin falsos DIRECT en el conjunto revisado y cero afirmaciones no respaldadas visibles. Con N pequeño no afirmar garantía de producción.

## 10. Secuencia de implementación mínima

**Gate 1 — contrato y fuentes**: revisar/adjudicar las 16 etiquetas y 20 casos; conservar gold histórico y emitir propuestas versionadas; auditar páginas y fuentes. 

**Gate 2 — descubrimiento flexible**: introducir query expansion limitada, evitar que material+flujo se pierdan, habilitar salida contextual separada; añadir lookup por ID documental.

**Gate 3 — reranking con fundamentos**: candidatos con fragmentos, comparación de restricciones y autoridad; el modelo propone y las validaciones deciden. Implementar fallback sin LLM.

**Gate 4 — respuestas útiles**: comparación fuente-respaldada, `NO_DIRECT` explícito, citas correctas, presentación por categoría. Mantener quote-gate para afirmaciones no evaluadas.

**Gate 5 — evaluación honesta**: ablations A/B/C/D, benchmark congelado independiente, pruebas adversariales, resultados primer pase vs reparaciones. El sistema puede seguir experimental si falta revisión especializada.

## 11. Archivos de evidencia y trazabilidad

- `phase3c_final_repair_interpreter_cases_v6.jsonl`
- `phase3c_final_repair_e2e_cases_v6.jsonl`
- `phase3c_final_repair_scientific_relevance_review_v2.json`
- `phase3c_final_repair_objective_retrieval_v2.jsonl`
- `NASA_PHASE3C_AUDITORIA_20_CASOS.md`
- Documento complementario `NASA_PHASE3C_RECONCILIACION_GOLD_PROPUESTAS_v1.json`.

**Estado final de esta propuesta:** lista para revisión de contrato y prototipo experimental, no significa que se hayan ejecutado cambios de código ni nuevos benchmarks.
