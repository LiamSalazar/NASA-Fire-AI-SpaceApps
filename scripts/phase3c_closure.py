"""Versioned closure receipts and sanitized reproducibility export."""

import argparse
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def freeze(directory):
    directory.mkdir(parents=True, exist_ok=False)
    files = []
    for folder in ("src", "domain", "ontology", "data/raw", "data/canonical", "evals", "tests"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                files.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                    }
                )
    for name in ("uv.lock", "pyproject.toml", ".gitignore", "README.md"):
        path = ROOT / name
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    write(
        directory / "baseline.json",
        {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "files": files,
            "historical_metrics": "REPORTED_NOT_REPRODUCED",
        },
    )


QUESTIONS = [
    "Does acrylic mean PMMA?",
    "Which NASA publications investigate depressurization for spacecraft fire suppression?",
    "Which experiments support NASA's conclusions about depressurization-based suppression, and under what conditions were the observations made?",
    "What did NASA observe about PMMA combustion?",
    "What did NASA observe about PMMA combustion under microgravity?",
    "Which conditions applied to Saffire-I S1 and S2?",
    "What happened when airflow was interrupted and subsequently restored?",
    "What observations support the authors' conclusions about the limitations of depressurization as a fire suppression technique?",
    "What unresolved research questions does NASA identify about spacecraft fire safety?",
    "Which NASA publications investigate seawater corrosion of aluminum?",
    "What was observed after oxygen was reintroduced following extinguishment?",
    "Which PMMA observations describe radiative quenching?",
]


def evaluate(directory):
    from dataclasses import replace

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.autonomous import registry_checks
    from nasa_fire_ai.ingestion.scientific_proposals import (
        extract_source,
        observation_conclusion_candidates,
        search_staged,
    )
    from nasa_fire_ai.ingestion.semantic import load_semantic_registry, project_legacy
    from nasa_fire_ai.query.ontology_navigation import RouteStep
    from nasa_fire_ai.query.v2 import QueryIntentV2
    from nasa_fire_ai.services.investigation import evaluate_sufficiency
    from nasa_fire_ai.services.maintenance import run_cycle
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    snapshot = directory / "runtime.sqlite"
    if snapshot.exists():
        raise FileExistsError(snapshot)
    source = EvidenceRegistry(Settings().registry_path, read_only=True)
    with sqlite3.connect(snapshot) as target:
        source.db.backup(target)
    source.db.close()
    reused_receipts = 0
    prior_snapshots = sorted((ROOT / "artifacts").glob("phase3c_closure_*/runtime.sqlite"))
    prior_snapshots = [p for p in prior_snapshots if p.resolve() != snapshot.resolve()]
    if prior_snapshots:
        previous = EvidenceRegistry(prior_snapshots[-1], read_only=True)
        with sqlite3.connect(snapshot) as target:
            for row in previous.db.execute(
                "SELECT cache_key,cache_kind,payload_json,created_at FROM phase3_cache WHERE cache_kind IN ('research_plan','scientific_extraction')"
            ):
                payload = json.loads(row[2])
                model_receipt = payload.get("model", {})
                if not payload.get("error_type") and not (
                    isinstance(model_receipt, dict) and model_receipt.get("error_type")
                ):
                    target.execute(
                        "INSERT OR IGNORE INTO phase3_cache VALUES (?,?,?,?)", tuple(row)
                    )
                    reused_receipts += 1
        previous.db.close()
    write(
        directory / "receipt_reuse.json",
        {
            "successful_receipts_imported": reused_receipts,
            "boundary": "Provider receipt replay only; no scientific facts or proposals imported",
        },
    )
    for flag in (
        "NATIVE_V2_QUERY_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
    ):
        os.environ[flag] = "true"
    os.environ["RESEARCH_MAX_ROUNDS"] = "4"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    os.environ["NEMOTRON_SCIENTIFIC_SYNTHESIS_ENABLED"] = "false"
    write(
        directory / "queries.json",
        {"questions": QUESTIONS, "candidate_budget": 8, "max_rounds": 4, "expert_labels": None},
    )
    # Execute the frozen pre-change service in a separate interpreter, against
    # the same registry snapshot, without changing the repository checkout.
    commit = json.loads((directory / "baseline.json").read_text())["commit"]
    baseline_env = dict(os.environ)
    baseline_env.update(
        AUTONOMOUS_RESEARCH_ENABLED="false",
        SCIENTIFIC_SYNTHESIS_ENABLED="true",
        NEMOTRON_RESEARCH_PLANNING_ENABLED="false",
    )
    with tempfile.TemporaryDirectory(prefix="nasa-closure-baseline-") as checkout:
        archive = subprocess.check_output(["git", "archive", commit, "src"], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(checkout, filter="data")
        for folder in ("domain", "ontology", "data"):
            (Path(checkout) / folder).symlink_to(ROOT / folder, target_is_directory=True)
        baseline_env["PYTHONPATH"] = str(Path(checkout) / "src")
        program = """import json,sys
from pathlib import Path
from dataclasses import replace
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.services.phase3 import Phase3AssistantService
root=Path(sys.argv[1]); service=Phase3AssistantService(root=root,settings=replace(Settings(),root=root,nvidia_api_key=None))
service.registry.db.close(); service.registry=EvidenceRegistry(Path(sys.argv[2]))
questions=json.loads(sys.argv[3]); rows=[]
for q in questions:
 r=service.answer_query(q); rows.append({'question':q,'answer':r.rendered_answer,'metadata':r.evidence_bundle.retrieval_metadata,'evidence_ids':[p['evidence_id'] for p in r.evidence_bundle.evidence_passages]})
print(json.dumps(rows))
"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                program,
                str(ROOT),
                str(snapshot.resolve()),
                json.dumps(QUESTIONS),
            ],
            cwd=checkout,
            env=baseline_env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        write(
            directory / "answers_a_baseline.json",
            {
                "commit": commit,
                "exit_code": result.returncode,
                "cases": json.loads(result.stdout) if result.returncode == 0 else [],
                "error_type": "BASELINE_PROCESS_FAILED" if result.returncode else None,
            },
        )
    settings = replace(Settings(), nvidia_api_key=None)
    service = Phase3AssistantService(root=ROOT, settings=settings)
    service.registry.db.close()
    service.registry = EvidenceRegistry(snapshot)
    for variant, research, synthesis in (
        ("b", False, False),
        ("c", True, False),
        ("e", True, True),
    ):
        os.environ["AUTONOMOUS_RESEARCH_ENABLED"] = str(research).lower()
        os.environ["SCIENTIFIC_SYNTHESIS_ENABLED"] = str(synthesis).lower()
        os.environ["NEMOTRON_RESEARCH_PLANNING_ENABLED"] = "false"
        rows = []
        for question in QUESTIONS:
            began = perf_counter()
            response = service.answer_query(question)
            bundle = response.evidence_bundle
            intent = QueryIntentV2.model_validate(bundle.retrieval_metadata["query_intent_v2"])
            rows.append(
                {
                    "question": question,
                    "answer": response.rendered_answer,
                    "intent": intent.model_dump(mode="json"),
                    "coverage": evaluate_sufficiency(question, intent, bundle, service.registry),
                    "metadata": bundle.retrieval_metadata,
                    "direct": bundle.direct_evidence,
                    "related": bundle.related_evidence,
                    "evidence_ids": [p["evidence_id"] for p in bundle.evidence_passages],
                    "latency_ms": (perf_counter() - began) * 1000,
                    "citations_resolve": all(
                        service.registry.resolve(p["evidence_id"]) for p in bundle.evidence_passages
                    ),
                    "scientific_precision": "NOT_MEASURABLE",
                }
            )
            print(variant, question[:42], flush=True)
        write(
            directory / f"answers_{variant}.json",
            {
                "cases": rows,
                "note": "Final emission gate is mandatory in every corrected V2 variant; C and E differ in the legacy synthesis flag, not scientific authority",
            },
        )
    # Three bounded live planner comparisons; credentials never enter receipts.
    live = Phase3AssistantService(root=ROOT)
    live.registry.db.close()
    live.registry = EvidenceRegistry(snapshot)
    os.environ["NEMOTRON_RESEARCH_PLANNING_ENABLED"] = "true"
    rows = []
    for question in (QUESTIONS[0], QUESTIONS[2], QUESTIONS[10]):
        response = live.answer_query(question)
        rows.append(
            {
                "question": question,
                "answer": response.rendered_answer,
                "metadata": response.evidence_bundle.retrieval_metadata,
                "evidence_ids": [
                    p["evidence_id"] for p in response.evidence_bundle.evidence_passages
                ],
            }
        )
        print("d", question[:42], flush=True)
    write(directory / "answers_d_planner.json", {"cases": rows})
    semantic = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    source_row = service.registry.db.execute(
        "SELECT source_id,sha256,filename FROM sources WHERE nasa_id='20260003546' AND status NOT IN ('SUPERSEDED_DOCUMENT','ROLLED_BACK_DOCUMENT') ORDER BY (source_id LIKE '%@%') DESC,retrieved_at DESC LIMIT 1"
    ).fetchone()
    if source_row:
        source_id = source_row[0]
        extraction = extract_source(
            source_id, service.registry, semantic, Settings(), model_enabled=True
        )
        write(
            directory / "source_extraction.json",
            {
                "source": dict(source_row),
                "extraction": extraction,
                "retrievable_proposals": search_staged(
                    "depressurization oxygen extinguishment",
                    service.registry,
                    limit=32,
                    source_ids=[source_id],
                ),
                "observation_conclusion_candidates": observation_conclusion_candidates(
                    service.registry, source_id
                ),
            },
        )
        cycles = [
            run_cycle(
                ROOT,
                service.registry,
                semantic,
                Settings(),
                identifiers=["20260003546"],
                dry_run=False,
                offline=True,
                model_enabled=True,
                max_sources=1,
                max_model_calls=1,
            )
            for _ in range(2)
        ]
        write(directory / "maintenance.json", {"cycles": cycles, "codex_runtime_dependency": False})
    store = project_legacy(ROOT, service.registry)
    routes = [
        store.explore_route(
            "PMMA",
            [RouteStep("hasMaterial", "REVERSE"), RouteStep("belongsToInvestigation")],
            service.registry,
        )
    ]
    from pyshacl import validate
    from rdflib import Graph

    shacl = {}
    for label, graph, shape in (
        ("canonical", Graph().parse(ROOT / "data/canonical/graph.ttl"), "shapes.ttl"),
        ("native", store.graph, "semantic_shapes.ttl"),
        ("taxonomy", store.graph, "semantic_taxonomy_shapes.ttl"),
    ):
        conforms, _, report = validate(graph, shacl_graph=str(ROOT / "ontology" / shape))
        shacl[label] = {"conforms": bool(conforms), "report": report}
    frozen = json.loads((directory / "baseline.json").read_text())["files"]
    drift = [
        row["path"]
        for row in frozen
        if row["path"].startswith(("data/raw/", "data/canonical/", "evals/"))
        and digest(ROOT / row["path"]) != row["sha256"]
    ]
    write(
        directory / "integrity.json",
        {
            "registry": registry_checks(service.registry),
            "shacl": shacl,
            "immutable_drift": drift,
            "graph_routes": routes,
        },
    )
    service.registry.db.close()
    live.registry.db.close()


def export(directory):
    import zipfile

    from nasa_fire_ai.config import Settings

    destination = directory / "audit.zip"
    if destination.exists():
        raise FileExistsError(destination)
    secrets = [
        value
        for key, value in os.environ.items()
        if any(word in key.upper() for word in ("API_KEY", "TOKEN", "PASSWORD", "SECRET"))
        and len(value) >= 8
    ]
    # Materializing settings loads .env with override=False, without exposing it.
    settings = Settings()
    secrets += [s for s in (settings.nvidia_api_key, settings.api_key) if s]
    from nasa_fire_ai.evidence import EvidenceRegistry

    # Reconstruct the evidence registry from public scientific and operational
    # review records, excluding private caches, embeddings and ingestion scratch.
    audit_db = directory / "audit_evidence.sqlite"
    if audit_db.exists():
        raise FileExistsError(audit_db)
    source = EvidenceRegistry(directory / "runtime.sqlite", read_only=True)
    clean = EvidenceRegistry(audit_db)
    for table in (
        "sources",
        "documents",
        "passages",
        "evidence_refs",
        "document_metadata",
        "semantic_staging",
        "evidence_locations",
        "structured_cells",
    ):
        for row in source.db.execute(f"SELECT * FROM {table}"):
            if any(secret in str(cell) for cell in row for secret in secrets):
                raise ValueError("Secret exclusion gate failed in registry field")
            clean.db.execute(
                f"INSERT INTO {table} VALUES ({','.join('?' for _ in row)})", tuple(row)
            )
    clean.db.execute("INSERT INTO passages_fts SELECT evidence_id,text FROM passages")
    clean.db.commit()
    clean.db.execute("VACUUM")
    clean.db.close()
    source.db.close()
    entries = []
    paths = []
    for folder in (
        "src",
        "domain",
        "ontology",
        "tests",
        "scripts",
        "ops",
        "evals",
        "data/canonical",
    ):
        paths += [
            p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        ]
    paths += [
        ROOT / name
        for name in ("README.md", "AGENTS.md", "uv.lock", "pyproject.toml", ".env.example")
    ]
    paths += [audit_db]
    paths += list((ROOT / "data/index").glob("scientific_context_*.json"))
    paths += [ROOT / "data/raw/manifest.json"]
    scientific_source = json.loads((directory / "source_extraction.json").read_text())["source"]
    selected_pdf = ROOT / scientific_source["filename"]
    if digest(selected_pdf) != scientific_source["sha256"]:
        raise ValueError("Selected NASA source digest changed")
    paths.append(selected_pdf)
    paths += [p for p in (ROOT / "artifacts/phase3c_closure_v2").glob("*.json")]
    paths += [p for p in (ROOT / "artifacts/phase3c_closure_v4").glob("*.json")]
    paths += list((ROOT / "docs").glob("PHASE3C_REASONING_CLOSURE*.md"))
    paths += [
        p for p in directory.rglob("*") if p.is_file() and p.suffix in {".json", ".txt", ".md"}
    ]
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(set(paths)):
            raw = path.read_bytes()
            for secret in secrets:
                if secret.encode() in raw:
                    raise ValueError("Secret exclusion gate failed")
            relative = str(path.relative_to(ROOT))
            entries.append(
                {
                    "path": relative,
                    "archive_path": "data/index/evidence.sqlite" if path == audit_db else relative,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            package.writestr("data/index/evidence.sqlite" if path == audit_db else relative, raw)
        manifest = {
            "files": entries,
            "count": len(entries),
            "configuration": {
                "model": settings.nvidia_phase3_model,
                "credentials": "EXCLUDED",
                "environment_precedence": "process wins",
            },
            "reproducibility": "PARTIAL",
            "excluded": [
                {
                    "path": "data/raw",
                    "reason": "Historical raw corpus excluded to avoid duplication; selected verified NTRS 20260003546 PDF is included. Baseline manifest contains historical paths/digests; acquisition recipes are in scripts/fetch_seed_corpus.py and scripts/maintain_knowledge.py",
                },
                {
                    "path": "data/index",
                    "reason": "Private operational caches and vector corpus excluded; a sanitized public evidence database and scientific context indexes are included for deterministic service replay",
                },
            ],
            "rerunnable_alone": [
                "isolated unit tests that construct fixtures",
                "contract and query schemas",
                "deterministic research CLI against exported public evidence registry and canonical projection",
            ],
            "requires_verified_corpus": [
                "real-source service evaluation",
                "SHACL provenance parity",
                "hybrid comparisons",
            ],
            "requires_credentials": ["fresh live inference"],
        }
        package.writestr("audit_manifest.json", json.dumps(manifest, indent=2))
    write(
        directory / "artifact_index.json",
        {
            "package": {
                "path": str(destination.relative_to(ROOT)),
                "bytes": destination.stat().st_size,
                "sha256": digest(destination),
            },
            "files": entries,
            "reproducibility": "PARTIAL",
        },
    )


def supplement(directory):
    from dataclasses import replace
    from unittest.mock import patch

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.services.native import answer_native_text
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    snapshot = directory / "runtime.sqlite"
    for flag in (
        "NATIVE_V2_QUERY_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "AUTONOMOUS_RESEARCH_ENABLED",
    ):
        os.environ[flag] = "true"
    os.environ["RESEARCH_MAX_ROUNDS"] = "5"
    os.environ["NEMOTRON_RESEARCH_PLANNING_ENABLED"] = "false"
    service = Phase3AssistantService(root=ROOT, settings=replace(Settings(), nvidia_api_key=None))
    service.registry.db.close()
    service.registry = EvidenceRegistry(snapshot)
    recoveries = []
    for query in (
        "What observations and interventions did NASA report about PMMA combustion?",
        "What observations and conditions did NASA report for Saffire-I?",
        "What observations and conclusions concern spacecraft fire suppression?",
    ):

        def incomplete(*args, **kwargs):
            response = answer_native_text(*args, **kwargs)
            for field in (
                "experimental_observations",
                "interventions",
                "nasa_conclusions",
                "conditions",
                "semantic_records",
                "evidence_passages",
            ):
                getattr(response.execution.bundle, field).clear()
            return response

        with patch("nasa_fire_ai.services.native.answer_native_text", incomplete):
            response = service.answer_query(query)
        recoveries.append(
            {
                "question": query,
                "fault_injection": "Initial information inventories and passages suppressed; subsequent searches run actual native executor over real NASA evidence",
                "answer": response.rendered_answer,
                "trace": response.evidence_bundle.retrieval_metadata["investigation"],
            }
        )
    write(
        directory / "adaptive_recovery.json",
        {"cases": recoveries, "real_source_evidence": True, "initial_fault_is_simulated": True},
    )
    flags = []
    for research, synthesis in ((False, False), (True, False), (False, True), (True, True)):
        os.environ["AUTONOMOUS_RESEARCH_ENABLED"] = str(research).lower()
        os.environ["SCIENTIFIC_SYNTHESIS_ENABLED"] = str(synthesis).lower()
        response = service.answer_query(QUESTIONS[3])
        flags.append(
            {
                "research": research,
                "synthesis": synthesis,
                "answer": response.rendered_answer,
                "gate": response.evidence_bundle.retrieval_metadata.get("final_emission_gate"),
                "verifications": response.evidence_bundle.retrieval_metadata.get(
                    "claim_verification"
                ),
            }
        )
    write(
        directory / "feature_flags.json",
        {"cases": flags, "identical_final_answers": len({r["answer"] for r in flags}) == 1},
    )
    # Frozen existing vector generation, no global vector enablement or corpus re-embedding.
    import numpy as np
    import yaml

    from nasa_fire_ai.ingestion.semantic import project_legacy
    from nasa_fire_ai.query.native import execute_native
    from nasa_fire_ai.query.native_interpreter import resolve_minimal
    from nasa_fire_ai.query.numeric_mentions import DeterministicMinimalInterpreter
    from nasa_fire_ai.query.v2 import QueryIntentV2
    from nasa_fire_ai.retrieval.semantic import (
        EmbeddingCache,
        LocalVectorIndex,
        NvidiaEmbeddingProvider,
    )

    settings = Settings()
    index = LocalVectorIndex(ROOT / "data/index/autonomy_vectors", "text_v1")
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    store = project_legacy(ROOT, service.registry)
    hybrid = {
        "precision": "NOT_MEASURABLE",
        "adoption": "KEEP_EXPERIMENTAL",
        "candidate_budget": 5,
        "cases": [],
    }
    try:
        ids = np.load(index.ids_path).tolist()
        available = [eid for eid in ids if service.registry.resolve(eid)]
        provider = NvidiaEmbeddingProvider(
            settings.nvidia_api_key,
            settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
            settings.nvidia_embedding_model,
            retries=1,
            timeout_seconds=20,
        )
        cache = EmbeddingCache(service.registry)
        queries = QUESTIONS[:5]
        vectors, hits, fresh = cache.embed_cached(provider, queries, "query", batch_size=5)
        hybrid["query_embedding_usage"] = {
            "cache_hits": hits,
            "fresh_units": fresh,
            "last_provider_receipt": getattr(provider, "last_receipt", None),
        }
        hybrid["vector_generation_sha256"] = digest(index.metadata_path)
        hybrid["finite_vectors"] = bool(np.isfinite(np.load(index.vectors_path)).all())
        hybrid["corpus_size"] = len(available)
        for query, vector in zip(queries, vectors):
            proposal = DeterministicMinimalInterpreter(store.registry, language).interpret_minimal(
                query
            )
            intent = resolve_minimal(proposal, store.registry, language, query=query)
            # resolve_minimal returns the validated V2 proposal used by native execution.
            if not isinstance(intent, QueryIntentV2):
                intent = intent.intent
            native = execute_native(intent, query, store, service.registry, limit=5)
            subjects = [
                r["id"] for r in native.bundle.direct_evidence + native.bundle.related_evidence
            ]
            subjects += native.bundle.retrieval_metadata.get("selection_trace", {}).get(
                "selected_information", []
            )
            if native.plan.documentary:
                subjects += native.plan.candidate_entity_ids
            graph_ids = sorted(
                {eid for entity in subjects for eid in store.evidence(entity) if eid in available}
            )
            lexical = [
                p["evidence_id"]
                for p in service.registry.search(query, eligible_ids=available, limit=5)
            ]
            vector_ids = [eid for eid, _ in index.search(vector, limit=5)]
            kg = graph_ids[:5]

            def fuse(*rankings):
                scores = {}
                for ranking in rankings:
                    for rank, eid in enumerate(ranking):
                        scores[eid] = scores.get(eid, 0) + 1 / (61 + rank)
                return sorted(scores, key=lambda eid: (-scores[eid], eid))[:5]

            rankings = {
                "A_FTS": lexical,
                "B_vector": vector_ids,
                "C_KG": kg,
                "D_lexical_KG": fuse(lexical, kg),
                "E_lexical_vector": fuse(lexical, vector_ids),
                "F_all": fuse(lexical, vector_ids, kg),
                "G_contextual": [
                    p["evidence_id"]
                    for p in native.bundle.evidence_passages
                    if p["evidence_id"] in available
                ][:5],
            }
            hybrid["cases"].append(
                {
                    "question": query,
                    "rankings": rankings,
                    "KG_empty": not kg,
                    "graph_targets": intent.targets,
                    "graph_subject_count": len(subjects),
                    "unique_ids": {name: len(set(values)) for name, values in rankings.items()},
                    "unique_useful_evidence": "NOT_MEASURABLE_WITHOUT_LABELS",
                }
            )
    except (RuntimeError, ValueError, FileNotFoundError, AttributeError) as error:
        hybrid["failure"] = type(error).__name__
    write(directory / "hybrid.json", hybrid)
    service.registry.db.close()


def baseline(directory):
    commit = json.loads((directory / "baseline.json").read_text())["commit"]
    snapshot = directory / "runtime.sqlite"
    environment = dict(os.environ)
    environment.update(
        NATIVE_V2_QUERY_ENABLED="true",
        AUTONOMOUS_RESEARCH_ENABLED="false",
        SCIENTIFIC_SYNTHESIS_ENABLED="true",
        SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED="true",
        SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED="true",
        ONTOLOGY_GRAPH_ENRICHMENT_ENABLED="true",
        NEMOTRON_RESEARCH_PLANNING_ENABLED="false",
    )
    with tempfile.TemporaryDirectory(prefix="nasa-baseline-replay-") as checkout:
        archive = subprocess.check_output(["git", "archive", commit, "src"], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(checkout, filter="data")
        for folder in ("domain", "ontology", "data"):
            (Path(checkout) / folder).symlink_to(ROOT / folder, target_is_directory=True)
        environment["PYTHONPATH"] = str(Path(checkout) / "src")
        program = """import json,sys
from pathlib import Path
from dataclasses import replace
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.services.phase3 import Phase3AssistantService
from nasa_fire_ai.services.investigation import evaluate_sufficiency
from nasa_fire_ai.query.v2 import QueryIntentV2
root=Path(sys.argv[1]); service=Phase3AssistantService(root=root,settings=replace(Settings(),root=root,nvidia_api_key=None))
service.registry.db.close(); service.registry=EvidenceRegistry(Path(sys.argv[2]))
rows=[]
for q in json.loads(sys.argv[3]):
 r=service.answer_query(q); intent=QueryIntentV2.model_validate(r.evidence_bundle.retrieval_metadata['query_intent_v2']); rows.append({'question':q,'answer':r.rendered_answer,'coverage':evaluate_sufficiency(q,intent,r.evidence_bundle,service.registry),'metadata':r.evidence_bundle.retrieval_metadata,'evidence_ids':[p['evidence_id'] for p in r.evidence_bundle.evidence_passages]})
print(json.dumps(rows))
"""
        result = subprocess.run(
            [sys.executable, "-c", program, str(ROOT), str(snapshot), json.dumps(QUESTIONS)],
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        write(
            directory / "answers_a_baseline_verified.json",
            {
                "commit": commit,
                "exit_code": result.returncode,
                "cases": json.loads(result.stdout) if result.returncode == 0 else [],
                "diagnostic": result.stderr
                if result.returncode
                else "Baseline package initially lacked repository-relative ontology/lexicon resources; replay links the frozen resources read-only in the isolated source checkout",
            },
        )


def quality(directory):
    directory.mkdir(parents=True, exist_ok=True)
    checks = []
    for name, command in (
        ("format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("pytest", ["uv", "run", "pytest", "-q"]),
    ):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        path = directory / f"{name}.txt"
        with path.open("x") as stream:
            stream.write(result.stdout + result.stderr)
        checks.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "log": str(path.relative_to(ROOT)),
                "sha256": digest(path),
            }
        )
        print(name, result.returncode, flush=True)
    write(
        directory / "quality.json",
        {
            "checks": checks,
            "passed": all(c["exit_code"] == 0 for c in checks),
            "warning_classification": "rdflib default_context DeprecationWarning in existing native and enrichment suites; no scientific assertion inferred from warnings",
        },
    )


def reports(directory):
    from collections import Counter

    import pymupdf

    from nasa_fire_ai.evidence import EvidenceRegistry

    def read(name):
        return json.loads((directory / name).read_text())

    answers = read("answers_e.json")["cases"]
    baseline_answers = read("answers_a_baseline_verified.json")
    extraction = read("source_extraction.json")
    source_file = ROOT / extraction["source"]["filename"]
    source_registry = EvidenceRegistry(directory / "runtime.sqlite", read_only=True)
    span_checks = []
    with pymupdf.open(source_file) as pdf:
        for row in source_registry.db.execute(
            "SELECT p.evidence_id,p.page,p.text FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=? ORDER BY p.page",
            (extraction["source"]["source_id"],),
        ):
            original = pdf[row["page"] - 1].get_text()
            span_checks.append(
                {
                    "evidence_id": row["evidence_id"],
                    "physical_page": row["page"],
                    "matches_original_pdf_page": " ".join(row["text"].split())
                    == " ".join(original.split()),
                }
            )
    source_registry.db.close()
    write(
        directory / "source_integrity_receipt.json",
        {
            "path": str(source_file.relative_to(ROOT)),
            "actual_sha256": digest(source_file),
            "registered_sha256": extraction["source"]["sha256"],
            "digest_matches": digest(source_file) == extraction["source"]["sha256"],
            "pages": span_checks,
        },
    )
    final_files = []
    for folder in ("src", "scripts", "tests", "domain", "ontology", "ops"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                final_files.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                    }
                )
    write(directory / "final_code_manifest.json", {"files": final_files})
    cases = read("answers_d_planner.json")["cases"]
    planning = [r for case in cases for r in case["metadata"]["investigation"]["model_calls"]]
    fresh = []
    for version in ("v2", "v4"):
        previous = ROOT / f"artifacts/phase3c_closure_{version}/answers_d_planner.json"
        if previous.exists():
            fresh += [
                r
                for case in json.loads(previous.read_text())["cases"]
                for r in case["metadata"]["investigation"]["model_calls"]
                if r["execution"] == "FRESH_INFERENCE"
            ]
    decisions = {
        "SEMANTIC_SUFFICIENCY": "PARTIAL",
        "ADAPTIVE_INVESTIGATION": "OPERATIONAL",
        "EVIDENCE_DRIVEN_REPLANNING": "PARTIAL",
        "NEMOTRON_PLANNING_VALUE": "INCONCLUSIVE",
        "FINAL_CLAIM_VERIFICATION": "ENFORCED",
        "FEATURE_FLAG_INTEGRATION": "VALIDATED",
        "CONCEPTUAL_QUERY_HANDLING": "VALIDATED",
        "BIBLIOGRAPHIC_QUERY_HANDLING": "PARTIAL",
        "SCIENTIFIC_EXTRACTION": "PARTIAL",
        "AUTOMATIC_PUBLICATION_CONTRACTS": "PARTIAL",
        "OBSERVATION_CONCLUSION_REASONING": "REVIEW_REQUIRED",
        "ONTOLOGY_GRAPH_REASONING": "PARTIAL",
        "HYBRID_RAG": "KEEP_EXPERIMENTAL",
        "AUTONOMOUS_MAINTENANCE": "PARTIAL",
        "OPERATIONAL_FAILURE_RECOVERY": "PARTIAL",
        "AUDIT_REPRODUCIBILITY": "PARTIAL",
        "END_TO_END_SCIENTIFIC_ANSWERS": "PARTIAL",
        "INDEPENDENT_SCIENTIFIC_RELEVANCE": "REVIEW_REQUIRED",
        "V2_DEFAULT_PATH": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    result = {
        "decisions": decisions,
        "scientific_precision": "NOT_MEASURABLE",
        "baseline_commit": baseline_answers["commit"],
        "baseline_exit_code": baseline_answers["exit_code"],
        "questions_freshly_evaluated": len(answers),
        "baseline_sufficient_count": sum(
            c["coverage"]["sufficient"] for c in baseline_answers["cases"]
        ),
        "corrected_sufficient_count": sum(c["coverage"]["sufficient"] for c in answers),
        "scientific_accuracy_from_counts": "NOT_PERMITTED",
        "fresh_planner_calls_campaign": len(fresh),
        "known_fresh_planner_tokens_campaign": sum(
            (r.get("usage") or {}).get("total_tokens", 0) for r in fresh
        ),
        "planner_replays_final_run": sum(r["execution"] == "CACHE_REPLAY" for r in planning),
        "source": extraction["source"],
        "extraction_status_counts": dict(
            Counter(
                r.get("review_status", r.get("status")) for r in extraction["extraction"]["items"]
            )
        ),
        "new_scientific_facts": extraction["extraction"]["canonical_scientific_changes"],
        "extraction_provider_error": extraction["extraction"].get("model", {}).get("error_type"),
        "extraction_unknown_usage": extraction["extraction"].get("model", {}).get("usage") is None,
        "historical_metrics": "266 tests and 38-question results are historical; current receipts cover twelve questions and the current test suite",
        "source_integrity": read("integrity.json"),
        "remaining_dependencies": [
            "Independent topical and claim relevance labels",
            "Approved prose-to-experimental-scope and epistemic publication contracts",
            "Reviewed observation-to-conclusion attribution; current canonical registry lacks a scientific support relation",
            "Full maintenance failure matrix and hard in-flight deadline enforcement",
            "Hybrid corpus labels and model-assisted usefulness judgments",
        ],
    }
    write(directory / "summary.json", result)
    packages = [
        (
            "semantic_sufficiency",
            "PARTIAL",
            ["src/nasa_fire_ai/services/investigation.py"],
            ["answers_a_baseline_verified.json", "answers_e.json"],
        ),
        (
            "adaptive_investigation",
            "OPERATIONAL",
            ["src/nasa_fire_ai/services/investigation.py"],
            ["adaptive_recovery.json"],
        ),
        (
            "nemotron_planning",
            "INCONCLUSIVE",
            ["src/nasa_fire_ai/llm/research.py"],
            ["answers_d_planner.json"],
        ),
        (
            "claim_emission_gate",
            "ENFORCED",
            [
                "src/nasa_fire_ai/services/claim_verification.py",
                "src/nasa_fire_ai/services/scientific_synthesis.py",
            ],
            ["feature_flags.json", "quality_verified/pytest.txt"],
        ),
        (
            "feature_flags",
            "VALIDATED",
            ["src/nasa_fire_ai/services/phase3.py"],
            ["feature_flags.json"],
        ),
        (
            "source_extraction",
            "PARTIAL",
            ["src/nasa_fire_ai/ingestion/scientific_proposals.py"],
            ["source_extraction.json"],
        ),
        (
            "automatic_publication",
            "PARTIAL",
            [
                "src/nasa_fire_ai/ingestion/scientific_proposals.py",
                "src/nasa_fire_ai/ingestion/semantic.py",
            ],
            ["source_extraction.json", "quality_verified/pytest.txt"],
        ),
        (
            "observation_conclusion",
            "REVIEW_REQUIRED",
            ["src/nasa_fire_ai/ingestion/scientific_proposals.py"],
            ["source_extraction.json"],
        ),
        (
            "graph_routing",
            "PARTIAL",
            ["src/nasa_fire_ai/query/native.py"],
            ["integrity.json", "hybrid.json"],
        ),
        (
            "hybrid_retrieval",
            "KEEP_EXPERIMENTAL",
            ["src/nasa_fire_ai/retrieval/semantic.py"],
            ["hybrid.json"],
        ),
        (
            "independent_runtime",
            "PARTIAL",
            ["scripts/research.py", "scripts/maintain_knowledge.py"],
            ["maintenance.json", "operations.json"],
        ),
        (
            "failure_recovery",
            "PARTIAL",
            ["src/nasa_fire_ai/services/maintenance.py"],
            ["maintenance.json", "quality_verified/pytest.txt"],
        ),
        ("reproducibility", "PARTIAL", ["scripts/phase3c_closure.py"], ["artifact_index.json"]),
        (
            "end_to_end_answers",
            "PARTIAL",
            ["src/nasa_fire_ai/services/phase3.py"],
            ["answers_e.json"],
        ),
        (
            "comparative_evaluation",
            "PARTIAL",
            ["scripts/phase3c_closure.py"],
            [
                "answers_a_baseline_verified.json",
                "answers_b.json",
                "answers_c.json",
                "answers_d_planner.json",
                "answers_e.json",
                "hybrid.json",
            ],
        ),
        ("readiness", "NO", ["README.md"], ["summary.json"]),
    ]
    write(
        directory / "work_packages.json",
        {
            "packages": [
                {
                    "name": name,
                    "decision": decision,
                    "code": code,
                    "receipts": [
                        str((directory / receipt).relative_to(ROOT)) for receipt in receipts
                    ],
                    "independent_scientific_review": None,
                }
                for name, decision, code, receipts in packages
            ]
        },
    )
    for name, decision, code, receipts in packages:
        text = (
            f"# Phase 3C closure: {name} — v1\n\nDecision: {decision}. Independent scientific precision: NOT MEASURABLE.\n\nImplementation: "
            + ", ".join(code)
            + ".\n\nExecution receipts: "
            + ", ".join(str((directory / p).relative_to(ROOT)) for p in receipts)
            + ".\n\nThese receipts distinguish engineering execution from scientific interpretation. No new scientific approval is inferred from retrieval, source proximity, valid JSON or passing tests. See docs/PHASE3C_REASONING_CLOSURE_V1.md and summary.json for limitations.\n"
        )
        with (directory / f"report_{name}_v1.md").open("x") as stream:
            stream.write(text)


def operations(directory):
    environment = dict(os.environ)
    environment["NVIDIA_API_KEY"] = ""
    registry = str(directory / "runtime.sqlite")
    commands = [
        ["uv", "run", "python", "scripts/research.py", "ask", QUESTIONS[5], "--registry", registry],
        [
            "uv",
            "run",
            "python",
            "scripts/research.py",
            "review",
            "depressurization",
            "--registry",
            registry,
        ],
        ["uv", "run", "python", "scripts/research.py", "status", "--registry", registry],
        [
            "uv",
            "run",
            "python",
            "scripts/maintain_knowledge.py",
            "validation-only",
            "--registry",
            registry,
        ],
    ]
    maintenance = [
        "uv",
        "run",
        "python",
        "scripts/maintain_knowledge.py",
        "cycle",
        "--execute",
        "--offline",
        "--nasa-id",
        "20260003546",
        "--max-sources",
        "1",
        "--extract",
        "--max-model-calls",
        "0",
        "--registry",
        registry,
    ]
    commands += [maintenance, maintenance]
    receipts = []
    for command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        receipts.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "output": result.stdout,
                "errors": result.stderr,
                "provider_profile": "Explicit no-key execution; deterministic fallback",
                "codex_runtime_dependency": False,
            }
        )
        print(command[4], result.returncode, flush=True)
    write(directory / "operations.json", {"commands": receipts})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "mode",
        choices=[
            "freeze",
            "baseline",
            "evaluate",
            "supplement",
            "operations",
            "reports",
            "quality",
            "export",
        ],
    )
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    args.directory = args.directory.resolve()
    if args.mode == "freeze":
        freeze(args.directory)
    elif args.mode == "evaluate":
        evaluate(args.directory)
    elif args.mode == "supplement":
        supplement(args.directory)
    elif args.mode == "quality":
        quality(args.directory)
    elif args.mode == "baseline":
        baseline(args.directory)
    elif args.mode == "operations":
        operations(args.directory)
    elif args.mode == "reports":
        reports(args.directory)
    else:
        export(args.directory)


if __name__ == "__main__":
    main()
