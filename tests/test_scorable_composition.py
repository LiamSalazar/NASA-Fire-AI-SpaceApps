"""R3 (SCIENCE_SCORABLE_COMPOSITION): a composition the document states, between validated
materials, is a scorable relation record in staging (formulation, constituent, role, proportion,
basis, applicability, evidence), never in the approved ontology and never with an invented share.
Invented materials and text only; no model call; nothing in the code names a material."""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service

from nasa_fire_ai.evaluation.phase1_protocol import candidates, outcome
from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
FLAG = "SCIENCE_SCORABLE_COMPOSITION"

NAMES = {"product": "Corvane", "filler": "Talcite", "host": "Kestrel", "other": "Mirelite"}
TESTED = "{product} seals, {filler} powder and {host} resin were tested here."
FILLER = "{product} uses {filler} filler in {host}."
SHARE = "The composition of {product} is 35% {filler} and 65% {host}."
MASS = "The composition of {product} is 35% {filler} and 65% {host} by weight."
UNKNOWN = "The proportion of {filler} in {product} is not known."
ONE_LISTED = "The composition of {product} is 65% {host}."
NEGATED = "{product} no longer uses {filler} filler in {host}."
CONTRAST = "{product} uses {filler} filler in {host} rather than {other}."


def fill(template, names=NAMES):
    return template.format(**names)


def run(service, *templates, names=NAMES, validated=("product", "filler", "host")):
    tested = fill(TESTED, names)
    text = (
        "Seal Compound Study\nII. Results\n"
        + " ".join([tested] + [fill(t, names) for t in templates])
        + "\n"
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, role, names[role], "Material", tested) for role in validated]
    result = validate(service, p, o)
    return p, result


def composition_records(result):
    return [
        r
        for r in result["records"]
        if r["kind"] == "relations" and (r.get("proposal") or {}).get("relation") == "hasComponent"
    ]


def labels(result):
    return {
        r["entity_id"]: r["proposal"]["label"] for r in result["records"] if r["kind"] == "entities"
    }


def by_constituent(result):
    names = labels(result)
    return {names.get(r["object"]): r for r in composition_records(result)}


def test_a_stated_filler_is_a_complete_staged_relation_with_its_printed_share(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, FILLER, SHARE)
    record = by_constituent(result)[NAMES["filler"]]
    names = labels(result)
    assert names[record["subject"]] == NAMES["product"]
    # Staged: only the relation is unregistered; its wording was read, not co-occurrence.
    assert record["reasons"] == ["UNREGISTERED_RELATION"]
    assert outcome([record]) == "COMPLETE_WITH_STAGED_EXTENSION"
    c = record["composition"]
    assert c["role"] == "filler"
    assert c["role_host"]["label"] == NAMES["host"]
    assert c["proportion"]["value"] == 35.0 and c["proportion"]["unit"] == "%"
    assert c["proportion"]["status"] == "REPORTED"
    assert c["basis"] == "UNSPECIFIED_IN_SOURCE"
    assert c["applicability"]["study"] == "current"
    # One located span for the pair, one for the share printed in another sentence.
    assert len(c["evidence"]) == 2 and all(e.get("start") is not None for e in c["evidence"])
    assert c["assertion_id"] in {a["id"] for a in result["composition_proposals"]}
    # Never in the approved ontology: the relation stays a staged extension.
    (extension,) = [
        e for e in result["ontology_extension_proposals"] if e.get("term") == "hasComponent"
    ]
    assert extension["activation"] == "NONE"
    assert extension["status"] == "STAGED_FOR_ONTOLOGY_REVIEW"
    assert record["id"] in extension.get("supporting_records", [])


def test_the_record_is_found_on_its_own_passage(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    p, result = run(service, FILLER, SHARE)
    record = by_constituent(result)[NAMES["filler"]]
    sentence = fill(FILLER)
    text = p["evidence"][0]["text"]
    start = text.index(sentence)
    target = {
        "kind": "relations",
        "evidence_id": p["evidence"][0]["evidence_id"],
        "start": start,
        "end": start + len(sentence),
    }
    assert record["id"] in {r["id"] for r in candidates(target, result["records"])}


def test_a_printed_basis_is_kept_and_an_unprinted_one_is_never_assumed(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _, stated = run(service, FILLER, MASS)
    _, unstated = run(service, FILLER, SHARE)
    assert by_constituent(stated)[NAMES["filler"]]["composition"]["basis"] == "MASS"
    assert (
        by_constituent(unstated)[NAMES["filler"]]["composition"]["basis"] == "UNSPECIFIED_IN_SOURCE"
    )


def test_a_documented_unknown_share_stays_unknown(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, FILLER, UNKNOWN)
    proportion = by_constituent(result)[NAMES["filler"]]["composition"]["proportion"]
    assert proportion["status"] == "NOT_KNOWN_PER_SOURCE"
    assert proportion.get("value") is None


def test_a_share_is_never_computed_from_the_other_listed_components(service, monkeypatch):
    # Only the host's share is printed: the filler's is not 100 - 65.
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, FILLER, ONE_LISTED)
    found = by_constituent(result)
    filler = found[NAMES["filler"]]["composition"]["proportion"]
    assert filler["status"] == "NOT_STATED_IN_SOURCE" and filler.get("value") is None
    assert found[NAMES["host"]]["composition"]["proportion"]["value"] == 65.0
    values = {r["composition"]["proportion"].get("value") for r in found.values()} - {None}
    assert values == {65.0}


def test_a_constituent_that_is_not_a_validated_entity_is_not_projected(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, FILLER, SHARE, validated=("product", "host"))
    assert NAMES["filler"] not in by_constituent(result)
    # The assertion itself is still staged for review, as today.
    assert any(a["component"]["label"] == NAMES["filler"] for a in result["composition_proposals"])


@pytest.mark.parametrize("template", [NEGATED, CONTRAST])
def test_a_negated_or_contrasted_constituent_is_never_a_component(service, monkeypatch, template):
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, template)
    found = by_constituent(result)
    assert NAMES["other"] not in found
    if template is NEGATED:
        assert NAMES["filler"] not in found


def test_renaming_the_materials_keeps_the_reading(service, monkeypatch):
    # Metamorphic: other invented names, same wording, same record shape.
    monkeypatch.setenv(FLAG, "1")
    renamed = {"product": "Halvane", "filler": "Opalite", "host": "Sorrel", "other": "Quillite"}
    _, a = run(service, FILLER, SHARE)
    _, b = run(service, FILLER, SHARE, names=renamed)
    ca = by_constituent(a)[NAMES["filler"]]["composition"]
    cb = by_constituent(b)[renamed["filler"]]["composition"]
    assert (ca["role"], ca["proportion"]["value"], ca["basis"]) == (
        cb["role"],
        cb["proportion"]["value"],
        cb["basis"],
    )
    assert len(composition_records(a)) == len(composition_records(b))


@pytest.mark.parametrize("templates", [(FILLER, SHARE), (FILLER, UNKNOWN), (CONTRAST,)])
def test_flags_off_identity(service, monkeypatch, templates):
    monkeypatch.delenv(FLAG, raising=False)
    _, absent = run(service, *templates)
    monkeypatch.setenv(FLAG, "0")
    _, off = run(service, *templates)
    assert [r["id"] for r in absent["records"]] == [r["id"] for r in off["records"]]
    assert absent["composition_proposals"] == off["composition_proposals"]
    # Today's behaviour: composition stays beside the records, never a record.
    assert composition_records(off) == []
    assert all("composition" not in r for r in off["records"])


# R3 review fixes: invented text that must never become a complete composition record.
ENV_ATMOSPHERE = (
    "{product} seals were tested in an atmosphere that is composed of 40% {filler} and 60% {host}."
)
ENV_CHAMBER = "{product} was burned in a chamber whose gas consists of 21% {filler}."
SAMPLE_COUNTS = "The {product} test matrix consists of 40% {filler} samples and 60% {host} samples."
FILL_LEVEL = "The {product} vessel was made up of 80% {host} fill at ignition."
LESS_THAN = "The composition of {product} is less than 10% {filler} and about 90% {host}."
RANGE = "The composition of {product} is 30-40% {filler}."
UP_TO = "The composition of {product} is up to 15% {filler}."
WHEREAS = "The composition of {product} is unchanged, whereas {other} is 35% {filler}."
WHICH = "The composition of {product} is similar to {other}, which is 35% {filler}."
CITED = (
    "Smith et al. [3] reported that the composition of {product} is 35% {filler} and 65% {host}."
)
CITED_BARE = "Smith et al. reported that the composition of {product} is 35% {filler}."
NEGATED_SHARE = "The composition of {product} is not 35% {filler}."


@pytest.mark.parametrize(
    "template", [ENV_ATMOSPHERE, ENV_CHAMBER, SAMPLE_COUNTS, FILL_LEVEL, WHEREAS, WHICH]
)
def test_a_share_of_something_else_is_never_the_products_composition(
    service, monkeypatch, template
):
    # F1/F2: the product must be the grammatical subject of the composition clause.
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, template)
    assert composition_records(result) == []


@pytest.mark.parametrize("template", [LESS_THAN, RANGE, UP_TO])
def test_a_bound_or_range_is_never_an_exact_reported_value(service, monkeypatch, template):
    # F3: a printed qualifier, held; never value REPORTED.
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, template)
    records = composition_records(result)
    assert records
    for record in records:
        proportion = record["composition"]["proportion"]
        assert proportion["status"] == "BOUND_OR_RANGE_REQUIRES_REVIEW"
        assert proportion.get("value") is None and proportion["qualifier"]
        assert outcome([record]) != "COMPLETE_WITH_STAGED_EXTENSION"


def test_an_exact_share_next_to_a_bound_stays_exact(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, "The composition of {product} is 35% {filler} and 65% {host}.")
    for record in composition_records(result):
        assert record["composition"]["proportion"]["status"] == "REPORTED"


@pytest.mark.parametrize("template", [CITED, CITED_BARE])
def test_a_cited_composition_is_never_the_current_study(service, monkeypatch, template):
    # F4: the cited sentence stays held as current-or-cited unresolved.
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, template)
    records = composition_records(result)
    assert records
    for record in records:
        assert "CURRENT_OR_CITED_STUDY_UNRESOLVED" in record["reasons"]
        assert outcome([record]) != "COMPLETE_WITH_STAGED_EXTENSION"


def test_a_negated_share_sentence_gives_no_share(service, monkeypatch):
    # F5: the pair is stated elsewhere; the negated sentence prints no proportion.
    monkeypatch.setenv(FLAG, "1")
    _, result = run(service, FILLER, NEGATED_SHARE)
    proportion = by_constituent(result)[NAMES["filler"]]["composition"]["proportion"]
    assert proportion["status"] == "NOT_STATED_IN_SOURCE" and proportion.get("value") is None


def test_a_host_read_only_from_a_filled_name_keeps_the_review_hold(service, monkeypatch):
    # F6: the name "Talcite-filled Kestrel" does not state the host side directly.
    monkeypatch.setenv(FLAG, "1")
    name = "Talcite-filled Kestrel"
    sentence = "Talcite-filled Kestrel coupons were ignited."
    text = "Seal Compound Study\nII. Results\n" + fill(TESTED) + " " + sentence + "\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "name", name, "Material", sentence),
        entity(p, "filler", "Talcite", "Material", fill(TESTED)),
        entity(p, "host", "Kestrel", "Material", fill(TESTED)),
    ]
    result = validate(service, p, o)
    records = [r for r in composition_records(result) if r["composition"]["role"] != "filler"]
    assert records
    for record in records:
        assert "RELATION_ENTAILMENT_REQUIRES_REVIEW" in record["reasons"]
        assert outcome([record]) != "COMPLETE_WITH_STAGED_EXTENSION"
