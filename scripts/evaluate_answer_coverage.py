"""Actual HTTP conversation probes with source-inspected information targets.

Coverage targets are documentary propositions, not scientific findings created
by this harness. Independent NLI is an automated communication probe, not a
scientist adjudication. All live attempts are saved; no best-run selection.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--implementation-root", type=Path, default=ROOT)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nli", type=Path, required=True)
    parser.add_argument("--ids", nargs="*")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    sys.path.insert(0, str(args.implementation_root / "src"))
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    from fastapi.testclient import TestClient

    from nasa_fire_ai.api import create_app
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.llm.conversation import NemotronConversation
    from nasa_fire_ai.query.lexicon import load_lexicon
    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.search import ScientificSearchService
    from nasa_fire_ai.services.semantic_support import LocalEntailment

    load_lexicon()  # Resolve archived-code assets before spending any provider calls.
    settings = Settings(root=ROOT)
    if not settings.nvidia_api_key:
        parser.error("Configured NVIDIA credentials are required")
    cases = json.loads(args.cases.read_text())
    if args.ids:
        cases = [c for c in cases if c["id"] in args.ids]
    from measure_answer_coverage import communication_check

    targets = json.loads(args.targets.read_text())["targets"]
    services = []
    verifier = LocalEntailment(args.nli)

    def factory():
        service = ConversationService(
            ScientificSearchService(ROOT / "data/snapshots/hackathon-20261105-v9", ROOT),
            provider=NemotronConversation(
                settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
            ),
            entailment=verifier,
        )
        services.append(service)
        return service

    report = {
        "mode": "live_http",
        "implementation_hashes": {
            name: hashlib.sha256((args.implementation_root / name).read_bytes()).hexdigest()
            for name in [
                "src/nasa_fire_ai/services/conversation.py",
                "src/nasa_fire_ai/services/semantic_support.py",
                "src/nasa_fire_ai/llm/conversation.py",
            ]
        },
        "case_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(args.targets.read_bytes()).hexdigest(),
        "independent_scientist_adjudication": False,
        "cases": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sessions = {}
    with TestClient(create_app(factory)) as client:
        for case in cases:
            payload = {
                "message": case["message"],
                "max_queries": 3,
                "evidence_limit": 12,
                "max_output_tokens": 4000,
                "detail": "standard",
            }
            if case.get("conversation") in sessions:
                payload["conversation_id"] = sessions[case["conversation"]]
            start = perf_counter()
            response = client.post("/api/v1/chat", json=payload)
            data = response.json()
            response_seconds = perf_counter() - start
            trace = services[0].traces.get(data.get("trace_id"), {}) if services else {}
            if case.get("conversation") and data.get("conversation_id"):
                sessions[case["conversation"]] = data["conversation_id"]
            if not trace and services:
                trace = {"provider_calls": list(getattr(services[0].provider, "receipts", []))}
            citation_checks = []
            for citation in data.get("citations", []):
                for support in citation.get("supports", []):
                    lookup = client.get("/api/v1/evidence/" + support["evidence_id"])
                    citation_checks.append(
                        {
                            "evidence_id": support["evidence_id"],
                            "http_status": lookup.status_code,
                            "exact_span": " ".join(support["passage"].split())
                            in " ".join(lookup.json().get("text", "").split()),
                        }
                    )
            emitted = {
                " ".join(s["claim_text"].split())
                for c in data.get("citations", [])
                if c.get("category") != "DISCOVERY"
                for s in c.get("supports", [])
            }
            retained = (
                services[0].retrieved.get(data.get("conversation_id"), []) if services else []
            )
            retained_ids = {r.get("evidence_id") for r in retained}
            inventory = trace.get("support_inventory", [])
            checks = []
            for target in (t for t in targets if case["id"] in t["case_ids"]):
                check = communication_check(verifier, emitted, target["proposition"])
                checks.append(
                    {
                        "target_id": target["id"],
                        "proposition": target["proposition"],
                        "candidate_retrieved": target["evidence_id"] in retained_ids,
                        "source_page_supplied": any(
                            target["evidence_id"] == s["evidence_id"]
                            for a in inventory
                            for s in a["spans"]
                        ),
                        "communication_probe": check,
                        "boundary": "Source-inspected target; independent NLI communication check, not manual response adjudication",
                    }
                )
            row = {
                **case,
                "http_status": response.status_code,
                "seconds": perf_counter() - start,
                "response_seconds": response_seconds,
                "communication_protocol": "per-supported-statement-NLI-v2",
                "response": {
                    k: v
                    for k, v in data.items()
                    if k not in {"evidence_groups", "additional_candidates"}
                },
                "candidate_count": len(retained),
                "citation_checks": citation_checks,
                "target_checks": checks,
                "trace": trace,
            }
            report["cases"].append(row)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "id": case["id"],
                        "http": response.status_code,
                        "mode": data.get("provider_status", {}).get("response_mode"),
                        "targets": sum(t["communication_probe"]["supported"] for t in checks),
                        "target_total": len(checks),
                        "seconds": row["seconds"],
                    }
                ),
                flush=True,
            )
    report["complete"] = True
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
