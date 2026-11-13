"""Synthetic contract cases, not NASA scientific observations or expert gold."""

import copy
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output, validate_output
from nasa_fire_ai.ingestion.document_structure import context_for, structure
from nasa_fire_ai.services.curation import CurationService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def service(tmp_path):
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, tmp_path / name)
    registry = EvidenceRegistry(tmp_path / "data/index/evidence.sqlite")
    yield CurationService(tmp_path, registry)
    registry.db.close()


def submitted(service, text):
    return service.submit(
        "Synthetic study", "Labeled synthetic test", [("source.md", text.encode())], "tester"
    )["package"]


def support(package, quote):
    return [{"evidence_id": package["evidence"][0]["evidence_id"], "quote": quote}]


def entity(package, key, label, cls, quote, study="current"):
    return {
        "key": key,
        "label": label,
        "class_id": cls,
        "study": study,
        "support": support(package, quote),
    }


def client_for(output):
    """Controlled stage adapter; returns only supplied, source-grounded fixture items."""
    client = Mock()

    def respond(**kwargs):
        from nasa_fire_ai.ingestion.document_extraction import STAGES, normalized

        payload = json.loads(kwargs["messages"][1]["content"])
        result = {k: copy.deepcopy(output[k]) for k in STAGES[payload["stage"]]}
        known = {e["label"]: e["key"] for e in payload["known_entities"]}
        keys = {
            e["key"]: known.get(e["label"], e["key"]) for e in output["entities"] if "support" in e
        }
        for items in result.values():
            for item in items:
                if "support" in item:
                    item["support"] = [
                        a["id"]
                        for a in payload["source_anchors"]
                        if any(
                            normalized(a["quote"]) in normalized(s["quote"])
                            for s in item["support"]
                        )
                    ][:6]
                for field in ("subject", "object"):
                    if field in item:
                        item[field] = keys.get(item[field], item[field])
                if "subjects" in item:
                    item["subjects"] = [keys.get(k, k) for k in item["subjects"]]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(result)), finish_reason="stop"
                )
            ],
            usage=None,
        )

    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    return client


def validate(service, package, output):
    return validate_output(output, package, structure(package, service.root), service.semantic)


def test_identity_can_span_only_contiguous_original_anchors(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    p = submitted(
        service, "Synthetic Investigation:\nA rotating apparatus\n\nUncited text.\nOther words"
    )
    o = Output().model_dump()
    o["entities"] = [
        entity(
            p,
            "study",
            "Synthetic Investigation: A rotating apparatus",
            "Investigation",
            "Synthetic Investigation:",
        )
    ]
    o["entities"][0]["support"] += support(p, "A rotating apparatus")
    d = structure(p, service.root)
    result = validate_output(o, p, d, extraction_semantic(service, p))["records"][0]
    assert result["status"] == "SOURCE_SUPPORTED"
    assert (
        result["identity_support"]["support"][0]["quote"]
        == "Synthetic Investigation:\nA rotating apparatus"
    )
    o["entities"][0]["label"] = "A rotating apparatus Other words"
    o["entities"][0]["support"] = support(p, "A rotating apparatus") + support(p, "Other words")
    result = validate_output(o, p, d, extraction_semantic(service, p))["records"][0]
    assert result["status"] == "REJECTED"


def test_source_variable_does_not_establish_arbitrary_condition_subclass(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    p = submitted(service, "Sensors record centrifugal acceleration and pressure.")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "variable", "centrifugal acceleration", "FlowCondition", p["evidence"][0]["text"])
    ]
    result = validate_output(o, p, structure(p, service.root), extraction_semantic(service, p))[
        "records"
    ][0]
    assert result["status"] == "UNRESOLVED"
    assert "CONDITION_SUBTYPE_REQUIRES_SOURCE_OR_APPROVED_ALIAS" in result["reasons"]


def test_duration_until_width_disappears_is_not_a_width_measurement(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    text = "Run A1 was tested. A1 flame width decreased to zero within 4 seconds."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "flame width",
            "expression": "4",
            "unit": "seconds",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    result = validate_output(o, p, structure(p, service.root), extraction_semantic(service, p))
    quantity = next(r for r in result["records"] if r["kind"] == "quantities")
    assert quantity["status"] == "REJECTED"
    assert "QUANTITY_NAME_UNIT_DIMENSION_CONTRADICTION" in quantity["reasons"]


def test_two_specimen_dimensions_bind_only_inside_their_original_names(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    text = "Two samples: Film 5 cm wide x 30 cm long and Rod 4 mm diameter were tested."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "film", "Film 5 cm wide x 30 cm long", "Sample", text),
        entity(p, "rod", "Rod 4 mm diameter", "Sample", text),
    ]
    q = {
        "subject": "film",
        "label": "width",
        "expression": "5",
        "unit": "cm",
        "epistemic": "experimental_configuration",
        "support": support(p, text),
    }
    o["quantities"] = [q]
    semantic = extraction_semantic(service, p)
    assert (
        validate_output(o, p, structure(p, service.root), semantic)["records"][-1]["status"]
        == "SOURCE_SUPPORTED"
    )
    q["subject"] = "rod"
    result = validate_output(o, p, structure(p, service.root), semantic)
    record = result["records"][-1]
    # The rod association is rejected; the value is revalidated on its own subject.
    film, rod = (result["entities_by_key"][k]["id"] for k in ("film", "rod"))
    assert record["subject"] == film != rod
    assert record["subject_recovery"] == {
        "proposed_subject": rod,
        "proposed_subject_rejection": "QUANTITY_LOCAL_SUBJECT_BINDING_UNRESOLVED",
        "method": "FULL_REVALIDATION_WITH_EACH_SOURCE_SUPPORTED_EXPERIMENTAL_SUBJECT",
        "recovered_subject": film,
        "status": "RECOVERED",
    }


def test_original_method_subsection_scope_crosses_pdf_pages_without_crossing_groups(service):
    import pymupdf

    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    with pymupdf.open() as pdf:
        for text in [
            "A. Alpha tests\nSynthetic apparatus description.",
            "Pressure was maintained at 20 Pa.",
            "B. Beta tests\nPressure was maintained at 40 Pa.",
        ]:
            pdf.new_page().insert_text((50, 50), text)
        data = pdf.tobytes()
    p = service.submit("Synthetic study", "Labeled scope test", [("source.pdf", data)], "tester")[
        "package"
    ]
    first, middle, last = p["evidence"]

    def ref(e, quote):
        return [{"evidence_id": e["evidence_id"], "quote": quote}]

    o = Output().model_dump()
    o["entities"] = [
        {
            "key": key,
            "label": label,
            "class_id": "ExperimentFamily",
            "study": "current",
            "support": ref(e, e["text"]),
        }
        for key, label, e in [("alpha", "Alpha tests", first), ("beta", "Beta tests", last)]
    ]
    o["quantities"] = [
        {
            "subject": "alpha",
            "label": "pressure",
            "expression": "20",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": ref(middle, middle["text"]),
        }
    ]
    document = structure(p, service.root)
    semantic = extraction_semantic(service, p)
    positive = validate_output(o, p, document, semantic)["records"][-1]
    assert positive["status"] == "SOURCE_SUPPORTED"
    assert positive["scope_context"]["basis"] == "EXACT_ORIGINAL_GROUP_SUBSECTION"
    assert positive["scope_context"]["support"][0]["evidence_id"] == first["evidence_id"]
    o["quantities"][0]["subject"] = "beta"
    result = validate_output(o, p, document, semantic)
    moved = result["records"][-1]
    # Beta never receives the Alpha-subsection value; it is revalidated on Alpha.
    assert moved["subject"] == result["entities_by_key"]["alpha"]["id"]
    assert moved["subject_recovery"]["proposed_subject"] == result["entities_by_key"]["beta"]["id"]
    assert moved["scope_context"]["basis"] == "EXACT_ORIGINAL_GROUP_SUBSECTION"


def test_group_subsection_cannot_promote_individual_run_value_to_whole_group(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    text = "A. Alpha tests\nRun A1 was tested at pressure 20 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "alpha", "Alpha tests", "ExperimentFamily", "A. Alpha tests"),
        entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was tested at pressure 20 Pa."),
    ]
    o["quantities"] = [
        {
            "subject": "alpha",
            "label": "pressure",
            "expression": "20",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, "Run A1 was tested at pressure 20 Pa."),
        }
    ]
    result = validate_output(o, p, structure(p, service.root), extraction_semantic(service, p))
    record = result["records"][-1]
    # The whole group never receives the run's value; the narrowest subject does.
    assert record["subject"] == result["entities_by_key"]["a1"]["id"]
    assert (
        record["subject_recovery"]["proposed_subject"] == (result["entities_by_key"]["alpha"]["id"])
    )


@pytest.mark.parametrize("boundary", ["III. Verification Testing", "4. Final Protocol"])
def test_arbitrary_numbered_section_ends_previous_group_scope(service, boundary):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    text = f"A. Alpha tests\nPressure was maintained at 20 Pa.\n{boundary}\nPressure was maintained at 40 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "alpha", "Alpha tests", "ExperimentFamily", "A. Alpha tests")]
    o["quantities"] = [
        {
            "subject": "alpha",
            "label": "pressure",
            "expression": "40",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, "Pressure was maintained at 40 Pa."),
        }
    ]
    result = validate_output(o, p, structure(p, service.root), extraction_semantic(service, p))
    record = result["records"][-1]
    # The value is kept from the source, but no group association is asserted.
    assert record["status"] == "UNRESOLVED" and record["subject"] is None
    assert record["subject_recovery"]["alternatives"] == []
    assert "QUANTITY_VALUE_PRESERVED_SUBJECT_UNRESOLVED" in record["reasons"]


def test_floating_figure_does_not_inherit_following_group(service):
    from nasa_fire_ai.ingestion.document_extraction import group_section_support

    text = "A. Alpha tests\nFigure 5: Temperature measurements."
    p = submitted(service, text)
    d = structure(p, service.root)
    span = {
        "source_id": p["evidence"][0]["source_id"],
        "evidence_id": p["evidence"][0]["evidence_id"],
        "start": text.index("Figure"),
        "quote": "Figure 5: Temperature measurements.",
    }
    entities = {
        "alpha": {
            "id": "alpha",
            "class_id": "ExperimentFamily",
            "label": "Alpha tests",
            "source_id": span["source_id"],
            "validation_status": "SOURCE_SUPPORTED",
        }
    }
    assert not group_section_support("alpha", [span], entities, d)


def test_roman_conclusion_scope_is_literal_document_investigation_not_cited_work(service):
    text = "# Synthetic study\nI. Methods\nAn apparatus was tested.\nIV. Conclusion\nThe results demonstrate the reported trend.\nEarlier work reported a different trend."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    s = {
        "text": "The results demonstrate the reported trend.",
        "class_id": "NASAConclusion",
        "epistemic": "author_reported_conclusion",
        "subjects": ["root"],
        "study": "current",
        "support": support(p, "The results demonstrate the reported trend."),
    }
    o["statements"] = [s]
    result = validate(service, p, o)["records"][-1]
    assert result["status"] == "SOURCE_SUPPORTED"
    assert result["scope_context"]["scope_is_individual_run"] is False
    s["text"] = "Earlier work reported a different trend."
    s["support"] = support(p, s["text"])
    assert validate(service, p, o)["records"][-1]["status"] != "SOURCE_SUPPORTED"


@pytest.mark.parametrize(
    "text",
    [
        "Figure 4: Original data with the best fit curve.",
        "This relationship is compared to experimental results.",
        "The least-squares fit describes the data.",
        "The flame length was computed from the fitted curve.",
        "The ignition temperature was estimated from the model.",
    ],
)
def test_fitted_caption_or_comparison_method_is_not_direct_observation(text):
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    assert role_errors({"text": text, "epistemic": "measured_observation"})


def test_source_objectives_are_not_executed_configuration():
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    assert role_errors(
        {
            "text": "Objectives\nDemonstrate the technique. Obtain new observations.",
            "epistemic": "experimental_configuration",
        }
    )
    assert not role_errors(
        {"text": "The pressure was maintained at 20 Pa.", "epistemic": "experimental_configuration"}
    )


def test_bullet_source_anchors_keep_epistemic_units_and_original_offsets(service):
    from nasa_fire_ai.ingestion.document_extraction import parse_stage_output, source_anchors

    text = "# Results\n• The sample pressure\nwas measured at 20 Pa\n• Future tests will use\n40 Pa\n• It is recommended to\nrepeat the procedure"
    p = submitted(service, text)
    d = structure(p, service.root)
    context = {
        "anchors": [{"evidence_id": p["evidence"][0]["evidence_id"], "quote": text, "start": 0}]
    }
    anchors = source_anchors({"members": d["segments"]}, context, [], p)
    atomic = [a for a in anchors.values() if a["statement_eligible"]]
    assert len(atomic) == 3
    assert all(text[a["start"] : a["end"]] == a["quote"] for a in atomic)
    assert any("sample pressure\nwas measured" in a["quote"] for a in atomic)
    assert all(a["quote"].count("•") == 1 for a in atomic)
    broad = next(k for k, a in anchors.items() if not a["statement_eligible"])
    out, errors = parse_stage_output(
        json.dumps(
            {
                "statements": [
                    {"anchor": broad, "epistemic": "guidance", "subjects": [], "study": "current"}
                ]
            }
        ),
        "propositions",
        anchors,
        "stop",
    )
    assert not out["statements"]
    assert errors


def test_wrapped_project_role_and_planned_strategy_are_distinct(service):
    text = "Example\nDevelopment Project Manager\nPhase 1 Baseline Testing\nIf no solution passes, the strategy will use a second phase."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "project", "Example Development", "Investigation", text),
        entity(p, "phase", "Phase 1 Baseline Testing", "ExperimentFamily", text),
    ]
    records = validate(service, p, o)["records"]
    assert records[0]["status"] == "SOURCE_SUPPORTED"
    assert records[1]["status"] == "UNRESOLVED"
    assert "STRATEGIC_PHASE_IS_NOT_ESTABLISHED_EXPERIMENT_GROUP" in records[1]["reasons"]


def test_mixed_bullets_and_goals_cannot_be_confirmed_scientific_results():
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    assert "MULTIPLE_BULLETS_REQUIRE_SEPARATE_EPISTEMIC_REVIEW" in role_errors(
        {
            "text": "• Measurements were completed\n• Future work is recommended",
            "epistemic": "guidance",
        }
    )
    assert "SOURCE_GOAL_IS_NOT_ESTABLISHED_RESULT" in role_errors(
        {"text": "Goal to improve material safety", "epistemic": "author_reported_conclusion"}
    )
    assert not role_errors(
        {
            "text": "The goal was achieved in the reported tests.",
            "epistemic": "author_reported_conclusion",
        }
    )


def test_original_dimensional_adjective_reuses_accessor_without_claiming_measurement(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic
    from nasa_fire_ai.ingestion.scientific_coverage import coverage

    text = "Fabric 5 cm wide x 30 cm long was mounted in the chamber."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "film", "Fabric 5 cm wide x 30 cm long", "Sample", text)]
    q = {
        "subject": "film",
        "label": "wide",
        "expression": "5",
        "unit": "cm",
        "epistemic": "experimental_configuration",
        "support": support(p, text),
    }
    o["quantities"] = [q]
    d = structure(p, service.root)
    semantic = extraction_semantic(service, p)
    v = validate_output(o, p, d, semantic)
    assert v["records"][-1]["status"] == "SOURCE_SUPPORTED"
    assert v["records"][-1]["mapping"]["source_accessor"] == "sample_width"
    assert v["records"][-1]["proposal"]["label"] == "wide"
    q["epistemic"] = "reported_quantity"
    v = validate_output(o, p, d, semantic)
    assert v["records"][-1]["status"] == "UNRESOLVED"
    assert v["records"][-1]["scientific_role_conflict"]
    inventory = coverage(p, d, v, [], [])
    assert inventory["source_units"][0]["quantity_inventory"][0]["state"] == "NOT_STRUCTURED"


def test_literal_article_identity_does_not_invent_execution_or_override_cited_scope(service):
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, resolve_explicit_scopes

    text = "# Synthetic study\n# Results\nThe flame extinguished after the flow stopped.\nEarlier measurements reported a different outcome.\nRun A1 was tested."
    p = submitted(service, text)
    prepared = service.prepare_scientific(
        p["id"],
        Settings(root=service.root, nvidia_api_key=None),
        budget=ExtractionBudget(max_model_calls=0),
    )
    o = Output().model_dump()
    roots = [
        e
        for e in prepared["package"]["scientific_extraction"]["raw_proposals"]["entities"]
        if e["class_id"] == "Investigation" and e["label"] == "Synthetic study"
    ]
    assert len(roots) == 1
    o["entities"] = [roots[0], entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was tested.")]
    s = {
        "text": "The flame extinguished after the flow stopped.",
        "class_id": "ReportedObservation",
        "epistemic": "measured_observation",
        "subjects": [],
        "study": "unknown",
        "support": support(p, "The flame extinguished after the flow stopped."),
    }
    # The runtime resolves only exact original offsets, not model-created spans.
    s["support"][0]["start"] = text.index(s["text"])
    o["statements"] = [s]
    d = structure(p, service.root)
    resolve_explicit_scopes(o, d)
    result = validate(service, p, o)["records"][-1]
    assert result["status"] == "SOURCE_SUPPORTED"
    assert result["scope_context"]["distributes_to_members"] is False
    s["subjects"] = ["a1"]
    assert validate(service, p, o)["records"][-1]["status"] != "SOURCE_SUPPORTED"
    s["subjects"] = []
    s["study"] = "cited"
    resolve_explicit_scopes(o, d)
    assert not s["subjects"] and s["study"] == "cited"
    s["study"] = "unknown"
    s["text"] = "Earlier measurements reported a different outcome."
    s["support"] = support(p, s["text"])
    s["support"][0]["start"] = text.index(s["text"])
    resolve_explicit_scopes(o, d)
    assert not s["subjects"]


def test_pdf_numeric_cells_are_pending_original_quantities_with_independent_tamper_check(service):
    import pymupdf

    from nasa_fire_ai.ingestion.pdf_quantities import pdf_table_quantities

    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 50), "Synthetic derived table\nResults from linear fits")
        data = pdf.tobytes()
    p = service.submit(
        "Synthetic derived table", "Synthetic table test", [("table.pdf", data)], "tester"
    )["package"]
    d = structure(p, service.root)
    d["detected_tables"] = [
        {
            "input_sha256": p["inputs"][0]["sha256"],
            "physical_pdf_page": 1,
            "bbox": [50, 50, 250, 150],
            "cells": [["Group A (mm/s)", "Group B (mm/s)"], [".15", ".40"]],
            "header": ["Group A (mm/s)", "Group B (mm/s)"],
            "header_external": False,
        }
    ]
    candidates = pdf_table_quantities(p, d)
    assert len(candidates) == 2
    assert [r["proposal"]["expression"] for r in candidates] == [".15", ".40"]
    assert all(
        r["status"] == "UNRESOLVED" and not r["scientific_execution_asserted"] for r in candidates
    )
    assert candidates[0]["proposal"]["unit"] == "mm/s"
    assert any(
        c["quote"] == "Results from linear fits"
        for c in candidates[0]["proposal"]["original_role_cues"]
    )
    assert candidates[0]["support_spans"][0]["locator"]["column_index"] == 0
    prepared = service.prepare_scientific(p["id"], Settings(root=service.root, nvidia_api_key=None))
    package = prepared["package"]
    # The real PDF has no detected table. Injecting fabricated cell proposals
    # cannot survive independent reconstruction from its original bytes.
    package["scientific_extraction"]["pdf_table_quantity_proposals"] = candidates
    assert any(
        "PDF quantitative proposals differ" in e for e in service.validate(package)["errors"]
    )


def test_transposed_table_units_preserve_axis_and_do_not_use_qualifier_as_unit():
    from nasa_fire_ai.ingestion.pdf_quantities import original_table_unit

    row = [{"original_value": "Nominal Voltage (V)"}, {"original_value": "15.14"}]
    unit, candidates = original_table_unit("Specimen B (Calculated)", row)
    assert unit == "V"
    assert candidates == [
        {"axis": "column", "literal": "Calculated", "recognized_unit_syntax": False},
        {"axis": "row", "literal": "V", "recognized_unit_syntax": True},
    ]
    assert original_table_unit("Length (cm)", [{"original_value": "Length (mm)"}])[0] is None
    assert original_table_unit("Unknown (estimate)", [])[0] is None


def test_author_abbreviation_does_not_sever_original_correlation_method(service):
    from nasa_fire_ai.ingestion.document_extraction import role_errors, source_anchors

    text = "Heat release is measured using Author et al. [12] correlation for the device. A second result follows."
    p = submitted(service, text)
    d = structure(p, service.root)
    anchors = source_anchors({"members": d["segments"]}, {"anchors": []}, [], p)
    quotes = [a["quote"] for a in anchors.values() if a["statement_eligible"]]
    assert quotes == [
        "Heat release is measured using Author et al. [12] correlation for the device.",
        "A second result follows.",
    ]
    assert "CORRELATION_ESTIMATE_IS_NOT_DIRECT_OBSERVATION" in role_errors(
        {"text": quotes[0], "epistemic": "measured_observation"}
    )
    assert not role_errors(
        {
            "text": "The height was measured using calibrated images.",
            "epistemic": "measured_observation",
        }
    )


def test_estimated_quantity_cannot_become_measurement_or_change_neighboring_measurement(service):
    text = "Run A1 was tested. A1 pressure was computed at 20 Pa; A1 oxygen concentration was measured at 21%."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
        for label, expression, unit in [
            ("pressure", "20", "Pa"),
            ("oxygen concentration", "21", "%"),
        ]
    ]
    rows = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    assert rows[0]["status"] == "REJECTED"
    assert "EXPLICIT_DERIVATION_IS_NOT_REPORTED_MEASUREMENT" in rows[0]["reasons"]
    assert rows[1]["status"] == "SOURCE_SUPPORTED"


def test_author_citation_in_conclusion_does_not_become_current_document_result(service):
    text = "# Synthetic study\nIV. Conclusion\nSmith16 reported the earlier trend."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": "Smith16 reported the earlier trend.",
            "class_id": "NASAConclusion",
            "epistemic": "author_reported_conclusion",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, "Smith16 reported the earlier trend."),
        }
    ]
    assert validate(service, p, o)["records"][-1]["status"] != "SOURCE_SUPPORTED"


def test_all_characters_and_distributed_context(service):
    text = (
        "# Methods\n\nAll experiments were conducted in microgravity in the Synthetic study.\n\n"
        + ("Unclassified documentary context. " * 600)
        + "\n\n# Results\n\nA1 flame extinguished.\n"
    )
    p = submitted(service, text)
    d = structure(p, service.root, 1200)
    assert "".join(s["text"] for s in d["segments"]) == text
    assert d["coverage"]["source_characters"] == d["coverage"]["segmented_characters"]
    assert len(d["segments"]) > 10
    assert any(
        "All experiments" in a["quote"] for a in context_for(d["segments"][-1], d)["anchors"]
    )
    r = service.prepare_scientific(p["id"], Settings(root=service.root, nvidia_api_key=None))
    assert r["processing"]["new_model_calls"] == 0
    assert any("A1 flame extinguished" in s["text"] for s in r["package"]["statements"])
    assert service.validate_originals(r["package"]) == []


def test_exact_source_scope_and_negative_assignments(service):
    text = "Run A1 was tested in microgravity at airflow velocity 20 cm/s; run A2 was tested in normal-gravity at airflow velocity 10 cm/s.\nA1 flame extinguished.\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a1", "A1", "ExperimentalRun", text),
        entity(p, "a2", "A2", "ExperimentalRun", text),
        entity(p, "mg", "microgravity", "ExperimentalCondition", text),
        entity(p, "ng", "normal-gravity", "ExperimentalCondition", text),
    ]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "airflow velocity",
            "expression": "20",
            "unit": "cm/s",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    o["relations"] = [
        {
            "subject": "a1",
            "object": "mg",
            "relation": "hasGravityCondition",
            "support": support(p, text),
        }
    ]
    o["statements"] = [
        {
            "text": "A1 flame extinguished.",
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["a1"],
            "study": "current",
            "support": support(p, "A1 flame extinguished."),
        }
    ]
    r = validate(service, p, o)
    assert all(x["status"] == "SOURCE_SUPPORTED" for x in r["records"])
    wrong = copy.deepcopy(o)
    wrong["quantities"][0]["subject"] = "a2"
    wrong["relations"][0]["object"] = "ng"
    wrong["statements"][0]["subjects"] = ["a2"]
    result = validate(service, p, wrong)
    records = result["records"]
    assert all(
        x["status"] != "SOURCE_SUPPORTED"
        for x in records
        if x["kind"] in {"relations", "statements"}
    )
    # A2 never receives A1's value: it is revalidated on A1, the only subject it fits.
    [moved] = [x for x in records if x["kind"] == "quantities"]
    assert moved["subject"] == result["entities_by_key"]["a1"]["id"]
    assert moved["subject_recovery"]["proposed_subject"] == result["entities_by_key"]["a2"]["id"]
    wrong["quantities"][0]["subject"] = "a1"
    assert (
        next(x for x in validate(service, p, wrong)["records"] if x["kind"] == "quantities")[
            "status"
        ]
        == "SOURCE_SUPPORTED"
    )


@pytest.mark.parametrize(
    ("text", "role", "cls"),
    [
        ("A1 flame shall be observed and recorded.", "measured_observation", "ReportedObservation"),
        ("A1 extinction may result from heat loss.", "measured_observation", "ReportedObservation"),
        ("A1 simulated flame extinguished.", "measured_observation", "ReportedObservation"),
        ("A1 initial pressure was set to 20 Pa.", "reported_quantity", "Measurement"),
    ],
)
def test_epistemic_upgrades_rejected(service, text, role, cls):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    if role == "reported_quantity":
        o["quantities"] = [
            {
                "subject": "a1",
                "label": "pressure",
                "expression": "20",
                "unit": "Pa",
                "epistemic": role,
                "support": support(p, text),
            }
        ]
    else:
        o["statements"] = [
            {
                "text": text,
                "class_id": cls,
                "epistemic": role,
                "subjects": ["a1"],
                "study": "current",
                "support": support(p, text),
            }
        ]
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"


def test_no_self_approval_and_unknown_concept_staged(service):
    text = "A1 used a porous radiative shield. A1 flame extinguished."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["concepts"] = [
        {
            "kind": "class",
            "term": "porous radiative shield",
            "definition": "Source-described shield",
            "parent_or_existing": None,
            "why_existing_insufficient": "No existing shield contract",
            "support": support(p, text),
        }
    ]
    c = client_for(o)
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=3, max_total_tokens=100000),
        client=c,
    )
    assert result["package"]["scientific_extraction"]["scientific_approval"] == "NONE"
    assert result["package"]["extensions"] == []
    assert (
        result["package"]["scientific_extraction"]["semantic_mappings"][0]["activation"] == "NONE"
    )
    assert not service.validate(result["package"])["ready"]
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0
    assert service.registry.staged_semantic_candidates()
    with pytest.raises(ValueError):
        Output.model_validate({**o, "approved": True})


def test_caching_resume_and_version_idempotence(service):
    text = "Run A1 was tested in microgravity. A1 flame extinguished."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    c = client_for(o)
    settings = Settings(root=service.root)
    budget = ExtractionBudget(max_model_calls=3, max_total_tokens=100000)
    first = service.prepare_scientific(
        p["id"], settings, model_enabled=True, budget=budget, client=c
    )
    second = service.prepare_scientific(
        p["id"], settings, model_enabled=True, budget=budget, client=c
    )
    assert second["digest"] == first["digest"]
    assert second["processing"]["new_model_calls"] == 0
    assert second["processing"]["cached_segments"] == 3
    assert c.client.with_options.return_value.chat.completions.create.call_count == 3
    for _ in range(3):
        service.regenerate(second["package"])
        assert service.save(second["package"], "tester")["digest"] == first["digest"]
    assert service.validate_originals(second["package"]) == []


def test_failed_segment_retry_and_budget(service):
    p = submitted(service, "A1 flame extinguished.\n\n" + ("Documentary context. " * 180))
    c = client_for(Output().model_dump())
    c.client.with_options.return_value.chat.completions.create.side_effect = [
        RuntimeError("Synthetic provider failure"),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"entities": []}'), finish_reason="stop"
                )
            ],
            usage=None,
        ),
    ]
    settings = Settings(root=service.root)
    first = service.prepare_scientific(
        p["id"],
        settings,
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=1, segment_chars=1200),
        client=c,
    )
    assert first["processing"]["new_model_calls"] == 1
    assert first["processing"]["outcomes"][0]["model"] == "FAILED"
    second = service.prepare_scientific(
        p["id"],
        settings,
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=1, segment_chars=1200),
        client=c,
    )
    assert second["processing"]["outcomes"][0]["model"] == "COMPLETE"
    assert second["processing"]["status"] == "PARTIAL_MODEL_COVERAGE"
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0


def test_unit_and_cited_current_validation(service):
    text = "Previous study P1 reported pressure 20 Pa. Current run A1 was tested at pressure 10 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "p1", "P1", "ExperimentalRun", text, "cited"),
        entity(p, "a1", "A1", "ExperimentalRun", text),
    ]
    o["quantities"] = [
        {
            "subject": "p1",
            "label": "pressure",
            "expression": "20",
            "unit": "kPa",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    o["relations"] = [
        {
            "subject": "a1",
            "object": "p1",
            "relation": "belongsToInvestigation",
            "support": support(p, text),
        }
    ]
    assert all(
        r["status"] == "REJECTED"
        for r in validate(service, p, o)["records"]
        if r["kind"] != "entities"
    )


def test_integrity_and_model_unavailability(service):
    p = submitted(service, "A1 flame shall be observed. A1 flame might extinguish.")
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root, nvidia_api_key=None), model_enabled=True
    )
    assert result["processing"]["new_model_calls"] == 0
    assert result["processing"]["status"] == "PARTIAL_MODEL_COVERAGE"
    assert any(
        r["proposal"].get("epistemic") == "normative_requirement"
        for r in result["package"]["scientific_extraction"]["records"]
    )
    mutated = copy.deepcopy(result["package"])
    mutated["evidence"][0]["locator"]["page"] = 2
    assert service.validate_originals(mutated)


def test_explicit_current_study_conclusion_and_normative_reasoning(service):
    text = "# Methods\n\nRun A1 was performed as part of the XYZ experiment in microgravity.\n\n# Conclusions\n\nThe results show that the XYZ flame extinguished.\nThe boundary temperature must be fairly constant.\n"
    package = submitted(service, text)
    result = service.prepare_scientific(package["id"], Settings(root=service.root))
    records = result["package"]["scientific_extraction"]["records"]
    assert any(r["kind"] == "relations" and r["status"] == "SOURCE_SUPPORTED" for r in records)
    assert any(
        r["kind"] == "statements"
        and r["proposal"]["epistemic"] == "author_reported_conclusion"
        and r["status"] == "SOURCE_SUPPORTED"
        for r in records
    )
    assert not any(
        s["epistemic"] == "normative_requirement" and "constant" in s["text"]
        for s in result["package"]["statements"]
    )


def test_partial_schema_preserves_other_items():
    from nasa_fire_ai.ingestion.document_extraction import parse_model_output

    result, errors = parse_model_output(
        json.dumps(
            {
                "entities": [{"key": "bad", "label": "A1", "class_id": "ExperimentalRun"}],
                "statements": [
                    {
                        "text": "An exact source observation.",
                        "class_id": "ReportedObservation",
                        "epistemic": "measured_observation",
                        "support": [
                            {"evidence_id": "E-test", "quote": "An exact source observation."}
                        ],
                    }
                ],
            }
        )
    )
    assert len(result["statements"]) == 1
    assert result["entities"] == []
    assert errors[0]["kind"] == "entities"


def test_existing_ontology_extinction_is_reused(service):
    text = "The source describes Extinction of the sample."
    package = submitted(service, text)
    output = Output().model_dump()
    output["concepts"] = [
        {
            "kind": "class",
            "term": "Extinction",
            "definition": "A source-described phenomenon",
            "parent_or_existing": None,
            "why_existing_insufficient": "Proposed unnecessarily",
            "support": support(package, text),
        }
    ]
    result = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=3, max_total_tokens=100000),
        client=client_for(output),
    )
    record = next(
        r for r in result["package"]["scientific_extraction"]["records"] if r["kind"] == "concepts"
    )
    assert record["mapping"]["kind"] == "existing_concept"
    assert record["reasons"] == ["EXISTING_CONCEPT_REUSE_REQUIRED"]
    assert service.semantic.class_metadata.get("Extinction") is None


def test_cited_study_cannot_label_itself_current(service):
    text = "Previous study P1 reported a flame. Current run A1 was tested."
    package = submitted(service, text)
    output = Output().model_dump()
    output["entities"] = [entity(package, "p1", "P1", "ExperimentalRun", text, "current")]
    assert validate(service, package, output)["records"][0]["status"] == "REJECTED"


def test_shared_methods_context_and_local_exception(service):
    methods = "All G tests were conducted in microgravity, except A2.\nRun A1 was part of group G.\nRun A2 was part of group G.\nA2 was tested in normal-gravity."
    package = submitted(
        service, methods + "\n\n# Results\n\nA1 flame extinguished. A2 flame continued to burn."
    )
    output = Output().model_dump()
    output["entities"] = [
        entity(package, "a1", "A1", "ExperimentalRun", methods),
        entity(package, "a2", "A2", "ExperimentalRun", methods),
        entity(package, "g", "G", "ExperimentFamily", methods),
        entity(package, "mg", "microgravity", "GravityCondition", methods),
        entity(package, "ng", "normal-gravity", "GravityCondition", methods),
    ]
    output["relations"] = [
        {
            "subject": "a1",
            "object": "mg",
            "relation": "hasGravityCondition",
            "support": support(package, methods),
        },
        {
            "subject": "a2",
            "object": "ng",
            "relation": "hasGravityCondition",
            "support": support(package, methods),
        },
    ]
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    document = structure(package, service.root)
    result = validate_output(output, package, document, extraction_semantic(service, package))
    relations = [r for r in result["records"] if r["kind"] == "relations"]
    assert all(r["status"] == "SOURCE_SUPPORTED" for r in relations)
    assert (
        relations[0]["context_resolution"]["resolution"]["status"] == "VERIFIED_APPLICABLE_CONTEXT"
    )
    assert relations[1]["context_resolution"]["resolution"]["status"] == "EXPLICIT_LOCAL"
    wrong = copy.deepcopy(output)
    wrong["relations"][1]["object"] = "mg"
    records = validate_output(wrong, package, document, extraction_semantic(service, package))[
        "records"
    ]
    assert records[-1]["status"] == "REJECTED"
    assert "LOCAL_SOURCE_CONTEXT_CONTRADICTS_PROPOSED_GRAVITY" in records[-1]["reasons"]


def test_table_attributes_preserve_values_units_and_roles(service):
    source = b"Run,Material,Gravity,Sample Thickness (cm),Airflow (cm/s),Burn Time (s)\nA1,PMMA,microgravity,0.37,20,420\nA2,PMMA,normal-gravity,0.40,10,70\n"
    saved = service.submit(
        "Synthetic table", "Explicitly synthetic", [("source.csv", source)], "tester"
    )
    result = service.prepare_scientific(saved["package"]["id"], Settings(root=service.root))
    attributes = result["package"]["scientific_extraction"]["table_quantity_proposals"]
    assert len(attributes) == 6
    thickness = [a for a in attributes if a["column"] == "Sample Thickness (cm)"]
    assert [(a["original_expression"], a["value"]["reported_unit"]) for a in thickness] == [
        ("0.37", "cm"),
        ("0.40", "cm"),
    ]
    assert all(a["source_role"] == "SPECIMEN_CHARACTERISTIC" for a in thickness)
    assert all(a["scientific_review"] == "PENDING" for a in attributes)
    assert service.validate_originals(result["package"]) == []
    mutated = copy.deepcopy(result["package"])
    mutated["scientific_extraction"]["table_quantity_proposals"][0]["value"]["reported_value"] = 999
    assert (
        "Structured table quantities differ from the original cells and mapping contracts"
        in service.validate(mutated)["errors"]
    )


@pytest.mark.parametrize(
    ("raw", "expected"), [(".25", 0.25), ("1e-3", 0.001), ("~.6", 0.6), ("-2.5e+2", -250)]
)
def test_original_numeric_expression_reuses_native_grammar(raw, expected):
    value = CurationService.parse_value(raw, "cm/s", None)
    assert value["reported_value"] == expected
    assert value["raw_expression"] == raw
    assert value["reported_unit"] == "cm/s"


def test_small_pdf_pages_share_bounded_model_window(service):
    import pymupdf

    pdf = pymupdf.open()
    for text in (
        "Synthetic document title",
        "Run A1 was tested in microgravity.",
        "A1 flame extinguished.",
    ):
        page = pdf.new_page()
        page.insert_text((50, 50), text)
    result = service.submit(
        "Synthetic PDF", "Explicitly synthetic", [("paper.pdf", pdf.tobytes())], "tester"
    )
    client = client_for(Output().model_dump())
    prepared = service.prepare_scientific(
        result["package"]["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=1),
        client=client,
    )
    assert prepared["processing"]["new_model_calls"] == 1
    assert len(prepared["processing"]["outcomes"][0]["members"]) == 3
    payload = json.loads(
        client.client.with_options.return_value.chat.completions.create.call_args.kwargs[
            "messages"
        ][1]["content"]
    )
    assert len(payload["segments"]) == 3
    anchors = {a["id"] for a in payload["source_anchors"]}
    assert all(set(e["support"]) <= anchors for e in payload["known_entities"])
    assert service.validate_originals(prepared["package"]) == []


def test_existing_rdf_class_instances_stage_without_global_activation(service):
    package = submitted(service, "Run A1 was tested in microgravity.")
    output = Output().model_dump()
    output["entities"] = [
        entity(package, "g", "microgravity", "GravityCondition", package["evidence"][0]["text"])
    ]
    prepared = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=1),
        client=client_for(output),
    )
    assert any(e["class_id"] == "GravityCondition" for e in prepared["package"]["entities"])
    assert "GravityCondition" not in service.semantic.class_metadata
    assert prepared["package"]["extensions"] == []
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0


def test_partial_schema_replay_preserves_proposals(service):
    package = submitted(service, "Run A1 was tested in microgravity. A1 flame extinguished.")
    output = Output().model_dump()
    output["entities"] = [{"key": "bad", "label": "A1", "class_id": "ExperimentalRun"}]
    output["statements"] = [
        {
            "text": "A1 flame extinguished.",
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": [],
            "study": "unknown",
            "support": support(package, "A1 flame extinguished."),
        }
    ]
    first = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=1),
        client=client_for(output),
    )
    second = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=0),
        client=client_for(output),
    )
    assert (
        first["package"]["scientific_extraction"]["raw_proposals"]
        == second["package"]["scientific_extraction"]["raw_proposals"]
    )
    assert first["digest"] == second["digest"]


def test_staged_scientific_recovery_and_cross_section_scope(service):
    methods = "Run A1 was performed as part of the XYZ experiment at pressure 20 Pa. Run A1 was part of group G. All G tests were conducted in microgravity."
    result_sentence = "A1 flame extinguished."
    conclusion = "The results show that extinction occurred."
    p = submitted(
        service,
        "# Methods\n\n"
        + methods
        + "\n\n# Results\n\n"
        + result_sentence
        + "\n\n# Conclusions\n\n"
        + conclusion,
    )
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a1", "A1", "ExperimentalRun", methods),
        entity(p, "xyz", "XYZ", "Investigation", methods),
        entity(p, "g", "G", "ExperimentFamily", methods),
        entity(p, "mg", "microgravity", "GravityCondition", methods),
    ]
    o["statements"] = [
        {
            "text": result_sentence,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["a1"],
            "study": "current",
            "support": support(p, result_sentence),
        },
        {
            "text": conclusion,
            "class_id": "NASAConclusion",
            "epistemic": "author_reported_conclusion",
            "subjects": ["xyz"],
            "study": "current",
            "support": support(p, conclusion),
        },
    ]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": "20",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, methods),
        }
    ]
    o["relations"] = [
        {
            "subject": "a1",
            "relation": "belongsToInvestigation",
            "object": "xyz",
            "support": support(p, methods),
        },
        {
            "subject": "a1",
            "relation": "hasGravityCondition",
            "object": "mg",
            "support": support(p, methods),
        },
    ]
    c = client_for(o)
    budget = ExtractionBudget(max_model_calls=3, max_total_tokens=200000)
    first = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, budget=budget, client=c
    )
    records = first["package"]["scientific_extraction"]["records"]
    assert first["processing"]["new_model_calls"] == 3
    assert first["processing"]["status"] == "COMPLETE"
    statements = [r for r in records if r["kind"] == "statements" and r["proposal"]["subjects"]]
    assert statements and all(r["status"] == "SOURCE_SUPPORTED" for r in statements)
    assert any(r["kind"] == "quantities" and r["status"] == "SOURCE_SUPPORTED" for r in records)
    assert any(r["kind"] == "relations" and r["status"] == "SOURCE_SUPPORTED" for r in records)
    author = next(
        r for r in statements if r["proposal"]["epistemic"] == "author_reported_conclusion"
    )
    assert len(author["scope"]) == 1 and author["scope"][0] != next(
        r["entity_id"]
        for r in records
        if r["kind"] == "entities" and r["proposal"]["label"] == "A1"
    )
    assert service.validate_originals(first["package"]) == []
    assert not any(
        "differs from original" in e for e in service.validate(first["package"])["errors"]
    )
    replay = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=0, max_total_tokens=200000),
        client=c,
    )
    assert replay["digest"] == first["digest"] and replay["processing"]["new_model_calls"] == 0
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0


def test_truncated_closed_items_survive_but_window_is_incomplete(service):
    p = submitted(service, "Run A1 was tested in microgravity.")
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        a = next(a for a in request["source_anchors"] if "Run A1" in a["quote"])
        item = {
            "key": "a1",
            "label": "A1",
            "class_id": "ExperimentalRun",
            "study": "current",
            "support": [a["id"]],
        }
        raw = '{"entities": [' + json.dumps(item) + ', {"key": "unfinished'
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=raw), finish_reason="length")],
            usage=None,
        )

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    first = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=1),
        client=c,
    )
    assert first["processing"]["outcomes"][0]["model"] == "PARTIAL_SCHEMA"
    assert first["processing"]["model_characters"] == 0
    records = first["package"]["scientific_extraction"]["records"]
    assert any(
        r["kind"] == "entities"
        and r["proposal"]["label"] == "A1"
        and r["status"] == "SOURCE_SUPPORTED"
        for r in records
    )
    checkpoint = service.registry.get_phase3_cache(
        first["processing"]["outcomes"][0]["cache_key"], "scientific_document_failure"
    )
    assert checkpoint["attempt_receipts"][0]["raw_response"].endswith("unfinished")
    second = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=0),
        client=c,
    )
    assert first["digest"] == second["digest"]
    assert second["processing"]["status"] == "PARTIAL_MODEL_COVERAGE"


@pytest.mark.parametrize(
    "raw,finish",
    [
        ('{"entities": [', "stop"),
        ("[{}]", "stop"),
        ('{"entities":[],"entities":[]}', "stop"),
        ('prefix {"entities":[]', "length"),
    ],
)
def test_malformed_stage_is_not_repaired(raw, finish):
    from nasa_fire_ai.ingestion.document_extraction import parse_stage_output

    with pytest.raises((ValueError, TypeError)):
        parse_stage_output(raw, "identity", {}, finish)


@pytest.mark.parametrize(
    "support_value", [None, [], ["invented-anchor"], [{"evidence_id": "E-invented", "quote": "A1"}]]
)
def test_wire_support_must_reference_supplied_original_anchor(support_value):
    from nasa_fire_ai.ingestion.document_extraction import parse_stage_output

    item = {"key": "a1", "label": "A1", "class_id": "ExperimentalRun", "study": "current"}
    if support_value is not None:
        item["support"] = support_value
    parsed, errors = parse_stage_output(json.dumps({"entities": [item]}), "identity", {}, "stop")
    assert parsed["entities"] == [] and errors


def test_parseable_json_with_wrong_endpoint_never_completes_science(service):
    p = submitted(service, "Run A1 was tested in microgravity.")
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        if request["stage"] == "identity":
            raw = {"entities": []}
        elif request["stage"] == "propositions":
            raw = {"statements": [], "quantities": [], "concepts": []}
        else:
            a = next(a for a in request["source_anchors"] if "Run A1" in a["quote"])
            run = next(e["key"] for e in request["known_entities"] if e["label"] == "A1")
            raw = {
                "relations": [
                    {
                        "subject": run,
                        "relation": "hasGravityCondition",
                        "object": "microgravity",
                        "support": [a["id"]],
                    }
                ]
            }
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(raw)), finish_reason="stop"
                )
            ],
            usage=None,
        )

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=3, max_total_tokens=200000),
        client=c,
    )
    assert result["processing"]["outcomes"][2]["model"] == "PARTIAL_SOURCE"
    assert result["processing"]["model_characters"] == 0
    assert result["processing"]["outcomes"][2]["source_errors"][0]["reasons"] == [
        "UNKNOWN_RELATION_ENDPOINT"
    ]


def test_conflicting_entity_key_rejects_all_dependents(service):
    text = "Run A1 was tested at pressure 20 Pa. Run A2 was tested at pressure 10 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "same", "A1", "ExperimentalRun", text),
        entity(p, "same", "A2", "ExperimentalRun", text),
    ]
    o["quantities"] = [
        {
            "subject": "same",
            "label": "pressure",
            "expression": "20",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    checked = validate(service, p, o)
    assert checked["entities_by_key"] == {}
    assert all(r["status"] == "REJECTED" for r in checked["records"])


@pytest.mark.parametrize(
    "text",
    [
        "Run A1 was planned for tomorrow.",
        "Run A1 was not performed.",
        "Run A1: Pre-test flow visualization data.",
    ],
)
def test_documentary_and_planned_run_identity_cannot_support_observation(service, text):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    assert validate(service, p, o)["records"][0]["status"] == "REJECTED"


def test_documentary_rows_preserve_cells_and_do_not_propose_runs(service):
    raw = b"Run,Description,Pressure (Pa)\nA1,Performed combustion,20\nF1,Pre-test flow visualization data,\nP1,Planned run,10\n"
    p = service.submit("Synthetic table", "Explicitly synthetic", [("rows.csv", raw)], "tester")[
        "package"
    ]
    result = service.prepare_scientific(p["id"], Settings(root=service.root))
    extraction = result["package"]["scientific_extraction"]
    assert [r["role"] for r in extraction["table_row_role_proposals"]] == [
        "EXECUTION_UNRESOLVED",
        "DOCUMENTARY_OR_PLANNED",
        "DOCUMENTARY_OR_PLANNED",
    ]
    assert [
        e["label"] for e in result["package"]["entities"] if e["class_id"] == "ExperimentalRun"
    ] == ["A1"]
    assert result["package"]["tables"][0]["rows"][2]["Pressure (Pa)"] == "10"
    assert service.validate_originals(result["package"]) == []


def historical_luci_fixture(service):
    root = ROOT / "tests/fixtures/scientific_extraction"
    package = json.loads((root / "luci_package.json").read_text())
    for item in package["inputs"]:
        target = service.root / item["stored_input"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / "luci_original.pdf", target)
    payloads = [r["payload"] for r in json.loads((root / "luci_failed_payloads.json").read_text())]
    return package, payloads


def test_historical_luci_normalized_provider_proposals_still_reject_bad_science(service):
    """Saved parsed provider outputs, not reconstructions of missing raw responses."""
    p, payloads = historical_luci_fixture(service)
    saved = service.save(p, "tester")
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    for payload in payloads:
        if not payload.get("output"):
            continue
        # Preserve historical IDs and support, validate through the production validator.
        checked = validate_output(
            payload["output"],
            saved["package"],
            structure(p, service.root),
            extraction_semantic(service, p),
        )
        assert all(
            r["status"] != "SOURCE_SUPPORTED"
            for r in checked["records"]
            if r["kind"] == "relations"
        )
    assert len(payloads) == 6
    assert all("raw_response" not in v for v in payloads)


def test_original_pdf_table_quantities_keep_columns_and_do_not_assert_runs(service):
    from nasa_fire_ai.ingestion.scientific_coverage import coverage

    p, _ = historical_luci_fixture(service)
    document = structure(p, service.root)
    inventory = coverage(p, document, {"records": []}, [], [])
    cells = inventory["pdf_table_quantity_inventory"]
    assert len(cells) == 9
    assert {c["page"] for c in cells} == {33, 36}
    base = next(c for c in cells if c["original_expression"] == ".9")
    assert base["header_unit_candidate"] == "mm/s"
    assert "Partial-" in base["original_column_header"]
    assert base["original_row"][0]["original_value"] == "Flame\nBase"
    assert not any(c["scientific_execution_asserted"] for c in cells)
    assert not inventory["source_supported_relationships"]


def test_ntrs_spacesuit_fire_screening_and_unrelated_source_rejection(service):
    """Screen metadata only, with controlled acquisition; no real NASA test data invented."""
    from contextlib import nullcontext
    from unittest.mock import patch

    import pymupdf

    pdf = pymupdf.open()
    pdf.new_page().insert_text((50, 50), "Synthetic spacesuit fire test fixture.")
    adapter = Mock()
    adapter.fetch_metadata.return_value = {
        "id": 12345,
        "title": "Synthetic spacesuit fire study",
        "abstract": "Synthetic spacesuit fire testing.",
        "distribution": "PUBLIC",
        "downloads": [
            {
                "draft": False,
                "mimetype": "application/pdf",
                "links": {"pdf": "/api/citations/12345/downloads/test.pdf"},
            }
        ],
    }
    response = Mock()
    response.iter_bytes.return_value = [pdf.tobytes()]
    with patch("httpx.stream", return_value=nullcontext(response)):
        submitted_source = service.submit_ntrs("12345", "tester", adapter=adapter)
    prepared = service.prepare_scientific(
        submitted_source["package"]["id"], Settings(root=service.root, nvidia_api_key=None)
    )
    assert prepared["processing"]["new_model_calls"] == 0
    assert service.validate_originals(prepared["package"]) == []
    # Fire wording without a NASA fire-safety context is uncertain: acquired for
    # review, never silently accepted as domain knowledge.
    adapter.fetch_metadata.return_value["modified"] = "second-version"
    adapter.fetch_metadata.return_value["abstract"] = "Synthetic ignition in a laboratory."
    adapter.fetch_metadata.return_value["title"] = "Synthetic combustion laboratory"
    uncertain = pymupdf.open()
    uncertain.new_page().insert_text((50, 50), "Synthetic ignition laboratory fixture.")
    response.iter_bytes.return_value = [uncertain.tobytes()]
    with patch("httpx.stream", return_value=nullcontext(response)):
        held = service.submit_ntrs("12345", "tester", adapter=adapter)
    provenance = held["package"]["source_provenance"]
    assert provenance["eligibility"] == "OFFICIAL_NASA_DOCUMENT_DOMAIN_REVIEW_REQUIRED"
    assert provenance["eligibility_assessment"]["domain_relevance"]["status"] == "UNCERTAIN"
    # Research outside the domain is not acquired.
    adapter.fetch_metadata.return_value["modified"] = "third-version"
    adapter.fetch_metadata.return_value["abstract"] = "Synthetic planetary spectroscopy."
    adapter.fetch_metadata.return_value["title"] = "Synthetic spectroscopy survey"
    unrelated = pymupdf.open()
    unrelated.new_page().insert_text((50, 50), "Synthetic spectroscopy fixture.")
    response.iter_bytes.return_value = [unrelated.tobytes()]
    with (
        patch("httpx.stream", return_value=nullcontext(response)),
        pytest.raises(ValueError, match="relevant"),
    ):
        service.submit_ntrs("12345", "tester", adapter=adapter)


def test_saved_source_quantity_can_traverse_staged_production_pipeline(service):
    """A controlled source extraction, not a successful live Nemotron execution.

    Reuses a literal configuration sentence from a saved failed LUCI proposal.
    Numeric expression/unit are read from source, never manufactured expectations.
    """
    import re

    from nasa_fire_ai.query.numeric_mentions import NUMBER

    package, payloads = historical_luci_fixture(service)
    statement = next(
        s
        for v in payloads
        for s in v.get("output", {}).get("statements", [])
        if "steady vehicle rotation" in s["text"]
    )
    match = re.search(rf"vehicle rotation of ({NUMBER}) (\w+)", statement["text"])
    assert match
    service.save(package, package["creator"])
    c = Mock()
    from nasa_fire_ai.ingestion.document_extraction import normalized

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        anchors = [
            a["id"]
            for a in request["source_anchors"]
            if a.get("in_task", True) and normalized(statement["text"]) in normalized(a["quote"])
        ]
        result = {k: [] for k in request["schema"]["properties"]}
        if anchors and request["stage"] == "identity":
            result["entities"] = [
                {
                    "key": "rotation",
                    "label": "vehicle rotation",
                    "class_id": "ExperimentalCondition",
                    "study": "current",
                    "support": anchors[:1],
                }
            ]
        elif anchors and request["stage"] == "propositions":
            entity_key = next(
                e["key"] for e in request["known_entities"] if e["label"] == "vehicle rotation"
            )
            result["quantities"] = [
                {
                    "subject": entity_key,
                    "label": "vehicle rotation",
                    "expression": match.group(1),
                    "unit": match.group(2),
                    "epistemic": "experimental_configuration",
                    "support": anchors[:1],
                }
            ]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(result)), finish_reason="stop"
                )
            ],
            usage=None,
        )

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    for _ in range(3):
        result = service.prepare_scientific(
            package["id"],
            Settings(root=service.root),
            model_enabled=True,
            budget=ExtractionBudget(),
            client=c,
        )
        if any(
            r["kind"] == "quantities" for r in result["package"]["scientific_extraction"]["records"]
        ):
            break
    records = result["package"]["scientific_extraction"]["records"]
    quantity = next(
        r
        for r in records
        if r["kind"] == "quantities" and r["proposal"]["label"] == "vehicle rotation"
    )
    # No approved rotation quantity is invented: the unit's dimension is known,
    # so the value stands and its property is only a staged proposal.
    assert quantity["mapping"]["property_id"] is None
    assert quantity["mapping"]["kind"] == "staged_property_proposal"
    assert quantity["mapping"]["property_proposal"]["activation"] == "NONE"
    assert quantity["semantic_property_status"] == "STAGED_PROPOSAL_NOT_APPROVED"
    assert quantity["proposal"]["expression"] == match.group(1)
    assert quantity["proposal"]["unit"] == match.group(2)
    assert quantity["support_spans"][0]["checksum"] == package["inputs"][0]["sha256"]
    assert (
        result["processing"]["status"] == "PARTIAL_MODEL_COVERAGE"
    )  # Other source science was deliberately omitted by this adapter.
    assert service.validate_originals(result["package"]) == []
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0


def test_quantity_label_is_not_inferred_from_unit(service):
    text = "Run A1 was tested. A1 special reading was 20 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": "20",
            "unit": "Pa",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    assert validate(service, p, o)["records"][-1]["reasons"] == [
        "QUANTITY_NAME_NOT_IN_SOURCE_SUPPORT"
    ]


def test_observation_comparison_cannot_silently_scope_to_only_one_run(service):
    text = "Run A1 was tested. Run A2 was tested. A1 burned while A2 extinguished."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a1", "A1", "ExperimentalRun", text),
        entity(p, "a2", "A2", "ExperimentalRun", text),
    ]
    o["statements"] = [
        {
            "text": "A1 burned while A2 extinguished.",
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["a2"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    record = validate(service, p, o)["records"][-1]
    assert record["status"] == "UNRESOLVED"
    assert record["reasons"] == ["STATEMENT_MULTI_RUN_SCOPE_REQUIRES_REVIEW"]


@pytest.mark.parametrize(
    "original,expression,unit",
    [
        ("~ 20 Pa", "20", "Pa"),
        ("<20 Pa", "20", "Pa"),
        ("20 Pa", "20", "pa"),
        ("1E-3 Pa", "1e-3", "Pa"),
    ],
)
def test_quantity_qualifiers_and_case_preserve_source(service, original, expression, unit):
    text = "Run A1 was tested at pressure " + original + "."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": expression,
            "unit": unit,
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"
    o["quantities"][0]["expression"] = original.rsplit(" ", 1)[0]
    o["quantities"][0]["unit"] = "Pa"
    assert validate(service, p, o)["records"][-1]["status"] == "SOURCE_SUPPORTED"


def test_citation_author_cannot_become_an_experimental_subject(service):
    p = submitted(service, "Avery Example performed the study. Run A1 was tested.")
    p["source_provenance"] = {
        "metadata": {"authorAffiliations": [{"meta": {"author": {"name": "Example, Avery"}}}]}
    }
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "person", "Avery Example", "Investigation", p["evidence"][0]["text"])
    ]
    checked = validate(service, p, o)
    assert checked["records"][0]["status"] == "REJECTED"
    assert "AUTHOR_OR_ORGANIZATION_IS_NOT_EXPERIMENTAL_SUBJECT" in checked["records"][0]["reasons"]


@pytest.mark.parametrize("expression", ["greater than 25", "about 25", "~25", ">25"])
def test_original_quantity_qualifiers_survive_without_numeric_conversion(service, expression):
    text = f"Run A1 was tested at pressure {expression} Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": expression,
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    checked = validate(service, p, o)
    assert checked["records"][-1]["status"] != "REJECTED"
    assert checked["records"][-1]["proposal"]["expression"] == expression
    o["quantities"][0]["expression"] = "25"
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"


def test_physical_analog_gravity_is_distinct_from_numerical_simulation():
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    assert (
        role_errors(
            {
                "text": "Samples burned in simulated reduced gravity.",
                "epistemic": "measured_observation",
            }
        )
        == []
    )
    assert "DERIVED_IS_NOT_OBSERVATION" in role_errors(
        {
            "text": "Numerical model results simulated the burning in reduced gravity.",
            "epistemic": "measured_observation",
        }
    )
    assert "DERIVED_IS_NOT_OBSERVATION" in role_errors(
        {
            "text": "Predicted flame growth for samples burned in simulated reduced gravity.",
            "epistemic": "measured_observation",
        }
    )


def test_same_named_specimens_cannot_exchange_results(service):
    first = "The carbon specimen was tested at pressure 20 Pa."
    second = "The carbon specimen was tested at pressure 40 Pa."
    p = submitted(service, first + "\n" + second)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "first", "carbon specimen", "Sample", first),
        entity(p, "second", "carbon specimen", "Sample", second),
    ]
    q = {
        "subject": "first",
        "label": "pressure",
        "expression": "20",
        "unit": "Pa",
        "epistemic": "experimental_configuration",
        "support": support(p, first),
    }
    o["quantities"] = [q]
    assert validate(service, p, o)["records"][-1]["status"] != "REJECTED"
    q["subject"] = "second"
    result = validate(service, p, o)
    record = result["records"][-1]
    # The second specimen never receives the first one's value.
    assert record["subject"] == result["entities_by_key"]["first"]["id"]
    assert (
        record["subject_recovery"]["proposed_subject"]
        == (result["entities_by_key"]["second"]["id"])
    )


def test_supported_narrative_run_survives_normal_curation_identity_validation(service):
    text = "Run A1 was tested in microgravity. A1 flame extinguished."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    prepared = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=client_for(o)
    )
    package = prepared["package"]
    assert not any(
        "lacks original table-row identity" in e for e in service.validate_attribution(package)
    )
    run = next(e for e in package["entities"] if e["class_id"] == "ExperimentalRun")
    run["label"] = "invented"
    assert any(
        "lacks original table-row identity" in e for e in service.validate_attribution(package)
    )


def test_physical_pdf_group_heading_preserves_scope_and_local_exception(service):
    import pymupdf

    pdf = pymupdf.open()
    for name in ("Group Alpha", "Group Beta"):
        page = pdf.new_page()
        page.insert_text((50, 110), "Oxygen concentration was 20%.", fontsize=12)
        # PDF drawing order deliberately places the physical title after the body.
        page.insert_text((50, 50), name, fontsize=28)
    p = service.submit(
        "Synthetic heading study",
        "Synthetic fixture only",
        [("source.pdf", pdf.tobytes())],
        "tester",
    )["package"]
    pdf.close()
    d = structure(p, service.root)
    assert d["layout_headings"][p["evidence"][0]["evidence_id"]]["quote"] == "Group Alpha"
    o = Output().model_dump()
    o["entities"] = [
        {
            "key": key,
            "label": label,
            "class_id": "ExperimentFamily",
            "study": "current",
            "support": [{"evidence_id": p["evidence"][i]["evidence_id"], "quote": label}],
        }
        for i, (key, label) in enumerate((("alpha", "Group Alpha"), ("beta", "Group Beta")))
    ]
    o["quantities"] = [
        {
            "subject": "alpha",
            "label": "Oxygen concentration",
            "expression": "20",
            "unit": "%",
            "epistemic": "reported_quantity",
            "support": [
                {
                    "evidence_id": p["evidence"][0]["evidence_id"],
                    "quote": "Oxygen concentration was 20%.",
                }
            ],
        }
    ]
    assert validate_output(o, p, d, service.semantic)["records"][-1]["status"] == "SOURCE_SUPPORTED"
    o["quantities"][0]["subject"] = "beta"
    result = validate_output(o, p, d, service.semantic)
    # Beta's page never receives the value; it is revalidated under Alpha's heading.
    assert result["records"][-1]["subject"] == result["entities_by_key"]["alpha"]["id"]
    assert result["records"][-1]["subject_recovery"]["status"] == "RECOVERED"
    assert service.validate_originals(p) == []


def test_material_cannot_become_a_gravity_endpoint(service):
    text = "Run A1 was tested with a carbon sample."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a1", "A1", "ExperimentalRun", text),
        entity(p, "material", "carbon", "Material", text),
    ]
    o["relations"] = [
        {
            "subject": "a1",
            "object": "material",
            "relation": "hasGravityCondition",
            "support": support(p, text),
        }
    ]
    assert validate(service, p, o)["records"][-1]["reasons"] == [
        "RELATION_ENDPOINT_CLASS_CONTRADICTION"
    ]


def test_original_word_quantity_is_retained_without_inventing_a_numeric_measurement(service):
    text = "Run A1 was tested. A1 burn duration was over two and a half minutes."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "burn duration",
            "expression": "over two and a half",
            "unit": "minutes",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    record = validate(service, p, o)["records"][-1]
    assert record["status"] == "UNRESOLVED"
    assert record["proposal"]["expression"] == "over two and a half"
    o["quantities"][0]["expression"] = "150"
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"


def test_inequality_stays_original_proposal_and_never_becomes_exact_native_measurement(service):
    text = "Run A1 was tested. A1 pressure was measured at >25 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": ">25",
            "unit": "Pa",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=client_for(o)
    )
    records = result["package"]["scientific_extraction"]["records"]
    q = next(
        r for r in records if r["kind"] == "quantities" and r["proposal"]["expression"] == ">25"
    )
    assert q["status"] == "SOURCE_SUPPORTED"
    assert not q["native_value_compatible"]
    assert q["id"] not in {v["id"] for v in result["package"]["values"]}
    assert service.parse_value("about 25", "Pa", None)["approximate"]


def test_explicit_unit_suffix_reuses_alias_without_creating_semantic_vocabulary(service):
    text = "Run A1 was tested. A1 O2% was measured at 20%."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "O2%",
            "expression": "20",
            "unit": "%",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    before = service.contract_digest()
    record = validate(service, p, o)["records"][-1]
    assert record["status"] == "SOURCE_SUPPORTED"
    assert record["mapping"]["property_id"] == "OxygenConcentration"
    assert record["proposal"]["label"] == "O2%"
    assert service.contract_digest() == before
    o["quantities"][0]["unit"] = "Pa"
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"


def test_parallel_quantities_with_same_unit_cannot_exchange_values(service):
    text = "Run A1 was tested. A1 oxygen concentration was 20% and relative humidity was 80%."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "oxygen concentration",
            "expression": "20",
            "unit": "%",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    assert validate(service, p, o)["records"][-1]["status"] == "SOURCE_SUPPORTED"
    o["quantities"][0]["expression"] = "80"
    assert validate(service, p, o)["records"][-1]["reasons"] == [
        "QUANTITY_NAME_VALUE_NOT_LOCALLY_BOUND"
    ]


@pytest.mark.parametrize(
    "role,expected",
    [
        ("guidance", "GUIDANCE_NOT_EXPLICIT_IN_SOURCE"),
        ("normative_requirement", "NORMATIVE_ROLE_NOT_EXPLICIT_IN_SOURCE"),
        ("open_question", "OPEN_QUESTION_NOT_EXPLICIT_IN_SOURCE"),
    ],
)
def test_observation_cannot_become_guidance_requirement_or_nasa_question(role, expected):
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    assert expected in role_errors({"text": "A1 flame extinguished.", "epistemic": role})


def test_scientific_deduction_is_neither_observation_nor_manufactured_question():
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    text = "Flame extinction must be caused by other factors."
    assert "SCIENTIFIC_INFERENCE_IS_NOT_OBSERVATION" in role_errors(
        {"text": text, "epistemic": "measured_observation"}
    )
    assert "OPEN_QUESTION_NOT_EXPLICIT_IN_SOURCE" in role_errors(
        {"text": text, "epistemic": "open_question"}
    )
    assert (
        role_errors(
            {"text": "Which factors control flame extinction?", "epistemic": "open_question"}
        )
        == []
    )
    assert (
        role_errors(
            {"text": "Record the flame extinction time.", "epistemic": "normative_requirement"}
        )
        == []
    )
    assert (
        role_errors(
            {"text": "The authors recommend testing this configuration.", "epistemic": "guidance"}
        )
        == []
    )


def test_equal_numbers_in_different_quantities_do_not_inflate_coverage(service):
    from nasa_fire_ai.ingestion.scientific_coverage import coverage

    text = "Run A1 was tested. A1 oxygen concentration was 20% and relative humidity was 20%."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "oxygen concentration",
            "expression": "20",
            "unit": "%",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    d = structure(p, service.root)
    checked = validate_output(o, p, d, service.semantic)
    q = checked["records"][-1]
    assert q["status"] == "SOURCE_SUPPORTED"
    assert len(q["quantity_value_spans"]) == 1
    inventory = coverage(p, d, checked, [], [])
    assert inventory["scientific_content_identified"]["literal_quantity_occurrences"] == 2
    assert inventory["detected_quantity_occurrences_structured"] == 1


@pytest.mark.parametrize(
    ("label", "expression", "valid"),
    [
        ("width", "~3.2", True),
        ("length", "~1.5", True),
        ("width", "~1.5", False),
        ("length", "~3.2", False),
    ],
)
def test_respectively_binds_parallel_values_to_their_original_variable(
    service, label, expression, valid
):
    text = (
        "Run A1 was tested. A1 width and length were observed (~3.2 cm and ~1.5 cm respectively)."
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "run",
            "label": label,
            "expression": expression,
            "unit": "cm",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    if valid:
        # The value stands; its unapproved property is staged, never activated.
        assert r["status"] == "SOURCE_SUPPORTED"
        assert r["mapping"]["kind"] == "staged_property_proposal"
        assert r["mapping"]["property_id"] is None
        assert r["mapping"]["property_proposal"]["activation"] == "NONE"
        assert r["mapping"]["property_proposal"]["dimension"] == "length"
        assert r["quantity_value_spans"][0]["quote"] == expression + " cm"
    else:
        assert r["status"] == "REJECTED"
        assert "QUANTITY_NAME_VALUE_NOT_LOCALLY_BOUND" in r["reasons"]


def test_anaphoric_author_conclusion_has_one_original_study_antecedent(service):
    first = "QUARTZ investigation was conducted using two specimens."
    claim = "The results demonstrate that no flame propagated."
    p = submitted(service, "# Results\n" + first + " " + claim)
    o = Output().model_dump()
    o["entities"] = [entity(p, "study", "QUARTZ", "Investigation", first)]
    o["statements"] = [
        {
            "text": claim,
            "class_id": "NASAConclusion",
            "epistemic": "author_reported_conclusion",
            "subjects": ["study"],
            "study": "current",
            "support": support(p, claim),
        }
    ]
    record = validate(service, p, o)["records"][-1]
    assert record["status"] == "SOURCE_SUPPORTED"
    assert record["scope_context"]["support"][0]["quote"] == first
    assert len(record["scope"]) == 1


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        ("which will fly next year.", "UNRESOLVED"),
        ("will test two materials next year.", "UNRESOLVED"),
        ("was conducted last year. Its results will help future missions.", "SOURCE_SUPPORTED"),
    ],
)
def test_future_investigation_is_not_current_completed_research(service, suffix, expected):
    text = "QUARTZ experiment " + suffix
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "study", "QUARTZ experiment", "Investigation", text)]
    r = validate(service, p, o)["records"][0]
    assert r["status"] == expected
    if expected == "UNRESOLVED":
        assert r["research_execution_role"] == "PLANNED_FUTURE_RESEARCH"


def test_long_original_investigation_name_is_not_arbitrarily_truncated(service):
    name = "Investigation of " + "comparative material combustion configurations " * 9
    p = submitted(service, name + " was conducted using two specimens.")
    o = Output().model_dump()
    o["entities"] = [entity(p, "study", name.strip(), "Investigation", p["evidence"][0]["text"])]
    validated = Output.model_validate(o).model_dump()
    r = validate(service, p, validated)["records"][0]
    assert len(r["proposal"]["label"]) > 300
    assert r["status"] == "SOURCE_SUPPORTED"


def test_anaphoric_conclusion_cannot_choose_between_current_and_cited_studies(service):
    first = "QUARTZ investigation was conducted alongside cited ONYX investigation."
    claim = "The results demonstrate that no flame propagated."
    p = submitted(service, "# Results\n" + first + " " + claim)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "study", "QUARTZ", "Investigation", first),
        entity(p, "prior", "ONYX", "Investigation", first, study="cited"),
    ]
    o["statements"] = [
        {
            "text": claim,
            "class_id": "NASAConclusion",
            "epistemic": "author_reported_conclusion",
            "subjects": ["study"],
            "study": "current",
            "support": support(p, claim),
        }
    ]
    record = validate(service, p, o)["records"][-1]
    assert record["status"] == "UNRESOLVED"
    assert "scope_context" not in record


def test_experimental_quantity_does_not_become_a_generic_material_property(service):
    text = "PMMA oxygen concentration was 20%."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "material", "PMMA", "Material", text)]
    o["quantities"] = [
        {
            "subject": "material",
            "label": "oxygen concentration",
            "expression": "20",
            "unit": "%",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "UNRESOLVED"
    assert r["native_scope_compatible"] is False
    assert "QUANTITY_REQUIRES_EXPERIMENTAL_SCOPE_NOT_MATERIAL_CONCEPT" in r["reasons"]
    from nasa_fire_ai.ingestion.scientific_coverage import coverage

    c = coverage(p, structure(p, service.root), validate(service, p, o), [], [])
    assert c["detected_quantity_occurrences_structured"] == 0


@pytest.mark.parametrize("label", ["20", "%", "20%", "20 %"])
def test_quantity_number_or_unit_cannot_replace_variable_name(service, label):
    text = "Run A1 was tested. A1 oxygen concentration was 20%."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "run",
            "label": label,
            "expression": "20",
            "unit": "%",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "REJECTED"
    assert "QUANTITY_VALUE_OR_UNIT_IS_NOT_A_QUANTITY_NAME" in r["reasons"]


@pytest.mark.parametrize(
    ("label", "expression", "valid"),
    [
        ("width", "5", True),
        ("length", "30", True),
        ("width", "30", False),
        ("length", "5", False),
    ],
)
def test_source_dimensional_adjectives_bind_to_adjacent_values_only(
    service, label, expression, valid
):
    text = "Specimen C1 was tested. C1 was 5 cm wide x 30 cm long."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "sample", "C1", "Sample", text)]
    o["quantities"] = [
        {
            "subject": "sample",
            "label": label,
            "expression": expression,
            "unit": "cm",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    if valid:
        assert r["status"] == "SOURCE_SUPPORTED"
        assert r["mapping"]["kind"] == "staged_property_proposal"
        assert r["quantity_name_support"]["global_alias_activation"] == "NONE"
        assert r["quantity_value_spans"][0]["quote"] == expression + " cm"
        from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

        approved = validate_output(
            o, p, structure(p, service.root), extraction_semantic(service, p)
        )["records"][-1]
        assert approved["status"] == "SOURCE_SUPPORTED"
        assert approved["mapping"]["source_accessor"] == "sample_" + label
        assert approved["source_role"] == "SPECIMEN_CHARACTERISTIC"
        assert approved["native_representation"] == "STAGED_ORIGINAL_SPECIMEN_CHARACTERISTIC"
    else:
        assert r["status"] == "REJECTED"


def test_temporal_long_does_not_establish_a_spatial_length():
    from nasa_fire_ai.ingestion.document_extraction import source_dimension_adjectives

    assert source_dimension_adjectives("length", "s") == []


@pytest.mark.parametrize(
    ("clause", "expression", "unit", "valid"),
    [
        ("extinguished at 12 s", "12", "s", True),
        ("extinguished at t = 12 s", "12", "s", True),
        ("was observed at 12 s and remained visible for 20 s", "20", "s", False),
        ("was tested at 12 Pa", "12", "Pa", False),
    ],
)
def test_explicit_temporal_coordinate_requires_original_syntax_not_unit_alone(
    service, clause, expression, unit, valid
):
    text = "Run A1 was tested. A1 " + clause + "."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "run",
            "label": "time",
            "expression": expression,
            "unit": unit,
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert (r["status"] != "REJECTED") == valid
    if valid:
        assert r["quantity_name_support"]["basis"] == "EXPLICIT_SOURCE_TEMPORAL_COORDINATE"


def test_original_group_heading_resolves_material_scoped_observation_with_audit(service):
    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page()
    heading, claim = "Results Alpha: PMMA", "PMMA flame extinguished."
    page.insert_text((40, 100), claim, fontsize=12)
    page.insert_text((40, 40), heading, fontsize=25)
    p = service.submit("Synthetic study", "Test only", [("source.pdf", pdf.tobytes())], "tester")[
        "package"
    ]
    pdf.close()
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "group", heading, "ExperimentFamily", heading),
        entity(p, "material", "PMMA", "Material", claim),
    ]
    o["statements"] = [
        {
            "text": claim,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["material"],
            "study": "current",
            "support": support(p, claim),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "SOURCE_SUPPORTED"
    assert r["proposed_subjects"] == ["material"]
    assert r["proposal"]["subjects"] == ["group"]
    assert r["scope_context"]["basis"] == "EXACT_ORIGINAL_EXPERIMENT_GROUP_HEADING"
    assert r["scope_context"]["support"][0]["quote"] == heading
    assert o["statements"][0]["subjects"] == ["material"]
    o["statements"][0]["subjects"] = ["invented"]
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"


def test_late_identity_rejection_rejects_dependents_without_endpoint_substitution(service):
    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page()
    heading, claim = "Results Alpha: ceramic", "Flame extinguished."
    page.insert_text((40, 40), heading, fontsize=25)
    page.insert_text((40, 100), claim, fontsize=12)
    p = service.submit("Synthetic study", "Test only", [("source.pdf", pdf.tobytes())], "tester")[
        "package"
    ]
    pdf.close()
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "old", heading, "Investigation", heading),
        entity(p, "group", heading, "ExperimentFamily", heading),
    ]
    o["statements"] = [
        {
            "text": claim,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": [key],
            "study": "current",
            "support": support(p, claim),
        }
        for key in ("old", "group")
    ]
    checked = validate(service, p, o)
    bad, good = [r for r in checked["records"] if r["kind"] == "statements"]
    assert bad["status"] == "REJECTED"
    assert "UNKNOWN_STATEMENT_ENDPOINT" in bad["reasons"]
    assert bad["proposal"]["subjects"] == ["old"]
    assert good["status"] == "SOURCE_SUPPORTED"
    assert "old" not in checked["entities_by_key"]


@pytest.mark.parametrize(
    ("role", "cls", "text", "reason"),
    [
        (
            "measured_observation",
            "ReportedObservation",
            "PMMA flame extinguished.",
            "STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE",
        ),
        (
            "derived_quantity",
            "Measurement",
            "A1 photograph after 90 seconds of burning.",
            "DERIVATION_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE",
        ),
        (
            "experimental_configuration",
            "ExperimentalCondition",
            "A1 flame tip spread is approximately linear.",
            "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE",
        ),
        (
            "experimental_configuration",
            "ExperimentalCondition",
            "A1 oxygen concentration decreases from 20% to 15%.",
            "CHANGING_OBSERVATION_IS_NOT_ESTABLISHED_CONFIGURATION",
        ),
    ],
)
def test_concept_scope_and_unsubstantiated_roles_are_not_scientific_acceptance(
    service, role, cls, text, reason
):
    p = submitted(service, "Run A1 was tested. " + text)
    o = Output().model_dump()
    o["entities"] = (
        [entity(p, "material", "PMMA", "Material", text)]
        if "PMMA" in text
        else [entity(p, "run", "A1", "ExperimentalRun", "Run A1 was tested.")]
    )
    o["statements"] = [
        {
            "text": text,
            "class_id": cls,
            "epistemic": role,
            "subjects": [o["entities"][0]["key"]],
            "study": "current",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "UNRESOLVED"
    assert reason in r["reasons"]


@pytest.mark.parametrize(
    ("text", "role", "expected"),
    [
        ("x\ny\nSample\nFlame\ng", "measured_observation", "FIGURE_LABEL_BLOCK_IS_NOT_OBSERVATION"),
        (
            "𝑥𝑓𝑏\n𝑥𝑓𝑡\nSample\nFlame\ng\n𝑙𝑓\n𝑉𝑓",
            "measured_observation",
            "FIGURE_LABEL_BLOCK_IS_NOT_OBSERVATION",
        ),
        ("x\ny\nSample\nFlame\ng", "documentary_context", None),
        ("Temperature\nremained\nconstant", "measured_observation", None),
        ("Flame\nwas\nnot\nconstant", "measured_observation", None),
        ("The measured width was approximately 7 mm.", "measured_observation", None),
        (
            "The base was constant, so this can be approximated as growth rate.",
            "measured_observation",
            "INFERRED_APPROXIMATION_IS_NOT_DIRECT_OBSERVATION",
        ),
        (
            "Tracking fluctuations affect fits; therefore this is only an approximate relationship.",
            "measured_observation",
            "INFERRED_APPROXIMATION_IS_NOT_DIRECT_OBSERVATION",
        ),
        (
            "The base was constant, so this can be approximated as growth rate.",
            "tentative_interpretation",
            None,
        ),
    ],
)
def test_nonpropositions_and_inferences_preserve_source_role(text, role, expected):
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    errors = role_errors({"text": text, "epistemic": role})
    assert (expected in errors) if expected else not errors


@pytest.mark.parametrize(
    ("quote", "role", "expected"),
    [
        ("Alpha specimens spread rate increased to 7 mm/s.", "measured_observation", "UNRESOLVED"),
        (
            "Alpha specimens spread rate increased to 7 mm/s.",
            "derived_quantity",
            "SOURCE_SUPPORTED",
        ),
        (
            "Alpha specimens chamber pressure remained 8 Pa.",
            "measured_observation",
            "SOURCE_SUPPORTED",
        ),
    ],
)
def test_nearest_derivation_context_is_variable_specific(service, quote, role, expected):
    text = (
        "Alpha specimens were tested.\n"
        "•\nInstantaneous spread rate is the derivative of the fitted position.\n"
        f"•\n{quote}"
    )
    p = submitted(service, text)
    out = Output().model_dump()
    out["entities"] = [entity(p, "alpha", "Alpha specimens", "ExperimentFamily", text)]
    out["statements"] = [
        {
            "text": quote,
            "class_id": "Measurement" if role == "derived_quantity" else "ReportedObservation",
            "epistemic": role,
            "subjects": ["alpha"],
            "study": "current",
            "support": support(p, quote),
        }
    ]
    checked = validate(service, p, out)
    record = next(r for r in checked["records"] if r["kind"] == "statements")
    assert record["status"] == expected, record
    if "spread rate" in quote:
        assert (
            record["epistemic_context"]["basis"] == "NEAREST_ORIGINAL_DERIVATION_OF_SAME_VARIABLE"
        )
        assert any("derivative" in s["quote"] for s in record["support_spans"])
    else:
        assert "epistemic_context" not in record


@pytest.mark.parametrize(
    ("label", "unit", "property_id"),
    [
        ("Initial Pressure (psia)", "psia", "Pressure"),
        ("final pressure", "psia", "Pressure"),
        ("vapor pressure", "psia", None),  # a different quantity, not a state
        ("initial pressure", "psig", None),  # gauge is not the absolute contract
    ],
)
def test_state_qualified_label_reuses_approved_property_only(service, label, unit, property_id):
    from nasa_fire_ai.ingestion.document_extraction import resolve_source_property

    status, prop = resolve_source_property(service.semantic, label, unit)
    assert prop == property_id
    assert status == ("CANONICAL_STATE_QUALIFIED" if property_id else "UNKNOWN")


def test_unknown_property_is_staged_with_source_units_never_activated(service):
    text = "Run A1 was tested. The A1 heat of combustion was 1332 cal/g."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "run",
            "label": "heat of combustion",
            "expression": "1332",
            "unit": "cal/g",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "SOURCE_SUPPORTED"
    staged = r["mapping"]["property_proposal"]
    assert r["mapping"]["property_id"] is None
    assert staged["term"] == "heat of combustion"
    assert (staged["dimension"], staged["canonical_unit"]) == ("specific_energy", "J/kg")
    assert staged["original_units"] == ["cal/g"]
    assert staged["activation"] == "NONE" and staged["status"] == "STAGED_FOR_ONTOLOGY_REVIEW"
    assert "heat of combustion" not in {
        a for prop in service.semantic.properties.values() for a in prop.aliases
    }
    assert r["unit_interpretation"]["original_unit"] == "cal/g"


def test_subject_recovery_never_falls_back_to_the_investigation(service):
    text = "Run A1 was tested. Pressure was maintained at 20 Pa."
    p = submitted(service, "# Synthetic study\n" + text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "run", "A1", "ExperimentalRun", "Run A1 was tested."),
    ]
    o["quantities"] = [
        {
            "subject": "run",
            "label": "pressure",
            "expression": "20",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, "Pressure was maintained at 20 Pa."),
        }
    ]
    result = validate(service, p, o)
    r = result["records"][-1]
    if r["status"] == "UNRESOLVED":
        assert r["subject"] is None
        assert result["entities_by_key"]["root"]["id"] not in r["subject_recovery"]["alternatives"]
    else:
        assert r["subject"] != result["entities_by_key"]["root"]["id"]


def test_value_absent_from_source_is_rejected_even_without_a_subject(service):
    text = "Run A1 was tested. Run B1 was tested at pressure 20 Pa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was tested."),
        entity(p, "b1", "B1", "ExperimentalRun", "Run B1 was tested at pressure 20 Pa."),
    ]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": "30",
            "unit": "Pa",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "REJECTED"


@pytest.mark.parametrize(
    ("text", "label", "expression", "unit", "supported"),
    [
        (
            "Run A1 was tested. A1 flame spread rate = 1.5 mm/s.",
            "flame spread rate",
            "1.5",
            "mm/s",
            True,
        ),
        (
            "Run A1 was tested. The A1 total spread of ~6 cm was seen.",
            "total spread",
            "~6",
            "cm",
            True,
        ),
        # The name follows the value: it names an object or a criterion, not this value.
        (
            "Run A1 used a 5 s limit rather than the 15 cm burn limit.",
            "burn limit",
            "15",
            "cm",
            False,
        ),
        ("Run A1 was tested. Figure 7: 0.8 mm A1 sample, 8.2 psia.", "sample", "0.8", "mm", False),
        (
            "Run A1 used a chamber that could provide operation at 57 kPa.",
            "chamber",
            "57",
            "kPa",
            False,
        ),
        # Values of a change verb are changes, not the named states.
        (
            "Run A1 was tested. A1 length and width decrease slowly (~1.2 cm and ~0.4 cm respectively).",
            "length",
            "~1.2",
            "cm",
            False,
        ),
        (
            "Run A1 was tested. A1 flame width and length are observed (~3.2 cm and ~1.5 cm respectively).",
            "length",
            "~1.5",
            "cm",
            True,
        ),
    ],
)
def test_staged_property_requires_printed_name_value_syntax(
    service, text, label, expression, unit, supported
):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "run",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] != "REJECTED", r["reasons"]
    assert (r["status"] == "SOURCE_SUPPORTED") is supported, r["reasons"]
    assert r["mapping"]["property_id"] is None
    if not supported:
        assert "QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED" in r["reasons"]
        assert r["mapping"]["property_proposal"]["activation"] == "NONE"


def test_gravity_level_written_as_value_is_not_a_quantity_name(service):
    text = "Run A1 was tested. The 1-g experiment ended sooner."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "run",
            "label": "1-g",
            "expression": "1",
            "unit": "g",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "REJECTED"


def test_a_pressure_setting_without_a_name_of_its_own_is_named_by_its_unit(service):
    text = "Run A1 was tested at 48% O2 and 8.2 psia."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", text)]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": "pressure",
            "expression": "8.2",
            "unit": "psia",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    record = validate(service, p, o)["records"][-1]
    assert record["quantity_name_support"]["basis"] == "UNIT_ESTABLISHES_APPROVED_PROPERTY"
    assert record["mapping"]["property_id"] == "Pressure"
