"""Fresh, bounded consolidation experiments with one frozen source universe."""

import argparse
import json
import os
import subprocess

from phase3c_consolidation import PREFIX, ROOT, digest, save


def snapshot():
    from nasa_fire_ai.evidence import EvidenceRegistry

    path = ROOT / "data/index/consolidation_snapshot_v1.sqlite"
    if path.exists():
        raise FileExistsError(path)
    target = EvidenceRegistry(path)
    original = ROOT / "artifacts/phase3c_real_context_evidence_v1.sqlite"
    target.db.execute("ATTACH DATABASE ? AS original", (f"file:{original}?mode=ro",))
    for table in (
        "sources",
        "documents",
        "passages",
        "evidence_refs",
        "document_metadata",
        "evidence_locations",
        "structured_cells",
        "semantic_staging",
    ):
        columns = [row[1] for row in target.db.execute(f"PRAGMA table_info({table})")]
        names = ",".join(columns)
        target.db.execute(f"INSERT INTO {table} ({names}) SELECT {names} FROM original.{table}")
    target.db.execute("INSERT INTO passages_fts SELECT evidence_id,text FROM passages")
    target.db.commit()
    save(
        "snapshot",
        {
            "source": str(original.relative_to(ROOT)),
            "source_sha256": digest(original),
            "registry": str(path.relative_to(ROOT)),
            "passages": target.db.execute("SELECT count(*) FROM passages").fetchone()[0],
            "embedding_cache_copied": False,
        },
    )


def evaluate():
    from phase3c_real_context import QUESTIONS, configure

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    configure()
    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    registry = ROOT / "data/index/consolidation_snapshot_v1.sqlite"
    records, pool = [], {}
    unseen = [
        ("unseen-oxygen", "Which oxygen levels were recorded in Saffire-I?"),
        ("unseen-terrestrial", "Show normal-gravity PMMA observations, including limitations."),
        (
            "unseen-comparison",
            "Compare PMMA observations across gravity conditions without inferring causation.",
        ),
    ]
    for variant in ("A", "B", "C", "D"):
        os.environ["SCIENTIFIC_SYNTHESIS_ENABLED"] = "false" if variant == "A" else "true"
        os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = (
            "true" if variant in {"C", "D"} else "false"
        )
        os.environ["MICROGRAVITY_FIRST_RETRIEVAL_ENABLED"] = "true"
        service = Phase3AssistantService(settings=Settings())
        service.registry = EvidenceRegistry(registry)
        for case_id, query in [*QUESTIONS, *unseen]:
            os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = (
                "true"
                if variant == "D" and case_id in {"default-pmma", "intervention", "real-exception"}
                else "false"
            )
            result = service.answer_query(query)
            bundle = result.evidence_bundle
            for passage in bundle.evidence_passages:
                pool[passage["evidence_id"]] = passage
            receipt = bundle.retrieval_metadata.get("scientific_synthesis", {})
            records.append(
                {
                    "variant": variant,
                    "case_id": case_id,
                    "question": query,
                    "intent": bundle.retrieval_metadata.get("query_intent_v2"),
                    "context_policy": bundle.retrieval_metadata.get("context_policy"),
                    "scientific_context": bundle.retrieval_metadata.get("scientific_context"),
                    "direct_ids": [r.get("id") for r in bundle.direct_evidence],
                    "related_ids": [r.get("id") for r in bundle.related_evidence],
                    "source_ids": [p["evidence_id"] for p in bundle.evidence_passages],
                    "citation_validity": all(
                        service.registry.resolve(p["evidence_id"]) for p in bundle.evidence_passages
                    ),
                    "synthesis": receipt,
                    "model": bundle.retrieval_metadata.get("nemotron_scientific_selection"),
                    "answer": result.rendered_answer.split("<details>", 1)[0],
                    "word_count": len(result.rendered_answer.split("<details>", 1)[0].split()),
                    "latency_ms": result.trace.latency_ms,
                    "reviewer": None,
                    "scientific_relevance": None,
                    "answer_usefulness": None,
                }
            )
            print(variant, case_id, len(receipt.get("selected_claims", [])), flush=True)
        save(
            f"answers_{variant.lower()}",
            {
                "cases": [r for r in records if r["variant"] == variant],
                "same_snapshot": True,
                "candidate_budget": 8,
                "documentary_pool_budget": 32,
            },
        )
    save("source_pool", pool)
    save(
        "comparison",
        {
            "configurations": {
                variant: {
                    "questions": len(rows := [r for r in records if r["variant"] == variant]),
                    "with_direct": sum(bool(r["direct_ids"]) for r in rows),
                    "selected_claims": sum(
                        len(r["synthesis"].get("selected_claims", [])) for r in rows
                    ),
                    "citation_valid_answers": sum(r["citation_validity"] for r in rows),
                    "mean_words": sum(r["word_count"] for r in rows) / len(rows),
                    "scientific_precision": None,
                    "independent_judgments": 0,
                }
                for variant in ("A", "B", "C", "D")
            },
            "E": "Vector retrieval evaluated separately; not adopted into native classification",
            "F": "Not enabled; incremental scientific benefit unreviewed",
        },
    )


def vectors():
    import numpy as np
    from phase3c_real_context import configure

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.semantic import project_legacy
    from nasa_fire_ai.retrieval.semantic import (
        EmbeddingCache,
        LocalVectorIndex,
        NvidiaEmbeddingProvider,
    )

    registry = EvidenceRegistry(ROOT / "data/index/consolidation_snapshot_v1.sqlite")
    units = json.loads((ROOT / "artifacts/phase3c_real_context_source_units_v8.json").read_text())[
        "units"
    ]
    groups = {}
    for row in units.values():
        if len(row["text"]) <= 10000:
            groups.setdefault(row.get("source_id"), []).append(row)
    rows = [
        group[index]
        for index in range(12)
        for _, group in sorted(groups.items())
        if index < len(group)
    ][:48]
    ids = [r["evidence_id"] for r in rows]
    cache = EmbeddingCache(registry)
    settings = Settings()
    provider = NvidiaEmbeddingProvider(
        settings.nvidia_api_key,
        settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        settings.nvidia_embedding_model,
        retries=1,
        timeout_seconds=35,
    )
    from phase3c_real_context import QUESTIONS

    questions = [
        *QUESTIONS[:10],
        ("paraphrase-extinction", "Did flames disappear when the ventilation stopped?"),
        (
            "paraphrase-material",
            "How did acrylic burning change with the diameter of the specimen?",
        ),
    ]
    configure()
    os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = "true"
    store = project_legacy(ROOT, registry)
    graph_cases = {
        variant: {
            row["case_id"]: row
            for row in json.loads(
                (ROOT / "artifacts" / f"{PREFIX}_answers_{variant}_v3.json").read_text()
            )["cases"]
        }
        for variant in ("a", "c")
    }
    receipts, outcomes = [], []
    try:
        query_vectors, hits, misses = cache.embed_cached(
            provider, [q for _, q in questions], "query", batch_size=12
        )
        receipts.append(
            {
                "role": "query",
                "historical_replay": hits,
                "fresh_inputs": misses,
                "receipt": getattr(provider, "last_receipt", {}),
            }
        )
        for representation in ("text", "section"):
            texts = [
                (r.get("section", "") + "\n" if representation == "section" else "") + r["text"]
                for r in rows
            ]
            if any(len(text) > 10000 for text in texts):
                raise ValueError("Selected source unit exceeds bounded representation budget")
            embedded, hits, misses = cache.embed_cached(provider, texts, "passage", batch_size=16)
            receipts.append(
                {
                    "representation": representation,
                    "historical_replay": hits,
                    "fresh_inputs": misses,
                    "receipt": getattr(provider, "last_receipt", {}),
                }
            )
            index = LocalVectorIndex(ROOT / "data/index/consolidation_vectors", representation)
            metadata = {
                "model": provider.model,
                "snapshot_sha256": digest(
                    ROOT / "artifacts/phase3c_real_context_source_units_v8.json"
                ),
                "representation": representation,
            }
            index.sync(dict(zip(ids, embedded)), metadata)
            unchanged = index.sync(dict(zip(ids, embedded)), metadata)
            for (case_id, query), vector in zip(questions, query_vectors):
                lexical = [
                    r["evidence_id"] for r in registry.search(query, eligible_ids=ids, limit=5)
                ]
                semantic = index.search(vector, limit=5)
                scores = {}
                for ranking in (lexical, [eid for eid, _ in semantic]):
                    for rank, eid in enumerate(ranking):
                        scores[eid] = scores.get(eid, 0) + 1 / (60 + rank + 1)
                hybrid = sorted(scores, key=lambda eid: (-scores[eid], eid))[:5]
                graph_rankings = {}
                for variant in ("a", "c"):
                    case = graph_cases[variant].get(case_id)
                    graph_rankings[variant] = sorted(
                        {
                            eid
                            for subject in (
                                (case or {}).get("direct_ids", [])
                                + (case or {}).get("related_ids", [])
                            )
                            for eid in store.evidence(subject)
                            if eid in ids
                        }
                    )[:5]

                def fuse(*rankings):
                    total = {}
                    for ranking in rankings:
                        for position, eid in enumerate(ranking):
                            total[eid] = total.get(eid, 0) + 1 / (61 + position)
                    return sorted(total, key=lambda eid: (-total[eid], eid))[:5]

                vector_ids = [eid for eid, _ in semantic]
                outcomes.append(
                    {
                        "case_id": case_id,
                        "query": query,
                        "representation": representation,
                        "lexical": lexical,
                        "vector": semantic,
                        "lexical_vector": hybrid,
                        "configurations": {
                            "A_lexical": lexical,
                            "B_vector": vector_ids,
                            "C_graph": graph_rankings["a"],
                            "D_lexical_vector": hybrid,
                            "E_lexical_graph": fuse(lexical, graph_rankings["a"]),
                            "F_lexical_vector_graph": fuse(
                                lexical, vector_ids, graph_rankings["a"]
                            ),
                            "G_verified_context_hybrid": fuse(
                                lexical, vector_ids, graph_rankings["c"]
                            ),
                        },
                        "graph_paraphrase_cases": "NOT_RUN"
                        if case_id not in graph_cases["a"]
                        else "EXECUTED_NATIVE_V2",
                        "independent_relevance": None,
                        "precision_at_5": None,
                        "unchanged_sync": unchanged,
                    }
                )
            assert np.isfinite(np.load(index.vectors_path)).all()
        save(
            "vector_pilot",
            {
                "status": "EXECUTED",
                "corpus_ids": ids,
                "representations": ["text", "section"],
                "receipts": receipts,
                "cases": outcomes,
                "adoption": "INCONCLUSIVE; no independent relevance labels",
                "raw_text_modified": False,
            },
        )
    except (RuntimeError, ValueError) as error:
        save(
            "vector_pilot",
            {
                "status": "PARTIAL",
                "error_type": type(error).__name__,
                "receipts": receipts,
                "cases": outcomes,
                "scientific_precision": None,
                "adoption": "INCONCLUSIVE",
            },
        )


def quality():
    from phase3c_real_context import configure
    from pyshacl import validate
    from rdflib import Graph

    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.autonomous import registry_checks
    from nasa_fire_ai.ingestion.semantic import project_legacy
    from nasa_fire_ai.query.native import NS

    receipts = []
    for label, command in (
        ("format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("pytest", ["uv", "run", "pytest", "-q"]),
    ):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        path = ROOT / "artifacts" / f"{PREFIX}_{label}_{phase3c_consolidation.RECEIPT_VERSION}.txt"
        with path.open("x") as stream:
            stream.write(result.stdout + result.stderr)
        receipts.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "execution": "FRESH_LOCAL_EXECUTION",
                "log": str(path.relative_to(ROOT)),
                "sha256": digest(path),
            }
        )
        print(label, result.returncode, flush=True)
    configure()
    os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = "true"
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, registry)
    shapes = {}
    for label, graph, shape in (
        ("canonical", Graph().parse(ROOT / "data/canonical/graph.ttl"), "shapes.ttl"),
        ("native", store.graph, "semantic_shapes.ttl"),
        ("taxonomy", store.graph, "semantic_taxonomy_shapes.ttl"),
    ):
        conforms, _, report = validate(graph, shacl_graph=str(ROOT / "ontology" / shape))
        shapes[label] = {"conforms": bool(conforms), "report": report, "execution": "FRESH_SHACL"}
        print(label, conforms, flush=True)
    frozen = json.loads((ROOT / "artifacts" / f"{PREFIX}_freeze_v1.json").read_text())["files"]
    changed = [
        relative
        for relative, expected in frozen.items()
        if not (ROOT / relative).exists() or digest(ROOT / relative) != expected
    ]
    missing_refs = sorted(
        {
            str(eid)
            for eid in store.graph.objects(None, NS.evidenceRef)
            if not registry.resolve(str(eid))
        }
    )
    save(
        "quality",
        {
            "commands": receipts,
            "shacl": shapes,
            "registry": registry_checks(registry),
            "frozen_files": len(frozen),
            "historical_changes": changed,
            "graph_missing_evidence": missing_refs,
            "independent_review": None,
        },
    )


if __name__ == "__main__":
    import phase3c_consolidation

    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["snapshot", "evaluate", "vectors", "quality"])
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()
    phase3c_consolidation.RECEIPT_VERSION = args.version
    globals()[args.operation]()
