"""Versioned consolidation receipts. Never overwrite historical evaluations."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
PREFIX = "phase3c_consolidation"
RECEIPT_VERSION = "v1"


def digest(path):
    with path.open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256")
    return value.hexdigest()


def save(name, payload):
    path = ROOT / "artifacts" / f"{PREFIX}_{name}_{RECEIPT_VERSION}.json"
    with path.open("x") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False, default=str)
        stream.write("\n")
    return path


def freeze():
    files = {
        str(path.relative_to(ROOT)): digest(path)
        for folder in ("data/raw", "data/canonical", "evals", "artifacts", "ontology", "domain")
        for path in (ROOT / folder).rglob("*")
        if path.is_file() and "__pycache__" not in str(path)
    }
    save(
        "freeze",
        {
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "files": files,
        },
    )
    print(f"Frozen {len(files)} existing files; no full SQLite/vector cache copy required.")


def baseline():
    import yaml

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["SCIENTIFIC_SYNTHESIS_ENABLED"] = "false"
    for flag in (
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED",
        "RELATIONAL_RELATED_RETRIEVAL_ENABLED",
        "NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
    ):
        os.environ[flag] = "true"
    from phase3c_real_context import QUESTIONS

    service = Phase3AssistantService(settings=Settings())
    records = []
    for case_id, query in QUESTIONS:
        result = service.answer_query(query)
        # Actual public service response; full sources remain in the registry.
        records.append(
            {
                "case_id": case_id,
                "question": query,
                "response": result.model_dump(mode="json")
                if hasattr(result, "model_dump")
                else str(result),
            }
        )
        print(case_id, flush=True)
    save(
        "baseline_answers",
        {
            "cases": records,
            "independent_review": None,
            "query_language": yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text()),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["freeze", "baseline"])
    args = parser.parse_args()
    globals()[args.operation]()
