from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Resolution:
    status: str
    canonical_ids: list[str]
    matched_alias: str | None = None


def load_lexicon():
    return yaml.safe_load((ROOT / "domain/lexicon.yaml").read_text())["concepts"]


def resolve(text: str) -> list[Resolution]:
    lower = text.lower()
    data = load_lexicon()
    results = []
    for alias, ids in (
        yaml.safe_load((ROOT / "domain/lexicon.yaml").read_text())
        .get("ambiguous_aliases", {})
        .items()
    ):
        if alias in lower:
            results.append(Resolution("ambiguous", ids, alias))
    for item in data:
        for alias in item["aliases"] + item.get("abbreviations", []):
            if alias.lower() in lower:
                results.append(Resolution("resolved", [item["canonical_id"]], alias))
                break
    return results or [Resolution("unknown", [])]
