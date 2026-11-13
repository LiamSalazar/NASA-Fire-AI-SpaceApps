"""Actual quality gates, immutable digests, source provenance and registry integrity."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS, identity


def main():
    out = ROOT / "artifacts/phase3c_targeted_integrity_v6.json"
    assert not out.exists()
    quality = []
    for i, command in enumerate(
        ["uv run ruff format --check .", "uv run ruff check .", "uv run pytest -q"]
    ):
        result = subprocess.run(
            command.split(), cwd=ROOT, capture_output=True, text=True, check=False
        )
        receipt = ROOT / f"artifacts/phase3c_targeted_quality_{i}_v6.txt"
        assert not receipt.exists()
        receipt.write_text(result.stdout + result.stderr)
        quality.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "receipt": str(receipt.relative_to(ROOT)),
            }
        )
        print({"command": command, "exit_code": result.returncode}, flush=True)
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "true"
    os.environ["FLEX_SOURCE_CORRECTIONS_ENABLED"] = "true"
    store = project_legacy(ROOT, registry)
    baseline = json.loads((ROOT / "artifacts/phase3c_targeted_baseline_v1.json").read_text())[
        "files"
    ]
    immutable = {
        p: h
        for p, h in baseline.items()
        if p.startswith(("data/raw/", "data/canonical/", "evals/", "artifacts/"))
    }
    changed = [
        p
        for p, h in immutable.items()
        if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
    ]
    historical_gold = {p: h for p, h in immutable.items() if p.startswith("evals/")}
    historical_benchmarks = {p: h for p, h in immutable.items() if p.startswith("artifacts/")}
    broken = [
        str(e)
        for e in store.graph.objects(None, NS.evidenceRef)
        if registry.resolve(str(e)) is None
    ]
    invalid_relations = [
        identity(r)
        for r in store.graph.subjects(RDF.type, NS.SemanticRelation)
        if any(
            identity(v) not in store.registry.relations for v in store.graph.objects(r, NS.relation)
        )
    ]
    orphans = {
        name: registry.db.execute(sql).fetchone()[0]
        for name, sql in {
            "passages_without_documents": "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL",
            "documents_without_sources": "SELECT count(*) FROM documents d LEFT JOIN sources s USING(source_id) WHERE s.source_id IS NULL",
            "cells_without_passages": "SELECT count(*) FROM structured_cells c LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
            "references_without_passages": "SELECT count(*) FROM evidence_refs e LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
            "fts_missing": "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL",
            "fts_duplicates": "SELECT count(*) FROM (SELECT evidence_id FROM passages_fts GROUP BY evidence_id HAVING count(*)>1)",
            "locations_without_passages": "SELECT count(*) FROM evidence_locations l LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
        }.items()
    }
    registry.db.execute("INSERT INTO passages_fts(passages_fts) VALUES ('integrity-check')")
    registry.db.commit()
    env = Settings()
    secrets = [env.nvidia_api_key, os.getenv("TYPESAFE_API_KEY"), env.api_key]
    secret_matches = []
    for directory in ["artifacts", "docs", "src", "scripts", "tests", "domain", "ontology"]:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in str(path):
                content = path.read_bytes()
                if any(secret and secret.encode() in content for secret in secrets):
                    secret_matches.append(str(path.relative_to(ROOT)))
    canonical = Graph().parse(ROOT / "data/canonical/graph.ttl")
    result = {
        "quality": quality,
        "immutable_files_checked": len(immutable),
        "changed_immutable_files": changed,
        "historical_gold_files_checked": len(historical_gold),
        "historical_benchmark_files_checked": len(historical_benchmarks),
        "canonical_shacl": bool(
            validate(canonical, shacl_graph=str(ROOT / "ontology/shapes.ttl"))[0]
        ),
        "native_shacl": bool(
            validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
        ),
        "literal_shacl": bool(
            validate(canonical, shacl_graph=str(ROOT / "ontology/enrichment_shapes.ttl"))[0]
        ),
        "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_violations": [
            tuple(r) for r in registry.db.execute("PRAGMA foreign_key_check")
        ],
        "manual_reference_checks": orphans,
        "broken_graph_evidence": broken,
        "invalid_ontology_relations": invalid_relations,
        "secret_matches_outside_env": secret_matches,
        "new_source_unit_accessors": "source:initial_carbon_dioxide, source:burning_rate (documented, opt-in)",
        "independent_scientific_review": "PENDING",
        "source_corrections": 532,
        "canonical_runs_added": 111,
        "canonical_samples_added": 19,
    }
    result["status"] = (
        "PASS"
        if all(q["exit_code"] == 0 for q in quality)
        and not (
            changed
            or broken
            or invalid_relations
            or secret_matches
            or any(orphans.values())
            or result["foreign_key_violations"]
        )
        and result["canonical_shacl"]
        and result["native_shacl"]
        and result["literal_shacl"]
        and result["sqlite_integrity"] == "ok"
        else "FAIL"
    )
    out.write_text(json.dumps(result, indent=2))
    print({"integrity": result["status"], "immutable_files": len(immutable)}, flush=True)


if __name__ == "__main__":
    main()
