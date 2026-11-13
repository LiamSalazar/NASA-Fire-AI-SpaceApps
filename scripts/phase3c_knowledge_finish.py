"""Measured reports, reviewer packet and final integrity for this bounded iteration."""

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
from nasa_fire_ai.ingestion.knowledge import enrich_native
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS
from nasa_fire_ai.query.offline_parser import parse_query
from nasa_fire_ai.query.v2 import v1_to_v2

ART = ROOT / "artifacts"


def read(name):
    return json.loads((ART / name).read_text())


def lines(name):
    return [json.loads(line) for line in (ART / name).read_text().splitlines()]


def receipt(name, data):
    path = ART / f"phase3c_knowledge_{name}_v1.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(data, indent=2) + "\n")


def report(name, body):
    path = ROOT / "docs" / f"PHASE3C_{name}.md"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(body.strip() + "\n")


def main():
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "false"
    evidence = EvidenceRegistry(Settings().registry_path)
    records = json.loads((ROOT / "data/canonical/records.json").read_text())
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    mentions = {
        k: v["aliases"]
        for k, v in language["entity_mentions"].items()
        if v["relation"] == "hasMaterial"
    }
    enrich_native(store, records, evidence, ROOT / "ontology/fire_safety.ttl", mentions)
    store.graph.serialize(ART / "phase3c_knowledge_final_graph_v1.ttl", format="turtle")
    summary = read("phase3c_knowledge_summary_v1.json")
    ontology = read("phase3c_knowledge_ontology_v1.json")
    projection = read("phase3c_knowledge_projection_final_v1.json")
    parity = read("phase3c_knowledge_native_checks_v1/phase3c_native_parity.json")
    gold = json.loads((ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json").read_text())
    gold_by_id = {c["id"]: c for c in gold["cases"]}
    discrepancies = []
    for case in parity["cases"]:
        if case["direct_equal"] and case["related_equal"] and case["evidence_equal"]:
            continue
        intent = v1_to_v2(parse_query(gold_by_id[case["case_id"]]["query"]))
        categories = []
        reasons = []
        if not case["direct_equal"] or not case["related_equal"]:
            if intent.requested_information == ["SafetyImplication"]:
                categories.append("BENCHMARK_CONTRACT_MISMATCH")
                reasons.append(
                    "V1 parser imposes SafetyImplication on NASA/epistemic wording; parity conversion preserves that mistaken intent. This harness does not evaluate the validated native interpreter."
                )
            elif intent.entity_constraints and all(
                c.relation == "belongsToInvestigation" for c in intent.entity_constraints
            ):
                categories.append("SOURCE_COVERAGE_DIFFERENCE")
                reasons.append(
                    "V1 two-run view omits BASS-II canonical runs present in the 405-run native projection."
                )
            else:
                categories.append("UNRESOLVED")
        if not case["evidence_equal"]:
            categories.append("EVIDENCE_SET_EXPANSION")
            reasons.append(
                "V2 evidence retention and information/documentary eligibility differ from V1; identity-set inequality alone does not measure scientific correctness."
            )
        discrepancies.append(
            {
                **case,
                "query": gold_by_id[case["case_id"]]["query"],
                "intent": intent.model_dump(mode="json"),
                "categories": categories,
                "first_stage": "interpretation contract"
                if "BENCHMARK_CONTRACT_MISMATCH" in categories
                else "candidate corpus/eligibility",
                "root_cause": reasons,
                "scientific_adjudication": "REVIEW_REQUIRED",
                "correction": "Use native validated intent for scientific evaluation; preserve historical parity harness. Review evidence-set differences individually.",
            }
        )
    receipt(
        "parity_root_causes",
        {
            "fresh_metrics": parity["metrics"],
            "cases": discrepancies,
            "category_counts": dict(
                Counter(category for row in discrepancies for category in row["categories"])
            ),
            "feature_flags": "exact default, enrichment disabled",
            "historical_harness_preserved": True,
        },
    )
    gap_rows = [
        {
            "gap": "3808 explicit run/investigation/sample/condition foreign keys absent from native associations",
            "earliest_stage": "G_GRAPH_PROJECTION",
            "status": "CORRECTED_OPT_IN",
            "evidence": "phase3c_knowledge_coverage_cases_v1.json",
        },
        {
            "gap": "Specimen description used as material identity",
            "earliest_stage": "E_NORMALIZATION",
            "status": "PARTIAL_CORRECTION",
            "resolved_approved_aliases": 70,
            "total_samples": 405,
        },
        {
            "gap": "2314 scalar fields lack executable property mapping",
            "earliest_stage": "F_SEMANTIC_REGISTRY",
            "status": "REVIEW_REQUIRED",
            "note": "Condition entities are now represented; their unknown property semantics remain unresolved.",
        },
        {
            "gap": "Acrylic/PMMA nomenclature present in documents but no approved family taxonomy",
            "earliest_stage": "C_EXTRACTION_AND_I_AUTHORITY",
            "status": "STAGED",
            "evidence_ids": ["E-751f8e0f5230aa68"],
        },
        {
            "gap": "Historical generator links Saffire-IV source observation to psi-98 Saffire-I",
            "earliest_stage": "G_GRAPH_PROJECTION",
            "severity": "HIGH",
            "status": "GENERATOR_CORRECTED_HISTORICAL_GRAPH_QUARANTINED",
            "note": "Native enrichment reads explicit canonical records, not historical instance edges.",
        },
        {
            "gap": "13 predicates in original graph lack ontology declarations",
            "earliest_stage": "D_ONTOLOGY",
            "status": "REVIEW_REQUIRED",
            "terms": ontology["undeclared_original_graph_predicates"],
        },
        {
            "gap": "Only 8/282 sources have canonical records",
            "earliest_stage": "C_EXTRACTION",
            "status": "INCOMPLETE_INVENTORY",
            "note": "Presence metric, not completeness or relevance of every passage.",
        },
        {
            "gap": "Two official sources acquired and parsed but require scientific extraction review",
            "earliest_stage": "A_SOURCE_COVERAGE",
            "status": "ACQUIRED_ISOLATED_REVIEW_REQUIRED",
        },
    ]
    receipt("gaps", gap_rows)
    proposals = [
        {
            "term": "supportedBy",
            "category": "NEW_RELATION_PROPOSED",
            "status": "REVIEW_REQUIRED",
            "reason": "Historical graph uses undeclared evidential relation; causal/evidential scope needs review.",
        },
        {
            "term": "specimen geometry relation",
            "category": "NEW_RELATION_PROPOSED",
            "status": "REVIEW_REQUIRED",
            "reason": "Geometry class exists but geometry predicate in historical graph is undeclared.",
        },
        {
            "term": "hasCondition / usesSample / madeOf / hasRun / reportedBy",
            "category": "EXISTING_ONTOLOGY_RELATION",
            "status": "EXPLICIT_FOREIGN_KEYS_PROJECTED",
        },
        {
            "term": "unmapped condition kinds",
            "category": "EXISTING_RELATION_REQUIRES_MAPPING",
            "status": "REVIEW_REQUIRED",
        },
        {
            "term": "acrylic family membership",
            "category": "SEMANTICALLY_AMBIGUOUS",
            "status": "REVIEW_REQUIRED",
            "reason": "Source-local nomenclature does not approve universal family edges.",
        },
    ]
    receipt("ontology_proposals", proposals)
    live = lines("phase3c_knowledge_live_calls_v1.jsonl")
    retries = lines("phase3c_knowledge_jev_retry_v1.jsonl")
    events = lines("phase3c_knowledge_ablation_api_calls_v1.jsonl")
    new_sources = lines("phase3c_knowledge_new_source_first_pass_v1.jsonl")
    nv_rows = (
        [r for r in live if r["component"] != "jev_advisory"]
        + [r for r in events if r["event_type"] != "jev_advisory"]
        + new_sources
    )
    jev_rows = (
        [r for r in live if r["component"] == "jev_advisory"]
        + retries
        + [r for r in events if r["event_type"] == "jev_advisory"]
    )
    nv_latency = [
        r["usage"]["latency_ms"]
        for r in nv_rows
        if r.get("usage", {}).get("latency_ms") is not None
    ]
    jev_latency = [
        r["latency_ms"]
        for r in jev_rows
        if r.get("status", "PASS") == "PASS" and r.get("latency_ms") is not None
    ]
    api_summary = {
        "NVIDIA_new_requests": 1 + sum(r.get("new_calls", 1) for r in nv_rows),
        "Jev_new_requests_including_contract_failures": 1
        + sum(r.get("new_calls", 1) for r in jev_rows),
        "initial_jev_contract_failures": 3,
        "corrected_jev_retries_successful": sum(r["status"] == "PASS" for r in retries),
        "NVIDIA_median_pilot_latency_ms": statistics.median(nv_latency),
        "Jev_median_success_latency_ms": statistics.median(jev_latency),
        "NVIDIA_input_tokens_excluding_connectivity": sum(
            r.get("usage", {}).get("input_tokens") or 0 for r in nv_rows
        ),
        "NVIDIA_output_tokens_excluding_connectivity": sum(
            r.get("usage", {}).get("output_tokens") or 0 for r in nv_rows
        ),
        "equivalent_expansions_accepted_initial_pilot": sum(
            len(r.get("accepted", [])) for r in live if r["component"] == "exploratory_planning"
        ),
        "equivalent_expansions_rejected_initial_pilot": sum(
            len(r.get("rejected", [])) for r in live if r["component"] == "exploratory_planning"
        ),
        "model_facts_published": 0,
        "monetary_cost": "NOT_AVAILABLE",
        "independent_relevance": "REVIEW_REQUIRED",
    }
    receipt("api_final", api_summary)
    ablation = lines("phase3c_knowledge_ablation_v1.jsonl")
    variants = {}
    for variant in "ABCDE":
        rows = [r for r in ablation if r["variant"] == variant]
        objective = [r for r in rows if r["required_identity_recovered"] is not None]
        variants[variant] = {
            "required_identity_recovery": {
                "numerator": sum(r["required_identity_recovered"] for r in objective),
                "denominator": len(objective),
            },
            "median_observed_latency_ms": statistics.median(
                r["user_perceived_latency_ms"] for r in rows
            ),
            "execution_modes": [
                r["receipt"]["configurations"]["B"].get("expansion", {}).get("execution_mode")
                for r in rows
            ],
            "scientific_precision_at_5": {"status": "UNESTABLISHED", "denominator": 0},
        }
    lexical = []
    for row in ablation:
        if row["variant"] == "A":
            hits = evidence.search(row["query"], limit=40)
            lexical.append(
                {
                    "case_id": row["case_id"],
                    "budget": 40,
                    "candidate_ids": [p["evidence_id"] for p in hits],
                    "policy": "Documentary lexical discovery; independently classify against original intent",
                }
            )
    receipt(
        "benchmark_final",
        {
            "variants": variants,
            "lexical_budget_matched": lexical,
            "objective_association_coverage": {
                "A": projection["association_coverage_before"],
                "B": projection["association_coverage_after"],
            },
            "latency_warning": "C makes new planning calls; D/E may reuse compatible cached planning/reranking. E warm latency is not a cold provider-speed improvement.",
            "independent_labels": 0,
            "selective_reranker_activation": {"numerator": 2, "denominator": 3},
            "full_reranking_comparison": "NOT_EXECUTED; scientific utility unestablished",
        },
    )
    original_packet = read("phase3c_controlled_scientific_relevance_review_packet_v2.json")
    additions = read("phase3c_related_review_packet_v1.json")["additions"]
    selected, seen = [], set()
    # Stratify across original questions and scientific roles, preserving each source row intact.
    for case_id in ["qi03", "qi11", "qi12", "qi14", "qi18", "qi19", "qi27", "qi42"]:
        rows = [r for r in additions if r["case_id"] == case_id]
        for row in rows[:2]:
            eid = row["candidate_evidence_id"]
            if eid in seen:
                continue
            seen.add(eid)
            selected.append(
                {
                    "original_review_row": row,
                    "selection_stratum": case_id,
                    "reviewer_label": None,
                    "reviewer_rationale": None,
                    "reviewer_authority_assessment": None,
                }
            )
    for row in read("phase3c_knowledge_staged_relations_v1.json"):
        selected.append(
            {
                "relation_candidate": row,
                "selection_stratum": "unapproved scientific relation",
                "reviewer_label": None,
                "reviewer_rationale": None,
                "reviewer_authority_assessment": None,
            }
        )
    for row in new_sources:
        selected.append(
            {
                "first_pass_source": row,
                "selection_stratum": "new source / structured gap",
                "reviewer_label": None,
                "reviewer_rationale": None,
                "reviewer_authority_assessment": None,
            }
        )
    receipt(
        "review_packet",
        {
            "original_packet_preserved": "phase3c_controlled_scientific_relevance_review_packet_v2.json",
            "original_cases": len(original_packet["cases"]),
            "original_candidates": sum(len(c["candidates"]) for c in original_packet["cases"]),
            "full_related_universe_preserved": "phase3c_related_review_packet_v1.json",
            "selected": selected,
            "expert_labels": 0,
            "adjudication": "PENDING",
        },
    )
    baseline = read("phase3c_knowledge_baseline_v1.json")["digests"]
    immutable = {
        p: h
        for p, h in baseline.items()
        if p.startswith(("data/raw/", "data/canonical/", "evals/", "artifacts/"))
    }
    changed = [
        p for p, h in immutable.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
    ]
    secrets_found = []
    secrets = [os.getenv(key) for key in ["NVIDIA_API_KEY", "TYPESAFE_API_KEY"] if os.getenv(key)]
    for folder in ["src", "scripts", "tests", "domain", "ontology", "docs", "artifacts", "evals"]:
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".json", ".jsonl", ".md", ".yaml", ".ttl"}:
                text = path.read_text(errors="replace")
                if any(secret in text for secret in secrets):
                    secrets_found.append(str(path.relative_to(ROOT)))
    native_ok = bool(
        validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
    )
    canonical_ok = bool(
        validate(
            Graph().parse(ROOT / "data/canonical/graph.ttl"),
            shacl_graph=str(ROOT / "ontology/shapes.ttl"),
        )[0]
    )
    integrity = {
        "immutable_checked": len(immutable),
        "changed_immutable_files": changed,
        "secret_matches_outside_env": secrets_found,
        "env_mode": oct((ROOT / ".env").stat().st_mode & 0o777),
        "env_ignored": subprocess.run(
            ["git", "check-ignore", "-q", ".env"], cwd=ROOT, check=False
        ).returncode
        == 0,
        "env_untracked": subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        ).returncode
        != 0,
        "native_shacl": native_ok,
        "canonical_shacl": canonical_ok,
        "sqlite_integrity": evidence.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_check": [list(r) for r in evidence.db.execute("PRAGMA foreign_key_check")],
        "unresolved_graph_evidence_ids": [
            str(e)
            for e in set(store.graph.objects(None, NS.evidenceRef))
            if evidence.resolve(str(e)) is None
        ],
        "fts_missing": evidence.db.execute(
            "SELECT count(*) FROM passages WHERE evidence_id NOT IN (SELECT evidence_id FROM passages_fts)"
        ).fetchone()[0],
        "final_graph_triples": len(store.graph),
        "final_relation_count": len(set(store.graph.subjects(RDF.type, NS.SemanticRelation))),
    }
    receipt("final_integrity", integrity)
    decisions = {
        "ONTOLOGY_COVERAGE_DECISION": "PARTIAL",
        "CORPUS_COVERAGE_DECISION": "PARTIAL",
        "SCIENTIFIC_EXTRACTION_DECISION": "KEEP_EXPERIMENTAL",
        "ENTITY_NORMALIZATION_DECISION": "ADOPT",
        "GRAPH_PROJECTION_DECISION": "ADOPT",
        "GRAPH_SEMANTIC_RETRIEVAL_DECISION": "KEEP_EXPERIMENTAL",
        "V1_V2_PARITY_DECISION": "PARTIALLY_RESOLVED",
        "NEMOTRON_LIVE_EVALUATION": "PASS",
        "JEV_LIVE_EVALUATION": "PASS",
        "SCIENTIFIC_RELEVANCE_DECISION": "REVIEW_REQUIRED",
        "V2_DEFAULT_PATH_DECISION": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    receipt("decisions", decisions)
    report(
        "ONTOLOGY_COVERAGE_AUDIT",
        f"""# Phase 3C ontology coverage

Original ontology: {len(ontology["classes"])} classes, {len(ontology["object_properties"])} object properties, {len(ontology["datatype_properties"])} datatype properties, {len(ontology["class_hierarchies"])} subclass declarations. No domain/range or property hierarchy declarations. Original graph uses 13 undeclared predicates; SHACL passing does not establish ontology completeness or scientific authority.

Native registry previously exposed 17 classes and five relations. Opt-in enrichment imports the source schema, aligns identically named classes, and exposes existing object properties. Associations are not taxonomy or causal support. supportedBy and specimen geometry predicates need reviewed ontology proposals; see phase3c_knowledge_ontology_proposals_v1.json. No new scientific terms or material-family edges were approved.
""",
    )
    report(
        "SOURCE_TO_GRAPH_GAP_ANALYSIS",
        """# Phase 3C source-to-graph gaps

The first loss occurs at different stages, not one missing taxonomy. Canonical foreign keys existed but 3,808 associations were not projected; these are now available opt-in. 2,314 condition fields lack executable registry mappings; their source-backed condition entities are preserved without numeric or measurement semantics being invented. 70 specimen descriptions resolve through existing approved aliases; remaining literals retain their source identities.

A historical generator linked Saffire-IV observations to Saffire-I by experiment-name rules. Those rules were removed. Historical canonical graph remains immutable and is not imported as instance authority. Acrylic nomenclature proposals and evidence-support semantics remain staged. Exact per-gap diagnoses and severity: phase3c_knowledge_gaps_v1.json.
""",
    )
    report(
        "NASA_CORPUS_COVERAGE",
        f"""# Phase 3C bounded NASA corpus coverage

Runtime: {summary["sources"]} sources, {summary["documents"]} documents, {summary["passages"]} passages. Only {summary["sources_with_canonical_records"]}/{summary["sources"]} source records have canonical scientific records. This is representation presence, not exhaustive extraction coverage or relevance precision.

Discovery used two bounded NTRS metadata queries (20-result ceilings); three distinct metadata identities were recorded. Two selected publications were acquired and parsed: [20210017780](https://ntrs.nasa.gov/citations/20210017780), 14 physical pages; [20220012861](https://ntrs.nasa.gov/citations/20220012861), nine pages. The second concerns two-color pyrometry, not a generic suppression experiment. Both remain isolated from runtime publication. Discovery receipts include authoritative URLs and raw digests. These exposed development sources are not blind holdouts.

The [official PSI combustion list](https://www.nasa.gov/physical-sciences-informatics-psi/psi-investigations-by-research-area/) defines an additional relevant acquisition backlog. This iteration has not reconciled every investigation/revision against all sources; NASA-wide completeness is unmeasured. Next refresh: reconcile PSI investigation IDs, paginate scoped NTRS queries, compare NASA standards revision metadata, deduplicate by publication ID/DOI/digest, prioritize missing experimental and safety evidence. Freeze genuinely unseen sources before inspecting their content.
""",
    )
    report(
        "ENTITY_NORMALIZATION_AUDIT",
        """# Phase 3C specimen normalization

405 specimens retain unchanged source descriptions and canonical geometry/condition payloads. A generic boundary-aware approved-alias resolver recognizes 70/405: PMMA 41, SIBAL Fabric 29. This count measures alias resolution, not all material identities; methanol/heptane literals remain preserved. Ambiguous multi-material labels are not merged. No production branch names a material.

Runs link to Sample through usesSample; samples link to actual material through madeOf. Approved identities also receive source-backed hasMaterial links. Unknown descriptions remain literal and recoverable. Geometry scalars remain source condition records, not newly approved geometric properties. Synthetic tests cover different geometries, different materials, ambiguity and unknown descriptions. Receipts: phase3c_knowledge_projection_final_v1.json.
""",
    )
    report(
        "SEMANTIC_EXTRACTION_AND_STAGING",
        """# Phase 3C scientific extraction and staging

Nemotron extraction is opt-in and proposed only. Exact source/evidence identity, supporting substring and both mentions are checked deterministically. Validation cannot approve scientific interpretation, numeric context or taxonomy. Content-addressed staging is idempotent; conflicting reuse of an existing candidate ID raises an error rather than overwriting review state.

Initial extraction accepted three span-valid proposals and rejected one mention/span mismatch. Two new-source first-pass calls are preserved separately. All remain pending scientific review. No LLM-proposed relation was published. Existing canonical foreign keys can be projected through existing ontology relations; unknown property mappings and unsupported evidential/causal relations remain proposals.
""",
    )
    report(
        "GRAPH_RELATION_COVERAGE",
        """# Phase 3C graph relation coverage

Objective fixture: 3,808 explicit foreign keys frozen in canonical records before development. Native association coverage changed from 0/3,808 to 3,808/3,808. This tests projection completeness for those records, not scientific extraction recall across NASA documents. Final graph and original first-pass projection have separate versioned receipts.

Native SemanticGraph.explore_route validates declared relation types, evidence resolution, traversal direction, depth/budget, cycles and review states. Property hierarchy may authorize a narrower predicate; the path records the actual predicate. Class inheritance uses approved subclass edges only; exact execution remains available. Example source-backed routes: psi-98 → hasRun → usesSample → madeOf; psi-98 → hasRun → hasCondition; Saffire-IV observation → reportedBy → source publication. None establishes causality or an observation-to-conclusion support relation. A synthetic evidential-looking relation remains an association unless stronger semantics are explicitly validated.

ONTOLOGY_GRAPH_ENRICHMENT_ENABLED=false by default. Unknown relationships raise a controlled error; exact retrieval survives optional model failures. Source ontology and canonical data are unchanged.
""",
    )
    report(
        "V1_V2_PARITY_ROOT_CAUSES",
        """# Phase 3C fresh parity diagnosis

Fresh exact parity: DIRECT 31/39; RELATED 37/39; evidence identities 6/39. Historical files are unchanged. The harness deliberately converts V1 parsing into V2; it does not test the native interpreter's corrected linguistic contract.

qi07/qi08: V1's two-run corpus omits BASS-II, while native canonical projection contains its runs. NASA/epistemic cases including qi14, qi16–18, qi27, qi33 and qi45 inherit V1's forced SafetyImplication class. Scientific correctness cannot be inferred from parity on that mistaken query contract. Evidence-set expansion accounts for additional differences and requires item-level scientific review. No repair was made solely to force parity. Case identities, original intents and first-stage causes: phase3c_knowledge_parity_root_causes_v1.json. Remaining evidence eligibility judgments require adjudication.
""",
    )
    report(
        "LIVE_NEMOTRON_JEV_EVALUATION",
        f"""# Phase 3C bounded live providers

Persistent .env is ignored/untracked, mode 0600; explicit environment variables take precedence. Both real connectivity requests returned HTTP 200: Nemotron configured model, Jev alias jev-latest resolved to jev-1.13.0. Final pilot totals: {api_summary["NVIDIA_new_requests"]} new NVIDIA requests; {api_summary["Jev_new_requests_including_contract_failures"]} new Jev requests including three failed contract calls and three justified corrected retries. No historical output is counted as new inference.

Median non-connectivity NVIDIA call latency {api_summary["NVIDIA_median_pilot_latency_ms"]:.1f} ms; successful Jev pilot latency {api_summary["Jev_median_success_latency_ms"]:.1f} ms. Token usage is recorded per call; monetary pricing was unavailable. Initial equivalent expansions accepted {api_summary["equivalent_expansions_accepted_initial_pilot"]}, rejected {api_summary["equivalent_expansions_rejected_initial_pilot"]}. Operator-preserving deterministic tests retain >= versus > distinction. Structured/model relevance output is not scientific gold.

A–E pilot contains three cases, two objective evidence identities. Selective reranking activated on 2/3 cases. C executed new planning, D selectively executed new reranking, E reused compatible same-input outputs plus optional Jev. Warm E latency cannot establish a cold-speed advantage. No independently reviewed relevance improvement or full-versus-selective scientific utility was established. Jev corrected rhetorical proposals are advisory; its incremental scientific relevance remains unestablished.
""",
    )
    report(
        "SCIENTIFIC_KNOWLEDGE_COVERAGE_RESULTS",
        """# Phase 3C knowledge coverage results

3,808/3,808 explicit canonical associations are now projected (previously 0/3,808). 70/405 specimen descriptions resolve through approved aliases. 405 runs and 682 typed executable conditions remain available; the other source condition records retain unresolved property semantics. No observed measurements or approved family relations were added.

Budget ceiling 40 for each A–E configuration; both objective identities recovered in every variant (2/2), including qi14. Acrylic ambiguity retrieves documentary candidates experimentally but cannot establish family-level DIRECT matches. A separate lexical baseline uses the same 40-candidate ceiling; larger discovery pools are not attributed to semantic reasoning. Precision@5/recall of scientific relevance remain unmeasured (zero independent labels).

Fresh dynamic suites pass 230/230 and 125/125. Generic fixtures additionally cover class/property hierarchies, multiple inheritance, associations, source provenance, cycles, rejected/unknown relations and dynamic relation declarations. Review packet deduplicates across historical cases and adds pending relation/new-source evidence. Full audit universes remain intact. Quality and final integrity receipts report exact checks; historical passes are not presented as new results.
""",
    )
    report(
        "KNOWLEDGE_COMPLETENESS_FINAL_DECISION",
        "# Phase 3C knowledge completeness decision\n\n"
        + "\n".join(f"- `{key} = {value}`" for key, value in decisions.items())
        + "\n\nAdoption applies to source-preserving normalization and explicit-foreign-key projection, not blanket enablement of experimental reasoning. Ontology lacks declarations/constraints and reviewed evidential semantics; corpus discovery is bounded and only eight runtime sources contain canonical records. Independent scientists must adjudicate nomenclature, taxonomy, evidence applicability and missing relation semantics. Remaining engineering: exhaustive scoped source inventory, expanded extraction coverage and a separate validated-native-intent parity campaign. Phase 4 has not begun.",
    )
    print(json.dumps({"decisions": decisions, "api": api_summary, "integrity": integrity}))


if __name__ == "__main__":
    main()
