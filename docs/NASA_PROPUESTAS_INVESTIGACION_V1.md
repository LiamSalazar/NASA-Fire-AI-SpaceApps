# NASA FIRE AI — Propuestas de investigación y evolución v1

Autor: Diego · Fecha: 17 de octubre de 2026 · Rama: `diego/research`

**Estado: PROPUESTA.** Liam debe validar este documento. No cambia código, flags,
contratos, ontología ni conocimiento publicado. Las propuestas deben pasar el
protocolo de §33 de la especificación: hipótesis, prueba reproductora,
comparación A/B y criterio de aceptación declarado antes del resultado.

## 1. Contexto y alcance

- **Código evaluado:** `main` en `54445d0` (Phase 1 v4) y la especificación
  integral v1.0 del 14 de octubre de 2026.
- **Estado de la fase:** `PHASE1_COMPLETE=NO` en v4. LUCI recupera 17 de 31
  objetivos. El paper independiente PTFE recupera 7 de 34. Cuando el sistema
  acepta algo, la precisión es alta (28 de 29).
- **Trabajo ya hecho en esta rama:** defecto 2 (gramática numérica). Los
  resultados están en `artifacts/phase1_generalizable_ingestion/v5/numeric_expression_grammar/`.

## 2. Hallazgo que condiciona la prioridad

Repetimos sin conexión las propuestas reales de Nemotron guardadas en v4 (0
llamadas al modelo).

- **Rechazos por sintaxis numérica:** bajaron de 69 a 3. Los 3 que quedan no son
  un valor numérico.
- **Lo que bloquea ahora:** 56 cantidades de PTFE ya pasan la sintaxis y se
  rechazan por `QUANTITY_SUBJECT_NOT_IN_APPLICABLE_SOURCE`. Entre ellas están
  `10,000 psia`, `0/20` reacciones/pruebas y `50 ft-lbs (68J)`.
- **Valores mal leídos antes:** se encontraron varios casos:
  - `000 psia` tomado de `10,000 psia`;
  - `6 g` donde la fuente dice `1/6 g`;
  - `425 °C` donde la fuente dice `above 425 °C`.

**Conclusión.** El cuello de botella del recall pasó a ser el **alcance
experimental (M2)**. Ninguna propuesta tecnológica de abajo sustituye esa
reparación, y conviene atacarla primero.

## 3. Aclaraciones para alinear cómo se explica el sistema

1. **No se reentrena solo.** La especificación lo prohíbe: §1.2 y D-21 dicen
   que no se ajustan pesos. Lo que crece es el conocimiento aprobado y
   versionado. La propuesta P2 describe la única forma de "mejora continua"
   compatible con la especificación.
2. **Lo que contiene las alucinaciones no es la ontología.** Son las
   compuertas: el LLM propone, validadores deterministas comparan contra el
   original, y el sistema se abstiene cuando no hay soporte. La precisión
   científica sigue sin medirse con jueces independientes (P-19).
3. **"GitHub del conocimiento para cualquier giro"** es una buena forma de
   explicar el producto. Hoy existen versión aprobada con digest exacto,
   publicación, rollback y procedencia. No existen los espacios por usuario
   tipo rama (Etapa E). El dominio sigue siendo específico de NASA (ontología,
   YAML de `domain/` y reglas en código).

| Concepto Git | Equivalente en conocimiento | Estado |
| --- | --- | --- |
| commit con autor | versión aprobada con evidencia y revisor | existe |
| rama | espacio de trabajo aislado | no existe (Etapa E) |
| pull request con diff | promoción con antes/después científico | parcial |
| CI | validadores, SHACL, verificación de afirmaciones | existe |
| revert | rollback sin borrar historia | existe |
| blame | localizador al original (página, tabla, fila) | parcial (visor pendiente) |

Un dato a favor de las ramas: `curation.py` ya publica cada versión como
N-Triples ordenadas. Ese es el mismo formato que LinkedDataHub versiona
directamente en Git.

## 4. Posición frente al estado del arte

Las piezas individuales ya existen:

- RAG anclado en ontología (OG-RAG, EMNLP 2025).
- Afirmación + evidencia + procedencia (micro/nanopublicaciones).
- RDF versionado en Git (LinkedDataHub) y diffs de grafos de conocimiento.
- Validación de grafos con LLM y humanos (Tsaneva et al. 2025).

No encontramos una herramienta que combine todo esto:

- tipos epistémicos como regla dura;
- DIRECT/RELATED con la diferencia explícita;
- el ciclo completo: el LLM propone, el código valida, una persona aprueba, y
  todo queda versionado;
- funcionamiento sin LLM.

El valor está en la integración disciplinada, no en un algoritmo nuevo.

## 5. Propuestas

Todas son opcionales, van detrás de un flag apagado por defecto, deben
compararse con y sin el cambio, y mantienen la ruta sin claves.

### P1 — Verificación de implicación por oración y abstención calibrada

- **Brecha:** `services/claim_verification.py:verify_claim` solo acepta citas
  exactas, normalizadas como subcadena. Esto obliga a respuestas literales, y
  P-04 exige que la cita *implique* la afirmación.
- **Base:**
  - VERICITE (BioNLP 2026): un modelo NLI verifica cada oración contra su cita.
  - CiteGuard (ICML 2026): control conformal de la tasa de falsos
    descubrimientos. Reportan que baja la proporción de afirmaciones sin
    soporte de 28–31% a menos de 10%, conservando 86–92% de las soportadas.
- **Integración:**
  - Una etapa adicional en `verify_claim`, después de la verificación exacta.
  - Paráfrasis controlada en `scientific_synthesis.py` (existe el flag
    `SCIENTIFIC_PARAPHRASE_ENABLED`).
  - Los números y unidades siguen verificándose de forma determinista
    (`store.payload`); el NLI solo juzga prosa.
- **Flag nuevo:** `CLAIM_ENTAILMENT_VERIFICATION_ENABLED=false`.
- **Aceptación:** sobre un conjunto adjudicado por linaje, la tasa de
  afirmaciones sin soporte queda por debajo de un α declarado (por ejemplo,
  0.05). La retención debe ser igual o mayor que la del modo de citas exactas,
  y no puede haber regresiones G2/G3.
- **Dependencia y riesgo:**
  - **Dependencia:** necesita etiquetas humanas para calibrar, como el visor de
    342 pares o los objetivos adjudicados de v4.
  - **Riesgos:** el NLI es débil con números y negaciones. Además agrega una
    dependencia pesada, que tendría que ir como grupo opcional.

### P2 — Mejora supervisada sin reentrenar (optimización de prompts)

- **Brecha:** la calidad de extracción depende de los prompts de
  `document_extraction.py` (`STAGE_INSTRUCTIONS`, `stage_prompt`), y hoy se
  ajustan a mano.
- **Base:** GEPA (arXiv 2507.19457, en DSPy). Evoluciona instrucciones leyendo
  trazas y retroalimentación textual, sin modificar pesos.
- **Integración:**
  - Los datos son correcciones y objetivos adjudicados de fuentes ya expuestas
    (LUCI, ignición, textiles, regulador, PTFE). Nunca se usa el holdout.
  - Cada versión de prompt se congela como parte del contrato y del digest de
    extracción, y entra solo si pasa la suite y la apruebe una persona.
- **Aceptación:** en la Etapa A (A/B/C), más objetivos correctos, cero errores
  críticos nuevos y un costo en tokens igual o menor, medidos en un conjunto
  de validación separado.
- **Riesgo:** sobreajuste a las fuentes expuestas. Mitigación: evaluación
  prospectiva congelada (§12 del prompt de Phase 1).

### P3 — Vigencia bitemporal

- **Brecha:** el capítulo 16 (contradicción, refutación, supersesión, vigencia)
  no está implementado.
- **Base:** Zep/Graphiti (arXiv 2501.13956). Separa tiempo válido de tiempo de
  registro, y marca `invalid_at` en lugar de borrar.
- **Integración:**
  - Los campos de vigencia irían en las afirmaciones aprobadas, mediante un
    contrato de extensión (§8.4). No se agrega vocabulario en silencio.
  - Se reutilizan `research_events` y `research_publications` de `curation.py`.
- **Caso real disponible:** `data/raw/nasa-std-6001-change3.pdf` junto a
  `nasa-std-6001.html` sirve para la prueba de §28.2, una norma reemplazada.
- **Aceptación:**
  - la consulta de seguridad muestra el requisito vigente comprobado y el
    histórico enlazado;
  - nunca se decide la vigencia solo por la fecha.

### P4 — Lectura de páginas con modelos de visión, solo como texto derivado

- **Brecha:** hay PDFs que son solo imagen (ACME bloqueado) y superíndices que
  se aplanan.
  - La gramática numérica nueva ya detecta `×103` como ambiguo, sin confirmar.
  - En v4, la entrada de imagen clasificó mal cantidades ajustadas.
- **Base:** olmOCR (arXiv 2502.18443) y modelos OCR de 2026 en olmOCR-Bench y
  OmniDocBench.
- **Integración:**
  - Se aplica solo a páginas sin texto extraíble o a ambigüedades tipográficas
    puntuales, por ejemplo para confirmar un exponente.
  - El texto resultante se guarda como *derivado* (P-10), con su localizador de
    página. Nunca decide roles científicos.
- **Aceptación:** ACME queda buscable, y las ambigüedades
  `FLATTENED_EXPONENT_UNCONFIRMED` se resuelven con evidencia de la página
  original, con cero valores numéricos alterados.

### P5 — Unidades y magnitudes mapeadas a QUDT

- **Brecha:** la razón más frecuente en LUCI es
  `QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED` (22 de 35 propuestas).
  `normalization/units.py` no conoce psia, ft-lbs, J, µL ni RPM, y quedan 537
  campos sin mapear.
- **Base:** Schema-Miner Pro (Semantic Web Journal, 2025–26): el LLM propone el
  mapeo, un humano lo valida y queda anclado a QUDT.
- **Integración:**
  - Partir de `ontology/incorporation_mappings.ttl`, que ya enlaza a QUDT como
    `skos:relatedMatch`.
  - Las propuestas pasan por el flujo de extensión de curación existente.
  - Ninguna conversión se activa sin aprobación (P-05).
- **Aceptación:** sube el porcentaje de cantidades con unidad resuelta y
  aprobada, sin conversiones dimensionalmente inválidas y sin vocabulario
  silencioso.

### P6 — RAG con hipergrafo anclado en la ontología (solo ablación)

- **Base:** OG-RAG (EMNLP 2025) reporta +55% de recall de hechos.
- **Integración:** como proyección derivada y opcional, igual que el índice
  vectorial. No crea un segundo almacén de verdad (D-01).
- **Aceptación:** mejora el recall de la información solicitada (hoy 0.68) sin
  aumentar los falsos DIRECT.

### P7 — Exportar las afirmaciones aprobadas como nanopublicaciones

- **Base:** extensión de *knowledge provenance* de nanopublicaciones (IJDL 2025).
- **Integración:** solo exportación de lectura, a partir de los N-Triples
  publicados: aserción, procedencia e información de publicación.
- **Valor:** auditoría con un estándar abierto. Es útil también como argumento
  frente a auditores en la aplicación futura del sistema fuera de NASA.

## 6. Prerrequisitos comunes

1. **Línea base medida:** sin ella ninguna propuesta puede demostrar mejora.
   - `data/index/evidence.sqlite` no está versionada, y un clon nuevo no puede
     responder preguntas ni correr 37 pruebas.
   - Se propone distribuir el ZIP saneado de `phase3c_closure.py export`, o un
     comando reproducible de reconstrucción.
2. **Conjunto adjudicado por linaje y un holdout prospectivo nuevo:** lo
   requieren D-20 y P0.
3. **Portabilidad:** el código debe correr igual en Linux y en Windows. En esta
   rama se corrigieron fsync de directorios, CRLF en RDF y CSV, y el mismo
   cuidado aplica a todo lo nuevo.

## 7. Decisiones que pedimos a Liam

- [ ] Validar el diagnóstico de §2: el alcance (M2) es el siguiente cuello de
      botella, y la gramática numérica se integra a `main`.
- [ ] Priorizar entre P1, P2 y P3. Nuestra recomendación es P1, luego P3 y
      luego P2: P1 y P3 se traducen directo al producto y P2 requiere más gold.
- [ ] Decidir si se acepta una dependencia opcional pesada (modelo NLI) para P1.
- [ ] Indicar cómo distribuir `evidence.sqlite` a colaboradores.
- [ ] Indicar qué parte de M2 puede tomar esta rama sin chocar con
      `document_extraction.py`.

## 8. Referencias

- OG-RAG / RAG con ontología: https://www.ic-arts.eu/wp-content/uploads/2025/01/Ontology-Guided-RAG-Approach-for-Improving-Semantic-Precision-of-LLMs.pdf
- CiteGuard (ICML 2026): https://icml.cc/virtual/2026/poster/64935
- VERICITE (BioNLP 2026): https://aclanthology.org/people/yixian-ma/
- DS@GT ARC at LongEval 2026 (arXiv 2607.14400): https://papers.cool/arxiv/2607.14400
- Zep, grafo temporal (arXiv 2501.13956): https://arxiv.org/abs/2501.13956v1
- GEPA en DSPy: https://dspy.ai/api/optimizers/GEPA/overview/
- olmOCR (arXiv 2502.18443): https://arxiv.org/pdf/2502.18443v3
- Schema-Miner Pro: https://www.semantic-web-journal.net/content/schema-miner-pro-agentic-ai-ontology-grounding-over-llm-discovered-scientific-schemas-1
- Validación de grafos con LLM y humanos: https://oro.open.ac.uk/103792
- Nanopublicaciones con knowledge provenance: https://link.springer.com/article/10.1007/s00799-025-00431-x
- Micropublications (arXiv 1305.3506): https://arxiv.org/pdf/1305.3506

Algunas cifras de CiteGuard, VERICITE y GEPA provienen de resúmenes y de la
búsqueda, no de una lectura completa de los papers. Hay que verificarlas en la
fuente antes de citarlas formalmente.
