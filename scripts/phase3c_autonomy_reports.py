"""Produce final versioned decisions and indexed evidence from executed receipts."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = os.getenv("AUTONOMY_REPORT_VERSION", "v2")


def read(name):
    return json.loads((ROOT / "artifacts" / name).read_text())


def save(name, value):
    with (ROOT / "artifacts" / name).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    answers = {
        variant: read(f"phase3c_autonomy_answers_{variant}_v7.json")["cases"]
        for variant in ["b", "c", "d"]
    }
    hybrid = read("phase3c_autonomy_hybrid_v2.json")
    model_hybrid = read("phase3c_autonomy_hybrid_model_v1.json")
    integrity = read("phase3c_autonomy_integrity_v7.json")
    source_runs = [
        read(f"phase3c_autonomy_maintenance_{suffix}_v1.json")
        for suffix in ["live", "versioned", "validated", "repeat", "regression"]
    ]
    extraction = source_runs[2]["items"][0]["extraction"]
    recovery = read("phase3c_autonomy_recovery_v7.json")
    graph = read("phase3c_autonomy_graph_paths_v7.json")
    claim_checks = read("phase3c_autonomy_claims_v1.json")
    summary = {}
    for variant, cases in answers.items():
        investigations = [r["investigation"] for r in cases if r["investigation"]]
        summary[variant.upper()] = {
            "cases": len(cases),
            "with_direct_ids": sum(bool(r["direct_ids"]) for r in cases),
            "citation_resolving_cases": sum(r["citations_resolve"] for r in cases),
            "mean_words": sum(len(r["answer"].split()) for r in cases) / len(cases),
            "additional_actions": sum(len(i["completed_actions"]) for i in investigations),
            "initially_sufficient": None
            if not investigations
            else sum(i["initial_coverage"]["sufficient"] for i in investigations),
            "finally_sufficient": None
            if not investigations
            else sum(i["final_coverage"]["sufficient"] for i in investigations),
            "mean_latency_ms": sum(r["latency_ms"] for r in cases) / len(cases),
            "duplicate_actions_executed": sum(
                len(i["completed_actions"])
                - len(
                    {
                        (a["operation"], a["query"].casefold().strip())
                        for a in i["completed_actions"]
                    }
                )
                for i in investigations
            ),
            "scientific_precision": "NOT_MEASURABLE",
            "independent_review_count": 0,
        }
    fresh_model_calls = []
    for run in source_runs:
        e = run["items"][0]["extraction"]
        if e.get("new_model_calls"):
            fresh_model_calls.append({"purpose": "scientific_extraction", **e["model"]})
    for path in sorted((ROOT / "artifacts").glob("phase3c_autonomy_answers_d_v*.json")):
        for case in json.loads(path.read_text())["cases"]:
            for receipt in (case.get("investigation") or {}).get("model_calls", []):
                if receipt["execution"] == "FRESH_INFERENCE":
                    fresh_model_calls.append(
                        {"purpose": "research_planning", "question": case["question"], **receipt}
                    )
    for case in model_hybrid["cases"]:
        if case["model"]["execution"] == "FRESH_INFERENCE":
            fresh_model_calls.append({"purpose": "hybrid_statement_organization", **case["model"]})
    tokens = sum((r.get("usage") or {}).get("total_tokens", 0) for r in fresh_model_calls)
    metrics = {
        "configurations": summary,
        "historical_A": read("phase3c_consolidation_comparison_v4.json")["configurations"]["A"],
        "historical_A_execution": "Historical receipt; unmodified pre-campaign code was not freshly rerun",
        "source_extraction": {
            "items": len(extraction["items"]),
            "pending": sum(i.get("review_status") == "PENDING" for i in extraction["items"]),
            "rejected": sum(i.get("review_status") == "REJECTED" for i in extraction["items"]),
            "canonical_scientific_changes": extraction["canonical_scientific_changes"],
        },
        "hybrid": {
            "corpus_units": len(hybrid["corpus_ids"]),
            "questions": len(hybrid["cases"]),
            "provider_calls": len(hybrid["provider_calls"]),
            "cache": hybrid["cache"],
            "empty_native_kg_rankings": sum(
                not c["rankings"]["C_native_kg"] for c in hybrid["cases"]
            ),
            "scientific_precision": "NOT_MEASURABLE",
        },
        "nemotron": {
            "new_calls": len(fresh_model_calls),
            "failed_calls": sum(bool(r.get("error_type")) for r in fresh_model_calls),
            "known_reported_tokens": tokens,
            "unreported_usage_calls": sum(r.get("usage") is None for r in fresh_model_calls),
            "billing_cost": None,
            "receipts": fresh_model_calls,
        },
        "jev": {
            "availability": read("phase3c_autonomy_jev_v1.json"),
            "advisory": read("phase3c_autonomy_jev_advisory_v1.json"),
        },
        "recovery_cases": len(recovery["cases"]),
        "independent_scientific_review": None,
    }
    save(f"phase3c_autonomy_metrics_{REPORT_VERSION}.json", metrics)
    decisions = {
        "AUTONOMOUS_RESEARCH_LOOP": "OPERATIONAL",
        "INTENT_AWARE_ROUTING": "PARTIAL",
        "EVIDENCE_SUFFICIENCY": "PARTIAL",
        "SCIENTIFIC_CLAIM_VERIFICATION": "PARTIAL",
        "OBSERVATION_CONCLUSION_LINKING": "REVIEW_REQUIRED",
        "AUTONOMOUS_SCIENTIFIC_EXTRACTION": "PARTIAL",
        "SOURCE_TO_KNOWLEDGE_PUBLICATION": "CONTROLLED",
        "ONTOLOGY_GRAPH_REASONING": "PARTIAL",
        "HYBRID_RAG": "KEEP_EXPERIMENTAL",
        "VECTOR_RETRIEVAL": "INCONCLUSIVE",
        "AUTONOMOUS_MAINTENANCE": "PARTIAL",
        "OPERATIONAL_FAILURE_RECOVERY": "PARTIAL",
        "NEMOTRON_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "JEV_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
        "END_TO_END_SCIENTIFIC_RESEARCH": "PARTIAL",
        "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    blockers = [
        "Independent scientific relevance, answer completeness and claim labels are unavailable; precision cannot be independently measured.",
        "Current-study experiment identities, groups, table quantities and gravity scopes need approved extraction contracts and adjudication.",
        "Observation-to-conclusion candidates have no approved attribution or support predicate; shared publication does not establish support.",
        "Claim verification is exact supplied statement verification; unrestricted paraphrase entailment and contradiction reasoning remain unimplemented.",
        "Intent-specific methodology, comparison completeness and general conceptual authority remain partial.",
        "The recurring timer is verified but not installed or enabled, as required; unattended deployment remains a deployment step.",
        "Maintenance has bounded retries, leases, isolation and regression checks, but full scientific quality drift monitoring and strict whole-operation deadline preemption remain incomplete.",
        "Vector and selective model components lack independently demonstrated scientific benefit; they remain disabled by default.",
    ]
    evidence_paths = [
        "artifacts/phase3c_autonomy_answers_c_v7.json",
        "artifacts/phase3c_autonomy_recovery_v7.json",
        "artifacts/phase3c_autonomy_maintenance_validated_v1.json",
        "artifacts/phase3c_autonomy_hybrid_v2.json",
        "artifacts/phase3c_autonomy_integrity_v7.json",
    ]
    save(
        f"phase3c_autonomy_decisions_{REPORT_VERSION}.json",
        {
            "decisions": decisions,
            "evidence": evidence_paths,
            "blockers": blockers,
            "scientific_precision": "NOT_MEASURABLE",
            "phase4_started": False,
        },
    )
    lines = [
        "# Phase 3C autonomous research engineering — final executed results",
        "",
        "A bounded research runtime and repeatable maintenance jobs are implemented and executed. Scientific readiness remains partial. No independent scientific precision is claimed. Phase 4 was not started.",
        "",
        "## A. Architectural implementation",
        "",
        "`Phase3AssistantService` retains the native QueryIntentV2 interpreter/executor and existing graph. Optional execution follows interpretation → initial native retrieval → typed sufficiency → justified native/document/ontology actions → source-backed claim verification → concise synthesis. Investigation receipts stay in EvidenceBundle metadata. Staged scientific entities project into the existing RDF graph with canonical=false and STAGED_CANDIDATE, and never enter canonical candidate enumeration.",
        "",
        "Modules changed or added: services/phase3.py, services/investigation.py, services/intent_answers.py, services/claim_verification.py, services/maintenance.py, services/scientific_synthesis.py, query/native_interpreter.py, query/conceptual.py, llm/research.py, ingestion/scientific_proposals.py, ingestion/semantic.py, retrieval/semantic.py. Operational interfaces: scripts/research.py, scripts/maintain_knowledge.py; evaluation and integrity scripts use versioned receipts.",
        "",
        "Defaults: three total retrieval rounds, eight follow-up action ceiling, eight candidates/action, 30-second between-action research deadline, at most two planning calls, conservative input/completion token reserve. The implemented planner currently makes at most one optional call/query. Initial retrieval remains native; additional actions retain explicit entity, numeric and source constraints. Simple sufficient queries stop immediately. V2/research, Nemotron planning and vectors remain experimental flags; CLI explicitly enables the validated research path.",
        "",
        "## B. Actual autonomous recovery",
        "",
    ]
    for case in recovery["cases"]:
        state = case["trace"]
        lines += [
            f"**{case['question']}**",
            "",
            f"Injected fault: {case['fault']}. Final decision: {state['final_decision']}.",
            "",
        ]
        for action in state["completed_actions"]:
            lines.append(
                f"- `{action['operation']}`: `{action['query']}`; missing `{action['requirement']}`; {len(action['recovered_evidence_ids'])} recovered references. Constraints retained in the full trace."
            )
        lines.append("")
    lines += [
        "Full before/after coverage, constraints, rejected actions, returned IDs and timings: artifacts/phase3c_autonomy_recovery_v7.json. These are real service executions with an intentionally incomplete first retrieval, not production benchmark branches.",
        "",
        "## C. Scientific interpretation and corrections",
        "",
        "Conceptual retrieval now shows actual source terminology such as acrylic/PMMA specimen wording and distinguishes documentary usage from total material equivalence. Bibliographic retrieval returns publication titles and matching passages, deduplicated by NASA identity, without ExperimentalRun requirements. The regression suite caught and corrected a report/source linguistic guard that had erased explicit gravity and guidance requests. An explicit technical topic modifier absent from a statement cannot establish sufficient support for that topic.",
        "",
        "The complex depressurization answer now retains unresolved conclusion support, experiment conditions and attribution. Pending exact source quotations are visible as proposed science, with unapproved scope. This is a useful partial result, not a validated observation-to-conclusion explanation.",
        "",
        "## D. Source-to-knowledge execution",
        "",
        f"NTRS 20260003546 reused its immutable content-addressed PDF; original SHA256 `{integrity['source_digest']}`. Twelve physical page texts were verified. Structure-selected original pages went through bounded Nemotron proposals, exact-span/quantity checks, existing-class mapping and isolated staging. One provider timeout fell back to deterministic sentence proposals. The successful validated extraction yielded {len(extraction['items'])} candidates: {metrics['source_extraction']['pending']} pending and {metrics['source_extraction']['rejected']} rejected. No new canonical scientific fact was published.",
        "",
        "Published contract: document identity, source provenance and original page text. Pending candidates retain exact original wording, evidence ID, physical page, offsets, digest, proposed class, group/scope, original quantities when proposed, limitations, validation reasons and scientific-review=null. Model-proposed classes and scope are not approved science. A subsequent deterministic maintenance cycle added remaining bounded sentence proposals without duplicate identities. Unknown gravity remains unresolved; a full-page proposal falsely assigning microgravity was rejected despite historical microgravity discussion in that same source.",
        "",
    ]
    for item in extraction["items"][:8]:
        proposal = item.get("proposal", {})
        lines += [
            f"- `{item.get('candidate_id')}` / {item.get('candidate_type')} / {item.get('review_status')}; `{item.get('evidence_id')}`, page {proposal.get('source_location', {}).get('page')}; reasons: {', '.join(proposal.get('publication_reasons', []))}."
        ]
    lines += [
        "",
        "Complete propositions and model traces: artifacts/phase3c_autonomy_maintenance_validated_v1.json. Natural-language retrieval of explicitly pending knowledge occurs through the real service and `research.py review`.",
        "",
        "## E. Ontology and KG",
        "",
    ]
    for route in graph["routes"]:
        lines.append(
            f"- `{route['start']}`: {len(route['receipt']['results'])} valid paths through {', '.join(s['relation'] + ' ' + s['direction'] for s in route['steps'])}. Every edge carries resolvable provenance; paths express association."
        )
    lines += [
        "",
        "Observation/conclusion pair candidates retain both exact statements and source IDs. Approved support links: zero. No causal/support vocabulary or scientific equivalence was silently added. The graph benchmark was repaired to execute actual native queries, retain publication/information candidate identities, and exclude lexical-only passages from KG eligibility. Valid empty graph sets remain empty.",
        "",
        "## F. Hybrid RAG",
        "",
        f"Expanded frozen corpus: {len(hybrid['corpus_ids'])} original units; {len(hybrid['cases'])} queries, including twelve developer-authored holdout probes. Configurations A lexical, B vector, C native KG eligibility, D lexical+KG, E lexical+vector, F all three, G context candidates were executed at k=5. KG ranks use BM25 only inside graph eligibility; they are not a new semantic graph scorer. {metrics['hybrid']['empty_native_kg_rankings']} KG rankings are empty. H attempted bounded model organization on two fixed candidate lists; the full receipt distinguishes fresh inference from no validated inventory.",
        "",
        "Precision@5, recall, nDCG and usefulness are unmeasurable without independent labels. Different candidates do not prove improved relevance. Vectors remain local and disabled in normal native execution. Actual 171-unit vector data was migrated to an atomic generation; interrupted manifest publication is regression-tested to retain the old searchable generation. Previous generations remain available for recovery.",
        "",
        "## G. Claim verification",
        "",
    ]
    for row in claim_checks["cases"]:
        lines.append(
            f"- {row.get('case', 'actual supplied service claim')}: **{row['verification']['status']}**; {', '.join(row['verification'].get('errors', [])) or 'exact supplied statement with preserved entities, context and provenance'}."
        )
    lines += [
        "",
        "Numeric changes, wrong epistemic type and wrong investigation identity were rejected while original grounded statements remained available. Two actual source claims were qualified because applicability was RELATED. This verifier deliberately rejects arbitrary paraphrases and cannot independently establish full scientific accuracy or causal entailment.",
        "",
        "## H. Autonomous operation",
        "",
        "Runnable commands:",
        "",
        "```bash",
        "uv run python scripts/research.py ask 'What did NASA observe about PMMA combustion?'",
        "uv run python scripts/research.py ask 'Which experiments support the reported conclusions?' --planner --json",
        "uv run python scripts/research.py review 'depressurization extinguishment'",
        "uv run python scripts/research.py status",
        "uv run python scripts/maintain_knowledge.py cycle --query 'depressurization fire suppression' --max-sources 1",
        "uv run python scripts/maintain_knowledge.py cycle --execute --query 'depressurization fire suppression' --max-sources 1",
        "uv run python scripts/maintain_knowledge.py cycle --execute --offline --nasa-id 20260003546 --extract",
        "uv run python scripts/maintain_knowledge.py validation-only",
        "uv run python scripts/maintain_knowledge.py rollback --source-id SOURCE_VERSION_ID",
        "```",
        "",
        "An actual discovery-led cycle found seven metadata records and selected an eligible official source without developer source selection. It correctly returned UNCHANGED for 20260003546. Offline controlled extraction and a repeated unchanged execution were also run; repeat inference count was zero. Per-cycle source/reference/FTS checks and autonomous-maintenance regressions passed. Persistent job leases prevent overlap, expired leases recover abandoned work, retry/backoff is bounded, and one failed extraction cannot stop later valid sources. Existing document publication/rollback tests retain raw input and citations.",
        "",
        "`ops/nasa-knowledge-maintenance.service.example` and `.timer.example` passed systemd-analyze verify in temporary deployment copies. They are not installed or enabled. The configured recurring cycle can discover and process bounded sources. API key absence still supports queries, scientific review listing, validation and deterministic extraction. Strict whole-operation preemption and scientific-quality drift monitoring remain incomplete.",
        "",
        "## I. Nemotron and Jev",
        "",
        f"New Nemotron requests: {len(fresh_model_calls)}; provider failures: {metrics['nemotron']['failed_calls']}; reported tokens across successful recorded calls: {tokens}; usage unavailable for {metrics['nemotron']['unreported_usage_calls']} calls. Counts exclude cache replay. Embedding calls and usage are recorded separately per request in hybrid_v1; hybrid_v2 reuses the cache. Billing cost is unavailable.",
        "",
        "Nemotron supplied valid bounded actions and exact-span scientific proposals, but no independently demonstrated scientific precision gain. Its altered wording was rejected. Jev availability and one advisory classification were executed; its confidence/label did not approve science or change canonical knowledge. Both incremental scientific values remain INCONCLUSIVE.",
        "",
        "## J. Scientific answer quality and comparisons",
        "",
        "The unmodified historical A renderer is cited from its frozen receipt, not mislabeled as a fresh run. Fresh B uses repaired routing/verification; C adds deterministic iteration; D adds selective model planning. E/F scientific hybrid adoption is not justified by unlabelled candidate rankings. The best shipping configuration remains conservative with optional components off by default.",
        "",
        "| Configuration | Cases | DIRECT identities present | Citation resolution | Mean words | Additional actions | Initially/finally sufficient |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for variant, row in summary.items():
        lines.append(
            f"| {variant} | {row['cases']} | {row['with_direct_ids']} | {row['citation_resolving_cases']}/{row['cases']} | {row['mean_words']:.1f} | {row['additional_actions']} | {row['initially_sufficient']}/{row['finally_sufficient']} |"
        )
    lines += [
        "",
        "B sufficiency counts are not measured with iteration disabled (None); C/D coverage is measured by the implemented engineering contracts. All are engineering coverage/formatting counts, not independent precision. Bibliographic and conceptual success is not measured by ExperimentalRun DIRECT counts. All scientific-review fields remain blank. Previously exposed and developer-authored holdouts are identified separately; the holdout is not independently adjudicated scientific gold.",
        "",
        "## K. Engineering integrity",
        "",
        "`uv run ruff format --check .`, `uv run ruff check .`, and the full `uv run pytest -q` passed (266 tests). Canonical, native and taxonomy SHACL conform; SQLite, reference anti-joins, FTS completeness and exact text consistency pass. All 1,050 historical digests remain unchanged; 159 original evidence units and twelve report pages match original cells/spans. Staged propositions are excluded from canonical enumeration. Dynamic checks: 230/230; post-freeze: 125/125; classes: 5/5. Historical 39-case parity remains DIRECT 31/39, RELATED 37/39 and exact evidence identities 6/39, so V2 parity is incomplete. V1/no-key rollback was actually executed.",
        "",
        "72,960 rdflib warnings are classified as Dataset.default_context deprecation in installed rdflib (233 native-semantic; 72,727 scientific-enrichment), and were not suppressed. Earlier failed regression/renderer/lint receipts are retained; the final quality receipt resolves the corrected gates. No original data, frozen gold or historical benchmark receipt was overwritten. Credentials are excluded from the indexed campaign artifacts.",
        "",
        "## L. Readiness",
        "",
        "```text",
    ]
    lines += [f"{key} = {value}" for key, value in decisions.items()]
    lines += ["```", "", "Remaining blockers:", ""] + [f"- {blocker}" for blocker in blockers]
    with (ROOT / f"docs/PHASE3C_AUTONOMOUS_RESEARCH_RESULTS_{REPORT_VERSION.upper()}.md").open(
        "x"
    ) as stream:
        stream.write("\n".join(lines) + "\n")
    final_cases = read("phase3c_autonomy_final_service_v2.json")["cases"]
    example_lines = [
        "# Actual autonomous-service scientific answers",
        "",
        "Source support and experimental attribution remain subject to the limits in the final report. These are actual final primary-registry service outputs; frozen comparisons remain in v7 receipts.",
        "",
    ]
    for case in final_cases:
        if case["id"] not in {"A", "B", "C", "D", "E", "F", "G", "H"}:
            continue
        example_lines += [
            f"## {case['id']}. {case['question']}",
            "",
            case["answer"],
            "",
            "```json",
            json.dumps(
                {"intent": case["intent"], "investigation": case["investigation"]}, indent=2
            ),
            "```",
            "",
        ]
    with (ROOT / f"docs/PHASE3C_AUTONOMOUS_ANSWERS_{REPORT_VERSION.upper()}.md").open(
        "x"
    ) as stream:
        stream.write("\n".join(example_lines))
    paths = set((ROOT / "artifacts").glob("phase3c_autonomy*"))
    paths.update((ROOT / "docs").glob("PHASE3C_AUTONOMOUS*"))
    paths.update((ROOT / "scripts").glob("phase3c_autonomy*"))
    paths.update(
        ROOT / p
        for p in [
            "scripts/research.py",
            "scripts/maintain_knowledge.py",
            "tests/test_investigation.py",
            "ops/nasa-knowledge-maintenance.service.example",
            "ops/nasa-knowledge-maintenance.timer.example",
            "src/nasa_fire_ai/services/investigation.py",
            "src/nasa_fire_ai/services/intent_answers.py",
            "src/nasa_fire_ai/services/claim_verification.py",
            "src/nasa_fire_ai/services/maintenance.py",
            "src/nasa_fire_ai/services/scientific_synthesis.py",
            "src/nasa_fire_ai/services/phase3.py",
            "src/nasa_fire_ai/query/native_interpreter.py",
            "src/nasa_fire_ai/query/conceptual.py",
            "src/nasa_fire_ai/llm/research.py",
            "src/nasa_fire_ai/ingestion/scientific_proposals.py",
            "src/nasa_fire_ai/ingestion/semantic.py",
            "src/nasa_fire_ai/retrieval/semantic.py",
        ]
    )
    paths.update((ROOT / "data/index/autonomy_vectors").glob("*"))
    raw = read("phase3c_consolidation_acquisition_v2.json")["raw_file"]
    paths.add(ROOT / raw)
    paths.add(ROOT / "data/index/autonomy_snapshot_v1.sqlite")
    from dotenv import dotenv_values

    # Read only for exclusion checks; explicit process values take precedence.
    local = dotenv_values(ROOT / ".env")
    secrets = [
        os.environ.get(key, local.get(key))
        for key in ["NVIDIA_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"]
    ]
    index = []
    expanded = set()
    for path in paths:
        expanded.update([path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()])
    for path in sorted(expanded):
        if path.name == ".env" or path.suffix == ".pyc":
            continue
        content = path.read_bytes()
        if any(secret and secret.encode() in content for secret in secrets):
            raise RuntimeError("Secret exclusion check failed")
        count = None
        if path.suffix == ".json":
            value = json.loads(content)
            count = len(value) if isinstance(value, (dict, list)) else None
        index.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "top_level_count": count,
            }
        )
    save(
        f"phase3c_autonomy_artifact_index_{REPORT_VERSION}.json",
        {
            "files": index,
            "counts": {"files": len(index), "bytes": sum(r["bytes"] for r in index)},
            "active": {
                "answers": "artifacts/phase3c_autonomy_final_service_v2.json",
                "hybrid": "artifacts/phase3c_autonomy_hybrid_v2.json",
                "quality": "artifacts/phase3c_autonomy_integrity_v7.json",
                "decisions": f"artifacts/phase3c_autonomy_decisions_{REPORT_VERSION}.json",
                "report": f"docs/PHASE3C_AUTONOMOUS_RESEARCH_RESULTS_{REPORT_VERSION.upper()}.md",
            },
            "secrets_excluded": True,
            "historical_artifacts_retained": True,
        },
    )
    print({"metrics": summary, "decisions": decisions, "indexed_files": len(index)})


if __name__ == "__main__":
    main()
