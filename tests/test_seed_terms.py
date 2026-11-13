"""Seed vocabulary (SCIENCE_EXCLUDE_SEED_TERMS): terms whose only origin is the MVP seed
lexicon are not sent to the model when the flag is on; with it off the requests are
byte-identical. Synthetic text only."""

import hashlib
import json

import pytest
from test_never_proposed_flags import run
from test_never_proposed_flags import service as _service

service = _service
FLAG = "SCIENCE_EXCLUDE_SEED_TERMS"
TEXT = (
    "II. Methods\nSample S1 was tested in the burner.\n"
    "Sample S1 was tested in the burner with the Gamma paste.\n"
    "The Quill gasket and the Quill gasket seat were inspected afterwards.\n"
)
# Seed names present in domain/lexicon.yaml and not in the approved ontology or registry.
SEED_ONLY = ("PMMA", "polymethyl methacrylate", "SIBAL Fabric", "Sibal", "low-g")
# Digest of the requests the code built before the flag existed (flag unset).
DIGEST = "dc0a247f963bb60c95bd15a3fa93f328c101e39e6416629a6f6ec7e1b9eb398f"


def capture(service, monkeypatch, on=None):
    monkeypatch.delenv(FLAG, raising=False)
    if on is not None:
        monkeypatch.setenv(FLAG, on)
    systems = []
    payloads = run(service, monkeypatch, text=TEXT, systems=systems)
    return payloads, systems


def digest(payloads, systems):
    blob = json.dumps([payloads, systems], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("on", [None, "0"])
def test_flag_off_requests_are_byte_identical(service, monkeypatch, on):
    payloads, systems = capture(service, monkeypatch, on=on)
    assert len(payloads) >= 3
    assert digest(payloads, systems) == DIGEST


def sent_strings(payloads, systems):
    from test_new_prompt_text_b8 import strings

    return [t for t in strings(payloads) if t] + systems


def test_seed_terms_are_sent_while_the_flag_is_off(service, monkeypatch):
    text = "\n".join(sent_strings(*capture(service, monkeypatch)))
    assert all(term in text for term in SEED_ONLY)


def test_seed_terms_are_absent_with_the_flag_on(service, monkeypatch):
    payloads, systems = capture(service, monkeypatch, on="1")
    text = "\n".join(sent_strings(payloads, systems)).casefold()
    assert not [term for term in SEED_ONLY if term.casefold() in text]
    assert all("aliases" in p["contracts"] for p in payloads)


def test_approved_labels_are_still_sent_with_the_flag_on(service, monkeypatch):
    payloads, systems = capture(service, monkeypatch, on="1")
    text = "\n".join(sent_strings(payloads, systems))
    for approved in ("normal gravity", "ExperimentalCondition", "Sample", "hasMaterial"):
        assert approved in text
    # An alias entry that kept at least one non-seed alias stays, without the seed ones.
    assert any(
        "terrestrial" in entry["aliases"] and "low-g" not in entry["aliases"]
        for p in payloads
        for entry in p["contracts"]["aliases"]
    )


def test_a_term_the_registry_also_names_is_not_seed_only(service):
    from nasa_fire_ai.ingestion.seed_terms import seed_only_keys, without_seed_aliases

    semantic = service.semantic
    root = service.root
    some_class = next(iter(semantic.class_metadata))
    entries = [{"aliases": [some_class, "Quill alloy"], "relation": "x"}]
    assert without_seed_aliases(entries, root, semantic) == entries
    assert "pmma" in seed_only_keys(root, semantic)
