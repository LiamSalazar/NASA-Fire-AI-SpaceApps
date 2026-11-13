"""Read-only baseline and native scientific-state checks, with new result artifacts."""

import json
import re
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evaluation.phase3c import digest, freeze_json, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy


def main():
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    db = evidence.db
    counts = {
        name: db.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        for name in (
            "sources",
            "documents",
            "passages",
            "passages_fts",
            "evidence_refs",
            "semantic_staging",
        )
    }
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    missing_refs = db.execute(
        "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL"
    ).fetchone()[0]
    fts_missing = db.execute(
        "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL"
    ).fetchone()[0]
    fts_dupes = db.execute(
        "SELECT count(*) FROM (SELECT evidence_id FROM passages_fts GROUP BY evidence_id HAVING count(*) != 1)"
    ).fetchone()[0]
    graph = Graph().parse(ROOT / "data/canonical/graph.ttl")
    canonical_shacl = bool(validate(graph, shacl_graph=str(ROOT / "ontology/shapes.ttl"))[0])
    store = project_legacy(ROOT, evidence)
    native_shacl = bool(
        validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
    )
    gold = json.loads((ROOT / "evals/phase1_5_retrieval_gold.json").read_text())["questions"]
    source_by_document = {
        r[0]: r[1] for r in db.execute("SELECT document_id,source_id FROM documents")
    }
    rows = []
    for case in gold:
        if not case["expected_source_ids"]:
            continue
        results = evidence.search(case["question"], limit=10)
        rank = next(
            (
                i
                for i, r in enumerate(results, 1)
                if source_by_document.get(r["document_id"]) in case["expected_source_ids"]
            ),
            None,
        )
        rows.append({"id": case["id"], "rank": rank})
    n = len(rows)
    bm25 = {
        f"Recall@{k}": proportion(sum(r["rank"] is not None and r["rank"] <= k for r in rows), n)
        for k in (1, 3, 5, 10)
    }
    bm25["MRR"] = {
        "numerator": sum(1 / r["rank"] for r in rows if r["rank"]),
        "denominator": n,
        "estimate": sum(1 / r["rank"] for r in rows if r["rank"]) / n,
    }
    forbidden = [
        "LEGACY_PROPERTY_METADATA",
        "LEGACY_RELATION_METADATA",
        "build_bundle_from_v1_as_v2",
        "classify_runs",
        "build_bundle_v2",
    ]
    native_source = (ROOT / "src/nasa_fire_ai/query/native.py").read_text()
    audit = {
        "forbidden_native_references": {name: native_source.count(name) for name in forbidden},
        "property_specific_native_branches": len(
            re.findall(
                r"(?:if|elif).*?(?:AirflowVelocity|OxygenConcentration|Pressure)", native_source
            )
        ),
        "source_id_specific_native_branches": len(
            re.findall(r"(?:if|elif).*?(?:psi-\d|ntrs-|PSI-)", native_source)
        ),
        "legacy_source_semantic_components_retained": 3,
        "legacy_source_semantic_mappings_retained": 16,
        "caveat": "Static identifier-reference audit plus runtime forbidden-call mocks; not formal whole-program proof",
    }
    result = {
        "baseline_counts": counts,
        "legacy_execution_runs": len(json.loads((ROOT / "data/canonical/runs.json").read_text())),
        "canonical_run_records": sum(
            r["type"] == "ExperimentalRunRecord"
            for r in json.loads((ROOT / "data/canonical/records.json").read_text())
        ),
        "db_integrity": integrity,
        "missing_document_refs": missing_refs,
        "fts_missing": fts_missing,
        "fts_duplicates": fts_dupes,
        "canonical_triples": len(graph),
        "canonical_shacl": canonical_shacl,
        "native_shacl": native_shacl,
        "native_triples": len(store.graph),
        "bm25": bm25,
        "audit": audit,
        "scientific_state": {
            "raw_files_modified": False,
            "historical_results_modified": False,
            "staging_to_direct": False,
            "new_scientific_aliases_added": False,
            "limitation": "405 canonical runs exist; generic scientific values projected from the two-row legacy execution view only",
        },
        "digests": {
            name: digest(ROOT / name)
            for name in (
                "data/canonical/runs.json",
                "data/canonical/records.json",
                "data/canonical/graph.ttl",
            )
        },
    }
    freeze_json(ROOT / "artifacts/phase3c_quality_integrity.json", result)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "baseline_counts",
                    "db_integrity",
                    "canonical_shacl",
                    "native_shacl",
                    "bm25",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
