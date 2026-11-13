"""Exposed regression and synthetic development evaluation; no expert gold inferred.

Only writes phase3c_related_* artifacts. Existing receipts are immutable inputs.
Model responses are historical replay with revised deterministic validation.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

from test_hierarchical_related import fixture
from test_hierarchical_related import intent as synthetic_intent

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.controlled_reasoning import (
    MAX_RERANK_CANDIDATES,
    ControlledReasoningFlags,
    _digest,
    _filter_source_constraints,
    run_ablation,
    validate_expansion,
)
from nasa_fire_ai.query.expansion_contracts import numeric_equivalence
from nasa_fire_ai.query.hierarchy import taxonomy_edges
from nasa_fire_ai.query.native import NS, execute_native
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.native import answer_native_controlled, render_native


def load(name):
    return json.loads((ROOT / name).read_text())


def rows(name):
    return [json.loads(line) for line in (ROOT / name).read_text().splitlines()]


def write(suffix, data):
    path = ROOT / f"artifacts/phase3c_related_{suffix}_v1.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")
    return str(path.relative_to(ROOT))


def fraction(n, d):
    if not d:
        return {"numerator": n, "denominator": d, "estimate": None}
    from nasa_fire_ai.evaluation.phase3c import proportion

    return proportion(n, d)


class HistoricalReplay:
    model_identity = "nvidia/nemotron-3.5-lightning-30b-a3b"

    def __init__(self, original, store, language):
        self.original, self.store, self.language = original, store, language

    def expand(self, query, intent):
        original = (
            self.original["configurations"]["B"].get("expansion")
            or self.original.get("expansion_replayed_from_first_pass")
            or {}
        )
        formulations = [
            row["query"]
            for key in ("accepted", "rejected")
            for row in original.get(key, [])
            if "query" in row
        ]
        result = {
            "accepted": [],
            "rejected": [],
            "hypotheses": [],
            "error": None,
            "execution_mode": "HISTORICAL_REPLAY_REVISED_POSTPROCESSING",
            "original_prompt": original.get("version"),
            "usage": {"replayed": True},
            "new_calls": 0,
        }
        for expanded in dict.fromkeys(formulations):
            valid, reason = validate_expansion(
                query, expanded, intent, self.store.registry, self.language
            )
            result["accepted" if valid else "rejected"].append(
                {"query": expanded, "accepted": valid, "reason": reason}
            )
            # Exposed old searches can be tested as unverified discovery, never
            # retroactively described as v2 model outputs or equivalent wording.
            if not valid and reason.startswith("added_registered_entity:"):
                result["hypotheses"].append(
                    {
                        "query": expanded,
                        "relationship": "UNVERIFIED_HYPOTHESIS",
                        "requested_concept": None,
                        "proposed_concept": None,
                    }
                )
        result["hypotheses"] = result["hypotheses"][:3]
        return result

    def rerank(self, query, intent, candidates):
        old = self.original["configurations"]["C"].get("reranking") or {}
        candidates = candidates[:MAX_RERANK_CANDIDATES]
        digest = _digest([(c["evidence_id"], _digest(c.get("text", ""))) for c in candidates])
        if digest != old.get("candidate_input_digest"):
            return {
                "judgments": [],
                "error": "INCOMPATIBLE_HISTORICAL_INPUT",
                "usage": {},
                "execution_mode": "NOT_EXECUTED",
            }
        passages = {c["evidence_id"]: c.get("text", "") for c in candidates}
        accepted = [
            j
            for j in old.get("judgments", [])
            if j["evidence_id"] in passages
            and (
                j["candidate_relevance"] not in {"HIGH", "MEDIUM"}
                or (j.get("supporting_span") and j["supporting_span"] in passages[j["evidence_id"]])
            )
        ]
        return {
            **old,
            "judgments": accepted,
            "usage": {"replayed": True},
            "execution_mode": "COMPATIBLE_HISTORICAL_REPLAY",
            "new_calls": 0,
        }


def main():
    import yaml

    registry = EvidenceRegistry(Settings().registry_path)
    store = project_legacy(ROOT, registry)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    gold = load("evals/phase3c_controlled_e2e_regression_gold_v1.json")
    originals = {
        r["case_id"]: r for r in rows("artifacts/phase3c_controlled_e2e_ablation_cases_v4.jsonl")
    }
    case_results, expansions, reranks, jev_comparisons = [], [], [], []
    review_additions, error_rows, paths, differences = [], [], [], []
    configs = ("A", "A_budget_matched", "B", "C", "D", "E")
    for case in gold["cases"]:
        started = perf_counter()
        q = QueryIntentV2.model_validate(case["expected_intent"])
        query, cid = case["query"], case["case_id"]
        A = execute_native(q, query, store, registry, hierarchical=False, relational=False)
        B = execute_native(q, query, store, registry, hierarchical=True, relational=True)
        replay = HistoricalReplay(originals[cid], store, language)
        discovery = run_ablation(
            query,
            q,
            store,
            registry,
            reasoner=replay,
            flags=ControlledReasoningFlags(
                query_expansion=True,
                contextual_reranking=True,
                selective_reranking=True,
                hierarchical_retrieval=True,
                relational_related=True,
            ),
        )
        grouped = answer_native_controlled(
            q,
            query,
            store,
            registry,
            flags=ControlledReasoningFlags(hierarchical_retrieval=True, relational_related=True),
        )
        lexical = _filter_source_constraints(registry.search(query, limit=40), q, registry)
        exact_ids = [p["evidence_id"] for p in A.bundle.evidence_passages]
        lexical_ids = list(dict.fromkeys(exact_ids + [p["evidence_id"] for p in lexical]))[:40]
        candidate_ids = {
            "A": exact_ids,
            "A_budget_matched": lexical_ids,
            "B": [p["evidence_id"] for p in B.bundle.evidence_passages],
            "C": discovery["configurations"]["B"]["candidate_ids"],
            "D": discovery["configurations"]["C"]["candidate_ids"],
        }
        candidate_ids["E"] = list(candidate_ids["D"])
        historical_jev = originals[cid]["configurations"]["D"].get("jev") or {}
        advisory = [
            j for j in historical_jev.get("judgments", []) if j["evidence_id"] in candidate_ids["D"]
        ]
        jev_comparisons.append(
            {
                "case_id": cid,
                "execution_mode": "HISTORICAL_ADVISORY_REPLAY",
                "advisory": advisory,
                "order_changed": False,
                "scientific_incremental_value": "UNESTABLISHED",
                "new_calls": 0,
                "reason": "Rhetorical class is not scientific relevance; labels are unreviewed.",
            }
        )
        expansion = discovery["configurations"]["B"]["expansion"]
        rerank = discovery["configurations"]["C"]["reranking"]
        expansions.append({"case_id": cid, **expansion})
        reranks.append(
            {"case_id": cid, "selective_policy": discovery["selective_reranking"], **rerank}
        )
        scoreable = case.get("scoreable_identity_case", False)
        required = set(case["required_evidence_ids"])
        classifications = {"A": A.bundle, **{k: B.bundle for k in ("B", "C", "D", "E")}}
        result = {
            "case_id": cid,
            "query": query,
            "intent": q.model_dump(mode="json"),
            "expected_evidence_ids": sorted(required),
            "objective_identity_case": scoreable,
            "objective_no_direct": case["expected_no_direct"],
            "review_required": case["review_required"],
            "candidate_budget_max": 40,
            "configurations": {},
            "latency_ms": {
                "A_native": A.latency_ms["total"],
                "B_native": B.latency_ms["total"],
                "synchronous_offline_evaluation": (perf_counter() - started) * 1000,
            },
            "grouped_search": grouped.execution.bundle.retrieval_metadata.get("grouped_search"),
            "rendered_answer": grouped.rendered_answer,
        }
        for name in configs:
            bundle = classifications.get(name, A.bundle)
            ids = candidate_ids[name]
            result["configurations"][name] = {
                "candidate_ids": ids,
                "required_identity_recovered": required.issubset(ids) if scoreable else None,
                "direct_entity_ids": [x["id"] for x in bundle.direct_evidence],
                "related_entity_ids": [x["id"] for x in bundle.related_evidence],
                "false_direct_on_no_direct_case": bool(
                    case["expected_no_direct"] and bundle.direct_evidence
                ),
                "new_model_calls": 0,
            }
        for item in B.bundle.direct_evidence + B.bundle.related_evidence:
            if item.get("relationship_explanation"):
                differences.append(
                    {"case_id": cid, "entity_id": item["id"], **item["relationship_explanation"]}
                )
        paths.append({"case_id": cid, **B.bundle.retrieval_metadata["hierarchical_retrieval"]})
        if case["review_required"]:
            error_rows.append(
                {
                    "case_id": cid,
                    "component": "scientific_adjudication",
                    "type": "SCIENTIFIC_RELEVANCE_PENDING",
                    "severity": "REVIEW_REQUIRED",
                }
            )
        if rerank.get("error") == "INCOMPATIBLE_HISTORICAL_INPUT":
            error_rows.append(
                {
                    "case_id": cid,
                    "component": "reranker",
                    "type": "INCOMPATIBLE_REPLAY",
                    "severity": "INFORMATIONAL",
                }
            )
        for rejection in expansion["rejected"]:
            error_rows.append(
                {
                    "case_id": cid,
                    "component": "equivalent_expansion",
                    "type": rejection["reason"],
                    "severity": "PREVENTED_CONSTRAINT_CHANGE",
                }
            )
        all_ids = list(dict.fromkeys(eid for ids in candidate_ids.values() for eid in ids))
        judgments = {j["evidence_id"]: j for j in rerank.get("judgments", [])}
        by_eid = {}
        for role, items in [
            ("DIRECT", B.bundle.direct_evidence),
            ("RELATED", B.bundle.related_evidence),
        ]:
            for item in items:
                for eid in item["evidence_ids"]:
                    by_eid.setdefault(eid, []).append(
                        {
                            "classification": role,
                            "entity_id": item["id"],
                            "conditions": item.get("relationship_explanation"),
                            "source_backed_payload": store.payload(item["id"]),
                        }
                    )
        for eid in all_ids:
            passage = registry.resolve(eid)
            if not passage:
                continue
            review_additions.append(
                {
                    "case_id": cid,
                    "original_question": query,
                    "candidate_evidence_id": eid,
                    "exact_source": registry.source_metadata(eid),
                    "evidence_text": passage["text"],
                    "location": {
                        "page": passage.get("page"),
                        "physical_pdf_page_verified": False,
                        "section": passage.get("section"),
                    },
                    "requested_constraints": q.model_dump(mode="json"),
                    "candidate_facts": by_eid.get(eid, []),
                    "current_scientific_classification": sorted(
                        {r["classification"] for r in by_eid.get(eid, [])}
                    )
                    or ["CONTEXTUAL"],
                    "taxonomy_paths": B.bundle.retrieval_metadata["hierarchical_retrieval"][
                        "receipts"
                    ],
                    "nemotron_suggested_relevance": judgments.get(eid),
                    "reranking_changed_order": candidate_ids["C"] != candidate_ids["D"],
                    "independent_reviewer_label": None,
                    "reviewer_scientific_justification": None,
                    "reviewer_authority_assessment": None,
                    "adjudication_status": "PENDING_DOMAIN_EXPERT",
                }
            )
        case_results.append(result)
    write("cases", case_results)
    write("expansions", expansions)
    write("nemotron_judgments", reranks)
    write("jev_comparisons", jev_comparisons)
    write("traversal_paths", paths)
    write("constraint_differences", differences)
    write("errors", error_rows)
    # New packet retains the original as an intact nested source, fields untouched.
    previous_packet = load(
        "artifacts/phase3c_controlled_scientific_relevance_review_packet_v2.json"
    )
    write(
        "review_packet",
        {
            "original_packet": previous_packet,
            "additions": review_additions,
            "independent_scientific_adjudication": "PENDING",
            "expert_labels_fabricated": False,
        },
    )
    write(
        "taxonomy",
        {
            "approved": [e.__dict__ for e in taxonomy_edges(store, registry)[0]],
            "staged": [e.__dict__ for e in taxonomy_edges(store, registry)[1]],
            "proposals": store.taxonomy_proposals,
        },
    )
    numeric_cases = [
        (">= 20 cm/s", "> 20 cm/s", False),
        ("<= 20 cm/s", "< 20 cm/s", False),
        ("= 10 cm/s", "= 0.10 m/s", True),
        (">= 20 cm/s", "at least 0.2 m/s", True),
        ("between 0.01 and 0.11 m/s", "from 1 to 11 cm/s", True),
        ("between 1 and 11 cm/s inclusive", "between 1 and 11 cm/s exclusive", False),
        ("0.01 ± 0.005 m/s", "1 +/- 0.5 cm/s", True),
        ("about 20 cm/s", "20 cm/s", False),
        ("0.01 ± 0.005 m/s", "0.01 m/s", False),
    ]
    numeric_results = [
        {"original": a, "expansion": b, "expected": expected, "actual": numeric_equivalence(a, b)}
        for a, b, expected in numeric_cases
    ]
    write("numeric_operators", numeric_results)
    synthetic = []
    taxonomy_shacl = True
    with TemporaryDirectory() as temp:
        neutral, er, edges = fixture(Path(temp))
        taxonomy_shacl = bool(
            validate(
                neutral.graph, shacl_graph=str(ROOT / "ontology/semantic_taxonomy_shapes.ttl")
            )[0]
        )
        for label, requested, speed in [
            ("broad", "FamilyA", None),
            ("specific", "MaterialA1", None),
            ("conditions", "MaterialA1", 0.2),
            ("ancestor", "SubfamilyA", None),
        ]:
            q = synthetic_intent(requested, speed)
            r = execute_native(q, label, neutral, er, hierarchical=True, relational=True)
            synthetic.append(
                {
                    "case_id": label,
                    "status": "SYNTHETIC_DEVELOPMENT_NOT_NASA",
                    "intent": q.model_dump(mode="json"),
                    "taxonomy": [e.__dict__ for e in edges],
                    "bundle": r.bundle.model_dump(mode="json"),
                    "rendered_answer": render_native(r.bundle),
                }
            )
    write("synthetic_fixtures", synthetic)
    from nasa_fire_ai.query.v2 import EntityConstraintV2, GenericValue, PropertyConstraintV2

    examples = []
    for label, question, q in [
        (
            "acrylic",
            "What about acrylic fires?",
            QueryIntentV2(
                targets=["ExperimentalRun"], clarification_required=True, ambiguities=["acrylic"]
            ),
        ),
        (
            "pmma",
            "PMMA combustion in microgravity",
            QueryIntentV2(
                targets=["ExperimentalRun"],
                entity_constraints=[
                    EntityConstraintV2(relation="hasMaterial", entity_id="PMMA"),
                    EntityConstraintV2(relation="hasGravityCondition", entity_id="microgravity"),
                ],
            ),
        ),
        (
            "same_material_different_conditions",
            "SIBAL Fabric at 30 cm/s airflow in microgravity",
            QueryIntentV2(
                targets=["ExperimentalRun"],
                entity_constraints=[
                    EntityConstraintV2(relation="hasMaterial", entity_id="SIBAL Fabric"),
                    EntityConstraintV2(relation="hasGravityCondition", entity_id="microgravity"),
                ],
                property_constraints=[
                    PropertyConstraintV2(
                        property_id="AirflowVelocity",
                        operator="EQ",
                        value=GenericValue(reported_value=30, reported_unit="cm/s"),
                    )
                ],
            ),
        ),
        (
            "unknown_velocity",
            "What about velocity effects?",
            QueryIntentV2(
                targets=["ExperimentalRun"], clarification_required=True, ambiguities=["velocity"]
            ),
        ),
    ]:
        answer = answer_native_controlled(
            q,
            question,
            store,
            registry,
            flags=ControlledReasoningFlags(hierarchical_retrieval=True, relational_related=True),
        )
        examples.append(
            {
                "case_id": label,
                "query": question,
                "bundle": answer.execution.bundle.model_dump(mode="json"),
                "rendered_answer": answer.rendered_answer,
            }
        )
    write("scientific_examples", examples)
    summary = {
        "status": "EXPOSED_REGRESSION_AND_SYNTHETIC_DEVELOPMENT",
        "N": len(case_results),
        "historical_baseline": load("artifacts/phase3c_controlled_e2e_ablation_summary_v4.json"),
        "configurations": {},
        "new_nemotron_calls": 0,
        "new_jev_calls": 0,
        "scientifically_reviewed_precision_at_5": {
            "numerator": None,
            "denominator": 0,
            "status": "NOT_SCOREABLE_NO_EXPERT_LABELS",
            "target": 0.90,
        },
        "related_precision_recall": "NOT_SCOREABLE_NO_REVIEWED_CANDIDATE_UNIVERSE",
        "end_to_end_usefulness": "PENDING_EXPERT_REVIEW",
        "numeric_fidelity": fraction(
            sum(r["actual"][0] == r["expected"] for r in numeric_results), len(numeric_results)
        ),
        "new_domain_taxonomy_edges": 0,
        "new_model_inference_cost": 0,
        "live_latency_and_selective_utility": "NOT_MEASURED_MISSING_RUNTIME_CREDENTIALS",
    }
    for name in configs:
        scored = [r for r in case_results if r["objective_identity_case"]]
        no_direct = [r for r in case_results if r["objective_no_direct"]]
        summary["configurations"][name] = {
            "required_identity_recovery": fraction(
                sum(r["configurations"][name]["required_identity_recovered"] for r in scored),
                len(scored),
            ),
            "false_direct_on_no_direct": fraction(
                sum(r["configurations"][name]["false_direct_on_no_direct_case"] for r in no_direct),
                len(no_direct),
            ),
            "candidate_total": sum(
                len(r["configurations"][name]["candidate_ids"]) for r in case_results
            ),
        }
    summary["latency_ms"] = {
        name: median(r["latency_ms"][name] for r in case_results)
        for name in ("A_native", "B_native", "synchronous_offline_evaluation")
    }
    summary["expansion_validation"] = {
        key: sum(len(r[key]) for r in expansions) for key in ("accepted", "rejected")
    }
    summary["reranking"] = {
        "compatible_replays": sum(
            r.get("execution_mode") == "COMPATIBLE_HISTORICAL_REPLAY" for r in reranks
        ),
        "incompatible_inputs": sum(
            r.get("error") == "INCOMPATIBLE_HISTORICAL_INPUT" for r in reranks
        ),
        "selectively_skipped": sum(
            r["selective_policy"]["reason"] == "adequate_deterministic_evidence" for r in reranks
        ),
    }
    write("benchmark_summary", summary)
    # Rerun the existing extensibility harness, redirecting every output/database.
    import phase3c_native_benchmarks as historical

    pass_number = 1
    while (ROOT / f"artifacts/phase3c_related_native_checks_v{pass_number}").exists():
        pass_number += 1
    historical.ART = ROOT / f"artifacts/phase3c_related_native_checks_v{pass_number}"
    historical.ART.mkdir(exist_ok=True)
    historical.check_freeze = lambda: None  # this iteration uses its own manifest below
    historical.dynamic()
    historical.dynamic(postfreeze=True)
    historical.parity()
    baseline = load("artifacts/phase3c_related_baseline_manifest_v1.json")["digests"]
    changed = [
        name
        for name, digest in baseline.items()
        if not (ROOT / name).exists()
        or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
    ]
    canonical = Graph().parse(ROOT / "data/canonical/graph.ttl")
    broken = sorted(
        str(eid)
        for eid in set(store.graph.objects(None, NS.evidenceRef))
        if not registry.resolve(str(eid))
    )
    integrity = {
        "synthetic_taxonomy_shacl": taxonomy_shacl,
        "historical_changed_paths": changed,
        "historical_digests_preserved": not changed,
        "canonical_shacl": bool(
            validate(canonical, shacl_graph=str(ROOT / "ontology/shapes.ttl"))[0]
        ),
        "native_shacl": bool(
            validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
        ),
        "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_violations": len(registry.db.execute("PRAGMA foreign_key_check").fetchall()),
        "broken_evidence_references": broken,
        "missing_fts_rows": registry.db.execute(
            "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL"
        ).fetchone()[0],
        "orphan_passages": registry.db.execute(
            "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL"
        ).fetchone()[0],
        "counts": {
            t: registry.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("sources", "documents", "passages", "passages_fts")
        },
        "native_graph_triples": len(store.graph),
        "native_checks_artifact_directory": str(historical.ART.relative_to(ROOT)),
        "dynamic_extensibility_rerun": True,
        "parity_rerun": True,
    }
    registry.db.execute("INSERT INTO passages_fts(passages_fts) VALUES('integrity-check')")
    integrity["fts_integrity_check"] = "PASS"
    integrity["status"] = (
        "PASS"
        if not changed
        and not broken
        and integrity["canonical_shacl"]
        and integrity["native_shacl"]
        and integrity["sqlite_integrity"] == "ok"
        and not integrity["foreign_key_violations"]
        and not integrity["missing_fts_rows"]
        and not integrity["orphan_passages"]
        else "FAIL"
    )
    write("integrity", integrity)
    write(
        "gold_adjudication_proposal",
        {
            "original_proposal": load(
                "artifacts/phase3c_controlled_gold_reconciliation_proposed_v1.json"
            ),
            "structural_contract_rationale": "QueryIntentV2.targets represents ExperimentalRun independently of requested_information epistemic classes.",
            "structural_disposition": "PROPOSED_FOR_CONTRACT_OWNER",
            "semantic_disposition": "REVIEW_REQUIRED",
            "historical_gold_modified": False,
            "approved": False,
        },
    )
    print(
        json.dumps(
            {
                "configurations": summary["configurations"],
                "latency_ms": summary["latency_ms"],
                "expansion": summary["expansion_validation"],
                "reranking": summary["reranking"],
                "integrity": integrity["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
