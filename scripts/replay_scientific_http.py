"""Replay cached, untrusted model propositions through the current HTTP verifier.

This is an evaluation provider, never production answer logic. Planning is
reconstructed from saved queries/needs; organization preserves current order.
No inference API is called. Retrieval, local NLI, repairs and citations run anew.
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.api import create_app, default_service
from nasa_fire_ai.llm.conversation import complete_segments_prefix
from nasa_fire_ai.llm.interfaces import ProviderFailure


class CachedGenerationFailure:
    def __init__(self, message):
        self.message = message


def parse_cached_generation(content):
    """Replay malformed archived output as its original provider failure."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            return complete_segments_prefix(content)
        except ProviderFailure as error:
            return CachedGenerationFailure(str(error))


class CachedPropositions:
    generation_name = "Cached model propositions (backend replay)"

    def __init__(self, cases):
        self.cases = cases
        self.receipts = []

    def cached_generation(self, stage):
        result = self.current["cached_generations"][stage]
        if isinstance(result, CachedGenerationFailure):
            raise ProviderFailure(result.message)
        return result

    def plan(self, question, history, max_queries):
        self.current = self.cases[question]
        self.explanations = 0
        if "planning" in self.current.get("cached_generations", {}):
            return self.cached_generation("planning")
        queries = [r["query"] for r in self.current["queries"]]
        return {
            "resolved_question": queries[-1] if queries else question,
            "queries": queries[:max_queries],
            "information_needs": self.current["information_needs"],
            "use_previous_sources": bool(history),
        }

    def refine(self, question, candidates, remaining):
        return {"resolved_question": question, "queries": [], "information_needs": []}

    def explain(self, payload, max_tokens):
        stage = "draft" if self.explanations == 0 else f"repair-{self.explanations}"
        self.explanations += 1
        if stage in self.current.get("cached_generations", {}):
            return self.cached_generation(stage)
        segments, seen = [], set()
        for claim in self.current["claims"]:
            text = claim.get("original_text")
            if claim["stage"] != stage or not text or text in seen:
                continue
            seen.add(text)
            segments.append(
                {
                    "text": text,
                    "support_ids": claim.get("proposed_support_ids", []),
                    "repair_of": claim.get("repair_of"),
                }
            )
        return {"segments": segments, "answer_plan": []}

    def organize(self, question, history, paragraphs):
        if "organization" in self.current.get("cached_generations", {}):
            return self.cached_generation("organization")
        return {"retained_indices": list(range(len(paragraphs)))}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument(
        "--profile", action="store_true", help="Profile each HTTP chat worker locally"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    campaign = json.loads((args.campaign / "campaign.json").read_text())
    cases, receipts = {}, []
    for case in campaign["cases"]:
        if case.get("provider_input_path"):
            ledger = ROOT / case["provider_input_path"]
        elif case.get("ledger_path"):
            ledger = ROOT / case["ledger_path"]
        else:
            saved = json.loads((args.campaign / (case["id"] + ".json")).read_text())
            ledger = ROOT / "data/index/claim_ledger" / (saved["body"]["trace_id"] + ".json")
        original = json.loads(ledger.read_text())
        archives = {}
        for stage, archive_path in case.get("generation_archives", {}).items():
            archive_file = ROOT / archive_path
            archive = json.loads(archive_file.read_text())
            content = archive["raw_content"]
            if hashlib.sha256(content.encode()).hexdigest() != archive["content_sha256"]:
                raise ValueError("Archived generation checksum mismatch")
            parsed = parse_cached_generation(content)

            def normalize(value):
                if isinstance(value, dict):
                    return {key.lstrip(":"): normalize(child) for key, child in value.items()}
                if isinstance(value, list):
                    return [normalize(child) for child in value]
                return value

            original.setdefault("cached_generations", {})[stage] = normalize(parsed)
            archives[stage] = hashlib.sha256(archive_file.read_bytes()).hexdigest()
        cases[case["question"]] = original
        receipts.append(
            {
                "id": case["id"],
                "original_ledger_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(),
                "input_kind": "reconstructed_provider_input_without_original_ledger"
                if case.get("provider_input_path")
                else "original_claim_ledger",
                "paragraph_preserving_generation_archives": archives,
                "proposal_representation": "original_generation_segments"
                if archives
                else "saved_atomic_claims_without_original_grouping",
            }
        )
    os.environ["NASA_SNAPSHOT"] = str(args.snapshot.resolve())
    os.environ["NASA_NLI_DIRECTORY"] = str(ROOT / "data/index/models/nasa-nli")

    active_services = []

    def factory():
        service = default_service()
        active_services.append(service)
        if service.entailment is None or service.search.semantic_candidates is None:
            service.search.close()
            raise RuntimeError("Replay requires the provisioned verifier and vector index")
        service.provider = CachedPropositions(cases)
        if args.profile:
            import cProfile
            import pstats

            original_chat = service.chat

            def profiled_chat(request):
                profiler = cProfile.Profile()
                started = time.monotonic()
                try:
                    return profiler.runcall(original_chat, request)
                finally:
                    identity = hashlib.sha256(request.message.encode()).hexdigest()[:12]
                    profiler.dump_stats(str(args.output / (identity + ".profile")))
                    stats = pstats.Stats(profiler)
                    rows = [
                        {
                            "file": Path(key[0]).name,
                            "line": key[1],
                            "function": key[2],
                            "calls": value[1],
                            "self_seconds": value[2],
                            "cumulative_seconds": value[3],
                        }
                        for key, value in stats.stats.items()
                    ]
                    rows.sort(key=lambda row: -row["cumulative_seconds"])
                    (args.output / (identity + ".timings.json")).write_text(
                        json.dumps(
                            {
                                "elapsed_seconds": time.monotonic() - started,
                                "functions": rows[:120],
                                "boundary": "Overlapping cumulative times; cached provider calls, actual HTTP backend/NLI.",
                            },
                            indent=2,
                        )
                        + "\n"
                    )

            service.chat = profiled_chat
        return service

    server = uvicorn.Server(
        uvicorn.Config(create_app(factory), host="127.0.0.1", port=args.port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError("HTTP server failed to start")
        time.sleep(0.1)
    (args.output / "replay_contract.json").write_text(
        json.dumps(
            {
                "kind": "CACHED_PROPOSITION_HTTP_REPLAY",
                "fresh_generation_calls": 0,
                "planning": "reconstructed from original queries and information needs",
                "organization": "cached original organizer when declared; identity ordering otherwise",
                "snapshot": str(args.snapshot),
                "cases": receipts,
                "implementation_sha256": {
                    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((ROOT / "src/nasa_fire_ai").rglob("*.py"))
                },
            },
            indent=2,
        )
        + "\n"
    )
    conversations = {}
    try:
        with httpx.Client(timeout=900) as client:
            record_checks = []
            for accession in (
                107,
                39,
                22,
                21,
                20,
                23,
                106,
                68,
                47,
                98,
                69,
                101,
                102,
                25,
                26,
                99,
                100,
                10,
                159,
            ):
                response = client.get(
                    f"http://127.0.0.1:{args.port}/api/v1/records",
                    params={"investigation": f"psi-{accession}", "limit": 2},
                )
                response.raise_for_status()
                records = response.json()
                verified = 0
                for record in records["items"]:
                    cells = [
                        cell
                        for source in record["evidence"]
                        for cell in source.get("source_cells", [])
                    ]
                    for field in record["fields"]:
                        q = field.get("qualifiers", {})
                        assert any(
                            cell["original_header"].strip() == q["source_header"]
                            and cell["original_value"] == q["original_value"]
                            for cell in cells
                        )
                        verified += 1
                assert records["items"] and verified
                record_checks.append(
                    {
                        "investigation": f"psi-{accession}",
                        "records": len(records["items"]),
                        "registered_records": records["total"],
                        "exact_fields_checked": verified,
                    }
                )
            (args.output / "http_original_records.json").write_text(
                json.dumps(record_checks, indent=2) + "\n"
            )
            for case in campaign["cases"]:
                request = {
                    "message": case["question"],
                    "max_queries": case.get("max_queries", 2 if case.get("followup_of") else 1),
                    "evidence_limit": case.get("evidence_limit", 10),
                    "max_output_tokens": case.get("max_output_tokens", 2000),
                }
                if case.get("followup_of"):
                    request["conversation_id"] = conversations[case["followup_of"]]
                start = time.monotonic()
                response = client.post(f"http://127.0.0.1:{args.port}/api/v1/chat", json=request)
                body = response.json()
                result = {
                    "id": case["id"],
                    "request": request,
                    "status": response.status_code,
                    "body": body,
                    "elapsed_seconds": time.monotonic() - start,
                }
                (args.output / (case["id"] + ".json")).write_text(
                    json.dumps(result, indent=2) + "\n"
                )
                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code} in {case['id']}")
                from fastapi.encoders import jsonable_encoder

                trace = active_services[-1].traces[body["trace_id"]]
                (args.output / (case["id"] + ".trace.json")).write_text(
                    json.dumps(jsonable_encoder(trace), indent=2) + "\n"
                )
                ledger = ROOT / "data/index/claim_ledger" / (body["trace_id"] + ".json")
                if ledger.is_file():
                    (args.output / (case["id"] + ".ledger.json")).write_bytes(ledger.read_bytes())
                conversations[case["id"]] = body["conversation_id"]
                print(
                    case["id"],
                    round(result["elapsed_seconds"], 1),
                    body["verification_status"],
                    flush=True,
                )
    finally:
        server.should_exit = True
        thread.join(timeout=30)


if __name__ == "__main__":
    main()
