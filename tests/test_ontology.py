from pathlib import Path

from pyshacl import validate
from rdflib import RDF, Graph, Literal, Namespace

ROOT = Path(__file__).resolve().parents[1]
FS = Namespace("https://example.org/nasa-fire-safety#")


def test_ontology_loads_and_shacl_validates():
    g = Graph().parse(ROOT / "ontology/fire_safety.ttl", format="turtle")
    n = FS["run"]
    g.add((n, RDF.type, FS.ExperimentalRun))
    g.add((n, FS.evidenceRef, Literal("E1")))
    g.add((n, FS.usesSample, FS["sample"]))
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl", format="turtle")
    conforms, _, _ = validate(g, shacl_graph=shapes)
    assert conforms
