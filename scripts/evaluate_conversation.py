"""Reproducible offline coverage or real HTTP/Nemotron conversational receipts.

These are executable probes, not human scientific quality grades. Expected
negative controls are evaluation annotations only, never production routing.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--nli", type=Path)
    parser.add_argument("--cases", type=Path, default=ROOT / "evals/phase56/questions_english_v2.json")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new; preserve earlier measurements")
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.services.search import ScientificSearchService

    settings = Settings()
    snapshot = ROOT / "data/snapshots/hackathon-20261105-v9"
    cases = json.loads(args.cases.read_text())
    report = {
        "mode": "live_http" if args.live else "offline_retrieval",
        "case_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "cases": [],
        "human_scientific_validation": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    if not args.live:
        engine = ScientificSearchService(snapshot, ROOT)
        try:
            report["snapshot_id"] = engine.manifest["snapshot_id"]
            report["coverage"] = engine.manifest["sources"]
            for case in cases:
                start = perf_counter()
                result = engine.search(
                    case["message"], assist=True, research=True, complete_claims=True
                )
                row = {
                    **case,
                    "seconds": perf_counter() - start,
                    "counts": {
                        k: len(getattr(result, k))
                        for k in ("direct", "related", "documentary", "discovery", "claims")
                    },
                    "source_ids": sorted(
                        {
                            e["source"]["source_id"]
                            for r in result.direct + result.related
                            for e in r["evidence"]
                        }
                        | {r["source"]["source_id"] for r in result.documentary + result.discovery}
                    ),
                    "negative_control_passed": not result.direct if case.get("no_direct") else None,
                    "unresolved": result.intent.unresolved_mentions,
                }
                report["cases"].append(row)
                print(json.dumps({"id": case["id"], **row["counts"]}), flush=True)
                save()
        finally:
            engine.close()
    else:
        if not settings.nvidia_api_key or args.nli is None:
            parser.error("Live evaluation requires NVIDIA configuration and --nli")
        from fastapi.testclient import TestClient

        from nasa_fire_ai.api import create_app
        from nasa_fire_ai.llm.conversation import NemotronConversation
        from nasa_fire_ai.services.conversation import ConversationService
        from nasa_fire_ai.services.semantic_support import LocalEntailment

        services = []

        def factory():
            engine = ScientificSearchService(snapshot, ROOT)
            provider = NemotronConversation(
                settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
            )
            service = ConversationService(
                engine, provider=provider, entailment=LocalEntailment(args.nli)
            )
            services.append(service)
            return service

        sessions = {}
        with TestClient(create_app(factory)) as client:
            for case in (c for c in cases if c.get("live")):
                start = perf_counter()
                payload = {
                    "message": case["message"],
                    "detail": "standard",
                    "max_queries": 3,
                    "max_output_tokens": 6000,
                }
                if cid := sessions.get(case.get("conversation")):
                    payload["conversation_id"] = cid
                response = client.post("/api/v1/chat", json=payload)
                data = response.json()
                if case.get("conversation") and "conversation_id" in data:
                    sessions[case["conversation"]] = data["conversation_id"]
                citation_checks = []
                for citation in data.get("citations", []):
                    retrieved = client.get("/api/v1/evidence/" + citation["evidence_id"])
                    original = retrieved.json()
                    citation_checks.append(
                        {
                            "evidence_id": citation["evidence_id"],
                            "http_status": retrieved.status_code,
                            "source_span_matches": " ".join(citation["supporting_passage"].split())
                            in " ".join(original.get("text", "").split()),
                        }
                    )
                trace = services[0].traces.get(data.get("trace_id"), {}) if services else {}
                groups = data.pop("evidence_groups", {})
                row = {
                    **case,
                    "http_status": response.status_code,
                    "seconds": perf_counter() - start,
                    "response": data,
                    "evidence_counts": {k: len(v) for k, v in groups.items()},
                    "citation_checks": citation_checks,
                    "trace": trace,
                }
                report["cases"].append(row)
                print(
                    json.dumps(
                        {
                            "id": case["id"],
                            "http": response.status_code,
                            "citations": len(data.get("citations", [])),
                            "provider": data.get("provider_status"),
                            "seconds": row["seconds"],
                        }
                    ),
                    flush=True,
                )
                save()
    save()


if __name__ == "__main__":
    main()
