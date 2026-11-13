"""What a paper discusses in background, theory or analysis is not its own experiment;
synthetic text, never NASA data."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

PAPER = (
    "# Synthetic study\n"
    "I. Introduction\nQuenching limits flames in thin fuels.\n"
    "II. Flame Limits\nThe heat loss term balances the supply term.\n"
    "q = h (T - T0) (Eq. 1)\n"
    "The quench boundary follows from the balance.\n"
    "III. Methods\nAlpha test series used a flow duct. The duct was purged with nitrogen.\n"
    "IV. Results\nAlpha test series flames went out at 18% oxygen.\n"
    "Radiative loss (Eq. 1) explains the trend.\n"
)


def records_for(service, text, entities=(), statements=()):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, *e) for e in entities]
    o["statements"] = [
        {
            "text": sentence,
            "class_id": cls,
            "epistemic": epistemic,
            "subjects": [],
            "study": "current",
            "support": support(p, sentence),
        }
        for sentence, cls, epistemic in statements
    ]
    return validate(service, p, o)["records"]


def held(record):
    return "SUPPORT_ONLY_IN_BACKGROUND_OR_ANALYSIS_SECTION" in record["reasons"]


@pytest.mark.parametrize(
    "label,sentence",
    [
        ("Quenching", "Quenching limits flames in thin fuels."),  # a role-titled section
        ("quench boundary", "The quench boundary follows from the balance."),  # equations
    ],
)
def test_a_concept_named_only_in_background_or_theory_is_held(service, label, sentence):
    (record,) = [
        r
        for r in records_for(service, PAPER, [("c", label, "Quenching", sentence)])
        if r["kind"] == "entities"
    ]
    assert record["status"] != "SOURCE_SUPPORTED" and held(record)


def test_an_entity_of_the_own_methods_or_results_is_not_held(service):
    records = records_for(
        service,
        PAPER,
        [("g", "Alpha test series", "ExperimentFamily", "Alpha test series used a flow duct.")],
    )
    (record,) = [r for r in records if r["kind"] == "entities"]
    assert not held(record)


def test_an_equation_reference_inside_a_results_sentence_does_not_make_it_theory(service):
    # Metamorphic: the same equation number, cited in prose, is not a printed equation.
    records = records_for(
        service,
        PAPER,
        [("g", "Alpha test series", "ExperimentFamily", "Alpha test series used a flow duct.")],
        [
            (
                "Alpha test series flames went out at 18% oxygen.",
                "ReportedObservation",
                "measured_observation",
            )
        ],
    )
    assert not any(held(r) for r in records if r["kind"] == "statements")


def test_an_observation_printed_only_in_theory_is_held(service):
    records = records_for(
        service,
        PAPER,
        [],
        [
            (
                "The heat loss term balances the supply term.",
                "ReportedObservation",
                "measured_observation",
            )
        ],
    )
    (record,) = [r for r in records if r["kind"] == "statements"]
    assert held(record)


def test_a_later_heading_ends_the_background_section(service):
    # Without numbered major sections the nearest printed heading governs: a
    # "Background" title does not reach the "Testing Methodology" that follows it.
    # (Per-page decks: the slide deck replay in milestone13/README.md.)
    text = (
        "# Synthetic deck\n## Background\nApollo era fibers are discontinued.\n"
        "## Testing Methodology\nCoupons were tested at 8 psia.\n"
    )
    records = records_for(
        service, text, [("s", "Coupons", "Sample", "Coupons were tested at 8 psia.")]
    )
    (record,) = [r for r in records if r["kind"] == "entities"]
    assert not held(record)
