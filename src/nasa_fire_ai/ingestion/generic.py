"""Source-independent table profiling and semantic staging; never publishes science."""

import re
from dataclasses import dataclass

from nasa_fire_ai.query.v2 import SemanticRegistry


@dataclass(frozen=True)
class ColumnProfile:
    label: str
    normalized_label: str
    raw_unit: str | None
    datatype: str
    nullable: bool
    samples: list[str]


@dataclass(frozen=True)
class SemanticResolution:
    raw_label: str
    status: str
    property_id: str | None
    raw_unit: str | None
    datatype: str


def propose_table_role(profiles: list[ColumnProfile]) -> dict:
    """Advisory structural role only: no header proves an executed experiment."""
    labels = {p.normalized_label for p in profiles}
    hints = {
        "Publication": {"doi", "publication", "title", "authors"},
        "MaterialInventory": {"material", "quantity", "inventory"},
        "ExperimentalDesign": {"planned", "design", "configuration"},
        "ExperimentalRun": {"run", "run id", "experiment id"},
    }
    roles = [role for role, terms in hints.items() if labels.intersection(terms)]
    return {
        "proposed_role": roles[0] if len(roles) == 1 else "UnresolvedTable",
        "authority": "UNREVIEWED_STRUCTURAL_HINT",
        "canonical": False,
    }


def documentary_row(row: dict[str, str]) -> list[str]:
    """Explicit non-execution labels only; blank cells and identifiers prove no role.

    Return the original cells establishing a documentary/planned exception.
    Absence of an exception does not establish that a run was performed.
    """
    return [
        value
        for value in row.values()
        if re.search(
            r"\b(?:pre[- ]test\s+flow\s+vis\w*\s+data|planned\s+(?:run|test)|"
            r"(?:run|test)\s+(?:not\s+(?:performed|conducted)|cancelled|canceled)|"
            r"documentary\s+(?:row|record))\b",
            str(value),
            re.IGNORECASE,
        )
    ]


def resolve_column(profile: ColumnProfile, registry: SemanticRegistry) -> SemanticResolution:
    """Registry-only semantic proposal; unknowns deliberately remain unresolved."""
    status, property_id = registry.resolve_property(profile.normalized_label, profile.raw_unit)
    return SemanticResolution(
        profile.label, status, property_id, profile.raw_unit, profile.datatype
    )


def profile_table(rows: list[dict[str, str]], sample_size: int = 5) -> list[ColumnProfile]:
    headers = list(rows[0]) if rows else []
    profiles = []
    for header in headers:
        values = [str(row.get(header, "")).strip() for row in rows]
        nonempty = [x for x in values if x]
        unit = re.search(r"\(([^)]+)\)", header)
        numeric = nonempty and all(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", x) for x in nonempty)
        ranged = nonempty and all(
            re.fullmatch(r"[-+]?\d+(?:\.\d+)?\s*[-–]\s*[-+]?\d+(?:\.\d+)?", x) for x in nonempty
        )
        label_without_unit = re.sub(r"\([^)]*\)", "", header)
        profiles.append(
            ColumnProfile(
                header,
                re.sub(r"[^a-z0-9]+", " ", label_without_unit.lower()).strip(),
                unit.group(1) if unit else None,
                "numeric" if numeric else "range" if ranged else "categorical",
                len(nonempty) != len(values),
                nonempty[:sample_size],
            )
        )
    return profiles
