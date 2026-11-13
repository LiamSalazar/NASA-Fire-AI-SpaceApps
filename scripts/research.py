"""Standalone scientific question, review and operational status interface."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.scientific_proposals import search_staged
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("mode", choices=["ask", "review", "status"])
    parser.add_argument("question", nargs="?", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--planner", action="store_true")
    parser.add_argument("--registry", type=Path, default=Settings().registry_path)
    args = parser.parse_args()
    if args.mode == "ask":
        if not args.question.strip():
            parser.error("Question required")
        for flag in [
            "NATIVE_V2_QUERY_ENABLED",
            "SCIENTIFIC_SYNTHESIS_ENABLED",
            "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
            "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
            "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
            "AUTONOMOUS_RESEARCH_ENABLED",
        ]:
            os.environ[flag] = "true"
        os.environ["NEMOTRON_RESEARCH_PLANNING_ENABLED"] = str(args.planner).lower()
        service = Phase3AssistantService()
        service.registry.db.close()
        service.registry = EvidenceRegistry(args.registry)
        response = service.answer_query(args.question)
        print(response.model_dump_json(indent=2) if args.json else response.rendered_answer)
    else:
        registry = EvidenceRegistry(args.registry, read_only=True)
        if args.mode == "review":
            value = (
                search_staged(args.question, registry, limit=32)
                if args.question
                else registry.staged_semantic_candidates()
            )
        else:
            exists = registry.db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='autonomous_jobs'"
            ).fetchone()
            value = {
                "maintenance_jobs": [
                    dict(r)
                    for r in registry.db.execute(
                        "SELECT job_id,started,status FROM autonomous_jobs ORDER BY started DESC LIMIT 10"
                    )
                ]
                if exists
                else [],
                "pending_scientific_review": sum(
                    r["review_status"] == "PENDING" for r in registry.staged_semantic_candidates()
                ),
                "codex_runtime_dependency": False,
            }
        print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
