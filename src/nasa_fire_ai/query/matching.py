from dataclasses import dataclass

from nasa_fire_ai.models import QueryIntent


@dataclass
class Match:
    run: dict
    matches: list[str]
    differs: list[str]
    unknown: list[str]


def _cmp(value, op, target):
    return {
        "<": value < target,
        "<=": value <= target,
        "=": value == target,
        ">=": value >= target,
        ">": value > target,
    }[op]


def classify_runs(intent: QueryIntent, runs: list[dict]) -> tuple[list[Match], list[Match]]:
    direct = []
    related = []
    for run in runs:
        matches = []
        differs = []
        for material in intent.materials:
            (matches if run.get("material", "").lower() == material.lower() else differs).append(
                f"material = {material}"
                if run.get("material", "").lower() == material.lower()
                else f"requested material = {material}; experiment = {run.get('material')}"
            )
        for g in intent.gravity_conditions:
            (matches if run.get("gravity", "").lower() == g.lower() else differs).append(
                f"gravity = {g}"
                if run.get("gravity", "").lower() == g.lower()
                else f"requested gravity = {g}; experiment = {run.get('gravity')}"
            )
        if intent.oxygen:
            target = intent.oxygen.value / (100 if intent.oxygen.unit == "%" else 1)
            actual = run.get("oxygen_fraction")
            ok = actual is not None and _cmp(actual, intent.oxygen.operator, target)
            (matches if ok else differs).append(
                f"oxygen {intent.oxygen.operator} {intent.oxygen.value}{intent.oxygen.unit or ''}"
                if ok
                else f"requested O2 {intent.oxygen.operator} {intent.oxygen.value}{intent.oxygen.unit or ''}; experiment = {actual}"
            )
        unknown = []
        if intent.flow_velocity:
            actual = run.get("flow_velocity_m_s")
            target = intent.flow_velocity.value * (
                0.01 if intent.flow_velocity.unit == "cm/s" else 1
            )
            if actual is None:
                unknown.append("flow velocity unavailable")
            elif _cmp(actual, intent.flow_velocity.operator, target):
                matches.append(
                    f"flow velocity {intent.flow_velocity.operator} {intent.flow_velocity.value}{intent.flow_velocity.unit or ''}"
                )
            else:
                differs.append(
                    f"requested flow {intent.flow_velocity.operator} {intent.flow_velocity.value}{intent.flow_velocity.unit or ''}; experiment = {actual} m/s"
                )
        if intent.flow_direction:
            actual = run.get("flow_direction")
            if actual is None:
                unknown.append("flow direction unavailable")
            elif actual.lower() == intent.flow_direction.lower():
                matches.append(f"flow direction = {intent.flow_direction}")
            else:
                differs.append(
                    f"requested flow direction = {intent.flow_direction}; experiment = {actual}"
                )
        item = Match(run, matches, differs, unknown)
        if not differs:
            direct.append(item)
        elif matches:
            related.append(item)
    return direct, related
