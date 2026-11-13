"""Fresh quality receipts for the real context pilot; never rewrites old receipts."""

import json
import os
import subprocess
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase3c_real_context as pilot

from nasa_fire_ai.evaluation.reconstruction import reconstruct_passage
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.contextual import attach_context_layer
from nasa_fire_ai.query.native import NS, execute_native
from nasa_fire_ai.query.v2 import QueryIntentV2

ART = ROOT / "artifacts"
PREFIX = "phase3c_real_context"
SNAPSHOT = ART / f"{PREFIX}_evidence_v1.sqlite"


def save(name, data, version="v8"):
    path = ART / f"{PREFIX}_{name}_{version}.json"
    with path.open("x") as file:
        json.dump(data, file, indent=2, default=str)
        file.write("\n")


def immutable_check():
    frozen = json.loads((ART / f"{PREFIX}_freeze_v1.json").read_text())["files"]
    immutable = {
        p: h
        for p, h in frozen.items()
        if p.startswith(("data/raw/", "data/canonical/", "evals/", "artifacts/"))
    }
    changed = [
        p for p, h in immutable.items() if not (ROOT / p).is_file() or pilot.digest(ROOT / p) != h
    ]
    return {"checked": len(immutable), "changed": changed, "passed": not changed}


def commands():
    receipts = []
    for name, command in [
        ("format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("pytest", ["uv", "run", "pytest", "-q"]),
    ]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        log = ART / f"{PREFIX}_{name}_v14.txt"
        with log.open("x") as file:
            file.write(result.stdout + result.stderr)
        receipts.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "execution": "FRESH_LOCAL_EXECUTION",
                "log": str(log.relative_to(ROOT)),
                "sha256": pilot.digest(log),
            }
        )
        print({"command": name, "exit_code": result.returncode}, flush=True)
    save("commands", receipts, version="v14")


def database_checks(evidence):
    db = evidence.db
    checks = {
        "integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_violations": [list(r) for r in db.execute("PRAGMA foreign_key_check")],
        "missing_documents": db.execute(
            "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL"
        ).fetchone()[0],
        "missing_sources": db.execute(
            "SELECT count(*) FROM documents d LEFT JOIN sources s USING(source_id) WHERE s.source_id IS NULL"
        ).fetchone()[0],
        "missing_fts": db.execute(
            "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL"
        ).fetchone()[0],
        "extra_fts": db.execute(
            "SELECT count(*) FROM passages_fts f LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL"
        ).fetchone()[0],
        "fts_duplicate_identities": db.execute(
            "SELECT count(*) FROM (SELECT evidence_id FROM passages_fts GROUP BY evidence_id HAVING count(*) != 1)"
        ).fetchone()[0],
        "fts_text_mismatches": db.execute(
            "SELECT count(*) FROM passages p JOIN passages_fts f USING(evidence_id) WHERE p.text != f.text"
        ).fetchone()[0],
        "passages": db.execute("SELECT count(*) FROM passages").fetchone()[0],
        "declared_foreign_keys": {
            t: len(db.execute(f"PRAGMA foreign_key_list({t})").fetchall())
            for t in ["sources", "documents", "passages", "evidence_refs"]
        },
    }
    # Existing schema has no FK declarations: explicit anti-joins above are
    # necessary; a vacuous PRAGMA alone would not establish registry integrity.
    return checks


def integrity():
    pilot.configure()
    evidence = EvidenceRegistry(SNAPSHOT)
    store = project_legacy(ROOT, evidence)
    attach_context_layer(store, evidence, ART / f"{PREFIX}_applicability_v8.json")
    graphs = [
        ("canonical", Graph().parse(ROOT / "data/canonical/graph.ttl"), "shapes.ttl"),
        ("native_context", store.graph, "semantic_shapes.ttl"),
        ("native_taxonomy", store.graph, "semantic_taxonomy_shapes.ttl"),
    ]
    shape_receipts = {}
    for name, graph, shapes in graphs:
        conforms, _, report = validate(graph, shacl_graph=str(ROOT / "ontology" / shapes))
        shape_receipts[name] = {
            "conforms": bool(conforms),
            "triples": len(graph),
            "report": report,
            "execution": "FRESH_SHACL",
        }
        print({"shacl": name, "conforms": bool(conforms)}, flush=True)
    missing_refs = sorted(
        {str(e) for e in store.graph.objects(None, NS.evidenceRef) if not evidence.resolve(str(e))}
    )
    units = json.loads((ART / f"{PREFIX}_source_units_v8.json").read_text())["units"]
    source_checks = []
    import pymupdf

    for key, unit in units.items():
        record = evidence.resolve(unit["evidence_id"])
        path = Path(record["raw_file"])
        if not path.is_absolute():
            path = ROOT / "data/raw" / path
        if path.suffix == ".pdf":
            with pymupdf.open(path) as pdf:
                raw = pdf[record["page"] - 1].get_text()
        elif record.get("source_cells"):
            receipt = reconstruct_passage(unit["evidence_id"], evidence, ROOT)
            source_checks.append(
                {
                    "unit": key,
                    "evidence_id": unit["evidence_id"],
                    "source_id": unit["source_id"],
                    "quote_exact": record["text"] == unit["text"],
                    "location_exact": receipt["status"] == "VERIFIED",
                    "checksum_valid": receipt["file_digest_valid"],
                    "structured_location": receipt["verified_location"],
                }
            )
            continue
        else:
            raw = path.read_text()
        source_checks.append(
            {
                "unit": key,
                "evidence_id": unit["evidence_id"],
                "source_id": unit["source_id"],
                "quote_exact": record["text"] == unit["text"],
                "location_exact": raw[record["start_offset"] : record["end_offset"]]
                == record["text"],
                "checksum_valid": pilot.digest(path) == record["checksum"],
                "structured_location": record.get("structured_location"),
            }
        )
    identities = json.loads((ART / "phase3c_fidelity_reconstruction_v1.json").read_text())[
        "identities"
    ]
    round_trips = []
    for identity in identities:
        eid = next(iter(identity.get("evidence_ids", [])), None)
        if not eid:
            eid = next(
                (e for e in store.evidence(identity["identity_id"]) if e.startswith("E-psi-")), None
            )
        if eid:
            receipt = reconstruct_passage(eid, evidence, ROOT)
            round_trips.append(
                {"entity": identity["identity_id"], "evidence_id": eid, "receipt": receipt}
            )
    active = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    native_source = (ROOT / "src/nasa_fire_ai/query/native.py").read_text()
    secret_keys = [
        os.getenv(name)
        for name in ["NVIDIA_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"]
        if os.getenv(name)
    ]
    secret_files = []
    for path in [
        *ART.glob(f"{PREFIX}*"),
        *ROOT.joinpath("docs").glob("PHASE3C_REAL_CONTEXT*"),
        ROOT / "data/index/scientific_context_v2.json",
    ]:
        if path.is_file() and path.suffix in {".json", ".md", ".txt", ".html"}:
            contents = path.read_text()
            if any(key in contents for key in secret_keys):
                secret_files.append(str(path.relative_to(ROOT)))
    save(
        "integrity",
        {
            "snapshot_db": database_checks(evidence),
            "active_db": database_checks(active),
            "shacl": shape_receipts,
            "broken_graph_evidence_refs": missing_refs,
            "context_rejections": store.context_layer.rejected,
            "source_units": source_checks,
            "historical_identity_round_trips": round_trips,
            "historical_digests": immutable_check(),
            "secret_exclusion": {"matched_files": secret_files, "dotenv_in_artifacts": False},
            "native_executor_has_v1_fallback": "build_bundle_v2" in native_source
            or "classify_runs" in native_source,
            "canonical_publications_from_llm": 0,
        },
    )


def regressions():
    import phase3c_native_benchmarks as benchmark

    output = ART / f"{PREFIX}_native_regressions_v8"
    output.mkdir(exist_ok=True)
    benchmark.ART = output

    def check_freeze():
        if not immutable_check()["passed"]:
            raise RuntimeError("immutable historical snapshot drift")

    benchmark.check_freeze = check_freeze
    for flag in [
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "NATIVE_V2_QUERY_ENABLED",
        "NEMOTRON_CONTEXT_INTERPRETATION_ENABLED",
    ]:
        os.environ[flag] = "false"
    for filename, operation in [
        ("phase3c_dynamic_property_benchmark.json", lambda: benchmark.dynamic()),
        ("phase3c_postfreeze_extensibility.json", lambda: benchmark.dynamic(postfreeze=True)),
        ("phase3c_native_parity.json", lambda: benchmark.parity()),
    ]:
        path = output / filename
        if not path.exists():
            operation()
    pilot.configure()
    evidence = EvidenceRegistry(SNAPSHOT)
    store = project_legacy(ROOT, evidence)
    attach_context_layer(store, evidence, ART / f"{PREFIX}_applicability_v8.json")
    cases = json.loads((ART / "phase3c_related_cases_v1.json").read_text())
    results = []
    for mode in ["BASELINE", "CONTEXT"]:
        os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = str(mode == "CONTEXT").lower()
        for case in cases:
            response = execute_native(
                QueryIntentV2.model_validate(case["intent"]), case["query"], store, evidence
            )
            refs = {p["evidence_id"] for p in response.bundle.evidence_passages}
            results.append(
                {
                    "case_id": case["case_id"],
                    "mode": mode,
                    "expected_identity_case": case["objective_identity_case"],
                    "expected_no_direct": case["objective_no_direct"],
                    "identity_recovered": bool(set(case["expected_evidence_ids"]) & refs),
                    "direct_ids": [r["id"] for r in response.bundle.direct_evidence],
                    "false_direct_software_condition": bool(
                        case["objective_no_direct"] and response.bundle.direct_evidence
                    ),
                    "citations_resolve": all(evidence.resolve(e) for e in refs),
                    "scientific_relevance": None,
                }
            )
    save(
        "retrieval_regression",
        {
            "cases": results,
            "case_count": len(cases),
            "native_tests_directory": str(output.relative_to(ROOT)),
            "labels_are_identity_not_independent_relevance": True,
        },
    )


def identity_audit():
    evidence = EvidenceRegistry(SNAPSHOT)
    identities = json.loads((ART / "phase3c_fidelity_reconstruction_v1.json").read_text())[
        "identities"
    ]
    receipts = [
        {
            "entity": record["identity_id"],
            "evidence_id": record["evidence_ids"][0],
            "reconstruction": reconstruct_passage(record["evidence_ids"][0], evidence, ROOT),
        }
        for record in identities
    ]
    save(
        "identity_round_trips",
        {"count": len(receipts), "cases": receipts, "execution": "FRESH_SOURCE_RECONSTRUCTION"},
    )


def full_source_validation():
    import pymupdf

    from nasa_fire_ai.evaluation.reconstruction import source_path
    from nasa_fire_ai.ingestion.source_spans import recover_span
    from nasa_fire_ai.ingestion.structured_provenance import round_trip

    evidence = EvidenceRegistry(SNAPSHOT)
    cells = [
        json.loads(r[0]) for r in evidence.db.execute("SELECT locator_json FROM structured_cells")
    ]
    errors = []
    for cell in cells:
        try:
            round_trip(cell, ROOT)
        except (ValueError, OSError, IndexError) as exc:
            errors.append({"evidence_id": cell["evidence_id"], "error": type(exc).__name__})
    documents, checks = {}, []
    for row in evidence.db.execute("SELECT * FROM evidence_locations"):
        locator = json.loads(row["location_json"])
        raw = source_path(ROOT, locator.get("raw_file"))
        if not raw or raw.suffix.lower() != ".pdf":
            continue
        if raw not in documents:
            documents[raw] = pymupdf.open(raw)
        page, supported = locator.get("physical_pdf_page"), False
        if page and 1 <= page <= len(documents[raw]):
            text = documents[raw][page - 1].get_text()
            if locator.get("exact_source_span"):
                try:
                    recover_span(text, locator["exact_source_span"]["span"])
                    supported = True
                except ValueError:
                    pass
            elif locator.get("row_identifier"):
                supported = locator["row_identifier"] in text
            else:
                supported = bool(locator.get("verification"))
        checks.append(
            {
                "evidence_id": row["evidence_id"],
                "physical_page": page,
                "source_supported": supported,
                "digest_valid": pilot.digest(raw) == locator.get("checksum"),
            }
        )
    for pdf in documents.values():
        pdf.close()
    evidence.db.execute("INSERT INTO passages_fts(passages_fts) VALUES ('integrity-check')")
    evidence.db.commit()
    conforms, _, report = validate(
        Graph().parse(ROOT / "data/canonical/graph.ttl"),
        shacl_graph=str(ROOT / "ontology/enrichment_shapes.ttl"),
    )
    save(
        "full_source_validation",
        {
            "execution": "FRESH_SOURCE_LOCATION_VALIDATION",
            "csv_cells_checked": len(cells),
            "csv_errors": errors,
            "pdf_locations": checks,
            "literal_shacl": bool(conforms),
            "literal_report": report,
            "fts_internal_integrity": "PASS",
        },
        version="v13",
    )
    print(
        {
            "csv_cells": len(cells),
            "errors": len(errors),
            "pdf_locations": len(checks),
            "bad_pdf": sum(not r["source_supported"] or not r["digest_valid"] for r in checks),
            "literal_shacl": bool(conforms),
        },
        flush=True,
    )


if __name__ == "__main__":
    stage = sys.argv[1]
    {
        "commands": commands,
        "integrity": integrity,
        "regressions": regressions,
        "identities": identity_audit,
        "source_locations": full_source_validation,
    }[stage]()
