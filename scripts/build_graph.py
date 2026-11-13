#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, Graph, Literal, Namespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
FS = Namespace("https://example.org/nasa-fire-safety#")
g = Graph()
g.parse(ROOT / "ontology/fire_safety.ttl", format="turtle")
records = json.loads((ROOT / "data/canonical/records.json").read_text())
classes = {
    "InvestigationRecord": FS.Investigation,
    "nasa_conclusion": FS.NASAConclusion,
    "guidance": FS.Guidance,
    "open_question": FS.NASAIdentifiedOpenQuestion,
    "NASAStandard": FS.NASAStandard,
    "ExperimentalRunRecord": FS.ExperimentalRun,
    "SampleRecord": FS.Sample,
    "ConditionRecord": FS.ExperimentalCondition,
    "InterventionRecord": FS.Intervention,
    "ObservationRecord": FS.Observation,
    "MeasurementObservationRecord": FS.MeasurementObservation,
    "ReportedExperimentalObservationRecord": FS.ReportedExperimentalObservation,
}
for r in records:
    node = FS[r.get("id", r.get("statement_id"))]
    g.add((node, RDF.type, classes.get(r["type"], FS.Publication)))
    for e in r["evidence_refs"]:
        g.add((node, FS.evidenceRef, Literal(e["evidence_id"])))
    if "title" in r:
        g.add((node, FS.title, Literal(r["title"])))
    if "text" in r:
        g.add((node, FS.text, Literal(r["text"])))
    if "description" in r:
        g.add((node, FS.text, Literal(r["description"])))
    if r["type"] == "SafetyStatementRecord":
        statement_classes = {
            "nasa_conclusion": FS.NASAConclusion,
            "safety_implication": FS.SafetyImplication,
            "requirement": FS.Requirement,
            "guidance": FS.Guidance,
            "design_criterion": FS.DesignCriterion,
            "test_criterion": FS.TestCriterion,
            "open_question": FS.NASAIdentifiedOpenQuestion,
        }
        g.remove((node, RDF.type, FS.Publication))
        g.add((node, RDF.type, statement_classes[r["statement_type"]]))
        g.add((node, FS.text, Literal(r["normalized_text"])))
        g.add((node, FS.reportedBy, FS[r["source_document"]]))
        if r.get("scope_applicability"):
            g.add((node, FS.scopeApplicability, Literal(r["scope_applicability"])))
        if r.get("investigation_id"):
            g.add((node, FS.concerns, FS[r["investigation_id"]]))
    elif r["type"] in {"InterventionRecord", "ObservationRecord"}:
        if r.get("investigation_id"):
            predicate = (
                FS.hasIntervention if r["type"] == "InterventionRecord" else FS.hasObservation
            )
            g.add((FS[r["investigation_id"]], predicate, node))
        if r.get("source_document"):
            g.add((node, FS.reportedBy, FS[r["source_document"]]))
    if r["type"] == "SampleRecord":
        # Raw reported material labels can contain quotes/slashes. Keep the
        # original label in canonical JSON; use a deterministic safe RDF local name.
        material = FS["material-" + re.sub(r"[^a-z0-9]+", "-", r["material"].lower()).strip("-")]
        g.add((material, RDF.type, FS.Material))
        g.add((node, FS.madeOf, material))
        if r.get("geometry"):
            g.add((node, FS.geometry, Literal(r["geometry"])))
    elif r["type"] == "ExperimentalRunRecord":
        g.add((FS[r["investigation_id"]], FS.hasRun, node))
        g.add((node, FS.usesSample, FS[r["sample_id"]]))
        for condition_id in r["condition_ids"]:
            g.add((node, FS.hasCondition, FS[condition_id]))
    elif r["type"] == "ConditionRecord":
        g.add((node, FS.conditionType, Literal(r["kind"])))
        for key, predicate in [
            ("reported_value", FS.reportedValue),
            ("reported_unit", FS.reportedUnit),
            ("canonical_value", FS.canonicalValue),
            ("canonical_unit", FS.canonicalUnit),
            ("reported_lower_value", FS.reportedLowerValue),
            ("reported_upper_value", FS.reportedUpperValue),
            ("canonical_lower_value", FS.canonicalLowerValue),
            ("canonical_upper_value", FS.canonicalUpperValue),
        ]:
            if r.get(key) is not None:
                g.add((node, predicate, Literal(r[key])))
        if r.get("is_approximate"):
            g.add((node, FS.isApproximate, Literal(True)))
out = ROOT / "data/canonical/graph.ttl"
g.serialize(out, format="turtle")
shapes = Graph().parse(ROOT / "ontology/shapes.ttl", format="turtle")
conforms, _, report = validate(g, shacl_graph=shapes)
print(json.dumps({"triples": len(g), "conforms": bool(conforms), "report": str(report)}))
raise SystemExit(0 if conforms else 1)
