"""Versioned consolidation handoff; no scientific expert labels are invented."""

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
PREFIX = "phase3c_consolidation"


def read(name):
    return json.loads((ROOT / "artifacts" / f"{PREFIX}_{name}.json").read_text())


def write_json(name, value):
    path = ROOT / "artifacts" / f"{PREFIX}_{name}.json"
    if path.exists() and json.loads(path.read_text()) == value:
        return
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def report(name, content):
    path = ROOT / "docs" / f"PHASE3C_CONSOLIDATION_{name}_V1.md"
    if path.exists() and path.read_text() == content + "\n":
        return
    with path.open("x") as stream:
        stream.write(content + "\n")


def main():
    comparison = read("comparison_v4")
    quality = read("quality_v2")
    cases = read("answers_c_v4")["cases"]
    baseline = {case["case_id"]: case for case in read("answers_a_v4")["cases"]}
    models = []
    for version in range(1, 5):
        for case in read(f"answers_d_v{version}")["cases"]:
            if case.get("model"):
                models.append({"role": "selection", "version": version, **case["model"]})
    for name in ("source_to_graph_v1", "context_retry_v1", "context_retry_v2"):
        value = read(name)
        receipt = value.get("context_interpretation") or value.get("fresh_context_inference")
        if receipt:
            models.append({"role": "context", "artifact": name, **receipt})
        else:
            models.append(
                {
                    "role": "context",
                    "artifact": name,
                    "execution": "FRESH_ATTEMPT",
                    "failure": value.get("provider_failure"),
                }
            )
    for case in read("generative_synthesis_v1")["cases"]:
        models.append({"role": "synthesis", **case["receipt"]})
    write_json(
        "model_inventory_v1", {"attempts": models, "jev_calls": 0, "independent_review": None}
    )

    decisions = {
        "SCIENTIFIC_SYNTHESIS": "KEEP_EXPERIMENTAL",
        "CLAIM_GROUNDING": "PARTIAL",
        "EVIDENCE_SELECTION": "KEEP_EXPERIMENTAL",
        "CONDITION_AGNOSTIC_RETRIEVAL": "VALIDATED",
        "HYBRID_RAG": "KEEP_EXPERIMENTAL",
        "VECTOR_RETRIEVAL": "INCONCLUSIVE",
        "ONTOLOGY_GRAPH_INTEGRATION": "PARTIAL",
        "AUTOMATED_SOURCE_DISCOVERY": "PARTIAL",
        "INCREMENTAL_INGESTION": "PARTIAL",
        "AUTOMATED_KNOWLEDGE_PUBLICATION": "CONTROLLED",
        "CONTINUOUS_EVALUATION": "PARTIAL",
        "NEMOTRON_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "JEV_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "END_TO_END_SCIENTIFIC_ANSWERS": "PARTIAL",
        "INDEPENDENT_SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
        "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    write_json("decisions_v1", {"decisions": decisions, "independent_reviewer": None})
    reviewer = []
    for case in cases:
        claims = case.get("synthesis", {}).get("selected_claims", [])
        # Stratified by query, scientific type and applicability; no duplicate review per path.
        seen = set()
        sample = []
        for claim in claims:
            key = (claim["epistemic_type"], claim.get("relationship_status"))
            if key not in seen:
                sample.append(claim)
                seen.add(key)
        reviewer.append(
            {
                "question": case["question"],
                "case_id": case["case_id"],
                "intent": case["intent"],
                "policy": case["context_policy"],
                "answer": case["answer"],
                "claims": sample,
                "reviewer": None,
                "relevance": None,
                "support": None,
                "completeness": None,
                "scientific_usefulness": None,
            }
        )
    write_json(
        "review_packet_v1",
        {"cases": reviewer, "source_pool": f"artifacts/{PREFIX}_source_pool_v4.json"},
    )

    architecture = """# Integrated architecture and synthesis

The public Phase3AssistantService still uses QueryIntentV2, SemanticRegistry,
project_legacy and the native executor. EvidenceBundle remains the common boundary.
No second graph, QueryIntentV3 or new scientific vocabulary was introduced.
The existing context layer verifies scoped source statements without rewriting run facts.
FTS5/BM25 remains enabled; existing vector components were evaluated separately.

`SCIENTIFIC_SYNTHESIS_ENABLED=true` enables bounded statement selection and compact rendering.
`SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED=true` enables verified applicability.
`NEMOTRON_SCIENTIFIC_SELECTION_ENABLED=true` enables optional bounded model selection;
`NEMOTRON_SCIENTIFIC_SYNTHESIS_ENABLED=true` additionally requests proposed claim text.
All new model stages are experimental, default off, with deterministic fallback.
V1 and the previous native renderer remain available.

Core implementation: services/scientific_synthesis.py, services/phase3.py,
services/native.py, llm/scientific_selection.py, models/GroundedClaim.
Sources, exact support spans, effective conditions, scientific entities, epistemic
types, scope limits and membership paths stay inspectable in the complete bundle.
"""
    report("SYNTHESIS", architecture)
    report(
        "CLAIM_GROUNDING",
        """# Claim grounding

Validation enforces exact supplied statements or complete documentary paragraphs,
source identity, evidence references, experimental identity, numbers and quantities,
epistemic type, effective context and unchanged graph paths. This is conservative
contract validation, not general semantic entailment or independent scientific review.
Unsupported fluent paraphrases are rejected; exact supported statements remain available.
Conditions and reported source quantities are not presented as observed outcomes.
Documentary quotations remain DOCUMENTARY, not DIRECT experimental facts.

Tests include a valid citation with wrong experimental scope, altered numbers,
negation, type alteration and missing source support. Full proposed model outputs
and rejection reasons are in generative_synthesis_v1.json; reviewers remain blank.
""",
    )
    report(
        "EVIDENCE_SELECTION",
        """# Selection and non-redundancy

Scientific statement identity includes source support, subject and epistemic type.
Duplicate graph paths do not create duplicate displayed findings. Distinct experiments
are not collapsed simply because they share a publication. Quantities are grouped by
source property and execution; full omitted evidence remains in EvidenceBundle.
Selection is question-dependent but lexical topical matching can still admit related
background before a more useful finding. Independent usefulness remains unmeasured.
""",
    )
    report(
        "COMPARISONS",
        """# Explicit constraints, preferences and comparisons

Unspecified gravity is a ranking/presentation preference, never a mandatory condition.
Explicit conditions govern DIRECT, while other applicable findings remain RELATED.
Normal-gravity overrides and comparison groups are exercised through the public V2 service.
Effective per-statement contexts are rendered, not blanket campaign statements.
The PMMA rod caption reports both 1g and microgravity, but 1g natural convection at
21% oxygen differs from the microgravity results averaged over flow and oxygen.
No isolated gravity-causality conclusion is justified by that comparison.
Saffire table geometry is retained as the original source field, not reconciled with
potentially different documentary specimen dimensions. This discrepancy needs review.
""",
    )
    report(
        "RAG_AUDIT",
        """# Actual retrieval and hybrid pilot

Existing capabilities: SQLite FTS5 with BM25, registry metadata eligibility,
ontology entity resolution, native graph constraints and traversals, verified
context scope, passage support and existing NVIDIA embedding/vector cache components.
No replacement of lexical retrieval or the native executor was made.

The bounded pilot compares A lexical, B vector, C graph, D lexical/vector,
E lexical/graph, F lexical/vector/graph and G verified-context hybrid at final k=5.
45 stratified source units, 12 questions and two representations (text; section/title)
share a frozen corpus. Two paraphrase graph cases were NOT_RUN, explicitly recorded.
G uses contextual graph results, not a newly evaluated model reranker.
Independent Precision@5, Recall and nDCG are null: no judged relevance universe exists.
Vector result changes and cosine scores are not evidence of scientific improvement.
""",
    )
    report(
        "VECTOR_DECISION",
        """# Embedding decision

The existing `nvidia/nemotron-3-embed-1b` provider was used, not the generative model.
Fresh inference processed 12 query, 45 text and 45 section inputs in seven bounded
requests. Only the last batch usage per embedding operation was exposed: 3,407
tokens is an available lower bound, not a complete bill. No price or recurring cost
is asserted. The v2 comparison is historical embedding replay, not fresh inference.
Vectors and checksums remain in local indexes/registry, not domain RDF.
Repeated sync changed zero vectors and did not rewrite unchanged files.
Table-header and fully context-augmented representation evaluation remains incomplete.
Global vector adoption is INCONCLUSIVE; no new recurring embedding job was installed.

Provider documentation: https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-embed-1b-infer
""",
    )
    report(
        "DISCOVERY",
        """# NASA discovery and acquisition

The existing NTRSAdapter now uses verified public citation search, metadata and
official PDF download paths. Twelve metadata records were discovered; ontology
vocabulary hints are reviewable, not automatic relevance certification.
PSI authentication/access was not bypassed and no unverified API was invented.
ACME 20210015913 acquisition was quarantined: its retrieved one-page PDF was
image-only, with no extractable text. OCR remains an explicit missing capability.
NASA 20260003546, Risks of Depress as a Fire Suppression Technique in Spacecraft,
was acquired and published under a document/provenance-only contract (12 pages).

Official interfaces: https://ntrs.nasa.gov/api/openapi/
and https://www.sti.nasa.gov/docs/20221122_OpenAPI_Documentation.pdf
""",
    )
    report(
        "INGESTION",
        """# Incremental ingestion and operation

Content-addressed append-only raw files, metadata/content/contract digests and version
records make updates repeatable. Unchanged metadata under the same extraction contract
skips download, parsing and index rebuild; `refresh` can inspect remote content explicitly.
Content changes preserve both versions; superseded sources leave active retrieval.
Publication of document, page, locator, citation and FTS records is transactional.
Malformed PDFs are quarantined before persistent source publication.
Rollback archives active publication, preserves historical citation resolution/raw files,
and restores the previous eligible version. Tests cover changed content at identical metadata.
Scientific facts are not automatically published by this document acquisition contract.

Runnable commands from the repository:

```bash
uv run python scripts/maintain_knowledge.py discover --query 'microgravity combustion'
uv run python scripts/maintain_knowledge.py dry-run --nasa-id 20260003546
uv run python scripts/maintain_knowledge.py controlled-update --nasa-id 20260003546
uv run python scripts/maintain_knowledge.py review-pending
uv run python scripts/maintain_knowledge.py validation-only
```

`--interpret` optionally proposes context with one bounded Nemotron request and staging.
Scheduling examples in ops/ are verified examples, not installed services.
Discovery does not yet automatically select scientific eligibility for bulk ingestion.
""",
    )
    report(
        "ONTOLOGY_ALIGNMENT",
        """# Ontology and graph publication

The new source is available through the existing native Document/Publication projection
and public V2 service, with registry-resolvable page citations. No experimental fact,
causal relation, recommendation or normative safety conclusion was canonized.
New ambiguous material/scope interpretations remain staged. Previously validated
context scopes still link BASS-II and Saffire-I runs through approved membership.
Automatic new-source experiment/observation/conclusion publication lacks sufficiently
reviewed extraction contracts; source-to-document-graph is operational, autonomous
source-to-experimental-fact-graph remains partial.
""",
    )
    report(
        "REVIEW_QUEUE",
        """# Review prioritization

Staging deduplicates semantic proposals, preserves original model payloads, and records
current validation state separately. Normative/risky language receives elevated priority.
An exact citation is not sufficient: declarative proposed-value aliases must be anchored
in support spans; entity/group scope remains review-required after lexical validation.
One Nomex proposal is staged; no new experimental membership has been scientifically
approved. The stratified review packet samples claim types and applicability per query,
not every duplicate graph path. Independent reviewer fields are null.
""",
    )
    report(
        "CONTINUOUS_REGRESSION",
        "# Fresh engineering gates\n\n```json\n"
        + json.dumps(quality, indent=2)
        + "\n```\n\nThe full quality gate is a runnable separate evaluation command, not yet an atomic gate for every unattended discovery cycle. Publication currently gates registry integrity, not all answer regressions. All 1,050 frozen historical digests are checked. Historical parity and dynamic suites were freshly executed in native_checks_v1; they are not promoted to independent scientific accuracy. The approximately 72,960 warnings originate in rdflib Dataset.default_context deprecation, not 72,960 scientific failures; no blanket warning suppression was introduced.",
    )
    report(
        "NEMOTRON",
        """# Fresh model evaluation

Seventeen generative attempts across all retained versions: twelve bounded selection
calls, three context attempts (two timed out) and two synthesis calls. Model receipts,
latency and available token usage are preserved in model_inventory_v1.json.
Selection removed unrelated background in the airflow case but recovered no additional
DIRECT-capable question beyond validated deterministic context. This is technical
selection benefit, not independently adjudicated scientific usefulness.
The successful fresh new-source context call proposed four relations: fabricated or
altered spans were rejected, an unsupported microgravity value was subsequently rejected,
and a source-backed Nomex mention remains staged with unresolved experimental scope.
No newly verified experimental context was recovered from this source.
Exact-statement synthesis acceptance is not demonstration of flexible paraphrase entailment.
New-source context interpretation therefore has measurable errors and incremental value
remains INCONCLUSIVE. No unlimited agent loop or model change occurred.
""",
    )
    report(
        "JEV",
        "# Jev advisory\n\nZero fresh Jev calls in this campaign. Existing integration and credentials remain untouched. Its incremental value is INCONCLUSIVE; model agreement would not establish scientific truth.",
    )
    answer_text = (
        "# Actual scientist-facing V2 results\n\nSame frozen source snapshot; candidate budget 8, documentary pool 32.\n\n```json\n"
        + json.dumps(comparison, indent=2)
        + "\n```\n\nThese counts measure technical DIRECT coverage, not independently reviewed answer correctness. Current final rollback/source-filter fixes are separately regression-tested; the v4 benchmark receipt records the synthesis implementation at execution time.\n"
    )
    for case in cases[:10]:
        a = baseline[case["case_id"]]
        answer_text += f"\n## {case['question']}\n\nBaseline: {a['word_count']} words; integrated: {case['word_count']} words.\n\n"
        answer_text += (
            "QueryIntentV2: `" + json.dumps(case["intent"], separators=(",", ":")) + "`.\n\n"
        )
        answer_text += f"Classification: {len(case['direct_ids'])} DIRECT and {len(case['related_ids'])} RELATED identities. Sources: {', '.join(case['source_ids'])}.\n\n"
        answer_text += case["answer"] + "\n\n"
        for claim in case.get("synthesis", {}).get("selected_claims", [])[:2]:
            path = [
                {
                    "statement_id": p.get("statement_id"),
                    "membership_paths": p.get("membership_paths"),
                    "provenance_path": p.get("provenance_path"),
                }
                for p in claim.get("graph_paths", [])
            ]
            answer_text += (
                "Support and applicable path (full exact spans remain in the case receipt):\n\n```json\n"
                + json.dumps(
                    {
                        "claim_id": claim["claim_id"],
                        "evidence_ids": claim["evidence_ids"],
                        "graph_paths": path,
                    },
                    indent=2,
                )
                + "\n```\n"
            )
    report("ANSWERS", answer_text)
    report(
        "FINAL_DECISION",
        "# Final adoption and remaining gaps\n\n"
        + "\n".join(f"`{key} = {value}`\n" for key, value in decisions.items())
        + "\n\nIndependent relevance/support/usefulness reviews remain absent. Unresolved conceptual acrylic/PMMA identity, explicit open-question scope, observation-to-conclusion links, source geometry reconciliation and new-source experimental scope must not be filled using model general knowledge. Existing gravity recovery (68 BASS-II + 2 Saffire-I runs; 335 other executions unresolved) is reused and freshly exercised, not a new autonomous recovery. There are zero new verified experimental gravity links, one rejected new-source microgravity proposal and no unsupported canonical publication. The vector pilot and autonomous scientific extraction/publication remain incomplete, despite working document acquisition, idempotence, staging and public query retrieval. Phase 4 was not started.\n\nSee ANSWERS_V1, model inventory, review packet, quality_v2 and artifact index for exact executions and limitations.",
    )

    # Scan only task-owned deliverables, never serialize credential values.
    from nasa_fire_ai.config import Settings

    settings = Settings()
    secrets = [value for value in (settings.nvidia_api_key, os.getenv("TYPESAFE_API_KEY")) if value]
    paths = list((ROOT / "artifacts").glob(f"{PREFIX}*")) + list(
        (ROOT / "docs").glob("PHASE3C_CONSOLIDATION*")
    )
    paths = [
        path
        for item in paths
        for path in ([item] if item.is_file() else item.rglob("*"))
        if path.is_file()
    ]
    leaks = [
        str(path.relative_to(ROOT))
        for path in paths
        if any(value.encode() in path.read_bytes() for value in secrets)
    ]
    write_json(
        "secret_exclusion_v1",
        {"checked_files": len(paths), "credential_value_hits": leaks, "env_included": False},
    )
    if leaks:
        raise RuntimeError("Credential exclusion gate failed")
    index = []
    for pattern, parent in ((f"{PREFIX}*", "artifacts"), ("PHASE3C_CONSOLIDATION*", "docs")):
        for item in sorted((ROOT / parent).glob(pattern)):
            for path in [item] if item.is_file() else sorted(item.rglob("*")):
                if path.is_file():
                    raw = path.read_bytes()
                    index.append(
                        {
                            "path": str(path.relative_to(ROOT)),
                            "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "records": len(json.loads(raw)) if path.suffix == ".json" else None,
                        }
                    )
    write_json(
        "artifact_index_v1",
        {
            "files": index,
            "files_count": len(index),
            "independent_review": None,
            "index_self_hash": "excluded to avoid recursive digest",
        },
    )
    print(
        json.dumps({"reports": 15, "indexed_files": len(index), "decisions": decisions}, indent=2)
    )


if __name__ == "__main__":
    main()
