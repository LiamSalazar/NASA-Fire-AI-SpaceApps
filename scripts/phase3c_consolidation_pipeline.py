"""Real source-to-native-graph demonstration and bounded context interpretation."""

import json
import os

from phase3c_consolidation import ROOT, save
from phase3c_real_context import configure

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.autonomous import KnowledgeMaintenance
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.context import NvidiaContextInterpreter
from nasa_fire_ai.llm.interfaces import ProviderFailure
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def main():
    configure()
    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = "true"
    os.environ["SCIENTIFIC_SYNTHESIS_ENABLED"] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    acquired = json.loads(
        (ROOT / "artifacts/phase3c_consolidation_acquisition_v2.json").read_text()
    )
    document_id = acquired["document_id"]
    pipeline = KnowledgeMaintenance(ROOT, evidence)
    pages = [evidence.resolve(eid) for eid in acquired["evidence_ids"]]
    selected = [page for page in pages if page["page"] in {1, 3, 4, 7, 12}]
    passages = [
        {
            "evidence_id": page["evidence_id"],
            "source_id": acquired["source_id"],
            "section": page["section"],
            "text": page["text"],
        }
        for page in selected
    ]
    interpreter = NvidiaContextInterpreter(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    proposals, failure = [], None
    try:
        proposals = interpreter.interpret(
            query="Identify source-backed experimental conditions and explicit scope exceptions. Separate author's actual tests from prior cited experiments, simulations, spacecraft risks and recommendations. Do not propagate a cited study's gravity to this whole publication.",
            entities=[document_id],
            passages=passages,
            allowed_predicates=["hasGravityCondition", "hasMaterial"],
        )
    except (ProviderFailure, ValueError) as error:
        failure = type(error).__name__
    outcomes = []
    for proposal in proposals:
        if proposal.validation_status == "REJECTED":
            outcomes.append({"proposal": proposal.model_dump(mode="json"), "status": "REJECTED"})
            continue
        for span in proposal.support_spans:
            outcomes.append(
                {
                    "proposal": proposal.model_dump(mode="json"),
                    "staging": pipeline.stage(
                        {
                            "evidence_id": span["evidence_id"],
                            "evidence_span": span["text"],
                            "contextual_proposal": proposal.model_dump(mode="json"),
                            "membership_verification": "UNRESOLVED; document identity does not establish experimental membership",
                        }
                    ),
                }
            )
            break
    fabricated = pipeline.stage(
        {
            "evidence_id": acquired["evidence_ids"][0],
            "evidence_span": "NASA proved all spacecraft flames disappear immediately.",
        }
    )
    store = project_legacy(ROOT, evidence)
    service = Phase3AssistantService(settings=settings)
    service.registry = evidence
    response = service.answer_query(
        "Find NASA publications about risks of depressurization as a fire suppression technique in spacecraft."
    )
    # This source adds documentary knowledge, not reviewed experimental facts.
    source_candidates = evidence.search(
        "depressurization suppression", eligible_ids=acquired["evidence_ids"], limit=3
    )
    save(
        "source_to_graph",
        {
            "acquisition": acquired,
            "source_window": passages,
            "fresh_context_inference": getattr(interpreter, "last_receipt", {}),
            "provider_failure": failure,
            "proposals": outcomes,
            "fabricated_proposal": fabricated,
            "native_document_classes": sorted(store.classes(document_id)),
            "native_document_evidence": store.evidence(document_id),
            "actual_service": response.model_dump(mode="json"),
            "documentary_source_candidates": source_candidates,
            "scientific_facts_published": 0,
            "independent_expert_review": None,
        },
    )
    print(
        {
            "proposals": len(proposals),
            "error": failure,
            "classes": sorted(store.classes(document_id)),
            "retrieved_in_service": bool(
                set(acquired["evidence_ids"])
                & {p["evidence_id"] for p in response.evidence_bundle.evidence_passages}
            ),
            "invalid_proposal": fabricated["status"],
        },
        flush=True,
    )


if __name__ == "__main__":
    main()
