"""B8 for the two redone subject rules: every text their tests use is invented. No string of
test_printed_label_binding.py shares a three-word phrase with a
frozen target quote, or a five-word phrase with the four development documents."""

import ast
import glob
import gzip
import json
from pathlib import Path

from test_new_prompt_text_b8 import V4, long_phrases
from test_prompt_has_no_source_phrases import phrases

HERE = Path(__file__).resolve().parent
MODULES = ("test_printed_label_binding.py",)


def literals():
    for name in MODULES:
        tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                yield node.value
            elif isinstance(node, ast.JoinedStr):
                yield "".join(v.value for v in node.values if isinstance(v, ast.Constant))


def test_rule_tests_copy_no_target_quote():
    quotes = []
    for path in glob.glob(f"{V4}/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    assert len(quotes) >= 124
    target = set().union(*(phrases(q) for q in quotes))
    assert sorted({" ".join(p) for t in literals() for p in phrases(t) & target}) == []


def test_rule_tests_copy_no_phrase_of_the_development_documents():
    documents = set()
    for path in glob.glob(f"{V4}/independent_*/prepared_1.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            package = json.load(handle)["package"]
        documents |= long_phrases("\n".join(e["text"] for e in package["evidence"]))
    assert len(documents) > 1000
    assert sorted({" ".join(p) for t in literals() for p in long_phrases(t) & documents}) == []
