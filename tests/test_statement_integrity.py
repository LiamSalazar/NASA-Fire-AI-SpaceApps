"""Synthetic statement integrity and cited-attribution checks; never NASA data."""

from nasa_fire_ai.ingestion.statement_integrity import (
    conflicting_roles,
    count_conflict,
    fragment_context,
    observation_cue,
    stated_criterion,
)
from nasa_fire_ai.ingestion.study_attribution import cited_attribution_nearby, reference_authors

REFERENCES = "References\n[1] Smith, A. B. and Jones, C., “Synthetic paper,” 1999.\n[2] Lee, D., “Other,” 2001.\n"


def doc(text):
    return {
        "segments": [
            {"evidence_id": "E1", "source_id": "S", "page": 1, "text": text},
            {"evidence_id": "R", "source_id": "S", "page": 2, "text": REFERENCES},
        ],
        "sections": [
            {"evidence_id": "R", "source_id": "S", "start": 0, "end": 10, "title": "References"}
        ],
    }


def span(text, quote):
    start = text.index(quote)
    return {"evidence_id": "E1", "start": start, "end": start + len(quote), "quote": quote}


def test_reference_list_authors_are_read_from_the_document_itself():
    assert reference_authors(doc("x")) == {"Smith", "Jones", "Lee"}


def test_named_cited_work_or_its_pronoun_is_not_the_current_study():
    text = (
        "The data presented by Smith and Jones is only a pass indication. "
        "Their data indicates that only one polymer passed. "
        "Our seal passed every test."
    )
    d = doc(text)
    assert cited_attribution_nearby(
        [span(text, "Their data indicates that only one polymer passed.")], d
    )
    assert cited_attribution_nearby([span(text, "The data presented by Smith and Jones")], d)
    assert cited_attribution_nearby([span(text, "Our seal passed every test.")], d) is None


def test_preceding_bracket_citation_marks_the_next_sentence():
    text = "The impact data is presented in Table 4 [3]. The results show the compounds were not sensitive."
    d = doc(text)
    assert cited_attribution_nearby(
        [span(text, "The results show the compounds were not sensitive.")], d
    )
    clean = "The impact data is presented in Table 3. The results show the compounds were not sensitive."
    assert (
        cited_attribution_nearby(
            [span(clean, "The results show the compounds were not sensitive.")], doc(clean)
        )
        is None
    )


def test_a_pronoun_in_the_previous_sentence_does_not_attribute_by_itself():
    text = "Both seals were compared and their performance was similar. The new seal passed."
    assert cited_attribution_nearby([span(text, "The new seal passed.")], doc(text)) is None


def pages(*texts):
    return {
        f"E{i}": {"evidence_id": f"E{i}", "source_id": "S", "page": i, "text": t}
        for i, t in enumerate(texts, 1)
    }


def located(evidence, key, quote):
    start = evidence[key]["text"].index(quote)
    return {"evidence_id": key, "start": start, "end": start + len(quote)}


def test_statement_cut_at_an_abbreviation_is_a_fragment():
    ev = pages("1\nUnder the same conditions, i.e. thickness and energy, it passed.\n")
    quote = "Under the same conditions, i.e."
    assert (
        fragment_context(quote, located(ev, "E1", quote), ev)["basis"]
        == "STATEMENT_ENDS_AT_ABBREVIATION"
    )


def test_sentence_cut_at_a_page_break_is_a_fragment_both_ways():
    ev = pages(
        "1\nThe sensitivity was attributed to the high percentage of\n",
        "2\nBronze filler in the compound.\nA separate sentence follows.\n",
    )
    tail = "The sensitivity was attributed to the high percentage of"
    assert fragment_context(tail, located(ev, "E1", tail), ev)["basis"] == (
        "SENTENCE_CONTINUES_ON_NEXT_PDF_PAGE"
    )
    head = "Bronze filler in the compound."
    assert fragment_context(head, located(ev, "E2", head), ev)["basis"] == (
        "SENTENCE_STARTS_ON_PREVIOUS_PDF_PAGE"
    )
    whole = "A separate sentence follows."
    assert fragment_context(whole, located(ev, "E2", whole), ev) is None


def test_a_slide_bullet_ending_a_page_without_punctuation_is_whole():
    ev = pages(
        "1\n• 1-g extinction happens 45 seconds sooner than partial-g extinction\n", "2\nNext.\n"
    )
    quote = "1-g extinction happens 45 seconds sooner than partial-g extinction"
    assert fragment_context(quote, located(ev, "E1", quote), ev) is None


def test_a_page_ending_with_a_full_sentence_does_not_mark_the_next_page():
    ev = pages("1\nThe first page ends here.\n", "2\nBronze filler was used.\n")
    quote = "Bronze filler was used."
    assert fragment_context(quote, located(ev, "E2", quote), ev) is None


def test_conflicting_counts_printed_together_are_held_for_review():
    text = (
        "Neither the wet nor dry tests showed any reactions out of the 80 impacts. "
        "Four of the additional 80 wet samples reacted with no remaining sample."
    )
    ev = pages(text)
    zero = "Neither the wet nor dry tests showed any reactions out of the 80 impacts."
    four = "Four of the additional 80 wet samples reacted with no remaining sample."
    assert count_conflict(located(ev, "E1", zero), ev)
    assert count_conflict(located(ev, "E1", four), ev)
    other = pages(zero + " Four of the additional 40 wet samples reacted.")
    assert count_conflict(located(other, "E1", zero), other) is None


def test_observation_requires_testing_or_result_wording():
    assert observation_cue("No reactions were recorded out of 20 samples.")
    assert observation_cue("The post-test picture shows the extruded material.")
    assert not observation_cue(
        "Alpha resin is a virgin granular resin which has been pre-sintered."
    )
    assert not observation_cue("The composition of Beta is 40% bronze and 60% polymer.")


def test_a_procedure_with_a_purpose_clause_is_not_an_observation():
    assert not observation_cue("A post-test picture was taken in order to show the extruded layer.")
    assert observation_cue("The post-test picture shows the extruded layer.")


def test_acceptance_and_recording_rules_are_criteria_not_configuration():
    assert stated_criterion("A sample is said to have passed if no reactions are recorded.")
    assert stated_criterion(
        "If the temperature rises above 425 C, then the AIT is recorded as >425 C."
    )
    assert stated_criterion("The pass/fail criterion is the number of reactions.")
    assert not stated_criterion("The chamber was pressurized with GOX and lowered into the bath.")


def record(rid, epistemic, start=0, status="SOURCE_SUPPORTED"):
    return {
        "id": rid,
        "kind": "statements",
        "status": status,
        "proposal": {"epistemic": epistemic},
        "statement_location": {"evidence_id": "E1", "start": start, "end": 40},
    }


def test_one_span_accepted_with_incompatible_roles_is_held():
    records = [
        record("a", "experimental_configuration"),
        record("b", "tentative_interpretation"),
        record("c", "tentative_interpretation", start=50),
        record("d", "hypothesis", start=50),
        record("e", "measured_observation", start=90),
        record("f", "documentary_context", start=90, status="UNRESOLVED"),
    ]
    assert conflicting_roles(records) == {"a", "b"}


def test_data_read_from_a_table_whose_caption_cites_a_reference_is_cited():
    from nasa_fire_ai.ingestion.study_attribution import cited_table_reference

    text = (
        "TABLE 6— Comparison data [4]\nRows.\nTABLE 3— Our data\nRows.\n"
        "The data listed in Table 6 indicate a 25% increase. The reactivity of the same material "
        "increases by 20%. The data in Table 3 show no reactions."
    )
    d = doc(text)
    assert cited_table_reference(
        [span(text, "The reactivity of the same material increases by 20%.")], d
    )
    assert cited_table_reference([span(text, "The data in Table 3 show no reactions.")], d) is None


def test_a_page_that_resumes_in_lower_case_continues_the_sentence():
    ev = pages("1\nA second batch of the material\n", "2\nwas tested under the same conditions.\n")
    quote = "A second batch of the material"
    assert fragment_context(quote, located(ev, "E1", quote), ev)["basis"] == (
        "SENTENCE_CONTINUES_ON_NEXT_PDF_PAGE"
    )


def test_a_caption_line_glued_to_a_sentence_is_a_fragment():
    ev = pages("1\nFigure 20 - SEM of the filter\nThe presence of the contaminant makes sense.\n")
    quote = "Figure 20 - SEM of the filter\nThe presence of the contaminant makes sense."
    assert fragment_context(quote, located(ev, "E1", quote), ev)["basis"] == (
        "STATEMENT_INCLUDES_A_CAPTION_LINE"
    )
    sentence = "Figure 1, below, is a pretest picture of the sample."
    ev = pages("1\n" + sentence + "\n")
    assert fragment_context(sentence, located(ev, "E1", sentence), ev) is None


def test_a_lower_case_start_after_an_unfinished_line_is_a_previous_sentence_tail():
    ev = pages(
        "1\nwith elevated regulator body\ntemperature  This sought to expand the demonstration.\n"
    )
    quote = "temperature  This sought to expand the demonstration."
    assert fragment_context(quote, located(ev, "E1", quote), ev)["basis"] == (
        "STATEMENT_STARTS_MID_SENTENCE"
    )
    ev = pages("1\nThe bath was heated. pH was measured after each run.\n")
    quote = "pH was measured after each run."
    assert fragment_context(quote, located(ev, "E1", quote), ev) is None


def test_an_auxiliary_at_a_page_end_continues_the_sentence():
    ev = pages(
        "1\nThe impacts were performed at rates faster than could be\n", "2\nAchieved in flight.\n"
    )
    quote = "The impacts were performed at rates faster than could be"
    assert fragment_context(quote, located(ev, "E1", quote), ev)["basis"] == (
        "SENTENCE_CONTINUES_ON_NEXT_PDF_PAGE"
    )


def test_pointers_rules_and_caveats_are_not_observations():
    from nasa_fire_ai.ingestion.statement_integrity import documentary_pointer, rule_or_caveat

    assert documentary_pointer("The results for Alpha are shown in Table 3.")
    assert not documentary_pointer("It can be seen in Table 3 that Alpha passed.")
    assert rule_or_caveat("The determination cannot be made from AIT alone.")
    assert rule_or_caveat("These percentages are only valid below 425 C.")
    assert not rule_or_caveat("The F7 required the pressure to be dropped to 5,000 psia.")
    # A perception that failed is an observation, not a rule.
    assert not rule_or_caveat("The small slivers cannot be seen on the surface in the picture.")


def test_journal_front_matter_is_not_a_statement():
    block = "X\nPaper ID:\nAvailable online at: www.example.org\nPublished XXXX\nA. Author1\nSynthetic title"
    ev = pages("1\n" + block + "\nABSTRACT: Synthetic words.\n")
    assert (
        fragment_context(block, located(ev, "E1", block), ev)["basis"]
        == "STATEMENT_IS_FRONT_MATTER"
    )
    sentence = "The data were published after the tests."
    ev = pages("1\n" + sentence + "\n")
    assert fragment_context(sentence, located(ev, "E1", sentence), ev) is None


def test_validity_caveats_and_bare_test_steps_are_recognised():
    from nasa_fire_ai.ingestion.statement_integrity import (
        procedure_without_outcome,
        validity_caveat,
    )

    assert validity_caveat("These percentages are only valid for a value below 425 C.")
    assert not validity_caveat("The comparison is valid.")
    assert not validity_caveat("It can only be speculated that the filler is zinc.")
    assert procedure_without_outcome(
        "Each was impacted with 98 J at 10,000 psia in LOX and in GOX."
    )
    assert not procedure_without_outcome("It was impacted with 98 J and passed with no reactions.")
    assert not procedure_without_outcome("A small sliver of the filling can be seen in the layer.")
