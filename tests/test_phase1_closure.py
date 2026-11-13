"""Synthetic end-to-end checks for table rows, document scope, lineage and integrity.

Every positive has a critical negative or a metamorphic twin; never NASA data.
"""

import copy

from test_document_extraction import entity, submitted, support
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    Output,
    section_for_span,
    validate_output,
)
from nasa_fire_ai.ingestion.document_structure import structure
from nasa_fire_ai.ingestion.table_continuity import link_continuation_tables

service = _service

ROWS = [
    ["Material", "Energy (J)", "Condition", "Reactions/Tests"],
    ["aAlpha", "10", "Wet", "0/20"],
    ["", "10", "Dry", "2/20"],
    ["", "10", "Hot", "0/20"],
]
TABLE_TEXT = "\n".join(v for row in ROWS for v in row)
TEXT = (
    "# Synthetic study\nII. Results\nTABLE 1— Synthetic impact data\n"
    + TABLE_TEXT
    + "\na-\nSynthetic standard lab\n"
)


def with_tables(service, package, rows=ROWS):
    document = structure(package, service.root)
    document["detected_tables"] = link_continuation_tables(
        [
            {
                "input_sha256": package["evidence"][0]["checksum"],
                "physical_pdf_page": package["evidence"][0]["page"],
                "bbox": [0, 0, 1, 1],
                "header": rows[0],
                "header_external": False,
                "cells": rows,
            }
        ]
    )
    return document


def run(service, package, output, document):
    return validate_output(copy.deepcopy(output), package, document, service.semantic)["records"]


def proposed(records):
    """The records of the test's own proposals, without printed-structure candidates."""
    return [r for r in records if not r.get("candidate_origin")]


def quantity(expression, label="Reactions/Tests", unit=None):
    return {
        "subject": "alpha",
        "label": label,
        "expression": expression,
        "unit": unit,
        "epistemic": "reported_quantity",
    }


def table_output(package, *quantities):
    o = Output().model_dump()
    o["entities"] = [
        entity(package, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(package, "alpha", "aAlpha", "Sample", "aAlpha"),
    ]
    o["quantities"] = [{**q, "support": support(package, TABLE_TEXT)} for q in quantities]
    return o


def test_value_in_a_continuation_row_binds_to_its_row_group_and_exact_cell(service):
    p = submitted(service, TEXT)
    o = table_output(p, quantity("2/20"))
    record = proposed(run(service, p, o, with_tables(service, p)))[-1]
    assert record["status"] != "REJECTED", record["reasons"]
    binding = record["table_row_binding"]
    assert binding["status"] == "UNIQUE"
    assert binding["rows"][0]["row_context"]["Condition"] == "Dry"
    [cell] = record["quantity_value_spans"]
    text = p["evidence"][0]["text"]
    assert text[cell["start"] : cell["end"]] == "2/20" and cell["start"] == text.index("2/20")
    assert record["quantity_name_support"]["basis"] == "ORIGINAL_TABLE_COLUMN_HEADER"
    # Without the detected table the same proposal has no subject binding.
    plain = proposed(run(service, p, o, structure(p, service.root)))[-1]
    assert plain["status"] == "UNRESOLVED" and plain["subject"] is None
    assert "QUANTITY_VALUE_PRESERVED_SUBJECT_UNRESOLVED" in plain["reasons"]


def test_value_in_several_but_not_all_group_rows_stays_unresolved(service):
    p = submitted(service, TEXT)
    record = proposed(run(service, p, table_output(p, quantity("0/20")), with_tables(service, p)))[
        -1
    ]
    assert record["table_row_binding"]["status"] == "AMBIGUOUS"
    assert record["status"] == "UNRESOLVED"
    assert "TABLE_VALUE_ROW_WITHIN_GROUP_AMBIGUOUS" in record["reasons"]
    energy = proposed(
        run(service, p, table_output(p, quantity("10", "Energy", "J")), with_tables(service, p))
    )[-1]
    assert energy["table_row_binding"]["status"] == "GROUP_CONSTANT"
    assert "TABLE_VALUE_ROW_WITHIN_GROUP_AMBIGUOUS" not in energy["reasons"]


def test_table_value_needs_the_column_header_as_its_name(service):
    p = submitted(service, TEXT)
    record = proposed(
        run(service, p, table_output(p, quantity("2/20", label="Outcome")), with_tables(service, p))
    )[-1]
    assert record["status"] == "REJECTED"
    assert record["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]


def test_whole_table_rows_are_not_a_prose_statement(service):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": TABLE_TEXT,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, TABLE_TEXT),
        }
    ]
    record = proposed(run(service, p, o, with_tables(service, p)))[-1]
    assert record["status"] == "REJECTED"
    assert record["reasons"] == ["TABLE_REGION_IS_NOT_A_STATEMENT"]


LINEAGE = (
    "# Synthetic study\nII. Results\nTABLE 1— Comparison data\n"
    "Material\nEnergy (J)\nReactions/Tests\naBeta\n10\n0/20\na-\n{legend}\n"
    "Beta seals were compared.\nReferences\n[1] Smith, A. B., “Synthetic paper,” 1999.\n"
)


def lineage_record(service, legend):
    p = submitted(service, LINEAGE.format(legend=legend))
    rows = [["Material", "Energy (J)", "Reactions/Tests"], ["aBeta", "10", "0/20"]]
    o = Output().model_dump()
    o["entities"] = [entity(p, "beta", "Beta", "Material", "Beta seals were compared.")]
    return run(service, p, o, with_tables(service, p, rows))[-1]


def test_comparator_printed_only_in_cited_rows_is_not_established_as_tested_here(service):
    cited = lineage_record(service, "Data of Smith")
    assert cited["status"] == "UNRESOLVED"
    assert "CURRENT_STUDY_LINEAGE_NOT_ESTABLISHED" in cited["reasons"]
    assert cited["lineage_context"]["status"] == "CITED_OR_EXTERNAL_ONLY"
    # Same table, a legend that names no cited author: lineage is not contradicted.
    own = lineage_record(service, "Synthetic standard lab")
    assert "CURRENT_STUDY_LINEAGE_NOT_ESTABLISHED" not in own["reasons"]


def lineage_entity(service, legend, label, study, row_label="aBeta"):
    p = submitted(service, LINEAGE.format(legend=legend).replace("aBeta", row_label))
    rows = [["Material", "Energy (J)", "Reactions/Tests"], [row_label, "10", "0/20"]]
    o = Output().model_dump()
    o["entities"] = [entity(p, "beta", label, "Material", "Beta seals were compared.", study=study)]
    return proposed(run(service, p, o, with_tables(service, p, rows)))[-1]


def test_material_printed_only_in_this_studys_rows_is_not_only_cited(service):
    own = lineage_entity(service, "Synthetic standard lab", "Beta", "cited")
    assert own["status"] == "UNRESOLVED"
    assert "CITED_STUDY_CONTRADICTED_BY_CURRENT_TABLE_ROWS" in own["reasons"]
    # Rows that do carry a cited lineage leave a cited comparator as it is.
    cited = lineage_entity(service, "Data of Smith", "Beta", "cited")
    assert "CITED_STUDY_CONTRADICTED_BY_CURRENT_TABLE_ROWS" not in cited["reasons"]


def test_row_group_with_a_parenthetical_name_counts_for_the_material(service):
    current = lineage_entity(service, "Data of Smith", "Beta", "current", "aBeta (BT)")
    assert "CURRENT_STUDY_LINEAGE_NOT_ESTABLISHED" in current["reasons"]
    # A different name that merely starts the same way is not the same material.
    other = lineage_entity(service, "Data of Smith", "Bet", "current", "aBeta (BT)")
    assert "CURRENT_STUDY_LINEAGE_NOT_ESTABLISHED" not in other["reasons"]


SCOPE = (
    "# Synthetic study\nII. Results\n{before}"
    "Alpha seals were tested at 10 J and passed with no reactions.\n"
    "References\n[1] Smith, A. B., “Synthetic paper,” 1999.\n"
)
OBSERVED = "Alpha seals were tested at 10 J and passed with no reactions."


def scope_record(service, before, text=OBSERVED):
    p = submitted(service, SCOPE.format(before=before))
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "alpha", "Alpha", "Material", OBSERVED),
    ]
    o["statements"] = [
        {
            "text": text,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["alpha"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    return run(service, p, o, structure(p, service.root))[-1]


def test_own_results_section_scopes_a_material_statement_to_the_one_investigation(service):
    record = scope_record(service, "")
    assert record["scope_context"]["basis"] == (
        "ORIGINAL_RESEARCH_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE"
    )
    assert record["proposed_subjects"] == ["alpha"]
    assert "STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE" not in record["reasons"]


def test_cited_work_named_just_before_keeps_the_statement_out_of_current_scope(service):
    for before in ("The comparison data come from Smith. ", "The data are in Table 4 [1]. "):
        record = scope_record(service, before)
        assert "STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE" in record["reasons"]
        assert record["status"] == "UNRESOLVED"


def test_material_description_is_not_promoted_to_a_current_observation(service):
    text = "Alpha resin is a virgin granular resin."
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "alpha", "Alpha", "Material", text),
    ]
    o["statements"] = [
        {
            "text": text,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["alpha"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert record["status"] == "UNRESOLVED"
    assert "STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE" in record["reasons"]


def test_one_sentence_accepted_with_two_incompatible_roles_is_held(service):
    text = "Alpha seals were tested at 10 J and passed with no reactions."
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    base = {"text": text, "subjects": ["root"], "study": "current", "support": support(p, text)}
    o["statements"] = [
        {**base, "class_id": "ReportedObservation", "epistemic": "measured_observation"},
        {**base, "class_id": "Publication", "epistemic": "documentary_context"},
    ]
    records = [
        r for r in run(service, p, o, structure(p, service.root)) if r["kind"] == "statements"
    ]
    assert all(r["status"] == "UNRESOLVED" for r in records)
    assert all("CONFLICTING_ROLE_PROPOSALS_FOR_SAME_SOURCE_SPAN" in r["reasons"] for r in records)


def test_two_values_in_one_expression_are_not_one_quantity(service):
    text = "The regulator offered ~.9 and 4.3 psid set-points."
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["quantities"] = [
        {
            "subject": "root",
            "label": "set-point",
            "expression": "~.9 and 4.3",
            "unit": "psid",
            "epistemic": "reported_quantity",
            "support": support(p, text),
        }
    ]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert record["reasons"] == ["QUANTITY_EXPRESSION_LISTS_SEPARATE_VALUES"]


def test_first_word_of_a_section_title_is_not_an_outline_prefix(service):
    text = (
        "# Synthetic study\nIntroduction\nBackground words.\nExperimental\nTest Apparatus\n"
        "The rig was built.\nResults and Discussion\nAlpha passed.\nA. Subsection\nBeta passed.\n"
    )
    p = submitted(service, text)
    d = structure(p, service.root)
    span = {"evidence_id": p["evidence"][0]["evidence_id"]}
    assert section_for_span({**span, "start": text.index("The rig")}, d) == (
        "Experimental\nTest Apparatus"
    )
    assert section_for_span({**span, "start": text.index("Alpha passed")}, d) == (
        "Results and Discussion"
    )
    # A punctuated outline letter is still a subsection, not a new major section.
    assert section_for_span({**span, "start": text.index("Beta passed")}, d) == (
        "Results and Discussion"
    )


def test_a_value_with_its_unit_is_not_a_named_entity(service):
    text = "Each sample was impacted at 72 ft-lbs (98J) in the impact tester."
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "energy", "72 ft-lbs (98J)", "Intervention", text)]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert record["status"] == "UNRESOLVED"
    assert "NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY" in record["reasons"]
    thickness = "Both were tested at 0.062 inches in thickness."
    p = submitted(service, "# Synthetic study\nII. Results\n" + thickness + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "t", "0.062 inches", "ExperimentalCondition", thickness),
        entity(p, "run", "Run 3", "ExperimentalRun", thickness.replace("Both were", "Run 3 was")),
    ]
    held, named = run(service, p, o, structure(p, service.root))[-2:]
    assert "NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY" in held["reasons"]
    assert "NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY" not in named["reasons"]


def test_an_observation_stating_a_purpose_describes_a_procedure(service):
    text = "A post-test picture of an Alpha sample was taken in order to show the extruded layer."
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": text,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert record["status"] == "UNRESOLVED"
    assert "OBSERVATION_DESCRIBES_A_PROCEDURE" in record["reasons"]


def test_footnote_marker_printed_with_a_row_group_is_not_part_of_the_entity_name(service):
    p = submitted(service, TEXT)
    document = with_tables(service, p)
    outcomes = {}
    for label in ("aAlpha", "Alpha"):
        o = Output().model_dump()
        o["entities"] = [entity(p, "alpha", label, "ExperimentFamily", "aAlpha")]
        outcomes[label] = proposed(run(service, p, o, document))[-1]
    glued, clean = outcomes["aAlpha"], outcomes["Alpha"]
    assert glued["status"] == clean["status"] == "SOURCE_SUPPORTED"
    # Both runs name the same group; the marker is kept as an annotation.
    assert glued["proposal"]["label"] == clean["proposal"]["label"] == "Alpha"
    assert glued["entity_id"] == clean["entity_id"]
    assert glued["label_normalization"]["footnote_marker"] == "a"
    assert glued["label_normalization"]["footnote_legend"] == ["Synthetic standard lab"]
    assert clean["identity_support"]["basis"] == "LEGEND_BACKED_FOOTNOTE_MARKER_ON_ROW_GROUP_LABEL"
    assert clean["identity_support"]["printed_form"] == "aAlpha"


def test_a_letter_without_a_legend_stays_in_the_name_and_a_clean_label_is_absent(service):
    p = submitted(service, TEXT.replace("a-\nSynthetic standard lab\n", ""))
    document = with_tables(service, p)
    o = Output().model_dump()
    o["entities"] = [entity(p, "alpha", "aAlpha", "ExperimentFamily", "aAlpha")]
    kept = proposed(run(service, p, o, document))[-1]
    assert kept["status"] == "SOURCE_SUPPORTED" and kept["proposal"]["label"] == "aAlpha"
    assert "label_normalization" not in kept
    o["entities"] = [entity(p, "alpha", "Alpha", "ExperimentFamily", "aAlpha")]
    absent = proposed(run(service, p, o, document))[-1]
    assert absent["status"] == "REJECTED"
    assert absent["reasons"] == ["ENTITY_LABEL_ABSENT_FROM_SUPPORT"]


def configuration_record(service, text):
    p = submitted(service, "# Synthetic study\nII. Methods\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": text,
            "class_id": "ExperimentalCondition",
            "epistemic": "experimental_configuration",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    return run(service, p, o, structure(p, service.root))[-1]


def test_a_reagent_or_device_that_was_used_is_a_configuration(service):
    used = configuration_record(service, "A mineral oil spike was used to assure combustion.")
    assert "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE" not in used["reasons"]
    documentary = configuration_record(
        service, "The data used in this comparison were obtained from other papers."
    )
    assert "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE" in documentary["reasons"]


def test_prior_to_a_procedure_step_is_not_prior_research(service):
    from nasa_fire_ai.ingestion.document_extraction import original_research_passage

    procedure = (
        "If the temperature rises above 425 C prior to ignition, the AIT is recorded as >425 C."
    )
    lineage = "Prior to this study, Alpha had not been tested at pressure."
    text = "# Synthetic study\nII. Methods\n" + procedure + "\n" + lineage + "\n"
    p = submitted(service, text)
    d = structure(p, service.root)

    def span(sentence):
        start = text.index(sentence)
        return {
            "evidence_id": p["evidence"][0]["evidence_id"],
            "start": start,
            "end": start + len(sentence),
            "quote": sentence,
        }

    assert original_research_passage([span(procedure)], d)
    assert not original_research_passage([span(lineage)], d)


def test_unresolved_proposals_stay_for_review_but_are_never_included_as_knowledge(service):
    first, second = "Alpha seals were tested at 10 J.", "Beta seals passed every test."
    p = submitted(service, first + " " + second)
    page = p["evidence"][0]

    def record(rid, text, status, reasons):
        start = page["text"].index(text)
        return {
            "id": rid,
            "kind": "statements",
            "status": status,
            "reasons": reasons,
            "support_spans": [
                {
                    "evidence_id": page["evidence_id"],
                    "source_id": page["source_id"],
                    "page": 1,
                    "start": start,
                    "end": start + len(text),
                    "quote": text,
                }
            ],
            "proposal": {
                "text": text,
                "class_id": "ReportedObservation",
                "epistemic": "measured_observation",
                "subjects": [],
                "study": "current",
            },
        }

    p["scientific_extraction"] = {
        "records": [
            record("proposal-ok", first, "SOURCE_SUPPORTED", []),
            record(
                "proposal-held", second, "UNRESOLVED", ["STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE"]
            ),
        ],
        "entities_by_key": {},
    }
    service.attach_scientific_proposals(p)
    by_id = {s["id"]: s for s in p["statements"] if s.get("origin") == "contextual"}
    assert by_id["proposal-ok"]["included"] is True
    assert by_id["proposal-ok"]["review_status"] == "SOURCE_SUPPORTED"
    assert by_id["proposal-held"]["included"] is False
    assert by_id["proposal-held"]["review_status"] == "UNRESOLVED"
    assert by_id["proposal-held"]["review_reasons"] == ["STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE"]


def relation(package, subject, name, obj, quote):
    return {"subject": subject, "relation": name, "object": obj, "support": support(package, quote)}


def test_subject_label_names_material_only_with_a_qualifier():
    from nasa_fire_ai.ingestion.document_extraction import subject_label_names_material as names

    assert names("Brass-filled PTFE (Batch #2)", "Brass-filled PTFE")["qualifier"] == "batch #2"
    assert names("Brass-filled PTFE sample", "Brass-filled PTFE")["qualifier"] == "sample"
    assert names("Alpha\n(Lot 1)", "Alpha")["qualifier"] == "lot 1"
    for subject, material in [
        ("Viton A-500", "Viton A"),
        ("Salox-M", "Brass-filled PTFE"),
        ("Brass-filled PTFE", "PTFE"),
        ("Alpha (cited)", "Alpha"),
        ("Alpha", "Alpha"),
        ("PT", "PT"),
    ]:
        assert names(subject, material) is None


def test_a_group_or_sample_named_after_its_material_is_made_of_it(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    text = (
        "# Synthetic study\nII. Results\nAlpha was tested. Alpha (Lot 1) passed. "
        "Alpha-500 failed. Beta samples burned."
    )
    p = submitted(service, text)
    # The draft-local registry carries the ontology's madeOf once extraction exists.
    p["scientific_extraction"] = {"records": []}
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "alpha", "Alpha", "Material", "Alpha was tested."),
        entity(p, "lot", "Alpha (Lot 1)", "ExperimentFamily", "Alpha (Lot 1) passed."),
        entity(p, "a500", "Alpha-500", "Sample", "Alpha-500 failed."),
        entity(p, "beta", "Beta samples", "Sample", "Beta samples burned."),
    ]
    o["relations"] = [
        relation(p, "lot", "madeOf", "alpha", "Alpha (Lot 1) passed."),
        relation(p, "a500", "madeOf", "alpha", "Alpha-500 failed."),
        relation(p, "beta", "madeOf", "alpha", "Beta samples burned."),
        relation(p, "alpha", "madeOf", "alpha", "Alpha was tested."),
    ]
    records = validate_output(
        copy.deepcopy(o), p, structure(p, service.root), extraction_semantic(service, p)
    )["records"]
    rels = [r for r in proposed(records) if r["kind"] == "relations"]
    assert rels[0]["status"] == "SOURCE_SUPPORTED", rels[0]["reasons"]
    assert rels[0]["context_resolution"]["basis"] == "SUBJECT_LABEL_NAMES_MATERIAL"
    assert rels[0]["context_resolution"]["qualifier"] == "lot 1"
    assert all(r["status"] != "SOURCE_SUPPORTED" for r in rels[1:])
    assert rels[3]["reasons"] == ["RELATION_ENDPOINT_CLASS_CONTRADICTION"]


def test_a_cut_short_omission_recovery_is_retried_on_the_window_halves(service):
    import json
    from types import SimpleNamespace
    from unittest.mock import Mock

    from test_adaptive_extraction import response

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget

    text = (
        "Run A1 was tested at pressure 20 Pa.\n"
        + "Documentary background context. " * 45
        + "\nA1 oxygen concentration was measured at 21%."
    )
    p = submitted(service, text)
    c = Mock()
    focused = []

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        subject = request["known_entities"][0]["key"] if request["known_entities"] else "a1"
        if request["stage"] == "identity":
            a = next(a for a in request["source_anchors"] if "Run A1" in a["quote"])
            result["entities"] = [
                {
                    "key": "a1",
                    "label": "A1",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [a["id"]],
                }
            ]
        elif request["stage"] == "propositions" and request.get("focus") == "quantities":
            local = [a for a in request["source_anchors"] if a["in_task"]]
            focused.append(len(local))
            whole = any("pressure 20" in a["quote"] for a in local) and any(
                "21%" in a["quote"] for a in local
            )
            if whole:
                # The recovery request over the whole window is cut short.
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content='{"quantities":['),
                            finish_reason="length",
                        )
                    ],
                    usage=None,
                )
            candidates = request["unstructured_quantity_candidates"]
            if candidates:
                result["quantities"] = [
                    {
                        "quantity_ref": candidates[0]["id"],
                        "subject": subject,
                        "label": "oxygen concentration",
                        "epistemic": "reported_quantity",
                    }
                ]
        elif request["stage"] == "propositions":
            a = next(a for a in request["source_anchors"] if "pressure" in a["quote"])
            result["quantities"] = [
                {
                    "subject": subject,
                    "label": "pressure",
                    "expression": "20",
                    "unit": "Pa",
                    "epistemic": "experimental_configuration",
                    "support": [a["id"]],
                }
            ]
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(max_output_tokens=256),
    )
    records = result["package"]["scientific_extraction"]["records"]
    trace = [
        (o["stage"], o.get("focus"), o["model"], o["attempts"], o.get("recovery"))
        for o in result["processing"]["outcomes"]
    ]
    assert any(
        r["kind"] == "quantities" and r["proposal"]["expression"] == "21" for r in records
    ), (
        trace,
        focused,
    )
    # The halves carry fewer anchors than the whole window that was cut short.
    assert len(focused) >= 2 and min(focused) < max(focused), (trace, focused)


def test_a_normalized_identity_still_travels_with_its_printed_anchor(service):
    from nasa_fire_ai.ingestion.document_extraction import grounded_entities

    p = submitted(service, TEXT)
    document = with_tables(service, p)
    o = Output().model_dump()
    o["entities"] = [entity(p, "alpha", "aAlpha", "ExperimentFamily", "aAlpha")]
    window = {"members": document["segments"]}
    known = grounded_entities(o, p, document, service.semantic, window)
    [alpha] = [e for e in known if e["key"] == "alpha"]
    assert alpha["label"] == "Alpha" and alpha["support"] == o["entities"][0]["support"]


def observation_record(
    service, text, epistemic="measured_observation", class_id="ReportedObservation"
):
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": text,
            "class_id": class_id,
            "epistemic": epistemic,
            "subjects": ["root"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    return run(service, p, o, structure(p, service.root))[-1]


def test_rules_caveats_and_pointers_typed_as_observations_are_held(service):
    held = {
        "A sample is said to have passed the test if no reactions are recorded out of 20 samples.": "OBSERVATION_STATES_A_CRITERION",
        "The determination of compatibility cannot be made from AIT data alone.": "OBSERVATION_STATES_A_RULE_OR_CAVEAT",
        "The impact results for Alpha are shown in Table 3.": "OBSERVATION_IS_A_DOCUMENTARY_POINTER",
    }
    for text, reason in held.items():
        record = observation_record(service, text)
        assert record["status"] == "UNRESOLVED" and reason in record["reasons"], (
            text,
            record["reasons"],
        )
    observed = observation_record(
        service, "Alpha seals were tested at 10 J and passed with no reactions."
    )
    assert not any(r.startswith("OBSERVATION_") for r in observed["reasons"]), observed["reasons"]


def test_a_test_step_without_an_outcome_is_not_an_observation(service):
    step = observation_record(
        service, "Each Alpha seal was impacted with 98 J at 10,000 psia in LOX."
    )
    assert step["status"] == "UNRESOLVED" and "OBSERVATION_DESCRIBES_A_PROCEDURE" in step["reasons"]
    observed = observation_record(
        service,
        "Each Alpha seal was impacted with 98 J at 10,000 psia and passed with no reactions.",
    )
    assert not any(r.startswith("OBSERVATION_") for r in observed["reasons"]), observed["reasons"]


def test_a_validity_caveat_typed_as_an_interpretation_is_held(service):
    caveat = "These percentages are only valid for an AIT value below the maximum test temperature."
    record = observation_record(
        service, caveat, epistemic="tentative_interpretation", class_id="NASAConclusion"
    )
    assert record["status"] == "UNRESOLVED", record["reasons"]
    assert "INTERPRETATION_STATES_A_VALIDITY_CAVEAT" in record["reasons"]
    reading = observation_record(
        service,
        "Since the filler fraction is not known, it can only be speculated that the filler is zinc.",
        epistemic="tentative_interpretation",
        class_id="NASAConclusion",
    )
    assert "INTERPRETATION_STATES_A_VALIDITY_CAVEAT" not in reading["reasons"]


def test_a_validity_caveat_typed_as_a_configuration_is_held(service):
    caveat = "These percentages are only valid for an AIT value below the maximum test temperature."
    record = observation_record(
        service, caveat, epistemic="experimental_configuration", class_id="ExperimentalCondition"
    )
    assert record["status"] == "UNRESOLVED", record["reasons"]
    assert "CONFIGURATION_STATES_A_VALIDITY_CAVEAT" in record["reasons"]
    setup = observation_record(
        service,
        "The Alpha chamber was purged with oxygen before pressurization.",
        epistemic="experimental_configuration",
        class_id="ExperimentalCondition",
    )
    assert "CONFIGURATION_STATES_A_VALIDITY_CAVEAT" not in setup["reasons"]


def test_a_table_caption_with_a_dash_is_not_an_experiment_family(service):
    caption = "Table 3—Impact data of synthetic compounds"
    series = "Alpha impact series"
    p = submitted(service, "# Synthetic study\nII. Results\n" + caption + "\n" + series + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "fam", caption, "ExperimentFamily", caption)]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert record["status"] == "UNRESOLVED"
    assert "CAPTION_IS_NOT_ESTABLISHED_EXPERIMENT_IDENTITY" in record["reasons"]
    o["entities"] = [entity(p, "fam", series, "ExperimentFamily", series)]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert "CAPTION_IS_NOT_ESTABLISHED_EXPERIMENT_IDENTITY" not in record["reasons"]


TESTED = (
    "# Synthetic study\nII. Results\nTABLE 1— Comparison data\n"
    "Material\nEnergy (J)\nReactions/Tests\naBeta\n10\n0/20\na-\n{legend}\n"
    "Beta seals were compared. The Beta heat of combustion was 1332 cal/g.\n"
    "References\n[1] Smith, A. B., “Synthetic paper,” 1999.\n"
)


def material_quantity_record(service, legend):
    sentence = "The Beta heat of combustion was 1332 cal/g."
    p = submitted(service, TESTED.format(legend=legend))
    rows = [["Material", "Energy (J)", "Reactions/Tests"], ["aBeta", "10", "0/20"]]
    o = Output().model_dump()
    o["entities"] = [entity(p, "beta", "Beta", "Material", "Beta seals were compared.")]
    o["quantities"] = [
        {
            "subject": "beta",
            "label": "heat of combustion",
            "expression": "1332",
            "unit": "cal/g",
            "epistemic": "reported_quantity",
            "support": support(p, sentence),
        }
    ]
    return proposed(run(service, p, o, with_tables(service, p, rows)))[-1]


def test_prose_value_of_a_material_this_document_tests_is_scoped_to_this_study(service):
    record = material_quantity_record(service, "Synthetic standard lab")
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert record["scope_context"] == {
        "basis": "MATERIAL_ESTABLISHED_AS_TESTED_IN_THIS_STUDY",
        "experimental_scope": "DOCUMENT_INVESTIGATION",
        "general_material_property": False,
    }
    # Never projected as a general material property.
    assert record["native_scope_compatible"] is False
    # A material printed only in cited rows is not established as tested here.
    cited = material_quantity_record(service, "Data of Smith")
    assert cited["status"] == "UNRESOLVED"
    assert "QUANTITY_REQUIRES_EXPERIMENTAL_SCOPE_NOT_MATERIAL_CONCEPT" in cited["reasons"]


def test_recovery_skips_values_already_printed_in_a_table_cell(service):
    from nasa_fire_ai.ingestion.table_continuity import printed_in_table

    p = submitted(service, TEXT)
    document = with_tables(service, p)
    page = p["evidence"][0]["page"]
    assert printed_in_table(document, page, "2/20")
    assert not printed_in_table(document, page, "3/20")
    assert not printed_in_table(document, page + 1, "2/20")


IMPACT = (
    "# Synthetic study\nII. Results\nTABLE 1— Impact data\n"
    "Material\nImpact Energy (J)\nSystem Pressure (psia)\nReactions/Tests\n"
    "aBeta (Lot #1)\n98\n10,000\n0/20\na-\nSynthetic standard lab\n"
    "The data show that Beta is compatible. It was impacted with 98 Joules at 10,000 psia.\n"
    "Gamma was compared. It was impacted with 98 Joules at 10,000 psia.\n"
)
IMPACT_ROWS = [
    ["Material", "Impact Energy (J)", "System Pressure (psia)", "Reactions/Tests"],
    ["aBeta (Lot #1)", "98", "10,000", "0/20"],
]


def impact_output(p, subject_label, sentence, epistemic="experimental_configuration"):
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "beta", "Beta", "Material", "The data show that Beta is compatible."),
        entity(p, "gamma", "Gamma", "Material", "Gamma was compared."),
    ]
    o["quantities"] = [
        {
            "subject": subject_label,
            "label": "impact energy",
            "expression": "98",
            "unit": "Joules",
            "epistemic": epistemic,
            "support": support(p, sentence),
        }
    ]
    return o


def test_prose_value_named_by_its_subjects_own_table_column_and_pronoun(service):
    p = submitted(service, IMPACT)
    document = with_tables(service, p, IMPACT_ROWS)
    beta = "The data show that Beta is compatible. It was impacted with 98 Joules at 10,000 psia."
    record = proposed(run(service, p, impact_output(p, "beta", beta), document))[-1]
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert (
        record["quantity_name_support"]["basis"] == "SAME_SUBJECT_VALUE_UNDER_DOCUMENT_TABLE_COLUMN"
    )
    assert record["subject_antecedent"]["basis"] == "PRONOUN_SUBJECT_OF_PRECEDING_SENTENCE"
    # The same printed value for a material without such a row has no name.
    gamma = "Gamma was compared. It was impacted with 98 Joules at 10,000 psia."
    other = proposed(run(service, p, impact_output(p, "gamma", gamma), document))[-1]
    assert other["status"] != "SOURCE_SUPPORTED"
    # What was applied is not a measured result.
    measured = proposed(
        run(service, p, impact_output(p, "beta", beta, "reported_quantity"), document)
    )[-1]
    assert measured["status"] == "REJECTED"
    assert "APPLIED_TEST_INPUT_IS_NOT_A_MEASUREMENT" in measured["reasons"]


def test_printed_relative_difference_is_kept_as_a_derived_value(service):
    text = "Run A1 was tested. The A1 heat of combustion was 12% lower than the reference."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "run", "A1", "ExperimentalRun", text)]
    q = {
        "subject": "run",
        "label": "heat of combustion",
        "expression": "12% lower",
        "unit": None,
        "epistemic": "derived_quantity",
        "support": support(p, text),
    }
    o["quantities"] = [q]
    record = run(service, p, o, structure(p, service.root))[-1]
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert (record["proposal"]["expression"], record["proposal"]["unit"]) == ("12", "%")
    assert record["relative_comparison"]["comparative"] == "lower"
    q["epistemic"] = "reported_quantity"
    reported = run(service, p, o, structure(p, service.root))[-1]
    assert "RELATIVE_DIFFERENCE_IS_A_DERIVED_QUANTITY" in reported["reasons"]


def test_a_row_group_of_a_material_is_preferred_over_the_material(service):
    p = submitted(service, IMPACT)
    document = with_tables(service, p, IMPACT_ROWS)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "beta", "Beta", "Material", "The data show that Beta is compatible."),
        entity(p, "lot", "aBeta (Lot #1)", "Sample", "aBeta (Lot #1)"),
    ]
    rows = "\n".join(v for row in IMPACT_ROWS for v in row)
    o["quantities"] = [
        {
            "subject": "root",
            "label": "Reactions/Tests",
            "expression": "0/20",
            "unit": None,
            "epistemic": "reported_quantity",
            "support": support(p, rows.replace("aBeta (Lot #1)", "aBeta (Lot #1)")),
        }
    ]
    result = validate_output(copy.deepcopy(o), p, document, service.semantic)
    record = proposed(result["records"])[-1]
    assert record["subject"] == result["entities_by_key"]["lot"]["id"], record["reasons"]
    assert record["subject_recovery"]["status"] == "RECOVERED"


CONDITIONS = (
    "# Synthetic study\nII. Results\nTABLE 1— Impact data\n"
    "Material\nTest Conditions\nReactions/Tests\n"
    "aBeta (Lot #1)\nLOX/-200°F\n0/20\nGOX/70°F\n0/20\na-\n{legend}\n"
    "Beta was tested in LOX/-200°F and GOX/70°F.\n"
    "References\n[1] Smith, A. B., “Synthetic paper,” 1999.\n"
)
CONDITION_ROWS = [
    ["Material", "Test Conditions", "Reactions/Tests"],
    ["aBeta (Lot #1)", "LOX/-200°F", "0/20"],
    ["", "GOX/70°F", "0/20"],
]


def structural_records(service, legend="Synthetic standard lab", condition_study="current"):
    p = submitted(service, CONDITIONS.format(legend=legend))
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "beta", "Beta", "Material", "Beta was tested in LOX/-200°F and GOX/70°F."),
        entity(p, "lot", "aBeta (Lot #1)", "Sample", "aBeta (Lot #1)"),
        entity(
            p,
            "lox",
            "LOX/-200°F",
            "ExperimentalCondition",
            "tested in LOX/-200°F",
            study=condition_study,
        ),
    ]
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    records = validate_output(
        copy.deepcopy(o),
        p,
        with_tables(service, p, CONDITION_ROWS),
        extraction_semantic(service, p),
    )["records"]
    lox = next(r["entity_id"] for r in records if r["proposal"].get("key") == "lox")
    return {
        r["proposal"]["relation"]: r
        for r in records
        if r["kind"] == "relations"
        and r.get("candidate_origin") == "PRINTED_SOURCE_STRUCTURE"
        and (r["proposal"]["relation"] != "hasCondition" or r.get("object") == lox)
    }


def test_printed_structure_proposes_membership_and_row_conditions_for_validation(service):
    relations = structural_records(service)
    assert relations["madeOf"]["status"] == "SOURCE_SUPPORTED"
    condition = relations["hasCondition"]
    assert condition["status"] == "SOURCE_SUPPORTED", condition["reasons"]
    assert condition["context_resolution"]["basis"] == "SUBJECT_TABLE_ROWS_PRINT_CONDITION"
    # A cited condition entity is never attached to this study's group.
    assert "hasCondition" not in structural_records(service, condition_study="cited")
    # Rows with a cited lineage do not give this group its condition.
    assert "hasCondition" not in structural_records(service, legend="Data of Smith")


def test_values_and_instruments_are_not_named_conditions_or_interventions(service):
    text = (
        "The plummet impacted the Run 3 sample at 98 Joules of energy (72 ft-lbs). "
        "Heating at 9 degrees F/min used an external heater. A water spray was applied."
    )
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "e", "98 Joules of energy (72 ft-lbs)", "ExperimentalCondition", text),
        entity(p, "r", "9 degrees F/min", "ExperimentalCondition", text),
        entity(p, "h", "external heater", "Intervention", text),
        entity(p, "pl", "plummet", "Intervention", text),
        entity(p, "w", "water spray", "Intervention", text),
    ]
    energy, rate, heater, plummet, spray = run(service, p, o, structure(p, service.root))
    assert "NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY" in energy["reasons"]
    assert "NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY" in rate["reasons"]
    assert "APPARATUS_OR_METHOD_IS_NOT_AN_INTERVENTION" in heater["reasons"]
    assert "APPARATUS_OR_METHOD_IS_NOT_AN_INTERVENTION" in plummet["reasons"]
    assert "APPARATUS_OR_METHOD_IS_NOT_AN_INTERVENTION" not in spray["reasons"]
    named = "Run 3 used 100% PBI knit fabric in 37% O2 at 8.2 psia."
    p = submitted(service, "# Synthetic study\nII. Results\n" + named + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "m", "100% PBI knit fabric", "Material", named),
        entity(p, "a", "37% O2 at 8.2 psia", "ExperimentalCondition", named),
    ]
    for record in run(service, p, o, structure(p, service.root)):
        assert "NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY" not in record["reasons"]


SPECIMENS = (
    "# Synthetic study\nII. Results\nThe Beta samples discussed in this paper were tested.\n"
    "TABLE 1— Combustion data\nMaterial\nHeat (cal/g)\nStandard Deviation (cal/g)\n"
    "aBeta\n1332\n13.81\na-\n{legend}\n"
    "References\n[1] Smith, A. B., “Synthetic paper,” 1999.\n"
)
SPECIMEN_ROWS = [
    ["Material", "Heat (cal/g)", "Standard Deviation (cal/g)"],
    ["aBeta", "1332", "13.81"],
]


def specimen_records(service, legend):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    p = submitted(service, SPECIMENS.format(legend=legend))
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "beta", "Beta", "Material", "The Beta samples discussed in this paper"),
    ]
    return validate_output(
        copy.deepcopy(o), p, with_tables(service, p, SPECIMEN_ROWS), extraction_semantic(service, p)
    )["records"]


def test_printed_specimens_their_study_and_a_dispersion_column_are_validated_candidates(
    service,
):
    records = [
        r for r in specimen_records(service, "Synthetic standard lab") if r.get("candidate_origin")
    ]
    by = {
        (r["kind"], r["proposal"].get("label") or r["proposal"].get("relation")): r for r in records
    }
    assert by[("entities", "Beta samples")]["status"] == "SOURCE_SUPPORTED"
    member = by[("relations", "belongsToInvestigation")]
    assert member["status"] == "SOURCE_SUPPORTED", member["reasons"]
    assert member["context_resolution"]["basis"] == "SUBJECT_DISCUSSED_IN_THIS_DOCUMENT"
    spread = by[("quantities", "Standard Deviation")]
    assert spread["status"] == "SOURCE_SUPPORTED", spread["reasons"]
    assert spread["proposal"]["epistemic"] == "derived_quantity"
    # Cited rows: the material is not tested here, so no candidate is proposed.
    cited = [r for r in specimen_records(service, "Data of Smith") if r.get("candidate_origin")]
    assert not [r for r in cited if r["status"] == "SOURCE_SUPPORTED"]


def test_a_role_only_hold_is_revalidated_with_the_detected_role(service):
    rule = (
        "If the system temperature rises above 400°C prior to ignition, then the AIT is "
        "recorded as >400°C."
    )
    record = observation_record(
        service, rule, epistemic="experimental_configuration", class_id="ExperimentalCondition"
    )
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert record["proposal"]["epistemic"] == "normative_requirement"
    assert record["role_recovery"]["proposed_epistemic"] == "experimental_configuration"
    assert record["role_recovery"]["method"] == "FULL_REVALIDATION_WITH_THE_DETECTED_ROLE"


def test_a_reading_of_a_cited_table_is_never_this_studys_observation(service):
    text = (
        "TABLE 6— Synthetic impact data [1]\nMaterial\nReactions\naGamma\n2/20\n"
        "The data listed in Table 6 indicate that Gamma reacted. "
        "The reactivity of the same material increases by 20% as the thickness is halved.\n"
        "References\n[1] Smith, A. B., “Synthetic paper,” 1999.\n"
    )
    p = submitted(service, "# Synthetic study\nII. Results\n" + text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    sentence = "The reactivity of the same material increases by 20% as the thickness is halved."
    o["statements"] = [
        {
            "text": sentence,
            "class_id": "Measurement",
            "epistemic": "derived_quantity",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, sentence),
        }
    ]
    document = with_tables(service, p, [["Material", "Reactions"], ["aGamma", "2/20"]])
    document["detected_tables"][0]["caption"] = "TABLE 6— Synthetic impact data [1]"
    record = proposed(run(service, p, o, document))[-1]
    assert record["status"] != "SOURCE_SUPPORTED", record.get("role_recovery")


def test_a_column_the_document_applies_holds_settings_not_results(service):
    p = submitted(service, IMPACT)
    document = with_tables(service, p, IMPACT_ROWS)
    rows = "\n".join(v for row in IMPACT_ROWS for v in row)
    o = Output().model_dump()
    o["entities"] = [entity(p, "lot", "aBeta (Lot #1)", "Sample", "aBeta (Lot #1)")]
    o["quantities"] = [
        {
            "subject": "lot",
            "label": label,
            "expression": value,
            "unit": unit,
            "epistemic": "reported_quantity",
            "support": support(p, rows),
        }
        for label, value, unit in [
            ("System Pressure", "10,000", "psia"),
            ("Reactions/Tests", "0/20", None),
        ]
    ]
    pressure, reactions = [
        r for r in proposed(run(service, p, o, document)) if r["kind"] == "quantities"
    ]
    # "It was impacted with 98 Joules at 10,000 psia": the pressure is a setting.
    assert pressure["proposal"]["epistemic"] == "experimental_configuration", pressure["reasons"]
    assert pressure["role_recovery"]["basis"] == "COLUMN_VALUE_APPLIED_IN_A_TEST_STEP"
    # A count is never made a setting by a sentence that also counts samples.
    assert reactions["proposal"]["epistemic"] == "reported_quantity"
    assert "role_recovery" not in reactions


def test_a_columns_state_word_settles_a_setting_versus_result_conflict(service):
    text = (
        "# Synthetic study\nII. Results\nTABLE 1— AIT data\nMaterial\nInitial Pressure (psia)\n"
        "Final Pressure (psia)\naBeta\n1500\n2268\na-\nSynthetic standard lab\n"
    )
    rows = [
        ["Material", "Initial Pressure (psia)", "Final Pressure (psia)"],
        ["aBeta", "1500", "2268"],
    ]
    p = submitted(service, text)
    document = with_tables(service, p, rows)
    table = "\n".join(v for row in rows for v in row)
    o = Output().model_dump()
    o["entities"] = [entity(p, "lot", "aBeta", "Sample", "aBeta")]
    o["quantities"] = [
        {
            "subject": "lot",
            "label": name,
            "expression": value,
            "unit": "psia",
            "epistemic": role,
            "support": support(p, table),
        }
        for name, value in [("Initial Pressure", "1500"), ("Final Pressure", "2268")]
        for role in ("experimental_configuration", "reported_quantity")
    ]
    records = {
        (r["proposal"]["label"], r["proposal"]["epistemic"]): r
        for r in proposed(run(service, p, o, document))
        if r["kind"] == "quantities"
    }
    assert records[("Final Pressure", "reported_quantity")]["status"] == "SOURCE_SUPPORTED"
    assert records[("Final Pressure", "experimental_configuration")]["status"] == "UNRESOLVED"
    # "initial" makes the reported reading of the same cell the one that is wrong.
    assert records[("Initial Pressure", "reported_quantity")]["status"] != "SOURCE_SUPPORTED"


def test_a_printed_group_of_a_material_proposed_as_a_material_is_its_specimen_group(service):
    p = submitted(service, IMPACT)
    document = with_tables(service, p, IMPACT_ROWS)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "beta", "Beta", "Material", "The data show that Beta is compatible."),
        entity(p, "lot", "aBeta (Lot #1)", "Material", "aBeta (Lot #1)"),
        entity(p, "gamma", "Gamma", "Material", "Gamma was compared."),
    ]
    records = {
        r["proposal"]["key"]: r
        for r in proposed(run(service, p, o, document))
        if r["kind"] == "entities"
    }
    assert records["lot"]["proposal"]["class_id"] == "Sample"
    assert (
        records["lot"]["class_recovery"]["basis"]
        == "PRINTED_ROW_GROUP_NAMES_A_GROUP_OF_A_PROPOSED_MATERIAL"
    )
    # A material that is not a printed group of another stays a material.
    assert records["gamma"]["proposal"]["class_id"] == "Material"
    assert "class_recovery" not in records["beta"]


def test_a_detection_criterion_typed_as_an_observation_is_held(service):
    criterion = observation_record(
        service, "The indication of autogenous ignition was the rapid increase of temperature."
    )
    assert criterion["status"] == "UNRESOLVED"
    assert "OBSERVATION_STATES_A_CRITERION" in criterion["reasons"]
    seen = observation_record(service, "An indication of reaction was seen in two Alpha samples.")
    assert "OBSERVATION_STATES_A_CRITERION" not in seen["reasons"]


def test_a_procedure_typed_as_an_interpretation_is_held(service):
    step = observation_record(
        service,
        "After the tests were conducted, the samples were analyzed for signs of combustion.",
        epistemic="tentative_interpretation",
        class_id="NASAConclusion",
    )
    assert step["status"] == "UNRESOLVED"
    assert "INTERPRETATION_DESCRIBES_A_PROCEDURE" in step["reasons"]
    reading = observation_record(
        service,
        "The samples were analyzed for signs of combustion, which suggests none occurred.",
        epistemic="tentative_interpretation",
        class_id="NASAConclusion",
    )
    assert "INTERPRETATION_DESCRIBES_A_PROCEDURE" not in reading["reasons"]


def same_anaphor_record(service, before, epistemic="experimental_configuration"):
    same = "The same compounds were then tested in a high-pressure LOX environment."
    p = submitted(service, "# Synthetic study\nII. Results\n" + before + " " + same + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": same,
            "class_id": "Publication"
            if epistemic == "documentary_context"
            else "ExperimentalCondition",
            "epistemic": epistemic,
            "subjects": ["root"],
            "study": "current",
            "support": support(p, same),
        }
    ]
    return run(service, p, o, structure(p, service.root))[-1]


def test_a_same_anaphor_after_cited_work_is_not_this_study(service):
    cited = "The impact data is presented in Table 4 [3]. The compounds were not sensitive."
    record = same_anaphor_record(service, cited)
    assert record["status"] == "UNRESOLVED"
    assert "SAME_ANAPHOR_CONTINUES_CITED_WORK" in record["reasons"]
    narrative = same_anaphor_record(service, cited, epistemic="documentary_context")
    assert "SAME_ANAPHOR_CONTINUES_CITED_WORK" not in narrative["reasons"]
    own = same_anaphor_record(service, "Alpha seals were impacted at 98 J. None reacted.")
    assert "SAME_ANAPHOR_CONTINUES_CITED_WORK" not in own["reasons"]


def test_a_test_medium_is_not_a_tested_material(service):
    text = "The chamber was pressurized with GOX. Alpha seals were tested at 98 J."
    p = submitted(service, "# Synthetic study\nII. Methods\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "g", "GOX", "Material", "The chamber was pressurized with GOX."),
        entity(p, "a", "Alpha", "Material", "Alpha seals were tested at 98 J."),
    ]
    gox, alpha = run(service, p, o, structure(p, service.root))
    assert gox["status"] == "UNRESOLVED"
    assert "TEST_MEDIUM_IS_NOT_A_TESTED_MATERIAL" in gox["reasons"]
    assert "TEST_MEDIUM_IS_NOT_A_TESTED_MATERIAL" not in alpha["reasons"]


def results_record(service, text, entities, subjects, epistemic, class_id, before=""):
    p = submitted(service, "# Synthetic study\nII. Results\n" + before + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        *[entity(p, key, label, cls, quote, study) for key, label, cls, quote, study in entities],
    ]
    o["statements"] = [
        {
            "text": text,
            "class_id": class_id,
            "epistemic": epistemic,
            "subjects": subjects,
            "study": "current",
            "support": support(p, text),
        }
    ]
    return run(service, p, o, structure(p, service.root))[-1]


def test_a_cited_family_name_inside_a_current_variant_name_keeps_current_scope(service):
    named = "Alpha E2 and Alpha F7 seals were prepared here."
    text = "The E2 Alpha seals were tested at 10 J and passed with no reactions."
    record = results_record(
        service,
        text,
        [
            ("fam", "Alpha", "Material", named, "cited"),
            ("e2", "Alpha E2", "Material", named, "current"),
        ],
        ["e2"],
        "measured_observation",
        "ReportedObservation",
        before=named + " ",
    )
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert record["scope_context"]["basis"] == (
        "ORIGINAL_RESEARCH_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE"
    )


def test_a_result_held_only_for_its_conclusion_role_is_recovered_as_an_observation(service):
    def conclusion(text):
        return results_record(
            service,
            text,
            [("alpha", "Alpha", "Material", text, "current")],
            ["alpha"],
            "author_reported_conclusion",
            "NASAConclusion",
        )

    result = conclusion("It was shown that Alpha seals produced no reactions at 10 J.")
    assert result["status"] == "SOURCE_SUPPORTED", result["reasons"]
    assert result["role_recovery"]["recovered_epistemic"] == "measured_observation"
    for text in (
        "The Alpha data discussed here were obtained from preexisting documented results.",
        "Alpha seals produced no reactions, so Alpha is therefore a suitable candidate.",
    ):
        held = conclusion(text)
        assert held.get("role_recovery", {}).get("recovered_epistemic") != (
            "measured_observation"
        ), text


def test_a_material_column_name_proposed_as_an_experiment_family_is_a_material(service):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "fam", "Alpha", "ExperimentFamily", "aAlpha")]
    family = proposed(run(service, p, o, with_tables(service, p)))[-1]
    assert family["class_recovery"]["recovered_class_id"] == "Material"
    assert family["class_recovery"]["basis"] == "PRINTED_MATERIAL_COLUMN_NAMES_A_MATERIAL"


def test_a_test_method_or_measured_property_is_not_a_condition(service):
    text = "Heat of combustion and high-pressure mechanical impact tests were run in LOX."
    p = submitted(service, "# Synthetic study\nII. Methods\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "h", "Heat of combustion", "ExperimentalCondition", text),
        entity(p, "m", "high-pressure mechanical impact", "ExperimentalCondition", text),
        entity(p, "l", "LOX", "ExperimentalCondition", text),
    ]
    heat, impact, lox = run(service, p, o, structure(p, service.root))
    assert "TEST_OR_PROPERTY_IS_NOT_A_CONDITION" in heat["reasons"]
    assert "TEST_OR_PROPERTY_IS_NOT_A_CONDITION" in impact["reasons"]
    assert "TEST_OR_PROPERTY_IS_NOT_A_CONDITION" not in lox["reasons"]


def test_a_contrast_clause_does_not_bind_another_subjects_value():
    from nasa_fire_ai.ingestion.document_extraction import local_binding

    quote = (
        "Alpha passed up to a pressure of 1,500 psia, whereas Beta began reacting above 500 psia."
    )
    entities = {
        "b": {"id": "b", "label": "Beta", "class_id": "Material"},
    }
    spans = [{"quote": quote}]
    assert not local_binding("b", "1,500 psia", spans, entities)
    assert local_binding("b", "above 500 psia", spans, entities)


def test_a_documentary_figure_statement_that_reports_what_it_shows_is_held():
    from nasa_fire_ai.ingestion.statement_integrity import documented_observation

    assert documented_observation(
        "The post-test picture of a sample shows that the material is extruded."
    )
    assert documented_observation("A small sliver of the filling can be seen in the layer.")
    assert not documented_observation("The data shows that Alpha is highly compatible.")
    assert not documented_observation("The impact results are shown in Figure 3.")


def test_a_recording_rule_proposed_for_a_specimen_is_recovered_at_the_studys_scope(service):
    text = "If the sample temperature rises above 425°C, then the AIT is recorded as >425°C."
    named = "Alpha samples were prepared for the AIT test."
    record = results_record(
        service,
        text,
        [("s", "Alpha samples", "Sample", named, "current")],
        ["s"],
        "measured_observation",
        "ReportedObservation",
        before=named + " ",
    )
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert record["proposal"]["epistemic"] == "normative_requirement"
    assert record["role_recovery"]["rule_scoped_to_study"] is True
    assert record["role_recovery"]["proposed_subjects"] == ["s"]


def test_a_tentative_interpretation_must_hedge_or_infer(service):
    def tentative(text):
        return observation_record(
            service, text, epistemic="tentative_interpretation", class_id="NASAConclusion"
        )

    fact = tentative("The composition of Alpha is 40% Bronze and 60% PTFE.")
    assert "TENTATIVE_INTERPRETATION_STATES_NO_INFERENCE" in fact["reasons"]
    hedged = tentative("It can only be speculated that the filler of Alpha is Zinc.")
    assert "TENTATIVE_INTERPRETATION_STATES_NO_INFERENCE" not in hedged["reasons"]


def test_running_page_headers_are_lines_most_pages_print_at_their_edge():
    from nasa_fire_ai.ingestion.document_extraction import running_headers

    header = "Synthetic Conference on Space Systems"
    evidence = {
        str(n): {"text": f"{header}\n{n}\n{body}"}
        for n, body in enumerate(
            (
                "Alpha seals were cut.",
                "Beta was dried overnight.",
                "Gamma rings were weighed.",
                "Delta burned slowly.",
                "Epsilon did not ignite.",
            ),
            start=1,
        )
    }
    evidence["6"] = {"text": "Synthetic Conference on Space Systems is cited once here."}
    assert running_headers(evidence) == ["synthetic conference on space systems"]
    assert running_headers({"1": {"text": f"{header}\nBody."}}) == []


def test_generic_specimen_descriptions_and_instrument_readouts_are_held(service):
    text = "The reacting sample burned. Alpha (Lot 1) samples passed."
    p = submitted(service, "# Synthetic study\nII. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "g", "reacting sample", "Sample", "The reacting sample burned."),
        entity(p, "n", "Alpha (Lot 1) samples", "Sample", "Alpha (Lot 1) samples passed."),
    ]
    generic, named = run(service, p, o, structure(p, service.root))
    assert "GENERIC_DESCRIPTION_IS_NOT_A_SPECIMEN_IDENTITY" in generic["reasons"]
    assert "GENERIC_DESCRIPTION_IS_NOT_A_SPECIMEN_IDENTITY" not in named["reasons"]
    readout = observation_record(
        service, "After the test, the calorimeter displayed the gross heat content of Alpha."
    )
    assert "OBSERVATION_DESCRIBES_A_PROCEDURE" in readout["reasons"]


def test_an_inference_with_so_is_a_tentative_interpretation(service):
    record = observation_record(
        service,
        "The flame base is constant, so this can be approximated as flame growth rate.",
        epistemic="tentative_interpretation",
        class_id="NASAConclusion",
    )
    assert "TENTATIVE_INTERPRETATION_STATES_NO_INFERENCE" not in record["reasons"]


def test_a_printed_batch_row_group_of_a_tested_material_is_a_specimen_candidate(service):
    from nasa_fire_ai.ingestion.document_extraction import structure_entity_candidates

    rows = [
        ["Material", "Energy (J)", "Condition", "Reactions/Tests"],
        ["Alpha (Batch #1)", "10", "Wet", "0/20"],
        ["", "10", "Dry", "2/20"],
    ]
    text = (
        "# Synthetic study\nII. Results\nTABLE 1— Synthetic impact data\n"
        + "\n".join(v for row in rows for v in row)
        + "\n"
    )
    p = submitted(service, text)
    document = with_tables(service, p, rows)
    o = Output().model_dump()
    o["entities"] = [entity(p, "alpha", "Alpha", "Material", "Alpha (Batch #1)")]
    labels = {c["label"]: c["class_id"] for c in structure_entity_candidates(o, p, document)}
    assert labels.get("Alpha (Batch #1)") == "Sample", labels


def test_a_held_conclusion_that_is_a_rule_source_or_procedure_takes_that_role(service):
    def conclusion(text):
        return results_record(
            service,
            text,
            [("alpha", "Alpha", "Material", text, "current")],
            ["alpha"],
            "author_reported_conclusion",
            "NASAConclusion",
        )

    rule = conclusion(
        "If the Alpha temperature rises above 425°C, then the AIT is recorded as >425°C."
    )
    assert rule["status"] == "SOURCE_SUPPORTED", rule["reasons"]
    assert rule["proposal"]["epistemic"] == "normative_requirement"
    source = conclusion(
        "The Alpha data discussed here were obtained from preexisting documented results."
    )
    assert source["proposal"]["epistemic"] == "documentary_context", source["reasons"]
    result = conclusion("Alpha seals were tested at 10 J and were shown to produce zero reactions.")
    assert (
        result.get("role_recovery", {}).get("recovered_epistemic") != "experimental_configuration"
    )


def test_numeric_cells_of_a_tested_materials_own_rows_are_quantity_candidates(service):
    from nasa_fire_ai.ingestion.document_extraction import structure_quantity_candidates

    rows = [
        ["Material", "AIT (°C)", "Initial Test Pressure (psia)", "Sample Thickness (inches)"],
        ["Alpha", ">425", "1500", "0.062"],
    ]
    text = (
        "# Synthetic study\nII. Results\nTABLE 2— Synthetic AIT data\n"
        + "\n".join(v for row in rows for v in row)
        + "\n"
    )
    p = submitted(service, text)
    document = with_tables(service, p, rows)
    o = Output().model_dump()
    o["entities"] = [entity(p, "alpha", "Alpha", "Material", "Alpha")]
    roles = {c["label"]: c["epistemic"] for c in structure_quantity_candidates(o, p, document)}
    assert roles == {
        "AIT": "reported_quantity",
        "Initial Test Pressure": "experimental_configuration",
        "Sample Thickness": "experimental_configuration",
    }, roles


def test_a_name_this_studys_rows_print_under_material_is_a_material_candidate(service):
    from nasa_fire_ai.ingestion.document_extraction import structure_entity_candidates

    rows = [
        ["Material", "Energy (J)", "Reactions/Tests"],
        ["Omega E2", "98", "0/20"],
        ["Phase 3", "", ""],
    ]
    text = (
        "# Synthetic study\nII. Results\nTABLE 3— Synthetic impact data\n"
        + "\n".join(v for row in rows for v in row)
        + "\n"
    )
    p = submitted(service, text)
    document = with_tables(service, p, rows)
    o = Output().model_dump()
    o["entities"] = [entity(p, "c", "Omega E2", "Material", "Omega E2", study="cited")]
    labels = {
        c["label"]: (c["class_id"], c["study"]) for c in structure_entity_candidates(o, p, document)
    }
    assert labels.get("Omega E2") == ("Material", "current"), labels
    assert "Phase 3" not in labels


def test_a_documentary_data_source_in_the_introduction_is_scoped_to_the_study(service):
    text = "The data used to compare Alpha to other polymers was obtained from other ASTM papers."
    p = submitted(service, "# Synthetic study\nI. Introduction\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study")]
    o["statements"] = [
        {
            "text": text,
            "class_id": "Publication",
            "epistemic": "documentary_context",
            "subjects": ["root"],
            "study": "current",
            "support": support(p, text),
        }
    ]
    record = proposed(run(service, p, o, structure(p, service.root)))[-1]
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]


def test_the_purpose_of_a_step_is_not_a_planned_result(service):
    record = observation_record(
        service,
        "In order to assure that combustion will occur, a mineral oil spike was used.",
        epistemic="author_reported_conclusion",
        class_id="NASAConclusion",
    )
    assert "PLANNED_OR_COUNTERFACTUAL_IS_NOT_OBSERVATION" not in record["reasons"], record[
        "reasons"
    ]
    planned = observation_record(
        service,
        "Certification testing will be performed at the test facility.",
        epistemic="author_reported_conclusion",
        class_id="NASAConclusion",
    )
    assert planned["status"] == "REJECTED"


def test_an_unnumbered_standard_heading_is_major_in_a_roman_numbered_paper():
    from nasa_fire_ai.ingestion.scientific_scope import logical_section

    document = {
        "package_title": "Synthetic study",
        "segments": [{"evidence_id": "E1", "source_id": "S"}],
        "sections": [
            {
                "title": "II. Flammability Limits",
                "evidence_id": "E1",
                "source_id": "S",
                "start": 0,
                "end": 10,
            },
            {
                "title": "Experimental Method",
                "evidence_id": "E1",
                "source_id": "S",
                "start": 20,
                "end": 39,
            },
            {
                "title": "A. Test Facility",
                "evidence_id": "E1",
                "source_id": "S",
                "start": 40,
                "end": 55,
            },
            {
                "title": "III. Results",
                "evidence_id": "E1",
                "source_id": "S",
                "start": 90,
                "end": 102,
            },
        ],
    }
    assert logical_section({"evidence_id": "E1", "start": 60}, document) == "Experimental Method"
    assert logical_section({"evidence_id": "E1", "start": 5}, document) == "II. Flammability Limits"


def test_a_relative_clause_does_not_give_a_ducts_size_to_the_samples_in_it():
    from nasa_fire_ai.ingestion.document_extraction import local_binding

    quote = "Installed was a 7.4 cm ID by 30 cm long quartz tube duct (Fig 5) where the Alpha samples were tested."
    entities = {"s": {"id": "s", "label": "Alpha samples", "class_id": "Sample"}}
    assert not local_binding("s", "7.4 cm", [{"quote": quote}], entities)


def test_value_naming_syntax_and_printed_relative_differences(service):
    from nasa_fire_ai.ingestion.document_extraction import staged_name_syntax

    text = "The sample was exposed to a 10 cm/s primer flow and a slow flow (~30 cm/s) of gas."
    evidence = {"E": {"text": text}}

    def basis(label, quote):
        start = text.index(quote)
        record = {
            "quantity_value_spans": [
                {"evidence_id": "E", "start": start, "end": start + len(quote), "quote": quote}
            ]
        }
        return staged_name_syntax(label, record, evidence)

    assert basis("primer flow", "10 cm/s") == "PRINTED_VALUE_MODIFIES_ITS_NAME"
    assert basis("slow flow", "30 cm/s") == "PRINTED_NAME_WITH_PARENTHETICAL_VALUE"
    assert basis("chamber", "10 cm/s") is None


def test_an_acronym_form_of_a_printed_name_is_normalized_to_the_printed_name(service):
    text = "The regulator tested was the Primary Oxygen Regulator (POR) 2.0, s/n 003 here."
    p = submitted(service, "# Synthetic study\nII. Testing\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "s", "POR 2.0, s/n 003", "Sample", text)]
    record = proposed(run(service, p, o, structure(p, service.root)))[-1]
    assert record["status"] != "REJECTED", record["reasons"]
    assert record["label_normalization"]["label"] == "Primary Oxygen Regulator (POR) 2.0, s/n 003"


def test_ranges_and_short_phrases_link_a_name_to_its_value():
    from nasa_fire_ai.ingestion.document_extraction import NAME_VALUE_LINK

    assert NAME_VALUE_LINK.fullmatch(" ranged from ")
    assert NAME_VALUE_LINK.fullmatch(" during this test sequence of ~")
    assert not NAME_VALUE_LINK.fullmatch(" during 3 runs of ")


def test_slide_lines_are_separate_units_but_wrapped_prose_and_table_cells_are_not():
    from nasa_fire_ai.ingestion.document_extraction import line_units, local_binding

    slide = (
        "100% Alpha knit fabric coupons tested at 48% O2 and 8.2 psia\n"
        "Custom Beta patches sewn to outer jacket fabric tested at 37% O2 and 8.2 psia"
    )
    entities = {"a": {"id": "a", "label": "100% Alpha knit fabric coupons", "class_id": "Sample"}}
    assert not local_binding("a", "37%", [{"quote": slide}], entities)
    assert local_binding("a", "48%", [{"quote": slide}], entities)
    prose = (
        "the reaction percentage decreased in a LOX environment from 5% in batch 1\nto less than 2%"
    )
    assert line_units(prose) == prose
    cells = "GOX/75°F\n10,000\nLOX/-297°F\n10,000"
    assert line_units(cells) == cells


def test_criteria_definitions_plot_keys_fragments_and_contact_blocks_are_held(service):
    from nasa_fire_ai.ingestion.statement_integrity import documentary_pointer, stated_criterion

    assert stated_criterion(
        "If it extinguished before the end of the drop, it was identified as non-flammable."
    )
    assert stated_criterion(
        "The limit (black circle) is the highest concentration where 5 passes were observed."
    )
    assert documentary_pointer("The closed symbols at ~25 cm/s are the centrifuge data.")
    assert not stated_criterion("The flame extinguished before the end of the drop.")
    fragment = observation_record(
        service, "onset of rotation) to bring the air to near solid body rotation."
    )
    assert "STATEMENT_IS_NOT_WHOLE_SOURCE_SENTENCE" in fragment["reasons"]
    contact = observation_record(
        service, "Walker NASA JSC Project Manager mary.walker@nasa.gov reported this."
    )
    assert "STATEMENT_IS_NOT_WHOLE_SOURCE_SENTENCE" in contact["reasons"]


def test_apparatus_and_section_titles_are_not_experiment_groups(service):
    text = "Testing Methodology. The NASA GRC 5.2 second drop tower was used. Alpha Impact Test Series ran."
    p = submitted(service, "# Synthetic study\nII. Methods\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "t", "Testing Methodology", "ExperimentFamily", text),
        entity(p, "d", "NASA GRC 5.2 second drop tower", "ExperimentalCondition", text),
        entity(p, "g", "Alpha Impact Test Series", "ExperimentFamily", text),
    ]
    title, tower, group = run(service, p, o, structure(p, service.root))
    assert "APPARATUS_OR_SECTION_TITLE_IS_NOT_EXPERIMENT_GROUP" in title["reasons"]
    assert "APPARATUS_OR_SECTION_TITLE_IS_NOT_EXPERIMENT_GROUP" in tower["reasons"]
    assert "APPARATUS_OR_SECTION_TITLE_IS_NOT_EXPERIMENT_GROUP" not in group["reasons"]


def test_group_material_by_its_name_and_the_specimen_the_document_tested(service):
    from nasa_fire_ai.ingestion.document_extraction import acronym_printed_form

    assert (
        acronym_printed_form(
            "POR 2.0, s/n 003", ["the Primary Oxygen Regulator (POR) 2.0, s/n 003 here"]
        )
        == "Primary Oxygen Regulator (POR) 2.0, s/n 003"
    )
    assert acronym_printed_form("Beta 2.0", ["the Primary Oxygen Regulator (POR) 2.0"]) is None
    text = "The regulator tested was the Alpha Unit 7. First Dodecane Wetted Alpha Test Series ran."
    p = submitted(service, "# Synthetic study\nII. Testing\n" + text + "\n")
    # The draft-local registry carries the ontology's relations once extraction exists.
    p["scientific_extraction"] = {"records": []}
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "u", "Alpha Unit 7", "Sample", "The regulator tested was the Alpha Unit 7."),
        entity(p, "g", "First Dodecane Wetted Alpha Test Series", "ExperimentFamily", text),
        entity(p, "d", "dodecane", "Material", text),
    ]
    o["relations"] = [
        {"subject": "g", "relation": "hasMaterial", "object": "d", "support": support(p, text)},
    ]
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    records = validate_output(
        copy.deepcopy(o), p, structure(p, service.root), extraction_semantic(service, p)
    )["records"]
    made = [
        r
        for r in records
        if r["kind"] == "relations" and r["proposal"]["relation"] == "hasMaterial"
    ]
    assert made[0]["context_resolution"]["basis"] == "GROUP_NAME_NAMES_ITS_MATERIAL"
    uses = [
        r for r in records if r["kind"] == "relations" and r["proposal"]["relation"] == "usesSample"
    ]
    assert uses and uses[0]["status"] == "SOURCE_SUPPORTED", [u["reasons"] for u in uses]


def test_values_in_a_groups_own_subsection_are_candidates_named_by_their_syntax(service):
    from nasa_fire_ai.ingestion.document_extraction import group_subsection_quantity_candidates

    text = (
        "# Synthetic study\nII. Methods\nB. Alpha Drop Testing\n"
        "The chamber is 299 l in volume with an I.D. of 81.2 cm. "
        "The igniter was a retractable 2.2 mm OD ceramic rod. "
        "Installed was a 7.4 cm ID by 30 cm long tube.\nIII. Results\nNothing else.\n"
    )
    p = submitted(service, text)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "g", "Alpha Drop Testing", "ExperimentFamily", "B. Alpha Drop Testing")
    ]
    found = {
        (c["label"], c["expression"])
        for c in group_subsection_quantity_candidates(o, document, set())
    }
    assert ("volume", "299") in found and ("I.D.", "81.2") in found
    assert ("OD ceramic rod", "2.2") in found
    assert not any(e == "7.4" for _, e in found)  # a bare "ID by ..." names no thing


def test_conditions_printed_in_a_groups_own_subsection_are_its_candidates(service):
    from nasa_fire_ai.ingestion.document_extraction import structure_relation_candidates

    text = (
        "# Synthetic study\nII. Methods\nA. Alpha Flow Testing\n"
        "The Alpha chamber ran at a steady primer flow.\n"
        "B. Beta Drop Testing\n"
        "To achieve lunar gravity, the chamber was rotated before the drop. "
        "The igniter was very similar to the one used at Alpha Flow Testing in normal gravity. "
        "The rig spins to add a radial acceleration to the normal gravity vertical force.\n"
        "III. Results\nNothing else.\n"
    )
    p = submitted(service, text)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a", "Alpha Flow Testing", "ExperimentFamily", "A. Alpha Flow Testing"),
        entity(p, "b", "Beta Drop Testing", "ExperimentFamily", "B. Beta Drop Testing"),
        entity(p, "lg", "lunar gravity", "GravityCondition", "To achieve lunar gravity"),
        entity(p, "ng", "normal gravity", "GravityCondition", "in normal gravity"),
        entity(p, "pf", "primer flow", "ExperimentalCondition", "a steady primer flow"),
    ]
    found = {
        (c["subject"], c["relation"], c["object"])
        for c in structure_relation_candidates(o, document)
    }
    assert ("b", "hasCondition", "lg") in found and ("a", "hasCondition", "pf") in found
    # The sentence naming another group attributes nothing to this one, and a
    # bare mention that is not a setting ("to the normal gravity vertical force")
    # attributes nothing either.
    assert ("b", "hasCondition", "ng") not in found
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    records = validate_output(copy.deepcopy(o), p, document, extraction_semantic(service, p))[
        "records"
    ]
    held = [
        r
        for r in records
        if r["kind"] == "relations"
        and r["proposal"]["object"] == "pf"
        and r["proposal"]["subject"] == "a"
    ]
    assert held and held[0]["status"] == "SOURCE_SUPPORTED", [h["reasons"] for h in held]
    assert held[0]["context_resolution"]["basis"] == "SUBJECT_SUBSECTION_PRINTS_CONDITION"


def test_method_section_values_outside_group_subsections_configure_the_investigation(service):
    from nasa_fire_ai.ingestion.document_extraction import group_subsection_quantity_candidates

    text = (
        "# Synthetic study\nII. Experimental Method\n"
        "Tests were run at the planned habitat pressure of 56.5 kPa for several materials.\n"
        "A. Alpha Drop Testing\nThe chamber is 299 l in volume.\n"
        "III. Results\nThe burn length was 12 cm.\n"
    )
    p = submitted(service, text)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "inv", "Synthetic study", "Investigation", "Synthetic study"),
        entity(p, "g", "Alpha Drop Testing", "ExperimentFamily", "A. Alpha Drop Testing"),
    ]
    found = {
        (c["subject"], c["label"], c["expression"], c["epistemic"])
        for c in group_subsection_quantity_candidates(o, document, set())
    }
    assert ("inv", "planned habitat pressure", "56.5", "experimental_configuration") in found
    assert ("g", "volume", "299", "experimental_configuration") in found
    # A results value names no subject by structure; the group keeps its own.
    assert not any(e == "12" for _, _, e, _ in found)
    assert not any(s == "inv" and e == "299" for s, _, e, _ in found)


def test_a_thing_printed_as_tested_at_settings_is_a_specimen_with_its_configuration(service):
    from nasa_fire_ai.ingestion.document_extraction import (
        structure_entity_candidates,
        structure_quantity_candidates,
        structure_relation_candidates,
    )

    text = (
        "# Synthetic study\nCOTS Solutions\n• Developed fire-resistant textile solutions:\n"
        "100% PBI knit fabric coupons \ntested at 48% O2 and 8.2 psia\n"
        "Custom fire-resistant patches sewn \nto outer jacket fabric tested at 37% \nO2 and 8.2 psia\n"
        "Next item on the slide\n"
    )
    p = submitted(service, text)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "c", "100% PBI knit fabric coupons", "Sample", "100% PBI knit fabric coupons"),
        entity(p, "o2", "37% O2", "AtmosphereCondition", "37% \nO2"),
    ]
    entities = structure_entity_candidates(o, p, document)
    patches = [e for e in entities if e["label"].startswith("Custom fire-resistant patches")]
    assert patches and patches[0]["class_id"] == "Sample"
    assert patches[0]["label"] == "Custom fire-resistant patches sewn to outer jacket fabric"
    assert not any(e["label"].startswith("100% PBI") for e in entities)  # already proposed
    o["entities"] += entities
    values = {
        (c["label"], c["expression"], c["unit"])
        for c in structure_quantity_candidates(o, p, document)
        if c["subject"] == patches[0]["key"]
    }
    assert values == {("O2", "37", "%"), ("pressure", "8.2", "psia")}
    relations = {
        (c["subject"], c["relation"], c["object"])
        for c in structure_relation_candidates(o, document)
    }
    assert (patches[0]["key"], "hasCondition", "o2") in relations
    assert ("c", "hasCondition", "o2") not in relations  # the coupons' clause ends at 8.2 psia


def _tested_at_reading(service, text):
    """What the production readers make of a "tested at" line, by printed name."""
    import re

    from nasa_fire_ai.ingestion.document_extraction import (
        structure_entity_candidates,
        structure_quantity_candidates,
        structure_relation_candidates,
    )

    p = submitted(service, text)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "o2", "37% O2", "AtmosphereCondition", re.search(r"37%\s*O2", text).group(0))
    ]
    samples = [e for e in structure_entity_candidates(o, p, document) if e["class_id"] == "Sample"]
    o["entities"] += samples
    keys = {e["key"]: e["label"] for e in samples}
    values = {
        (keys[c["subject"]], c["label"], c["expression"], c["unit"])
        for c in structure_quantity_candidates(o, p, document)
        if c["subject"] in keys
    }
    relations = {
        (keys[c["subject"]], c["relation"], c["object"])
        for c in structure_relation_candidates(o, document)
        if c["subject"] in keys
    }
    return {e["label"] for e in samples}, values, relations


def test_rewrapping_a_tested_at_line_preserves_the_specimen_and_its_settings(service):
    # Metamorphic: the same slide text wrapped at different widths reads the same.
    wrappings = [
        "Custom fire-resistant patches sewn \nto outer jacket fabric tested at 37% \nO2 and 8.2 psia\n",
        "Custom fire-resistant patches sewn to outer \njacket fabric tested at 37% O2 and \n8.2 psia\n",
        "Custom fire-resistant patches sewn to outer jacket fabric tested at 37% O2 and 8.2 psia\n",
    ]
    readings = [
        _tested_at_reading(service, "# Synthetic study\nCOTS Solutions\n" + w + "Next item\n")
        for w in wrappings
    ]
    assert all(reading == readings[0] for reading in readings), readings
    labels, values, relations = readings[0]
    name = "Custom fire-resistant patches sewn to outer jacket fabric"
    assert labels == {name}
    assert values == {(name, "O2", "37", "%"), (name, "pressure", "8.2", "psia")}
    assert relations == {(name, "hasCondition", "o2")}


def test_a_different_specimen_or_setting_on_the_line_changes_the_reading(service):
    # Negative: a changed specimen name or qualifier is a different reading.
    labels, values, relations = _tested_at_reading(
        service,
        "# Synthetic study\nCOTS Solutions\nNomex felt liners tested at 37% O2 and 10.2 psia\n",
    )
    assert labels == {"Nomex felt liners"}
    assert values == {
        ("Nomex felt liners", "O2", "37", "%"),
        ("Nomex felt liners", "pressure", "10.2", "psia"),
    }
    assert relations == {("Nomex felt liners", "hasCondition", "o2")}


def _subsection_conditions(service, text, conditions):
    from nasa_fire_ai.ingestion.document_extraction import structure_relation_candidates

    p = submitted(service, text)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a", "Alpha Flow Testing", "ExperimentFamily", "A. Alpha Flow Testing"),
        entity(p, "b", "Beta Drop Testing", "ExperimentFamily", "B. Beta Drop Testing"),
        entity(p, "c", "Gamma Drop Testing", "ExperimentFamily", "C. Gamma Drop Testing"),
    ] + [entity(p, key, label, "GravityCondition", quote) for key, label, quote in conditions]
    return {
        (x["subject"], x["relation"], x["object"])
        for x in structure_relation_candidates(o, document)
        if x["relation"] == "hasCondition"
    }


def test_a_subsection_condition_follows_its_heading_and_its_wording(service):
    head = (
        "# Synthetic study\nThe study compares lunar gravity with microgravity.\n"
        "II. Methods\nA. Alpha Flow Testing\nThe Alpha chamber ran in normal gravity.\n"
    )
    tail = "III. Results\nNothing else.\n"
    conditions = [
        ("lg", "lunar gravity", "lunar gravity"),
        ("mg", "microgravity", "microgravity"),
        ("ng", "normal gravity", "normal gravity"),
    ]
    # Metamorphic: rewrapping the subsection's lines changes nothing.
    for lines in (
        "To achieve lunar gravity, the chamber was rotated before the drop.\n",
        "To achieve lunar \ngravity, the chamber was \nrotated before the drop.\n",
    ):
        found = _subsection_conditions(
            service,
            head
            + "B. Beta Drop Testing\n"
            + lines
            + "C. Gamma Drop Testing\nNothing here.\n"
            + tail,
            conditions,
        )
        assert found == {("b", "hasCondition", "lg"), ("a", "hasCondition", "ng")}, found
    # Negative: the same sentence under another heading belongs to that group.
    found = _subsection_conditions(
        service,
        head
        + "B. Beta Drop Testing\nNothing here.\nC. Gamma Drop Testing\n"
        + "To achieve lunar gravity, the chamber was rotated before the drop.\n"
        + tail,
        conditions,
    )
    assert found == {("c", "hasCondition", "lg"), ("a", "hasCondition", "ng")}, found
    # Negative: a changed gravity condition is a different condition.
    found = _subsection_conditions(
        service,
        head
        + "B. Beta Drop Testing\nTo achieve microgravity, the package was released.\n"
        + "C. Gamma Drop Testing\nNothing here.\n"
        + tail,
        conditions,
    )
    assert found == {("b", "hasCondition", "mg"), ("a", "hasCondition", "ng")}, found


def _requests(client):
    import json

    return [
        (
            kwargs["messages"][0]["content"],
            json.loads(kwargs["messages"][1]["content"]),
        )
        for _args, kwargs in client.client.with_options.return_value.chat.completions.create.call_args_list
    ]


# Alpha's condition is mentioned without a setting phrase, so no printed-structure
# candidate links it: only the model can, from the anchor's group scope.
GROUPED_TEXT = (
    "# Synthetic study\nII. Methods\nA. Alpha Flow Testing\n"
    "The Alpha chamber used a steady primer flow.\n"
    "B. Beta Drop Testing\n"
    "To achieve lunar gravity, the chamber was rotated before the drop.\n"
    "III. Results\nNothing else.\n"
)


def _grouped_fixture(service, p, with_primer_flow):
    o = Output().model_dump()
    # The controlled adapter maps a support to the whole original anchor it
    # contains, so every support here is the printed sentence under a heading.
    alpha = "The Alpha chamber used a steady primer flow."
    beta = "To achieve lunar gravity, the chamber was rotated before the drop."
    o["entities"] = [
        entity(p, "a", "Alpha Flow Testing", "ExperimentFamily", alpha),
        entity(p, "b", "Beta Drop Testing", "ExperimentFamily", beta),
        entity(p, "lg", "lunar gravity", "ExperimentalCondition", beta),
    ]
    if with_primer_flow:
        o["entities"].append(entity(p, "pf", "primer flow", "ExperimentalCondition", alpha))
    o["relations"] = [
        {"subject": "b", "relation": "hasCondition", "object": "lg", "support": support(p, beta)}
    ]
    return o


def test_model_requests_carry_each_anchors_heading_and_group_and_relation_signatures(service):
    from test_document_extraction import client_for

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget

    p = submitted(service, GROUPED_TEXT)
    client = client_for(_grouped_fixture(service, p, with_primer_flow=False))
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=24),
        client=client,
    )
    relationships = [
        (prompt, payload)
        for prompt, payload in _requests(client)
        if payload["stage"] == "relationships"
    ]
    assert relationships
    prompt, payload = relationships[0]
    assert "relation_signatures" in prompt and "narrowest explicit subject" in prompt
    beta = next(e["key"] for e in payload["known_entities"] if e["label"] == "Beta Drop Testing")
    under_beta = [a for a in payload["source_anchors"] if "To achieve lunar gravity" in a["quote"]]
    assert under_beta and all(
        a["heading"] == "B. Beta Drop Testing" and a["group"] == beta for a in under_beta
    )
    alpha_anchor = next(a for a in payload["source_anchors"] if "steady primer flow" in a["quote"])
    assert alpha_anchor["heading"] == "A. Alpha Flow Testing" and alpha_anchor["group"] != beta
    assert payload["relation_signatures"]["hasCondition"] == {
        "subject_classes": ["ExperimentFamily", "ExperimentalRun", "Investigation", "Sample"],
        "object_classes": ["ExperimentalCondition"],
    }
    # The fixture linked every group that prints a condition: no directed request.
    assert not any(
        "task" in payload and "group=" in payload["task"] for _, payload in relationships
    )


def test_a_group_left_unlinked_gets_one_request_directed_at_its_subsection(service):
    from test_document_extraction import client_for

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget

    p = submitted(service, GROUPED_TEXT)
    client = client_for(_grouped_fixture(service, p, with_primer_flow=True))
    prepared = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=24),
        client=client,
    )
    directed = [
        payload
        for _prompt, payload in _requests(client)
        if payload["stage"] == "relationships" and "group=" in payload.get("task", "")
    ]
    # One directed request; the controlled adapter answers it with Beta's relation,
    # outside the directed subject enum, so ordinary recovery retries the halves.
    assert directed, [p.get("task") for _, p in _requests(client)]
    payload = directed[0]
    alpha = next(e["key"] for e in payload["known_entities"] if e["label"] == "Alpha Flow Testing")
    assert payload["task"].startswith("Resolve the relations of known entity " + alpha)
    assert payload["schema"]["$defs"]["Relation"]["properties"]["subject"]["enum"] == [alpha]
    in_task = [a for a in payload["source_anchors"] if a["in_task"]]
    assert any(a.get("group") == alpha and "steady primer flow" in a["quote"] for a in in_task)
    records = prepared["package"]["scientific_extraction"]["records"]
    assert any(
        r["kind"] == "relations" and r["status"] == "SOURCE_SUPPORTED" for r in records
    )  # Beta's relation from the ordinary pass is kept


def test_a_method_value_the_tables_print_per_row_stays_with_the_rows(service):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    text = (
        "# Synthetic study\nII. Experimental Method\n"
        "Samples were struck with an impact energy of 72 ft-lbs in every test.\n"
        "III. Results\nNothing.\n"
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", "Synthetic study", "Investigation", "Synthetic study")]
    o["quantities"] = [
        {
            "subject": "inv",
            "label": "impact energy",
            "expression": "72",
            "unit": "ft-lbs",
            "epistemic": "experimental_configuration",
            "support": support(p, "an impact energy of 72 ft-lbs"),
        }
    ]

    def quantity(document):
        records = validate_output(copy.deepcopy(o), p, document, extraction_semantic(service, p))[
            "records"
        ]
        return next(r for r in records if r["kind"] == "quantities")

    plain = quantity(structure(p, service.root))
    assert plain["status"] == "SOURCE_SUPPORTED", plain["reasons"]
    assert (
        plain["scope_context"]["basis"] == "ORIGINAL_METHOD_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE"
    )
    with_rows = structure(p, service.root)
    with_rows["detected_tables"].append(
        {
            "physical_pdf_page": 1,
            "header": ["Material", "Impact energy (ft-lbs)", "Reactions/Tests"],
            "cells": [
                ["Material", "Impact energy (ft-lbs)", "Reactions/Tests"],
                ["Alpha", "72", "0/20"],
                ["Beta", "72", "1/20"],
            ],
        }
    )
    held = quantity(with_rows)
    assert held["status"] != "SOURCE_SUPPORTED"  # the rows are the narrower printed subjects
    # A column of another variable does not hold it.
    other = structure(p, service.root)
    other["detected_tables"].append(
        {
            "physical_pdf_page": 1,
            "header": ["Material", "Thickness (mm)"],
            "cells": [["Material", "Thickness (mm)"], ["Alpha", "72"]],
        }
    )
    assert quantity(other)["status"] == "SOURCE_SUPPORTED"
