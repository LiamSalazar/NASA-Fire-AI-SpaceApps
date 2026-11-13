"""Review of c099faa, group 3 (#19): each publication-safety point is checked from the
proposals through validation, curation and projection to the graph. Synthetic text and a
controlled stand-in for the model; no live call, no NASA data.
"""

import copy

import pytest
from test_document_extraction import entity
from test_document_extraction import service as _service
from test_publication_safety import projected
from test_scientific_facets import quantity, statement

from nasa_fire_ai.services.curation import digest

service = _service
STUDY = "Synthetic study"


def kept(package, record_id):
    """The curated statements and values that came from one proposal."""
    return [
        x
        for x in [*package["statements"], *package["values"]]
        if record_id in (x.get("scientific_proposal_id"), x.get("id"))
    ]


@pytest.mark.parametrize("proposed_first", [True, False])
def test_2_two_modality_readings_of_one_span_reach_the_graph_as_neither(service, proposed_first):
    sentence = "Planned oxygen for each panel: 34 %."

    def build(p, o):
        o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
        plain = statement(
            p, sentence, "experimental_configuration", "ExperimentalCondition", ["inv"]
        )
        pair = [plain, {**plain, "modality": "proposed"}]
        o["statements"] = pair[::-1] if proposed_first else pair

    records, in_graph, package = projected(service, sentence, build)
    readings = [r for r in records if r["kind"] == "statements"]
    assert readings and not [r for r in readings if r["id"] in in_graph]
    assert not [
        s
        for r in readings
        for s in package["statements"]
        if r["id"] in (s.get("scientific_proposal_id"), s.get("id")) and s.get("included", True)
    ]


@pytest.mark.parametrize(
    ("sentence", "label", "value", "unit"),
    [
        # 3: a future setting on a subject that is not a run.
        ("Panel C3 will be burned again at 34 % oxygen.", "oxygen", "34", "%"),
        # 5: a prescribed limit with no stated modality.
        ("The pressure for Panel C3 must not exceed 50 kPa.", "pressure", "50", "kPa"),
        # 3, other wording of the future.
        ("Panel C3 is scheduled to be burned at 34 % oxygen.", "oxygen", "34", "%"),
    ],
)
def test_3_5_a_value_printed_as_not_done_never_reaches_the_graph(
    service, sentence, label, value, unit
):
    def build(p, o):
        o["entities"] = [entity(p, "s", "Panel C3", "Sample", sentence)]
        o["quantities"] = [
            quantity(p, sentence, "s", label, value, unit, "experimental_configuration")
        ]

    records, in_graph, package = projected(service, sentence, build)
    (record,) = [r for r in records if r["kind"] == "quantities"]
    assert record["status"] == "UNRESOLVED"
    assert "VALUE_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW" in record["reasons"]
    assert record["id"] not in in_graph
    assert not [v for v in package["values"] if v["id"] == record["id"]]


def test_3_control_the_same_value_printed_as_done_reaches_the_graph(service):
    # Metamorphic control: the harness publishes a done value, so the absence above
    # is the guard's doing, not the harness's.
    sentence = "Panel C3 was burned at 34 % oxygen."

    def build(p, o):
        o["entities"] = [entity(p, "s", "Panel C3", "Sample", sentence)]
        o["quantities"] = [
            quantity(p, sentence, "s", "oxygen", "34", "%", "experimental_configuration")
        ]

    records, in_graph, package = projected(service, sentence, build)
    (record,) = [r for r in records if r["kind"] == "quantities"]
    assert record["id"] in in_graph and package["values"]


def test_4_a_printed_structure_candidate_planned_in_a_subsection_never_reaches_the_graph(
    service,
):
    text = (
        "II. Methods\nB. Alpha Drop Testing\n"
        "Future tests will use a chamber pressure of 50 kPa.\n"
        "III. Results\nNothing else.\n"
    )

    def build(p, o):
        o["entities"] = [
            entity(p, "inv", STUDY, "Investigation", STUDY),
            entity(p, "g", "Alpha Drop Testing", "ExperimentFamily", "B. Alpha Drop Testing"),
        ]

    records, in_graph, _ = projected(service, text, build)
    candidates = [
        r for r in records if r["kind"] == "quantities" and r["proposal"].get("expression") == "50"
    ]
    assert candidates, "the printed structure proposes the value"
    assert not [r for r in candidates if r["id"] in in_graph]
    assert not [r for r in candidates if r["status"] == "SOURCE_SUPPORTED"]


@pytest.mark.parametrize("modality", ["proposed", "conditional"])
def test_6_a_not_done_configuration_statement_is_kept_out_like_its_value(service, modality):
    sentence = (
        "The follow-on tests will hold oxygen at 34 % for each panel."
        if modality == "proposed"
        else "If ignition fails, the panels will be held at 34 % oxygen."
    )

    def build(p, o):
        o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
        o["statements"] = [
            statement(
                p,
                sentence,
                "experimental_configuration",
                "ExperimentalCondition",
                ["inv"],
                modality=modality,
            )
        ]

    records, in_graph, package = projected(service, sentence, build)
    (record,) = [r for r in records if r["kind"] == "statements"]
    assert record["id"] not in in_graph
    assert all(not s.get("included", True) for s in kept(package, record["id"]))


def test_7_regenerating_twice_gives_the_same_package_and_digest(service):
    sentence = "The follow-on tests will hold oxygen at 34 % for each panel."

    def build(p, o):
        o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
        o["quantities"] = [
            quantity(
                p, sentence, "inv", "oxygen", "34", "%", "experimental_configuration", "proposed"
            )
        ]

    _, _, package = projected(service, sentence, build)
    service.regenerate(package)
    once = copy.deepcopy(package)
    service.regenerate(package)
    assert package["non_executed_values"] == once["non_executed_values"]
    assert digest(package) == digest(once)


@pytest.mark.parametrize("cls", ["ReportedObservation", "TestCriterion"])
def test_8_a_configuration_outside_its_class_set_never_reaches_the_graph(service, cls):
    sentence = "Run A1 was held at 21 % oxygen."

    def build(p, o):
        o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", sentence)]
        o["statements"] = [statement(p, sentence, "experimental_configuration", cls, ["a1"])]

    records, in_graph, _ = projected(service, sentence, build)
    (record,) = [r for r in records if r["kind"] == "statements"]
    assert record["status"] == "REJECTED" and record["id"] not in in_graph
