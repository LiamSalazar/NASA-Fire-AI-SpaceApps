"""The ten cited cases once open in the trim invariant: with ORIGIN_CHECK on (the default), the
full printed sentence of the wrongly marked value is never SOURCE_SUPPORTED, and neither is any
trimmed variant of it (same trim generator as tests/test_trim_invariant.py). Invented text only."""

import copy
import random

import pytest
from test_trim_invariant import (
    EXTRA_FLAGS,
    FLAGS,
    KINDS,
    cases,
    run,
    semantic_of,
    structure_of,
    variants,
)
from test_trim_invariant import service as _service

service = _service

CITED = [
    "syn-" + name
    for name in (
        "tarred-rope",
        "dry-hemp",
        "knotted-wick",
        "coiled-thread",
        "silk-thread",
        "linen-band",
        "raw-wool-yarn",
        "kapok-wick",
        "reed-cord",
        "twisted-rush",
    )
]
BUILDERS = dict(cases())
HELD = {"UNRESOLVED", "REJECTED"}


@pytest.fixture(autouse=True)
def families_on(monkeypatch):
    for kind in KINDS:
        monkeypatch.setenv(FLAGS[kind], "1")
    for name in EXTRA_FLAGS:
        monkeypatch.setenv(name, "1")
    monkeypatch.delenv("SCIENCE_ORIGIN_CHECK", raising=False)


@pytest.mark.parametrize("name", CITED)
def test_the_full_sentence_and_every_trim_of_a_cited_value_stay_held(service, name):
    package, output = BUILDERS[name](service)
    document = structure_of(service, package)
    semantic = semantic_of(service, package)
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    made = variants(output["quantities"][0], evidence, random.Random(0), 6)
    assert made, "the value is placeable in its printed sentence"
    full, trimmed, _sentence = made
    status = run(copy.deepcopy(output), package, document, semantic, {0: full})[0]["status"]
    assert status in HELD, ("full", status)
    assert trimmed, "at least one trimmed variant"
    for support in trimmed:
        status = run(copy.deepcopy(output), package, document, semantic, {0: support})[0]["status"]
        assert status in HELD, (support[0]["quote"], status)
