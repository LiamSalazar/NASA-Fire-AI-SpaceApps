"""'Prior to' a step orders a procedure; 'prior work' points at earlier research; synthetic text."""

import pytest

from nasa_fire_ai.ingestion.document_extraction import original_research_passage


def results_passage(sentence):
    text = "III. Results\n" + sentence + "\n"
    doc = {
        "segments": [{"evidence_id": "E-0", "source_id": "src", "start": 0, "text": text}],
        "sections": [
            {"evidence_id": "E-0", "source_id": "src", "start": 0, "title": "III. Results"}
        ],
        "package_title": "Synthetic valve study",
    }
    span = {
        "evidence_id": "E-0",
        "source_id": "src",
        "start": text.index(sentence),
        "quote": sentence,
    }
    return original_research_passage([span], doc)


@pytest.mark.parametrize(
    "sentence",
    [
        "Closure times of 40 ms were measured prior to re-connecting the valve to the manifold.",
        "Closure times of 40 ms were measured prior to opening the valve.",
        "Closure times of 40 ms were measured prior to ignition.",
        "Closure times of 40 ms were measured prior to initiation of the impact sequence.",
    ],
)
def test_a_step_ordered_by_prior_to_is_the_papers_own_procedure(sentence):
    assert results_passage(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        "Closure times of 40 ms were measured in prior work.",
        "Closure times of 40 ms were measured prior to this study.",
        "Closure times of 40 ms were measured prior to the present investigation.",
        "Closure times of 40 ms were measured in prior tests.",
        "Closure times of 40 ms were measured in previous tests.",
    ],
)
def test_prior_work_stays_earlier_research(sentence):
    assert not results_passage(sentence)
