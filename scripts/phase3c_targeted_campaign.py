"""Versioned targeted correction receipts. Does not mutate historical source/gold."""

import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.enrichment import source_rows
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.ingestion.structured_provenance import register_cells, round_trip, table_cells
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.query.v2 import QueryIntentV2

ART = ROOT / "artifacts"
VERSION = next((v for v in ("v4", "v3", "v2") if "--" + v in sys.argv), "v1")


def write(name, data):
    path = ART / f"phase3c_targeted_{name}_{VERSION}.json"
    if path.exists():
        if json.loads(path.read_text()) == json.loads(json.dumps(data, default=str)):
            return
        raise FileExistsError(path)
    path.write_text(json.dumps(data, indent=2, default=str))


def datasets(evidence):
    inventory = json.loads((ART / "phase3c_enrichment_psi_v1.json").read_text())
    reports, canonical, provenance = [], [], []
    for dataset in inventory["rows"]:
        if dataset["priority"] != 1:
            continue
        staged = []
        published = []
        for filename in dataset["table_files"]:
            path = ROOT / filename
            headers, rows, metadata = table_cells(path, ROOT)
            source = dataset["psi_metadata_matches"][0]
            sid = source["accession"].lower()
            source_row = {
                "source_id": sid,
                "source_type": "PSI experimental table",
                "nasa_id": source["accession"],
                "title": source["title"],
                "doi": source.get("doi"),
                "url": f"https://psi.nasa.gov/physci/repo/data/studies/{source['accession']}",
                "filename": filename,
                "sha256": metadata["checksum"],
                "status": "validated_local_table",
            }
            # Existing sources are preserved; new source identities are additive.
            if not evidence.db.execute(
                "SELECT 1 FROM sources WHERE source_id=?", (sid,)
            ).fetchone():
                evidence.add_source(source_row)
            document = f"{sid}-targeted-table-v1"
            evidence.add_document(document, sid, source["title"])
            run_column = (
                headers.index("As Run Test #") if dataset["investigation"] == "BASS" else None
            )
            counts = Counter(
                row[run_column]
                for row in rows
                if run_column is not None and len(row) == len(headers)
            )
            for ordinal, row in enumerate(rows, 2):
                eid = f"E-targeted-{sid}-{metadata['checksum'][:16]}-row-{ordinal}"
                text = json.dumps(dict(zip(headers, row)), ensure_ascii=False)
                evidence.add_passage(
                    {
                        "evidence_id": eid,
                        "document_id": document,
                        "page": None,
                        "section": "Experimental table; logical CSV row " + str(ordinal),
                        "text": text,
                        "start_offset": ordinal,
                        "end_offset": ordinal,
                        "raw_file": filename,
                        "checksum": metadata["checksum"],
                    }
                )
                if len(row) != len(headers):
                    staged.append(
                        {
                            "row_ordinal": ordinal,
                            "values": row,
                            "reason": "ragged_schema",
                            "evidence_id": eid,
                        }
                    )
                    continue
                register_cells(evidence, eid, metadata, ordinal, headers, row)
                values = dict(zip(headers, row))
                disposition = "REVIEW_REQUIRED"
                reason = {
                    "FLEX-2": "configuration ranges and alternatives; no individual run identifier",
                    "SAFFIRE-II": "sample and camera rows; mixed gravity columns and qualitative metrics require scoped mapping",
                    "SAFFIRE-III": "sample identifiers are not demonstrated individual run identifiers",
                    "SAME": "sample rows; weight-loss rate requires scientific role and sample-run adjudication",
                    "SAME-R": "trial and aging quantities; run/sample context and scientific roles require review",
                    "SPICE": "repeated time/fuel rows; no demonstrated stable run identifier",
                }.get(dataset["investigation"], "missing or repeated as-run identifier")
                if (
                    run_column is not None
                    and row[run_column].strip()
                    and counts[row[run_column]] == 1
                    and values.get("Date")
                    and values.get("Sample #")
                ):
                    run_id = f"{sid}-as-run-{row[run_column]}"
                    record = {
                        "type": "ExperimentalRunRecord",
                        "id": run_id,
                        "investigation_id": sid,
                        "source_id": sid,
                        "reported_test_id": values["Test #"],
                        "reported_sample_id": values["Sample #"],
                        "reported_date": values["Date"],
                        "reported_material_description": values["Fuel Sample Material"],
                        "evidence_refs": [{"evidence_id": eid, "source_id": sid}],
                        "scientific_scope": "as-run identity only; gravity, material identity and measured responses not inferred",
                    }
                    canonical.append(record)
                    published.append(run_id)
                    disposition = "PUBLISHED_IDENTITY_ONLY"
                    reason = "unique explicit As Run Test #, source sample and date; no scientific response mapping"
                staged.append(
                    {
                        "row_ordinal": ordinal,
                        "source_values": values,
                        "evidence_id": eid,
                        "disposition": disposition,
                        "reason": reason,
                    }
                )
            if published:
                canonical.insert(
                    0,
                    {
                        "type": "InvestigationRecord",
                        "id": sid,
                        "source_id": sid,
                        "title": source["title"],
                        "evidence_refs": [
                            {
                                "evidence_id": f"E-targeted-{sid}-{metadata['checksum'][:16]}-row-2",
                                "source_id": sid,
                            }
                        ],
                    },
                )
            reports.append(
                {
                    "investigation": dataset["investigation"],
                    "source_id": sid,
                    **metadata,
                    "original_headers": headers,
                    "rows_examined": len(rows),
                    "duplicate_rows": len(rows) - len({tuple(r) for r in rows}),
                    "published_runs": len(published),
                    "published_ids": published,
                    "staged_rows": sum(
                        r.get("disposition") != "PUBLISHED_IDENTITY_ONLY" for r in staged
                    ),
                    "record_type": "explicit as-run identity"
                    if published
                    else "configuration/sample/trial/acquisition candidates",
                    "validation_authority": "ENGINEERING_SOURCE_CONTRACT_REVIEW; NOT independent scientist review",
                    "rows": staged,
                }
            )
    canonical_path = ROOT / "data/canonical/phase3c_targeted_psi_records_v1.json"
    if canonical_path.exists():
        raise FileExistsError(canonical_path)
    canonical_path.write_text(json.dumps(canonical, indent=2))
    for row in evidence.db.execute("SELECT locator_json FROM structured_cells"):
        locator = json.loads(row[0])
        provenance.append({"locator": locator, "round_trip": round_trip(locator, ROOT)})
    write("psi_publication", reports)
    write("cell_provenance", provenance)


def evaluate(evidence):
    existing_evidence = EvidenceRegistry(
        ROOT / "data/index/phase3c_targeted_existing_snapshot_v2.sqlite"
    )
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "false"
    store = project_legacy(ROOT, existing_evidence)
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "false"
    baseline_store = project_legacy(ROOT, existing_evidence)
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    fields = []
    for row in store.source_enrichment_report["mapped"]:
        original = row["original"]
        refs = original["evidence_refs"]
        source_matches = []
        for ref in refs:
            passage = evidence.resolve(ref["evidence_id"])
            headers, values = source_rows(passage, ROOT)
            source_matches.append(
                {
                    "evidence_id": ref["evidence_id"],
                    "unique_row_resolved": headers is not None,
                    "headers": headers,
                    "values": values,
                }
            )
        fields.append(
            {
                "record_id": row["record_id"],
                "kind": original["kind"],
                "original": original,
                "qualifiers": row["qualifiers"],
                "source_checks": source_matches,
                "source_value_preserved": store.payload(row["record_id"])["qualifiers"][
                    "original_record"
                ]
                == original,
                "scientific_role_review": "TECHNICAL_RULE_REVIEW; independent review pending",
            }
        )
    write("executable_field_audit", fields)
    unresolved = [
        r
        for r in json.loads((ART / "phase3c_enrichment_field_inventory_v1.json").read_text())
        if r["disposition"] == "REVIEW_REQUIRED"
    ]
    write(
        "field_resolutions",
        {
            "initial_counts": dict(Counter(r["kind"] for r in unresolved)),
            "scientifically_resolved": 0,
            "remaining_count": len(unresolved),
            "rows": unresolved,
            "dispositions": {
                "initial_carbon_dioxide": "Original header CO; imported CO2 kind lacks authority. Keep quarantined; no CO/CO2 assumption.",
                "burning_rate": "Original header mm; no documented denominator. Keep quarantined.",
                "gmt": "time/scheduling metadata; no science observation mapping",
                "flow_restrictor": "apparatus setting; calibration unavailable",
                "fan_display": "instrument display; calibration unavailable",
                "air_display": "instrument display; calibration unavailable",
                "total_frames_shot": "acquisition count; no observation mapping",
            },
        },
    )
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "true"
    expanded = project_legacy(ROOT, evidence)
    intents = []
    for query in [
        "BASS tests",
        "BASS-II tests",
        "BASS and BASS-II tests",
        "Does acrylic mean PMMA?",
        "Is nitrogen equivalent to helium?",
        "What did NASA observe about suppression?",
        "What has NASA reported about suppressing PMMA fires in microgravity?",
    ]:
        mentions = ["observations"] if "observe" in query else []
        intent = resolve_minimal(
            MinimalInterpretationV2(requested_information=mentions),
            expanded.registry,
            language,
            query=query,
        )
        result = execute_native(
            intent, query, expanded, evidence, hierarchical=True, relational=True
        )
        intents.append(
            {
                "original_query": query,
                "intent": intent.model_dump(mode="json"),
                "direct": result.bundle.direct_evidence,
                "related": result.bundle.related_evidence,
                "metadata": result.bundle.retrieval_metadata,
            }
        )
    write("query_intents", intents)
    cases = json.loads((ART / "phase3c_related_cases_v1.json").read_text())
    results, proposals = [], []
    for case in cases:
        intent = QueryIntentV2.model_validate(case["intent"])
        row = {
            "case_id": case["case_id"],
            "original_query": case["query"],
            "frozen_intent": case["intent"],
            "variants": {},
        }
        for label, graph in [("A", baseline_store), ("B", store), ("C", expanded)]:
            candidate_registry = evidence if label == "C" else existing_evidence
            result = execute_native(
                intent, case["query"], graph, candidate_registry, hierarchical=True, relational=True
            )
            row["variants"][label] = {
                "direct": result.bundle.direct_evidence,
                "related": result.bundle.related_evidence,
                "evidence_ids": [p["evidence_id"] for p in result.bundle.evidence_passages],
                "presentation": result.bundle.retrieval_metadata["related_presentation"],
                "timings_ms": result.latency_ms,
                "identity_recovered": bool(
                    {p["evidence_id"] for p in result.bundle.evidence_passages}
                    & set(case.get("expected_evidence_ids", []))
                )
                if case.get("objective_identity_case")
                else None,
                "false_direct": bool(result.bundle.direct_evidence)
                if case.get("objective_no_direct")
                else None,
            }
            if label == "B":
                for candidate in result.bundle.related_evidence:
                    proposals.append(
                        {
                            "case_id": case["case_id"],
                            "original_query": case["query"],
                            "candidate": candidate,
                            "label": None,
                            "independent_review": "PENDING",
                            "proposal_authority": "ENGINEERING_CANDIDATE_PACKET",
                            "claim_applicability": "requires scientific review; matching material is insufficient",
                        }
                    )
        results.append(row)
    write("scientific_cases", results)
    write(
        "related_review",
        {
            "scientific_precision": "NOT_MEASURABLE",
            "independent_labels": 0,
            "candidate_universe": proposals,
            "label_options": [
                "DIRECT_RELEVANT",
                "RELATED_USEFUL",
                "CONTEXTUAL_USEFUL",
                "TOPICALLY_RELATED_BUT_NOT_ANSWERING",
                "IRRELEVANT",
                "SCIENTIFICALLY_MISLEADING",
                "INSUFFICIENT_CONTEXT",
            ],
        },
    )
    write(
        "shacl",
        {
            "canonical": bool(
                validate(
                    Graph().parse(ROOT / "data/canonical/graph.ttl"),
                    shacl_graph=str(ROOT / "ontology/shapes.ttl"),
                )[0]
            ),
            "native": bool(
                validate(expanded.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
            ),
        },
    )
    spec = importlib.util.spec_from_file_location(
        "targeted_checks", ROOT / "scripts/phase3c_native_benchmarks.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ART = ART / f"phase3c_targeted_native_checks_{VERSION}"
    module.ART.mkdir()
    module.check_freeze = lambda: None
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "false"
    module.dynamic()
    module.dynamic(postfreeze=True)
    module.EvidenceRegistry = lambda path: existing_evidence
    module.parity()


if __name__ == "__main__":
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    if "datasets" in sys.argv:
        datasets(registry)
    elif "evaluate" in sys.argv:
        evaluate(registry)
