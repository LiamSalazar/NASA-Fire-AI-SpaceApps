"""Reproducible real-source contextual evaluation; versioned outputs only."""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
PREFIX = "phase3c_real_context"
VERSION = "v3"
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.context import ContextStatement, ContextStatus, SourceLocation
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.contextual import reconstruct_structure, register_source_unit
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.contextual import attach_context_layer


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, payload):
    version = "v1" if name == "freeze" else VERSION
    path = ART / f"{PREFIX}_{name}_{version}.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def freeze():
    manifest = ART / f"{PREFIX}_freeze_v1.json"
    if manifest.exists():
        print("Existing freeze retained")
        return
    files = {
        str(p.relative_to(ROOT)): digest(p)
        for folder in ["data/raw", "data/canonical", "evals", "artifacts", "ontology", "domain"]
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in str(p)
    }
    write("freeze", {"files": files, "count": len(files)})
    target = ART / f"{PREFIX}_evidence_v1.sqlite"
    with (
        sqlite3.connect(f"file:{ROOT}/data/index/evidence.sqlite?mode=ro", uri=True) as original,
        sqlite3.connect(target) as backup,
    ):
        original.backup(backup)
    print({"frozen_files": len(files), "snapshot": str(target.relative_to(ROOT))})


def configure():
    for flag in [
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED",
        "RELATIONAL_RELATED_RETRIEVAL_ENABLED",
        "NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED",
    ]:
        os.environ[flag] = "true"
    for flag in [
        "PSI_STRUCTURED_PUBLICATION_ENABLED",
        "FLEX_SOURCE_CORRECTIONS_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
    ]:
        os.environ[flag] = "false"


def raw_text(evidence, sid):
    row = evidence.db.execute(
        "SELECT raw_file FROM passages p JOIN documents d USING(document_id) WHERE source_id=? AND raw_file LIKE '%.txt' LIMIT 1",
        (sid,),
    ).fetchone()
    return Path(row[0]).read_text()


def between(text, start, end, *, last=False):
    offset = text.rfind(start) if last else text.find(start)
    if offset < 0:
        raise ValueError(start)
    finish = text.find(end, offset + len(start))
    if finish < 0:
        raise ValueError(end)
    return text[offset:finish].strip()


def extract():
    configure()
    evidence = EvidenceRegistry(ART / f"{PREFIX}_evidence_v1.sqlite")
    store = project_legacy(ROOT, evidence)
    units = {}
    data = {
        "version": "phase3c-real-source-context-v1",
        "entities": [],
        "statements": [],
        "scientific_records": [],
        "model_validated_records": [],
        "independent_review": None,
    }
    bass = raw_text(evidence, "ntrs-20210011385")
    poster = raw_text(evidence, "ntrs-20160000593")
    saffire = raw_text(evidence, "ntrs-20170008805")

    def unit(key, sid, text, section, role="paragraph"):
        units[key] = register_source_unit(evidence, sid, text, section=section, role=role)
        return units[key]

    unit(
        "bass-environment",
        "ntrs-20160000593",
        between(poster, "Approach\n", "Why ISS for BASS-II?"),
        "Approach",
    )
    unit(
        "bass-summary",
        "ntrs-20210011385",
        between(bass, "Summary \nThe Burning", "NASA/TM-20210011385 2"),
        "Summary",
    )
    appendix_start = bass.find("Appendix A.—Test Matrices", bass.find("NASA/TM-20210011385 103"))
    appendix_end = bass.find("Appendix B.—", appendix_start)
    appendix = bass[appendix_start:appendix_end]
    unit(
        "bass-appendix",
        "ntrs-20210011385",
        between(appendix, "Appendix A.—Test Matrices", "A.1 Bhattacharjee Test Matrix"),
        "Appendix A",
        "section",
    )
    unit(
        "bass-material",
        "ntrs-20160000593",
        between(
            poster,
            "Residence Time Driven Flame Spread\nSubrata",
            "Residence Time Driven Flame Spread\nComparison",
        ),
        "Residence Time Driven Flame Spread",
    )
    unit(
        "bass-film-observation",
        "ntrs-20160000593",
        between(
            poster,
            "Sequence of top views showing radiative quenching",
            "Material Ignition and Suppression Test",
        ),
        "Residence Time Driven Flame Spread",
        "caption",
    )
    unit(
        "bass-rods",
        "ntrs-20160000593",
        between(
            poster,
            "Material Ignition and Suppression Test\nCarlos",
            "Material Ignition and Suppression Test\n3.00",
        ),
        "Material Ignition and Suppression Test",
    )
    unit(
        "bass-comparison",
        "ntrs-20160000593",
        between(poster, "There is a downward trend", "1g Clear"),
        "PMMA rod comparison",
        "caption",
    )
    unit(
        "bass-narrow",
        "ntrs-20160000593",
        between(poster, "Narrow Channel Validation\nFletcher", "Spacecraft Materials Microgravity"),
        "Narrow Channel Validation",
    )
    unit(
        "bass-sibal",
        "ntrs-20160000593",
        between(poster, "Growth and Extinction Limit\nJames", "Growth and Extinction Limit\nLong"),
        "Growth and Extinction Limit",
    )
    unit(
        "saffire-execution",
        "ntrs-20170008805",
        between(saffire, "Experiment\n• The Saffire", "5\n\nAir Flow"),
        "Experiment",
    )
    unit(
        "saffire-tests",
        "ntrs-20170008805",
        between(saffire, "Saffire-I Description", "16\n\nSaffire 1 video"),
        "Saffire-I Description and SIBAL results",
    )
    unit(
        "saffire-gravity",
        "ntrs-20170008805",
        between(saffire, "Left: Flame base", "20\n\nSIBAL"),
        "Concurrent and opposed-flow comparison",
        "caption",
    )
    unit(
        "saffire-controls",
        "ntrs-20170008805",
        between(saffire, "Saffire-2; Why Silicone?", "13\n\nSaffire-I Description"),
        "Saffire-II silicone ground and flight tests",
    )
    unit(
        "saffire-conclusions",
        "ntrs-20170008805",
        between(saffire, "Summary and Conclusions", "26\n"),
        "Summary and Conclusions",
    )
    # Separate the ground reference from the flight results; both are actual
    # documentary evidence, without inventing execution IDs for ground data.
    ground_quote = between(
        saffire, "In upward-burning, normal-gravity tests", "Microgravity behavior was sought:"
    )
    unit(
        "silicone-ground",
        "ntrs-20170008805",
        ground_quote,
        "Saffire-II terrestrial reference tests",
    )
    space_quote = between(saffire, "Results were convincing although", "It was surprising")
    unit("silicone-flight", "ntrs-20170008805", space_quote, "Saffire-II silicone results")

    def entity(eid, cls, keys, *, scopes=(), text=None):
        spans = [units[k] for k in keys]
        row = {
            "id": eid,
            "class_id": cls,
            "evidence_ids": [s["evidence_id"] for s in spans],
            "source_ids": sorted({s["source_id"] for s in spans}),
            "scope_entities": list(scopes),
        }
        if text:
            row["text"] = text
        data["entities"].append(row)
        return row

    def direct_path(subject, target, keys, relation="concerns"):
        return [
            {
                "from": subject,
                "to": target,
                "relation": relation,
                "basis": "EXPLICIT_SOURCE_IDENTITY",
                "support_spans": [units[k] for k in keys],
            }
        ]

    def statement(
        sid,
        dimension,
        value,
        subjects,
        keys,
        scope_entity,
        paths,
        *,
        relation=None,
        scope="group",
        exceptions=(),
        numeric=None,
    ):
        spans = [units[k] for k in keys]
        row = ContextStatement(
            statement_id=sid,
            context_type=dimension,
            value=value,
            entity_ids=subjects,
            evidence_ids=[s["evidence_id"] for s in spans],
            original_text=spans[0]["text"],
            source_location=SourceLocation(
                document_id=evidence.resolve(spans[0]["evidence_id"])["document_id"],
                source_id=spans[0]["source_id"],
                section=spans[0]["section"],
            ),
            scope=scope,
            scope_entity=scope_entity,
            validation_status=ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
            relation=relation
            or {"gravity": "hasGravityCondition", "material": "hasMaterial"}[dimension],
            support_spans=spans,
            membership_paths=paths,
            exceptions=list(exceptions),
            property_value=numeric,
        )
        data["statements"].append(row.model_dump(mode="json"))

    identities = json.loads((ART / "phase3c_fidelity_reconstruction_v1.json").read_text())[
        "identities"
    ]
    memberships = []
    for record in identities:
        subject = record["identity_id"]
        if record["investigation_id"] != "psi-25":
            continue
        token = subject.removeprefix("psi-25-")
        match = re.search(
            r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", appendix, re.IGNORECASE
        )
        if not match:
            memberships.append(
                {
                    "entity": subject,
                    "status": "UNKNOWN",
                    "reason": "no exact run identifier in appendix",
                }
            )
            continue
        # A run identifier alone is insufficient across documents. Require the
        # source sample-number cell to agree with the report's local row span.
        refs = store.evidence(subject)
        cells = [
            cell for eid in refs for cell in (evidence.resolve(eid) or {}).get("source_cells", [])
        ]
        samples = [
            c["original_value"].strip()
            for c in cells
            if c["original_header"].strip() in {"Sample Number", "Sample #", "Sample ID"}
        ]
        local = appendix[max(0, match.start() - 100) : match.end() + 180]
        sample_match = bool(samples) and any(
            re.search(r"(?<!\w)" + re.escape(sample) + r"(?!\w)", local, re.IGNORECASE)
            for sample in samples
        )
        if not sample_match:
            memberships.append(
                {
                    "entity": subject,
                    "status": "UNKNOWN",
                    "reason": "sample identity cross-check unavailable",
                    "source_samples": samples,
                    "report_span": local,
                }
            )
            continue
        key = "membership-" + token
        unit(key, "ntrs-20210011385", local, "Appendix A run " + token, "table")
        row_key = "registry-" + token
        source_eid = next(eid for eid in refs if evidence.resolve(eid).get("source_cells"))
        units[row_key] = {
            "evidence_id": source_eid,
            "text": evidence.resolve(source_eid)["text"],
            "source_id": "psi-25",
            "role": "table",
            "section": "Experimental table",
        }
        path = [
            {
                "from": subject,
                "to": "psi-25",
                "relation": "belongsToInvestigation",
                "basis": "NATIVE_GRAPH",
                "support_spans": [units[row_key], units[key], units["bass-appendix"]],
            }
        ]
        statement(
            "gravity-" + token,
            "gravity",
            "microgravity",
            [subject],
            ["bass-environment", "bass-appendix", key, row_key],
            "psi-25",
            {subject: path},
            scope="campaign",
        )
        memberships.append(
            {"entity": subject, "status": "VERIFIED_APPLICABLE_CONTEXT", "path": path}
        )

    # The two PSI-98 records match the documentary concurrent and opposed
    # executions by explicit flow direction, width, and elapsed time; do not
    # equate publication sample label 1-2 with an intact 94-cm specimen.
    for subject in ["psi-98-S1", "psi-98-S2"]:
        eid = "E-psi-98-table-" + subject[-2:]
        units[subject] = {
            "evidence_id": eid,
            "text": evidence.resolve(eid)["text"],
            "source_id": "psi-98",
            "role": "table",
            "section": "Experimental table",
        }
        row = evidence.resolve(eid)["text"]
        expected = [
            ",40.6,",
            ",20,",
            ",420,Concurrent" if subject.endswith("S1") else ",70,Opposed",
        ]
        if not all(token in row for token in expected):
            memberships.append(
                {"entity": subject, "status": "UNKNOWN", "reason": "execution fingerprint mismatch"}
            )
            continue
        path = [
            {
                "from": subject,
                "to": "psi-98",
                "relation": "belongsToInvestigation",
                "basis": "NATIVE_GRAPH",
                "support_spans": [units[subject], units["saffire-tests"], units["saffire-gravity"]],
            }
        ]
        statement(
            "gravity-" + subject,
            "gravity",
            "microgravity",
            [subject],
            ["saffire-gravity", "saffire-tests", subject],
            "psi-98",
            {subject: path},
            scope="group",
        )
        memberships.append(
            {
                "entity": subject,
                "status": "VERIFIED_APPLICABLE_CONTEXT",
                "path": path,
                "specimen_reuse_limit": "opposed run used remaining fuel; original width/length is not remaining fuel size",
            }
        )

    groups = [
        ("context:bass-film-series", ["bass-material"], ["psi-25"]),
        ("context:bass-ground-rods", ["bass-comparison"], []),
        ("context:bass-flight-rods", ["bass-rods", "bass-comparison"], ["psi-25"]),
        ("context:silicone-ground", ["silicone-ground"], []),
        ("context:silicone-flight", ["silicone-flight", "saffire-controls"], []),
    ]
    for eid, keys, scopes in groups:
        entity(eid, "Investigation", keys, scopes=scopes)

    specs = [
        (
            "context:bass-film-observation",
            "ReportedObservation",
            "bass-film-observation",
            "context:bass-film-series",
            "microgravity",
            "PMMA",
            "DETERMINISTIC",
        ),
        (
            "context:bass-ground-rod-observation",
            "ReportedObservation",
            "bass-comparison",
            "context:bass-ground-rods",
            "normal-gravity",
            "PMMA",
            "NEMOTRON_ASSISTED",
        ),
        (
            "context:bass-flight-rod-observation",
            "ReportedObservation",
            "bass-comparison",
            "context:bass-flight-rods",
            "microgravity",
            "PMMA",
            "NEMOTRON_ASSISTED",
        ),
        (
            "context:silicone-ground-observation",
            "ReportedObservation",
            "silicone-ground",
            "context:silicone-ground",
            "normal-gravity",
            None,
            "DETERMINISTIC",
        ),
        (
            "context:silicone-flight-observation",
            "ReportedObservation",
            "silicone-flight",
            "context:silicone-flight",
            "microgravity",
            None,
            "NEMOTRON_ASSISTED",
        ),
    ]
    for eid, cls, key, group, gravity, material, method in specs:
        supporting_keys = [key]
        if "bass" in eid:
            supporting_keys += [
                "bass-material" if "film" in eid else "bass-rods",
                "bass-environment",
            ]
        if "silicone-flight" in eid:
            supporting_keys += ["saffire-controls"]
        text = units[key]["text"]
        entity(eid, cls, supporting_keys, scopes=[group], text=text)
        paths = {eid: direct_path(eid, group, supporting_keys)}
        statement("gravity-" + eid, "gravity", gravity, [eid], supporting_keys, group, paths)
        if material:
            statement("material-" + eid, "material", material, [eid], supporting_keys, group, paths)
        data["scientific_records"].append(
            {
                "id": eid,
                "class_id": cls,
                "text": text,
                "support_spans": [units[k] for k in supporting_keys],
                "source_ids": sorted({units[k]["source_id"] for k in supporting_keys}),
                "method": method,
            }
        )

    # A narrower conclusion retains only its own comparison group, without
    # projecting that conclusion onto all Saffire experiments.
    conclusion = "Flammability of silicone in microgravity appears to be reduced compared to normal gravity, at least for the flow speeds tested."
    unit("silicone-conclusion", "ntrs-20170008805", conclusion, "Summary and Conclusions")
    cid = "context:silicone-conclusion"
    entity(
        cid,
        "NASAConclusion",
        ["silicone-conclusion"],
        scopes=["context:silicone-flight"],
        text=conclusion,
    )
    data["scientific_records"].append(
        {
            "id": cid,
            "class_id": "NASAConclusion",
            "text": conclusion,
            "support_spans": [units["silicone-conclusion"]],
            "source_ids": ["ntrs-20170008805"],
            "method": "DETERMINISTIC",
        }
    )
    statement(
        "gravity-" + cid,
        "gravity",
        "microgravity",
        [cid],
        ["silicone-conclusion", "saffire-controls"],
        "context:silicone-flight",
        {
            cid: direct_path(
                cid, "context:silicone-flight", ["silicone-conclusion", "saffire-controls"]
            )
        },
    )

    # Source-reported shared numeric condition belongs only to the explicitly
    # terrestrial PMMA comparison, never to the entire BASS campaign.
    ground_id = "context:bass-ground-rod-observation"
    statement(
        "oxygen-ground-rods",
        "oxygen",
        "21%",
        [ground_id],
        ["bass-comparison"],
        "context:bass-ground-rods",
        {ground_id: direct_path(ground_id, "context:bass-ground-rods", ["bass-comparison"])},
        relation="OxygenConcentration",
        numeric={"reported_value": 21, "reported_unit": "%"},
    )
    apparatus = "context:bass-wind-tunnel"
    entity(apparatus, "ExperimentalCondition", ["bass-environment"], scopes=["psi-25"])
    statement(
        "apparatus-bass-films",
        "apparatus",
        apparatus,
        ["context:bass-film-observation"],
        ["bass-environment", "bass-material"],
        "context:bass-film-series",
        {
            "context:bass-film-observation": direct_path(
                "context:bass-film-observation",
                "context:bass-film-series",
                ["bass-environment", "bass-material"],
            )
        },
        relation="hasCondition",
    )

    # Actual intervention and aftermath are on the same source slide. The
    # slide's micro/partial-gravity question is not execution-level gravity.
    import pymupdf

    with pymupdf.open(ROOT / "data/raw/ntrs-20205007829.pdf") as pdf:
        fire_slide = pdf[15].get_text()
    unit(
        "saffire-iv-fire",
        "ntrs-20205007829",
        fire_slide,
        "Fire Suppression Requirements",
        "paragraph",
    )
    intervention = between(
        fire_slide, "For the Saffire-IV PMMA sample", "The fire didn’t extinguish"
    ).rstrip("\n")
    aftermath = between(fire_slide, "The fire didn’t extinguish", "In a spacecraft")
    unit(
        "saffire-iv-intervention", "ntrs-20205007829", intervention, "Fire Suppression Requirements"
    )
    unit("saffire-iv-observation", "ntrs-20205007829", aftermath, "Fire Suppression Requirements")
    question = between(fire_slide, "For a fixed fire suppression system", "\nFor the Saffire-IV")
    unit("saffire-iv-question", "ntrs-20205007829", question, "Fire Suppression Requirements")
    group = "context:saffire-iv-pmma-test"
    entity(group, "ExperimentalRun", ["saffire-iv-fire"])
    for rid, cls, key in [
        ("context:saffire-iv-flow-intervention", "Intervention", "saffire-iv-intervention"),
        ("context:saffire-iv-flow-observation", "ReportedObservation", "saffire-iv-observation"),
        ("context:saffire-iv-suppression-question", "OpenQuestion", "saffire-iv-question"),
    ]:
        entity(rid, cls, [key, "saffire-iv-fire"], scopes=[group], text=units[key]["text"])
        data["scientific_records"].append(
            {
                "id": rid,
                "class_id": cls,
                "text": units[key]["text"],
                "support_spans": [units[key], units["saffire-iv-fire"]],
                "source_ids": ["ntrs-20205007829"],
                "method": "DETERMINISTIC",
            }
        )
        if cls != "OpenQuestion":
            statement(
                "material-" + rid,
                "material",
                "PMMA",
                [rid],
                ["saffire-iv-intervention", key],
                group,
                {rid: direct_path(rid, group, ["saffire-iv-fire"])},
            )
    data["documentary_links"] = [
        {
            "subject": "context:saffire-iv-flow-intervention",
            "relation": "concerns",
            "object": group,
            "evidence_ids": [units["saffire-iv-fire"]["evidence_id"]],
        },
        {
            "subject": "context:saffire-iv-flow-observation",
            "relation": "concerns",
            "object": group,
            "evidence_ids": [units["saffire-iv-fire"]["evidence_id"]],
        },
    ]

    write(
        "source_units",
        {
            "units": units,
            "structures": {
                sid: reconstruct_structure(evidence, sid)
                for sid in ["ntrs-20210011385", "ntrs-20160000593", "ntrs-20170008805"]
            },
        },
    )
    write("applicability", data)
    write("memberships", memberships)
    attach_context_layer(store, evidence, ART / f"{PREFIX}_applicability_{VERSION}.json")
    write(
        "extraction",
        {
            "sources": 4,
            "source_units": len(units),
            "statements": len(data["statements"]),
            "accepted": len(store.context_layer.resolver.statements),
            "rejected": store.context_layer.rejected,
            "memberships": {
                state: sum(m["status"] == state for m in memberships)
                for state in ["UNKNOWN", "VERIFIED_APPLICABLE_CONTEXT"]
            },
            "independent_review": None,
        },
    )
    print(json.loads((ART / f"{PREFIX}_extraction_{VERSION}.json").read_text()))


def live(corrective=False):
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.llm.context import NvidiaContextInterpreter
    from nasa_fire_ai.llm.interfaces import ProviderFailure

    settings = Settings()
    model = NvidiaContextInterpreter(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    units = json.loads((ART / f"{PREFIX}_source_units_{VERSION}.json").read_text())["units"]
    data = json.loads((ART / f"{PREFIX}_applicability_{VERSION}.json").read_text())
    windows = [
        (
            "bass-campaign",
            [
                "bass-environment",
                "bass-summary",
                "bass-appendix",
                "membership-B1",
                "registry-B1",
                "membership-M17",
                "registry-M17",
            ],
            ["psi-25", "psi-25-B1", "psi-25-M17"],
        ),
        (
            "saffire-campaign",
            ["saffire-execution", "saffire-tests", "saffire-gravity", "psi-98-S1", "psi-98-S2"],
            ["psi-98", "psi-98-S1", "psi-98-S2"],
        ),
        (
            "mixed-pmma",
            [
                "bass-environment",
                "bass-material",
                "bass-film-observation",
                "bass-rods",
                "bass-comparison",
                "bass-narrow",
                "bass-sibal",
            ],
            [e["id"] for e in data["entities"] if e["id"].startswith("context:bass")],
        ),
        (
            "mixed-silicone",
            [
                "saffire-controls",
                "silicone-ground",
                "silicone-flight",
                "silicone-conclusion",
                "saffire-conclusions",
            ],
            [e["id"] for e in data["entities"] if e["id"].startswith("context:silicone")],
        ),
        (
            "intervention",
            [
                "saffire-iv-fire",
                "saffire-iv-intervention",
                "saffire-iv-observation",
                "saffire-iv-question",
            ],
            [e["id"] for e in data["entities"] if e["id"].startswith("context:saffire-iv")],
        ),
    ]
    if corrective:
        windows = [
            (
                "mixed-pmma",
                ["bass-rods", "bass-comparison"],
                ["context:bass-ground-rod-observation", "context:bass-flight-rod-observation"],
            ),
            (
                "mixed-silicone",
                ["saffire-controls", "silicone-ground", "silicone-flight"],
                ["context:silicone-ground-observation", "context:silicone-flight-observation"],
            ),
        ]
    results = []
    for name, keys, entities in windows:
        suffix = "v4" if corrective else VERSION
        path = ART / f"{PREFIX}_live_{name}_{suffix}.json"
        if path.exists():
            receipt = json.loads(path.read_text())
            results.append(receipt)
            print({"window": name, "execution": "CHECKPOINT_REPLAY"}, flush=True)
            continue
        passages = [units[k] for k in keys]
        payload = {
            "window": name,
            "query": "Identify the gravity context for the ground and flight observation entities from the supplied comparison passages. Propose at most two relations. Use hasGravityCondition, object_value normal-gravity or microgravity, context_scope group and quantifier IDENTIFIED. Quote the exact source words, preserving newlines. The names distinguish which group an entity represents; verify it from the documentary comparison rather than treating the investigation topic as a condition. Return a proposals array matching the required schema.",
            "entities": entities,
            "passages": passages,
            "allowed_predicates": [
                "hasGravityCondition",
                "hasMaterial",
                "hasCondition",
                "OxygenConcentration",
                "AirflowVelocity",
                "belongsToInvestigation",
                "concerns",
                "hasObservation",
                "hasIntervention",
            ],
        }
        receipt = {
            "input": payload,
            "input_digest": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
        }
        try:
            proposals = model.interpret(**{k: v for k, v in payload.items() if k != "window"})
            receipt["proposals"] = [p.model_dump(mode="json") for p in proposals]
        except ProviderFailure:
            receipt["proposals"] = []
        receipt.update(model.last_receipt)
        path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        results.append(receipt)
        print(
            {
                "window": name,
                "execution": receipt["execution"],
                "proposals": len(receipt["proposals"]),
                "latency_ms": receipt["latency_ms"],
                "error": receipt.get("error"),
            },
            flush=True,
        )

    configure()
    evidence = EvidenceRegistry(ART / f"{PREFIX}_evidence_v1.sqlite")
    store = project_legacy(ROOT, evidence)
    attach_context_layer(store, evidence, ART / f"{PREFIX}_applicability_{VERSION}.json")
    validations = []
    recovered = set()
    for receipt in results:
        for proposal in receipt["proposals"]:
            from nasa_fire_ai.context import ContextualProposal

            validation = store.context_layer.validate_model_proposal(
                ContextualProposal.model_validate(proposal)
            )
            validations.append({"window": receipt["input"]["window"], **validation})
            if not validation["reasons"]:
                recovered.add(proposal["subject_entity"])
    data["model_validated_records"] = sorted(recovered)
    if corrective:
        for name in ["model_applicability", "model_validation"]:
            if (ART / f"{PREFIX}_{name}_v4.json").exists():
                raise FileExistsError(name)
        (ART / f"{PREFIX}_model_applicability_v4.json").write_text(
            json.dumps(data, indent=2) + "\n"
        )
    else:
        write("model_applicability", data)
    summary = {
        "cases": validations,
        "fresh_calls": sum(r["execution"] == "FRESH_INFERENCE" for r in results),
        "valid_structured_outputs": sum(not r.get("error") for r in results),
        "validated_proposals": sum(not r["reasons"] for r in validations),
        "staged_or_rejected": sum(bool(r["reasons"]) for r in validations),
        "latency_ms": [r["latency_ms"] for r in results],
        "usage": [r["usage"] for r in results],
        "new_scientific_accuracy": None,
        "eligible_model_records": sorted(recovered),
    }
    if corrective:
        (ART / f"{PREFIX}_model_validation_v4.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
    else:
        write("model_validation", summary)


QUESTIONS = [
    ("default-pmma", "What did NASA observe about PMMA combustion?"),
    ("explicit-pmma", "What did NASA observe about PMMA combustion under microgravity?"),
    ("normal-gravity", "What do the available investigations report under normal gravity?"),
    (
        "comparative",
        "How do combustion observations differ between microgravity and normal gravity?",
    ),
    ("bass-identity", "What was investigated in BASS-II?"),
    ("saffire-conditions", "Which conditions applied to the Saffire-I experiments?"),
    (
        "material-runs",
        "Which experimental runs used PMMA, and how were their conditions different?",
    ),
    ("intervention", "What happened after airflow was interrupted and restored?"),
    ("conceptual", "Does acrylic mean PMMA?"),
    ("questions", "What unresolved questions did NASA identify about microgravity fire safety?"),
    (
        "multi-hop",
        "Which observations support NASA's conclusions about flame suppression under microgravity?",
    ),
    (
        "real-exception",
        "What observations distinguish normal gravity and microgravity silicone tests?",
    ),
    ("inclusive-boundary", "PMMA in microgravity with oxygen at most 22.2%"),
    ("exclusive-boundary", "PMMA in microgravity with oxygen below 22.2%"),
    ("absent", "PMMA in microgravity at pressure 123 Pa"),
]


def revalidate_model():
    from nasa_fire_ai.context import ContextualProposal

    configure()
    evidence = EvidenceRegistry(ART / f"{PREFIX}_evidence_v1.sqlite")
    store = project_legacy(ROOT, evidence)
    attach_context_layer(store, evidence, ART / f"{PREFIX}_applicability_{VERSION}.json")
    validations = []
    for window in ["mixed-pmma", "mixed-silicone"]:
        receipt = json.loads((ART / f"{PREFIX}_live_{window}_v4.json").read_text())
        for row in receipt["proposals"]:
            validation = store.context_layer.validate_model_proposal(
                ContextualProposal.model_validate(row)
            )
            validations.append({"window": window, **validation})
    data = json.loads((ART / f"{PREFIX}_applicability_{VERSION}.json").read_text())
    data["model_validated_records"] = sorted(
        {r["proposal"]["subject_entity"] for r in validations if not r["reasons"]}
    )
    (ART / f"{PREFIX}_model_applicability_v5.json").write_text(json.dumps(data, indent=2) + "\n")
    (ART / f"{PREFIX}_model_validation_v5.json").write_text(
        json.dumps(
            {
                "execution": "DETERMINISTIC_VALIDATION_REPLAY_OF_FRESH_RECEIPTS",
                "new_calls": 0,
                "cases": validations,
                "eligible_model_records": data["model_validated_records"],
                "policy": "reversible whitespace/NFC span recovery only; paraphrase and wrong scope rejected",
            },
            indent=2,
        )
        + "\n"
    )
    print([(r["proposal"]["subject_entity"], r["status"], r["reasons"]) for r in validations])


def upgrade():
    """Declare source-literal material identity and actual scope exclusions."""
    data = json.loads((ART / f"{PREFIX}_model_applicability_v5.json").read_text())
    source_units = json.loads((ART / f"{PREFIX}_source_units_v3.json").read_text())
    units = source_units["units"]
    material = "context:silicone-material"
    data["entities"].append(
        {
            "id": material,
            "class_id": "Material",
            "evidence_ids": [units["saffire-controls"]["evidence_id"]],
            "source_ids": ["ntrs-20170008805"],
            "scope_entities": [],
        }
    )
    data["query_aliases"] = {material: {"relation": "hasMaterial", "aliases": ["silicone"]}}
    for rid in [
        "context:silicone-ground-observation",
        "context:silicone-flight-observation",
        "context:silicone-conclusion",
    ]:
        base = next(s for s in data["statements"] if s["statement_id"] == "gravity-" + rid)
        data["statements"].append(
            {
                **json.loads(json.dumps(base)),
                "statement_id": "material-" + rid,
                "context_type": "material",
                "relation": "hasMaterial",
                "value": material,
            }
        )
    for statement in data["statements"]:
        if statement["statement_id"] == "gravity-context:silicone-flight-observation":
            statement["entity_ids"].append("context:silicone-ground-observation")
            statement["exceptions"] = ["context:silicone-ground-observation"]
        if statement["statement_id"] == "gravity-context:bass-flight-rod-observation":
            statement["entity_ids"].append("context:bass-ground-rod-observation")
            statement["exceptions"] = ["context:bass-ground-rod-observation"]
    write("applicability", data)
    write("source_units", source_units)


def install():
    """Append verified source units to the operational registry and install index."""
    source = EvidenceRegistry(ART / f"{PREFIX}_evidence_v1.sqlite")
    target = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    units = json.loads((ART / f"{PREFIX}_source_units_v8.json").read_text())["units"]
    inserted = 0
    for unit in units.values():
        eid = unit["evidence_id"]
        if target.resolve(eid):
            continue
        row = dict(
            source.db.execute("SELECT * FROM passages WHERE evidence_id=?", (eid,)).fetchone()
        )
        target.add_passage(row)
        location = source.resolve(eid).get("structured_location")
        if location:
            target.add_evidence_location(eid, location)
        inserted += 1
    path = ROOT / "data/index/scientific_context_v2.json"
    payload = (ART / f"{PREFIX}_applicability_v8.json").read_text()
    if path.exists() and path.read_text() != payload:
        raise FileExistsError("existing operational context index differs")
    if not path.exists():
        path.write_text(payload)
    write(
        "installation",
        {
            "new_registry_units": inserted,
            "index": str(path.relative_to(ROOT)),
            "index_digest": digest(path),
            "raw_files_modified": 0,
            "canonical_relations_published": 0,
        },
    )


def evaluate():
    from nasa_fire_ai.query.native import classify_native
    from nasa_fire_ai.services.native import answer_native_text

    configure()
    evidence = EvidenceRegistry(ART / f"{PREFIX}_evidence_v1.sqlite")
    store = project_legacy(ROOT, evidence)
    model_path = ART / f"{PREFIX}_applicability_v8.json"
    attach_context_layer(
        store,
        evidence,
        model_path if model_path.exists() else ART / f"{PREFIX}_applicability_{VERSION}.json",
    )
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    source_pool = {}
    records = []
    for variant in ["A", "B", "C", "D"]:
        os.environ["MICROGRAVITY_FIRST_RETRIEVAL_ENABLED"] = "false" if variant == "A" else "true"
        os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = (
            "true" if variant in {"C", "D"} else "false"
        )
        os.environ["NEMOTRON_CONTEXT_INTERPRETATION_ENABLED"] = (
            "true" if variant == "D" else "false"
        )
        for case_id, query in QUESTIONS:
            response = answer_native_text(query, store, evidence, language)
            bundle = response.execution.bundle.model_dump(mode="json")
            for passage in bundle["evidence_passages"]:
                source_pool[passage["evidence_id"]] = passage
            bundle["evidence_passages"] = [p["evidence_id"] for p in bundle["evidence_passages"]]
            records.append(
                {
                    "case_id": case_id,
                    "variant": variant,
                    "question": query,
                    "intent": response.execution.plan.intent.model_dump(mode="json"),
                    "bundle": bundle,
                    "answer": response.rendered_answer.split("<details>", 1)[0],
                    "citations_resolve": all(
                        evidence.resolve(eid) for eid in bundle["evidence_passages"]
                    ),
                    "latency_ms": response.execution.latency_ms,
                    "expert_scientific_relevance": None,
                    "expert_correct_scope": None,
                    "expert_attribution": None,
                    "expert_usefulness": None,
                    "reviewer": None,
                }
            )
            print(
                {
                    "variant": variant,
                    "case": case_id,
                    "direct": len(bundle["direct_evidence"]),
                    "related": len(bundle["related_evidence"]),
                    "resolver": bundle["retrieval_metadata"]
                    .get("scientific_context", {})
                    .get("resolver_invoked", False),
                    "clarification": response.execution.plan.intent.clarification_required,
                },
                flush=True,
            )
    identities = json.loads((ART / "phase3c_fidelity_reconstruction_v1.json").read_text())[
        "identities"
    ]
    gravity = []
    for identity in identities:
        subject = identity["identity_id"]
        local = sorted(store.relations(subject, "hasGravityCondition"))
        result = store.context_layer.resolver.resolve(subject, "gravity")
        gravity.append(
            {
                "entity": subject,
                "before_local_values": local,
                "before_status": "EXPLICIT_LOCAL" if local else "UNKNOWN",
                "after": result.model_dump(mode="json"),
                "expert_scope_label": None,
            }
        )
    import csv

    pairs = list(csv.DictReader((ART / "phase3c_fidelity_candidate_matrix_v4.csv").open()))
    comparison = []
    from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal

    for row in pairs:
        intent = resolve_minimal(
            MinimalInterpretationV2(), store.registry, language, query=row["original_question"]
        )
        outcomes = {}
        for variant in ["A", "C"]:
            os.environ["SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED"] = (
                "true" if variant == "C" else "false"
            )
            status, detail = classify_native(
                row["evidence_identity_ref"], intent, store, related_policy=True
            )
            outcomes[variant] = {"status": status, "detail": detail}
        comparison.append(
            {
                "pair_id": row["pair_id"],
                "question": row["original_question"],
                "entity": row["evidence_identity_ref"],
                "outcomes": outcomes,
                "scientific_relevance": None,
            }
        )
    write(
        "answers",
        {
            "cases": records,
            "source_pool": f"artifacts/{PREFIX}_answer_sources_{VERSION}.json",
            "candidate_budget": 8,
            "documentary_pool_budget": 32,
            "same_registry_snapshot": True,
            "independent_labels": 0,
        },
    )
    write("answer_sources", source_pool)
    write(
        "gravity_audit",
        {
            "cases": gravity,
            "before_unknown": sum(not r["before_local_values"] for r in gravity),
            "after_unknown": sum(r["after"]["status"] == "UNKNOWN" for r in gravity),
            "recovered": sum(
                not r["before_local_values"]
                and r["after"]["status"] == "VERIFIED_APPLICABLE_CONTEXT"
                for r in gravity
            ),
            "pairs": comparison,
        },
    )
    summaries = {}
    for variant in ["A", "B", "C", "D"]:
        cases = [r for r in records if r["variant"] == variant]
        summaries[variant] = {
            "queries": len(cases),
            "queries_with_direct": sum(bool(r["bundle"]["direct_evidence"]) for r in cases),
            "direct_records": sum(len(r["bundle"]["direct_evidence"]) for r in cases),
            "related_records": sum(len(r["bundle"]["related_evidence"]) for r in cases),
            "resolver_invoked_queries": sum(
                r["bundle"]["retrieval_metadata"]
                .get("scientific_context", {})
                .get("resolver_invoked", False)
                for r in cases
            ),
            "citation_valid_answers": sum(r["citations_resolve"] for r in cases),
            "scientific_precision": None,
        }
    write(
        "comparison",
        {
            "configurations": summaries,
            "E": "NOT_RUN; no independent advisory gold and model agreement cannot verify applicability",
            "retrieval_count_is_not_accuracy": True,
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--live-corrective", action="store_true")
    parser.add_argument("--revalidate-model", action="store_true")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze()
    if args.extract:
        extract()
    if args.live:
        live()
    if args.evaluate:
        evaluate()
    if args.live_corrective:
        live(corrective=True)
    if args.revalidate_model:
        revalidate_model()
    if args.upgrade:
        upgrade()
    if args.install:
        install()


if __name__ == "__main__":
    main()
