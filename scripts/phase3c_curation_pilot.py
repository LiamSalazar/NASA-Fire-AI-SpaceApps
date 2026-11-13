"""Real-source incorporation receipts. All approvals belong to an isolated test principal."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from curate_research import initialize_workspace

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.scientific_correction import interpret_correction
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def write(directory, name, value):
    path = directory / (name + ".json")
    with path.open("x") as handle:
        json.dump(value, handle, indent=2)


def run(directory, live=False):
    workspace = initialize_workspace(directory / "workspace")
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    registry.db.execute("ATTACH DATABASE ? AS frozen", (str(ROOT / "data/index/evidence.sqlite"),))
    for table in (
        "sources",
        "documents",
        "passages",
        "evidence_refs",
        "evidence_locations",
        "structured_cells",
        "document_metadata",
    ):
        registry.db.execute(f"INSERT INTO main.{table} SELECT * FROM frozen.{table}")
    registry.db.execute(
        "INSERT INTO passages_fts(evidence_id,text) SELECT evidence_id,text FROM passages"
    )
    registry.db.commit()
    registry.db.execute("DETACH DATABASE frozen")
    principal = "development-scientist"
    curator = CurationService(workspace, registry, ReviewPolicy(frozenset({principal}), True))
    for key, value in {
        "NATIVE_V2_QUERY_ENABLED": "true",
        "SCIENTIFIC_SYNTHESIS_ENABLED": "true",
        "NEMOTRON_SCIENTIFIC_SELECTION_ENABLED": "false",
        "AUTONOMOUS_RESEARCH_ENABLED": "false",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED": "false",
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED": "false",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED": "false",
    }.items():
        os.environ[key] = value
    settings = Settings(root=workspace, nvidia_api_key=None)
    assistant = Phase3AssistantService(root=workspace, settings=settings)
    # No source-derived values/rows edited. The two pretest camera rows are explicit exclusions.
    submitted = curator.submit(
        "Saffire-I isolated incorporation pilot",
        "Review the public PSI-98 table and methodology in an isolated re-import.",
        [
            (p.name, p.read_bytes())
            for p in [
                ROOT / "data/raw/psi/PSI-98_experimental_table.csv",
                ROOT / "data/raw/psi/PSI-98_metadata.json",
            ]
        ],
        principal,
    )
    pid = submitted["package"]["id"]
    write(directory, "submitted", submitted)
    write(directory, "templates", curator.templates())
    write(directory, "clarifications_initial", curator.questions(submitted["package"]))
    before = assistant.answer_query(
        "Which conditions applied to Saffire-I isolated incorporation pilot?"
    )
    historical_before = assistant.answer_query("Which conditions applied to Saffire-I S1 and S2?")
    write(directory, "query_before", before.model_dump(mode="json"))
    write(directory, "historical_before", historical_before.model_dump(mode="json"))
    runs = [e for e in submitted["package"]["entities"] if e["class_id"] == "ExperimentalRun"]
    exclusions = [
        {
            "action": "exclude",
            "subject": e["id"],
            "reason": "Original table identifies pre-test flow visualization/camera data, not combustion runs",
        }
        for e in runs
        if e["label"] not in {"S1", "S2"}
    ]
    preview = curator.preview_correction(
        pid,
        exclusions,
        "Retain pre-test visualization rows as documentary evidence; they are not combustion runs.",
        principal,
    )
    write(directory, "exceptions_preview", preview)
    curator.apply_correction(preview, principal)
    current = curator.get(pid)
    table = current["package"]["tables"][0]
    curator.clarification(
        pid,
        "table-role:" + table["id"],
        "ExperimentalRun",
        "S1 and S2 report executed burns; pretest rows excluded",
        principal,
    )
    # Meaningful previously unmodeled property. No direct ontology file edits for this study.
    extension = {
        "property": {
            "property_id": "SampleThickness",
            "dimension": "length",
            "canonical_unit": "m",
            "aliases": ["sample thickness"],
        },
        "definition": "Thickness of the fuel specimen as reported in the PSI table; original cm values are retained.",
        "why_existing_insufficient": "The current quantity registry models velocity, oxygen, pressure and flow direction, but no thickness quantity.",
        "domain": "ExperimentalRun",
        "range": "numeric",
        "evidence_ids": [table["evidence_ids"][0]],
        "impact": "Compatible addition; existing geometry descriptions and scientific identities remain unchanged.",
        "validation_contract": "SemanticRegistry.validate",
    }
    write(directory, "extension_proposal", extension)
    curator.propose_extension(pid, extension, principal)
    curator.approve_extension(pid, "SampleThickness", principal)
    question_receipts = []
    while True:
        questions = curator.questions(curator.get(pid)["package"])
        if not questions:
            break
        q = questions[0]
        if q["kind"] == "context":
            selection, reason, unit = (
                "campaign",
                "PSI-98 metadata explicitly identifies the Saffire flight campaign and microgravity environment",
                None,
            )
        elif q["kind"] == "mapping" and q["id"].endswith(":Sample Thickness (cm)"):
            selection, reason, unit = (
                "SampleThickness",
                "Thickness column and cm unit are explicit source fields",
                None,
            )
        elif q["kind"] == "mapping" and q["id"].endswith(":Percent O2"):
            selection, reason, unit = (
                "OxygenConcentration",
                "Percent O2 explicitly denotes oxygen concentration as percent",
                "%",
            )
        elif q["kind"] == "mapping":
            selection, reason, unit = (
                "documentary",
                "Retain original ancillary dimensions, ignition, burn-time and camera fields without asserting unreviewed quantity contracts",
                None,
            )
        elif q["kind"] == "scope":
            selection, reason, unit = (
                "documentary",
                "Metadata prose may summarize other campaigns or general objectives; no unsupported run-specific observation/conclusion attribution",
                None,
            )
        else:
            raise ValueError("Pilot requires another scientific decision: " + q["question"])
        changed = curator.clarification(pid, q["id"], selection, reason, principal, unit)
        question_receipts.append(
            {
                "question": q,
                "selection": selection,
                "reason": reason,
                "result_digest": changed["digest"],
            }
        )
    write(directory, "clarification_receipts", question_receipts)
    # Both guided and model-interpreted correction paths run against actual source-supported runs.
    instruction = "Assign S1 and S2 to microgravity"
    result = interpret_correction(
        curator, pid, instruction, principal, Settings(root=workspace), live
    )
    write(directory, "natural_correction", result)
    if "proposal" in result:
        changed = curator.apply_correction(result["proposal"], principal)
        write(directory, "natural_correction_applied", changed)
    current = curator.get(pid)
    write(directory, "reviewed", current)
    validation = curator.validate(current["package"])
    write(directory, "validation", validation)
    if not validation["ready"]:
        raise ValueError("Real pilot blocked: " + str(validation["errors"]))
    receipt = curator.approve_and_publish(pid, current["digest"], principal)
    write(directory, "approval_publication", receipt)
    write(directory, "idempotence", curator.publish(pid, current["digest"], principal))
    queries = [
        "Which conditions applied to Saffire-I isolated incorporation pilot?",
        "Find SIBAL Fabric experiments in Saffire-I isolated incorporation pilot under microgravity",
        "Which measurements were reported in Saffire-I isolated incorporation pilot?",
        "Find SIBAL Fabric in Saffire-I isolated incorporation pilot under normal gravity",
        "What observations were reported in Saffire-I isolated incorporation pilot?",
        "What conclusions were reported in Saffire-I isolated incorporation pilot?",
        "Find SampleThickness below 0.5 cm in Saffire-I isolated incorporation pilot",
    ]
    answers = [assistant.answer_query(q).model_dump(mode="json") for q in queries]
    write(directory, "query_after", answers)
    write(
        directory,
        "historical_after",
        assistant.answer_query("Which conditions applied to Saffire-I S1 and S2?").model_dump(
            mode="json"
        ),
    )
    graph = project_legacy(workspace, registry)
    graph.graph.serialize(directory / "activated_graph.ttl", format="turtle")
    write(
        directory,
        "activated_relations",
        [
            {
                "run": e["label"],
                "material": sorted(graph.relations(e["id"], "hasMaterial")),
                "gravity": sorted(graph.relations(e["id"], "hasGravityCondition")),
                "investigation": sorted(graph.relations(e["id"], "belongsToInvestigation")),
            }
            for e in runs
            if e["label"] in {"S1", "S2"}
        ],
    )
    # Later scoped correction to a previously documentary field; source remains unchanged.
    unchanged = curator.save(current["package"], principal)
    write(
        directory,
        "unchanged_regeneration",
        {"same_digest": unchanged["digest"] == current["digest"]},
    )
    current["package"]["purpose"] += " Additional exact-version review of publication recovery."
    revised = curator.save(current["package"], principal)
    try:
        curator.publish(pid, current["digest"], principal)
    except ValueError as error:
        write(directory, "stale_approval_rejected", {"rejected": True, "reason": str(error)})
    curator.approve(pid, revised["digest"], principal)
    failed = []
    for point in ("graph", "index"):
        try:
            curator.publish(pid, revised["digest"], principal, fail_at=point)
        except RuntimeError as error:
            failed.append(
                {
                    "point": point,
                    "error": str(error),
                    "active_digest": registry.db.execute(
                        "SELECT digest FROM research_active WHERE package_id=?", (pid,)
                    ).fetchone()[0],
                    "restored_previous": registry.db.execute(
                        "SELECT digest FROM research_active WHERE package_id=?", (pid,)
                    ).fetchone()[0]
                    == current["digest"],
                }
            )
    write(directory, "failure_recovery", failed)
    write(directory, "revision_publication", curator.publish(pid, revised["digest"], principal))
    write(directory, "rollback", curator.rollback(pid, principal))
    write(
        directory,
        "history",
        [
            dict(r)
            for r in registry.db.execute(
                "SELECT package_id,version,digest,creator,created_at FROM research_packages"
            )
        ],
    )
    write(
        directory,
        "integrity",
        {
            "sqlite": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": [list(r) for r in registry.db.execute("PRAGMA foreign_key_check")],
            "fts_missing": len(
                {r[0] for r in registry.db.execute("SELECT evidence_id FROM passages")}
                - {r[0] for r in registry.db.execute("SELECT evidence_id FROM passages_fts")}
            ),
            "fts_duplicates": registry.db.execute(
                "SELECT count(*) FROM (SELECT evidence_id,count(*) c FROM passages_fts GROUP BY evidence_id HAVING c>1)"
            ).fetchone()[0],
            "new_citations_resolve": all(
                registry.resolve(eid)
                for a in answers
                for c in a["answer"]["generated_claims"]
                for eid in c["evidence_ids"]
            ),
            "raw_table_sha256": hashlib.sha256(
                (ROOT / "data/raw/psi/PSI-98_experimental_table.csv").read_bytes()
            ).hexdigest(),
            "scope": "Development approval, actual public NASA sources, no institutional NASA authorization",
        },
    )
    write(
        directory, "events", [dict(r) for r in registry.db.execute("SELECT * FROM research_events")]
    )
    print(
        json.dumps(
            {
                "directory": str(directory),
                "package": pid,
                "publication": "ACTIVE_TEST_ONLY",
                "metrics": validation["metrics"],
                "queries": len(answers),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    run(args.directory, args.live)
