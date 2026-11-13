"""Scientific ingestion contracts, including adversarial publication and scope cases."""

import shutil
from pathlib import Path

import pytest

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.scientific_correction import interpret_correction
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy
from nasa_fire_ai.services.phase3 import Phase3AssistantService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def curator(tmp_path):
    for directory in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    registry = EvidenceRegistry(tmp_path / "data/index/evidence.sqlite")
    service = CurationService(tmp_path, registry, ReviewPolicy(frozenset({"test-scientist"}), True))
    yield service
    registry.db.close()


def compatible(curator, extra=""):
    # Explicitly synthetic adversarial fixture, never described as NASA observations.
    files = [
        (
            "controlled.csv",
            (
                "Run,Group,Material,Gravity,Airflow (cm/s),Observation,Interpretation,Hypothesis,Open question\n"
                "A1,B,PMMA,microgravity,20,PMMA flame extinguished.,The authors suggest a tentative explanation.,A hypothesis remains untested.,Further research is required.\n"
                "A2,B,PMMA,normal-gravity,10,PMMA flame continued to burn.,The authors suggest a tentative explanation.,A hypothesis remains untested.,Further research is required.\n"
                + extra
            ).encode(),
        )
    ]
    saved = curator.submit(
        "Controlled ambiguity fixture", "Synthetic contract tests", files, "test-scientist"
    )
    table = saved["package"]["tables"][0]
    return curator.clarification(
        saved["package"]["id"],
        "table-role:" + table["id"],
        "ExperimentalRun",
        "Controlled fixture explicitly describes executed runs",
        "test-scientist",
    )


def test_regeneration_exclusion_and_correction_idempotence(curator):
    saved = compatible(curator)
    package = saved["package"]
    subject = package["entities"][1]["id"]
    operations = [{"action": "exclude", "subject": subject, "reason": "Synthetic preliminary row"}]
    proposal = curator.preview_correction(
        package["id"], operations, "Exclude preliminary row", "test-scientist"
    )
    current = curator.apply_correction(proposal, "test-scientist")
    for _ in range(4):
        curator.regenerate(current["package"])
        regenerated = curator.save(current["package"], "test-scientist")
        assert regenerated["digest"] == current["digest"]
        assert len(regenerated["package"]["exclusions"]) == 1
        repeated = curator.preview_correction(
            package["id"], operations, "Repeat exclusion", "test-scientist"
        )
        assert curator.apply_correction(repeated, "test-scientist")["digest"] == current["digest"]
        curator.approve_and_publish(package["id"], current["digest"], "test-scientist")
        store = project_legacy(curator.root, curator.registry)
        assert subject not in store.entities()
        curator.rollback(package["id"], "test-scientist")
        curator.publish(package["id"], current["digest"], "test-scientist")


def test_generic_class_relation_and_actual_assistant(curator, monkeypatch):
    from rdflib import RDFS

    from nasa_fire_ai.query.native import NS, node

    saved = compatible(curator)
    package = saved["package"]
    eid = package["evidence"][0]["evidence_id"]
    observation = next(s for s in package["statements"] if s["epistemic"] == "measured_observation")
    conclusion = next(
        s for s in package["statements"] if s["epistemic"] == "tentative_interpretation"
    )
    cls = {
        "kind": "class",
        "id": "SyntheticExtinctionObservation",
        "name": "Synthetic extinction observation",
        "definition": "Synthetic subtype for an isolated ontology edge test, never a NASA discovery",
        "purpose": "Exercise dynamic class contracts",
        "parent": "ReportedObservation",
        "why_existing_insufficient": "Synthetic test of a reviewed finer classification",
        "constraints": {},
        "intended_instances": [observation["id"]],
        "query_terms": ["synthetic extinction observations"],
        "evidence_ids": [eid],
        "impact": "Compatible synthetic addition",
    }
    curator.propose_extension(package["id"], cls, "test-scientist")
    with pytest.raises(PermissionError):
        curator.approve_extension(package["id"], cls["id"], "unauthorized")
    curator.approve_extension(package["id"], cls["id"], "test-scientist")
    relation = {
        "kind": "object_property",
        "id": "syntheticDiscussedBy",
        "name": "Synthetic discussed by",
        "definition": "Reviewed documentary discussion attribution, not causality or proof",
        "purpose": "Exercise source-to-target type validation",
        "why_existing_insufficient": "Synthetic edge test",
        "domain": [cls["id"]],
        "range": ["NASAConclusion"],
        "direction": "source_to_target",
        "scope": "Synthetic statement scope",
        "evidence_requirements": "Original fixture evidence",
        "transitive": False,
        "constraints": {},
        "evidence_ids": [eid],
        "impact": "Compatible addition",
    }
    curator.propose_extension(package["id"], relation, "test-scientist")
    curator.approve_extension(package["id"], relation["id"], "test-scientist")
    operations = [
        {
            "action": "classify_statement",
            "subject": observation["id"],
            "class_id": cls["id"],
            "epistemic": "measured_observation",
            "evidence_ids": [eid],
        },
        {
            "action": "add_relation",
            "subject": observation["id"],
            "relation": relation["id"],
            "object": conclusion["id"],
            "evidence_ids": [eid],
        },
    ]
    preview = curator.preview_correction(
        package["id"], operations, "Reviewed synthetic subtype and discussion", "test-scientist"
    )
    current = curator.apply_correction(preview, "test-scientist")
    bad = {**operations[1], "subject": conclusion["id"], "object": observation["id"]}
    with pytest.raises(ValueError, match="type contract"):
        curator.preview_correction(package["id"], [bad], "Wrong direction", "test-scientist")
    receipt = curator.approve_and_publish(package["id"], current["digest"], "test-scientist")
    assert receipt["publication"]["shacl"]
    store = project_legacy(curator.root, curator.registry)
    assert (node(cls["id"]), RDFS.subClassOf, node("ReportedObservation")) in store.graph
    assert store.relations(observation["id"], relation["id"]) == {conclusion["id"]}
    assert store.payload(conclusion["id"])["epistemic"] == "tentative_interpretation"
    from pyshacl import validate as validate_shapes
    from rdflib import RDF

    from nasa_fire_ai.services.curation import extension_shapes

    shapes = extension_shapes(store)
    assert validate_shapes(store.graph, shacl_graph=shapes)[0]
    # Deliberate isolated RDF corruption must fail generated domain/range shapes.
    store.graph.remove((node(observation["id"]), RDF.type, node(cls["id"])))
    store.graph.add((node(observation["id"]), RDF.type, node("NASAConclusion")))
    assert not validate_shapes(store.graph, shacl_graph=shapes)[0]
    monkeypatch.setenv("NATIVE_V2_QUERY_ENABLED", "true")
    monkeypatch.setenv("NEMOTRON_SCIENTIFIC_SELECTION_ENABLED", "false")
    assistant = Phase3AssistantService(
        root=curator.root, settings=Settings(root=curator.root, nvidia_api_key=None)
    )
    result = assistant.answer_query("Which synthetic extinction observations describe PMMA?")
    assert any(
        r["id"] == observation["id"] for r in result.evidence_bundle.experimental_observations
    ), result.model_dump(mode="json")
    assert any(
        r.get("approved_relationships") and r.get("id") == observation["id"]
        for r in result.evidence_bundle.semantic_records
    )
    assert all(
        curator.registry.resolve(eid)
        for eid in store.graph.objects(node(observation["id"]), NS.evidenceRef)
    )
    curator.rollback(package["id"], "test-scientist")
    assert cls["id"] not in project_legacy(curator.root, curator.registry).registry.class_metadata
    curator.publish(package["id"], current["digest"], "test-scientist")
    assert cls["id"] in project_legacy(curator.root, curator.registry).registry.class_metadata


def test_question_plans_and_complete_context(curator):
    import json

    from nasa_fire_ai.llm.scientific_correction import (
        correction_context,
        generate_clarifications,
        normalize_operations,
    )

    assert normalize_operations(
        [{"exclude": {"subject": "source-statement", "reason": "Documentary"}}]
    ) == [{"action": "exclude", "subject": "source-statement", "reason": "Documentary"}]
    assert (
        normalize_operations(
            [{"operation": "scope", "subject": "source-statement", "objects": []}]
        )[0]["action"]
        == "scope"
    )
    with pytest.raises(ValueError, match="wrapper"):
        normalize_operations([{"exclude": {"action": "publish", "subject": "source-statement"}}])
    with pytest.raises(ValueError, match="Unsupported"):
        normalize_operations([{"action": "replace_source", "subject": "source-statement"}])

    saved = curator.submit(
        "Synthetic shared wind fixture",
        "Synthetic grouping test",
        [("wind.csv", b"Run,Wind (cm/s)\nR1,20\nR2,30\n")],
        "test-scientist",
    )
    questions = curator.questions(saved["package"])
    mapping = next(q for q in questions if q["kind"] == "mapping")
    assert mapping["alternatives"] == ["AirflowVelocity", "documentary", "extension"]
    assert mapping["options"][-1]["selection"] == "another"
    assert all(o["operations"] for o in mapping["options"][:-1])
    assert mapping["affected_records"] == 2
    generated = generate_clarifications(
        curator, saved["package"]["id"], Settings(nvidia_api_key=None)
    )
    assert generated["receipt"]["execution"] == "DETERMINISTIC"
    serialized, receipt = correction_context(
        curator, saved["package"], "Assign R1 to microgravity", saved["package"]["entities"]
    )
    assert json.loads(serialized)["instruction"] == "Assign R1 to microgravity"
    assert receipt["input_characters"] <= 24000
    curator.clarification(
        saved["package"]["id"],
        mapping["id"],
        "AirflowVelocity",
        "Source-supported synthetic wind mapping",
        "test-scientist",
    )
    assert mapping["id"] not in [
        q["id"] for q in curator.questions(curator.get(saved["package"]["id"])["package"])
    ]


def test_reject_existing_concept_and_epistemic_upgrade(curator):
    saved = compatible(curator)
    package = saved["package"]
    eid = package["evidence"][0]["evidence_id"]
    hypothesis = next(s for s in package["statements"] if s["epistemic"] == "hypothesis")
    with pytest.raises(ValueError, match="Uncertain"):
        curator.preview_correction(
            package["id"],
            [
                {
                    "action": "classify_statement",
                    "subject": hypothesis["id"],
                    "class_id": "ReportedObservation",
                    "epistemic": "measured_observation",
                    "evidence_ids": [eid],
                }
            ],
            "Unsafe upgrade",
            "test-scientist",
        )
    with pytest.raises(ValueError, match="Reuse"):
        curator.propose_extension(
            package["id"],
            {
                "kind": "class",
                "id": "Extinction",
                "name": "Extinction",
                "definition": "Already in ontology",
                "purpose": "Negative reuse test",
                "why_existing_insufficient": "Unsupported assertion",
                "evidence_ids": [eid],
                "impact": "Compatible",
                "constraints": {},
                "parent": "ReportedObservation",
                "intended_instances": [hypothesis["id"]],
                "query_terms": ["extinction"],
            },
            "test-scientist",
        )


def test_narrative_whitespace_and_multiple_scope_reopen(curator):
    from nasa_fire_ai.ingestion.scientific_proposals import deterministic_propositions

    text = "Both runs were observed to continue to burn. Results\nindicate that extinction was not achieved."
    propositions = deterministic_propositions(
        [{"evidence_id": "synthetic", "text": text}], curator.semantic
    )
    assert [p["class_id"] for p in propositions] == ["ReportedObservation", "NASAConclusion"]
    assert propositions[1]["quote"] in text
    saved = curator.submit(
        "Synthetic shared narrative",
        "Synthetic scope grouping",
        [("runs.csv", b"Run,Material\nR1,PMMA\nR2,PMMA\n"), ("narrative.txt", text.encode())],
        "test-scientist",
    )
    package = saved["package"]
    runs = [e["id"] for e in package["entities"] if e["class_id"] == "ExperimentalRun"]
    q = next(
        q for q in curator.questions(package) if q["kind"] == "scope" and "observation" in q["id"]
    )
    assert q["allows_multiple"]
    changed = curator.clarification(
        package["id"], q["id"], runs, "Source explicitly identifies both runs", "test-scientist"
    )
    observation = next(
        s for s in changed["package"]["statements"] if s["epistemic"] == "measured_observation"
    )
    assert observation["scope"] == runs
    assert q["id"] not in [q["id"] for q in curator.questions(changed["package"])]
    reopened = curator.reopen_decision(
        package["id"], q["id"], "Review narrower scope", "test-scientist"
    )
    assert q["id"] in [q["id"] for q in curator.questions(reopened["package"])]


def test_legacy_table_encoding_preserves_input(curator):
    data = "Run,Material,Note\nR1,PMMA,µm notation\n".encode("cp1252")
    saved = curator.submit(
        "Synthetic legacy encoding",
        "Byte preservation test",
        [("table.csv", data)],
        "test-scientist",
    )
    package = saved["package"]
    assert package["inputs"][0]["encoding"] == "cp1252"
    assert package["tables"][0]["rows"][0]["Note"] == "µm notation"
    assert not curator.validate_originals(package)
    assert (curator.root / package["inputs"][0]["stored_input"]).read_bytes() == data


def test_grouped_mapping_and_unit_guard(curator):
    data = b"Run,Material,Wind (cm/s)\nR1,acrylic,20\nR2,acrylic,30\n"
    saved = curator.submit(
        "Alias fixture", "Controlled ambiguity", [("table.csv", data)], "creator"
    )
    questions = curator.questions(saved["package"])
    mapping = next(q for q in questions if q["kind"] == "mapping")
    material = next(q for q in questions if q["kind"] == "identity")
    assert mapping["affected_records"] == material["affected_records"] == 2
    with pytest.raises(ValueError, match="unit"):
        curator.clarification(
            saved["package"]["id"], mapping["id"], "Pressure", "Incorrect mapping", "test-scientist"
        )
    curator.clarification(
        saved["package"]["id"],
        mapping["id"],
        "AirflowVelocity",
        "Source defines wind velocity",
        "test-scientist",
    )
    changed = curator.clarification(
        saved["package"]["id"],
        material["id"],
        "PMMA",
        "Controlled source alias reviewed",
        "test-scientist",
    )
    assert len(changed["package"]["values"]) == 2
    assert not any(
        q["id"] in {mapping["id"], material["id"]} for q in curator.questions(changed["package"])
    )
    assert curator.validate(changed["package"])["metrics"]["duplicate_questions_avoided"] == 2


def test_approval_version_idempotence_failure_history(curator):
    saved = compatible(curator)
    pid = saved["package"]["id"]
    assert curator.validate(saved["package"])["ready"]
    with pytest.raises(PermissionError):
        curator.approve(pid, saved["digest"], "unauthorized")
    with pytest.raises(PermissionError):
        curator.publish(pid, saved["digest"], "test-scientist")
    receipt = curator.approve_and_publish(pid, saved["digest"], "test-scientist")
    assert receipt["publication"]["shacl"]
    assert curator.publish(pid, saved["digest"], "test-scientist")["status"] == "ALREADY_ACTIVE"
    original_count = curator.registry.db.execute("SELECT count(*) FROM passages").fetchone()[0]
    unchanged = curator.save(saved["package"], "test-scientist")
    assert unchanged["digest"] == saved["digest"]
    saved["package"]["purpose"] += " Revised scientific review scope."
    revised = curator.save(saved["package"], "test-scientist")
    with pytest.raises(ValueError, match="changed"):
        curator.publish(pid, saved["digest"], "test-scientist")
    curator.approve(pid, revised["digest"], "test-scientist")
    for failure in ("graph", "index"):
        with pytest.raises(RuntimeError):
            curator.publish(pid, revised["digest"], "test-scientist", fail_at=failure)
        assert (
            curator.registry.db.execute("SELECT digest FROM research_active").fetchone()[0]
            == saved["digest"]
        )
        assert (
            curator.registry.db.execute("SELECT count(*) FROM passages").fetchone()[0]
            == original_count
        )
    curator.publish(pid, revised["digest"], "test-scientist")
    assert curator.rollback(pid, "test-scientist")["restored_digest"] == saved["digest"]
    assert curator.get(pid, 1)["package"]["version"] == 1
    assert curator.registry.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_scope_epistemic_and_read_only_boundaries(curator):
    saved = compatible(curator)
    package = saved["package"]
    first, second = [e["id"] for e in package["entities"] if e["class_id"] == "ExperimentalRun"]
    conclusion = next(
        s for s in package["statements"] if s["epistemic"] == "tentative_interpretation"
    )
    op = {"action": "scope", "subject": conclusion["id"], "objects": [second]}
    proposal = curator.preview_correction(
        package["id"],
        [op],
        "Only the terrestrial control supports this interpretation",
        "test-scientist",
    )
    changed = curator.apply_correction(proposal, "test-scientist")
    assert next(s for s in changed["package"]["statements"] if s["id"] == conclusion["id"])[
        "scope"
    ] == [second]
    with pytest.raises(ValueError, match="read-only"):
        curator.preview_correction(
            package["id"],
            [
                {
                    "action": "add_relation",
                    "subject": "PMMA",
                    "relation": "hasMaterial",
                    "object": first,
                    "evidence_ids": [],
                }
            ],
            "Attempt to edit historical identity",
            "test-scientist",
        )
    with pytest.raises(ValueError, match="Conflicting"):
        curator.preview_correction(
            package["id"],
            [
                {
                    "action": "add_relation",
                    "subject": first,
                    "relation": "hasGravityCondition",
                    "object": "normal-gravity",
                    "evidence_ids": package["entities"][1]["evidence_ids"],
                }
            ],
            "Conflicting correction",
            "test-scientist",
        )
    curator.approve_and_publish(package["id"], changed["digest"], "test-scientist")
    graph = project_legacy(curator.root, curator.registry)
    assert graph.relations(first, "hasGravityCondition") == {"microgravity"}
    assert graph.relations(second, "hasGravityCondition") == {"normal-gravity"}
    assert graph.payload(conclusion["id"])["epistemic"] == "tentative_interpretation"
    assert any(s["epistemic"] == "hypothesis" for s in changed["package"]["statements"])
    assert any(s["epistemic"] == "open_question" for s in changed["package"]["statements"])


def test_campaign_context_local_control_and_duplicate(curator):
    data = b"Run,Material,Gravity\nC1,PMMA,\nC2,PMMA,normal-gravity\n"
    files = [
        ("runs.csv", data),
        (
            "methods.txt",
            b"The campaign was performed in microgravity. C2 was a terrestrial control.",
        ),
    ]
    saved = curator.submit(
        "Campaign fixture", "Controlled inheritance fixture", files, "test-scientist"
    )
    pid = saved["package"]["id"]
    assert curator.submit(
        "Campaign fixture",
        "Controlled inheritance fixture",
        list(reversed(files)),
        "test-scientist",
    )["duplicate"]
    context = next(q for q in curator.questions(saved["package"]) if q["kind"] == "context")
    changed = curator.clarification(
        pid,
        context["id"],
        "campaign",
        "Methodology identifies campaign and local control exception",
        "test-scientist",
    )
    runs = [e for e in changed["package"]["entities"] if e["class_id"] == "ExperimentalRun"]
    gravities = {
        e["label"]: {
            r["object"]
            for r in changed["package"]["relations"]
            if r["subject"] == e["id"] and r["relation"] == "hasGravityCondition"
        }
        for e in runs
    }
    assert gravities == {"C1": {"microgravity"}, "C2": {"normal-gravity"}}


def test_natural_language_proposal_and_incorrect_model(curator):
    saved = compatible(curator)
    pid = saved["package"]["id"]
    settings = Settings(root=curator.root, nvidia_api_key=None)
    bad = interpret_correction(
        curator, pid, "Make all uncertain ideas demonstrated facts", "test-scientist", settings
    )
    assert bad["blocked"]
    # Offline multi-run correction against a fresh table without gravity.
    new = curator.submit(
        "NL fixture",
        "Controlled source",
        [("runs.csv", b"Run,Material,Gravity\nR1,PMMA,microgravity\nR2,PMMA,microgravity\n")],
        "test-scientist",
    )
    result = interpret_correction(
        curator,
        new["package"]["id"],
        "Assign R1 and R2 to microgravity",
        "test-scientist",
        settings,
    )
    assert len(result["proposal"]["operations"]) == 2
    changed = curator.apply_correction(result["proposal"], "test-scientist")
    assert sum(r["relation"] == "hasGravityCondition" for r in changed["package"]["relations"]) == 2
    # Wrong model endpoint is rejected through the same typed validator.
    with pytest.raises(ValueError, match="endpoint"):
        curator.preview_correction(
            pid,
            [
                {
                    "action": "add_relation",
                    "subject": saved["package"]["entities"][1]["id"],
                    "relation": "hasMaterial",
                    "object": "invented-PMMA-equivalent",
                    "evidence_ids": [saved["package"]["evidence"][0]["evidence_id"]],
                }
            ],
            "Incorrect Nemotron interpretation",
            "test-scientist",
        )


def test_extension_and_source_value_fidelity(curator):
    saved = curator.submit(
        "Quantity fixture",
        "Controlled new quantity",
        [("droplets.csv", b"Run,Burning Rate (mm2/s)\nD1,0.75\nD2,0.81\n")],
        "test-scientist",
    )
    package = saved["package"]
    proposal = {
        "property": {
            "property_id": "DropletSquaredDiameterRate",
            "dimension": "area_per_time",
            "canonical_unit": "m2/s",
            "aliases": ["burning rate"],
        },
        "definition": "Source-reported fitted decrease in squared droplet diameter per time",
        "why_existing_insufficient": "Velocity is not squared diameter per time",
        "domain": "ExperimentalRun",
        "range": "numeric",
        "evidence_ids": [package["evidence"][0]["evidence_id"]],
        "impact": "Compatible addition; no existing records changed",
        "validation_contract": "SemanticRegistry.validate",
    }
    proposed = curator.propose_extension(package["id"], proposal, "test-scientist")
    assert not proposed["package"]["extensions"][0]["approved"]
    curator.approve_extension(package["id"], "DropletSquaredDiameterRate", "test-scientist")
    current = curator.get(package["id"])
    question = next(q for q in curator.questions(current["package"]) if q["kind"] == "mapping")
    changed = curator.clarification(
        package["id"],
        question["id"],
        "DropletSquaredDiameterRate",
        "Controlled source quantity definition reviewed",
        "test-scientist",
    )
    assert changed["package"]["values"][0]["value"]["reported_value"] == 0.75
    assert changed["package"]["values"][0]["value"]["reported_unit"] == "mm2/s"
    op = {
        "action": "value",
        "subject": changed["package"]["values"][0]["id"],
        "value": {"reported_value": 99, "reported_unit": "mm2/s", "raw_expression": "99"},
        "evidence_ids": [package["evidence"][0]["evidence_id"]],
    }
    with pytest.raises(ValueError, match="original source"):
        curator.preview_correction(package["id"], [op], "Fabricate a number", "test-scientist")


def test_new_source_queryability_and_hypothesis(curator, monkeypatch):
    saved = compatible(curator)
    for flag, value in {
        "NATIVE_V2_QUERY_ENABLED": "true",
        "NEMOTRON_SCIENTIFIC_SELECTION_ENABLED": "false",
        "SCIENTIFIC_SYNTHESIS_ENABLED": "true",
        "AUTONOMOUS_RESEARCH_ENABLED": "false",
    }.items():
        monkeypatch.setenv(flag, value)
    service = Phase3AssistantService(
        root=curator.root, settings=Settings(root=curator.root, nvidia_api_key=None)
    )
    before = service.answer_query(
        "What observations were reported in Controlled ambiguity fixture?"
    )
    assert not any(
        s["id"].startswith(saved["package"]["id"])
        for s in before.evidence_bundle.experimental_observations
    )
    curator.approve_and_publish(saved["package"]["id"], saved["digest"], "test-scientist")
    after = service.answer_query("What observations were reported in Controlled ambiguity fixture?")
    assert any(
        s["id"].startswith(saved["package"]["id"])
        for s in after.evidence_bundle.experimental_observations
    )
    assert all(
        curator.registry.resolve(eid)
        for claim in after.answer.generated_claims
        for eid in claim.evidence_ids
    )
    response = service.answer_query(
        "What conclusions were reported in Controlled ambiguity fixture?"
    )
    assert any(c.epistemic_type == "hypothesis" for c in response.answer.generated_claims)
    assert "Reported hypothesis" in response.rendered_answer


def test_draft_preview_isolation_and_source_tampering(curator):
    saved = compatible(curator)
    before = curator.registry.db.execute("SELECT count(*) FROM passages").fetchone()[0]
    result = curator.preview_query(
        saved["package"]["id"], "What observations were reported in Controlled ambiguity fixture?"
    )
    assert result.rendered_answer.startswith("DRAFT PREVIEW")
    assert result.evidence_bundle.experimental_observations
    assert curator.registry.db.execute("SELECT count(*) FROM passages").fetchone()[0] == before
    assert not curator.registry.db.execute("SELECT * FROM research_active").fetchall()
    changed = saved["package"]
    changed["evidence"][0]["text"] = "Fabricated source statement"
    assert not curator.validate(changed)["ready"]
    assert any("original submitted" in e for e in curator.validate(changed)["errors"])


def test_scientific_ui_actual_widgets(curator, monkeypatch):
    from streamlit.testing.v1 import AppTest

    saved = compatible(curator)
    monkeypatch.setenv("NASA_CURATION_DEVELOPMENT", "true")
    monkeypatch.setenv("NASA_CURATION_WORKSPACE", str(curator.root))
    script = f"import sys\nsys.path.insert(0,{str(ROOT / 'app')!r})\nfrom curation_view import show_curation\nfrom pathlib import Path\nshow_curation(Path({str(ROOT)!r}))"
    app = AppTest.from_string(script, default_timeout=15).run()
    assert not app.exception
    assert any(button.label == "Approve and incorporate" for button in app.button)
    assert any(element.label == "Research materials" for element in app.get("file_uploader"))
    assert app.get("graphviz_chart")
    # Explicit exact-version review approval through actual UI button.
    consent = next(c for c in app.checkbox if c.label.startswith("I reviewed"))
    consent.check().run()
    next(b for b in app.button if b.label == "Approve and incorporate").click().run()
    assert not app.exception
    assert (
        curator.registry.db.execute("SELECT digest FROM research_active").fetchone()[0]
        == saved["digest"]
    )


def test_incorrect_advisory_output_and_invalid_scientific_number(curator):
    import json
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    saved = compatible(curator)
    package = saved["package"]
    response = SimpleNamespace(
        usage=None,
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "operations": [
                                {
                                    "action": "add_relation",
                                    "subject": package["entities"][1]["id"],
                                    "relation": "hasMaterial",
                                    "object": "fabricated-alias",
                                    "evidence_ids": [package["evidence"][0]["evidence_id"]],
                                }
                            ],
                            "unresolved": [],
                        }
                    )
                )
            )
        ],
    )
    adapter = MagicMock()
    adapter.client.with_options.return_value.chat.completions.create.return_value = response
    with patch(
        "nasa_fire_ai.llm.scientific_correction.NvidiaStructuredClient", return_value=adapter
    ):
        result = interpret_correction(
            curator,
            package["id"],
            "Correct material identity",
            "test-scientist",
            Settings(root=curator.root, nvidia_api_key="test-placeholder"),
            True,
        )
    assert result["blocked"]
    assert curator.get(package["id"])["digest"] == saved["digest"]
    value = package["values"][0]
    changed = {**value["value"], "reported_value": 999}
    with pytest.raises(ValueError, match="original expression"):
        curator.preview_correction(
            package["id"],
            [
                {
                    "action": "value",
                    "subject": value["id"],
                    "value": changed,
                    "evidence_ids": value["evidence_ids"],
                }
            ],
            "Mismatch numeric value and expression",
            "test-scientist",
        )


def test_reuse_published_quantity_contract_and_preserve_reference(curator):
    saved = curator.submit(
        "Thickness contract",
        "Controlled source",
        [("one.csv", b"Run,Thickness (cm)\nR1,0.37\n")],
        "test-scientist",
    )
    package = saved["package"]
    extension = {
        "property": {
            "property_id": "SpecimenThickness",
            "dimension": "length",
            "canonical_unit": "m",
            "aliases": ["thickness"],
        },
        "definition": "Reported specimen thickness",
        "why_existing_insufficient": "Length quantity absent from registry",
        "domain": "ExperimentalRun",
        "range": "numeric",
        "evidence_ids": [package["evidence"][0]["evidence_id"]],
        "impact": "Compatible addition",
        "validation_contract": "SemanticRegistry.validate",
    }
    curator.propose_extension(package["id"], extension, "test-scientist")
    curator.approve_extension(package["id"], "SpecimenThickness", "test-scientist")
    for q in curator.questions(curator.get(package["id"])["package"]):
        selection = "ExperimentalRun" if q["kind"] == "table_role" else "SpecimenThickness"
        curator.clarification(
            package["id"],
            q["id"],
            selection,
            "Explicitly labeled controlled table",
            "test-scientist",
        )
    reviewed = curator.get(package["id"])
    curator.approve_and_publish(package["id"], reviewed["digest"], "test-scientist")
    reloaded = CurationService(curator.root, curator.registry, curator.policy)
    another = reloaded.submit(
        "Second compatible thickness table",
        "Known contract",
        [("two.csv", b"Run,Thickness (cm)\nR2,0.42\n")],
        "test-scientist",
    )
    assert another["package"]["values"][0]["property_id"] == "SpecimenThickness"
    assert not any(q["kind"] == "mapping" for q in reloaded.questions(another["package"]))
    assert reloaded.get(package["id"])["digest"] == reviewed["digest"]
    assert reloaded.templates()["properties"][-1]["property_id"] == "SpecimenThickness"


def test_wrong_observation_run_and_stale_correction_preview(curator):
    saved = compatible(curator)
    package = saved["package"]
    runs = [e["id"] for e in package["entities"] if e["class_id"] == "ExperimentalRun"]
    observation = next(s for s in package["statements"] if s["epistemic"] == "measured_observation")
    with pytest.raises(ValueError, match="Statement applicability/table-row"):
        curator.preview_correction(
            package["id"],
            [{"action": "scope", "subject": observation["id"], "objects": [runs[1]]}],
            "Controlled wrong attribution fixture",
            "test-scientist",
        )
    # A genuine documentary exclusion changes the draft and makes a previously
    # source-supported preview stale, without publishing wrong attribution.
    correct = curator.preview_correction(
        package["id"],
        [{"action": "scope", "subject": observation["id"], "objects": [runs[0]]}],
        "Original source row belongs to first run, not the terrestrial control",
        "test-scientist",
    )
    changed = curator.preview_correction(
        package["id"],
        [
            {
                "action": "exclude",
                "subject": observation["id"],
                "reason": "Retain documentary evidence",
            }
        ],
        "Withhold scientific assertion",
        "test-scientist",
    )
    curator.apply_correction(changed, "test-scientist")
    assert next(
        s
        for s in curator.get(package["id"])["package"]["statements"]
        if s["id"] == observation["id"]
    )["scope"] == [runs[0]]
    with pytest.raises(ValueError, match="changed"):
        curator.apply_correction(correct, "test-scientist")


def test_measurement_retrieval_and_approved_rdf_integrity(curator, monkeypatch):
    saved = curator.submit(
        "Duration study",
        "Controlled measurement contract",
        [("durations.csv", b"Run,Burn Time (s)\nT1,420\nT2,70\n")],
        "test-scientist",
    )
    package = saved["package"]
    extension = {
        "property": {
            "property_id": "BurnDuration",
            "dimension": "time",
            "canonical_unit": "s",
            "aliases": ["burn time"],
            "context": "reported_quantity",
        },
        "definition": "Source reported burn duration",
        "why_existing_insufficient": "No duration contract",
        "domain": "ExperimentalRun",
        "range": "numeric",
        "evidence_ids": [package["evidence"][0]["evidence_id"]],
        "impact": "Compatible addition",
        "validation_contract": "SemanticRegistry.validate",
    }
    curator.propose_extension(package["id"], extension, "test-scientist")
    curator.approve_extension(package["id"], "BurnDuration", "test-scientist")
    for question in curator.questions(curator.get(package["id"])["package"]):
        curator.clarification(
            package["id"],
            question["id"],
            "ExperimentalRun" if question["kind"] == "table_role" else "BurnDuration",
            "Controlled source contract reviewed",
            "test-scientist",
        )
    current = curator.get(package["id"])
    receipt = curator.approve_and_publish(package["id"], current["digest"], "test-scientist")
    monkeypatch.setenv("NATIVE_V2_QUERY_ENABLED", "true")
    monkeypatch.setenv("NEMOTRON_SCIENTIFIC_SELECTION_ENABLED", "false")
    assistant = Phase3AssistantService(
        root=curator.root, settings=Settings(root=curator.root, nvidia_api_key=None)
    )
    response = assistant.answer_query("Which measurements were reported in Duration study?")
    assert len(response.evidence_bundle.measurements) == 2
    assert "420 s" in response.rendered_answer and "70 s" in response.rendered_answer
    assert all(c.authority == "RESEARCHER_CURATED" for c in response.answer.generated_claims)
    graph_file = curator.root / receipt["publication"]["graph_path"]
    assert graph_file.suffix == ".nt"
    graph_file.write_text("tampered approved RDF")
    with pytest.raises(ValueError, match="checksum"):
        project_legacy(curator.root, curator.registry)


def test_curation_enforces_the_endpoint_contract_extraction_uses(curator):
    package = compatible(curator)["package"]
    kinds = {e["id"]: e["class_id"] for e in package["entities"]}
    run = next(i for i, c in kinds.items() if c == "ExperimentalRun")
    study = next(i for i, c in kinds.items() if c == "Investigation")
    evidence = package["relations"][0]["evidence_ids"]
    assert not any("type contract" in e for e in curator.validate(package)["errors"])
    # A study is not a material: "hasMaterial" admits only a Material object.
    package["relations"].append(
        {"subject": run, "relation": "hasMaterial", "object": study, "evidence_ids": evidence}
    )
    assert any(
        "object violates approved type contract" in e for e in curator.validate(package)["errors"]
    )


def _condition_object_errors(curator, base, class_id, monkeypatch):
    import copy

    from nasa_fire_ai.query.v2 import RelationDefinition

    package = copy.deepcopy(base)
    # hasCondition is an approved ontology relation; register it for this package
    # as a package with a scientific extraction would.
    registry = curator.property_registry(package)
    registry.register_relation(RelationDefinition("hasCondition"))
    monkeypatch.setattr(curator, "property_registry", lambda _package: registry)
    kinds = {e["id"]: e for e in package["entities"]}
    run = next(i for i, e in kinds.items() if e["class_id"] == "ExperimentalRun")
    evidence = kinds[run]["evidence_ids"]
    package["entities"].append(
        {
            "id": "synthetic-object",
            "label": "Object",
            "class_id": class_id,
            "evidence_ids": evidence,
        }
    )
    package["relations"].append(
        {
            "subject": run,
            "relation": "hasCondition",
            "object": "synthetic-object",
            "evidence_ids": evidence,
        }
    )
    return [e for e in curator.validate(package)["errors"] if "type contract" in e]


def test_an_approved_subclass_satisfies_the_endpoint_contract(curator, monkeypatch):
    base = compatible(curator)["package"]
    # GravityCondition is an approved rdfs:subClassOf ExperimentalCondition.
    assert _condition_object_errors(curator, base, "GravityCondition", monkeypatch) == []
    # Metamorphic: an unrelated class is still refused.
    assert _condition_object_errors(curator, base, "Material", monkeypatch)


def test_ancestry_is_transitive_cycle_safe_and_approved_only():
    from nasa_fire_ai.ingestion.semantic import class_ancestors

    metadata = {
        "Grandchild": {"approved_ontology_parents": ["Child"]},
        "Child": {"parent": "Root"},
        "Root": {},
        "LoopA": {"parent": "LoopB"},
        "LoopB": {"parent": "LoopA"},
    }
    assert class_ancestors("Grandchild", metadata) == {"Grandchild", "Child", "Root"}
    assert class_ancestors("LoopA", metadata) == {"LoopA", "LoopB"}
    # A parent only a model proposed (a staged term) is not in the approved metadata.
    assert class_ancestors("ProposedShield", metadata) == {"ProposedShield"}
