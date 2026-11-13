"""Flags off, nothing moves: with SCIENCE_MODAL_29148, SCIENCE_PURPOSE_READER and
SCIENCE_RECORDING_RULE off, every reading the three rules touch is byte-identical to
the code before them. All three are on by default (modal and recording since bb75114,
the purpose reader since it replaced C2), so "off" means "0" for each.

The digests below were computed by ``snapshot`` on the working tree at 54c16e4 (with
its uncommitted flag-default changes), before any of the three rules existed. If the
base legitimately changes for another reason, regenerate them at the parent commit of
the rule implementation, never at the implementation itself:

    PYTHONPATH=tests uv run python -c "import test_redo_clause_flags_off as t; print(t.digests())"

Synthetic text only (B8): an invented domain (concrete, seals, welds, cells, ovens).
"""

import hashlib
import json
import pathlib

import pytest
from test_contract_candidates import configuration_reasons
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import clause_cues, statement_integrity
from nasa_fire_ai.ingestion import document_extraction as de
from nasa_fire_ai.ingestion.document_extraction import role_errors
from nasa_fire_ai.ingestion.scientific_facets import facet_review, modality_review

service = _service

ON_BY_DEFAULT = ("SCIENCE_MODAL_29148", "SCIENCE_RECORDING_RULE", "SCIENCE_PURPOSE_READER")
NEW_FLAGS = ON_BY_DEFAULT
# The contract flags the rules sit next to, pinned to today's defaults so that a later
# default change elsewhere does not masquerade as a change of these rules.
PINNED = {
    "SCIENCE_CONTRACT_C2": "1",
    "SCIENCE_CONTRACT_C3": "0",
    "SCIENCE_CONTRACT_C4": "0",
}

CORPUS = [
    # Modal verbs.
    "A thinner gasket may be used when the flange runs cold.",
    "A thinner gasket can be employed when the flange runs cold.",
    "The fitted curve can be applied to estimate wall loss.",
    "Two primers are permitted on porous slabs.",
    "Operators should vent the oven before opening it.",
    "The bond may weaken at low humidity.",
    "The cylinders will be cured for 28 days.",
    "The cylinders were cured for 28 days.",
    "A thinner gasket was used on the cold flange.",
    # Purpose clauses.
    "To decrease scatter, four cylinders were cast and set in each mould of Run A1.",
    "To decrease scatter, four cylinders were cast and set in Run A1, and the slump increased with each batch.",
    "Four cylinders were cast and set in each mould of Run A1, to decrease scatter.",
    "Each panel was primed, aiming for a 40 um film.",
    "Each panel was primed with 40 um of sealer, aiming for a smooth finish.",
    "To determine the drift, the oven was held at 120 C.",
    "The oven was held at 120 C in order to determine the drift.",
    "The lid was clamped so that the vapour could not escape.",
    "The joint cooled quickly, so that the solder cracked.",
    "To date, no seal has leaked.",
    "The rig was heated to 300 C and the seal held.",
    "The bond was found to be weak.",
    "Each tube was flushed to remove the residue, and the wall thinned by 2 %.",
    "The heater of Run A1 was adjusted between runs.",
    "Four alloys were tested in Run A1.",
    "Wall temperatures of Run A1 followed the schedule.",
    "Two shims were positioned under the base plate of Run A1.",
    "The load cell of Run A1 was calibrated before each series.",
    # Recording rules.
    "If the weld shows porosity, the joint is classified as a reject.",
    "If a cell vents, the cycle is scored as void.",
    "If a cell vents, then the cycle is scored as void.",
    "If the gauge drifts past the band, the reading is classified as void.",
    "The reading was classified as void after the gauge drifted.",
    "If no value is printed, the emissivity is taken as 0.9.",
    "If the seal holds, then the joint is considered as sound.",
    "Values are reported as mean and range.",
    "If values are reported as means, the bars show the range.",
    "Unless the bead cracks, the joint is recorded as a pass.",
]
ROLES = (
    "guidance",
    "normative_requirement",
    "measured_observation",
    "experimental_configuration",
    "author_reported_conclusion",
    "open_question",
)
FACET_ROLES = ("test_criterion", "design_criterion", "guidance", "normative_requirement")
MODALITIES = ("intended", "hypothetical", "proposed", "prescriptive", "conditional")
CONFIGURATION_TEXTS = [t for t in CORPUS if "Run A1" in t]


def first_number(text):
    import re

    found = re.search(r"\d+(?:\.\d+)?", text)
    return found.group() if found else None


def readings():
    """Every reading the three rules may touch, for the whole corpus (no service)."""
    out = []
    for text in CORPUS:
        row = {"text": text}
        row["role_errors"] = {r: role_errors({"text": text, "epistemic": r}) for r in ROLES}
        row["modality"] = {
            m: [modality_review(text, m), modality_review(text, m, first_number(text))]
            for m in MODALITIES
        }
        row["facets"] = {
            r: facet_review("statements", {"text": text, "epistemic": r}) for r in FACET_ROLES
        }
        row["clause"] = {
            "execution": clause_cues.execution(text),
            "criterion": clause_cues.criterion(text),
            "plan": clause_cues.plan(text),
            "goal": clause_cues.goal(text),
            "strip_frames": clause_cues.strip_frames(text),
            "governing": clause_cues.governing_clause(text),
        }
        row["integrity"] = {
            "observation_cue": statement_integrity.observation_cue(text),
            "procedure_without_outcome": statement_integrity.procedure_without_outcome(text),
            "stated_criterion": statement_integrity.stated_criterion(text),
        }
        out.append(row)
    return out


def request_text():
    """The role vocabulary as the request sends it."""
    vocabulary = (
        de.request_role_vocabulary()
        if hasattr(de, "request_role_vocabulary")
        else de.ROLE_VOCABULARY
    )
    return json.dumps(vocabulary, sort_keys=True, ensure_ascii=False)


def validation(service):
    return [[t, sorted(configuration_reasons(service, t))] for t in CONFIGURATION_TEXTS]


def digest(node):
    return hashlib.sha256(
        json.dumps(node, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def digests(service=None):
    import os

    for flag in ON_BY_DEFAULT:
        os.environ[flag] = "0"
    os.environ.update(PINNED)
    found = {"readings": digest(readings()), "request": digest(request_text())}
    if service is not None:
        found["validation"] = digest(validation(service))
    return found


# Computed before the rules exist (see the module docstring).
GOLDEN = {
    "readings": "37236e68bd2b31db9a7be587f3d32eac92b155ee03b86fed67034273af012833",
    "request": "63a48cacb2dcd33b3ef32d76f443c4b9276b56a8a6c301fb2600ca444071ef82",
    # Regenerated when the two C2 set-up phrases ("tested in", "adjusted") were removed with
    # the purpose reader on by default: only the two corpus rows built on them changed, each
    # now carrying the configuration reason it did not carry before (the readings and the
    # request digests are untouched).
    "validation": "9e3090cd584b076d539f9262e9207a397276492b17c7413f8b691df693b3872b",
}


@pytest.fixture
def pinned(monkeypatch):
    for flag, value in PINNED.items():
        monkeypatch.setenv(flag, value)
    return monkeypatch


def test_readings_are_byte_identical_with_the_flags_off(pinned):
    for flag in NEW_FLAGS:
        pinned.setenv(flag, "0")
    assert digest(readings()) == GOLDEN["readings"]
    assert digest(request_text()) == GOLDEN["request"]


def test_validation_is_byte_identical_with_the_flags_off(service, pinned):
    for flag in NEW_FLAGS:
        pinned.setenv(flag, "0")
    assert digest(validation(service)) == GOLDEN["validation"]


def default_source():
    return "\n".join(
        pathlib.Path(module.__file__).read_text(encoding="utf-8")
        for module in (de, clause_cues, statement_integrity)
        + tuple(
            __import__(f"nasa_fire_ai.ingestion.{name}", fromlist=["x"])
            for name in (
                "scientific_facets",
                "extraction_schema",
                "printed_layout",
                "subject_recognition",
                "quantity_validation",
                "extraction_request",
                "extraction_validation",
                "entity_validation",
                "statement_validation",
                "relation_validation",
                "extraction_resources",
            )
        )
    )


@pytest.mark.parametrize("flag", ON_BY_DEFAULT)
def test_each_flag_is_on_by_default(flag):
    source = default_source()
    assert f'os.getenv("{flag}", "1") == "1"' in source
    assert f'os.getenv("{flag}", "0") == "1"' not in source


@pytest.mark.parametrize("flag", NEW_FLAGS)
def test_each_flag_alone_changes_something(pinned, service, flag):
    # A flag that moves nothing is not a rule; each one must change the corpus reading.
    for other in NEW_FLAGS:
        pinned.setenv(other, "0")
    pinned.setenv(flag, "1")
    changed = (
        digest(readings()) != GOLDEN["readings"]
        or digest(validation(service)) != GOLDEN["validation"]
    )
    assert changed
