"""Versioned source review and full native numeric evaluation on a frozen corpus.

Run --reconstruct before corrections; --evaluate after corrections. No raw writes.
"""

import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.evaluation.phase3c import freeze_json
from nasa_fire_ai.evaluation.reconstruction import identity_record, read_json, reconstruct_passage
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import ProviderFailure
from nasa_fire_ai.query.hierarchy import constraint_explanation
from nasa_fire_ai.query.native import classify_native
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.native import answer_native, answer_native_text

ART = ROOT / "artifacts"
VERSION = "v1"
SOURCE_POOL = {}
RECORD_POOL = {}
NUMERIC_IDS = {"qi09", "qi10", "qi11", "qi34", "qi35", "qi37", "qi50"}


def write(name, value):
    freeze_json(ART / f"phase3c_fidelity_{name}_{VERSION}.json", value)


def stores():
    # Work only on a backup: graph projection has operational staging/cache writes.
    path = ROOT / "data/index/phase3c_fidelity_snapshot_v1.sqlite"
    if not path.exists():
        import sqlite3

        with (
            sqlite3.connect(
                f"file:{ROOT}/data/index/evidence.sqlite?mode=ro", uri=True
            ) as original,
            sqlite3.connect(path) as backup,
        ):
            original.backup(backup)
    evidence = EvidenceRegistry(path)
    for flag in (
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED",
        "RELATIONAL_RELATED_RETRIEVAL_ENABLED",
    ):
        os.environ[flag] = "true"
    for flag in ("PSI_STRUCTURED_PUBLICATION_ENABLED", "FLEX_SOURCE_CORRECTIONS_ENABLED"):
        os.environ[flag] = "false"
    os.environ["NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED"] = "false"
    return evidence, project_legacy(ROOT, evidence)


class ReplayInterpreter:
    def __init__(self, row):
        self.row = row

    def interpret_minimal(self, query):
        if query != self.row["query"]:
            raise ProviderFailure("replay query mismatch")
        return MinimalInterpretationV2.model_validate_json(self.row["minimal_raw_output"])


def historic_predictions():
    path = ART / "phase3c_corrective_interpreter_resolution_repair_v1.jsonl"
    return {r["case_id"]: r for r in (json.loads(line) for line in path.read_text().splitlines())}


def response_trace(response):
    result = response.execution
    bundle = result.bundle
    payload = bundle.model_dump(mode="json")
    for passage in payload["evidence_passages"]:
        SOURCE_POOL[passage["evidence_id"]] = passage
    payload["evidence_passages"] = [
        {"evidence_id": p["evidence_id"], "source_record_ref": p["evidence_id"]}
        for p in payload["evidence_passages"]
    ]
    for field in [
        "semantic_records",
        "conditions",
        "measurements",
        "experimental_observations",
        "interventions",
        "nasa_conclusions",
        "safety_implications",
        "requirements",
        "guidance",
        "design_test_criteria",
        "nasa_identified_open_questions",
        "publications",
    ]:
        refs = []
        for record in payload[field]:
            key = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
            RECORD_POOL[key] = record
            refs.append(
                {"scientific_record_ref": key, "id": record.get("id", record.get("statement_id"))}
            )
        payload[field] = refs
    return {
        "intent": result.plan.intent.model_dump(mode="json"),
        "planner_constraints": [
            c.model_dump(mode="json") for c in result.plan.intent.property_constraints
        ],
        "candidate_budget": 8,
        "direct": bundle.direct_evidence,
        "related": bundle.related_evidence,
        "bundle": payload,
        "record_pool_ref": f"artifacts/phase3c_fidelity_trace_records_{VERSION}.json",
        "source_pool_ref": f"artifacts/phase3c_fidelity_trace_sources_{VERSION}.json",
        "answer": response.rendered_answer.split("<details>", 1)[0].strip(),
        "latency_ms": result.latency_ms,
    }


def reconstruct():
    evidence, store = stores()
    review = read_json(ART / "phase3c_targeted_related_review_complete_v4.json")["candidates"]
    counts = collections.Counter(r["case_id"] for r in review)
    uses = collections.Counter(r["candidate"]["id"] for r in review)
    candidates = {r["candidate"]["id"]: r["candidate"] for r in review}
    observed = {
        "pairs": len(review),
        "queries": len(counts),
        "unique_candidates": len(candidates),
        "unique_evidence_sets": len(
            {tuple(sorted(r["candidate"]["evidence_ids"])) for r in review}
        ),
        "reuse_distribution": dict(collections.Counter(uses.values())),
        "query_distribution": dict(counts),
        "independent_labels": sum(r.get("independent_label") is not None for r in review),
        "unknown_gravity": sum(
            any(
                d["dimension"] == "hasGravityCondition" and d["status"] == "UNKNOWN"
                for d in r["candidate"]["relationship_explanation"]["dimensions"]
            )
            for r in review
        ),
        "unknown_phenomenon": sum(
            r["candidate"]["relationship_explanation"]["scientific_context"]["phenomenon_status"]
            == "UNKNOWN"
            for r in review
        ),
        "embedded_complete_sources": sum(
            bool(r["candidate"].get("source_text") and r["candidate"].get("verified_location"))
            for r in review
        ),
    }
    expected = {
        "pairs": 342,
        "queries": 9,
        "unique_candidates": 70,
        "unique_evidence_sets": 70,
        "independent_labels": 0,
        "unknown_gravity": 340,
        "unknown_phenomenon": 342,
        "embedded_complete_sources": 0,
        "reuse_distribution": {5: 68, 1: 2},
        "query_distribution": {
            "qi01": 41,
            "qi02": 41,
            "qi03": 27,
            "qi04": 27,
            "qi09": 41,
            "qi10": 41,
            "qi11": 27,
            "qi26": 27,
            "qi42": 70,
        },
    }
    write(
        "audit",
        {
            "observed": observed,
            "previous_audit": expected,
            "discrepancies": {
                k: {"expected": v, "actual": observed[k]}
                for k, v in expected.items()
                if observed[k] != v
            },
            "supplementary_materials": {
                n: [str(p.relative_to(ROOT)) for p in ROOT.rglob(n)]
                for n in [
                    "NASA_PHASE3C_AUDITORIA_TECNICA_5_ARTEFACTOS.md",
                    "NASA_PHASE3C_COLA_REVISION_70_EVIDENCIAS.csv",
                ]
            },
            "authority": "Original repository JSON recomputation; no external technical review ground truth",
        },
    )
    passages = {
        eid: reconstruct_passage(eid, evidence, ROOT)
        for c in candidates.values()
        for eid in c["evidence_ids"]
    }
    records = read_json(ROOT / "data/canonical/records.json")
    identities = [
        identity_record(c, store, records, c["evidence_ids"]) for c in candidates.values()
    ]
    source_contexts = {}
    for sid in ("psi-25", "psi-98"):
        path = ROOT / f"data/raw/psi/PSI-{sid.split('-')[1]}_metadata.json"
        data = read_json(path)
        study = data["studies"][0]
        source_contexts[sid] = {
            "raw_file": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "official_title": study["title"],
            "source_version": data.get("version"),
            "investigation_identifier": study["identifier"],
            "source_comments": study["comments"],
            "applicability": "Investigation context only; no automatic run inheritance",
        }
    write(
        "reconstruction",
        {
            "identities": identities,
            "source_records": passages,
            "investigation_contexts": source_contexts,
            "unique_identity_count": len(identities),
            "verified_source_count": sum(p["status"] == "VERIFIED" for p in passages.values()),
            "missing_sources": [eid for eid, p in passages.items() if p["status"] != "VERIFIED"],
            "independent_labels": 0,
        },
    )
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    cases = read_json(ART / "phase3c_targeted_parity_reconciliation_v4.json")["cases"]
    predictions = historic_predictions()
    baseline = []
    for c in cases:
        if c["case_id"] not in NUMERIC_IDS:
            continue
        response = answer_native_text(
            c["original_query"],
            store,
            evidence,
            language,
            ReplayInterpreter(predictions[c["case_id"]]),
        )
        baseline.append(
            {
                "case_id": c["case_id"],
                "original_question": c["original_query"],
                "interpreter_execution": "CACHED_REPLAY; historical prompt, current pre-correction resolver",
                "cached_receipt": "artifacts/phase3c_corrective_interpreter_resolution_repair_v1.jsonl",
                "cached_proposal": predictions[c["case_id"]]["minimal_raw_output"],
                "historical_frozen_intent": c["frozen_intent"],
                "trace": response_trace(response),
            }
        )
    write("numeric_before", baseline)
    print(
        {
            "audit": observed,
            "recovered": len(passages),
            "verified": sum(p["status"] == "VERIFIED" for p in passages.values()),
        },
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstruct", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--version", default="v1", choices=["v1", "v2", "v3", "v4"])
    args = parser.parse_args()
    global VERSION
    VERSION = args.version
    if args.reconstruct:
        reconstruct()
    if args.evaluate:
        evaluate()


def evaluate():
    evidence, store = stores()
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    cases = read_json(ART / "phase3c_targeted_parity_reconciliation_v4.json")["cases"]
    before = {r["case_id"]: r for r in read_json(ART / "phase3c_fidelity_numeric_before_v1.json")}
    gold = read_json(ROOT / "evals/phase3c_numeric_gold_proposal_v1.json")["cases"]
    predictions = historic_predictions()
    numerical = []
    full_intents = {}
    for g in gold:
        response = answer_native_text(g["query"], store, evidence, language)
        trace = response_trace(response)
        trace["numeric_extraction"] = [
            numeric_trace(c, store.registry)
            for c in response.execution.plan.intent.property_constraints
        ]
        expected = g["expected"]
        actual = trace["numeric_extraction"][0] if trace["numeric_extraction"] else {}
        passed = all(actual.get(k) == v for k, v in expected.items())
        row = {
            "case_id": g["case_id"],
            "original_question": g["query"],
            "split": g["split"],
            "expected": expected,
            "numeric_fidelity_pass": passed,
            "current": trace,
            "execution": "FRESH_NATIVE_EXECUTION; deterministic language, no external inference",
        }
        full_intents[g["case_id"]] = response.execution.plan.intent
        if g["case_id"] in NUMERIC_IDS:
            old = before[g["case_id"]]
            canonical = response.execution.plan.intent.model_copy(deep=True)
            from nasa_fire_ai.query.v2 import GenericValue, PropertyConstraintV2

            canonical.property_constraints = [
                PropertyConstraintV2(
                    property_id=expected["property_id"],
                    operator=expected["operator"],
                    value=GenericValue(
                        reported_value=expected["reported_value"],
                        reported_unit=expected["reported_unit"],
                        approximate=expected["approximate"],
                        raw_expression=actual.get("raw_expression"),
                    ),
                )
            ]
            frozen = QueryIntentV2.model_validate(old["historical_frozen_intent"])
            row["historical_frozen_current_corpus"] = response_trace(
                answer_native(frozen, g["query"], store, evidence)
            )
            row["source_reviewed_canonical"] = response_trace(
                answer_native(canonical, g["query"], store, evidence)
            )
            replay = answer_native_text(
                g["query"], store, evidence, language, ReplayInterpreter(predictions[g["case_id"]])
            )
            row["cached_model_current_resolver"] = response_trace(replay)
            row["historical_production_numeric"] = [
                numeric_trace(c, store.registry)
                for c in QueryIntentV2.model_validate(old["trace"]["intent"]).property_constraints
            ]
            row["historical_first_loss"] = (
                "LINGUISTIC_PROPOSAL_OMITS_OXYGEN"
                if g["case_id"] == "qi37"
                else "RESOLVER_REJECTS_MODEL_PROPERTY_LABEL_air flow velocity"
                if g["case_id"] == "qi10"
                else "COMPARISON_AMBIGUITY_BLOCKS_ANSWER; numeric retained"
                if g["case_id"] == "qi50"
                else "NO_LOSS_IN_CACHED_PRODUCTION_PATH"
            )
            row["historical_gold_defect"] = not bool(
                old["historical_frozen_intent"]["property_constraints"]
            )
            row["historical_probe_limitation"] = (
                "Empty linguistic proposal did not exercise numerical extraction"
            )
            row["retrieval_deltas"] = candidate_deltas(
                row["historical_frozen_current_corpus"], trace
            )
            affected = sorted(
                {
                    c["id"]
                    for t in [
                        row["historical_frozen_current_corpus"],
                        trace,
                        row["source_reviewed_canonical"],
                    ]
                    for k in ["direct", "related"]
                    for c in t[k]
                }
            )
            row["candidate_constraint_review"] = []
            for identity in affected:
                _, detail = classify_native(identity, canonical, store, related_policy=True)
                row["candidate_constraint_review"].append(
                    {
                        "candidate_id": identity,
                        "evidence_ids": store.evidence(identity),
                        "dimensions": constraint_explanation(
                            identity, canonical, store, {}, detail
                        )["dimensions"],
                        "independent_scientific_label": None,
                    }
                )
        numerical.append(row)
        print(
            {
                "case": g["case_id"],
                "numeric_pass": passed,
                "direct": len(trace["direct"]),
                "related": len(trace["related"]),
            },
            flush=True,
        )
    os.environ["NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED"] = "true"
    corrected_store = project_legacy(ROOT, evidence)
    for row in numerical:
        response = answer_native_text(row["original_question"], corrected_store, evidence, language)
        row["with_source_context_validation"] = response_trace(response)
        row["source_context_delta"] = candidate_deltas(
            row["current"], row["with_source_context_validation"]
        )
    write("numeric_results", numerical)
    reconstruct_review(evidence, corrected_store, cases, language, full_intents)
    scientific = []
    for c in cases:
        response = answer_native_text(c["original_query"], corrected_store, evidence, language)
        if c["case_id"] in {
            "qi01",
            "qi03",
            "qi09",
            "qi10",
            "qi11",
            "qi14",
            "qi18",
            "qi27",
            "qi34",
            "qi35",
            "qi37",
            "qi42",
            "qi50",
            "qi49",
        }:
            scientific.append(
                {
                    "case_id": c["case_id"],
                    "question": c["original_query"],
                    "trace": response_trace(response),
                    "citations_resolve": all(
                        evidence.resolve(p["evidence_id"])
                        for p in response.execution.bundle.evidence_passages
                    ),
                    "scientific_usefulness": None,
                    "independent_reviewer": None,
                }
            )
    write("answer_traces", scientific)
    write("trace_records", RECORD_POOL)
    write("trace_sources", SOURCE_POOL)


def numeric_trace(constraint, registry):
    value = registry.validate(constraint)
    original = constraint.value
    op = constraint.operator
    boundary = value.canonical_value
    return {
        "property_id": constraint.property_id,
        "physical_quantity": registry.properties[constraint.property_id].dimension,
        "operator": op,
        "reported_value": original.reported_value,
        "reported_unit": original.reported_unit,
        "raw_expression": original.raw_expression,
        "canonical_value": boundary,
        "canonical_unit": value.canonical_unit,
        "lower": value.lower
        if value.lower is not None
        else boundary
        if op in ["GT", "GTE"]
        else None,
        "upper": value.upper
        if value.upper is not None
        else boundary
        if op in ["LT", "LTE"]
        else None,
        "lower_inclusive": op == "GTE" if op in ["GT", "GTE"] else None,
        "upper_inclusive": op == "LTE" if op in ["LT", "LTE"] else None,
        "approximate": original.approximate,
        "tolerance": value.tolerance,
        "logical_grouping": "CONJUNCTION; disjunction requires clarification",
    }


def candidate_deltas(before, after):
    result = {}
    for kind in ["direct", "related"]:
        a = {c["id"] for c in before[kind]}
        b = {c["id"] for c in after[kind]}
        result[kind] = {
            "before": len(a),
            "after": len(b),
            "added": sorted(b - a),
            "removed": sorted(a - b),
        }
    return result


REVIEW_FIELDS = [
    "SCIENTIFIC_RELEVANCE",
    "CORRECT_RELATIONSHIP_TYPE",
    "CORRECT_EPISTEMIC_CLASS",
    "CORRECT_SCIENTIFIC_SCOPE",
    "SOURCE_PROVENANCE_VALID",
    "ANSWER_USEFULNESS",
    "REVIEWER_JUSTIFICATION",
    "REVIEWER_ID",
    "REVIEW_DATE",
]


def reconstruct_review(evidence, store, cases, language, full_intents):
    from nasa_fire_ai.query.native_interpreter import resolve_minimal

    reconstruction = read_json(ART / "phase3c_fidelity_reconstruction_v1.json")
    identities = {r["identity_id"]: r for r in reconstruction["identities"]}
    pairs = read_json(ART / "phase3c_targeted_related_review_complete_v4.json")["candidates"]
    case_map = {c["case_id"]: c for c in cases}
    packet = []
    coverage = []
    disagreements = []
    for pair in pairs:
        case = case_map[pair["case_id"]]
        intent = full_intents.get(pair["case_id"]) or resolve_minimal(
            MinimalInterpretationV2(), store.registry, language, query=pair["query"]
        )
        identity = pair["candidate"]["id"]
        status, detail = classify_native(identity, intent, store, related_policy=True)
        explanation = constraint_explanation(identity, intent, store, {}, detail)
        gravity = next(
            (
                d["status"]
                for d in explanation["dimensions"]
                if d["dimension"] == "hasGravityCondition"
            ),
            "NOT_APPLICABLE",
        )
        phenotype = explanation["scientific_context"]
        limitations = [
            "Source configuration is valid; query-specific outcome usefulness requires review"
        ]
        if gravity == "UNKNOWN":
            limitations.append("Requested gravity not established at run level")
        if not identities[identity]["actual_phenomena"]:
            limitations.append("No source-backed run-level phenomenon relation or outcome claim")
        row = {
            "pair_id": pair["case_id"] + "::" + identity,
            "query_id": pair["case_id"],
            "original_question": pair["query"],
            "original_explicit_constraints": {
                "literal_question": pair["query"],
                "numeric": [numeric_trace(c, store.registry) for c in intent.property_constraints],
            },
            "historical_interpreted_constraints": case["frozen_intent"],
            "interpreted_constraints": intent.model_dump(mode="json"),
            "evidence_identity_ref": identity,
            "source_record_refs": identities[identity]["source_record_refs"],
            "actual_conditions_ref": identity,
            "requested_vs_actual": explanation["dimensions"],
            "historical_relationship": "RELATED",
            "technical_relationship": status,
            "why_retrieved": pair["candidate"]["relationship_explanation"]["why_useful"],
            "technical_applicability": detail,
            "possible_use": "Configuration/material context only; no outcome inferred",
            "what_it_does_not_establish": limitations,
            "epistemic_type": identities[identity]["epistemic_type"],
            "source_authority": "NASA PSI archived source; exact cells verified",
            "technical_proposal_authority": "DETERMINISTIC_ENGINEERING; NOT_EXPERT_LABEL",
            "independent_review": dict.fromkeys(REVIEW_FIELDS),
        }
        packet.append(row)
        coverage.append(
            {
                "pair_id": row["pair_id"],
                "gravity_status": "VERIFIED_" + gravity
                if gravity in ["MATCH", "DIFFER"]
                else gravity,
                "gravity_source_scope": "Existing canonical run declaration"
                if gravity != "UNKNOWN"
                else "Investigation approach is available; flight-table execution scope crosswalk absent",
                "context_statement_ref": identities[identity]["investigation_id"],
                "experiment_evidence_refs": row["source_record_refs"],
                "phenomenon_request_status": phenotype["phenomenon_status"],
                "phenomenon_evidence_status": phenotype["phenomenon_evidence_status"],
                "root_cause": "A_NOT_REQUESTED"
                if phenotype["phenomenon_status"] == "NOT_REQUESTED"
                else "D_SOURCE_NOT_ESTABLISHED",
                "new_inherited_relationships": 0,
            }
        )
    write(
        "review_packet",
        {
            "pairs": packet,
            "allowed_scientific_labels": [
                "DIRECT_RELEVANT",
                "RELATED_USEFUL",
                "CONTEXTUAL_USEFUL",
                "TOPICAL_ONLY",
                "IRRELEVANT",
                "SCIENTIFICALLY_MISLEADING",
                "INSUFFICIENT_CONTEXT",
            ],
            "reconstruction_ref": "artifacts/phase3c_fidelity_reconstruction_v1.json",
            "reviewer_labels": 0,
            "source_retrieval_not_duplicated": True,
        },
    )
    write(
        "coverage",
        {
            "pairs": coverage,
            "before": {"unknown_gravity": 340, "unknown_phenomenon_status": 342},
            "after": dict(collections.Counter(r["gravity_status"] for r in coverage)),
            "phenomenon_root_causes": dict(collections.Counter(r["root_cause"] for r in coverage)),
            "source_phenomenon_unknown": sum(
                r["phenomenon_evidence_status"] == "UNKNOWN" for r in coverage
            ),
            "run_scope_context_inheritance": "NOT_ADOPTED; investigation descriptions do not uniquely identify flight-table execution population",
            "review_required_existing_saffire_gravity": "Canonical gravity cites table row lacking gravity column; confirm flight/ground identity before upgrading provenance",
        },
    )
    disagreements = [
        {
            "issue": "BASS-II flight versus ground execution scope",
            "identity_refs": sorted(k for k in identities if k.startswith("psi-25")),
            "source_context_ref": "psi-25",
            "reason": "Approach explicitly describes ISS microgravity tests; individual table runs lack environment columns. Validate population before inheritance.",
            "expert_label": None,
        },
        {
            "issue": "Saffire S1/S2 gravity provenance",
            "identity_refs": ["psi-98-S1", "psi-98-S2"],
            "source_context_ref": "psi-98",
            "reason": "Metadata describes Cygnus flight; table includes opposed S2; canonical row gravity lacks its own source column. Confirm S2 execution scope.",
            "expert_label": None,
        },
        {
            "issue": "qi18 antecedent and scientific question scope",
            "query_id": "qi18",
            "evidence_ids": ["E-safety-saffire-suppression-open-question"],
            "reason": "Incomplete these questions cannot independently identify the question content",
            "expert_label": None,
        },
    ]
    write("expert_queue", {"issues": disagreements, "independent_review_obtained": False})
    path = ART / f"phase3c_fidelity_candidate_matrix_{VERSION}.csv"
    with path.open("x", newline="") as handle:
        fields = [
            "pair_id",
            "query_id",
            "original_question",
            "evidence_identity_ref",
            "source_record_refs",
            "technical_relationship",
            "requested_vs_actual",
            "epistemic_type",
            "what_it_does_not_establish",
            *REVIEW_FIELDS,
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in packet:
            writer.writerow(
                {
                    k: json.dumps(row[k], ensure_ascii=False)
                    if isinstance(row.get(k), (dict, list))
                    else row.get(k, "")
                    for k in fields
                }
            )
    stratify(evidence, store, cases, packet)


def stratify(evidence, store, cases, packet):
    # Strata are reproducible technical selection criteria, not relevance labels.
    strata = {}

    def add(name, refs, basis):
        strata[name] = {
            "refs": refs,
            "basis": basis,
            "scientific_gold": None,
            "split": "DEVELOPMENT_SOURCE_REVIEW",
        }

    add(
        "UNKNOWN_GRAVITY",
        [
            r["pair_id"]
            for r in packet
            if any(
                d["dimension"] == "hasGravityCondition" and d["status"] == "UNKNOWN"
                for d in r["requested_vs_actual"]
            )
        ][:3],
        "Run-level source scope unresolved",
    )
    add(
        "MULTIPLE_DIFFERENCES",
        [r["pair_id"] for r in packet if len(r["technical_applicability"]["differs"]) > 1][:3],
        "Explicit constraint contradictions",
    )
    add(
        "MATERIAL_CONFIGURATION_WITHOUT_PHENOMENON",
        [r["pair_id"] for r in packet][:3],
        "Valid PSI material/configuration does not establish a requested outcome",
    )
    add(
        "CANONICAL_MICROGRAVITY_PENDING_PROVENANCE",
        ["psi-98-S1", "psi-98-S2"],
        "Existing declaration; source scope verification still required",
    )
    add(
        "NUMERIC_BOUNDARY_MATCH",
        ["qi11::psi-98-S1", "qi50::psi-98-S2"],
        "20 cm/s satisfies >=20 and =20",
    )
    add(
        "NUMERIC_BOUNDARY_CONTRADICTION",
        ["qi34::psi-98-S1", "qi35::psi-98-S2"],
        "20 cm/s fails <20 and <=10",
    )
    for name, eid in [
        ("OBSERVATION", "E-safety-saffire-observation"),
        ("SAFETY_IMPLICATION", "E-safety-saffire-suppression-risk"),
        ("INCOMPLETE_ANAPHORA", "E-safety-saffire-suppression-open-question"),
    ]:
        add(
            name,
            [eid] if evidence.resolve(eid) else [],
            "Source rhetorical function requires separate review",
        )
    add(
        "CONCEPTUAL_ENTITY_RELATIONSHIP",
        ["qi49"],
        "Experimental material overlap cannot answer equivalence",
    )
    add(
        "AMBIGUOUS_INVESTIGATION",
        ["qi08"],
        "Historical BASS/PSI-25 defect separated from current PSI-26",
    )
    add(
        "SHARED_VALIDATED_MATERIAL_FAMILY",
        [],
        "No source-reviewed family transfer added; use existing taxonomy test fixtures, not invented NASA case",
    )
    add(
        "SAME_PHENOMENON_DIFFERENT_APPARATUS", [], "Run-level phenomenon source mapping unavailable"
    )
    add(
        "VERIFIED_DIFFERENT_GRAVITY",
        [],
        "No execution-level differently-gravitating example verified in scoped 70",
    )
    add(
        "LEXICALLY_SIMILAR_IRRELEVANT",
        [],
        "Requires actual domain relevance reviewer; lexical similarity cannot supply a label",
    )
    add(
        "GENUINE_OPEN_QUESTION",
        [],
        "Anaphoric candidate is incomplete; do not manufacture a question",
    )
    add(
        "GENUINE_NO_ANSWER",
        ["qi27"],
        "No source-backed suppression outcome for requested PMMA microgravity scope currently established; no NASA knowledge-gap inference",
    )
    add(
        "CONTEXTUAL_NASA_DOCUMENT",
        ["E-safety-saffire-observation"],
        "Documentary context is scoped separately from experimental matching",
    )
    add(
        "VERIFIED_DIRECT",
        ["qi11::psi-98-S1"],
        "Technical constraint MATCH; independent scientific direct-relevance label blank",
    )
    add(
        "RELATED_ONE_EXPLICIT_DIFFERENCE",
        ["qi34::psi-98-S1"],
        "Shared physical quantity, explicit airflow bound contradiction",
    )
    write(
        "stratified_review",
        {
            "strata": strata,
            "unavailable_strata": [n for n, s in strata.items() if not s["refs"]],
            "independent_frozen_language_cases_ref": "evals/phase3c_numeric_gold_proposal_v1.json",
            "independent_scientific_test_split": "UNAVAILABLE; no independently labeled source universe",
        },
    )


if __name__ == "__main__":
    main()
