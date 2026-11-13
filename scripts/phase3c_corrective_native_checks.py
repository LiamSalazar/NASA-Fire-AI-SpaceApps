"""Reuse historical benchmark harness with isolated corrective output paths."""

import json
import sys
from pathlib import Path

from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase3c_native_benchmarks as historical_harness
from phase3c_corrective_live import check_freeze

from nasa_fire_ai.evaluation.phase3c import digest, freeze_json, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS


def main():
    check_freeze()
    output = ROOT / "artifacts/phase3c_corrective_native_checks_v1"
    output.mkdir(exist_ok=True)
    historical_harness.ART = output
    historical_harness.check_freeze = check_freeze
    for name, operation in (
        ("phase3c_dynamic_property_benchmark.json", lambda: historical_harness.dynamic()),
        (
            "phase3c_postfreeze_extensibility.json",
            lambda: historical_harness.dynamic(postfreeze=True),
        ),
        ("phase3c_native_parity.json", historical_harness.parity),
    ):
        if not (output / name).exists():
            operation()
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    baseline = json.loads((ROOT / "artifacts/phase3c_corrective_baseline_v1.json").read_text())
    immutable = {
        name: digest(ROOT / name) == expected
        for name, expected in baseline["digests"].items()
        if name.startswith(("data/raw/", "data/canonical/"))
    }
    counts = {
        table: evidence.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("sources", "documents", "passages", "passages_fts", "semantic_staging")
    }
    broken = [
        str(e)
        for e in set(store.graph.objects(None, NS.evidenceRef))
        if evidence.resolve(str(e)) is None
    ]
    canonical = __import__("rdflib").Graph().parse(ROOT / "data/canonical/graph.ttl")
    gold = json.loads((ROOT / "evals/phase1_5_retrieval_gold.json").read_text())["questions"]
    doc_source = dict(evidence.db.execute("SELECT document_id,source_id FROM documents").fetchall())
    ranks = []
    for c in gold:
        if not c["expected_source_ids"]:
            continue
        found = evidence.search(c["question"], limit=10)
        ranks.append(
            next(
                (
                    i
                    for i, p in enumerate(found, 1)
                    if doc_source.get(p["document_id"]) in c["expected_source_ids"]
                ),
                None,
            )
        )
    bm25 = {
        f"Recall@{k}": proportion(sum(r is not None and r <= k for r in ranks), len(ranks))
        for k in (1, 3, 5, 10)
    }
    bm25["MRR"] = {
        "numerator": sum(1 / r for r in ranks if r),
        "denominator": len(ranks),
        "estimate": sum(1 / r for r in ranks if r) / len(ranks),
    }
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_integrity_v1.json",
        {
            "version": "POST_HOLDOUT_REPAIR-v1",
            "immutable_sources_unchanged": all(immutable.values()),
            "immutable_file_checks": immutable,
            "counts": counts,
            "db_integrity": evidence.db.execute("PRAGMA integrity_check").fetchone()[0],
            "canonical_shacl": bool(
                validate(canonical, shacl_graph=str(ROOT / "ontology/shapes.ttl"))[0]
            ),
            "native_shacl": bool(
                validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
            ),
            "native_triples": len(store.graph),
            "broken_native_evidence_ids": broken,
            "fts_missing": evidence.db.execute(
                "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL"
            ).fetchone()[0],
            "document_orphans": evidence.db.execute(
                "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL"
            ).fetchone()[0],
            "legacy_unreviewed_epistemic_records_quarantined": store.legacy_statement_staging,
            "bm25": bm25,
            "projection": store.projection_report,
        },
    )
    print("Corrective native checks and scientific integrity persisted")


if __name__ == "__main__":
    main()
