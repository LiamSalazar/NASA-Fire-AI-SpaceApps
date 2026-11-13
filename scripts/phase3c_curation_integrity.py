"""Fresh final integrity, citation, source preservation and UI receipts."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def check(directory, workspace):
    baseline = json.loads((directory / "baseline.json").read_text())
    frozen = [
        row
        for row in baseline["files"]
        if row["path"].startswith(("data/raw/", "evals/", "data/canonical/"))
    ]
    changed = [
        r["path"]
        for r in frozen
        if not (ROOT / r["path"]).is_file()
        or hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest() != r["sha256"]
    ]
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    store = project_legacy(workspace, registry)
    native_ok, _, native_report = validate(
        store.graph, shacl_graph=str(workspace / "ontology/semantic_shapes.ttl")
    )
    canonical_ok, _, canonical_report = validate(
        Graph().parse(ROOT / "data/canonical/graph.ttl"),
        shacl_graph=str(ROOT / "ontology/shapes.ttl"),
    )
    all_ids = {str(e) for e in store.graph.objects(None, NS.evidenceRef)}
    missing = [eid for eid in all_ids if not registry.resolve(eid)]
    input_path = Path(registry.db.execute("PRAGMA database_list").fetchone()[2])
    result = {
        "canonical_shacl": canonical_ok,
        "canonical_report": str(canonical_report),
        "native_shacl": native_ok,
        "native_report": str(native_report),
        "scientific_triples": len(store.graph),
        "graph_evidence_ids": len(all_ids),
        "missing_graph_evidence_ids": missing,
        "sqlite": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_violations": [
            list(r) for r in registry.db.execute("PRAGMA foreign_key_check")
        ],
        "frozen_inputs_checked": len(frozen),
        "frozen_inputs_changed": changed,
        "main_registry_preserved": hashlib.sha256(
            (ROOT / "data/index/evidence.sqlite").read_bytes()
        ).hexdigest()
        == next(
            r["sha256"] for r in baseline["files"] if r["path"] == "data/index/evidence.sqlite"
        ),
        "canonical_publication_location": "data/canonical/research; selected immutable RDF versions augment existing KG",
        "active_versions": [
            dict(r)
            for r in registry.db.execute(
                "SELECT a.package_id,a.digest,p.receipt FROM research_active a JOIN research_publications p USING(digest)"
            )
        ],
        "registry_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "vector_status": "Native executor retains disabled experimental vector retrieval; no enabled-vector activation demonstrated",
        "standards_mapping_triples": len(
            Graph().parse(ROOT / "ontology/incorporation_mappings.ttl")
        ),
    }
    (directory / "final_integrity.json").write_text(json.dumps(result, indent=2))
    os.environ["NASA_CURATION_DEVELOPMENT"] = "true"
    os.environ["NASA_CURATION_WORKSPACE"] = str(workspace.resolve())
    sys.path.insert(0, str(ROOT / "app"))
    app = AppTest.from_string(
        f"from curation_view import show_curation\nfrom pathlib import Path\nshow_curation(Path({str(ROOT)!r}))",
        default_timeout=20,
    ).run()
    ui = {
        "exceptions": [e.message for e in app.exception],
        "buttons": [b.label for b in app.button],
        "file_uploaders": [e.label for e in app.get("file_uploader")],
        "graphs": len(app.get("graphviz_chart")),
        "captions": [c.value for c in app.caption],
        "boundary": "Actual widgets rendered; exact-version checkbox/button approval exercised by test_scientific_ui_actual_widgets. No independent domain usability study.",
    }
    (directory / "ui_final_receipt.json").write_text(json.dumps(ui, indent=2))
    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    assistant = Phase3AssistantService(
        root=workspace, settings=Settings(root=workspace, nvidia_api_key=None)
    )
    questions = [
        "Which conditions applied to Saffire-I isolated incorporation pilot?",
        "Which measurements were reported in Saffire-I isolated incorporation pilot?",
        "Find SIBAL Fabric in Saffire-I isolated incorporation pilot under normal gravity",
        "What observations were reported in Depressurization suppression source pilot?",
        "What conclusions were reported in Depressurization suppression source pilot?",
        "What open questions were reported in Depressurization suppression source pilot?",
        "Which conditions applied to Saffire-I S1 and S2?",
    ]
    answers = [assistant.answer_query(q).model_dump(mode="json") for q in questions]
    (directory / "final_queries.json").write_text(json.dumps(answers, indent=2))
    store.graph.serialize(directory / "final_graph.ttl", format="turtle")
    curator = CurationService(
        workspace, registry, ReviewPolicy(frozenset({"development-scientist"}), True)
    )
    exports = {}
    for item in curator.list_packages():
        current = curator.get(item["package_id"])
        exports[item["package_id"]] = {
            "digest": current["digest"],
            "validation": curator.validate(current["package"]),
            "approved_rdf_history": len(list((workspace / "data/canonical/research").glob("*.nt"))),
        }
    (directory / "final_package_readiness.json").write_text(json.dumps(exports, indent=2))
    secrets = [
        os.environ.get(k)
        for k in ("NVIDIA_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY")
        if os.environ.get(k)
    ]
    leaked = []
    for path in directory.rglob("*"):
        if path.is_file() and any(value.encode() in path.read_bytes() for value in secrets):
            leaked.append(str(path.relative_to(directory)))
    (directory / "secrets_exclusion.json").write_text(
        json.dumps(
            {
                "secret_values_found": bool(leaked),
                "affected_files": leaked,
                "env_included": any(p.name == ".env" for p in directory.rglob("*")),
            },
            indent=2,
        )
    )
    print(
        {
            "native_shacl": native_ok,
            "canonical_shacl": canonical_ok,
            "frozen_changed": changed,
            "missing_citations": len(missing),
            "UI_errors": len(ui["exceptions"]),
            "secrets_leaked": bool(leaked),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    check(args.directory, args.workspace)
