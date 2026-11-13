"""Phase-3C deterministic preparation, freeze, native stress and parity.

No historical evaluation file is modified. Gold comes from reviewed semantics,
never model predictions. Commands are independent resumable campaign stages.
"""

import argparse
import json
import random
import sys
from pathlib import Path
from unittest.mock import patch

from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.evaluation.phase3c import digest, freeze_json, latency, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.models import ConversationContext, QueryIntent
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.offline_parser import parse_query
from nasa_fire_ai.query.v2 import (
    ComparisonV2,
    EntityConstraintV2,
    GenericValue,
    PropertyConstraintV2,
    PropertyDefinition,
    QueryIntentV2,
    RelationDefinition,
    SemanticRegistry,
    v1_to_v2,
)
from nasa_fire_ai.services.pipeline import build_bundle

ART = ROOT / "artifacts"
CORE = [
    "src/nasa_fire_ai/query/v2.py",
    "src/nasa_fire_ai/query/native.py",
    "src/nasa_fire_ai/query/native_interpreter.py",
    "src/nasa_fire_ai/ingestion/generic.py",
    "src/nasa_fire_ai/ingestion/semantic.py",
    "src/nasa_fire_ai/evidence/registry.py",
    "domain/semantic_registry.yaml",
    "domain/legacy_semantic_projection.yaml",
    "domain/query_language_v2.yaml",
    "ontology/semantic_shapes.ttl",
    "ontology/shapes.ttl",
]


def native_guard():
    from contextlib import ExitStack

    stack = ExitStack()
    for target in (
        "nasa_fire_ai.services.pipeline.build_bundle",
        "nasa_fire_ai.query.matching.classify_runs",
        "nasa_fire_ai.query.v2_execution.build_bundle_from_v1_as_v2",
        "nasa_fire_ai.query.v2_execution.build_bundle_v2",
    ):
        stack.enter_context(
            patch(target, side_effect=AssertionError("forbidden compatibility execution"))
        )
    return stack


def prepare():
    source = ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json"
    reviewed = json.loads(source.read_text())
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    requested = {
        "experiments": "ExperimentalRun",
        "measurements": "Measurement",
        "observations": "ReportedObservation",
        "conclusions": "NASAConclusion",
        "publications": "Publication",
        "safety": "SafetyImplication",
    }
    safety = {
        "requirement": "Requirement",
        "guidance": "Guidance",
        "open_question": "OpenQuestion",
        "safety_implication": "SafetyImplication",
    }
    cases = []
    for case in reviewed["cases"]:
        expected = case["expected"]
        kwargs = {
            key: expected[key] for key in ("materials", "investigations", "gravity_conditions")
        }
        kwargs.update(
            {key: value for key, value in expected["numeric_constraints"].items() if value}
        )
        intent = v1_to_v2(QueryIntent(**kwargs))
        intent.operation = "COMPARE" if expected["query_mode"] == "compare" else "SEARCH"
        intent.requested_information = list(
            dict.fromkeys(
                [requested[x] for x in expected["requested_information"]]
                + [safety[x] for x in expected["safety_intents"]]
            )
        )
        intent.source_constraints = expected["source_constraints"]
        intent.unresolved_mentions = expected["unknown_terms"]
        intent.ambiguities = expected["ambiguous_terms"]
        intent.clarification_required = expected["clarification_required"]
        if len(expected["comparison_targets"]) >= 2:
            intent.comparison = ComparisonV2(operands=expected["comparison_targets"])
        reason = None
        # Historical gap declarations name generic constructs but do not provide
        # reviewed serialized field truth. Preserve this limit rather than infer gold.
        if case["review_status"] == "CONTRACT_GAP":
            reason = "REVIEWED_GAP_WITHOUT_COMPLETE_V2_FIELD_GOLD"
        if case["review_status"] == "CONVERSATIONAL_CONTEXT_GAP":
            reason = "NO_REVIEWED_CONTEXT_FIXTURE"
        context = case.get("context_fixture")
        if context:
            ConversationContext.model_validate(context)
            intent.conversation_reference = (
                expected["comparison_targets"][0] if expected["comparison_targets"] else None
            )
        valid = False
        if reason is None:
            store.registry.validate_intent(QueryIntentV2.model_validate(intent.model_dump()))
            valid = True
        cases.append(
            {
                "id": case["id"],
                "query": case["query"],
                "kind": case["kind"],
                "review_status": case["review_status"],
                "expected": intent.model_dump(mode="json"),
                "supported": valid,
                "unsupported_reason": reason,
                "context": context,
                "label_provenance": case["label_provenance"],
            }
        )
    freeze_json(
        ROOT / "evals/phase3c_queryintent_v2_gold_v1.json",
        {
            "version": "phase3c-reviewed-v1",
            "source_digest": digest(source),
            "cases": cases,
            "policy": "No unreviewed intended fields inferred from historical gap labels; gaps remain explicit.",
        },
    )
    # Intent first, deterministic surface second. These are software composition
    # fixtures; their truth concerns constraints, not NASA scientific conclusions.
    compositions = []
    for i in range(30):
        low = 0.01 + (i % 10) * 0.01
        high = low + 0.1
        material = "PMMA" if i % 2 == 0 else "SIBAL Fabric"
        ec = [
            EntityConstraintV2(relation="hasMaterial", entity_id=material),
            EntityConstraintV2(relation="hasGravityCondition", entity_id="microgravity"),
        ]
        pc = PropertyConstraintV2(
            property_id="AirflowVelocity",
            operator="BETWEEN",
            value=GenericValue(lower=low, upper=high, reported_unit="m/s"),
        )
        q = QueryIntentV2(
            targets=["ExperimentalRun"], entity_constraints=ec, property_constraints=[pc]
        )
        query = f"Find experiments using {material} in microgravity with airflow between {low:.2f} and {high:.2f} m/s"
        pattern = "two_entities_range"
        if i >= 10 and i < 20:
            q.property_constraints[0] = PropertyConstraintV2(
                property_id="AirflowVelocity",
                operator="APPROX",
                value=GenericValue(
                    reported_value=low, reported_unit="m/s", approximate=True, tolerance=0.005
                ),
            )
            query = f"Find experiments using {material} in microgravity with airflow about {low:.2f} +/- 0.005 m/s"
            pattern = "two_entities_explicit_approximation"
        elif i >= 20:
            q.source_constraints = ["psi-98"]
            q.unresolved_mentions = ["unregistered-condition"]
            query += " from psi-98 with unregistered-condition"
            pattern = "two_entities_range_source_unknown"
        store.registry.validate_intent(q)
        compositions.append(
            {
                "id": f"comp{i + 1:02}",
                "query": query,
                "expected": q.model_dump(mode="json"),
                "kind": pattern,
                "supported": True,
                "context": None,
            }
        )
    freeze_json(
        ROOT / "evals/phase3c_compositional_gold_v1.json",
        {
            "version": "phase3c-compositional-v1",
            "cases": compositions,
            "patterns": 3,
            "limitation": "30 parameterized cases, only three composition patterns; no vocabulary novelty claim",
        },
    )
    print(
        json.dumps(
            {
                "standalone": proportion(
                    sum(
                        c["supported"]
                        for c in cases
                        if not c["context"] and c["review_status"] != "CONVERSATIONAL_CONTEXT_GAP"
                    ),
                    47,
                ),
                "conversational": proportion(sum(c["supported"] for c in cases if c["context"]), 3),
            }
        )
    )


def freeze(second_pass=False):
    freeze_json(
        ART
        / (
            "phase3c_native_freeze_second_pass.json"
            if second_pass
            else "phase3c_native_freeze.json"
        ),
        {
            "version": "phase3c-native-r1" if second_pass else "phase3c-native-v1",
            "status": "FROZEN_BEFORE_HOLDOUT_SELECTION",
            "architecture_digests": {name: digest(ROOT / name) for name in CORE},
            "evaluation_digests": {
                name: digest(ROOT / name)
                for name in (
                    "evals/phase3c_queryintent_v2_gold_v1.json",
                    "evals/phase3c_compositional_gold_v1.json",
                )
            },
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "prompt": "phase3c-minimal-v1",
        },
    )


def check_freeze():
    active = ART / "phase3c_projection_repair_freeze.json"
    if not active.exists():
        active = ART / "phase3c_native_freeze_second_pass.json"
    if not active.exists():
        active = ART / "phase3c_native_freeze.json"
    frozen = json.loads(active.read_text())
    for name, expected in frozen["architecture_digests"].items():
        if digest(ROOT / name) != expected:
            raise RuntimeError(f"architecture drift after freeze: {name}")


def dynamic(postfreeze=False):
    if postfreeze:
        check_freeze()
    rng = random.Random(39017 if not postfreeze else 799837)
    registry = SemanticRegistry(relations=[RelationDefinition("FixtureRelation")])
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(
        ART
        / ("phase3c_stress_evidence.sqlite" if postfreeze else "phase3c_dynamic_evidence.sqlite")
    )
    count_numeric, count_categorical = (25, 10) if not postfreeze else (13, 7)
    rows = []
    for i in range(count_numeric + count_categorical):
        numeric = i < count_numeric
        pid = f"Fixture_{rng.getrandbits(128):032x}"
        registry.register(
            PropertyDefinition(
                pid,
                "temperature" if numeric else "none",
                "K" if numeric else None,
                datatype="numeric" if numeric else "categorical",
            )
        )
        for label, val in (
            ("low", 10 if numeric else "red"),
            ("mid", 20 if numeric else "green"),
            ("high", 30 if numeric else "blue"),
        ):
            subject = f"{pid}:{label}"
            store.add_entity(subject, "ExperimentalRun", ["E-" + subject])
            store.add_value(
                "value:" + subject,
                subject,
                pid,
                GenericValue(reported_value=val, reported_unit="K" if numeric else None),
                ["E-" + subject],
            )
            registry.entities.add("fixture-group")
            store.add_relation(subject, "FixtureRelation", "fixture-group", ["E-" + subject])
        tests = (
            [
                ("EQ", 20, {"mid"}),
                ("LT", 20, {"low"}),
                ("LTE", 20, {"low", "mid"}),
                ("GT", 20, {"high"}),
                ("GTE", 20, {"mid", "high"}),
                ("BETWEEN", None, {"mid"}),
                ("NEQ", 20, {"low", "high"}),
                ("IN", [10, 30], {"low", "high"}),
            ]
            if numeric
            else [
                ("EQ", "green", {"mid"}),
                ("NEQ", "green", {"low", "high"}),
                ("IN", ["red", "blue"], {"low", "high"}),
            ]
        )
        for op, value, labels in tests:
            v = GenericValue(
                reported_value=value,
                reported_unit="K" if numeric else None,
                lower=15 if op == "BETWEEN" else None,
                upper=25 if op == "BETWEEN" else None,
            )
            q = QueryIntentV2(
                targets=["ExperimentalRun"],
                source_constraints=[],
                entity_constraints=[
                    EntityConstraintV2(relation="FixtureRelation", entity_id="fixture-group")
                ],
                property_constraints=[PropertyConstraintV2(property_id=pid, operator=op, value=v)],
            )
            # Isolate fixtures by registered class, avoiding a benchmark-specific planner branch.
            cls = "Class_" + pid
            registry.register_target_class(cls)
            for label in ("low", "mid", "high"):
                store.add_entity(f"{pid}:{label}", cls, [f"E-{pid}:{label}"])
            q.targets = [cls]
            with native_guard():
                result = execute_native(q, pid, store, evidence)
            direct = {x["id"] for x in result.bundle.direct_evidence}
            related = {x["id"] for x in result.bundle.related_evidence}
            expected_direct = {f"{pid}:{x}" for x in labels}
            expected_related = {f"{pid}:{x}" for x in {"low", "mid", "high"} - labels}
            rows.append(
                {
                    "property_id": pid,
                    "datatype": "numeric" if numeric else "categorical",
                    "operator": op,
                    "compile": True,
                    "direct_correct": direct == expected_direct,
                    "related_correct": related == expected_related,
                    "latency_ms": result.latency_ms,
                }
            )
    class_tests = []
    for i in range(5):
        cls = f"Information_{rng.getrandbits(128):032x}"
        registry.register_target_class(cls)
        registry.register_information_class(cls)
        subject = "subject:" + cls
        store.add_entity(subject, cls, ["E-" + cls])
        with native_guard():
            result = execute_native(
                QueryIntentV2(targets=[cls], requested_information=[cls]), cls, store, evidence
            )
        class_tests.append(
            {
                "class_id": cls,
                "correct": result.plan.candidate_entity_ids == [subject]
                and result.bundle.semantic_records[0]["id"] == subject,
            }
        )
    result = {
        "numeric_properties": count_numeric,
        "categorical_properties": count_categorical,
        "case_count": len(rows),
        "cases": rows,
        "classes": class_tests,
        "native_guard": "PASS",
        "metrics": {
            "execution": proportion(
                sum(r["direct_correct"] and r["related_correct"] for r in rows), len(rows)
            ),
            "direct_correctness": proportion(sum(r["direct_correct"] for r in rows), len(rows)),
            "related_correctness": proportion(sum(r["related_correct"] for r in rows), len(rows)),
            "class_execution": proportion(sum(r["correct"] for r in class_tests), len(class_tests)),
        },
        "latency": {k: latency([r["latency_ms"][k] for r in rows]) for k in rows[0]["latency_ms"]},
    }
    path = ART / (
        "phase3c_postfreeze_extensibility.json"
        if postfreeze
        else "phase3c_dynamic_property_benchmark.json"
    )
    freeze_json(path, result)
    print(json.dumps(result["metrics"]))


def parity():
    check_freeze()
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    gold = json.loads((ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json").read_text())
    rows = []
    for case in gold["cases"]:
        if case["review_status"] != "REVIEWED_SCORED":
            continue
        v1intent = parse_query(case["query"])
        old = build_bundle(v1intent, case["query"], ROOT, evidence)
        q = v1_to_v2(v1intent)
        try:
            with native_guard():
                new = execute_native(q, case["query"], store, evidence)
        except LookupError as exc:
            rows.append(
                {
                    "case_id": case["id"],
                    "direct_equal": False,
                    "related_equal": False,
                    "evidence_equal": False,
                    "compile_error": str(exc),
                }
            )
            continue
        ids = lambda items: sorted(x["id"] for x in items)
        old_e = sorted(p["evidence_id"] for p in old.evidence_passages)
        new_e = sorted(p["evidence_id"] for p in new.bundle.evidence_passages)
        rows.append(
            {
                "case_id": case["id"],
                "direct_equal": ids(old.direct_evidence) == ids(new.bundle.direct_evidence),
                "related_equal": ids(old.related_evidence) == ids(new.bundle.related_evidence),
                "evidence_equal": old_e == new_e,
                "v1_direct": ids(old.direct_evidence),
                "v2_direct": ids(new.bundle.direct_evidence),
                "v1_related": ids(old.related_evidence),
                "v2_related": ids(new.bundle.related_evidence),
                "v1_evidence": old_e,
                "v2_evidence": new_e,
                "native_eligible": new.eligible_evidence_ids,
                "native_latency_ms": new.latency_ms,
            }
        )
    conforms = validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
    result = {
        "cases": rows,
        "native_guard": "PASS",
        "graph_triples": len(store.graph),
        "shacl": bool(conforms),
        "metrics": {
            key: proportion(sum(r[field] for r in rows), len(rows))
            for key, field in (
                ("DIRECT_PARITY", "direct_equal"),
                ("RELATED_PARITY", "related_equal"),
                ("EVIDENCE_ID_PARITY", "evidence_equal"),
            )
        },
    }
    filename = (
        "phase3c_native_parity_projection_repair.json"
        if (ART / "phase3c_native_parity_second_pass.json").exists()
        else (
            "phase3c_native_parity_second_pass.json"
            if (ART / "phase3c_native_parity.json").exists()
            else "phase3c_native_parity.json"
        )
    )
    freeze_json(ART / filename, result)
    graph_file = (
        "phase3c_projected_graph_provenance_repair.ttl"
        if filename == "phase3c_native_parity_projection_repair.json"
        else "phase3c_projected_graph.ttl"
    )
    store.graph.serialize(destination=str(ART / graph_file), format="turtle")
    print(json.dumps(result["metrics"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "prepare",
            "freeze",
            "secondfreeze",
            "repairfreeze",
            "dynamic",
            "postfreeze",
            "parity",
        ],
    )
    args = parser.parse_args()
    if args.stage == "postfreeze":
        dynamic(True)
    elif args.stage == "secondfreeze":
        freeze(True)
    elif args.stage == "repairfreeze":
        freeze_json(
            ART / "phase3c_projection_repair_freeze.json",
            {
                "version": "phase3c-projection-provenance-r3",
                "parent_freeze_digest": digest(ART / "phase3c_native_freeze_second_pass.json"),
                "architecture_digests": {name: digest(ROOT / name) for name in CORE},
                "change": "GENERIC_BUG_FIX: canonical-only legacy values; native executor unchanged",
            },
        )
    else:
        {"prepare": prepare, "freeze": freeze, "dynamic": dynamic, "parity": parity}[args.stage]()
