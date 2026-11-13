"""Environment subjects V2 (SCIENCE_ENVIRONMENT_SUBJECTS_V2): the identity request for
cited and target environments is kept as the single environment mechanism; it asks for
the approved condition class only; the value roles no longer tell the model to give
values the environment as subject; validation is unchanged: a value reaches an
environment only through the existing chain (a condition carries only the value printed
in its own label, then applicability), or through the printed-label binding rule
designed elsewhere. Off by default. Synthetic text."""

import copy

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service
from test_never_proposed_flags import run

from nasa_fire_ai.ingestion.document_extraction import ENVIRONMENT_VALUE_ROLES, Output

service = _service
V1 = "SCIENCE_ENVIRONMENT_SUBJECTS"
V2 = "SCIENCE_ENVIRONMENT_SUBJECTS_V2"
ROW12 = "SCIENCE_ENTITY_FACETS"
OWN = "Synthetic Habitat Panel Study"
# A cited environment whose own label prints its value.
LABELLED_ENV = "Kestrel habitat air at 48 kPa"
LABELLED = "The Kestrel habitat air at 48 kPa was used in that earlier work [3]."
# The same environment named without its value in the label.
BARE_ENV = "Kestrel habitat air"
BARE = "The Kestrel habitat air was held at 48 kPa [3]."
# A target of this study, printed only in the introduction.
TARGET_ENV = "qualification chamber air at 31 kPa"
TARGET = "The qualification chamber air at 31 kPa must be reached."


def flags(monkeypatch, *on):
    for name in (V1, V2, ROW12):
        monkeypatch.delenv(name, raising=False)
    for name in on:
        monkeypatch.setenv(name, "1")


def payloads(service, monkeypatch, *on):
    # run() resets its own flags (V1 among them) and sets those passed to it.
    flags(monkeypatch, *on)
    return run(service, monkeypatch, flags=tuple(f for f in on if f == V1))


def paper(service, intro, results="Nothing else was measured."):
    return submitted(service, f"{OWN}\nI. Introduction\n{intro}\nII. Results\n{results}\n")


def output(p, text, env_label, study="cited", expression="48"):
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "inv", OWN, "Investigation", OWN),
        entity(p, "env", env_label, "ExperimentalCondition", text, study=study),
    ]
    o["quantities"] = [
        {
            "subject": "env",
            "label": "pressure",
            "expression": expression,
            "unit": "kPa",
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    return o


def records(service, text, env_label, **kw):
    p = paper(service, text)
    return validate(service, p, output(p, text, env_label, **kw))["records"]


def one(rows, kind, key=None):
    found = [
        r for r in rows if r["kind"] == kind and (key is None or r["proposal"].get("key") == key)
    ]
    assert len(found) == 1
    return found[0]


# ---------------------------------------------------------------- flags off


def test_flags_off_nothing_new_is_asked(service, monkeypatch):
    found = payloads(service, monkeypatch)
    keys = (
        "environment_identity_contract",
        "environment_value_roles",
        "condition_identity_contract",
    )
    assert not any(k in p for p in found for k in keys)


def test_v1_alone_is_unchanged(service, monkeypatch):
    found = payloads(service, monkeypatch, V1)
    roles = [p["environment_value_roles"] for p in found if p["stage"] == "propositions"]
    assert roles and all(r == ENVIRONMENT_VALUE_ROLES for r in roles)


# ---------------------------------------------------------------- flag on (request)


def test_v2_keeps_the_identity_request(service, monkeypatch):
    found = payloads(service, monkeypatch, V2)
    identity = [p for p in found if p["stage"] == "identity"]
    assert identity and all("environment_identity_contract" in p for p in identity)


def test_v2_identity_request_asks_only_for_the_registered_condition_class(service, monkeypatch):
    # The condition subclasses of the ontology are not registered for extraction; an
    # entity typed with one is staged and its values held.
    found = payloads(service, monkeypatch, V2)
    contract = next(
        p["environment_identity_contract"] for p in found if "environment_identity_contract" in p
    )
    assert "ExperimentalCondition" in contract
    assert "subclass" not in contract


def test_v2_value_roles_never_assign_the_environment_as_subject(service, monkeypatch):
    found = payloads(service, monkeypatch, V2)
    roles = [p["environment_value_roles"] for p in found if p["stage"] == "propositions"]
    assert roles and all(r != ENVIRONMENT_VALUE_ROLES for r in roles)
    assert "as its subject" not in " ".join(" ".join(r) for r in roles)
    # The bound entry travels unchanged.
    assert ENVIRONMENT_VALUE_ROLES[2] in roles[0]


def test_v2_is_the_single_environment_mechanism(service, monkeypatch):
    found = payloads(service, monkeypatch, V2, ROW12)
    assert not any("condition_identity_contract" in p for p in found)
    assert any("environment_identity_contract" in p for p in found)


# ---------------------------------------------------------------- validation: positive


def test_a_value_printed_in_the_environment_label_keeps_it(service, monkeypatch):
    flags(monkeypatch, V2)
    rows = records(service, LABELLED, LABELLED_ENV)
    q = one(rows, "quantities")
    assert q["status"] == "SOURCE_SUPPORTED", q["reasons"]
    assert q["subject"] == one(rows, "entities", "env")["entity_id"]


# ---------------------------------------------------------------- validation: negative


def test_a_value_outside_the_environment_label_is_never_bound(service, monkeypatch):
    # The clause names the environment, but its label does not print the value: the
    # existing condition check refuses the association and keeps the value alone.
    flags(monkeypatch, V2)
    q = one(records(service, BARE, BARE_ENV), "quantities")
    assert q["status"] == "UNRESOLVED"
    assert q["subject"] is None
    assert "QUANTITY_SUBJECT_IS_A_CONDITION" in q["reasons"]
    assert "QUANTITY_VALUE_PRESERVED_SUBJECT_UNRESOLVED" in q["reasons"]


def test_a_target_environment_printed_only_in_background_stays_held(service, monkeypatch):
    flags(monkeypatch, V2)
    rows = records(service, TARGET, TARGET_ENV, study="current", expression="31")
    env = one(rows, "entities", "env")
    assert "SUPPORT_ONLY_IN_BACKGROUND_OR_ANALYSIS_SECTION" in env["reasons"]
    assert one(rows, "quantities")["status"] != "SOURCE_SUPPORTED"


# ---------------------------------------------------------------- metamorphic


def strip(rows):
    return [
        (r["kind"], r["status"], sorted(r["reasons"]))
        for r in rows
        if r["kind"] in {"entities", "quantities"}
    ]


def test_validation_is_identical_with_the_flag_on_and_off(service, monkeypatch):
    for text, label in ((LABELLED, LABELLED_ENV), (BARE, BARE_ENV)):
        p = paper(service, text)
        o = output(p, text, label)
        flags(monkeypatch)
        off = strip(validate(service, p, copy.deepcopy(o))["records"])
        flags(monkeypatch, V2)
        on = strip(validate(service, p, copy.deepcopy(o))["records"])
        assert on == off


def test_renaming_the_environment_keeps_the_outcome(service, monkeypatch):
    flags(monkeypatch, V2)
    outcomes = []
    for name in ("Kestrel habitat air", "Osprey station air"):
        text = LABELLED.replace("Kestrel habitat air", name)
        q = one(
            records(service, text, LABELLED_ENV.replace("Kestrel habitat air", name)), "quantities"
        )
        outcomes.append((q["status"], sorted(q["reasons"])))
    assert outcomes[0] == outcomes[1]
