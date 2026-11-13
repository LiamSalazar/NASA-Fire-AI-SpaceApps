"""B8 for the three clause rules: every sentence their tests use is invented. No string of
these test files shares a three-word phrase with a frozen target quote, nor a five-word
phrase with the four development documents."""

import ast
import glob
import gzip
import json
from pathlib import Path

import pytest
from test_prompt_has_no_source_phrases import STOP, phrases, words

HERE = Path(__file__).resolve().parent
# The rules' test files expected in this tree (explicit: a missing one fails).
FILES = (
    "test_abbreviation_segmentation.py",
    "test_cited_value_attribution_gap.py",
    "test_composition_classes.py",
    "test_cited_comparison_negative.py",
    "test_contract_candidates.py",
    "test_modal_29148.py",
    "test_provenance_classes.py",
    "test_purpose_reader.py",
    "test_purpose_reader_v3.py",
    "test_recording_and_fragments.py",
    "test_recording_rule.py",
    "test_redo_clause_flags_off.py",
    "test_seed_terms.py",
    "test_setup_verb_class.py",
)


@pytest.mark.parametrize("name", FILES)
def test_every_expected_test_file_is_present(name):
    assert (HERE / name).exists(), name


V4 = "artifacts/phase1_generalizable_ingestion/v4"


def long_phrases(text, n=5):
    # As in test_new_prompt_text_b8: five words, at least three of them content words.
    w = words(text)
    return {
        tuple(w[i : i + n])
        for i in range(len(w) - n + 1)
        if sum(x not in STOP for x in w[i : i + n]) >= 3
    }


def literals(name):
    tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.FunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and len(node.value.split()) >= 3
    ]


@pytest.mark.parametrize("name", FILES)
def test_no_test_sentence_copies_a_target_quote(name):
    quotes = []
    for path in glob.glob(f"{V4}/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    assert len(quotes) >= 124
    target = set().union(*(phrases(q) for q in quotes))
    shared = {" ".join(p) for text in literals(name) for p in phrases(text) & target}
    assert sorted(shared) == []


@pytest.mark.parametrize("name", FILES)
def test_no_test_sentence_copies_a_development_document(name):
    documents = set()
    for path in glob.glob(f"{V4}/independent_*/prepared_1.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            package = json.load(handle)["package"]
        documents |= long_phrases("\n".join(e["text"] for e in package["evidence"]))
    assert documents
    shared = {" ".join(p) for text in literals(name) for p in long_phrases(text) & documents}
    assert sorted(shared) == []
