"""Fresh native regressions; immutable historical outputs are never overwritten."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import phase3c_native_benchmarks as benchmark
from phase3c_consolidation import PREFIX, ROOT, digest, save
from phase3c_real_context import configure

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.autonomous import KnowledgeMaintenance
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def check_historical():
    frozen = json.loads((ROOT / "artifacts" / f"{PREFIX}_freeze_v1.json").read_text())["files"]
    changed = [
        name
        for name, expected in frozen.items()
        if not (ROOT / name).is_file() or digest(ROOT / name) != expected
    ]
    if changed:
        raise RuntimeError("Historical source/gold/receipt drift")


def main():
    check_historical()
    benchmark.ART = ROOT / "artifacts/phase3c_consolidation_native_checks_v1"
    benchmark.ART.mkdir(exist_ok=False)
    benchmark.check_freeze = check_historical
    for flag in (
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "NATIVE_V2_QUERY_ENABLED",
        "SCIENTIFIC_SYNTHESIS_ENABLED",
    ):
        os.environ[flag] = "false"
    benchmark.dynamic()
    benchmark.dynamic(postfreeze=True)
    benchmark.parity()
    configure()
    os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = "false"
    evidence = EvidenceRegistry(Settings().registry_path)
    store = project_legacy(ROOT, evidence)
    cases = json.loads((ROOT / "artifacts/phase3c_related_cases_v1.json").read_text())
    receipts = []
    for case in cases:
        result = execute_native(
            QueryIntentV2.model_validate(case["intent"]),
            case["query"],
            store,
            evidence,
            hierarchical=True,
            relational=True,
        )
        ids = [row["evidence_id"] for row in result.bundle.evidence_passages]
        receipts.append(
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "direct_ids": [row["id"] for row in result.bundle.direct_evidence],
                "related_ids": [row["id"] for row in result.bundle.related_evidence],
                "evidence_ids": ids,
                "identity_recovered": bool(set(ids) & set(case.get("expected_evidence_ids", [])))
                if case.get("objective_identity_case")
                else None,
                "false_direct": bool(result.bundle.direct_evidence)
                if case.get("objective_no_direct")
                else None,
                "independent_relevance": None,
            }
        )
    save(
        "retrieval_regression",
        {"execution": "FRESH_NATIVE_EXECUTION", "cases": receipts, "count": len(receipts)},
    )
    pipeline = KnowledgeMaintenance(ROOT, evidence)
    save(
        "staging_revalidation",
        {"cases": pipeline.revalidate_staged_contexts(), "canonical_scientific_changes": 0},
    )
    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = "true"
    os.environ["SCIENTIFIC_SYNTHESIS_ENABLED"] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    service = Phase3AssistantService()
    response = service.answer_query(
        "Find NASA publications about risks of depressurization as a fire suppression technique in spacecraft."
    )
    save(
        "new_source_answer",
        {
            "response": response.model_dump(mode="json"),
            "independent_relevance": None,
            "new_source_recovered": any(
                "E-auto-" in p["evidence_id"] for p in response.evidence_bundle.evidence_passages
            ),
        },
    )
    # Optional free-form generation: two live calls, strict proof checks, fallback.
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SYNTHESIS_ENABLED"] = "true"
    generated = []
    for query in (
        "What happened after airflow was interrupted and restored?",
        "What did NASA observe about PMMA combustion under microgravity?",
    ):
        response = service.answer_query(query)
        generated.append(
            {
                "question": query,
                "receipt": response.evidence_bundle.retrieval_metadata.get(
                    "nemotron_scientific_selection"
                ),
                "final_answer": response.rendered_answer,
                "final_claims": [
                    claim.model_dump(mode="json") for claim in response.answer.generated_claims
                ],
                "independent_review": None,
            }
        )
    save("generative_synthesis", {"cases": generated, "model": Settings().nvidia_phase3_model})
    scheduling = []
    with tempfile.TemporaryDirectory(prefix="nasa-maintenance-unit-") as temporary:
        for name in ("service", "timer"):
            path = Path(temporary) / f"nasa-knowledge-maintenance.{name}"
            path.write_text((ROOT / f"ops/nasa-knowledge-maintenance.{name}.example").read_text())
        try:
            result = subprocess.run(
                [
                    "systemd-analyze",
                    "verify",
                    str(Path(temporary) / "nasa-knowledge-maintenance.service"),
                    str(Path(temporary) / "nasa-knowledge-maintenance.timer"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            scheduling.append(
                {
                    "command": "systemd-analyze verify",
                    "exit_code": result.returncode,
                    "output": result.stdout + result.stderr,
                    "installed": False,
                }
            )
        except FileNotFoundError:
            scheduling.append({"status": "NOT_AVAILABLE", "installed": False})
    save("scheduling", scheduling)
    check_historical()


if __name__ == "__main__":
    main()
