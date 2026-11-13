"""Isolated first-pass new-source extraction; no scientific publication."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import stage_relation_proposal
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner

OUT = ROOT / "artifacts/phase3c_knowledge_new_source_first_pass_v1.jsonl"
if OUT.exists():
    raise FileExistsError(OUT)
settings = Settings()
registry = EvidenceRegistry(
    ROOT / "artifacts/phase3c_knowledge_new_source_isolated/evidence.sqlite"
)
adapter = NvidiaStructuredClient(
    settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
)
reasoner = NemotronControlledReasoner(
    adapter.client,
    settings.nvidia_phase3_model,
    load_semantic_registry(ROOT / "domain/semantic_registry.yaml"),
)
for rid, page_number in [("20210017780", 5), ("20220012861", 2)]:
    parsed = json.loads(
        (ROOT / f"artifacts/phase3c_knowledge_ntrs_{rid}_parsed_v1.json").read_text()
    )
    sid = "new-ntrs-" + rid
    registry.add_source(
        {
            "source_id": sid,
            "nasa_id": rid,
            "url": "https://ntrs.nasa.gov/citations/" + rid,
            "sha256": parsed["sha256"],
            "status": "PARSED_REVIEW_REQUIRED",
        }
    )
    registry.add_document(sid, sid, rid)
    for page in parsed["pages"]:
        eid = sid + "-page-" + str(page["physical_pdf_page"])
        registry.add_passage(
            {
                "evidence_id": eid,
                "document_id": sid,
                "page": page["physical_pdf_page"],
                "text": page["text"],
                "section": None,
                "start_offset": 0,
                "end_offset": len(page["text"]),
                "raw_file": f"data/raw/phase3c-knowledge-ntrs-{rid}.pdf",
                "checksum": parsed["sha256"],
            }
        )
    passage = registry.resolve(sid + "-page-" + str(page_number))
    row = {
        "nasa_id": rid,
        "evidence_id": passage["evidence_id"],
        "source_digest": parsed["sha256"],
        "physical_pdf_page": page_number,
        "page_location_verified": True,
        "new_calls": 1,
        "execution_mode": "NEW_LIVE_REQUEST",
        "prompt_version": "knowledge-new-source-v1",
        "input_digest": hashlib.sha256(passage["text"].encode()).hexdigest(),
        "scientific_gold": None,
        "approved_facts": 0,
        "evaluation_role": "EXPOSED_DEVELOPMENT_SOURCE_FIRST_PASS",
    }
    system = 'Return JSON {"relations":[{"subject_mention":string,"predicate_candidate":string,"object_mention":string,"supporting_span":string}]}. Propose at most two explicit source relations, never scientific inferences. All mentions and spans must be exact substrings. Table column alignment is not guaranteed: do not infer sample-to-value assignments. Experimental conditions are not observed measurements. Proposed semantics require human review.'
    try:
        output, usage = reasoner._json_call(system, passage["text"], 650)
        row.update(
            {"output": output, "usage": usage, "status": "PASS", "staged": [], "rejected": []}
        )
        for proposal in output.get("relations", []):
            try:
                row["staged"].append(
                    stage_relation_proposal(
                        {**proposal, "source_id": sid, "evidence_id": passage["evidence_id"]},
                        registry,
                    )
                )
            except (ValueError, TypeError) as exc:
                row["rejected"].append({"proposal": proposal, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001 - bounded external service boundary
        row.update({"status": "FAIL", "error": type(exc).__name__})
    with OUT.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    print(json.dumps({"nasa_id": rid, "status": row["status"]}), flush=True)
