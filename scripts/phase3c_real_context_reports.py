"""Assemble reports from actual versioned receipts, preserving blank expert labels."""

import collections
import json
import re
from pathlib import Path

import phase3c_real_context as pilot

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
DOC = ROOT / "docs"
PREFIX = "phase3c_real_context"

DECISIONS = {
    "MICROGRAVITY_DEFAULT_POLICY": "ADOPT",
    "REAL_SOURCE_CONTEXT_EXTRACTION": "PARTIAL",
    "BASS_II_CONTEXT_APPLICABILITY": "VERIFIED",
    "SAFFIRE_I_CONTEXT_APPLICABILITY": "VERIFIED",
    "MIXED_GRAVITY_EXCEPTION_HANDLING": "VALIDATED",
    "NON_GRAVITY_CONTEXT_REASONING": "PARTIAL",
    "SCIENTIFIC_SCOPE_RESOLUTION": "KEEP_EXPERIMENTAL",
    "ONTOLOGY_GRAPH_INTEGRATION": "PARTIAL",
    "NEMOTRON_CONTEXTUAL_VALUE": "INCONCLUSIVE",
    "JEV_ADVISORY_VALUE": "INCONCLUSIVE",
    "END_TO_END_CONTEXTUAL_REASONING": "PARTIAL",
    "SCIENTIFIC_ATTRIBUTION": "REVIEW_REQUIRED",
    "INDEPENDENT_SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
    "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
    "READY_FOR_PHASE_4": "NO",
}


def read(name, version="v8"):
    return json.loads((ART / f"{PREFIX}_{name}_{version}.json").read_text())


def save(name, payload):
    with (ART / f"{PREFIX}_{name}_v11.json").open("x") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")


def doc(name, title, body):
    with (DOC / f"PHASE3C_REAL_CONTEXT_{name}_V1.md").open("x") as file:
        file.write(f"# {title}\n\n{body.strip()}\n")


def main():
    data = read("applicability")
    answers = read("answers", "v10")
    comparison = read("comparison", "v10")
    audit = read("gravity_audit", "v10")
    integrity = read("integrity")
    identities = read("identity_round_trips")
    assert identities["count"] == 70
    full_source_checks = read("full_source_validation", "v13")
    assert full_source_checks["literal_shacl"] and not full_source_checks["csv_errors"]
    graph_audit = read("graph_relation_audit", "v14")
    model = read("model_validation", "v5")
    sources = read("answer_sources", "v10")
    live = [json.loads(p.read_text()) for p in ART.glob(f"{PREFIX}_live_*_v[34].json")]
    accepted = [r for r in model["cases"] if not r["reasons"]]
    rejected = [r for r in model["cases"] if r["reasons"]]
    by_dimension = collections.Counter(s["context_type"] for s in data["statements"])
    groups = sorted({s["scope_entity"] for s in data["statements"]})
    exceptions = [s for s in data["statements"] if s["exceptions"]]
    pytest_log = (ART / f"{PREFIX}_pytest_v14.txt").read_text()
    test_result = re.search(r"(\d+) passed, (\d+) warnings in ([\d.]+)s", pytest_log)
    if not test_result:
        raise RuntimeError("final fresh test suite has not passed")
    units = read("source_units")["units"]
    model_usage = collections.Counter()
    for call in live:
        usage = call.get("usage") or {}
        for field in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            model_usage[field] += usage.get(field, 0)
    summary = {
        "sources": len({u["source_id"] for u in units.values()}),
        "source_units": len(units),
        "context_statements": len(data["statements"]),
        "validated_statements": len(data["statements"]) - len(integrity["context_rejections"]),
        "context_dimensions": dict(by_dimension),
        "linked_scopes": groups,
        "explicit_exclusions": len(exceptions),
        "pilot_identities": len(audit["cases"]),
        "query_candidate_pairs": len(audit["pairs"]),
        "before_unknown": audit["before_unknown"],
        "after_unknown": audit["after_unknown"],
        "unknown_native_runs_outside_pilot": graph_audit["context_statuses"]["UNKNOWN"],
        "verified_contextual_recoveries": audit["recovered"],
        "fresh_model_calls": len(live),
        "schema_valid_calls": sum(bool(r.get("proposals")) for r in live),
        "validated_model_proposals": len(accepted),
        "rejected_model_proposals": len(rejected),
        "model_newly_verified_relationships": 0,
        "model_available_usage": dict(model_usage),
        "independent_judgments": 0,
        "scientific_precision": None,
        "automated_tests": int(test_result[1]),
        "warnings": int(test_result[2]),
        "csv_cells_verified": full_source_checks["csv_cells_checked"],
        "physical_pdf_locators_verified": len(full_source_checks["pdf_locations"]),
        "decisions": DECISIONS,
    }
    save("summary", summary)
    save(
        "decisions",
        {
            "fields": DECISIONS,
            "independent_reviewer": None,
            "review_date": None,
            "phase4_started": False,
        },
    )
    save(
        "review_packet",
        {
            "answer_traces": f"artifacts/{PREFIX}_answers_v10.json",
            "source_pool": f"artifacts/{PREFIX}_answer_sources_v10.json",
            "context_statements": f"artifacts/{PREFIX}_applicability_v8.json",
            "gravity_paths": f"artifacts/{PREFIX}_gravity_audit_v10.json",
            "model_proposals": f"artifacts/{PREFIX}_model_validation_v5.json",
            "cases": [
                {
                    "case_id": c["case_id"],
                    "variant": c["variant"],
                    "question": c["question"],
                    "expert_relevance": None,
                    "expert_scope": None,
                    "expert_attribution": None,
                    "expert_answer_completeness": None,
                    "reviewer": None,
                    "notes": None,
                }
                for c in answers["cases"]
            ],
            "labels_are_not_fabricated": True,
        },
    )
    table = "| Configuration | Questions with DIRECT | DIRECT records | RELATED records | Resolver invoked |\n|---|---:|---:|---:|---:|\n"
    for label, values in comparison["configurations"].items():
        table += f"| {label} | {values['queries_with_direct']}/15 | {values['direct_records']} | {values['related_records']} | {values['resolver_invoked_queries']}/15 |\n"
    decisions_text = "\n".join(f"{key} = {value}" for key, value in DECISIONS.items())
    doc(
        "EXTRACTION",
        "Real NASA document context extraction",
        f"""
Four existing NASA sources evaluated; no new downloads and no raw edits. Registered {len(units)} exact source units through the existing Evidence Registry. Validated {len(data["statements"])} statements across {len(groups)} distinct scopes with typed membership paths. The baseline 213-test report was verified by fresh execution before changes; final tests are {test_result[1]} passing. Previous historical 207-test and 70/342 reports are not presented as fresh execution receipts.

Sources: NTRS 20210011385 (BASS-II Summary Report), 20160000593 (BASS-II poster), 20170008805 (Saffire results), 20205007829 (fire-suppression presentation, physical PDF page 16). Source IDs, original text, source offsets, checksums, sections, table rows and citations are in `artifacts/{PREFIX}_source_units_v8.json`. Structure reconstruction retains section transitions; extraction used bounded, deliberately selected real-source windows and source-specific pilot assembly, not autonomous whole-corpus interpretation.

The first extraction selected appended PDF bookmarks instead of the actual Appendix A and left 68 BASS identities UNKNOWN. That failed receipt v1 is preserved; v2 selects the actual Appendix A after printed page 103 and verifies Test ID AND Sample # against the structured table. v3 adds the physical-PDF intervention and question. v6 had a shallow-copy scope aliasing defect detected by tests; v8 fixes it with independent statement data. v3 and v8 answer comparisons are intermediate; v10 is authoritative. Operational index: `data/index/scientific_context_v2.json`; v1 is superseded, not silently overwritten.

Statements by dimension: {dict(by_dimension)}. Scientific observations, interventions, conclusions and a research question are separately typed source records, not measurements or inferred recommendations. Extraction remains PARTIAL: reproducible engineering pilot, not independently reviewed general scientific extraction.
""",
    )
    doc(
        "POLICY",
        "Microgravity-first end-to-end policy",
        """
The existing V2 experimental service applies preference at documentary selection (32 candidates, final 8) and presentation of verified scientific candidates. Microgravity is a ranking preference only; unspecified-gravity queries can retain terrestrial comparisons and unknown conditions. Explicit normal-gravity constraints and comparative queries suppress the default preference. No UNKNOWN field is rewritten and canonical source values are unchanged.

`Phase3AssistantService.answer_query` routes through the native V2 executor only with `NATIVE_V2_QUERY_ENABLED=true`. Enable `SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED=true` for source-backed applicability. `MICROGRAVITY_FIRST_RETRIEVAL_ENABLED` defaults true. Context and native V2 default false. Live interpretation also requires `NEMOTRON_CONTEXT_INTERPRETATION_ENABLED=true` and an explicit `CONTEXT_QUERY_LIVE_CALL_BUDGET` (default 0, clamped to 2). `.env` is reused through existing Settings; explicit environment values win. Keyless execution remains deterministic. PSI publication and FLEX correction flags were disabled in controlled comparisons.

QueryIntentV2 remains the execution contract; the V1 object in the app response is only its existing display envelope. V1 rollback is unchanged when native V2 is off. Actual app/service, default PMMA, explicit microgravity, normal gravity and grouped comparison tests exercise these boundaries. In this 15-case set B changes no structured recoveries over A; preference alone is not a scientific fact.
""",
    )
    doc(
        "SCOPE",
        "Scientific scope and exception validation",
        """
Each statement retains context dimension, existing ontology predicate/property, exact value, entities, quantifier, scope, source statement, support spans, evidence IDs, graph/membership paths, exclusions, conflicts and authority. Separate source spans establish the context and group identity without requiring the same condition to recur in a local row.

Execution/local > subgroup > campaign > document. SOME, UNSPECIFIED, THEORETICAL and unverified conditional statements do not inherit. Explicit source-group exclusions prevent flight context from crossing to ground controls. Equally applicable incompatible statements remain CONFLICTED, regardless of model priority or lexical ranking. Missing conditions are UNKNOWN, not contradicted. Existing six scope tests plus real end-to-end and adversarial tests cover these decisions.

Two real source exclusions are retained: terrestrial PMMA rod comparisons and terrestrial silicone comparisons. These are source-backed group partitions represented as exclusions; not claims that NASA used an internal software exception vocabulary. Wrong group/document scope, unrelated run, fabricated ID, wrong gravity, limited quantifier, invented exceptions and conditional proposals are rejected even with a correct citation. Whitespace/NFC is reversible; changed words or numbers are not.

Validation is technical source applicability, not independent scientific relevance approval. Novel model interpretations lacking independently verifiable membership/scope remain staged. No indiscriminate transitivity and no program-to-experiment property inheritance.
""",
    )
    doc(
        "BASS_II",
        "BASS-II contextual applicability",
        """
68 historical BASS-II identities have source-backed microgravity applicability. Paths connect each native run's PSI-25 evidence and belongsToInvestigation relation to exact Appendix A Test ID and Sample # membership and the BASS-II report's ISS/microgravity campaign declaration. PSI-25 local rows do not need to repeat gravity. The ISS platform and Microgravity Science Glovebox/wind tunnel are documented in the poster Approach section.

The PMMA-film observation is linked to its explicitly labeled PMMA study, not all campaign specimens. PMMA rod ground and flight results remain separate. Ground rods use natural convection at 21% oxygen; flight comparison values average airflow and oxygen. No imposed airflow velocity is inferred from ground natural convection. The native index contains 129 BASS run rows, while the report describes 126 tests; this discrepancy is not silently repaired. Only the 68 pilot run memberships were individually audited; broader completeness remains unresolved.

Author observations and run configuration identities are different evidence types. Recovering run gravity does not establish suppression outcomes for every run. Full original rows, quoted Appendix spans and graph paths: `artifacts/phase3c_real_context_gravity_audit_v10.json`.
""",
    )
    doc(
        "SAFFIRE_I",
        "Saffire-I contextual applicability",
        """
Both PSI-98 pilot executions have verified applicable microgravity context. The presentation identifies Saffire-I concurrent burning for 420 s followed by an opposed contingency test on remaining material, with a caption explicitly comparing concurrent and opposed microgravity burning. Run fingerprints join the 420/Concurrent and 70/Opposed structured records to that identified test group.

Actual experiment platform: the unmanned resupply vehicle after it departs the ISS; an investigation's ISS metadata is not the location of the combustion test. Exact source language is preserved rather than creating a new platform relation from metadata. Initial oxygen 21.7%, airflow 20 cm/s and specimen width 40.6 cm remain source quantities with original units. The source says about 10% of fuel remained for the contingency; the original 94 cm specimen length is not asserted to be the intact remaining specimen length for the second burn.

Saffire-II silicone controls are distinct from Saffire-I; their context is not propagated to PSI-98 runs. Technical source/group linkage is VERIFIED, independent attribution review remains required.
""",
    )
    doc(
        "MIXED_GRAVITY",
        "Real mixed-gravity exception handling",
        """
Two real comparisons were evaluated: BASS-II PMMA rods and Saffire-II silicone. Both source documents discuss flight research alongside actual terrestrial tests. Ground PMMA rods are labeled 1g in natural convection and at 21% oxygen; microgravity values are averaged across flow and oxygen, so the comparison is not a matched-condition causal estimate.

Silicone source sections distinguish normal-gravity tests with differing thicknesses from the flight results: none of the flight silicone samples sustained spreading after ignition ended. The source's conclusion is restricted to tested flow speeds. Potential silica deposition/buoyancy explanations remain hypotheses, not measured causal observations. The source also says microgravity behavior 'was sought'; this objective alone is not used as execution evidence. Nemotron's proposal relying on that prospective sentence was rejected.

Explicit normal-gravity requests return the verified terrestrial records. Comparative questions preserve both groups. The two source exclusions are exercised through native queries and resolver tests. Technically VALIDATED within these selected sources; no independent scientific judgment is claimed.
""",
    )
    doc(
        "NON_GRAVITY",
        "Non-gravity scientific context",
        """
Eight material statements maintain PMMA-film, PMMA-rod, Saffire-IV PMMA and silicone identity across explicitly linked source units. Silicone is a literal source identity instantiated with the existing Material class, not a new ontology predicate or acrylic equivalence. Ground PMMA oxygen 21% and documented wind-tunnel/MSG apparatus are typed contexts; numbers and units are unaltered and apply only to linked scopes.

The Saffire-IV source (NTRS 20205007829, physical page 16) establishes PMMA, flow interruption for 20 seconds, non-extinction and renewed growth after flow returned. Separate Intervention and ReportedObservation records link to the same source-identified test through typed concerns membership. No execution gravity is assigned to this slide; the explicit microgravity PMMA question therefore receives this record only as RELATED with unknown gravity.

Material continuity does not extend to later SIBAL or silicone sections. A source conclusion is separately typed and its flow-speed qualification is preserved. OpenQuestion text is retained but the broad explicit-microgravity query lacks verified question-to-gravity applicability and remains documentary CONTEXTUAL, not fabricated DIRECT. Phenomenon mappings, generalized atmospheric ranges, pressure and all-domain extraction remain PARTIAL. Original source quantities are not recommendations.
""",
    )
    doc(
        "ONTOLOGY_KG",
        "Ontology and native graph integration",
        """
Reused SemanticRegistry, QueryIntentV2, native SemanticGraph/executor, original ontology predicates/classes, Evidence Registry/FTS, hierarchical interpretation and EvidenceBundle. Context dimensions and preference/exception policies are declarative registry extensions. No QueryIntentV3, parallel graph or silent ontology vocabulary.

Verified applicability is reified inside the same native RDF graph with reviewState VERIFIED_CONTEXTUAL_APPLICABILITY and resolvable evidence. Canonical accessors filter these records; only the enabled resolver supplies contextual actual values. Source identities are noncanonical. Traversal explicitly opts into verified context and remains association-only: graph distance/citation never proves causality or inheritance. Context-aware material, environment and intervention retrieval use typed paths and exact group identity. A ContextAuthority SHACL shape enforces allowed authority states and evidence references.

Canonical publication requires explicit APPROVED review; model-generated candidates cannot promote themselves. Live proposals are staged or validated against source-backed references; agreement between models is not scientific verification. Membership materialization uses already supported predicates. File locations/checksums remain solely in the evidence registry/index, not domain assertions. Observation-to-conclusion support joins are not currently verified and are deliberately downgraded to RELATED. Generic graph integration remains PARTIAL, not a complete scientific reasoning engine.
""",
    )
    calls_table = (
        "| Window | Execution | Latency ms | Error | Proposals |\n|---|---|---:|---|---:|\n"
    )
    for call in live:
        calls_table += f"| {call['input']['window']} | Fresh | {call.get('latency_ms', 0):.0f} | {call.get('error', 'none')} | {len(call.get('proposals', []))} |\n"
    doc(
        "NEMOTRON",
        "Nemotron real-context inference",
        f"""
{len(live)} fresh NVIDIA calls against actual selected NASA windows; model `nvidia/nemotron-3.5-lightning-30b-a3b`, existing configured base URL and credentials. Five initial calls failed (two timeouts, three invalid schemas); two corrective bounded calls yielded four proposals. Final deterministic validation recovered reversible whitespace in two proposals; two remain rejected (altered PMMA quotation; prospective silicone objective plus nonexact quote). No unreviewed canonical facts published.

{calls_table}

Available usage: {dict(model_usage)}. Usage/raw output unavailable for the initial failed calls; not estimated. Successful calls take approximately 2.90 and 12.34 seconds. Checkpoints retain input windows, evidence IDs, exact quotations, proposal payloads and validations. Revalidation v5 is explicitly replay of those fresh receipts, not another inference call. The schema correction used at most four proposals and 1,800 output tokens, timeout 40 s, no retries.

The two accepted proposals confirm already reconstructed source scopes. Newly verified independent relationships: 0; extra recovered evidence over C: 0. D replays the checkpoint-assisted context; live calls occurred in extraction, not in each of the 15 query requests (query budget 0). This is not an online live-versus-baseline performance claim. Novel interpretations without validated membership remain staged. Incremental Nemotron value INCONCLUSIVE; schema success is not scientific value. Jev was not called: no comparable independent advisory labels, value INCONCLUSIVE, zero fresh Jev calls.
""",
    )
    traces = []
    representative = [
        "default-pmma",
        "explicit-pmma",
        "normal-gravity",
        "saffire-conditions",
        "intervention",
        "real-exception",
    ]
    for case_id in representative:
        case = next(c for c in answers["cases"] if c["case_id"] == case_id and c["variant"] == "C")
        bundle = case["bundle"]
        context = bundle["retrieval_metadata"].get("scientific_context", {})
        path_records = [
            {
                "statement_id": s["statement_id"],
                "source_statement": s["original_text"],
                "scope": s["scope"],
                "validation_status": s["validation_status"],
                "membership_paths": s["membership_paths"],
                "evidence_ids": s["evidence_ids"],
            }
            for s in context.get("applied_statements", [])
        ]
        traces.append(
            {
                "case_id": case_id,
                "question": case["question"],
                "intent": case["intent"],
                "gravity_policy": bundle["retrieval_metadata"].get("context_policy"),
                "contexts_and_paths": path_records,
                "direct_ids": [r["id"] for r in bundle["direct_evidence"]],
                "related_ids": [r["id"] for r in bundle["related_evidence"]],
                "citations": [
                    {
                        "evidence_id": e,
                        "source_id": sources[e].get("source_metadata", {}).get("source_id"),
                        "location": sources[e].get("structured_location")
                        or sources[e].get("section"),
                        "source_text": sources[e]["text"],
                    }
                    for e in bundle["evidence_passages"]
                ],
                "answer": case["answer"],
                "independent_review": None,
            }
        )
    save(
        "representative_traces",
        {"cases": traces, "actual_native_queries": True, "not_synthetic": True},
    )
    trace_body = "Six complete real-source query-to-answer traces follow. The machine-readable version also includes every exact context statement, path, citation and blank review field: `artifacts/phase3c_real_context_representative_traces_v11.json`. Full 60-query traces: `artifacts/phase3c_real_context_answers_v10.json`.\n"
    for trace in traces:
        trace_body += f"\n## {trace['question']}\n\nQueryIntentV2 constraints: `{json.dumps(trace['intent']['entity_constraints'])}`; requested classes: `{trace['intent']['requested_information']}`. Effective gravity policy: `{trace['gravity_policy']}`.\n\nDIRECT: {trace['direct_ids']}. RELATED: {trace['related_ids']}. Native resolver invoked; source/group paths retained in the companion receipt.\n\n"
        # Full scientist-facing answers, not hand-written substitutes.
        trace_body += trace["answer"] + "\n"
    doc("ANSWERS", "Actual end-to-end scientific answers", trace_body)
    doc(
        "COMPARISON",
        "Baseline versus contextual comparison",
        f"""
A: deterministic native V2 without preference or resolver. B: preference only. C: validated source-backed scope. D: same verified corpus plus checkpointed Nemotron-assisted interpretations. E: not run. Same SQLite snapshot, 8 final documentary candidates, 32 pooled candidates; no extra NASA sources between configurations. Canonical/source normalization flags equal. 15 natural-language cases each, 60 answers total; all citation identities resolve. Counts are software outcomes, not scientific precision.

{table}

C and D are identical in DIRECT/RELATED identity sets; model-redundant relations do not earn a retrieval gain. A/B answer count 3/15 versus C/D 11/15 is a recovery measure only, not 73% accuracy. Ground and unknown-gravity PMMA remain present under default preference but are not DIRECT for explicit microgravity. Inclusive/exclusive oxygen boundaries yield 40 versus 38 DIRECT runs while source numbers are preserved. Unverified observation-to-conclusion joins have no DIRECT answer. Absent pressure evidence is not a NASA knowledge gap.

Historical pilot audit: {audit["before_unknown"]} UNKNOWN local fields → {audit["after_unknown"]} UNKNOWN within the selected 70 identities; {audit["recovered"]} verified contextual recoveries. All 342 original query-candidate pairs reclassified A/C with preserved original matrix: 163 RELATED→DIRECT, 179 RELATED→RELATED. No numeric source changes and no material-family behavior equivalence. Across all 405 native runs, 335 contextual gravity scopes remain UNKNOWN; recovery must not be generalized beyond the individually linked pilot. Independent relevance/precision remains null.
""",
    )
    doc(
        "ATTRIBUTION_FAILURES",
        "Scientific attribution failures and negative controls",
        """
Rejected model proposals: the flight-PMMA quotation changed the source wording; the flight-silicone proposal used prospective objectives and nonexact quotation. These cannot establish experimental gravity. Two accepted model proposals are redundant, not discoveries. Correct citations with wrong group, scope or run remain rejected in adversarial tests.

The Saffire-I ISS metadata is not used as the burn location. Original intact specimen dimensions do not describe remaining fuel after the concurrent burn. Source-dependent natural-convection ground comparisons are not matched-condition causal experiments. The Saffire-IV interruption source has no verified execution-gravity link, so microgravity is UNKNOWN. Graph connectivity does not establish which observations support a conclusion; the multi-hop question stays RELATED. Broad research-question gravity applicability and acrylic/PMMA exact conceptual identity are unresolved; RAG evidence remains CONTEXTUAL.

No false inheritance was found in the tested source partitions/negative software controls. This is not a zero-error scientific precision estimate: no independent reviewers supplied applicability judgments. Unrestricted whole-corpus or autonomous cross-document interpretations are unvalidated. The 68 BASS pilot IDs link through exact Test ID/sample identity; similar wording alone does not merge studies. The historical 70/342 audit is not independent gold, and tests are not scientists' approval.
""",
    )
    doc(
        "QUALITY",
        "Fresh engineering and source-integrity gates",
        f"""
Final fresh commands: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pytest -q`. {test_result[1]} tests passed, {test_result[2]} warnings. Final logs/exit receipts v14, not historical replays. Numeric 19-case fidelity is included in the fresh full suite. Existing dynamic suites reran with new output paths: 230/230 and post-freeze 125/125. Native forbidden-V1-call guard passed. Fresh 39-case V1/V2 parity: DIRECT 31/39, RELATED 37/39, evidence sets 6/39; strict historical parity remains incomplete. V1 rollback service remains default.

The existing 20-case retrieval regression ran both baseline and context: 8/8 required identity cases recovered in each, zero objective no-DIRECT failures, all citations resolve. These objective software/identity labels are not expert relevance gold.

Canonical, contextual-native, taxonomy and literal SHACL passed. Both active and isolated SQLite integrity are ok. FKs have no reported violations; the schema declares no foreign keys, so explicit source/document anti-joins also run and pass. FTS has no missing/extra identities, duplicate IDs or text mismatches; its internal integrity command passed. Snapshot has 7,226 passages; active registry has 7,225 (the snapshot retains one failed-extraction source unit not installed operationally). All 7,226 graph evidence refs resolve and ontology relation IDs are registered. All 159 final source units have exact source text/locations/checksums, all 12,758 CSV cells round-trip without error, all 278 stored physical PDF locators verify, and all 70 historical identities round-trip to verified source records. Zero context-index validation rejections. {integrity["historical_digests"]["checked"]} historical raw/canonical/gold/artifact digests checked, zero changes. API-secret scan has no matched artifact files; `.env` is not exported.

Warnings: rdflib Dataset.default_context deprecation, 233 from native semantic tests and 72,727 from scientific enrichment/pyshacl iteration; third-party API migration noise, not failed scientific assertions. Separate import-time fitz compatibility deprecation is existing PyMuPDF usage in legacy ingestion/reconstruction. Neither is suppressed. Project defects found and corrected: source-index shallow-copy membership leakage and wrong test trace-key; their unsuccessful logs remain. Repeated full-suite attempts failed due disk exhaustion, not scientific validation; only this run's disposable test SQLite copies and a zero-byte failed regression output were removed. The context fixture now excludes the unrelated 260 MB embedding cache, reducing its copy to 70 MB; original historical embedding data is untouched. Fresh subsequent execution is authoritative, not failed partial logs.
""",
    )
    doc(
        "FINAL_DECISION",
        "Real-context Phase 3C final adoption and readiness",
        f"""
Implemented and operationally exercised the existing experimental native V2 path. Real source contexts are usable without changing canonical run facts; no parallel graph, QueryIntentV3 or Phase 4. Partial decisions reflect bounded curator-prepared extraction, model schema failures/no incremental discoveries, unverified conclusion joins and absent independent review—not a missing engineering integration.

```text
{decisions_text}
```

Source-backed BASS-II and Saffire-I pilot applicability is technically verified, not independently endorsed. Microgravity preference is adopted; source interpretation, scope and graph integration stay flagged experimental. No full automatic corpus-wide adoption. Remaining dependencies: independent scientific relevance/attribution labels; broader run memberships and phenomenon semantics; validated observation-to-conclusion relations; generic source extraction beyond prepared windows; successful useful new model discoveries. Jev remains optional advisory and unmeasured.

Reproduction: `uv run python scripts/phase3c_real_context.py --extract` originally generated versioned extraction trials; use receipts v8 for the final context index, not the historic v1 trial. Final A/B/C/D evaluation invoked `phase3c_real_context.evaluate()` with VERSION v10 and the immutable isolated evidence snapshot. Quality stages: `scripts/phase3c_real_context_quality.py` (commands, integrity, regressions, identities). Outputs are create-only checkpoint receipts; choose a new output version for another run. Production opt-in: NATIVE_V2_QUERY_ENABLED=true and SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED=true; default preference is already true, API call budget defaults zero. Disable NATIVE_V2_QUERY_ENABLED for V1 rollback.

Artifact index: `artifacts/phase3c_real_context_artifact_index_v11.json`. Five-plus complete real-source answer examples are in `docs/PHASE3C_REAL_CONTEXT_ANSWERS_V1.md` and its trace receipt. Independent reviewer fields are blank. Phase 4 readiness: NO.
""",
    )
    # Each indexed checksum is computed after all payloads are complete; the
    # index cannot checksum itself without recursion.
    paths = [
        *ART.glob(f"{PREFIX}*"),
        *DOC.glob("PHASE3C_REAL_CONTEXT*_V1.md"),
        ROOT / "data/index/scientific_context_v2.json",
    ]
    expanded = []
    for path in paths:
        expanded.extend(path.rglob("*") if path.is_dir() else [path])
    entries = []
    for path in sorted(set(expanded)):
        if not path.is_file():
            continue
        count = None
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text())
                count = (
                    len(payload)
                    if isinstance(payload, list)
                    else {k: len(v) for k, v in payload.items() if isinstance(v, list)}
                )
            except json.JSONDecodeError:
                count = "INCOMPLETE_FAILED_RECEIPT"
        entries.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": pilot.digest(path),
                "counts": count,
            }
        )
    save(
        "artifact_index",
        {
            "files": entries,
            "file_count": len(entries),
            "authoritative_answers": f"artifacts/{PREFIX}_answers_v10.json",
            "authoritative_context_index": "data/index/scientific_context_v2.json",
            "authoritative_gates": f"artifacts/{PREFIX}_commands_v14.json",
            "historical_trials_preserved": True,
            "index_self_digest": "excluded to avoid recursive hashing",
            "expert_review": None,
        },
    )
    print(summary)


if __name__ == "__main__":
    main()
