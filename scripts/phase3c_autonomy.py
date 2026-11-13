"""Versioned Phase-3C autonomous-engine execution receipts, not scientific gold."""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.scientific_proposals import observation_conclusion_candidates
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.services.phase3 import Phase3AssistantService

PREFIX = "phase3c_autonomy"
VERSION = os.getenv("PHASE3C_AUTONOMY_VERSION", "v1")
SNAPSHOT = ROOT / "data/index/autonomy_snapshot_v1.sqlite"
QUESTIONS = [
    ("A", "What did NASA observe about PMMA combustion?"),
    ("B", "What did NASA observe about PMMA combustion under microgravity?"),
    ("C", "Does acrylic mean PMMA?"),
    ("D", "Which NASA publications discuss depressurization as a fire suppression technique?"),
    (
        "E",
        "Which experiments support NASA's conclusions about depressurization-based fire suppression, and under what conditions were the observations made?",
    ),
    ("F", "How do PMMA combustion observations differ between microgravity and normal gravity?"),
    ("G", "What happened when airflow was interrupted and later restored?"),
    ("H", "What questions about fire suppression remain unresolved in the NASA literature?"),
]
HOLDOUT = [
    ("holdout-pressure", "Which starting pressures were reported for depressurization tests?"),
    ("holdout-method", "What test configurations were used to study cabin venting?"),
    ("holdout-backfill", "Which NASA sources describe nitrogen backfill during fire suppression?"),
    (
        "holdout-reignition",
        "What was observed after oxygen was reintroduced following extinguishment?",
    ),
    ("holdout-condition", "What oxygen concentrations applied to normal-gravity PMMA tests?"),
    ("holdout-limits", "Which explicit limitations were reported for depressurization testing?"),
    ("holdout-numeric", "Find observations for PMMA at 21% oxygen."),
    ("holdout-source", "Find publications discussing venting rates and extinguishment."),
    ("holdout-phenomenon", "What observations distinguish radiative quenching from blowoff?"),
    ("holdout-geometry", "Which PMMA specimen diameters were reported?"),
    ("holdout-unrelated", "Which NASA publications report seawater corrosion of aluminum?"),
    ("holdout-unavailable", "What did NASA observe about PMMA combustion at 999 kPa?"),
]


def save(name, value):
    path = ROOT / "artifacts" / f"{PREFIX}_{name}_{VERSION}.json"
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def configure():
    for flag in [
        "NATIVE_V2_QUERY_ENABLED",
        "SCIENTIFIC_SYNTHESIS_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "AUTONOMOUS_RESEARCH_ENABLED",
    ]:
        os.environ[flag] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    os.environ["NEMOTRON_RESEARCH_PLANNING_ENABLED"] = "false"


def service():
    instance = Phase3AssistantService()
    instance.registry.db.close()
    instance.registry = EvidenceRegistry(SNAPSHOT)
    return instance


def snapshot():
    if SNAPSHOT.exists():
        raise FileExistsError(SNAPSHOT)
    source = EvidenceRegistry(Settings().registry_path, read_only=True)
    with sqlite3.connect(SNAPSHOT) as target:
        source.db.backup(target)
    old = json.loads((ROOT / "artifacts/phase3c_consolidation_review_packet_v1.json").read_text())
    historical = [(r["case_id"], r.get("question", r.get("query"))) for r in old["cases"]]
    cases = list(dict.fromkeys(QUESTIONS + historical + HOLDOUT))
    save(
        "queries",
        {
            "cases": [
                {
                    "id": cid,
                    "question": q,
                    "independent_labels": None,
                    "holdout": cid.startswith("holdout"),
                }
                for cid, q in cases
                if q
            ],
            "label_authority": "Developer-authored engineering probes, not independently adjudicated scientific gold",
            "snapshot": str(SNAPSHOT.relative_to(ROOT)),
            "snapshot_sha256_before_evaluation": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
            "source_count": source.db.execute("SELECT count(*) FROM sources").fetchone()[0],
            "passage_count": source.db.execute("SELECT count(*) FROM passages").fetchone()[0],
        },
    )


def evaluate():
    configure()
    cases = json.loads((ROOT / "artifacts/phase3c_autonomy_queries_v1.json").read_text())["cases"]
    for variant in ["B", "C", "D"]:
        os.environ["AUTONOMOUS_RESEARCH_ENABLED"] = str(variant != "B").lower()
        instance = service()
        rows = []
        for case in cases:
            os.environ["NEMOTRON_RESEARCH_PLANNING_ENABLED"] = str(
                variant == "D" and case["id"] in {"E", "C", "holdout-reignition"}
            ).lower()
            began = perf_counter()
            response = instance.answer_query(case["question"])
            bundle = response.evidence_bundle
            rows.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "variant": variant,
                    "answer": response.rendered_answer,
                    "intent": bundle.retrieval_metadata.get("query_intent_v2"),
                    "direct_ids": [r["id"] for r in bundle.direct_evidence],
                    "related_ids": [r["id"] for r in bundle.related_evidence],
                    "evidence_ids": [p["evidence_id"] for p in bundle.evidence_passages],
                    "citations_resolve": all(
                        instance.registry.resolve(p["evidence_id"])
                        for p in bundle.evidence_passages
                    ),
                    "investigation": bundle.retrieval_metadata.get("investigation"),
                    "claim_verification": bundle.retrieval_metadata.get("claim_verification", []),
                    "staged_knowledge": bundle.retrieval_metadata.get(
                        "staged_scientific_knowledge", []
                    ),
                    "selection": bundle.retrieval_metadata.get("selection_trace"),
                    "latency_ms": (perf_counter() - began) * 1000,
                    "scientific_precision": None,
                    "independent_review": None,
                }
            )
            print(variant, case["id"], len(bundle.direct_evidence), flush=True)
        save(
            "answers_" + variant.lower(),
            {
                "cases": rows,
                "snapshot": str(SNAPSHOT.relative_to(ROOT)),
                "candidate_budget": 8,
                "initial_plus_maximum_rounds": 3,
                "classification_boundary": "All scientific precision fields unmeasured; DIRECT identity counts are engineering only",
            },
        )
        instance.registry.db.close()
    configure()
    instance = service()
    from nasa_fire_ai.services.native import answer_native_text as actual

    recoveries = []
    for question in [
        QUESTIONS[0][1],
        QUESTIONS[6][1],
        "What conclusions did NASA report for Saffire-I fire suppression?",
    ]:

        def incomplete(*args, **kwargs):
            response = actual(*args, **kwargs)
            bundle = response.execution.bundle
            for name in [
                "experimental_observations",
                "interventions",
                "nasa_conclusions",
                "evidence_passages",
            ]:
                getattr(bundle, name).clear()
            return response

        with patch("nasa_fire_ai.services.native.answer_native_text", incomplete):
            response = instance.answer_query(question)
        recoveries.append(
            {
                "question": question,
                "fault": "Initial requested-information inventories and passages deliberately removed at service retrieval boundary",
                "answer": response.rendered_answer,
                "trace": response.evidence_bundle.retrieval_metadata["investigation"],
                "scientific_review": None,
            }
        )
    save(
        "recovery",
        {
            "cases": recoveries,
            "service_workflow": True,
            "benchmark_specific_production_branches": False,
        },
    )
    source_id = "ntrs-20260003546@b4b64e88992718a75980"
    save(
        "attribution",
        {
            "source_id": source_id,
            "candidates": observation_conclusion_candidates(instance.registry, source_id),
            "approved_support_links": 0,
            "independent_scientific_review": None,
        },
    )
    store = project_legacy(ROOT, instance.registry)
    from nasa_fire_ai.query.ontology_navigation import RouteStep

    routes = []
    for subject, steps in [
        ("PMMA", [RouteStep("hasMaterial", "REVERSE"), RouteStep("belongsToInvestigation")]),
        ("psi-98", [RouteStep("belongsToInvestigation", "REVERSE"), RouteStep("hasMaterial")]),
    ]:
        routes.append(
            {
                "start": subject,
                "steps": [s.__dict__ for s in steps],
                "receipt": store.explore_route(subject, steps, instance.registry),
                "scientific_semantics": "ASSOCIATION; neither causality nor conclusion support",
            }
        )
    save(
        "graph_paths",
        {
            "routes": routes,
            "staged_rdf_propositions": getattr(store, "staged_proposition_count", 0),
        },
    )


def fuse(*rankings, limit=5):
    scores = {}
    for ranking in rankings:
        for rank, eid in enumerate(ranking):
            scores[eid] = scores.get(eid, 0) + 1 / (61 + rank)
    return sorted(scores, key=lambda eid: (-scores[eid], eid))[:limit]


def hybrid():
    import numpy as np

    from nasa_fire_ai.query.native import execute_native
    from nasa_fire_ai.query.v2 import QueryIntentV2
    from nasa_fire_ai.retrieval.semantic import (
        EmbeddingCache,
        LocalVectorIndex,
        NvidiaEmbeddingProvider,
    )

    configure()
    registry = EvidenceRegistry(SNAPSHOT)
    units = json.loads((ROOT / "artifacts/phase3c_real_context_source_units_v8.json").read_text())[
        "units"
    ]
    corpus = {r["evidence_id"]: registry.resolve(r["evidence_id"]) for r in units.values()}
    for r in registry.db.execute(
        "SELECT p.evidence_id FROM passages p JOIN documents d USING(document_id) WHERE d.source_id LIKE 'ntrs-20260003546@%'"
    ):
        corpus[r[0]] = registry.resolve(r[0])
    corpus = {eid: row for eid, row in corpus.items() if row and len(row["text"]) <= 10000}
    ids = sorted(corpus)
    cache = EmbeddingCache(registry)
    receipts = []

    class RecordedProvider(NvidiaEmbeddingProvider):
        def _embed(self, texts, input_type):
            began = perf_counter()
            vectors = super()._embed(texts, input_type)
            receipts.append({**self.last_receipt, "latency_ms": (perf_counter() - began) * 1000})
            print("embedded", input_type, len(texts), flush=True)
            return vectors

    settings = Settings()
    provider = RecordedProvider(
        settings.nvidia_api_key,
        settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        settings.nvidia_embedding_model,
        retries=1,
        timeout_seconds=25,
    )
    rows = json.loads(
        (
            ROOT
            / f"artifacts/phase3c_autonomy_answers_c_{os.getenv('AUTONOMY_ANSWER_VERSION', 'v1')}.json"
        ).read_text()
    )["cases"]
    results, usage = [], []
    try:
        vectors, hits, fresh = cache.embed_cached(
            provider, [corpus[eid]["text"] for eid in ids], "passage", batch_size=16
        )
        usage.append({"role": "passage", "cache_hits": hits, "fresh_units": fresh})
        qv, hits, fresh = cache.embed_cached(
            provider, [r["question"] for r in rows], "query", batch_size=16
        )
        usage.append({"role": "query", "cache_hits": hits, "fresh_units": fresh})
        index = LocalVectorIndex(ROOT / "data/index/autonomy_vectors", "text_v1")
        index.sync(
            dict(zip(ids, vectors)),
            {
                "model": provider.model_identity(),
                "corpus_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            },
        )
        unchanged = index.sync(
            dict(zip(ids, vectors)),
            {
                "model": provider.model_identity(),
                "corpus_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            },
        )
        integrity = bool(np.isfinite(np.load(index.vectors_path)).all())
        store = project_legacy(ROOT, registry)
        for row, vector in zip(rows, qv):
            query = row["question"]
            intent = QueryIntentV2.model_validate(row["intent"])
            lexical = [r["evidence_id"] for r in registry.search(query, eligible_ids=ids, limit=5)]
            semantic = [eid for eid, score in index.search(vector, limit=5)]
            native = execute_native(intent, query, store, registry, limit=5)
            graph_subjects = list(
                dict.fromkeys(
                    [
                        r["id"]
                        for r in native.bundle.direct_evidence + native.bundle.related_evidence
                    ]
                    + native.bundle.retrieval_metadata.get("selection_trace", {}).get(
                        "selected_information", []
                    )
                    + (native.plan.candidate_entity_ids if native.plan.documentary else [])
                )
            )
            # Native KG handles document targets and information-class candidates,
            # not just ExperimentalRun matches copied from an old benchmark.
            graph_ids = sorted(
                {
                    eid
                    for subject in graph_subjects
                    for eid in store.evidence(subject)
                    if eid in corpus
                }
            )
            graph_ranked = [
                r["evidence_id"]
                for r in registry.search(query, eligible_ids=sorted(set(graph_ids)), limit=5)
            ]
            contextual = [eid for eid in row["evidence_ids"] if eid in corpus][:5]
            ranks = {
                "A_lexical": lexical,
                "B_vector": semantic,
                "C_native_kg": graph_ranked,
                "D_lexical_kg": fuse(lexical, graph_ranked),
                "E_lexical_vector": fuse(lexical, semantic),
                "F_lexical_vector_kg": fuse(lexical, semantic, graph_ranked),
                "G_validated_context_candidates": fuse(lexical, semantic, contextual),
            }
            results.append(
                {
                    "id": row["id"],
                    "question": query,
                    "rankings": ranks,
                    "kg_candidate_entities": len(graph_subjects),
                    "kg_evidence_in_snapshot": len(set(graph_ids)),
                    "kg_ranking_method": "Native KG eligibility, BM25 ordering inside fixed evidence universe",
                    "empty_graph_reason": "No graph-eligible evidence in frozen representation"
                    if not graph_ids
                    else None,
                    "precision_at_5": None,
                    "recall": None,
                    "ndcg": None,
                    "independent_labels": None,
                    "H_selective_model_hybrid": "NOT_EXECUTED; no reviewed benefit gate for model reranking",
                }
            )
        status = "EXECUTED"
    except (RuntimeError, ValueError, OSError) as error:
        status = "PARTIAL"
        integrity, unchanged = None, None
        usage.append({"error_type": type(error).__name__})
    save(
        "hybrid",
        {
            "status": status,
            "corpus_ids": ids,
            "source_representations": "Original narrative, context, table-derived units and acquired report pages",
            "cases": results,
            "cache": usage,
            "provider_calls": receipts,
            "vector_integrity": integrity,
            "unchanged_sync": unchanged,
            "precision": "NOT_MEASURABLE",
            "adoption": "KEEP_EXPERIMENTAL",
            "source_text_mutated": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("stage", choices=["snapshot", "evaluate", "hybrid"])
    globals()[parser.parse_args().stage]()
