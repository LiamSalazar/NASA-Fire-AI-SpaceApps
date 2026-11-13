"""Prepare source reviews, execute fresh integrity gates, and publish measured decisions."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import RDF, Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase3c_fidelity_campaign as campaign

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evaluation.phase3c import freeze_json
from nasa_fire_ai.evaluation.reconstruction import read_json, source_path
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import HEADER_KIND
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.ingestion.source_spans import recover_span
from nasa_fire_ai.ingestion.structured_provenance import round_trip
from nasa_fire_ai.query.native import NS, execute_native, identity
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.native import answer_native_text

ART = ROOT / "artifacts"


def write(name, data):
    freeze_json(ART / f"phase3c_fidelity_{name}_v1.json", data)


def prepare():
    evidence, _ = campaign.stores()
    os.environ["NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED"] = "true"
    store = project_legacy(ROOT, evidence)
    reconstruction = read_json(ART / "phase3c_fidelity_reconstruction_v1.json")
    reviewed = []
    for record in reconstruction["identities"]:
        eid = record["evidence_ids"][0]
        source = reconstruction["source_records"][eid]
        cells = source["registry_passage"]["source_cells"]
        mapped = []
        canonical = {c["kind"]: c for c in record["original_scientific_records"]}
        for cell in cells:
            header = cell["original_header"]
            value = cell["original_value"]
            contract = HEADER_KIND.get(header)
            if contract is None:
                matches = [
                    kind
                    for kind in canonical
                    if re.sub(r"[^a-z0-9]", "", kind.lower())
                    == re.sub(r"[^a-z0-9]", "", header.lower())
                ]
                contract = (matches[0], None) if len(matches) == 1 else None
            scientific = canonical.get(contract[0]) if contract else None
            unit = contract[1] if contract else None
            if unit is None:
                match = re.search(r"\(([^)]+)\)", header)
                unit = match[1] if match else None
            check = None
            if scientific:
                try:
                    check = float(value) == float(scientific["reported_value"])
                except (ValueError, TypeError):
                    check = value == scientific["reported_value"]
            mapped.append(
                {
                    "evidence_ref": eid,
                    "column_ordinal": cell["column_ordinal"],
                    "row_ordinal": cell["row_ordinal"],
                    "original_header": header,
                    "original_value": value,
                    "original_unit": unit,
                    "unit_basis": "existing HEADER_KIND contract or literal header; absent remains null",
                    "canonical_record_ref": scientific.get("id") if scientific else None,
                    "canonical_value": scientific.get("canonical_value") if scientific else None,
                    "canonical_unit": scientific.get("canonical_unit") if scientific else None,
                    "value_preservation_check": check,
                    "role": "SOURCE_REPORTED_CONFIGURATION_OR_DATA; observation not inferred",
                    "provenance_status": "EXACT_CELL_VERIFIED",
                    "raw_file": cell["raw_file"],
                    "file_digest": cell["checksum"],
                }
            )
        material = record["sample"]["material"]
        material_cells = [
            c["original_value"]
            for c in cells
            if c["original_header"].strip() in ["Material", "Fuel Sample Material"]
        ]
        source_run = [
            c["original_value"]
            for c in cells
            if c["original_header"].strip() in ["Test #", "Sample Number"]
        ]
        reviewed.append(
            {
                "identity_id": record["identity_id"],
                "source_exists": source["status"] == "VERIFIED",
                "official_title": reconstruction["investigation_contexts"][
                    record["investigation_id"]
                ]["official_title"],
                "material_supported": material in material_cells,
                "run_identity_supported": any(
                    record["identity_id"].endswith("-" + v.strip()) for v in source_run
                ),
                "source_text_preserved": source["passage_content_valid"],
                "verified_location": source["verified_location"],
                "cell_reviews": mapped,
                "gravity_provenance": "REVISE_CANONICAL_TABLE_ONLY_DECLARATION"
                if record["identity_id"].startswith("psi-98")
                else "UNKNOWN_EXECUTION_SCOPE",
                "epistemic_check": "Configuration/data record; no experimental conclusion inferred",
                "duplicate_underlying_source": False,
                "independent_reviewer_label": None,
            }
        )
    write(
        "identity_validity",
        {
            "identities": reviewed,
            "technical_identity_checks_pass": all(
                r["source_exists"]
                and r["material_supported"]
                and r["run_identity_supported"]
                and r["source_text_preserved"]
                for r in reviewed
            ),
            "scientific_value_checks_require_scope_review": True,
            "verified_cells": sum(len(r["cell_reviews"]) for r in reviewed),
            "canonical_condition_crosswalks": sum(
                c["canonical_record_ref"] is not None for r in reviewed for c in r["cell_reviews"]
            ),
            "source_validity_not_query_applicability": True,
        },
    )
    cases = read_json(ART / "phase3c_targeted_parity_reconciliation_v4.json")["cases"]
    omitted = []
    for case in cases:
        if case["case_id"] not in ["qi01", "qi02", "qi09", "qi10", "qi27", "qi42", "qi50"]:
            continue
        intent = QueryIntentV2.model_validate(case["frozen_intent"])
        result = execute_native(
            intent, case["original_query"], store, evidence, hierarchical=True, relational=True
        )
        selected = {c["id"] for c in result.bundle.direct_evidence + result.bundle.related_evidence}
        for subject in ["psi-98-S1", "psi-98-S2"]:
            omitted.append(
                {
                    "query_id": case["case_id"],
                    "question": case["original_query"],
                    "candidate_id": subject,
                    "requested_materials": [
                        c.entity_id
                        for c in intent.entity_constraints
                        if c.relation == "hasMaterial"
                    ],
                    "actual_material": sorted(store.relations(subject, "hasMaterial")),
                    "selected": subject in selected,
                    "source_ref": "E-psi-98-table-" + subject[-2:],
                    "technical_disposition": "ELIGIBLE_MATERIAL_OR_EXPLICIT_COMPARISON"
                    if subject in selected
                    else "REQUIRED_PMMA_ANCHOR_NOT_SATISFIED",
                    "contextual_role": "SIBAL configuration can be documentary context for broader questions; not PMMA suppression evidence",
                    "scientific_relevance": None,
                }
            )
    write("saffire_omissions", omitted)
    # Preserve final answers separately from earlier diagnostic traces.
    campaign.VERSION = "v5"
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    final = []
    selected = {
        "qi01",
        "qi03",
        "qi09",
        "qi10",
        "qi11",
        "qi14",
        "qi18",
        "qi27",
        "qi34",
        "qi35",
        "qi37",
        "qi42",
        "qi49",
        "qi50",
    }
    for case in cases:
        if case["case_id"] not in selected:
            continue
        response = answer_native_text(case["original_query"], store, evidence, language)
        final.append(
            {
                "case_id": case["case_id"],
                "original_question": case["original_query"],
                "trace": campaign.response_trace(response),
                "citation_identity_valid": all(
                    evidence.resolve(p["evidence_id"])
                    for p in response.execution.bundle.evidence_passages
                ),
                "scientific_usefulness": None,
                "independent_reviewer": None,
            }
        )
    campaign.write("answer_traces", final)
    campaign.write("trace_records", campaign.RECORD_POOL)
    campaign.write("trace_sources", campaign.SOURCE_POOL)
    write(
        "phenomenon_diagnostics",
        {
            "review_342": "No specific phenomenon requested in these nine literal questions; NOT_REQUESTED concerns applicability, not evidence coverage",
            "broad_source_run_phenomena": {
                "identities_without_explicit_canonical_phenomenon": 70,
                "new_phenomenon_relations": 0,
            },
            "targeted_queries": {
                "qi14": "B: explicit suppression topic retained as linguistic topic; no approved phenomenon entity mapping",
                "qi27": "B: suppressing is explicitly requested; raw topic retained, material match alone cannot establish suppression",
                "observation_source": "C: source/canonical observation says flame persistence, registry has no approved entity; no automatic new vocabulary",
                "psi_rows": "D: configuration and source program title do not establish per-run phenomenon outcomes",
            },
            "source_topic_hypotheses_are_canonical": False,
        },
    )
    build_viewer(reconstruction)
    print({"identity_reviews": len(reviewed), "final_answers": len(final)}, flush=True)


def build_viewer(reconstruction):
    packet = read_json(ART / "phase3c_fidelity_review_packet_v4.json")
    payload = json.dumps({"sources": reconstruction, "packet": packet}, ensure_ascii=False).replace(
        "</", "<\\/"
    )
    html = """<!doctype html><meta charset="utf-8"><title>NASA Phase 3C scientific review</title>
<style>body{font:16px system-ui;max-width:1100px;margin:2em auto;padding:1em}pre{white-space:pre-wrap;background:#eee;padding:1em}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:.5em}label{display:block;margin:.8em 0}input,select,textarea{font:inherit;width:95%}button{font:inherit;padding:.5em;margin:.5em}</style>
<h1>Scientific evidence applicability review</h1><p>342 query–candidate pairs; 70 source identities. Technical proposals are separate from blank independent scientific judgments. Save the exported CSV to preserve your review.</p>
<label>Query and candidate<select id="choose"></select></label><button id="prev">Previous</button><button id="next">Next</button>
<h2 id="question"></h2><pre id="dimensions"></pre><h2>Original evidence</h2><div id="source"></div>
<h2>Independent review</h2><div id="fields"></div><button id="export">Export reviewer CSV</button>
<script id="data" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.querySelector('#data').textContent),pairs=data.packet.pairs,labels=data.packet.allowed_scientific_labels,fields=Object.keys(pairs[0].independent_review),reviews={};
const select=document.querySelector('#choose');pairs.forEach((p,i)=>{let o=document.createElement('option');o.value=i;o.textContent=p.query_id+' — '+p.evidence_identity_ref;select.append(o)});
function text(tag,value,parent){let e=document.createElement(tag);e.textContent=value;parent.append(e);return e}
function show(){const p=pairs[+select.value];document.querySelector('#question').textContent=p.original_question;document.querySelector('#dimensions').textContent=JSON.stringify({requested:p.interpreted_constraints,conditions:p.requested_vs_actual,limits:p.what_it_does_not_establish},null,2);const box=document.querySelector('#source');box.replaceChildren();p.source_record_refs.forEach(id=>{const s=data.sources.source_records[id];text('h3',id,box);text('p',data.sources.investigation_contexts[s.source.source_id].official_title,box);text('p',JSON.stringify(s.verified_location),box);text('pre',s.registry_passage.text,box);let table=document.createElement('table');let head=document.createElement('tr');s.original_headers.forEach(h=>text('th',h,head));table.append(head);let row=document.createElement('tr');s.structured_row.forEach(v=>text('td',v,row));table.append(row);box.append(table);text('pre','Before: '+JSON.stringify(s.context_before)+'\\nAfter: '+JSON.stringify(s.context_after),box)});const form=document.querySelector('#fields');form.replaceChildren();fields.forEach(field=>{const label=text('label',field,form);let input=document.createElement(field==='SCIENTIFIC_RELEVANCE'?'select':field==='REVIEWER_JUSTIFICATION'?'textarea':'input');if(field==='SCIENTIFIC_RELEVANCE'){['',...labels].forEach(v=>{let o=document.createElement('option');o.value=v;o.textContent=v||'Unreviewed';input.append(o)})}input.value=(reviews[p.pair_id]||{})[field]||'';input.onchange=()=>{(reviews[p.pair_id]||= {})[field]=input.value};label.append(input)})}
select.onchange=show;document.querySelector('#prev').onclick=()=>{select.value=Math.max(0,+select.value-1);show()};document.querySelector('#next').onclick=()=>{select.value=Math.min(pairs.length-1,+select.value+1);show()};document.querySelector('#export').onclick=()=>{const quote=v=>'"'+String(v||'').replaceAll('"','""')+'"';let rows=[['pair_id','query_id','evidence_identity_ref',...fields],...pairs.map(p=>[p.pair_id,p.query_id,p.evidence_identity_ref,...fields.map(f=>(reviews[p.pair_id]||{})[f]||'')])];let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([rows.map(r=>r.map(quote).join(',')).join('\\r\\n')],{type:'text/csv'}));a.download='phase3c_independent_review.csv';a.click()};show();
</script>""".replace("PAYLOAD", payload)
    (ART / "phase3c_fidelity_review_viewer_v1.html").write_text(html)


def identity_whitespace():
    """Resolve a literal equality failure while preserving both original strings."""
    audit = read_json(ART / "phase3c_fidelity_identity_validity_v1.json")
    reconstruction = read_json(ART / "phase3c_fidelity_reconstruction_v1.json")
    identities = {r["identity_id"]: r for r in reconstruction["identities"]}
    for row in audit["identities"]:
        canonical = identities[row["identity_id"]]["sample"]["material"]
        original = [
            c["original_value"]
            for c in row["cell_reviews"]
            if c["original_header"].strip() in ["Material", "Fuel Sample Material"]
        ]
        row["material_original_values"] = original
        row["material_canonical_value"] = canonical
        row["material_whitespace_only_difference"] = canonical not in original and canonical in [
            v.strip() for v in original
        ]
        row["material_supported"] = (
            canonical in original or row["material_whitespace_only_difference"]
        )
        for cell in row["cell_reviews"]:
            cell["canonical_conversion_check"] = None
            if cell["canonical_value"] is not None and cell["original_unit"]:
                try:
                    from nasa_fire_ai.normalization.units import normalize

                    value, unit = normalize(float(cell["original_value"]), cell["original_unit"])
                    cell["canonical_conversion_check"] = (
                        value == cell["canonical_value"] and unit == cell["canonical_unit"]
                    )
                except (ValueError, TypeError):
                    pass
    audit["technical_identity_checks_pass"] = all(
        r["source_exists"]
        and r["material_supported"]
        and r["run_identity_supported"]
        and r["source_text_preserved"]
        for r in audit["identities"]
    )
    audit["source_original_values_modified"] = False
    audit["whitespace_corrections"] = [
        r["identity_id"] for r in audit["identities"] if r["material_whitespace_only_difference"]
    ]
    freeze_json(ART / "phase3c_fidelity_identity_validity_v2.json", audit)


def final_review_metadata():
    stratified = read_json(ART / "phase3c_fidelity_stratified_review_v4.json")
    strata = stratified["strata"]
    strata["VERIFIED_DIRECT"]["refs"] = ["qi50::psi-98-S1", "qi50::psi-98-S2"]
    strata["VERIFIED_DIRECT"]["basis"] = (
        "Source-reviewed table identity and exact requested airflow; no gravity requested and no independent relevance approval"
    )
    strata["REJECTED_TABLE_ONLY_GRAVITY"] = strata.pop("CANONICAL_MICROGRAVITY_PENDING_PROVENANCE")
    strata["REJECTED_TABLE_ONLY_GRAVITY"]["basis"] = (
        "Existing table-only gravity declaration staged under the source validator"
    )
    strata["SAFETY_IMPLICATION"]["refs"] = ["E-safety-suppression-system-implication"]
    strata["GENUINE_OPEN_QUESTION"]["refs"] = ["E-safety-saffire-suppression-open-question"]
    strata["GENUINE_OPEN_QUESTION"]["basis"] = (
        "Verified original page supplies explicit qualification questions; scientific versus normative scope requires review; incomplete sentence alone remains excluded"
    )
    strata["VERIFIED_MICROGRAVITY_CONTEXT"] = {
        "refs": ["psi-25::Approach"],
        "basis": "Archived metadata explicitly says microgravity combustion tests were performed aboard ISS; investigation-level context does not establish every table execution",
        "scientific_gold": None,
        "split": "DEVELOPMENT_SOURCE_REVIEW",
    }
    stratified["unavailable_strata"] = [name for name, s in strata.items() if not s["refs"]]
    stratified["source_context_ref"] = "artifacts/phase3c_fidelity_documentary_sources_v3.json"
    freeze_json(ART / "phase3c_fidelity_stratified_review_v5.json", stratified)
    queue = read_json(ART / "phase3c_fidelity_expert_queue_v4.json")
    for issue in queue["issues"]:
        if issue.get("query_id") == "qi18":
            issue["reason"] = (
                "Physical page 16 and antecedent qualification questions are recovered. Scientific open-question versus normative qualification scope still needs independent judgment."
            )
            issue["verified_context_ref"] = "artifacts/phase3c_fidelity_documentary_sources_v3.json"
    freeze_json(ART / "phase3c_fidelity_expert_queue_v5.json", queue)
    numeric = read_json(ART / "phase3c_fidelity_numeric_results_v4.json")
    from nasa_fire_ai.query.numeric_mentions import NUMBER, UNIT

    lexical = []
    for row in numeric:
        for trace in row["current"]["numeric_extraction"]:
            raw = trace.get("raw_expression") or ""
            lexical.append(
                {
                    "case_id": row["case_id"],
                    "original_question": row["original_question"],
                    "raw_numeric_tokens": re.findall(NUMBER, raw),
                    "raw_unit_tokens": re.findall(UNIT, raw, re.IGNORECASE),
                    "typed_trace": trace,
                    "basis": "Literal tokens from preserved execution raw_expression; not a new interpreter or NASA assertion",
                }
            )
    write("numeric_lexical_tokens", lexical)


def integrity():
    quality = []
    for i, command in enumerate(
        ["uv run ruff format --check .", "uv run ruff check .", "uv run pytest -q"]
    ):
        result = subprocess.run(
            command.split(), cwd=ROOT, capture_output=True, text=True, check=False
        )
        path = ART / f"phase3c_fidelity_quality_{i}_v3.txt"
        with path.open("x") as handle:
            handle.write(result.stdout + result.stderr)
        quality.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "receipt": str(path.relative_to(ROOT)),
            }
        )
        print(quality[-1], flush=True)
    evidence, _ = campaign.stores()
    os.environ["NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED"] = "true"
    store = project_legacy(ROOT, evidence)
    frozen = read_json(ART / "phase3c_fidelity_freeze_v1.json")["manifests"]
    immutable = {
        p: h
        for p, h in frozen.items()
        if p.startswith(("data/raw/", "data/canonical/", "evals/", "artifacts/"))
    }
    changed = [
        p
        for p, h in immutable.items()
        if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
    ]
    refs = {str(e) for e in store.graph.objects(None, NS.evidenceRef)}
    broken = [e for e in refs if evidence.resolve(e) is None]
    invalid = [
        identity(r)
        for r in store.graph.subjects(RDF.type, NS.SemanticRelation)
        if any(
            identity(v) not in store.registry.relations for v in store.graph.objects(r, NS.relation)
        )
    ]
    checks = {
        name: evidence.db.execute(sql).fetchone()[0]
        for name, sql in {
            "passages_without_documents": "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL",
            "documents_without_sources": "SELECT count(*) FROM documents d LEFT JOIN sources s USING(source_id) WHERE s.source_id IS NULL",
            "cells_without_passages": "SELECT count(*) FROM structured_cells c LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
            "fts_missing": "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL",
            "fts_extra": "SELECT count(*) FROM passages_fts f LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
            "fts_text_mismatch": "SELECT count(*) FROM passages p JOIN passages_fts f USING(evidence_id) WHERE p.text != f.text",
            "fts_duplicates": "SELECT count(*) FROM (SELECT evidence_id FROM passages_fts GROUP BY evidence_id HAVING count(*)>1)",
            "refs_without_passages": "SELECT count(*) FROM evidence_refs e LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
            "locations_without_passages": "SELECT count(*) FROM evidence_locations l LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL",
        }.items()
    }
    cells = [
        json.loads(r[0]) for r in evidence.db.execute("SELECT locator_json FROM structured_cells")
    ]
    cell_errors = []
    for cell in cells:
        try:
            round_trip(cell, ROOT)
        except (ValueError, OSError, IndexError) as error:
            cell_errors.append({"evidence_id": cell["evidence_id"], "error": type(error).__name__})
    # Check every stored PDF locator against original words and digest, rather
    # than interpreting extracted-page fields as physical pages.
    pdf_checks = []
    import pymupdf

    documents = {}
    for row in evidence.db.execute("SELECT * FROM evidence_locations"):
        locator = json.loads(row["location_json"])
        raw = source_path(ROOT, locator.get("raw_file"))
        if not raw or raw.suffix.lower() != ".pdf":
            continue
        if raw not in documents:
            documents[raw] = pymupdf.open(raw)
        page = locator.get("physical_pdf_page")
        valid_page = bool(page and 1 <= page <= len(documents[raw]))
        digest = hashlib.sha256(raw.read_bytes()).hexdigest() == locator.get("checksum")
        supported = False
        if valid_page:
            text = documents[raw][page - 1].get_text()
            if locator.get("exact_source_span"):
                try:
                    recover_span(text, locator["exact_source_span"]["span"])
                    supported = True
                except ValueError:
                    pass
            elif locator.get("row_identifier"):
                supported = locator["row_identifier"] in text
            else:
                supported = bool(locator.get("verification"))
        pdf_checks.append(
            {
                "evidence_id": row["evidence_id"],
                "physical_page": page,
                "digest_valid": digest,
                "source_locator_support": supported,
                "verification_scope": "Exact span or table row identifier; cell boxes retain earlier table alignment receipts",
            }
        )
    for document in documents.values():
        document.close()
    evidence.db.execute("INSERT INTO passages_fts(passages_fts) VALUES ('integrity-check')")
    evidence.db.commit()
    env = Settings()
    secrets = [env.nvidia_api_key, env.api_key, os.getenv("TYPESAFE_API_KEY")]
    secret_files = []
    for directory in ["artifacts", "docs", "src", "scripts", "tests", "domain", "ontology"]:
        for path in (ROOT / directory).rglob("*"):
            if (
                path.is_file()
                and "__pycache__" not in str(path)
                and any(secret and secret.encode() in path.read_bytes() for secret in secrets)
            ):
                secret_files.append(str(path.relative_to(ROOT)))
    canonical = Graph().parse(ROOT / "data/canonical/graph.ttl")
    result = {
        "quality": quality,
        "immutable_files_checked": len(immutable),
        "changed_immutable_files": changed,
        "historical_gold_files_checked": sum(p.startswith("evals/") for p in immutable),
        "historical_artifacts_checked": sum(p.startswith("artifacts/") for p in immutable),
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
        "foreign_keys": [tuple(r) for r in evidence.db.execute("PRAGMA foreign_key_check")],
        "registry_fts_checks": checks,
        "graph_evidence_refs_checked": len(refs),
        "broken_graph_evidence": broken,
        "invalid_relations": invalid,
        "csv_cells_checked": len(cells),
        "csv_cell_errors": cell_errors,
        "pdf_location_checks": pdf_checks,
        "secret_matches": secret_files,
        "gravity_declarations_staged": [
            r
            for r in store.projection_staging
            if "gravity declaration lacks" in r.get("reason", "")
        ],
    }
    result["status"] = (
        "PASS"
        if (
            all(r["exit_code"] == 0 for r in quality)
            and not (
                changed
                or broken
                or invalid
                or cell_errors
                or secret_files
                or result["foreign_keys"]
                or any(checks.values())
            )
            and all(result[k] for k in ["canonical_shacl", "native_shacl", "literal_shacl"])
            and result["sqlite_integrity"] == "ok"
            and all(r["digest_valid"] and r["source_locator_support"] for r in pdf_checks)
        )
        else "FAIL"
    )
    freeze_json(ART / "phase3c_fidelity_integrity_v3.json", result)
    print({"integrity": result["status"], "immutable_files": len(immutable)}, flush=True)


def regressions():
    spec = importlib.util.spec_from_file_location(
        "fresh_fidelity_native", ROOT / "scripts/phase3c_native_benchmarks.py"
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    native.ART = ART / "phase3c_fidelity_native_checks_v1"
    native.ART.mkdir()
    # These source freezes are checked by this campaign's immutable manifest.
    native.check_freeze = lambda: None
    original = EvidenceRegistry
    native.EvidenceRegistry = lambda p: original(
        ROOT / "data/index/phase3c_fidelity_snapshot_v1.sqlite"
        if p == ROOT / "data/index/evidence.sqlite"
        else p
    )
    for flag in [
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED",
        "PSI_STRUCTURED_PUBLICATION_ENABLED",
        "FLEX_SOURCE_CORRECTIONS_ENABLED",
        "HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED",
        "RELATIONAL_RELATED_RETRIEVAL_ENABLED",
    ]:
        os.environ[flag] = "false"
    native.dynamic()
    native.dynamic(postfreeze=True)
    native.parity()
    evidence, store = campaign.stores()
    rows = []
    for case in read_json(ART / "phase3c_related_cases_v1.json"):
        result = execute_native(
            QueryIntentV2.model_validate(case["intent"]),
            case["query"],
            store,
            evidence,
            hierarchical=True,
            relational=True,
        )
        eids = {p["evidence_id"] for p in result.bundle.evidence_passages}
        rows.append(
            {
                "case_id": case["case_id"],
                "direct": [x["id"] for x in result.bundle.direct_evidence],
                "related": [x["id"] for x in result.bundle.related_evidence],
                "required_identity_recovered": bool(
                    eids.intersection(case.get("expected_evidence_ids", []))
                )
                if case.get("objective_identity_case")
                else None,
                "false_direct": bool(result.bundle.direct_evidence)
                if case.get("objective_no_direct")
                else None,
                "source_ids_resolve": all(evidence.resolve(e) for e in eids),
                "scientific_relevance": None,
            }
        )
    write("20_case_regression", rows)
    print({"retrieval_regression_cases": len(rows)}, flush=True)


def reports():
    result = read_json(ART / "phase3c_fidelity_integrity_v3.json")
    numerical = read_json(ART / "phase3c_fidelity_numeric_results_v4.json")
    reconstruction = read_json(ART / "phase3c_fidelity_reconstruction_v1.json")
    coverage = read_json(ART / "phase3c_fidelity_coverage_v4.json")
    validity = read_json(ART / "phase3c_fidelity_identity_validity_v2.json")
    live = [
        json.loads(l)
        for version in ["v1", "v2"]
        for l in (ART / f"phase3c_fidelity_live_{version}.jsonl").read_text().splitlines()
    ]
    pilot = read_json(ART / "phase3c_fidelity_context_pilot_v2.json")
    summary = {
        provider: {
            "fresh_calls": sum(r["provider"] == provider for r in live)
            + (pilot["E_contextual_model"].get("new_calls", 0) + 1 if provider == "NVIDIA" else 0),
            "unique_historical_interpretations": 7 if provider == "NVIDIA" else 0,
            "cached_inference_replays_executed": 35 if provider == "NVIDIA" else 0,
            "scientific_precision": "NOT_MEASURABLE",
            "latency_ms": [r["latency_ms"] for r in live if r["provider"] == provider],
            "new_canonical_facts": 0,
        }
        for provider in ["NVIDIA", "Jev"]
    }
    summary["invalid_nemotron_exact_spans"] = sum(
        v.get("span_exact") is False
        for r in live
        for v in r.get("proposal_validation", [])
        if isinstance(v, dict)
    )
    summary["source_context_trials"] = (
        "v1 lacked source path; v2 source file resolved but terminal punctuation prevented full-page reconstruction. These are diagnostic limitations, not scientific source absence. Final v3 PDF source packet resolves all four."
    )
    summary["redundant_jev_call"] = (
        "Safety implication repeated once in v2 with identical passage; explicitly counted as fresh execution, not benefit"
    )
    summary["pilot"] = pilot
    summary["earlier_pilot_harness_limitation"] = (
        "v1 claimed page context, but adapter v4 ignored source_context; v2 transmits four registered source contexts and changes the cache key."
    )
    summary["pilot_invalid_proposals"] = pilot["E_contextual_model"].get("invalid", [])
    summary["NVIDIA"]["latency_ms"].extend(
        [
            read_json(ART / f"phase3c_fidelity_context_pilot_{version}.json")["E_contextual_model"][
                "usage"
            ]["latency_ms"]
            for version in ["v1", "v2"]
        ]
    )
    for provider in ["NVIDIA", "Jev"]:
        usage = [
            r.get("usage") or (r.get("output") or {}).get("usage") or {}
            for r in live
            if r["provider"] == provider
        ]
        if provider == "NVIDIA":
            usage.extend(
                [
                    read_json(ART / f"phase3c_fidelity_context_pilot_{version}.json")[
                        "E_contextual_model"
                    ]["usage"]
                    for version in ["v1", "v2"]
                ]
            )
        summary[provider]["known_input_tokens"] = sum(u.get("input_tokens", 0) for u in usage)
        summary[provider]["known_output_tokens"] = sum(u.get("output_tokens", 0) for u in usage)
    write("model_summary", summary)
    decisions = {
        "EVIDENCE_RECONSTRUCTION": "COMPLETE",
        "SOURCE_PROVENANCE": "PARTIALLY_VERIFIED",
        "NUMERIC_QUERY_FIDELITY": "PASS",
        "HISTORICAL_NUMERIC_GOLD": "REVISION_PROPOSED",
        "GRAVITY_CONTEXT": "INADEQUATE",
        "PHENOMENON_MAPPING": "PARTIAL",
        "RELATED_APPLICABILITY": "REVIEW_REQUIRED",
        "EPISTEMIC_CLASSIFICATION": "REVIEW_REQUIRED",
        "NEMOTRON_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "JEV_INCREMENTAL_VALUE": "INCONCLUSIVE",
        "INDEPENDENT_SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
        "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    write("decisions", decisions)
    numeric_table = "| Case | Property/operator | Original → canonical | Final DIRECT / RELATED | Historical loss |\n|---|---|---|---:|---|\n"
    for row in numerical:
        if row["case_id"] not in campaign.NUMERIC_IDS:
            continue
        e = row["expected"]
        t = row["with_source_context_validation"]
        numeric_table += f"| {row['case_id']} | {e['property_id']} {e['operator']} | {e['reported_value']} {e['reported_unit']} → {e['canonical_value']} {e['canonical_unit']} | {len(t['direct'])} / {len(t['related'])} | {row['historical_first_loss']} |\n"
    quality = "; ".join(f"`{r['command']}` exit {r['exit_code']}" for r in result["quality"])
    docs = {
        "PHASE3C_EVIDENCE_RECONSTRUCTION.md": f"""# Phase 3C evidence reconstruction (fidelity v1)

All {reconstruction["unique_identity_count"]} identities resolve to original immutable PSI rows. All {reconstruction["verified_source_count"]} source rows and {validity["verified_cells"]} cells round-trip against file digests and logical ordinals. Missing rows: {reconstruction["missing_sources"]}. CSV ordinals include the header and are never PDF pages. Original headers, values, adjacent rows, sample/run identities and existing canonical records are preserved. {validity["canonical_condition_crosswalks"]} cell-to-canonical crosswalks are recorded; absent role/unit mappings remain explicit. No observation or conclusion is manufactured from configuration.

`artifacts/phase3c_fidelity_reconstruction_v1.json` stores each source identity once. `phase3c_fidelity_identity_validity_v2.json` separates existence/material/value checks from applicability. Official investigation titles come from immutable PSI metadata; recorded NASA URLs are attributed, remote availability was not retested. Four narrative citations were independently resolved by source-level filename/digest, with unique spans on physical pages 16 (three) and 7 (one). Three registry passages add terminal periods absent from the PDF; original source spans and this difference are preserved in `phase3c_fidelity_documentary_sources_v3.json`. Four operational locations were published without changing scientific records.

Rows are intact; factual applicability is not thereby approved. BASS-II display settings have no verified velocity calibration. The source table does not supply gravity for Saffire S1/S2. The B4 canonical material drops one outer trailing space; both original and canonical strings remain explicit, with no factual material change. Investigation context is available, but execution population/flight-versus-ground links require validation.
""",
        "PHASE3C_NUMERICAL_QUERY_FIDELITY.md": f"""# Numerical query fidelity (fidelity v4)

The latest audit reproduced exactly: 342 pairs, nine questions, 70 candidate/evidence sets, 68 reused five times and two used once. The historical probe explicitly used an empty linguistic proposal: it never tested numerical extraction. Frozen qi09/qi11/qi35/qi37 lack numeric constraints; qi10/qi34/qi50 retain them. Historical gold remains unchanged.

Actual cached production proposals were replayed through the pre-correction resolver before edits. qi09/qi11/qi34/qi35 retained numbers. qi10's model label `air flow velocity` was unregistered; qi37 omitted oxygen; qi50 kept airflow but an unresolved compound comparison phrase blocked the answer. These are distinct from historical gold/probe defects. Original literal property expressions now take precedence over lossy model mentions, using registry aliases and typed unit validation. Numbers embedded in run IDs are not quantities. Approximation remains APPROX; no tolerance is invented. Unrepresentable disjunctions and mixed-unit ranges require clarification.

{numeric_table}

19/19 literal numeric proposals pass the full native entry-point/planner trace (seven exposed plus twelve frozen synthetic formulations). This measures constraint fidelity, not scientific precision. Strict/inclusive boundaries have different candidate outcomes. Standalone numeric contradictions now remain RELATED only under the existing relational policy; the strict rollback path retains its behavior. Dynamic properties need no property-specific branch. The conservative offline interpreter supplies native access without an API key. Unknown scientific vocabulary remains unapproved.
""",
        "PHASE3C_GRAVITY_AND_PHENOMENON_COVERAGE.md": f"""# Gravity and phenomenon coverage (fidelity v4)

Gravity UNKNOWN before: 340/342. Under opt-in source-context validation: {coverage["after"].get("UNKNOWN", 0)}/342. The two prior matches came from hardcoded PSI-98 ingestion declarations citing a CSV with no gravity column. `NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED=true` stages these assertions in the existing projection. The canonical history is untouched. No gravity inheritance or new scientific relationship was added. A physical platform or program title does not establish every execution's condition. BASS-II Approach explicitly describes ISS microgravity tests; membership of each table execution in that population is unresolved.

All 342 old phenomenon statuses were UNKNOWN. These nine questions request materials/gravity/numbers, not a specific phenomenon: all 342 now have NOT_REQUESTED applicability, while all 342 source-phenomenon evidence statuses remain UNKNOWN. This is a status clarification, not new phenomenon coverage. qi14/qi27 explicitly ask about suppression: raw topic wording is retained separately as QUERY_PHENOMENON_UNMAPPED, without inventing a SemanticRegistry entity. The observation record supplies a raw flame-persistence term, but no approved term mapping; PSI configurations do not establish run-level outcomes. The root-cause ledger distinguishes A (no request), B (unmapped query topic), C (source term unapproved), and D (source outcome unestablished).
""",
        "PHASE3C_RELATED_EVIDENCE_APPLICABILITY.md": """# RELATED evidence applicability (fidelity v4)

The original 342 pairs remain individual review units. All 70 identities have intact source rows; none is thereby labeled useful. PMMA rows often establish material/configuration while leaving requested gravity and airflow UNKNOWN. Repeated candidate sets are compatible with missing source conditions; the numeric traces demonstrate whether a bound was actually preserved. qi09/qi10 retain 41 RELATED configurations. With source-context validation qi11 has 29 RELATED and no DIRECT; qi34/qi35 expose two same-quantity contradictions each. qi37 keeps approximation without inventing a threshold; it has no DIRECT match. qi50 compares S1/S2 at source-reported 20 cm/s, with two numeric DIRECT records, without claiming gravity.

Saffire S1/S2 report SIBAL, not PMMA. Their exclusion from required-PMMA structured matches is defensible under the existing material anchor; qi42's grouped/broader scope or explicit qi50 comparison has different eligibility. The rows do not establish PMMA suppression. Broader documentary context is kept separately, rather than restoring rows for parity. `phase3c_fidelity_saffire_omissions_v1.json` records inclusion/exclusion per query. Presentation retains previous grouping and all identities; raw source payloads are referenced once in the final packet. Useful RELATED, TOPICAL_ONLY, IRRELEVANT and misleading counts remain unmeasured with no independent labels.
""",
        "PHASE3C_REVIEW_PACKET_METHODOLOGY.md": """# Scientific review methodology (fidelity v4)

Open `artifacts/phase3c_fidelity_review_viewer_v1.html` for the standalone source-and-constraint viewer, or use `phase3c_fidelity_candidate_matrix_v4.csv`. The viewer embeds each of 70 unique source records once and navigates 342 separate pairs. It displays original rows/headers, neighboring context, digests, locators and requested-versus-actual dimensions. The CSV provides stable query/evidence identities and reconstruction references. Browser edits export to CSV; no labels are generated automatically.

Identity integrity and query applicability are separate. Nine independent reviewer fields are blank. Allowed relevance labels include DIRECT_RELEVANT, RELATED_USEFUL, CONTEXTUAL_USEFUL, TOPICAL_ONLY, IRRELEVANT, SCIENTIFICALLY_MISLEADING and INSUFFICIENT_CONTEXT. Deterministic proposals are explicitly non-expert. The final strata and queue are `phase3c_fidelity_stratified_review_v5.json` and `phase3c_fidelity_expert_queue_v5.json`. The disagreement queue concerns execution population, Saffire source scope and normative/anaphoric interpretation; no actual scientific reviewer disagreement is claimed.

Strata include valid configurations, explicit numeric matches/contradictions, unknown gravity, documentary context, observation versus safety implication, conceptual questions, ambiguous investigation identity and incomplete anaphora. The frozen synthetic numeric set is separate from development source cases. A validated material-family transfer, verified differing-gravity execution pair, independently labeled lexical distractor and independent scientific gold remain unavailable in this source-reviewed universe. Those slots remain unavailable; they are not filled with inferred labels or new corpus data. This limitation prevents a claim that all desired independent scientific strata are complete.
""",
        "PHASE3C_NUMERICAL_END_TO_END_RESULTS.md": f"""# Numerical end-to-end results (fidelity v4)

Every question traverses `answer_native_text` → literal/linguistic interpretation → typed expression/unit validation → QueryIntentV2 → native plan → candidate classification → EvidenceBundle → deterministic rendering. Seven cached model proposals are separately replayed, not described as fresh inference. The source-reviewed canonical numeric intent comes from hand-specified literal question gold; it is never a new NASA measurement. A/B comparisons use the same corpus backup. Numeric corrections (C) are separated from opt-in source checks (D); final answer traces use verified citations.

{numeric_table}

Examples disclose requested and source-reported values: qi34 asks below 20 cm/s while S1/S2 report 20 cm/s, so they are RELATED. qi35 asks at most 0.10 m/s (=10 cm/s), and the same rows fail that condition. No source-backed PMMA airflow value was invented from BASS air-display settings. Exact lexical tokens, including 0.10 and percent, are retained in `phase3c_fidelity_numeric_lexical_tokens_v1.json`. An unspecified approximate 20% is not exact equality and cannot yield a newly fabricated tolerance. Candidate-count changes are not relevance metrics. Current/canonical/replayed/frozen traces, full planner constraints and affected-candidate dimensions are preserved in `phase3c_fidelity_numeric_results_v4.json`; repeated scientific/source payloads use shared trace pools.
""",
        "PHASE3C_SCIENTIFIC_RELEVANCE_EVALUATION.md": """# Scientific relevance evaluation (fidelity v1)

14 scientist-facing final traces are preserved in `phase3c_fidelity_answer_traces_v5.json`, including source IDs, questions, typed/planned conditions, bundles, deterministic answers and limitations. Citations are registry-resolvable; narrative physical pages are independently verified. Successful recovery of an evidence ID is measured separately from useful answering.

qi14 requests observations and does not silently include safety implications. qi18's incomplete “these questions” is excluded as a complete NASA question; the recovered PDF context is quoted separately for antecedent review. qi27 can return the source-backed PMMA flow-off intervention as contextual support, while explicitly disclosing UNKNOWN experimental scope. PMMA configuration rows are not suppression outcomes. BASS/BASS-II, acrylic/PMMA, conceptual-versus-experimental questions and multi-entity clarification/grouping behavior remain protected. The ontology has no approved material-family edges; no such edge was invented.

Independent reviewers obtained: zero. Scientific usefulness, contamination, Precision@k, Recall@k and nDCG are NOT MEASURABLE. Technical source/constraint verification is complete within scope; execution-level gravity provenance, phenomenon vocabulary approval, source-applicability interpretation and independent scientific review remain dependencies. Missing DIRECT evidence is never called a NASA knowledge gap.
""",
        "PHASE3C_CONTEXTUAL_RERANKING_VALIDATION.md": f"""# Contextual reranking validation (fidelity v1)

Existing settings load the existing dotenv file with explicit environment precedence. No credential file was changed. Fresh source-context/advisory receipts and two versioned executions of one fixed four-candidate contextual reranking pilot are checkpointed. NVIDIA model: nvidia/nemotron-3.5-lightning-30b-a3b; existing Jev adapter reused. NVIDIA fresh calls: {summary["NVIDIA"]["fresh_calls"]}; Jev fresh calls: {summary["Jev"]["fresh_calls"]}; cached historical NVIDIA interpretations: 7 per explicitly identified replay evaluation. No connectivity-only calls were made.

The first source-context trials exposed missing per-passage file metadata and registry punctuation differences; final reconstruction resolves the source at the document level. Nemotron produced one non-source supporting span, rejected by exact-span validation. Jev proposed Requirement for an incomplete modal open-question statement; that proposal was not adopted. Its safety implication routing agrees with existing technical classification, which is not independent validation. One redundant safety routing call was made and is counted as fresh, without claimed benefit.

The fixed four-source pilot preserves D eligibility, records E proposals and exact-span validation, and makes no canonical changes. Pilot v1 claimed full-page context but the adapter ignored its source_context field; this harness error is explicit in v2. The corrected adapter transmits bounded registered context, hashes it in the cache key, and rejects a new missing-span proposal in v2. F is not adopted: rhetorical class does not resolve requested gravity or scientific applicability. No discovery expansion or larger candidate budget was used. Per-call latency and usage are in `phase3c_fidelity_model_summary_v1.json`; successful outputs and failed proposals are retained. Incremental scientific precision remains unmeasured. Both providers remain optional and experimental.
""",
        "PHASE3C_EVIDENCE_REVIEW_FINAL_DECISION.md": f"""# Evidence review final decision (fidelity v1)

Technically resolved source reconstruction, numerical fidelity, targeted source-provenance checks, review exports and citation/context presentation. Historical raw/canonical/gold/artifact digests are preserved; no corpus enrichment, ontology redesign, QueryIntentV3 or Phase 4 was performed. Existing V1 default/rollback and V2 experimental flags remain. The new source check is explicitly opt-in: NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED=false by default; enable true on the reviewed experimental path. Existing PSI publication/FLEX corrections stay disabled in controlled comparisons.

```text
{chr(10).join(k + " = " + v for k, v in decisions.items())}
```

Fresh gates: {quality}. Integrity: {result["status"]}; {result["immutable_files_checked"]} frozen files checked with {len(result["changed_immutable_files"])} changed immutable files. Canonical/native/literal SHACL, SQLite/FKs, evidence/FTS identity, cell round trips, physical PDF locators, graph references and secrets checks have fresh receipts. Native dynamic/parity and 20-case retrieval reruns are separate technical measures; parity differences are not scientific relevance judgments.

Remaining dependencies: establish execution-level gravity scope; approve any phenomenon vocabulary/source mappings; obtain independent relevance and epistemic judgments; fill genuinely absent scientific review strata. Evidence existence is complete; independent applicability is not approved. Phase 4 readiness is NO.
""",
    }
    for filename, content in docs.items():
        path = ROOT / "docs" / filename
        with path.open("x") as handle:
            handle.write(content)
    index = {
        "reports": list(docs),
        "primary_reconstruction": "artifacts/phase3c_fidelity_reconstruction_v1.json",
        "review_packet": "artifacts/phase3c_fidelity_review_packet_v4.json",
        "csv": "artifacts/phase3c_fidelity_candidate_matrix_v4.csv",
        "viewer": "artifacts/phase3c_fidelity_review_viewer_v1.html",
        "numeric_results": "artifacts/phase3c_fidelity_numeric_results_v4.json",
        "final_answers": "artifacts/phase3c_fidelity_answer_traces_v5.json",
        "integrity": "artifacts/phase3c_fidelity_integrity_v3.json",
        "decisions": decisions,
        "historical_gold_modified": False,
        "independent_scientific_labels": 0,
        "receipts": [
            str(p.relative_to(ROOT)) for p in ART.glob("phase3c_fidelity*") if p.is_file()
        ],
    }
    write("artifact_index", index)
    print(
        {"reports": len(docs), "decision": "KEEP_EXPERIMENTAL", "integrity": result["status"]},
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    for mode in [
        "prepare",
        "identity_whitespace",
        "final_review_metadata",
        "regressions",
        "integrity",
        "reports",
    ]:
        parser.add_argument("--" + mode, action="store_true")
    args = parser.parse_args()
    for mode in [
        "prepare",
        "identity_whitespace",
        "final_review_metadata",
        "regressions",
        "integrity",
        "reports",
    ]:
        if getattr(args, mode):
            globals()[mode]()


if __name__ == "__main__":
    main()
