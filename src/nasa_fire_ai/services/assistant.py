from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.models import QueryIntent
from nasa_fire_ai.query import classify_runs


def answer(intent: QueryIntent, runs: list[dict], registry: EvidenceRegistry, query: str):
    direct, related = classify_runs(intent, runs)
    eligible = [e for m in direct for e in m.run.get("evidence_ids", [])]
    return {
        "status": "DIRECT" if direct else "RELATED" if related else "NO_DIRECT_EVIDENCE",
        "direct": direct,
        "related": related,
        "passages": registry.search(query, eligible or None),
        "llm_synthesis": "disabled unless OPENAI_API_KEY is configured",
    }
