"""Conservative conversion of PSI experimental-table rows to canonical records."""

import hashlib
import re
from pathlib import Path

from nasa_fire_ai.models import (
    ConditionRecord,
    EvidenceReference,
    ExperimentalRunRecord,
    SampleRecord,
)
from nasa_fire_ai.normalization import normalize


def _evidence(row_id: str) -> list[EvidenceReference]:
    return [
        EvidenceReference(
            evidence_id=f"E-psi-98-table-{row_id}", source_id="psi-98", section="Experimental table"
        )
    ]


def _number(text: str) -> float:
    return float(text.strip())


def oxygen_condition(row_id: str, reported: str) -> ConditionRecord:
    clean = reported.replace("~", "").strip()
    values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", clean)]
    if "-" in clean and len(values) == 2:
        low, high = values
        low_normalized, unit = normalize(low, "%")
        high_normalized, _ = normalize(high, "%")
        return ConditionRecord(
            kind="oxygen",
            reported_value=reported,
            reported_unit="%",
            canonical_unit=unit,
            reported_lower_value=low,
            reported_upper_value=high,
            canonical_lower_value=low_normalized,
            canonical_upper_value=high_normalized,
            evidence_refs=_evidence(row_id),
        )
    value = values[0]
    normalized, unit = normalize(value, "%")
    return ConditionRecord(
        kind="oxygen",
        reported_value=reported,
        reported_unit="%",
        canonical_value=normalized,
        canonical_unit=unit,
        is_approximate="~" in reported,
        evidence_refs=_evidence(row_id),
    )


def _condition(row_id: str, kind: str, reported: str, unit: str) -> ConditionRecord:
    value = _number(reported)
    normalized, canonical_unit = normalize(value, unit)
    return ConditionRecord(
        kind=kind,
        reported_value=value,
        reported_unit=unit,
        canonical_value=normalized,
        canonical_unit=canonical_unit,
        evidence_refs=_evidence(row_id),
    )


def canonicalize_psi98(rows: list[dict[str, str]], raw_file: Path) -> tuple[list[dict], list[dict]]:
    """Returns serializable canonical entities and compact matching-run projections."""
    entities: list[dict] = []
    runs: list[dict] = []
    for row in rows:
        run_id = row.get("Sample Number", "")
        # PSI table also contains camera/pre-test rows; they are not experimental samples.
        if run_id not in {"S1", "S2"} or not row.get("Material"):
            continue
        evidence = _evidence(run_id)
        sample = SampleRecord(
            id=f"psi-98-{run_id}-sample",
            material=row["Material"],
            geometry="rectangular fabric sheet",
            evidence_refs=evidence,
        )
        conditions = [
            _condition(run_id, "sample_thickness", row["Sample Thickness (cm)"], "cm"),
            _condition(run_id, "sample_length", row["Sample Length (cm)"], "cm"),
            _condition(run_id, "sample_width", row["Sample Width (cm)"], "cm"),
            _condition(run_id, "flow_velocity", row["Air Flow (cm/s)"], "cm/s"),
            oxygen_condition(run_id, row["Percent O2"]),
            _condition(run_id, "ignition_power", row["Ignition Power (W)"], "W"),
            _condition(run_id, "ignition_time", row["Ignition Time (s)"], "s"),
            _condition(run_id, "burn_time", row["Burn Time (s)"], "s"),
            ConditionRecord(
                kind="flow_direction", reported_value=row["Flow Direction"], evidence_refs=evidence
            ),
            ConditionRecord(kind="gravity", reported_value="microgravity", evidence_refs=evidence),
        ]
        run = ExperimentalRunRecord(
            id=f"psi-98-{run_id}",
            investigation_id="psi-98",
            sample_id=sample.id,
            condition_ids=[f"psi-98-{run_id}-{condition.kind}" for condition in conditions],
            evidence_refs=evidence,
        )
        entities.extend(
            [
                {"type": "SampleRecord", **sample.model_dump(mode="json")},
                {"type": "ExperimentalRunRecord", **run.model_dump(mode="json")},
                *[
                    {
                        "type": "ConditionRecord",
                        "id": f"psi-98-{run_id}-{condition.kind}",
                        **condition.model_dump(mode="json"),
                    }
                    for condition in conditions
                ],
            ]
        )
        runs.append(
            {
                "id": run.id,
                "material": row["Material"],
                "gravity": "microgravity",
                "oxygen_fraction": conditions[4].canonical_value,
                "oxygen_range_fraction": [
                    conditions[4].canonical_lower_value,
                    conditions[4].canonical_upper_value,
                ],
                "flow_velocity_m_s": conditions[3].canonical_value,
                "flow_direction": row["Flow Direction"],
                "burn_time_s": float(row["Burn Time (s)"]),
                "evidence_ids": [evidence[0].evidence_id],
            }
        )
    return entities, runs


def table_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonicalize_psi25_b1(rows: list[dict[str, str]]) -> tuple[list[dict], list[dict]]:
    """Ingest one clean, source-table row; complex multi-stage BASS rows remain untouched."""
    row = next((item for item in rows if item.get("Test #") == "B1"), None)
    if row is None:
        return [], []
    evidence = [
        EvidenceReference(
            evidence_id="E-psi-25-table-B1", source_id="psi-25", section="Experimental table"
        )
    ]
    sample = SampleRecord(
        id="psi-25-B1-sample", material=row["Fuel Sample Material"], evidence_refs=evidence
    )
    conditions = [
        ConditionRecord(kind="gmt", reported_value=float(row["GMT"]), evidence_refs=evidence),
        ConditionRecord(
            kind="flow_restrictor",
            reported_value=float(row["Flow restrictor"]),
            evidence_refs=evidence,
        ),
        ConditionRecord(
            kind="fan_display", reported_value=float(row["Fan display"]), evidence_refs=evidence
        ),
        ConditionRecord(
            kind="air_display", reported_value=float(row["Air display"]), evidence_refs=evidence
        ),
        ConditionRecord(
            kind="initial_oxygen",
            reported_value=float(row["Calibrated  initial O2 % by vol"]),
            reported_unit="%",
            canonical_value=normalize(float(row["Calibrated  initial O2 % by vol"]), "%")[0],
            canonical_unit="fraction",
            evidence_refs=evidence,
        ),
        ConditionRecord(
            kind="final_oxygen",
            reported_value=float(row["Calibrated final O2 % by vol"]),
            reported_unit="%",
            canonical_value=normalize(float(row["Calibrated final O2 % by vol"]), "%")[0],
            canonical_unit="fraction",
            evidence_refs=evidence,
        ),
        ConditionRecord(
            kind="total_frames_shot",
            reported_value=float(row["Total Frames Shot"]),
            evidence_refs=evidence,
        ),
    ]
    run = ExperimentalRunRecord(
        id="psi-25-B1",
        investigation_id="psi-25",
        sample_id=sample.id,
        condition_ids=[f"psi-25-B1-{item.kind}" for item in conditions],
        evidence_refs=evidence,
    )
    entities = [
        {"type": "SampleRecord", **sample.model_dump(mode="json")},
        {"type": "ExperimentalRunRecord", **run.model_dump(mode="json")},
        *[
            {
                "type": "ConditionRecord",
                "id": f"psi-25-B1-{item.kind}",
                **item.model_dump(mode="json"),
            }
            for item in conditions
        ],
    ]
    return entities, [
        {"id": run.id, "material": sample.material, "evidence_ids": ["E-psi-25-table-B1"]}
    ]
