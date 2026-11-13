"""Real NASA narrative, additive development contracts, fresh bounded advisory receipts."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from phase3c_curation_pilot import write

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.scientific_correction import generate_clarifications, interpret_correction
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def run(directory, workspace, live=False):
    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    os.environ["AUTONOMOUS_RESEARCH_ENABLED"] = "false"
    principal = "development-scientist"
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    curator = CurationService(workspace, registry, ReviewPolicy(frozenset({principal}), True))
    original = next((ROOT / "data/raw/autonomous").glob("ntrs-20260003546-*.pdf"))
    saved = curator.submit(
        "Depressurization attribution validation",
        "Isolated source-backed scientific subtype and author attribution; no new physical inference",
        [(original.name, original.read_bytes())],
        principal,
    )
    package = saved["package"]
    pid = package["id"]
    write(directory, "submitted", saved)
    questions = generate_clarifications(curator, pid, Settings(root=workspace), model_enabled=live)
    write(directory, "generated_questions", questions)
    while remaining := curator.questions(curator.get(pid)["package"]):
        q = remaining[0]
        curator.clarification(
            pid,
            q["id"],
            "documentary",
            "Unselected source propositions remain documentary; attribution is reviewed separately",
            principal,
        )
    observation = next(
        s
        for s in package["statements"]
        if "Several test samples maintained a flame" in " ".join(s["text"].split())
    )
    conclusion = next(
        s
        for s in package["statements"]
        if "This demonstrated" in " ".join(s["text"].split())
        and "insufficient to extinguish" in " ".join(s["text"].split())
    )
    assert observation["epistemic"] == "measured_observation"
    assert conclusion["epistemic"] == "author_reported_conclusion"
    eids = sorted(set(observation["evidence_ids"] + conclusion["evidence_ids"]))
    cls = {
        "kind": "class",
        "id": "SustainedFlameObservation",
        "name": "Sustained flame observation",
        "definition": "An author-reported observation of flame persistence during an identified intervention; it does not assert steady burning or a confirmed mechanism",
        "purpose": "Distinguish reported persistence observations from phenomenon identity and author interpretations",
        "parent": "ReportedObservation",
        "intended_instances": [observation["id"]],
        "query_terms": ["sustained flame observations", "flame persistence observations"],
        "why_existing_insufficient": "StableBurning is a phenomenon, not this epistemic observation category; generic ReportedObservation does not preserve the reviewed subtype",
        "constraints": {},
        "evidence_ids": eids,
        "impact": "Additive development classification; historical identities and semantics retained",
    }
    curator.propose_extension(pid, cls, principal)
    curator.approve_extension(pid, cls["id"], principal)
    relation = {
        "kind": "object_property",
        "id": "authorInterpretsObservation",
        "name": "Author interprets observation",
        "definition": "The source author explicitly interprets the identified observation; this is attribution, not causality or independent confirmation",
        "purpose": "Preserve the explicit 'This demonstrated' textual attribution in the source",
        "why_existing_insufficient": "Existing membership, material and condition relations cannot encode the author's observation-to-interpretation attribution",
        "domain": ["NASAConclusion"],
        "range": ["ReportedObservation"],
        "direction": "source_to_target",
        "scope": "The source paragraph reports persistence at 4 psia and continued burning; the author's following sentence interprets that described experimental outcome",
        "evidence_requirements": "Exact observation and author interpretation spans plus the paragraph explicitly linking them",
        "transitive": False,
        "constraints": {},
        "evidence_ids": eids,
        "impact": "Compatible noncausal addition; no historical records rewritten",
    }
    curator.propose_extension(pid, relation, principal)
    curator.approve_extension(pid, relation["id"], principal)
    operations = [
        {"action": "scope", "subject": observation["id"], "objects": [pid]},
        {"action": "scope", "subject": conclusion["id"], "objects": [pid]},
        {
            "action": "classify_statement",
            "subject": observation["id"],
            "class_id": cls["id"],
            "epistemic": "measured_observation",
            "evidence_ids": eids,
        },
        {
            "action": "add_relation",
            "subject": conclusion["id"],
            "relation": relation["id"],
            "object": observation["id"],
            "evidence_ids": eids,
        },
    ]
    preview = curator.preview_correction(
        pid,
        operations,
        "Development review of explicit current-source author attribution; broader applicability remains investigation-level",
        principal,
    )
    write(directory, "scientific_preview", preview)
    changed = curator.apply_correction(preview, principal)
    write(directory, "reviewed", changed)
    write(directory, "publication", curator.approve_and_publish(pid, changed["digest"], principal))
    assistant = Phase3AssistantService(
        root=workspace, settings=Settings(root=workspace, nvidia_api_key=None)
    )
    responses = [
        assistant.answer_query(q).model_dump(mode="json")
        for q in [
            "Which sustained flame observations describe depressurization?",
            "What conclusions were reported in Depressurization attribution validation?",
            "What observations were reported in Depressurization attribution validation under microgravity?",
        ]
    ]
    write(directory, "queries", responses)
    assert any(
        r["id"] == observation["id"]
        for r in responses[0]["evidence_bundle"]["experimental_observations"]
    )
    assert any(
        r.get("id") == conclusion["id"]
        and any(edge["relation"] == relation["id"] for edge in r.get("approved_relationships", []))
        for r in responses[1]["evidence_bundle"]["semantic_records"]
    )
    store = project_legacy(workspace, registry)
    write(
        directory,
        "ontology_and_evidence",
        {
            "class": cls,
            "relationship": relation,
            "observation": observation,
            "conclusion": conclusion,
            "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
            "approved_relation": sorted(store.relations(conclusion["id"], relation["id"])),
            "evidence_resolves": all(registry.resolve(eid) for eid in eids),
            "scientific_review_authority": "isolated development contract validation; no independent expert label",
        },
    )
    before = curator.get(pid)
    for _ in range(5):
        curator.regenerate(before["package"])
        assert curator.save(before["package"], principal)["digest"] == before["digest"]
    write(
        directory,
        "regeneration",
        {
            "cycles": 5,
            "stable_digest": before["digest"],
            "exclusions": len(before["package"]["exclusions"]),
            "relations": len(before["package"]["relations"]),
        },
    )
    write(directory, "rollback", curator.rollback(pid, principal))
    assert cls["id"] not in project_legacy(workspace, registry).registry.class_metadata
    write(directory, "reactivation", curator.publish(pid, changed["digest"], principal))
    # Free-text fallback is tested separately against the previous real-source prose draft.
    other = json.loads((directory.parent / "prose/prose_reviewed.json").read_text())["package"]
    tentative = next(
        s
        for s in other["statements"]
        if s["epistemic"] == "tentative_interpretation" and s.get("included")
    )
    instructions = [
        "Retain only as documentary evidence the tentative interpretation statement "
        + tentative["id"]
        + ". Exclude that scientific assertion; do not change any other statement.",
        "Replace the original source wording with 'Nomex extinguished in all four tests' and publish it as an observation.",
        "Fix the scientific scope of the conclusions; the right experimental group is unclear.",
    ]
    results = []
    for index, instruction in enumerate(instructions):
        result = interpret_correction(
            curator,
            other["id"],
            instruction,
            principal,
            Settings(root=workspace),
            model_enabled=live,
        )
        if "proposal" in result and index == 0:
            corrected = curator.apply_correction(result["proposal"], principal)
            result["applied_digest"] = corrected["digest"]
            result["validation_after_application"] = curator.validate(corrected["package"])
            result["publication"] = curator.approve_and_publish(
                other["id"], corrected["digest"], principal
            )
            result["rollback"] = curator.rollback(other["id"], principal)
        results.append(result)
    write(directory, "natural_language_results", results)
    write(
        directory,
        "integrity",
        {
            "sqlite": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": [list(r) for r in registry.db.execute("PRAGMA foreign_key_check")],
            "fts_missing": registry.db.execute(
                "SELECT count(*) FROM passages WHERE evidence_id NOT IN (SELECT evidence_id FROM passages_fts)"
            ).fetchone()[0],
        },
    )
    registry.db.close()
    print(
        json.dumps(
            {
                "new_class": cls["id"],
                "new_relation": relation["id"],
                "query_count": len(responses),
                "fallback_outcomes": [r.get("receipt", {}).get("outcome") for r in results],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    run(args.directory, args.workspace, args.live)
