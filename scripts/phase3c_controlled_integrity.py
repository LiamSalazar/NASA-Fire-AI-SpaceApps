"""Versioned native/code freeze and scientific integrity checks for Phase 3C."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS

FREEZE = ROOT / "artifacts/phase3c_controlled_native_freeze_v1.json"
RESULT = ROOT / "artifacts/phase3c_controlled_integrity_v1.json"
BASELINE = ROOT / "artifacts/phase3c_final_repair_baseline.json"
FROZEN_CODE = (
    "domain/semantic_registry.yaml",
    "domain/query_language_v2.yaml",
    "ontology/shapes.ttl",
    "ontology/semantic_shapes.ttl",
    "src/nasa_fire_ai/models/__init__.py",
    "src/nasa_fire_ai/query/v2.py",
    "src/nasa_fire_ai/query/native.py",
    "src/nasa_fire_ai/query/native_interpreter.py",
    "src/nasa_fire_ai/query/controlled_reasoning.py",
    "src/nasa_fire_ai/llm/native_interpreter.py",
    "src/nasa_fire_ai/evidence/registry.py",
    "src/nasa_fire_ai/services/native.py",
    "src/nasa_fire_ai/services/grounding.py",
    "scripts/phase3c_controlled_e2e.py",
    "scripts/phase3c_controlled_analysis.py",
)
FROZEN_GOLD = (
    "evals/phase3c_controlled_e2e_regression_gold_v1.json",
    "artifacts/phase3c_controlled_gold_reconciliation_proposed_v1.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> dict:
    payload = {
        "version": "phase3c-controlled-native-freeze-v1",
        "status": "FROZEN_AFTER_IMPLEMENTATION_BEFORE_FINAL_INTEGRITY_CHECKS",
        "code_digests": {name: sha(ROOT / name) for name in FROZEN_CODE},
        "gold_digests": {name: sha(ROOT / name) for name in FROZEN_GOLD},
        "historical_phase3c_baseline": str(BASELINE.relative_to(ROOT)),
        "features_default_off": [
            "SEMANTIC_QUERY_EXPANSION_ENABLED",
            "CONTEXTUAL_RERANKING_ENABLED",
            "JEV_ADVISORY_TRIAGE_ENABLED",
            "SCIENTIFIC_PARAPHRASE_ENABLED",
        ],
    }
    if FREEZE.exists() and json.loads(FREEZE.read_text()) != payload:
        raise RuntimeError("Controlled freeze already exists and does not match current code/gold")
    FREEZE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def integrity() -> dict:
    frozen = json.loads(FREEZE.read_text())
    current = {
        name: sha(ROOT / name) for name in (*frozen["code_digests"], *frozen["gold_digests"])
    }
    changed_after_freeze = [
        name
        for name, expected in {**frozen["code_digests"], **frozen["gold_digests"]}.items()
        if current[name] != expected
    ]

    baseline = json.loads(BASELINE.read_text())
    historical_mismatches = []
    for name, expected in baseline["digests"].items():
        path = ROOT / name
        actual = sha(path) if path.is_file() else None
        if actual != expected:
            historical_mismatches.append(name)
    historical_eval_mismatches = [
        name
        for name in historical_mismatches
        if name.startswith(("artifacts/", "evals/", "data/raw/", "data/canonical/"))
    ]

    evidence = EvidenceRegistry(Settings().registry_path)
    store = project_legacy(ROOT, evidence)
    db_integrity = evidence.db.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = evidence.db.execute("PRAGMA foreign_key_check").fetchall()
    evidence.db.execute("INSERT INTO passages_fts(passages_fts) VALUES('integrity-check')")
    fts_check = "PASS"
    canonical_graph = Graph().parse(ROOT / "data/canonical/graph.ttl")
    canonical_shacl = validate(canonical_graph, shacl_graph=str(ROOT / "ontology/shapes.ttl"))
    native_shacl = validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))
    broken_refs = sorted(
        str(ref)
        for ref in set(store.graph.objects(None, NS.evidenceRef))
        if evidence.resolve(str(ref)) is None
    )
    count = lambda table: evidence.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    missing_fts = evidence.db.execute(
        "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) "
        "WHERE f.evidence_id IS NULL"
    ).fetchone()[0]
    orphan_passages = evidence.db.execute(
        "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) "
        "WHERE d.document_id IS NULL"
    ).fetchone()[0]
    staged = evidence.db.execute(
        "SELECT source_id,evidence_id,payload_json,review_status FROM semantic_staging"
    ).fetchall()
    incomplete_staging = sum(
        not row["source_id"]
        or not row["evidence_id"]
        or not json.loads(row["payload_json"])
        or row["review_status"] not in {"PENDING", "REVIEWED", "REJECTED"}
        for row in staged
    )
    dynamic = json.loads(
        (ROOT / "artifacts/phase3c_final_repair_extensibility_v1.json").read_text()
    )
    output = {
        "version": "phase3c-controlled-integrity-v1",
        "freeze": str(FREEZE.relative_to(ROOT)),
        "changed_after_freeze": changed_after_freeze,
        "historical_baseline_mismatch_count": len(historical_mismatches),
        "historical_baseline_mismatch_paths": historical_mismatches,
        "historical_eval_or_data_mismatch_paths": historical_eval_mismatches,
        "historical_benchmark_artifacts_intact": not historical_eval_mismatches,
        "canonical_raw_files_unchanged": all(
            name not in historical_mismatches
            for name in baseline["digests"]
            if name.startswith(("data/raw/", "data/canonical/"))
        ),
        "database": {
            "integrity_check": db_integrity,
            "foreign_key_violations": len(foreign_keys),
        },
        "evidence_registry_counts": {
            table: count(table)
            for table in ("sources", "documents", "passages", "passages_fts", "semantic_staging")
        },
        "evidence_integrity": {
            "missing_fts_rows": missing_fts,
            "orphan_passages": orphan_passages,
            "broken_native_evidence_refs": broken_refs,
            "fts_integrity_check": fts_check,
        },
        "semantic_graph": {
            "triples": len(store.graph),
            "shacl_conforms": bool(native_shacl[0]),
            "broken_evidence_refs": len(broken_refs),
        },
        "canonical_graph_shacl_conforms": bool(canonical_shacl[0]),
        "staging": {
            "rows": len(staged),
            "incomplete_provenance_or_state": incomplete_staging,
        },
        "dynamic_property_regression": {
            "existing_artifact": "artifacts/phase3c_final_repair_extensibility_v1.json",
            "recorded_results": dynamic,
            "rerun": False,
        },
        "status": "PASS"
        if not changed_after_freeze
        and not historical_eval_mismatches
        and not broken_refs
        and not incomplete_staging
        and not missing_fts
        and not orphan_passages
        and db_integrity == "ok"
        and not foreign_keys
        and canonical_shacl[0]
        and native_shacl[0]
        else "FAIL",
    }
    RESULT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "check"))
    args = parser.parse_args()
    result = freeze() if args.command == "freeze" else integrity()
    print(
        json.dumps(
            {
                "status": result.get("status", "FROZEN"),
                "artifact": str((FREEZE if args.command == "freeze" else RESULT).relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
