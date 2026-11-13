#!/usr/bin/env python3
"""Deterministic PSI-98 RDF graph query demonstration; no inference layer."""

import json
from pathlib import Path

from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parents[1]
FS = Namespace("https://example.org/nasa-fire-safety#")
graph = Graph().parse(ROOT / "data/canonical/graph.ttl", format="turtle")


def run_id(node):
    return str(node).removeprefix(str(FS))


def condition_value(run, kind, predicate=FS.reportedValue):
    for condition in graph.objects(run, FS.hasCondition):
        if str(graph.value(condition, FS.conditionType)) == kind:
            value = graph.value(condition, predicate)
            return value.toPython() if value is not None else None
    return None


saffire = sorted(graph.objects(FS["psi-98"], FS.hasRun), key=run_id)
sibal = [
    run
    for run in saffire
    if str(graph.value(graph.value(run, FS.usesSample), FS.madeOf)).endswith(
        "material-sibal-fabric"
    )
]
airflow = [
    run for run in saffire if condition_value(run, "flow_velocity", FS.canonicalValue) <= 0.20
]
s1, s2 = FS["psi-98-S1"], FS["psi-98-S2"]
print(
    json.dumps(
        {
            "all_saffire_i": [run_id(run) for run in saffire],
            "sibal_fabric": [run_id(run) for run in sibal],
            "airflow_lte_0_20_m_s": [run_id(run) for run in airflow],
            "compare_s1_s2": {
                "equal": {
                    "material": "SIBAL Fabric",
                    "gravity": condition_value(s1, "gravity"),
                    "flow_velocity_m_s": condition_value(s1, "flow_velocity", FS.canonicalValue),
                },
                "different": {
                    "flow_direction": {
                        "S1": condition_value(s1, "flow_direction"),
                        "S2": condition_value(s2, "flow_direction"),
                    },
                    "burn_time_s": {
                        "S1": condition_value(s1, "burn_time", FS.canonicalValue),
                        "S2": condition_value(s2, "burn_time", FS.canonicalValue),
                    },
                    "oxygen_reported": {
                        "S1": condition_value(s1, "oxygen"),
                        "S2": condition_value(s2, "oxygen"),
                    },
                },
            },
        },
        indent=2,
    )
)
