"""Fresh engineering gates and original-source checks for the autonomous campaign."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pyshacl import validate
from rdflib import Graph

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.autonomous import registry_checks
from nasa_fire_ai.ingestion.scientific_proposals import CONTRACT, stage_proposition
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS

VERSION = os.getenv("PHASE3C_AUTONOMY_VERSION", "v1")


def main():
    commands = []
    for name, command in [
        ("format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("pytest", ["uv", "run", "pytest", "-q"]),
    ]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        log = ROOT / "artifacts" / f"phase3c_autonomy_{name}_final_{VERSION}.txt"
        with log.open("x") as stream:
            stream.write(result.stdout + result.stderr)
        commands.append(
            {"command": command, "exit_code": result.returncode, "log": str(log.relative_to(ROOT))}
        )
        print(name, result.returncode, flush=True)
    for flag in [
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
    ]:
        os.environ[flag] = "true"
    registry = EvidenceRegistry(Settings().registry_path)
    store = project_legacy(ROOT, registry)
    shacl = {}
    for label, graph, shape in [
        ("canonical", Graph().parse(ROOT / "data/canonical/graph.ttl"), "shapes.ttl"),
        ("native", store.graph, "semantic_shapes.ttl"),
        ("taxonomy", store.graph, "semantic_taxonomy_shapes.ttl"),
    ]:
        conforms, _, report = validate(graph, shacl_graph=str(ROOT / "ontology" / shape))
        shacl[label] = {"conforms": bool(conforms), "report": report}
        print(label, bool(conforms), flush=True)
    frozen = json.loads((ROOT / "artifacts/phase3c_consolidation_freeze_v1.json").read_text())[
        "files"
    ]
    changed = [
        relative
        for relative, digest in frozen.items()
        if not (ROOT / relative).exists()
        or hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest
    ]
    baseline = json.loads((ROOT / "artifacts/phase3c_autonomy_baseline_v1.json").read_text())[
        "files"
    ]
    immutable = [
        row
        for row in baseline
        if row["path"].startswith(
            ("data/raw/", "data/canonical/", "evals/", "artifacts/phase3c_consolidation")
        )
    ]
    drift = [
        row["path"]
        for row in immutable
        if hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() != row["sha256"]
    ]
    missing_refs = sorted(
        {
            str(eid)
            for eid in store.graph.objects(None, NS.evidenceRef)
            if registry.resolve(str(eid)) is None
        }
    )
    staging = []
    for candidate in registry.staged_semantic_candidates():
        proposal = candidate.get("proposal", {})
        if proposal.get("contract") != CONTRACT or candidate["review_status"] != "PENDING":
            continue
        passage = registry.resolve(candidate["evidence_id"])
        loc = proposal["source_location"]
        staging.append(
            {
                "candidate_id": candidate["candidate_id"],
                "original_span_matches": bool(
                    passage
                    and passage["text"][loc["start_offset"] : loc["end_offset"]]
                    == proposal["original_wording"]
                ),
                "source_digest_matches": bool(
                    passage and passage["checksum"] == proposal["source_digest"]
                ),
                "canonical": candidate["candidate_id"] in store.entities(),
            }
        )
    acquisition = json.loads(
        (ROOT / "artifacts/phase3c_consolidation_acquisition_v2.json").read_text()
    )
    import pymupdf

    pages = []
    with pymupdf.open(ROOT / acquisition["raw_file"]) as pdf:
        for eid in acquisition["evidence_ids"]:
            passage = registry.resolve(eid)
            pages.append(
                {
                    "evidence_id": eid,
                    "page": passage["page"],
                    "raw_page_matches": pdf[passage["page"] - 1].get_text() == passage["text"],
                }
            )
    # A historical spacecraft discussion is present in this Earth-based report;
    # membership cannot establish its tests as microgravity.
    first = registry.resolve(acquisition["evidence_ids"][2])
    negative = stage_proposition(
        {
            "class_id": "ExperimentalCondition",
            "evidence_id": first["evidence_id"],
            "quote": first["text"],
            "gravity": "microgravity",
            "scope": "current study",
        },
        registry,
        store.registry,
    )
    source_units = json.loads(
        (ROOT / "artifacts/phase3c_real_context_source_units_v8.json").read_text()
    )["units"]
    original_units = []
    import csv

    for unit in source_units.values():
        row = registry.resolve(unit["evidence_id"])
        path = Path(row["raw_file"])
        if not path.is_absolute():
            path = ROOT / "data/raw" / path
        digest_valid = hashlib.sha256(path.read_bytes()).hexdigest() == row["checksum"]
        if row.get("source_cells"):
            records = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
            exact = all(
                records[c["row_ordinal"] - 1][c["column_ordinal"] - 1] == c["original_value"]
                for c in row["source_cells"]
            )
        else:
            if path.suffix.lower() == ".pdf":
                with pymupdf.open(path) as pdf:
                    text = pdf[row["page"] - 1].get_text()
            else:
                text = path.read_text()
            exact = text[row["start_offset"] : row["end_offset"]] == unit["text"]
        original_units.append(
            {
                "evidence_id": row["evidence_id"],
                "digest_valid": digest_valid,
                "exact_original_value_or_span": exact,
            }
        )
    value = {
        "commands": commands,
        "shacl": shacl,
        "registry": registry_checks(registry),
        "historical_frozen_count": len(frozen),
        "historical_changes": changed,
        "campaign_immutable_count": len(immutable),
        "campaign_immutable_changes": drift,
        "missing_graph_references": missing_refs,
        "staged_propositions": staging,
        "source_digest": acquisition["content_sha"],
        "new_report_pages": pages,
        "original_units": original_units,
        "negative_microgravity_proposal": negative,
        "scientific_precision": "NOT_MEASURABLE",
        "warning_classification": "rdflib Dataset.default_context deprecation inside installed rdflib; unchanged unsuppressed engineering warning",
    }
    with (ROOT / f"artifacts/phase3c_autonomy_integrity_{VERSION}.json").open("x") as stream:
        json.dump(value, stream, indent=2)
    if (
        any(c["exit_code"] for c in commands)
        or not all(s["conforms"] for s in shacl.values())
        or changed
        or drift
        or missing_refs
        or not all(
            s["original_span_matches"] and s["source_digest_matches"] and not s["canonical"]
            for s in staging
        )
        or not all(r["digest_valid"] and r["exact_original_value_or_span"] for r in original_units)
    ):
        raise RuntimeError("Engineering integrity gate failed")


if __name__ == "__main__":
    main()
