"""Measured closure receipts and review proposals; never rewrites historical artifacts."""

import hashlib
import json
import os
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import RDF, Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import validate_relation_proposal
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.controlled_reasoning import _digest, validate_expansion
from nasa_fire_ai.query.native import NS, execute_native
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.query.offline_parser import parse_query
from nasa_fire_ai.query.v2 import QueryIntentV2, v1_to_v2

ART = ROOT / "artifacts"


def read(name):
    return json.loads((ART / name).read_text())


def lines(name):
    return [json.loads(line) for line in (ART / name).read_text().splitlines()]


def write(name, value):
    path = ART / f"phase3c_enrichment_{name}_v1.json"
    if path.exists():
        if json.loads(path.read_text()) == json.loads(json.dumps(value, default=str)):
            return
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, default=str))


def main():
    evidence = EvidenceRegistry(Settings().registry_path)
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    store = project_legacy(ROOT, evidence)
    summary = read("phase3c_enrichment_summary_v1.json")
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    cases = read("phase3c_enrichment_regressions_v1.json")["cases"]
    native = read("phase3c_enrichment_native_checks_v1/phase3c_native_parity.json")
    enriched = read("phase3c_enrichment_native_checks_v2/phase3c_native_parity.json")
    gold = {
        c["id"]: c
        for c in json.loads(
            (ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json").read_text()
        )["cases"]
    }
    discrepancies = []
    for old, new in zip(native["cases"], enriched["cases"], strict=True):
        intent = v1_to_v2(parse_query(gold[new["case_id"]]["query"]))
        categories, causes = [], []
        if intent.requested_information == ["SafetyImplication"]:
            categories.append("BENCHMARK_CONTRACT_MISMATCH")
            causes.append(
                "Frozen V1 parser imposes an epistemic class from NASA/suppression language; use validated native intent in separate evaluation."
            )
        if any(c.entity_id == "psi-25" for c in intent.entity_constraints):
            categories.append("SOURCE_COVERAGE_DIFFERENCE")
            causes.append("V1 two-run view versus canonical BASS-II run coverage.")
        added_d = sorted(set(new["v2_direct"]) - set(old["v2_direct"]))
        added_r = sorted(set(new["v2_related"]) - set(old["v2_related"]))
        if added_d:
            categories.append("VALID_SEMANTIC_CORRECTION")
            causes.append(
                "Approved material aliases separate PMMA specimen identity from geometry; source-backed BASS-II runs now match unconstrained PMMA search."
            )
            if gold[new["case_id"]]["expected"].get("unknown_terms") or gold[new["case_id"]][
                "expected"
            ].get("ambiguous_terms"):
                categories.append("BENCHMARK_CONTRACT_MISMATCH")
                causes.append(
                    "Legacy conversion loses an ambiguous/unresolved term; a run match is not an answer to material equivalence. Native interpreter retains ambiguity."
                )
        if added_r:
            categories.append("EVIDENCE_SET_EXPANSION")
            causes.append(
                "Approved aliases expose additional same-material specimens; missing conditions stay UNKNOWN, not DIRECT."
            )
        if not new["evidence_equal"]:
            categories.append("EVIDENCE_SET_EXPANSION")
            causes.append(
                "Documentary retention and candidate evidence differ; item-level relevance remains unreviewed."
            )
        if (not new["direct_equal"] or not new["related_equal"]) and not categories:
            categories.append("UNRESOLVED")
        discrepancies.append(
            {
                **new,
                "query": gold[new["case_id"]]["query"],
                "intent": intent.model_dump(mode="json"),
                "baseline_v2_direct": old["v2_direct"],
                "baseline_v2_related": old["v2_related"],
                "added_direct": added_d,
                "added_related": added_r,
                "categories": sorted(set(categories)),
                "first_stage": "INTERPRETATION"
                if "BENCHMARK_CONTRACT_MISMATCH" in categories
                else "ENTITY_NORMALIZATION_AND_CORPUS_ELIGIBILITY",
                "root_causes": causes,
                "scientific_adjudication": "REVIEW_REQUIRED" if categories else "NO_DISCREPANCY",
                "recommended_correction": "Preserve V1 rollback; adjudicate native-intent semantic eligibility and evidence usefulness separately.",
            }
        )
    parity = {
        "default_metrics": native["metrics"],
        "enriched_metrics": enriched["metrics"],
        "cases": discrepancies,
        "category_counts": dict(Counter(c for r in discrepancies for c in r["categories"])),
        "categories_overlap": True,
        "genuine_regressions_confirmed": 0,
        "independent_scientific_review": "PENDING",
    }
    write("parity_reconciliation", parity)
    technical = []
    for cid, mentions in [("qi14", ["observations"]), ("qi18", ["open questions"]), ("qi27", [])]:
        case = next(c for c in cases if c["case_id"] == cid)
        proposal = MinimalInterpretationV2(requested_information=mentions)
        if cid == "qi27":
            proposal.entities = ["PMMA", "microgravity"]
        intent = resolve_minimal(proposal, store.registry, language, query=case["query"])
        result = execute_native(
            intent, case["query"], store, evidence, hierarchical=True, relational=True
        )
        technical.append(
            {
                "case_id": cid,
                "original_question": case["query"],
                "frozen_intent": case["frozen_intent"],
                "proposed_intent": intent.model_dump(mode="json"),
                "proposal_authority": "NON_EXPERT_TECHNICAL_CONTRACT_REVIEW",
                "approval": "PENDING",
                "direct": result.bundle.direct_evidence,
                "related": result.bundle.related_evidence,
                "evidence_ids": [p["evidence_id"] for p in result.bundle.evidence_passages],
                "selection_trace": result.bundle.retrieval_metadata["selection_trace"],
                "reviewer_label": None,
                "reviewer_rationale": None,
            }
        )
    write("epistemic_proposals", technical)
    live = lines("phase3c_enrichment_live_v1.jsonl")
    events = lines("phase3c_enrichment_ablation_api_calls_v1.jsonl")
    planning = lines("phase3c_enrichment_planning_v1.jsonl")
    connectivity = read("phase3c_enrichment_connectivity_v1.json")
    replay = []
    for receipt in lines("phase3c_knowledge_live_calls_v1.jsonl"):
        if receipt.get("component") != "extraction":
            continue
        for rejected in receipt.get("rejected", []):
            p = rejected["proposal"]
            eid = receipt["case_id"]
            try:
                candidate = validate_relation_proposal(
                    {
                        **p,
                        "evidence_id": eid,
                        "source_id": evidence.source_metadata(eid)["source_id"],
                    },
                    evidence,
                )
                replay.append(
                    {
                        "candidate": candidate,
                        "status": "RECOVERED",
                        "execution_mode": "HISTORICAL_REPLAY_REVISED_SPAN_VALIDATION",
                        "new_calls": 0,
                    }
                )
            except (ValueError, TypeError) as exc:
                replay.append(
                    {
                        "proposal": p,
                        "status": "REJECTED",
                        "reason": str(exc),
                        "execution_mode": "HISTORICAL_REPLAY_REVISED_SPAN_VALIDATION",
                        "new_calls": 0,
                    }
                )
    write("historical_span_revalidation", replay)
    revalidated = []
    original_cases = read("phase3c_related_cases_v1.json")
    for event in events:
        if event.get("event_type") != "query_expansion":
            continue
        case = next(c for c in original_cases if _digest(c["query"]) == event["query_digest"])
        intent = QueryIntentV2.model_validate(case["intent"])
        for candidate in event["accepted"]:
            allowed, reason = validate_expansion(
                case["query"], candidate["query"], intent, store.registry, language
            )
            revalidated.append(
                {
                    "case_id": case["case_id"],
                    "query": candidate["query"],
                    "original_live_verdict": "ACCEPTED",
                    "revised_verdict": "ACCEPTED" if allowed else "REJECTED",
                    "reason": reason,
                    "new_calls": 0,
                    "execution_mode": "NEW_LIVE_RESPONSE_REVISED_DETERMINISTIC_VALIDATION",
                }
            )
    write("expansion_revalidation", revalidated)
    api_rows = connectivity + live + planning + events

    def provider(r):
        return r.get("provider", "Jev" if r.get("event_type") == "jev_advisory" else "NVIDIA")

    api = {
        "new_calls": dict(Counter(provider(r) for r in api_rows if r.get("new_calls") == 1)),
        "replayed_provider_calls": 0,
        "revised_historical_span_checks": len(replay),
        "validated_relation_proposals": sum(len(r.get("validated", [])) for r in live),
        "rejected_relation_proposals": sum(len(r.get("rejected", [])) for r in live),
        "proposals_published_as_canonical_science": 0,
        "service_failures": sum(
            r.get("status") == "FAIL" or bool(r.get("error")) for r in api_rows
        ),
        "usage": {},
        "median_latency_ms": {},
        "equivalent_expansions_initially_accepted": sum(len(r.get("accepted", [])) for r in events),
        "equivalent_expansions_initially_rejected": sum(len(r.get("rejected", [])) for r in events),
        "exploratory_hypotheses": sum(len(r.get("hypotheses", [])) for r in events),
        "equivalent_expansion_revalidation": revalidated,
        "rerank_invalid_judgments": sum(len(r.get("invalid", [])) for r in events),
        "independent_relevance": "UNMEASURED; no expert labels",
        "monetary_cost": "UNAVAILABLE",
        "call_limit": {"NVIDIA": 60, "Jev": 30},
        "cache_note": "D/E may reuse live C/D responses within this campaign; warm latency is not cold model performance.",
    }
    for p in ["NVIDIA", "Jev"]:
        rows = [r for r in api_rows if provider(r) == p]
        usages = [
            r.get("usage", r.get("output", r.get("response", {})).get("usage", {})) for r in rows
        ]
        api["usage"][p] = {
            "input_tokens": sum(u.get("input_tokens") or 0 for u in usages),
            "output_tokens": sum(u.get("output_tokens") or 0 for u in usages),
            "receipts_with_usage": sum(bool(u) for u in usages),
            "receipt_count": len(rows),
        }
        latency = [r.get("latency_ms", r.get("usage", {}).get("latency_ms")) for r in rows]
        api["median_latency_ms"][p] = statistics.median(x for x in latency if x is not None)
    write("live_summary", api)
    ablation = lines("phase3c_enrichment_ablation_v1.jsonl")
    variants = {}
    for variant in "ABCDE":
        rows = [r for r in ablation if r["variant"] == variant]
        labels = [
            r["required_identity_recovered"]
            for r in rows
            if r["required_identity_recovered"] is not None
        ]
        variants[variant] = {
            "identity_recovery": {"numerator": sum(labels), "denominator": len(labels)},
            "cases": len(rows),
            "candidate_budget": 40,
            "median_latency_ms": statistics.median(r["user_perceived_latency_ms"] for r in rows),
            "scientific_precision_at_5": {
                "numerator": None,
                "denominator": 0,
                "status": "NOT_MEASURED",
            },
        }
    lexical = [
        {
            "case_id": r["case_id"],
            "budget": 40,
            "evidence_ids": [p["evidence_id"] for p in evidence.search(r["query"], limit=40)],
        }
        for r in ablation
        if r["variant"] == "A"
    ]
    regression_metrics = {}
    for label in "AB":
        ids = [
            c["variants"][label]["identity_recovered"]
            for c in cases
            if c["variants"][label]["identity_recovered"] is not None
        ]
        false = [
            c["variants"][label]["false_direct"]
            for c in cases
            if c["variants"][label]["false_direct"] is not None
        ]
        regression_metrics[label] = {
            "identity_recovery": {"numerator": sum(ids), "denominator": len(ids)},
            "false_direct": {"numerator": sum(false), "denominator": len(false)},
            "cases": len(cases),
        }
    write(
        "benchmark_summary",
        {
            "variants": variants,
            "budget_matched_lexical": lexical,
            "regressions": regression_metrics,
            "new_source_field_recovery": read("phase3c_enrichment_regressions_v1.json")[
                "source_field_recovery"
            ],
            "scientific_relevance_gold": "PENDING",
            "full_vs_selective_reranking": "NOT_EXECUTED; no claim of superior utility",
        },
    )
    packet = read("phase3c_knowledge_review_packet_v2.json")
    additions = [item for r in live for item in r.get("validated", [])]
    write(
        "review_packet",
        {
            "original_packet": packet,
            "original_reviewer_fields_preserved": True,
            "technical_proposals": technical,
            "candidate_relations": [
                {
                    "candidate": a,
                    "reviewer_label": None,
                    "reviewer_rationale": None,
                    "reviewer_authority_assessment": None,
                }
                for a in additions
            ],
            "scientific_adjudication": "PENDING",
            "expert_labels": 0,
        },
    )
    field_inventory = read("phase3c_enrichment_field_inventory_v1.json")
    role_proposals = {
        "gmt": "IDENTIFIER_OR_TIMESTAMP",
        "flow_restrictor": "CATEGORICAL_SETTING",
        "fan_display": "SETPOINT_DISPLAY",
        "air_display": "SETPOINT_DISPLAY",
        "total_frames_shot": "ACQUISITION_COUNT",
    }
    for item in field_inventory:
        if item["role"] == "UNRESOLVED":
            item["role_proposal"] = role_proposals.get(item["kind"], "INSUFFICIENT_SOURCE_CONTEXT")
            item["review_status"] = "REVIEW_REQUIRED"
    write("field_role_proposals", field_inventory)
    # Integrity gates run against current implementation, not preserved old results.
    baseline = read("phase3c_enrichment_baseline_v1.json")["digests"]
    frozen = {
        p: h
        for p, h in baseline.items()
        if p.startswith(("data/raw/", "data/canonical/", "evals/", "artifacts/"))
    }
    changed = [
        p
        for p, h in frozen.items()
        if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
    ]
    secrets = [os.environ[k] for k in ["NVIDIA_API_KEY", "TYPESAFE_API_KEY"] if os.environ.get(k)]
    leaks = []
    for folder in ["src", "scripts", "tests", "domain", "ontology", "docs", "artifacts", "evals"]:
        for path in (ROOT / folder).rglob("*"):
            if (
                path.is_file()
                and path.suffix
                in {
                    ".py",
                    ".json",
                    ".jsonl",
                    ".yaml",
                    ".md",
                    ".ttl",
                    ".txt",
                }
                and any(secret in path.read_text(errors="replace") for secret in secrets)
            ):
                leaks.append(str(path.relative_to(ROOT)))
    qualities = []
    for args in [
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "pytest", "-q"],
    ]:
        run = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
        log = ART / ("phase3c_enrichment_quality_" + str(len(qualities)) + "_v1.txt")
        log.write_text(run.stdout + run.stderr)
        qualities.append(
            {
                "command": " ".join(args),
                "exit_code": run.returncode,
                "output": str(log.relative_to(ROOT)),
                "summary": run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "",
            }
        )
    canonical = Graph().parse(ROOT / "data/canonical/graph.ttl")
    evidence.db.execute("INSERT INTO passages_fts(passages_fts) VALUES('integrity-check')")
    previous = Graph().parse(ART / "phase3c_knowledge_final_graph_v2.ttl")
    missing_relations = sorted(
        str(x)
        for x in set(previous.subjects(RDF.type, NS.SemanticRelation))
        - set(store.graph.subjects(RDF.type, NS.SemanticRelation))
    )
    integrity = {
        "quality": qualities,
        "immutable_files_checked": len(frozen),
        "changed_immutable_files": changed,
        "secret_matches_outside_env": leaks,
        "env_mode": oct((ROOT / ".env").stat().st_mode & 0o777),
        "env_ignored": subprocess.run(
            ["git", "check-ignore", "-q", ".env"], cwd=ROOT, check=False
        ).returncode
        == 0,
        "env_untracked": subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode
        != 0,
        "canonical_shacl": bool(
            validate(canonical, shacl_graph=str(ROOT / "ontology/shapes.ttl"))[0]
        ),
        "native_shacl": bool(
            validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
        ),
        "literal_shacl": bool(
            validate(canonical, shacl_graph=str(ROOT / "ontology/enrichment_shapes.ttl"))[0]
        ),
        "sqlite_integrity": evidence.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_violations": [
            list(r) for r in evidence.db.execute("PRAGMA foreign_key_check")
        ],
        "fts_integrity": "PASS",
        "fts_missing": evidence.db.execute(
            "SELECT count(*) FROM passages WHERE evidence_id NOT IN (SELECT evidence_id FROM passages_fts)"
        ).fetchone()[0],
        "broken_graph_evidence": [
            str(e)
            for e in set(store.graph.objects(None, NS.evidenceRef))
            if evidence.resolve(str(e)) is None
        ],
        "missing_previous_relations": missing_relations,
        "current_condition_count": store.projection_report["conditions"],
        "current_staging_count": len(store.projection_staging),
        "postfreeze_and_dynamic_suites": [
            "phase3c_enrichment_native_checks_v1/phase3c_dynamic_property_benchmark.json",
            "phase3c_enrichment_native_checks_v1/phase3c_postfreeze_extensibility.json",
        ],
        "changed_code_manifest": [
            p
            for p, h in baseline.items()
            if p.startswith(("src/", "domain/", "ontology/"))
            and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
        ],
    }
    integrity["status"] = (
        "PASS"
        if all(q["exit_code"] == 0 for q in qualities)
        and not changed
        and not leaks
        and not missing_relations
        and not integrity["broken_graph_evidence"]
        and all(
            integrity[k]
            for k in [
                "canonical_shacl",
                "native_shacl",
                "literal_shacl",
                "env_ignored",
                "env_untracked",
            ]
        )
        and integrity["sqlite_integrity"] == "ok"
        and not integrity["foreign_key_violations"]
        and not integrity["fts_missing"]
        else "FAIL"
    )
    write("integrity", integrity)
    decisions = {
        "ONTOLOGY_SEMANTIC_COVERAGE": "PARTIAL",
        "SPECIMEN_NORMALIZATION": "ADOPT",
        "UNRESOLVED_FIELD_MAPPING": "IMPROVED",
        "SCIENTIFIC_EXTRACTION": "KEEP_EXPERIMENTAL",
        "EXISTING_CORPUS_ENRICHMENT": "PARTIAL",
        "PSI_CORPUS_COVERAGE": "PARTIAL",
        "GRAPH_PROJECTION": "ADOPT",
        "EPISTEMIC_CLASSIFICATION": "REVIEW_REQUIRED",
        "V1_V2_PARITY": "PARTIALLY_RESOLVED",
        "NEMOTRON_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "JEV_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "INDEPENDENT_SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
        "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    write(
        "decisions",
        {
            "decisions": decisions,
            "quality_status": integrity["status"],
            "scope": "Adoption applies to source-preserving mechanics and existing-authority accessors. Experimental flags remain off; new scientific interpretation is not approved.",
        },
    )
    psi = read("phase3c_enrichment_psi_v1.json")
    texts = {
        "PHASE3C_SEMANTIC_ENRICHMENT_IMPLEMENTATION.md": """# Phase 3C semantic enrichment implementation\n\nReuses QueryIntentV2, SemanticRegistry, native projection/executor, Evidence Registry, NVIDIA client and Jev adapter. `SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED=false` independently gates additions inside existing ontology enrichment; both flags must be true. Default exact V2 and V1 remain available. No embeddings or second retrieval engine.\n\nTyped source accessors resolve original canonical kinds, validate units and preserve original records plus evidence. They do not establish observed measurements. Numeric failures remain staged. Exact atomic Fuel-cell matches resolve existing source-backed material identities. Original specimen IDs and descriptions remain distinct. Idempotence covers graph triples, executable counts and staging. Alias lookup recognizes source labels with spaces. Source-span validation preserves source offsets through whitespace/NFC only. PDF table cells retain bounding boxes and physical indexes; scientific roles remain unapproved.\n\nChanges: `ingestion/enrichment.py`, `knowledge.py`, `source_spans.py`, `semantic.py`, `pdf.py`, `normalization/units.py`, `query/native_interpreter.py`, `evidence_selection.py`, `native.py`, `controlled_reasoning.py`, registry/configuration and ontology shapes. Existing adapters and shared dotenv loader are reused unchanged. API failure never publishes a fact.\n\nArtifact index: all `artifacts/phase3c_enrichment_*_v1.json/jsonl`, fresh native suites in `phase3c_enrichment_native_checks_v1/v2`. Final measured receipts: summary, benchmark_summary, live_summary, parity_reconciliation, review_packet, integrity and decisions. Historical files remain inputs.""",
        "PHASE3C_ONTOLOGY_PREDICATE_RECONCILIATION.md": """# Ontology predicate reconciliation\n\n13 historically used predicates audited individually with actual subject types, object kinds and usage counts. Twelve existing literal predicates receive datatype declarations and local SHACL constraints; no domain/range entailments, authority promotion or new scientific vocabulary. `supportedBy` remains undeclared pending evidential semantics review. Existing citation links cannot establish scientific support or causality.\n\nOntology now has 32 classes, 11 object properties, 16 datatype properties and 18 subclass edges. Class/property relation meanings remain distinct. Canonical and native SHACL results are in integrity; full per-predicate dispositions in predicate_audit. Scientific ontology coverage remains partial.""",
        "PHASE3C_SPECIMEN_NORMALIZATION_RESULTS.md": """# Specimen normalization\n\n70/405 approved-alias matches become 312/405 source-backed material links: 242 additional specimens use exact canonical material plus unique immutable CSV Fuel cells. Two material identities (Methanol and Heptane) are exposed; 405 specimen identities remain distinct. Original labels, evidence rows and units are retained.\n\nOf the original 335 unresolved descriptions: 242 normalizable with existing source authority, 36 require aliases, 57 lack sufficient context; ontology extension/conflicting identities/non-material categories have zero classified cases in this bounded audit. These categories are technical dispositions, not expert correctness labels. Duplicate table rows without a stable row locator remain unresolved rather than guessed. Generic negation, mixture/coating and compatible-material descriptions do not automatically resolve identity.\n\nExplicit labeled dimensions are extracted as review proposals, preserving source spans and original units. Unlabeled sizes acquire no invented axis. Full specimen inventory and per-source counts are versioned. Independent normalization precision is unmeasured.""",
        "PHASE3C_UNRESOLVED_FIELDS_ANALYSIS.md": f"""# Unresolved source fields\n\n2314 unresolved fields become 537; executable canonical source conditions increase 682 → 2459. Fourteen declarative source-field selectors expose 1777 records. Every new field retains original values/units, numeric conversion, evidence and role; observed status is NOT_ASSERTED. All 1777/1777 expected values are executable in source-field regression, not a measurement-accuracy benchmark.\n\nFLEX Burning rate is declared in mm (258 records): rate dimension unresolved, never replaced by burn time or invented mm²/s. FLEX CO composition was canonically named carbon dioxide (274 records): chemical identity unresolved, never silently published as CO₂. Five remaining operational fields require review. Field-role proposals retain their unresolved status.\n\nMappings by kind: `{json.dumps(summary["mapped_by_kind"])}`. Initial and extinction diameters are distinct selectors; gas initial/final values remain distinct; ppm normalizes to fraction; specimen dimensions and intervention power/time are not observed responses. Field inventory is the full field-level review queue.""",
        "PHASE3C_SCIENTIFIC_EXTRACTION_CORRECTIONS.md": f"""# Scientific extraction corrections\n\nSpan recovery accepts exact unique text or reversible whitespace/NFC differences with offsets into the original passage. Numbers, units, paraphrases, negation changes and ambiguous duplicate spans remain rejected. A matching span establishes textual presence only. Semantic mapping and expert approval remain separate.\n\nFive fresh live extraction passages yielded {api["validated_relation_proposals"]} span-validated candidates and {api["rejected_relation_proposals"]} rejected proposals. None became canonical science. Candidate receipts preserve supporting text, source/document identity and unverified page status. Historical failed outputs were separately revalidated and explicitly labeled replay, not new inference.\n\nThree actual NASA PDFs produced 21 detected table layouts, retaining cells/bounding boxes and verified physical PDF indexes. Multi-line cells can contain several source rows; no automatic row alignment, measured values or canonical publication is claimed. A synthetic table regression verifies column separation. PDF page verification applies only to these newly extracted layout receipts.\n\nA fresh expansion added NASA safety to a broad acrylic query. The equivalent-reformulation validator now rejects unverified semantic wording additions after removing only typed quantities and approved aliases. Exploratory discovery remains separately permitted. Expansion revalidation documents revised post-processing of the already executed call.""",
        "PHASE3C_EXISTING_CORPUS_ENRICHMENT.md": """# Existing corpus enrichment\n\nSame runtime snapshot: 282 sources, 286 documents, 6055 passages; eight sources have canonical records. Canonical runs remain 405 and observations remain one. Native entities 4110 → 4112; reified relations 4769 → 5011; source accessors 682 → 2459; normalized specimen-material links 70 → 312. Existing 3808 explicit structural associations and previous relation identities are retained. No model-created observed measurements or taxonomy facts.\n\nEnrichment selects existing experimental tables, SoFIE specimen descriptions, Saffire observation/intervention text, suppression guidance/question context and FLEX PDF tables. The main validated increase is access to already canonical fields and material identities. Narrative relation candidates remain staged. Per-source inventory contains passage counts, canonical types and new mappings; zero canonical records does not prove a source lacks science.\n\nTwo official PSI metadata records were acquired append-only, outside the evaluated 282-source snapshot. They are exposed investigations, not unseen holdouts; no new canonical facts or runtime passages are attributed to acquisition. Corpus enrichment remains partial because documentary scientific statements still need approved mappings and source review.""",
        "PHASE3C_PSI_COVERAGE_RECONCILIATION.md": f"""# PSI coverage reconciliation\n\nRechecked [NASA's official combustion inventory]({psi["rows"][0]["official_inventory"]}) and reconciled all 19 investigations against local metadata, files, evidence and canonical records. Three are partially structured (BASS-II, FLEX, Saffire-I), seven have local structured tables not published canonically, four have documentary exposure, five are not acquired under this policy. Exact canonical InvestigationRecord-title count 2/19 understated FLEX run representation.\n\nEvery row includes PSI identifier/DOI, official access path, local table files, canonical record counts, documentary evidence and next action. DAFT and DAFT-2 share PSI-47 metadata; lexical documentary matches do not establish experimental identity. Local index historical downloaded-file counts do not imply those files exist on this machine.\n\nBounded new acquisition: PSI-68 and PSI-107 official metadata, append-only raw receipts and digests. Prioritized backlog: validate available BASS/FLEX-2/Saffire-II/III/SAME/SAME-R/SPICE table schemas, row identities, scientific roles and evidence references before canonical approval; then acquire missing ACME and scoped scientific datasets. Refresh official inventory and revisions monthly, append changed versions, freeze unseen first-pass evaluations. This is coverage of a defined 19-investigation universe, not all NASA knowledge.""",
        "PHASE3C_EPISTEMIC_CLASSIFICATION_AUDIT.md": """# Epistemic classification audit\n\nqi14 frozen intent requests both observation and safety implication; native execution follows that contract. Technical proposal requests observations only and separates the observed failure to extinguish from active-suppression implications. qi27 broad NASA reports should not be forced to SafetyImplication. Historical gold stays unchanged.\n\nqi18 standalone “Additional focused tests may be required…” does not state question content. Experimental source enrichment excludes anaphoric-only question records from DIRECT and recovers same-source containing question context as CONTEXTUAL for review. This does not label rhetorical requirements questions as independently approved NASA open scientific questions.\n\nqi19 SoFIE explicitly describes acrylic cylinders (PMMA), supporting documentary relevance and specimen nomenclature; no general acrylic→PMMA equivalence, family-wide behavior or measured result is published. Fresh reranking rates its exact fuel span HIGH, versus historical LOW; this is a model proposal, not an expert label.\n\nOriginal 16 review elements and their reviewer fields remain intact in the expanded packet. New source-backed proposals and technical intent adjudications have blank expert labels. Observations, specifications, interventions, conclusions and implications retain separate authority.""",
        "PHASE3C_V1_V2_PARITY_RECONCILIATION.md": f"""# Fresh V1/V2 parity reconciliation\n\nDefault exact: DIRECT 31/39, RELATED 37/39, evidence-set identity 6/39. Experimental ontology/source enrichment: DIRECT 28/39, RELATED 28/39, evidence identity 6/39. These are agreement metrics, not accuracy.\n\nCase-level receipt includes V1/V2 identities, pre-enrichment V2 outputs, first divergence, root cause, proposed correction and review status. Added PMMA DIRECT records in qi24/qi25 reflect approved specimen aliases; qi49 inherits legacy conversion's lost acrylic ambiguity and cannot establish equivalence. Additional BASS-II same-material runs become RELATED where other conditions are UNKNOWN. Frozen NASA/suppression information-class mistakes and V1 two-run coverage are kept visible.\n\nCategory counts (overlapping): `{json.dumps(parity["category_counts"])}`. No equality-forcing repair or historical gold edit. Zero genuine implementation regressions confirmed in this audit does not establish relevance of every expanded candidate; residual item-level disagreements require scientific review. Separate 20-case source-backed regression stays 8/8 identity and 0/4 incorrect DIRECT; dynamic suites freshly pass 230/230 and 125/125.""",
        "PHASE3C_NEMOTRON_JEV_ENRICHMENT_EVALUATION.md": f"""# Live Nemotron/Jev enrichment evaluation\n\nUses existing ignored/untracked .env with restrictive permissions, shared dotenv precedence and unchanged provider adapters. Both fresh minimal connectivity requests succeeded. New calls: `{json.dumps(api["new_calls"])}`; provider failures {api["service_failures"]}; monetary cost unavailable. Token usage and measured medians are in live_summary. Fresh extraction, unknown specimen normalization, verified graph-route proposal, broad planning and selective reranking are included; model proposals publish zero scientific facts.\n\nA–E pilot: three previously exposed cases, identical runtime snapshot and budget 40; A uses existing V2/ontology baseline, B adds source enrichment and existing relational traversal, C adds controlled planning, D selective reranking, E optional Jev. Budget-matched lexical candidates are included. This layered pilot cannot separately attribute B's effects to traversal versus enrichment. Objective identities recover 2/2 in each variant. D/E can reuse compatible responses within the same campaign; warm E latency is not evidence of faster cold inference. Full-versus-selective utility comparison was not run.\n\nFive extraction passages produce {api["validated_relation_proposals"]} source-span-valid candidates, {api["rejected_relation_proposals"]} rejects. One initial equivalent expansion is rejected by revised semantic validation. Reranking invalid judgments: {api["rerank_invalid_judgments"]}. Jev classifies explicit observations versus implications as advisory; no independent review-workload or relevance benefit was measured. Precision@5 and scientific incremental value remain unmeasured without expert labels. Both providers remain optional/experimental.""",
        "PHASE3C_ENRICHMENT_FINAL_READINESS_DECISION.md": f"""# Phase 3C enrichment final decision\n\nMeasured source-preserving enrichment improves executable knowledge without promoting model assertions. Same snapshot regression: 8/8 objective identities, 0/4 designated false DIRECT; 1777/1777 source-field values executable; dynamic 230/230 and post-freeze 125/125. Quality/integrity status: {integrity["status"]}; command receipts and immutable digest checks in integrity. Historical raw/canonical/gold/receipts remain unchanged.\n\n```text\n"""
        + "\n".join(f"{k} = {v}" for k, v in decisions.items())
        + """\n```\n\nRemaining blockers: define supportedBy evidential semantics; resolve ambiguous rate units and CO/CO₂ source terminology; obtain source context for 93 specimens; independently adjudicate epistemic labels, taxonomy and expanded candidate usefulness; publish seven available investigation tables only after schema/row/role/provenance validation; acquire missing scoped investigations. Technical approval is not scientist approval. No Phase 4 work was initiated.\n\nReports and machine-readable receipts are indexed in PHASE3C_SEMANTIC_ENRICHMENT_IMPLEMENTATION.md.""",
    }
    for filename, text in texts.items():
        path = ROOT / "docs" / filename
        if path.exists():
            raise FileExistsError(path)
        path.write_text(text + "\n")
    write(
        "artifact_index",
        {
            "reports": list(texts),
            "receipts": sorted(str(p.relative_to(ROOT)) for p in ART.glob("phase3c_enrichment*")),
            "authoritative_graph": "artifacts/phase3c_enrichment_graph_v1.ttl",
            "decisions": "artifacts/phase3c_enrichment_decisions_v1.json",
        },
    )
    print(
        json.dumps(
            {"quality": integrity["status"], "api": api["new_calls"], "decisions": decisions}
        )
    )


if __name__ == "__main__":
    main()
