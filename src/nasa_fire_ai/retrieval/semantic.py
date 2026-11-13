"""Phase-2 semantic retrieval primitives.

Vectors propose candidates and rank documentary evidence; they never establish
scientific identity, DIRECT/RELATED status, or ontology facts.
"""

import hashlib
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
import numpy as np

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.models import DiscoveryCandidate, SemanticResolutionResult
from nasa_fire_ai.query.lexicon import load_lexicon, resolve

PREPROCESSING_VERSION = "phase2-v1"


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def model_identity(self) -> str: ...

    @abstractmethod
    def dimensions(self) -> int | None: ...


@dataclass
class NvidiaEmbeddingProvider(EmbeddingProvider):
    api_key: str | None
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "nvidia/nemotron-3-embed-1b"
    retries: int = 3
    timeout_seconds: float = 90
    _dimension: int | None = None

    def model_identity(self) -> str:
        return self.model

    def dimensions(self) -> int | None:
        return self._dimension

    def _embed(
        self, texts: list[str], input_type: Literal["query", "passage"]
    ) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured")
        payload = {
            "model": self.model,
            "input": texts,
            "input_type": input_type,
            "encoding_format": "float",
            "truncate": "NONE",
        }
        last_error = None
        for attempt in range(self.retries):
            try:
                response = httpx.post(
                    self.base_url.rstrip("/") + "/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    time.sleep(2**attempt)
                    last_error = RuntimeError(f"NVIDIA embedding HTTP {response.status_code}")
                    continue
                response.raise_for_status()
                result = response.json()
                self.last_receipt = {
                    "execution": "FRESH_INFERENCE",
                    "model": self.model,
                    "input_role": input_type,
                    "inputs": len(texts),
                    "usage": result.get("usage"),
                    "http_status": response.status_code,
                }
                data = result.get("data", [])
                vectors = [
                    item["embedding"] for item in sorted(data, key=lambda item: item["index"])
                ]
                if len(vectors) != len(texts):
                    raise RuntimeError("embedding response length mismatch")
                self._dimension = len(vectors[0]) if vectors else self._dimension
                return vectors
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(2**attempt)
        raise RuntimeError("NVIDIA embedding request failed") from last_error

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "query")

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "passage")


def content_key(model: str, role: str, text: str, version: str = PREPROCESSING_VERSION) -> str:
    return hashlib.sha256(f"{model}|{role}|{version}|{text}".encode()).hexdigest()


def embedding_segments(text: str, limit_chars: int = 2800) -> list[str]:
    """Preserve all passage content for embedding by deterministic subsegmenting.

    The NVIDIA token limit cannot be estimated safely from character count for
    scientific symbols.  Each subsegment is embedded and averaged; the stored
    evidence passage itself remains complete and unchanged.
    """
    if len(text) <= limit_chars:
        return [text]
    return [text[start : start + limit_chars] for start in range(0, len(text), limit_chars)]


class EmbeddingCache:
    def __init__(self, registry: EvidenceRegistry):
        self.db = registry.db
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS embedding_cache(
            cache_key TEXT PRIMARY KEY, model_id TEXT, input_role TEXT,
            content_checksum TEXT, preprocessing_version TEXT, vector_json TEXT,
            dimension INTEGER, created_at TEXT)"""
        )
        self.db.commit()

    def get(self, model: str, role: str, text: str) -> list[float] | None:
        row = self.db.execute(
            "SELECT vector_json FROM embedding_cache WHERE cache_key=?",
            (content_key(model, role, text),),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, model: str, role: str, text: str, vector: list[float]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO embedding_cache VALUES (?,?,?,?,?,?,?,datetime('now'))",
            (
                content_key(model, role, text),
                model,
                role,
                hashlib.sha256(text.encode()).hexdigest(),
                PREPROCESSING_VERSION,
                json.dumps(vector),
                len(vector),
            ),
        )
        self.db.commit()

    def embed_cached(
        self,
        provider: EmbeddingProvider,
        texts: list[str],
        role: Literal["query", "passage"],
        batch_size: int = 32,
    ) -> tuple[list[list[float]], int, int]:
        vectors: list[list[float] | None] = [
            self.get(provider.model_identity(), role, text) for text in texts
        ]
        missing = [i for i, vector in enumerate(vectors) if vector is None]
        for start in range(0, len(missing), batch_size):
            indexes = missing[start : start + batch_size]
            segments = [
                embedding_segments(texts[index]) if role == "passage" else [texts[index]]
                for index in indexes
            ]
            flat = [part for parts in segments for part in parts]
            generated = (
                provider.embed_queries(flat) if role == "query" else provider.embed_passages(flat)
            )
            cursor = 0
            for index, parts in zip(indexes, segments):
                vector = (
                    np.asarray(generated[cursor : cursor + len(parts)], dtype=np.float32)
                    .mean(axis=0)
                    .tolist()
                )
                cursor += len(parts)
                self.put(provider.model_identity(), role, texts[index], vector)
                vectors[index] = vector
        return (
            [vector for vector in vectors if vector is not None],
            len(texts) - len(missing),
            len(missing),
        )


@dataclass
class LocalVectorIndex:
    root: Path
    index_id: str

    def _manifest(self):
        return json.loads(self.metadata_path.read_text()) if self.metadata_path.exists() else {}

    def _generation_path(self, kind, manifest):
        name = manifest.get(f"{kind}_file", f"{self.index_id}.{kind}.npy")
        if Path(name).name != name:
            raise ValueError("Vector generation paths must stay within index directory")
        return self.root / name

    @property
    def vectors_path(self) -> Path:
        return self._generation_path("vectors", self._manifest())

    @property
    def ids_path(self) -> Path:
        return self._generation_path("ids", self._manifest())

    @property
    def metadata_path(self) -> Path:
        return self.root / f"{self.index_id}.metadata.json"

    def write(self, ids: list[str], vectors: list[list[float]], metadata: dict) -> None:
        """Publish complete immutable generations via an atomic manifest swap.

        Previous generations remain available for rollback and concurrent readers.
        Interrupted preparation cannot change the current manifest.
        """
        if len(ids) != len(vectors) or len(set(ids)) != len(ids):
            raise ValueError("Vector identity/length mismatch")
        self.root.mkdir(parents=True, exist_ok=True)
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.size:
            if (
                matrix.ndim != 2
                or not np.isfinite(matrix).all()
                or (np.linalg.norm(matrix, axis=1) == 0).any()
            ):
                raise ValueError("Invalid embedding matrix")
            matrix /= np.linalg.norm(matrix, axis=1, keepdims=True).clip(min=1e-12)
        generation = uuid.uuid4().hex
        vectors_file = f"{self.index_id}.{generation}.vectors.npy"
        ids_file = f"{self.index_id}.{generation}.ids.npy"
        for name, array in [(vectors_file, matrix), (ids_file, np.asarray(ids, dtype=str))]:
            with (self.root / name).open("xb") as stream:
                np.save(stream, array)
                stream.flush()
                os.fsync(stream.fileno())
        temporary = self.root / f".{self.index_id}.{generation}.manifest.tmp"
        value = {
            **metadata,
            "generation": generation,
            "vectors_file": vectors_file,
            "ids_file": ids_file,
            "number_of_vectors": len(ids),
            "embedding_dimension": int(matrix.shape[1])
            if matrix.ndim == 2 and len(matrix)
            else None,
        }
        with temporary.open("x") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.metadata_path)
        # Windows cannot open a directory for fsync; os.replace is already atomic there.
        if os.name != "nt":
            descriptor = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def sync(self, vectors_by_id: dict[str, list[float]], metadata: dict) -> dict[str, int]:
        """Update changed/new IDs and remove stale IDs without new embeddings for unchanged text."""
        manifest = self._manifest()
        ids_path = self._generation_path("ids", manifest)
        vectors_path = self._generation_path("vectors", manifest)
        old_ids = list(np.load(ids_path)) if ids_path.exists() else []
        old_vectors = np.load(vectors_path) if vectors_path.exists() else np.empty((0, 0))
        retained = {
            str(eid): old_vectors[i].tolist()
            for i, eid in enumerate(old_ids)
            if str(eid) in vectors_by_id
        }

        def normalized(vector: list[float]) -> np.ndarray:
            value = np.asarray(vector, dtype=np.float32)
            return value / max(float(np.linalg.norm(value)), 1e-12)

        changed = sum(
            1
            for eid, vector in vectors_by_id.items()
            if eid not in retained or not np.allclose(retained[eid], normalized(vector))
        )
        stale = len(old_ids) - len(retained)
        existing_metadata = (
            json.loads(self.metadata_path.read_text()) if self.metadata_path.exists() else {}
        )
        metadata_changed = any(
            existing_metadata.get(key) != value for key, value in metadata.items()
        )
        if changed or stale or metadata_changed or not self.metadata_path.exists():
            self.write(list(vectors_by_id), [vectors_by_id[eid] for eid in vectors_by_id], metadata)
        return {
            "new_or_changed": changed,
            "stale_removed": stale,
            "unchanged": len(vectors_by_id) - changed,
        }

    def search(
        self, query_vector: list[float], limit: int = 10, eligible_ids: set[str] | None = None
    ) -> list[tuple[str, float]]:
        manifest = self._manifest()
        vectors = np.load(self._generation_path("vectors", manifest))
        ids = np.load(self._generation_path("ids", manifest))
        q = np.asarray(query_vector, dtype=np.float32)
        q /= max(float(np.linalg.norm(q)), 1e-12)
        scores = vectors @ q
        rows = [
            (str(ids[i]), float(scores[i]))
            for i in np.argsort(scores)[::-1]
            if eligible_ids is None or str(ids[i]) in eligible_ids
        ]
        return rows[:limit]


def semantic_resolve(
    term: str,
    concept_index: LocalVectorIndex,
    provider: EmbeddingProvider,
    cache: EmbeddingCache,
    limit: int = 5,
) -> SemanticResolutionResult:
    exact = resolve(term)
    if exact[0].status == "resolved":
        return SemanticResolutionResult(
            status="RESOLVED_SAFE_ALIAS",
            query_term=term,
            canonical_ids=exact[0].canonical_ids,
            reason="controlled canonical label or safe alias",
        )
    if exact[0].status == "ambiguous":
        return SemanticResolutionResult(
            status="AMBIGUOUS",
            query_term=term,
            canonical_ids=exact[0].canonical_ids,
            reason="controlled ambiguous alias",
        )
    vector, _, _ = cache.embed_cached(provider, [term], "query")
    candidates = [
        {"canonical_id": cid, "semantic_similarity_score": score}
        for cid, score in concept_index.search(vector[0], limit)
    ]
    return SemanticResolutionResult(
        status="SEMANTIC_CANDIDATE" if candidates else "UNKNOWN",
        query_term=term,
        candidates=candidates,
        reason="embedding retrieval candidate; identity remains unvalidated",
    )


def concept_texts() -> list[dict]:
    """Approved controlled vocabulary only; no corpus-derived definitions."""
    return [
        {
            "id": item["canonical_id"],
            "text": "; ".join(
                [
                    item["canonical_label"],
                    *item["aliases"],
                    *item.get("abbreviations", []),
                    item.get("notes", ""),
                ]
            ),
            "category": item["category"],
        }
        for item in load_lexicon()
    ]


def rrf(bm25_ids: list[str], vector_ids: list[str], k: int = 60) -> list[dict]:
    scores: dict[str, dict] = {}
    for method, ids in (("bm25", bm25_ids), ("vector", vector_ids)):
        for rank, evidence_id in enumerate(ids, 1):
            item = scores.setdefault(
                evidence_id,
                {
                    "evidence_id": evidence_id,
                    "bm25_rank": None,
                    "vector_rank": None,
                    "rrf_score": 0.0,
                },
            )
            item[f"{method}_rank"] = rank
            item["rrf_score"] += 1 / (k + rank)
    return sorted(scores.values(), key=lambda item: (-item["rrf_score"], item["evidence_id"]))


def discovery_candidates(
    query: str, ranked: list[dict], registry: EvidenceRegistry, excluded: set[str]
) -> list[DiscoveryCandidate]:
    result = []
    for rank, item in enumerate(ranked, 1):
        if item["evidence_id"] in excluded:
            continue
        passage = registry.resolve(item["evidence_id"])
        if not passage:
            continue
        source = registry.db.execute(
            "SELECT source_id FROM documents WHERE document_id=?", (passage["document_id"],)
        ).fetchone()
        result.append(
            DiscoveryCandidate(
                candidate_id=f"discovery-{item['evidence_id']}",
                query=query,
                evidence_id=item["evidence_id"],
                source_id=source[0] if source else "unknown",
                document_id=passage["document_id"],
                page=passage["page"],
                section=passage["section"],
                passage=passage["text"],
                vector_score=item.get("vector_score"),
                bm25_rank=item.get("bm25_rank"),
                bm25_score=item.get("bm25_score"),
                hybrid_rank=rank,
                reason_for_discovery="Retrieved as a semantically/documentarily relevant candidate; no structured relation was inferred.",
            )
        )
    return result
