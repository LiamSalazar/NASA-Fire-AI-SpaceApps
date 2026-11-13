#!/usr/bin/env python3
"""Deterministic RDF queries for the curated safety evidence branch."""

import json
from pathlib import Path

from rdflib import RDF, Graph, Namespace

ROOT = Path(__file__).resolve().parents[1]
FS = Namespace("https://example.org/nasa-fire-safety#")
graph = Graph().parse(ROOT / "data/canonical/graph.ttl", format="turtle")


def ids(class_):
    return sorted(str(node).removeprefix(str(FS)) for node in graph.subjects(RDF.type, class_))


def text_ids(term):
    return sorted(
        str(subject).removeprefix(str(FS))
        for subject, text in graph.subject_objects(FS.text)
        if term.lower() in str(text).lower()
    )


def concerns(investigation):
    return sorted(
        str(subject).removeprefix(str(FS))
        for subject in graph.subjects(FS.concerns, FS[investigation])
    )


def main():
    print(
        json.dumps(
            {
                "requirements": ids(FS.Requirement),
                "guidance": ids(FS.Guidance),
                "suppression": sorted(
                    set(
                        text_ids("suppression")
                        + ["saffire-suppression-conclusion", "saffire-suppression-open-question"]
                    )
                ),
                "pmma": sorted(set(text_ids("PMMA") + concerns("psi-98"))),
                "open_questions": ids(FS.NASAIdentifiedOpenQuestion),
                "evidence_connected_to_safety": [
                    str(item).removeprefix(str(FS))
                    for item in graph.objects(FS["saffire-suppression-conclusion"], FS.supportedBy)
                ],
                "direct_evidence_plus_open_question": {
                    "direct": ["saffire-iv-flow-off-observation"],
                    "open_question": ["saffire-suppression-open-question"],
                },
                "no_direct_without_open_question": {
                    "status": "NO_DIRECT_EVIDENCE",
                    "open_questions_created": [],
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
