"""Second real-source pilot: source-reported outcomes and uncertainty, without invented runs."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from phase3c_curation_pilot import write

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def run(directory, workspace):
    import os

    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["AUTONOMOUS_RESEARCH_ENABLED"] = "false"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    principal = "development-scientist"
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    curator = CurationService(workspace, registry, ReviewPolicy(frozenset({principal}), True))
    assistant = Phase3AssistantService(
        root=workspace, settings=Settings(root=workspace, nvidia_api_key=None)
    )
    source = next((ROOT / "data/raw/autonomous").glob("ntrs-20260003546-*.pdf"))
    saved = curator.submit(
        "Depressurization suppression source pilot",
        "Represent selected author statements from actual NTRS 20260003546; no invented run identities or gravity.",
        [(source.name, source.read_bytes())],
        principal,
    )
    pid = saved["package"]["id"]
    write(directory, "prose_submitted", saved)
    write(directory, "prose_clarifications", curator.questions(saved["package"]))
    selected = [
        s
        for s in saved["package"]["statements"]
        if any(
            term in s["text"]
            for term in (
                "extinguished in two of the four tests",
                "it was likely the lack of oxygen",
                "Future work will involve CFD",
                "Testing of Nomex showed",
            )
        )
    ]
    while questions := curator.questions(curator.get(pid)["package"]):
        q = questions[0]
        curator.clarification(
            pid,
            q["id"],
            "documentary",
            "Retain unselected/cited-study prose as documentary evidence; no unsupported experimental attribution",
            principal,
        )
    ops = [{"action": "scope", "subject": s["id"], "objects": [pid]} for s in selected]
    preview = curator.preview_correction(
        pid,
        ops,
        "The selected current-study Nomex result, tentative oxygen interpretation, author conclusion and future CFD work are reported by this investigation; individual run attribution remains unavailable.",
        principal,
    )
    write(directory, "prose_correction_preview", preview)
    changed = curator.apply_correction(preview, principal)
    write(directory, "prose_reviewed", changed)
    write(directory, "prose_validation", curator.validate(changed["package"]))
    write(
        directory,
        "prose_approval_publication",
        curator.approve_and_publish(pid, changed["digest"], principal),
    )
    queries = [
        "What observations were reported in Depressurization suppression source pilot?",
        "What conclusions were reported in Depressurization suppression source pilot?",
        "What open questions were reported in Depressurization suppression source pilot?",
    ]
    write(
        directory,
        "prose_query_after",
        [assistant.answer_query(q).model_dump(mode="json") for q in queries],
    )
    print(
        {
            "selected": len(selected),
            "source_proposals": len(saved["package"]["statements"]),
            "digest": changed["digest"],
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    args = p.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    run(args.directory, args.workspace)
