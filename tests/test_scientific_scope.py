"""Synthetic source-scope positives and critical negatives; never NASA data."""

import copy

from test_document_extraction import (
    client_for,
    entity,
    submitted,
    support,
    validate,
)
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output
from nasa_fire_ai.ingestion.document_structure import structure

service = _service


def test_article_title_and_numbered_history_do_not_replace_introduction(service):
    from nasa_fire_ai.ingestion.document_extraction import section_for_span

    text = "# Synthetic study\nI. Introduction\nHistorical context is described.\n1. Testing the old apparatus\nThe old seal ruptured.\nII. Testing\nThe new seal was measured."
    p = submitted(service, text)
    d = structure(p, service.root)
    span = {"evidence_id": p["evidence"][0]["evidence_id"], "start": text.index("The old")}
    assert section_for_span(span, d) == "I. Introduction"
    span["start"] = text.index("The new")
    assert section_for_span(span, d) == "II. Testing"
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": "The old seal ruptured.",
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, "The old seal ruptured."),
        }
    ]
    assert validate(service, p, o)["records"][-1]["status"] != "SOURCE_SUPPORTED"


def test_figure_reference_binds_printed_quantity_to_exact_group_only(service):
    text = "II. Methods\nAlpha test series was conducted. Beta test series was conducted.\nIII. Results\nThe pressure was 20 kPa (Figure 1).\n\nFigure 1 - Alpha test series\n\nFigure 2 - Beta test series\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, k, label, "ExperimentFamily", label + " was conducted.")
        for k, label in [("a", "Alpha test series"), ("b", "Beta test series")]
    ]
    o["quantities"] = [
        {
            "subject": "a",
            "label": "pressure",
            "expression": "20",
            "unit": "kPa",
            "epistemic": "reported_quantity",
            "support": support(p, "The pressure was 20 kPa (Figure 1)."),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] == "SOURCE_SUPPORTED"
    assert r["scope_context"]["basis"] == "EXPLICIT_ORIGINAL_FIGURE_GROUP_REFERENCE"
    assert r["scope_context"]["image_interpretation"] is False
    o["quantities"][0]["subject"] = "b"
    result = validate(service, p, o)
    # Figure 1 prints Alpha, so Beta never receives the value.
    assert result["records"][-1]["subject"] == result["entities_by_key"]["a"]["id"]
    assert result["records"][-1]["scope_context"]["basis"] == (
        "EXPLICIT_ORIGINAL_FIGURE_GROUP_REFERENCE"
    )


def test_test_article_acronym_names_its_article_only_in_context(service):
    """Decision 2 (mandate 2026-10-25): contextual acronym linking, never substitution."""
    text = "I. Methods\nThe component tested was the Synthetic Regulator (RX) 2.0.\nII. Testing\nRX pressure was maintained at 20 kPa."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(
            p,
            "sample",
            "Synthetic Regulator (RX) 2.0",
            "Sample",
            "The component tested was the Synthetic Regulator (RX) 2.0.",
        )
    ]
    o["quantities"] = [
        {
            "subject": "sample",
            "label": "pressure",
            "expression": "20",
            "unit": "kPa",
            "epistemic": "experimental_configuration",
            "support": support(p, "RX pressure was maintained at 20 kPa."),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    # The sentence printing the value speaks about the article it defines.
    assert r["status"] == "SOURCE_SUPPORTED", r["reasons"]
    assert r["scope_context"]["basis"] == "SOURCE_DEFINED_TEST_ARTICLE_ACRONYM_NAMES_LOCAL_SUBJECT"
    assert r["scope_context"]["original_acronym"] == "RX"
    assert r["scope_context"]["global_alias_activation"] == "NONE"
    assert r["proposal"]["expression"] == "20" and r["proposal"]["unit"] == "kPa"
    o["quantities"][0]["unit"] = "Pa"
    assert validate(service, p, o)["records"][-1]["status"] == "REJECTED"


def test_a_value_measured_around_the_article_does_not_become_the_articles(service):
    # Metamorphic: the same value, printed in a clause that only orders a procedure
    # around the article, is held for review, never attributed to it.
    sentence = "Pressure was maintained at 20 kPa before re-attaching the RX."
    text = (
        "I. Methods\nThe component tested was the Synthetic Regulator (RX) 2.0.\n"
        f"II. Testing\n{sentence}"
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(
            p,
            "sample",
            "Synthetic Regulator (RX) 2.0",
            "Sample",
            "The component tested was the Synthetic Regulator (RX) 2.0.",
        )
    ]
    o["quantities"] = [
        {
            "subject": "sample",
            "label": "pressure",
            "expression": "20",
            "unit": "kPa",
            "epistemic": "experimental_configuration",
            "support": support(p, sentence),
        }
    ]
    r = validate(service, p, o)["records"][-1]
    assert r["status"] != "SOURCE_SUPPORTED"
    assert (r.get("scope_context") or {}).get("basis") != (
        "SOURCE_DEFINED_TEST_ARTICLE_ACRONYM_NAMES_LOCAL_SUBJECT"
    )


def test_the_acronym_guard_reads_the_clause_not_the_letters():
    from nasa_fire_ai.ingestion.scientific_scope import acronym_names_local_subject

    assert acronym_names_local_subject("RX", "The RX outlet pressure stayed at 120 kPa.")
    assert acronym_names_local_subject("RX", "During testing, the RX leaked at 3 kPa.")
    assert not acronym_names_local_subject("RX", "Times were logged before re-attaching the RX.")
    assert not acronym_names_local_subject("RX", "Data were taken after removing the RX.")
    # Letters inside another word are not the acronym.
    assert not acronym_names_local_subject("RX", "The RXB valve was used.")


def test_acronym_never_transfers_between_versions_or_cited_samples(service):
    from nasa_fire_ai.ingestion.scientific_scope import test_article_alias_review

    d = {
        "segments": [{"evidence_id": "e", "source_id": "s"}],
        "sections": [{"evidence_id": "e", "source_id": "s", "start": 0, "title": "II. Testing"}],
    }
    e = {
        "x": {
            "id": "x",
            "class_id": "Sample",
            "study": "current",
            "validation_status": "SOURCE_SUPPORTED",
            "source_id": "s",
            "label": "Device (RX) 2.0",
            "support": [{"quote": "The component tested was the Device (RX) 2.0."}],
        }
    }
    span = {
        "evidence_id": "e",
        "source_id": "s",
        "start": 20,
        "quote": "RX 3.0 pressure was 20 kPa.",
    }
    assert not test_article_alias_review("x", [span], e, d)
    e["x"]["study"] = "cited"
    span["quote"] = "RX pressure was 20 kPa."
    assert not test_article_alias_review("x", [span], e, d)


def test_inferred_damage_and_tentative_causes_are_not_measured_observations():
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    for text in [
        "Function was nominal, thus indicating no internal damage.",
        "The elevated temperature appeared to have softened the seal.",
        "The model confirmed negligible lag.",
    ]:
        assert role_errors({"text": text, "epistemic": "measured_observation"})
    assert not role_errors(
        {"text": "A flame appeared after ignition.", "epistemic": "measured_observation"}
    )


def test_duplicate_inference_variants_preserve_audit_but_one_active_native_assertion(service):
    p = submitted(service, "Run A1 was tested.\nA1 flame extinguished.")
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was tested.")]
    s = {
        "text": "A1 flame extinguished.",
        "class_id": "ReportedObservation",
        "epistemic": "measured_observation",
        "subjects": ["a1"],
        "study": "current",
        "support": support(p, "A1 flame extinguished."),
    }
    o["statements"] = [s, copy.deepcopy(s)]
    o["statements"][1]["support"] += support(p, "Run A1 was tested.")
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root, nvidia_api_key=None),
        model_enabled=True,
        client=client_for(o),
        budget=ExtractionBudget(max_model_calls=3),
    )
    records = result["package"]["scientific_extraction"]["records"]
    duplicates = [r for r in records if r.get("duplicate_of")]
    assert duplicates
    active = [
        s
        for s in result["package"]["statements"]
        if s.get("origin") == "contextual" and s["text"] == "A1 flame extinguished."
    ]
    assert len(active) == 1
    assert any(r["proposal"]["text"] == "A1 flame extinguished." for r in duplicates)
    rows = service.registry.db.execute(
        "SELECT review_status FROM semantic_staging WHERE json_extract(payload_json,'$.proposal.duplicate_of') IS NOT NULL"
    ).fetchall()
    assert rows and all(r[0] == "SUPERSEDED" for r in rows)


def test_cross_page_sentence_fragment_requires_original_continuation_review():
    from nasa_fire_ai.ingestion.scientific_scope import page_continuation_context

    evidence = {
        "a": {
            "evidence_id": "a",
            "source_id": "s",
            "page": 1,
            "text": "Repeated header\n1\nThe process was faster than could be",
        },
        "b": {
            "evidence_id": "b",
            "source_id": "s",
            "page": 2,
            "text": "Repeated header\n2\nachieved with the former setup. A complete sentence follows.",
        },
    }
    span = {
        "evidence_id": "b",
        "source_id": "s",
        "page": 2,
        "start": 0,
        "end": len(evidence["b"]["text"]),
        "quote": evidence["b"]["text"],
    }
    proof = page_continuation_context([span], evidence)
    assert proof and proof["evidence_id"] == "a" and "could be" in proof["quote"]
    evidence["a"]["text"] += "."
    assert not page_continuation_context([span], evidence)


def test_static_specimen_dimension_variants_merge_without_changing_original_values(service):
    p = submitted(service, "Film 5 cm wide was mounted. The film was inspected.")
    o = Output().model_dump()
    o["entities"] = [entity(p, "film", "Film 5 cm wide", "Sample", "Film 5 cm wide was mounted.")]
    q = {
        "subject": "film",
        "label": "width",
        "expression": "5",
        "unit": "cm",
        "epistemic": "experimental_configuration",
        "support": support(p, "Film 5 cm wide was mounted."),
    }
    o["quantities"] = [q, copy.deepcopy(q)]
    o["quantities"][1]["support"] = support(
        p, "Film 5 cm wide was mounted. The film was inspected."
    )
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic, validate_output

    result = validate_output(o, p, structure(p, service.root), extraction_semantic(service, p))
    qs = [r for r in result["records"] if r["kind"] == "quantities"]
    assert len(qs) == 2 and all(r["status"] == "SOURCE_SUPPORTED" for r in qs)
    assert sum(not r.get("duplicate_of") for r in qs) == 1
    assert all(r["proposal"]["expression"] == "5" and r["proposal"]["unit"] == "cm" for r in qs)
