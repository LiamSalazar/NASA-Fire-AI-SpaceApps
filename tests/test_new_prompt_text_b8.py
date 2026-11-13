"""Every prompt text the flagged mechanisms add is invented: it shares no phrase with a frozen
target quote, and no longer phrase with the four development documents (B8)."""

import glob
import gzip
import json

from test_never_proposed_flags import run
from test_never_proposed_flags import service as _service
from test_prompt_has_no_source_phrases import STOP, phrases, words

service = _service
FLAGS = (
    "SCIENCE_ENVIRONMENT_SUBJECTS",
    "SCIENCE_PRODUCT_MATERIALS",
    "SCIENCE_BACKGROUND_FACETS",
    "SCIENCE_STRUCTURED_PROVENANCE",
    "SCIENCE_ROLE_VOCABULARY",
)
ADDED_KEYS = (
    "environment_identity_contract",
    "environment_value_roles",
    "product_material_contract",
    "background_facet_contract",
    "data_provenance_role",
    "role_vocabulary",
    "ontology_context",
    "ontology_context_use",
    "source_term_contract",
    "vocabulary_extension",
    "candidate_snippets",
)
# Track B flags: reviewed staged terms from a frozen snapshot, and per-candidate snippets.
TRACK_B = ("SCIENCE_STAGED_CONTEXT", "SCIENCE_CANDIDATE_SNIPPETS")
# Invented staged terms from an invented origin PDF: never from a development document.
SNAPSHOT = {
    "version": "test-1",
    "terms": [
        {
            "term": "PlateCoolingRate",
            "kind": "class",
            "parent": "Measurement",
            "review_status": "REVIEWED",
            "origins": [{"source_id": "origin", "pdf_sha256": "0" * 64}],
        },
        {
            "term": "hasSealRating",
            "kind": "relation",
            "domain": ["Sample"],
            "range": ["Measurement"],
            "review_status": "REVIEWED",
            "origins": [{"source_id": "origin", "pdf_sha256": "0" * 64}],
        },
    ],
}


def track_b(monkeypatch, tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    monkeypatch.setenv("SCIENCE_STAGED_SNAPSHOT", str(path))
    for flag in TRACK_B:
        monkeypatch.setenv(flag, "1")


# Request keys that quote the document itself (its evidence, anchors and what the model
# read from them); every other key is text the code wrote or took from the vocabulary.
DOCUMENT_KEYS = frozenset(
    {
        "stage",
        "focus",
        "document_identity",
        "segments",
        "original_logical_sections",
        "source_anchors",
        "shared_context",
        "known_entities",
        "original_tables",
    }
)
V4 = "artifacts/phase1_generalizable_ingestion/v4"


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


def long_phrases(text, n=5):
    w = words(text)
    return {
        tuple(w[i : i + n])
        for i in range(len(w) - n + 1)
        if sum(x not in STOP for x in w[i : i + n]) >= 3
    }


def request_texts(payloads, systems):
    """Every string a request carries except the document's own text: the system prompts,
    the vocabulary (contracts, aliases, ontology context), the schema, the instructions,
    and the coverage and approved term of each source-term candidate (not its printed words)."""
    texts = list(systems)
    for payload in payloads:
        for key, value in payload.items():
            if key in DOCUMENT_KEYS or key.startswith("unstructured_") or key == "role_check":
                continue
            if key == "source_term_candidates":
                value = [{k: v for k, v in c.items() if k != "printed"} for c in value]
            texts += strings(value)
    return texts


CANDIDATE_TEXT = (
    "II. Methods\nSample S1 was tested in the burner.\n"
    "Sample S1 was tested in the burner with the Gamma paste.\n"
    "The quill gasket seat was inspected. The quill gasket seat was cleaned. "
    "Quill gasket seat wear was low.\n"
)


def all_request_texts(service, monkeypatch, tmp_path):
    track_b(monkeypatch, tmp_path)
    for flag in (*FLAGS, "SCIENCE_EXCLUDE_SEED_TERMS"):
        monkeypatch.setenv(flag, "1")
    systems = []
    payloads = run(service, monkeypatch, flags=FLAGS[:3], text=CANDIDATE_TEXT, systems=systems)
    keys = {k for p in payloads for k in p}
    # The vocabulary reaches the prompt through these keys; the check must see them.
    assert {"contracts", "ontology_context", "ontology_context_use", "schema"} <= keys
    assert {"relation_signatures", "vocabulary_extension", "role_vocabulary"} <= keys
    assert {"source_term_candidates", "source_term_contract"} <= keys
    return request_texts(payloads, systems)


def added_texts(service, monkeypatch, tmp_path):
    track_b(monkeypatch, tmp_path)
    for flag in FLAGS:
        monkeypatch.setenv(flag, "1")
    payloads = run(service, monkeypatch, flags=FLAGS[:3])
    texts = [t for p in payloads for key in ADDED_KEYS if key in p for t in strings(p[key])]
    schema = [p["schema"] for p in payloads if "schema" in p]
    texts += [t for s in schema for t in strings(s) if len(t.split()) > 6]
    assert any("data_provenance" in t for t in texts)
    return texts


def test_added_prompt_text_copies_no_target_quote(service, monkeypatch, tmp_path):
    quotes = []
    for path in glob.glob(f"{V4}/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    assert len(quotes) >= 124
    target = set().union(*(phrases(q) for q in quotes))
    texts = added_texts(service, monkeypatch, tmp_path)
    assert sorted({" ".join(p) for t in texts for p in phrases(t) & target}) == []


def test_added_prompt_text_copies_no_phrase_of_the_development_documents(
    service, monkeypatch, tmp_path
):
    documents = set()
    for path in glob.glob(f"{V4}/independent_*/prepared_1.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            package = json.load(handle)["package"]
        documents |= long_phrases("\n".join(e["text"] for e in package["evidence"]))
    assert documents
    texts = added_texts(service, monkeypatch, tmp_path)
    assert sorted({" ".join(p) for t in texts for p in long_phrases(t) & documents}) == []


def test_every_request_text_but_the_document_copies_no_target_quote(service, monkeypatch, tmp_path):
    quotes = []
    for path in glob.glob(f"{V4}/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    target = set().union(*(phrases(q) for q in quotes))
    texts = all_request_texts(service, monkeypatch, tmp_path)
    assert sorted({" ".join(p) for t in texts for p in phrases(t) & target}) == []


def test_every_request_text_but_the_document_copies_no_development_phrase(
    service, monkeypatch, tmp_path
):
    documents = set()
    for path in glob.glob(f"{V4}/independent_*/prepared_1.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            package = json.load(handle)["package"]
        documents |= long_phrases("\n".join(e["text"] for e in package["evidence"]))
    assert documents
    texts = all_request_texts(service, monkeypatch, tmp_path)
    assert sorted({" ".join(p) for t in texts for p in long_phrases(t) & documents}) == []
