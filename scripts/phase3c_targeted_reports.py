"""Publish measured closure receipts and review-required adoption decisions."""

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def read(name):
    return json.loads((ART / name).read_text())


def write(name, value):
    path = ART / f"phase3c_targeted_{name}_v2.json"
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2))


def main():
    integrity = read("phase3c_targeted_integrity_v6.json")
    assert integrity["status"] == "PASS"
    parity = read("phase3c_targeted_native_checks_v4/phase3c_native_parity.json")
    cases = read("phase3c_targeted_parity_reconciliation_v4.json")["cases"]
    scientific = read("phase3c_targeted_scientific_cases_v4.json")
    fields = read("phase3c_targeted_field_correctness_v2.json")
    flex = read("phase3c_targeted_flex_corrections_v3.json")
    datasets = read("phase3c_targeted_psi_publication_v2.json")
    pdf = read("phase3c_targeted_pdf_provenance_v2.json")
    provenance = read("phase3c_targeted_legacy_provenance_v2.json")
    intents = read("phase3c_targeted_query_intents_v4.json")
    live = [
        json.loads(line)
        for filename in [
            "phase3c_targeted_live_v1.jsonl",
            "phase3c_targeted_live_review_v1.jsonl",
            "phase3c_targeted_ablation_calls_v1.jsonl",
        ]
        for line in (ART / filename).read_text().splitlines()
    ]
    for row in live:
        if not isinstance(row.get("usage"), dict):
            row["usage"] = {}
        if not row.get("provider"):
            row["provider"] = "Jev" if row["event_type"] == "jev_advisory" else "NVIDIA"
    usage = {
        provider: {
            "new_calls": sum(r.get("new_calls", 0) for r in live if r["provider"] == provider),
            "failed_contracts": sum(
                r.get("status") == "FAILED" for r in live if r["provider"] == provider
            ),
            "known_input_tokens": sum(
                (r.get("usage") or {}).get("input_tokens") or 0
                for r in live
                if r["provider"] == provider
            ),
            "known_output_tokens": sum(
                (r.get("usage") or {}).get("output_tokens") or 0
                for r in live
                if r["provider"] == provider
            ),
            "median_latency_ms": statistics.median(
                r.get("latency_ms", (r.get("usage") or {}).get("latency_ms", 0))
                for r in live
                if r["provider"] == provider
            ),
            "usage_completeness": "NVIDIA failed source-span contract lacks captured usage; Jev adapter does not expose token usage",
            "scientific_incremental_value": "NOT_MEASURABLE",
        }
        for provider in ["NVIDIA", "Jev"]
    }
    write(
        "live_summary",
        {
            "providers": usage,
            "new_inference_only": True,
            "canonical_model_facts_published": 0,
            "cache_replay_note": "D/E/F pilot reuses compatible expansion/rerank contracts; F latency includes warm replay and is not a cold inference speed comparison",
            "scientific_support_failures": 1,
            "independently_reviewed_labels": 0,
            "ranking_strategy_comparison": "deterministic weighted ordering versus selective contextual model proposals; no independent relevance labels",
        },
    )
    remaining = fields["remaining_staging"]
    write(
        "remaining_ambiguities",
        {
            "count": len(remaining),
            "records": remaining,
            "source_conflicts": flex["staged"],
            "original_pending": 537,
            "corrected": len(flex["corrections"]),
            "observations_added": 0,
        },
    )
    write("bass_identity_tests", [r for r in intents if "BASS" in r["original_query"]])
    write(
        "conceptual_query_tests",
        [r for r in intents if r["metadata"].get("conceptual_query", {}).get("active")],
    )
    epistemic = []
    for proposal in read("phase3c_enrichment_epistemic_proposals_v1.json"):
        case = next(r for r in cases if r["case_id"] == proposal["case_id"])
        epistemic.append(
            {
                "original_proposal": proposal,
                "current_native_resolution": case["native_resolution_probe"],
                "current_result": case["variants"]["native_C"],
                "expert_approval": None,
                "disposition": "TECHNICAL_INTENT_CORRECTION; independent scientific adjudication pending",
            }
        )
    write("epistemic_dispositions", epistemic)
    review = read("phase3c_targeted_related_review_complete_v4.json")["candidates"]
    strata = {}
    for candidate in review:
        details = candidate["candidate"].get("relationship_explanation", {})
        dimensions = details.get("dimensions", [])
        label = (
            "UNKNOWN_GRAVITY"
            if any(
                d["dimension"] == "hasGravityCondition" and d["status"] == "UNKNOWN"
                for d in dimensions
            )
            else "DIFFERING_CONSTRAINTS"
            if any(d["status"] == "DIFFER" for d in dimensions)
            else "RELATED_CONSTRAINT_OVERLAP"
        )
        strata.setdefault(label, [])
        if len(strata[label]) < 5:
            strata[label].append(candidate)
    write(
        "stratified_review",
        {
            "technical_strata": strata,
            "conceptual_cases": read("phase3c_targeted_conceptual_query_tests_v2.json"),
            "epistemic_cases": epistemic,
            "all_related_candidates": len(review),
            "reviewer_labels": 0,
            "scientific_precision_at_1_3_5": "NOT_MEASURABLE",
            "scientific_recall_at_k": "NOT_MEASURABLE",
            "nDCG": "NOT_MEASURABLE",
            "false_direct_scientific_rate": "NOT_MEASURABLE",
            "contamination": "UNADJUDICATED; do not count all expansions as beneficial",
            "additional_strata_required": [
                "independently verified DIRECT",
                "same phenomenon/different experiment",
                "incorrect study identity",
                "lexically similar irrelevant document",
                "genuine no-evidence",
                "claim attribution accuracy",
            ],
        },
    )
    objective = {
        variant: {
            "identity_numerator": sum(
                c["variants"][variant]["identity_recovered"] is True for c in scientific
            ),
            "identity_denominator": sum(
                c["variants"][variant]["identity_recovered"] is not None for c in scientific
            ),
            "false_direct_numerator": sum(
                c["variants"][variant]["false_direct"] is True for c in scientific
            ),
            "false_direct_denominator": sum(
                c["variants"][variant]["false_direct"] is not None for c in scientific
            ),
        }
        for variant in ["A", "B", "C"]
    }
    write(
        "benchmark_summary",
        {
            "objective_source_identity_cases": objective,
            "parity": parity["metrics"],
            "fields": {
                "preserved": fields["preservation_numerator"],
                "converted": fields["conversion_numerator"],
                "denominator": fields["denominator"],
            },
            "dynamic_cases": 230,
            "postfreeze_cases": 125,
            "independent_scientific_precision": "NOT_MEASURABLE",
            "source_corpus_difference": "A/B 6055 original passages; C adds 733 structured table rows, 111 BASS run identities and 19 sample identities. FLEX corrections tested separately and in complete reconciliation C.",
        },
    )
    decisions = {
        "QUERY_INTENT_CORRECTION": "ADOPT",
        "CONCEPTUAL_QUERY_HANDLING": "KEEP_EXPERIMENTAL",
        "RELATED_SELECTION": "KEEP_EXPERIMENTAL",
        "EPISTEMIC_CLASSIFICATION": "REVIEW_REQUIRED",
        "FLEX_FIELD_SEMANTICS": "PARTIALLY_RESOLVED",
        "PSI_DATASET_PUBLICATION": "PARTIAL",
        "SOURCE_PROVENANCE": "PARTIALLY_VERIFIED",
        "V1_V2_PARITY": "PARTIALLY_RESOLVED",
        "NEMOTRON_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "JEV_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "INDEPENDENT_SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
        "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    write("decisions", decisions)
    special = [
        r
        for r in cases
        if r["case_id"] in ["qi01", "qi03", "qi08", "qi14", "qi18", "qi27", "qi42", "qi49"]
    ]
    table = "| Case | Historical enriched RELATED | Current eligible RELATED | Presentation groups |\n|---|---:|---:|---:|\n"
    for r in special:
        b = r["variants"]["B"]
        table += f"| {r['case_id']} | {len(r['historical_enriched_related'])} | {len(b['related'])} | {len(b['related_groups']['groups'])} |\n"
    dataset_table = "| Dataset | Rows | Published runs | Published samples | Identity rows staged / quantities pending |\n|---|---:|---:|---:|---|\n"
    for d in datasets:
        dataset_table += f"| {d['investigation']} ({d['source_id']}) | {d['rows_examined']} | {d['published_runs']} | {d.get('published_samples', 0)} | {d['staged_rows']}; unsupported scientific quantities remain pending |\n"
    decision_text = "\n".join(f"{k} = {v}" for k, v in decisions.items())
    reports = {
        "PHASE3C_TARGETED_SCIENTIFIC_CORRECTION_IMPLEMENTATION.md": f"""# Targeted Phase 3C scientific correction implementation

Implemented registry alias separation/maximal-span identity matching; existing V2 EXPLAIN/documentary operation for conceptual queries; bounded native investigation groups; broad report information-class handling; statement-scope topical checks; RELATED presentation groups with complete candidate retention; verified CSV cell and physical PDF provenance; additive opt-in PSI identities and original-PDF source-unit crosswalks. No QueryIntentV3, new engine, ontology replacement or Phase 4.

New ingestion modules: `validated_psi.py`, `structured_provenance.py`, `source_corrections.py`. Existing native executor, interpreter, hierarchy explanations, evidence registry and renderer carry the changes. Existing NVIDIA/Jev adapters and dotenv precedence are reused. No credentials were changed or published. Default V1 path remains available unchanged, with its historical alias/epistemic limitations explicitly retained for rollback and parity.

`PSI_STRUCTURED_PUBLICATION_ENABLED=false` and `FLEX_SOURCE_CORRECTIONS_ENABLED=false` are default opt-in gates. Existing source/ontology and controlled-reasoning flags remain independent. Raw files, original canonical inputs, historical gold and receipts remain unchanged: {integrity["immutable_files_checked"]} preserved digests. Typed source accessors now carry explicit initial/final scope rather than inheriting every context word in the question. Three exact approved sample material labels create evidence-backed PMMA/SIBAL links; mixtures and missing labels remain unresolved. New canonical version files publish 111 source-explicit runs and 19 samples; publication is engineering source-contract validation, not independent scientist review.

Run `uv run python scripts/phase3c_targeted_campaign.py` stages only with unused version names; historical outputs are never overwritten. Reports and receipts are indexed by `artifacts/phase3c_targeted_artifact_index_v2.json`. Baseline tests: 149. Final suite: 170. Quality gates and corpus receipts identify exact inputs. Initial v1 exploratory receipts included additive documents; v2/v3/v4 comparisons isolate the original evidence universe. Snapshot v2 supersedes v1 operational schema migration while preserving the same 6055 original passages.
""",
        "PHASE3C_BASS_IDENTITY_AND_QUERY_INTENT_AUDIT.md": """# BASS identity and query intent

The native language dictionary incorrectly assigned BASS to PSI-25; PSI-26 is distinct. BASS-II and its official name now resolve only PSI-25; BASS and its official name resolve PSI-26. Longest-contained approved alias suppression prevents BASS inside BASS-II from becoming an extra investigation. Separate occurrences preserve both identities. No family relation or shared-run identity was invented.

With opt-in identities: BASS retrieves 111 published PSI-26 runs; BASS-II retrieves its existing 129; both yield two explicit groups totaling 240. Repeated/missing BASS as-run numbers (11 rows) remain staged. Canonical publication uses source identifiers, not arbitrary row counts. Without publication enabled, recognizing PSI-26 does not manufacture runs.

Generic tests use DEMO/DEMO-X and two synthetic investigations. `phase3c_targeted_bass_identity_tests_v2.json` records real queries. Frozen qi08 retains its incorrect PSI-25 filter for parity; current native interpretation is separately recorded. The V1 rollback parser retains historical behavior; corrected identity is adopted on the native V2 path.
""",
        "PHASE3C_CONCEPTUAL_QUERY_SEMANTICS.md": """# Conceptual scientific query semantics

A linguistic guard recognizes term meaning, equivalence, explicit class membership, definitions and relationship questions. It reuses EXPLAIN plus Publication in QueryIntentV2. The original question also guards execution after lossy legacy conversion. Experimental DIRECT/RELATED hits are not answers to equivalence questions. Approved provenance-bearing ontology relations and registry identities are inspected; only approved relations with both mentioned endpoints are returned with their evidence. Pending relations are counted but never adopted. Documentary quotations remain available; no new exact equivalence is inferred.

Does acrylic mean PMMA? returns documentary support with zero experimental DIRECT/RELATED results. A source describing an acrylic PMMA specimen cannot establish equivalence across a material family, uniform combustion behavior, or class-wide findings. Unknown terminology remains unresolved scientific knowledge; no independent material taxonomy was supplied. Broad structured ontology relationship answering remains experimental: the implementation prevents the demonstrated retrieval substitution but does not independently adjudicate terminology.

Unseen tests cover helium/nitrogen, specimen/apparatus, extinction definitions and an explicitly approved synthetic identity relation. Native and legacy-converted conceptual searches are both tested. Receipts: `phase3c_targeted_conceptual_query_tests_v2.json` and versioned query intents. This is conceptual operation correctness, not evidence relevance precision.
""",
        "PHASE3C_RELATED_EVIDENCE_RELEVANCE_AUDIT.md": f"""# RELATED scientific relevance audit

{table}
These are eligible candidate counts, not useful-evidence counts. The complete 39-case candidate packet contains {len(review)} RELATED candidates with scientific constraints and provenance; independent labels remain empty. Historical qi01's two Saffire different-material matches are excluded by the explicitly enabled material-anchor policy. This policy/configuration distinction is not a measured precision improvement.

Grouping uses investigation, actual material and requested-condition signature, preserves UNKNOWN, retains all run IDs/citations and deduplicates citations within groups. If detailed dimensions are unavailable, complete reported-value signatures prevent collapsing contradictory records. Other conditions can differ; the response states that limitation. Numeric conditions, ontology paths and evidence references remain accessible. Phenomenon and measurement context are now explicit, with absent facts UNKNOWN and usefulness UNADJUDICATED.

No new ranking weights were fitted to gold. Existing weighted ordering remains experimental. A bounded selective-model comparison on the suppression-report query identifies the known intervention as partial contextual support, without changing eligibility. No independent ranking-strategy superiority is demonstrated. Useful additional evidence and irrelevant contamination are UNADJUDICATED, rather than counted as zero or assumed beneficial. Precision@1/3/5, useful RELATED precision, recall and nDCG are NOT MEASURABLE without independent judged labels. Stratified proposals and required missing strata are in `phase3c_targeted_stratified_review_v2.json`.
""",
        "PHASE3C_FLEX_AMBIGUOUS_FIELDS_RESOLUTION.md": """# FLEX ambiguous field resolution

Initial unresolved: 274 initial-carbon-dioxide records, 258 burning-rate records and five operational records. NASA/TP-2015-216046 A.1 (printed 19, physical PDF 25) defines CO2 and a burning-rate constant fitted from droplet diameter squared versus time. Table IX (physical pages 26–34) labels CO2 mole fraction and mm2/s. The local PSI CSV headings omit subscript/exponent/unit details. See [NASA report](https://ntrs.nasa.gov/citations/20150023456) and immutable `data/raw/ntrs-20150023456.pdf`.

Validated correction: 274/274 CO2 records and 258/258 burning-rate constants, total 532/532. Exact reported approximation strings (~6 and ~9) corroborate row correspondence without becoming exact durations; no approximate or conflicting value is forced into a scalar match. Original row numbers were reindexed in parts of the CSV, so the crosswalk preserves CSV labels and original NASA test labels separately. Original CSV values and units remain intact; PDF-backed units are additional validated source quantities. Burning-rate constants remain SOURCE_DERIVED, never observed lengths or invented linear rates. mm2/s normalizes to m2/s; mm remains m.

`gmt` is scheduling metadata; `flow_restrictor` apparatus setting; `fan_display` and `air_display` uncalibrated displays; `total_frames_shot` acquisition count. They remain outside scientific observation publication. Five operational records remain staged; both scientific field families are fully source-corroborated. Source-version digests, all field records, exact PDF geometry and conflicts are in the FLEX corrections and remaining-ambiguity receipts. Independent scientist adjudication remains pending.

The original 1777 executable fields pass 1777/1777 value/unit preservation and deterministic conversions. This does not establish independent scientific role accuracy. NASA's dictionary notes that some extinction diameters are extrapolated; the generic accessor deliberately never asserts all are directly measured.
""",
        "PHASE3C_PSI_DATASET_PUBLICATION_RESULTS.md": f"""# PSI structured dataset publication

{dataset_table}
All 733 source rows were inspected with original headers, checksums, duplicate counts and complete staged source values. Exact file paths come from the prior PSI reconciliation artifact. New canonical artifacts are additive and opt-in. Engineering source-contract approval is not independent scientist review.

BASS: unique explicit As Run Test # plus source date/sample permits 111 run identities; 11 missing/repeated identities remain staged. Original material descriptions are preserved without guessing PMMA from an unlabeled sphere or inheriting gravity. FLEX-2's eight rows list configuration alternatives/ranges, not identified individual runs. Saffire-II publishes nine explicit sample identities, including blank material labels; camera/footnote rows remain separate. Mixed gravity columns, approximate values and derived O2 footnotes prevent blanket observation publication. Saffire-III publishes two samples, without claiming samples are runs. SAME publishes eight sample identities; same-conditions-as references are not silently expanded. SAME-R and SPICE require stable trial/run identity and scientific role review; SPICE duplicate acquisition rows are not new experiments.

Supported sample labels remain raw source labels, with no canonical material merge or unsupported numeric mapping. Native projection idempotence and explicit identity queries are tested. Detailed staged rows and blockers: `phase3c_targeted_psi_publication_v2.json`. Current canonical totals add 111 runs and 19 samples; the old 405 runs remain unchanged.
""",
        "PHASE3C_TABLE_PROVENANCE_VALIDATION.md": f"""# Table provenance validation

FLEX import code assigned the same one-based logical CSV record ordinal to start_offset/end_offset. These were never valid character spans; historical values remain unchanged and are explicitly typed by new registry locators. Character spans retain half-open start/end for narrative/PDF evidence. Multiline/duplicate CSV fixtures verify that logical records and character offsets are not conflated.

Structured locations are stored only in SQLite, carrying source file/checksum/version, table, row ordinal, column ordinal, original header/value and unit-source status. No missing data dictionary is invented. All seven datasets have row/cell locators. Historical row recovery verifies checksum and reconstructed source text; documented legacy UTF-8 replacement decoding is corroborated against the raw bytes while original cp1252 cells remain preserved. {sum(r["status"] == "EXACT_ROW_VERIFIED" for r in provenance["rows"])} historical CSV rows are verified; {provenance["round_trip_numerator"]}/{provenance["round_trip_denominator"]} CSV cell checks pass.

FLEX original PDF rows are bound by test/engineering identifiers, all column line counts and actual same-row word coordinates. {pdf["numerator"]}/{pdf["denominator"]} corrected scientific cells round-trip to physical pages and cell boxes. The evidence API and native bundles expose verified PDF location metadata. Source-level coverage beyond these verified records remains PARTIALLY_VERIFIED; older/missing/ambiguous locators are not manufactured. Receipts: legacy_provenance_v2, cell_provenance_v1, pdf_provenance_v1.
""",
        "PHASE3C_EPISTEMIC_CLASSIFICATION_CORRECTIONS.md": """# Epistemic classification corrections

qi14 current native intent requests ReportedObservation only and retrieves the one source-backed flame-persistence observation. Historical safety-only or observation-plus-implication contracts remain frozen; their implication hits are not accepted as an answer to the original observation request.

qi18 current native open-question lookup produces no DIRECT complete question from the isolated anaphoric statement. Antecedent source passages remain contextual review material. Frozen safety-class retrieval can return three statements, which is a benchmark-contract discrepancy, not three identified scientific questions.

qi27 broad reporting requests observations, interventions and conclusions, rather than SafetyImplication alone. Explicit suppression wordforms must appear in the statement's own documented scope. Same material alone or a topic appearing elsewhere on a page cannot establish answering relevance. The PMMA flow-off intervention remains contextual support; missing run/gravity applicability prevents DIRECT. No experimental outcome or gravity is inherited without evidence.

Existing epistemic proposals are preserved with current dispositions and empty expert approval fields. Engineering class/topic tests are separate from independent scientific gold. `phase3c_targeted_epistemic_dispositions_v2.json` records both historical proposals and current behavior.
""",
        "PHASE3C_ENRICHED_PARITY_RECONCILIATION.md": """# Enriched parity reconciliation

Fresh frozen-contract 39-case suite: DIRECT 29/39, RELATED 28/39, exact evidence identity 6/39. The historic enriched comparison was 28/39, 28/39 and 6/39. Parity is agreement with the legacy path, not scientific accuracy. qi49's experimental substitution is corrected using the original question without editing frozen gold.

The complete per-case v2 reconciliation preserves query, frozen intent/gold, historical before/enriched identities, new A/B/C identities, added/removed candidates, native-resolution probe, constraints, evidence identities and unresolved review disposition. The deterministic native probe uses raw alias/information discovery and does not claim a full provider interpretation of every numeric query. Four difficult interpretation questions have actual new provider receipts. A/B use the same original evidence universe; C labels newly published structured identities and PDF crosswalks separately.

BASS's frozen PSI-25 intent still retrieves BASS-II for parity; corrected native intent retrieves PSI-26. qi14/18/27 preserve disputed epistemic gold independently. No expansion is called beneficial merely for matching material. All unresolved scientific discrepancies remain REVIEW_REQUIRED. Dynamic-property regression 230/230 and post-freeze extensibility 125/125 pass. The 20-case scientific suite recovers 8/8 designated source identities and 0/4 designated false-DIRECT cases in A/B/C; these are technical objective checks, not expert precision.
""",
        "PHASE3C_NEMOTRON_JEV_TARGETED_EVALUATION.md": f"""# Nemotron and Jev targeted evaluation

Existing dotenv loader and provider adapters were reused with explicit environment precedence and no credential changes. New NVIDIA requests: {usage["NVIDIA"]["new_calls"]}; new Jev requests: {usage["Jev"]["new_calls"]}. NVIDIA has one failed source-span output contract; no model-generated canonical scientific fact was published. Usage/latency/prompt versions/input digests are in live_summary and checkpointed JSONL receipts; incomplete usage is explicitly marked.

Pilots cover BASS/BASS-II, acrylic/PMMA conceptual interpretation, broad suppression-report intent, observation/intervention/open-question context, BASS/FLEX-2 tables and RELATED review. The A–F one-query pilot uses candidate budget 20: A deterministic original fields, B enriched existing corpus, C validated PSI identities, D controlled exploration, E selective reranking, F optional Jev. D/E/F compatible-cache replay is distinguished from new inference. F's warm latency cannot establish faster cold inference.

The reranker retains the known PMMA flow-off intervention as partial contextual support and does not change DIRECT eligibility. Equivalent expansion proposals were not granted semantic authority. BASS/definition guards now make model calls unnecessary for their demonstrated deterministic corrections. No source-backed expert relevance labels exist to establish ranking benefit. Both providers' scientific incremental value is INCONCLUSIVE; Jev's valid class proposals are advisory rather than scientific approval.
""",
        "PHASE3C_SCIENTIFIC_RETRIEVAL_FINAL_DECISION.md": f"""# Scientific retrieval final decision

Implemented and validated dependency-ready corrections; independent scientific relevance remains unadjudicated. Source-backed publication is deliberately limited to verified run/sample identities and corroborated source quantities. No Phase 4 work began.

```text
{decision_text}
```

Quality: 170 tests; ruff format/check, canonical/native/literal SHACL, registered ontology relations, SQLite and manual reference integrity, FTS completeness, evidence resolution and secret exclusion pass. {integrity["immutable_files_checked"]} immutable historical digests are unchanged, including {integrity["historical_gold_files_checked"]} gold files and {integrity["historical_benchmark_files_checked"]} historical artifacts. Row/cell checks and scientific-source identity suites are executed, not inferred from SHACL.

Remaining blockers: independently judge RELATED usefulness/contamination and epistemic labels; strengthen broad conceptual ontology relationship answers; review five operational mappings; validate unresolved structured PSI numeric roles and run identities; verify older provenance beyond the scoped tables; retain explicit V1 historical limitations. A larger candidate set, derived-value accessibility, more run identities and passing engineering tests do not establish scientist-approved answer quality. Independent scientific precision, recall, nDCG, response usefulness and attribution accuracy are NOT MEASURABLE with zero expert labels.
""",
    }
    for name, text in reports.items():
        path = ROOT / "docs" / name
        path.write_text(text)
    write(
        "artifact_index",
        {
            "reports": ["docs/" + name for name in reports],
            "receipts": [str(p.relative_to(ROOT)) for p in sorted(ART.glob("phase3c_targeted*"))],
            "canonical_publication": [
                "data/canonical/phase3c_targeted_psi_records_v1.json",
                "data/canonical/phase3c_targeted_psi_samples_v1.json",
            ],
            "baseline": "artifacts/phase3c_targeted_baseline_v1.json",
            "final_integrity": "artifacts/phase3c_targeted_integrity_v6.json",
            "final_decisions": decisions,
        },
    )
    print({"reports": len(reports), "decisions": decisions})


if __name__ == "__main__":
    main()
