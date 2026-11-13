"""Trim invariant: trimming a record's quote inside its located printed sentence never moves
the record to a more accepted status.

    status(trimmed quote) <= status(full sentence), with REJECTED < UNRESOLVED < SOURCE_SUPPORTED.

The general acceptance test for every "vetoes read the evidence sentence" family: a veto that reads
only the model's quote can be evaded by dropping the words it reads. The engine is
`trim_violations`; each family adds its kind to `KINDS` and its flag to `FLAGS`.

The reference unit is the printed line(s) around the located span, cut by the current splitter
(clause_cues.SENTENCE_BREAK on the segmentation view: every line break and every sentence end, no
de-wrap layer): the line holding the span, or the union of the lines it touches. A "full" variant
extends the located quote to that unit; a "trimmed" variant cuts the unit at word boundaries on both
sides of the value (the value occurrence and its number stay inside). A sentence wrapped over two
printed lines is two units here: that cross-line case is the declared residual, not tested.
Seeded and deterministic.

Run:  pytest tests/test_trim_invariant.py                      (synthetic + negatives, fast)
      TRIM_INVARIANT_SLOW=1 pytest tests/test_trim_invariant.py (the saved readings)
The violations the slow mode reports are synthetic trims over real records: they show that the gap
can be evaded, not that the model has evaded it.

Flags: SCIENCE_EVIDENCE_VETO_QUANTITIES=1 turns family 1 (quantities) on; the test must pass with
it on. With it off it reports the violations (the defect), see `main`.
"""

import copy
import gzip
import json
import os
import random
import re
import shutil
import sys
from pathlib import Path

import pytest
from test_cited_value_attribution_gap import (
    GUARDS,
    REFERENCES,
    REVIEW,
    SYNTHETIC,
)
from test_document_extraction import entity, submitted, support
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.clause_cues import SENTENCE_BREAK, locate_value, segmentation_view
from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.source_spans import locate

service = _service
ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = "SOURCE_SUPPORTED"
ORDER = {"REJECTED": 0, "UNRESOLVED": 1, SUPPORTED: 2}
KINDS = ("quantities", "entities", "relations")  # families add their kind here
FLAGS = {
    "quantities": "SCIENCE_EVIDENCE_VETO_QUANTITIES",
    "entities": "SCIENCE_EVIDENCE_VETO_ENTITIES",
    "relations": "SCIENCE_EVIDENCE_VETO_ENTITIES",
}
EXTRA_FLAGS = ("SCIENCE_NUMERIC_UNIT_RANGE",)  # fixes the family relies on
LIVE = Path(os.getenv("NASA_LIVE_DIR", r"C:/Users/legom/Documents/proyects/nasa-live")) / os.getenv(
    "TRIM_REPLAY_SET", "replay-14b-base"
)
NEGATIVES = (
    ROOT
    / "artifacts/phase1_generalizable_ingestion/v6/milestone14/package_c/historical_negatives_receipt.json"
)
TAG = "_trim_index"

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def printed_line(text, offset):
    """(start, end) of the printed line holding ``offset``: the piece between two cuts of the
    current splitter (a line break or a sentence end), no de-wrap."""
    start = 0
    for cut in SENTENCE_BREAK.finditer(segmentation_view(text)):
        if cut.start() >= offset:
            return start, cut.start()
        start = cut.end()
    return start, len(text)


def value_site(item, evidence):
    """(support index, evidence text, absolute value offset, value length) or None."""
    try:
        spans = locate(item["support"], evidence)
    except (ValueError, KeyError):
        return None
    for index, span in enumerate(spans):
        found = locate_value(span["quote"], item.get("expression"))
        if found is not None:
            number = NUMBER.match(span["quote"][found:])
            length = len(number.group()) if number else 1
            return index, span, span["start"] + found, length
    return None


def word_starts(text, lo, hi):
    return [p for p in range(lo, hi + 1) if p == lo or text[p - 1].isspace() and p < len(text)]


def word_ends(text, lo, hi):
    return [
        p
        for p in range(lo, hi + 1)
        if p == hi or (p < len(text) and text[p].isspace() and not text[p - 1].isspace())
    ]


def label_site(item, evidence, labels):
    """(support index, span, absolute offset, length) of the labels an entity or a relation names
    in its support, or None. The anchor is the union of the first printed occurrence of each
    label inside one span (the trim never cuts into it, as it never cuts into a value)."""
    labels = [label for label in labels if isinstance(label, str) and label]
    try:
        spans = locate(item["support"], evidence)
    except (ValueError, KeyError):
        return None
    if not labels:  # no endpoint is defined: the anchor is the start of the first span
        return (0, spans[0], spans[0]["start"], 0) if spans else None
    for index, span in enumerate(spans):
        low, high = None, None
        for label in labels:
            found = re.search(
                r"(?<![\w-])" + re.escape(label) + r"(?![\w-])", span["quote"], re.IGNORECASE
            )
            if found is None:
                low = None
                break
            a, b = span["start"] + found.start(), span["start"] + found.end()
            low = a if low is None else min(low, a)
            high = b if high is None else max(high, b)
        if low is not None:
            return index, span, low, high - low
    return None


def anchor_site(output, kind, item, evidence):
    """The anchor a trim keeps whole, by kind: the value of a quantity, the label of an entity,
    the labels of the two endpoints of a relation."""
    if kind == "quantities":
        return value_site(item, evidence)
    by_key = {e["key"]: e["label"] for e in output["entities"]}
    if kind == "entities":
        return label_site(item, evidence, [item["label"]])
    return label_site(item, evidence, [by_key.get(item["subject"]), by_key.get(item["object"])])


def variants(item, evidence, rng, trims, site="value"):
    """(full_support, [trimmed_support, ...]) for one proposal, or None when not placeable."""
    site = value_site(item, evidence) if site == "value" else site
    if not site:
        return None
    index, span, vabs, vlen = site
    text = evidence[span["evidence_id"]]["text"]
    s0, _ = printed_line(text, span["start"])
    _, s1 = printed_line(text, max(span["start"], span["end"] - 1))
    lo, hi = min(span["start"], s0), max(span["end"], s1)  # the union of the lines it touches
    starts = [p for p in word_starts(text, lo, vabs) if p <= vabs]
    ends = [p for p in word_ends(text, vabs + vlen, hi) if p >= vabs + vlen]
    if not starts or not ends:
        return None

    def made(a, b):
        out = copy.deepcopy(item["support"])
        out[index] = {"evidence_id": span["evidence_id"], "quote": text[a:b], "start": a}
        return out

    full = made(lo, hi)
    cuts = {
        (rng.choice(starts), rng.choice(ends)) for _ in range(trims * 3)
    }  # distinct, seeded draws
    cuts = sorted(c for c in cuts if (c[0], c[1]) != (lo, hi))[:trims]
    return full, [made(a, b) for a, b in cuts], text[lo:hi]


def run(output, package, document, semantic, supports, kind="quantities"):
    """Validate the output with each proposal's support replaced; {index: record}."""
    from nasa_fire_ai.ingestion.extraction_validation import validated_output

    out = copy.deepcopy(output)
    for index, support_ in supports.items():
        out[kind][index]["support"] = support_
        out[kind][index][TAG] = index
    result = validated_output(out, package, document, semantic)
    return {
        r["proposal"][TAG]: r
        for r in result["records"]
        if r["kind"] == kind and TAG in r["proposal"]
    }


UNDEFINED_ENDPOINT = []  # (kind, index, trims) of the relations whose endpoint is not defined
STRUCTURAL_ENDPOINT = []  # same, for endpoints the pipeline itself defines ("structure-" keys)


def undefined_endpoint(output, kind, item):
    """ "undefined", "structural" or None. A relation naming an endpoint key the output does not
    define is not skipped: it is checked and must not be SOURCE_SUPPORTED, whole or trimmed. A
    "structure-" key is an entity the validation builds from the document's own structure (not in
    the model output): counted apart, and checked as any relation."""
    if kind != "relations":
        return None
    keys = {e["key"] for e in output["entities"]}
    missing = [k for k in (item.get("subject"), item.get("object")) if k not in keys]
    if missing and all(str(k).startswith("structure-") for k in missing):
        return "structural"
    return "undefined" if missing else None


def trim_violations(
    output, package, document, semantic, seed=0, trims=3, only=None, kind="quantities"
):
    """[(index, full_status, trimmed_status, sentence, trimmed_quote)] where a trim is accepted more."""
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    rng = random.Random(seed)
    plan, undefined, structural = {}, set(), set()
    for index, item in enumerate(output[kind]):
        if only is not None and index not in only:
            continue
        if "support" not in item:
            continue
        endpoint = undefined_endpoint(output, kind, item)
        if endpoint == "undefined":
            undefined.add(index)
        elif endpoint == "structural":
            structural.add(index)
        made = variants(item, evidence, rng, trims, anchor_site(output, kind, item, evidence))
        if made:
            plan[index] = made
    if not plan:
        return [], 0
    full = run(output, package, document, semantic, {i: p[0] for i, p in plan.items()}, kind)
    found, checked = [], 0
    for t in range(trims):
        supports = {i: p[1][t] for i, p in plan.items() if t < len(p[1])}
        if not supports:
            break
        trimmed = run(output, package, document, semantic, supports, kind)
        for i, record in trimmed.items():
            if i not in full:
                continue
            checked += 1
            a, b = full[i]["status"], record["status"]
            if ORDER[b] > ORDER[a]:
                found.append((i, a, b, plan[i][2], plan[i][1][t][0]["quote"]))
            elif i in undefined and SUPPORTED in (a, b):
                found.append((i, a, b, "UNDEFINED_ENDPOINT_SUPPORTED", plan[i][1][t][0]["quote"]))
    for i in structural & set(plan):
        STRUCTURAL_ENDPOINT.append((kind, i, len(plan[i][1])))
    for i in undefined & set(plan):
        UNDEFINED_ENDPOINT.append((kind, i, len(plan[i][1])))
        if i in full and full[i]["status"] == SUPPORTED:
            found.append(
                (i, full[i]["status"], full[i]["status"], "UNDEFINED_ENDPOINT_SUPPORTED", "")
            )
    return found, checked


# ---- (c) the synthetic cases -------------------------------------------------------------


def synthetic_output(service, material, study, sentence, expression):
    p = submitted(service, "II. Results\n" + sentence + "\n" + REFERENCES)
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", material, "Sample", sentence, study=study)]
    o["quantities"] = [
        {
            "subject": "n",
            "label": "smolder time",
            "expression": expression,
            "unit": "s",
            "epistemic": "reported_quantity",
            "support": support(p, sentence),
        }
    ]
    return p, o


# Invented trims of the audit's families (quantity facets, not-done, caption, derivation).
AUDIT = (
    {
        "name": "chamber",
        "sentence": "In the Alpha run the chamber pressure was set to 2.4 atm for the next series.",
        "expression": "2.4",
        "unit": "atm",
        "label": "chamber pressure",
        "epistemic": "experimental_configuration",
    },
    {
        "name": "burn rate",
        "sentence": "In the Alpha run the calculated burn rate was 2.1 mm/s.",
        "expression": "2.1",
        "unit": "mm/s",
        "label": "burn rate",
        "epistemic": "reported_quantity",
    },
    {
        "name": "flame",
        "sentence": "Figure 6 \u2013 Alpha sheet flame length 4.2 cm at 21% O2",
        "expression": "4.2",
        "unit": "cm",
        "label": "flame length",
        "epistemic": "reported_quantity",
        "subject": ("Alpha sheet", "Sample"),
    },
    {
        "name": "rival",
        "sentence": "The Beta sheet, cut from the Alpha sheet, had an ignition temperature of 410 C.",
        "expression": "410",
        "unit": "C",
        "label": "ignition temperature",
        "epistemic": "reported_quantity",
        "subject": ("Alpha sheet", "Sample"),
        "others": (("Beta sheet", "Sample"),),
    },
)


def audit_output(service, case):
    sentence = case["sentence"]
    label, cls = case.get("subject", ("Alpha run", "ExperimentalRun"))
    p = submitted(service, "II. Results\n" + sentence + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", label, cls, sentence, study="current")]
    for k, (other, other_cls) in enumerate(case.get("others", ())):
        o["entities"].append(entity(p, f"o{k}", other, other_cls, sentence, study="current"))
    o["quantities"] = [
        {
            "subject": "n",
            "label": case["label"],
            "expression": case["expression"],
            "unit": case["unit"],
            "epistemic": case["epistemic"],
            "support": support(p, sentence),
        }
    ]
    return p, o


def semantic_of(service, package):
    from nasa_fire_ai.ingestion.document_extraction import extraction_semantic

    return extraction_semantic(service, package)


def structure_of(service, package):
    from test_document_extraction import structure

    return structure(package, service.root)


def check(service, package, output, seed=0, trims=6, kind="quantities"):
    document = structure_of(service, package)
    return trim_violations(
        output, package, document, semantic_of(service, package), seed, trims, kind=kind
    )


def cases():
    for c in (*SYNTHETIC, *REVIEW):
        yield (
            "syn-" + c[0].replace(" ", "-"),
            (lambda s, c=c: synthetic_output(s, c[0], c[1], c[2], c[3])),
        )
    for c in GUARDS:
        yield (
            "guard-" + c[2][:20].replace(" ", "-"),
            (lambda s, c=c: synthetic_output(s, c[0], "current", c[1], c[2])),
        )
    for c in AUDIT:
        yield "audit-" + c["name"], (lambda s, c=c: audit_output(s, c))


# Closed by the final round of ORIGIN_CHECK (fixes 1, 2, 4-7): the ten cases that were open now hold.
OPEN_CITED = set()
OPEN_REASON = (
    "Freeze 3.2 condition (evidence-reading families 1-3): a trimmed quote that drops a "
    "citation marker must not be more accepted; open until the cited family closes it."
)


def case_params():
    def marks(name):
        if name in OPEN_CITED:
            return [pytest.mark.xfail(strict=True, reason=OPEN_REASON)]
        return []

    return [pytest.param(name, build, id=name, marks=marks(name)) for name, build in cases()]


@pytest.fixture(autouse=True)
def families_on(monkeypatch):
    """Every family's flag is on, unless TRIM_INVARIANT_FLAGS=off (report the defect)."""
    if os.getenv("TRIM_INVARIANT_FLAGS", "on") != "off":
        for kind in KINDS:
            monkeypatch.setenv(FLAGS[kind], "1")
        for name in EXTRA_FLAGS:
            monkeypatch.setenv(name, "1")


@pytest.mark.parametrize(("name", "build"), case_params())
def test_trimming_a_synthetic_quantity_never_raises_its_status(service, monkeypatch, name, build):
    monkeypatch.setenv("SCIENCE_ORIGIN_CHECK", "1")
    package, output = build(service)
    found, _checked = check(service, package, output)
    assert not found, found


# Invented entities and relations (family 3): the sentence is the whole printed line; every trim
# keeps the label(s) whole and cuts the words around them.
ENTITY_AUDIT = (
    (
        "planned run",
        "Test 7 was performed as a dry run and later cancelled.",
        "7",
        "ExperimentalRun",
    ),
    (
        "strategic phase",
        "Phase 2 will extend the programme if funding allows.",
        "Phase 2",
        "ExperimentFamily",
    ),
    (
        "future research",
        "The Alpha Experiment which will fly next year studies ignition.",
        "Alpha Experiment",
        "Investigation",
    ),
    (
        "cited research",
        "Previous studies Alpha Tests reported smoldering in this blend.",
        "Alpha Tests",
        "ExperimentFamily",
    ),
    (
        "test medium",
        "The chamber was pressurized with Zeta gas before each burn.",
        "Zeta gas",
        "Material",
    ),
    ("plain run", "Test 8 was performed on the Alpha sheet.", "8", "ExperimentalRun"),
)
RELATION_AUDIT = (
    ("exception", "Alpha was burned at 21% O2 except in Run 4."),
    ("negation", "Alpha was not burned at 21% O2 in the second series."),
    ("plain", "Alpha was burned at 21% O2 in the second series."),
)


def entity_audit_output(service, case):
    _name, sentence, label, cls = case
    p = submitted(service, "II. Results\n" + sentence + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", label, cls, sentence, study="current")]
    return p, o


def relation_audit_output(service, case):
    _name, sentence = case
    p = submitted(service, "II. Results\n" + sentence + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "s", "Alpha", "Sample", sentence),
        entity(p, "o", "21% O2", "ExperimentalCondition", sentence),
    ]
    o["relations"] = [
        {"subject": "s", "relation": "hasCondition", "object": "o", "support": support(p, sentence)}
    ]
    return p, o


@pytest.mark.parametrize("case", ENTITY_AUDIT, ids=[c[0] for c in ENTITY_AUDIT])
def test_trimming_a_synthetic_entity_never_raises_its_status(service, case):
    package, output = entity_audit_output(service, case)
    found, checked = check(service, package, output, kind="entities")
    assert checked
    assert not found, found


@pytest.mark.parametrize("case", RELATION_AUDIT, ids=[c[0] for c in RELATION_AUDIT])
def test_trimming_a_synthetic_relation_never_raises_its_status(service, case):
    package, output = relation_audit_output(service, case)
    found, checked = check(service, package, output, kind="relations")
    assert checked
    assert not found, found


# ---- (a) the saved readings, (b) the historical negatives -----------------------------------


def prepared_context(service, prepared):
    """What the offline replay validates: (consolidated output, package, document, semantic)."""
    from nasa_fire_ai.ingestion.document_extraction import (
        Output as O,
    )
    from nasa_fire_ai.ingestion.document_extraction import (
        merge_output,
        resolve_explicit_scopes,
    )
    from nasa_fire_ai.ingestion.table_continuity import link_continuation_tables

    package = prepared["package"]
    extraction = package["scientific_extraction"]
    document = extraction["document"]
    document["detected_tables"] = link_continuation_tables(document["detected_tables"])
    output = extraction["raw_proposals"]
    resolve_explicit_scopes(output, document)
    consolidated = O().model_dump()
    merge_output(consolidated, output)
    return consolidated, package, document, semantic_of(service, package)


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def same_proposal(kind, item, saved):
    """Whether a consolidated proposal is the saved record's proposal, by what names it."""
    if kind == "quantities":
        return item.get("expression") == saved.get("expression") and item.get("label") == saved.get(
            "label"
        )
    if kind == "entities":
        return item.get("label") == saved.get("label") and item.get("class_id") == saved.get(
            "class_id"
        )
    return all(item.get(k) == saved.get(k) for k in ("subject", "relation", "object"))


def drive(service, path, seed, trims, ids=None, kind="quantities"):
    consolidated, package, document, semantic = prepared_context(service, load(path))
    only = None
    if ids is not None:
        saved = {
            r["id"]: r["proposal"]
            for r in package["scientific_extraction"]["records"]
            if r["id"] in ids and r["kind"] == kind
        }
        only = {
            i
            for i, q in enumerate(consolidated[kind])
            if any(same_proposal(kind, q, p) for p in saved.values())
        }
    return trim_violations(consolidated, package, document, semantic, seed, trims, only, kind)


@pytest.mark.skipif(not NEGATIVES.exists(), reason="no negatives receipt")
def test_trimming_a_historical_negative_never_raises_its_status(service):
    receipt = json.loads(NEGATIVES.read_text(encoding="utf-8"))
    bad, checked = [], 0
    for entry in receipt["sets"]:
        path = ROOT / entry["original_package"]
        if not path.exists():
            continue
        ids = {item["id"] for item in entry["items"]}
        found, n = drive(service, path, seed=1, trims=4, ids=ids)
        bad += [(entry["label"], *f) for f in found]
        checked += n
    if not checked:
        # The 29 negatives are 23 statements and 6 entities: no quantity among them. The
        # statement and entity families extend KINDS and `variants` for their own kind.
        pytest.skip("no quantity among the historical negatives")
    assert not bad, (checked, bad)


@pytest.mark.skipif(not NEGATIVES.exists(), reason="no negatives receipt")
def test_trimming_a_historical_negative_entity_never_raises_its_status(service):
    receipt = json.loads(NEGATIVES.read_text(encoding="utf-8"))
    bad, checked = [], 0
    for entry in receipt["sets"]:
        path = ROOT / entry["original_package"]
        if not path.exists():
            continue
        ids = {item["id"] for item in entry["items"]}
        found, n = drive(service, path, seed=1, trims=4, ids=ids, kind="entities")
        bad += [(entry["label"], *f) for f in found]
        checked += n
    if not checked:
        pytest.skip("no entity among the historical negatives")
    assert not bad, (checked, bad)


TOLERATED = (
    ROOT
    / "artifacts/phase1_generalizable_ingestion/v6/milestone14/phase1/trim_residual"
    / "QUANTITIES_TOLERATED.json"
)
TOLERATED_COUNT = 14  # the set may not grow


def tolerated_cases():
    return json.loads(TOLERATED.read_text(encoding="utf-8"))["cases"]


def crosses_a_printed_line_break(case):
    """The trim is a piece of its sentence that spans two printed lines (a break inside it)."""
    trim, full = case["trim_text"], case["full_text"]
    return trim in full and "\n" in trim.strip() and case["full_status"] != case["trim_status"]


def without_tolerated(violations):
    """Violations (path, index, full status, trim status, sentence, trim) outside the tolerated set.

    Only the quantities kind has a tolerance: the exact cases of the artifact, each a trim across
    a printed line break. A tolerated case that no longer violates is reported by a warning."""
    import warnings

    cases = tolerated_cases()
    assert len(cases) <= TOLERATED_COUNT, "the tolerated set grew"
    assert all(crosses_a_printed_line_break(c) for c in cases)
    keys = {
        (
            c["package"],
            c["record_index"],
            c["full_status"],
            c["trim_status"],
            c["full_text"],
            c["trim_text"],
        )
        for c in cases
    }
    outside = [v for v in violations if tuple(v) not in keys]
    seen = {tuple(v) for v in violations}
    for key in sorted(keys - seen):
        warnings.warn(f"tolerated trim no longer violates: {key[0]} record {key[1]}", stacklevel=2)
    return outside


@pytest.mark.skipif(
    os.getenv("TRIM_INVARIANT_SLOW") != "1" or not LIVE.exists(),
    reason="slow: set TRIM_INVARIANT_SLOW=1 (saved readings under nasa-live)",
)
@pytest.mark.parametrize("kind", KINDS)
def test_trimming_any_saved_record_never_raises_its_status(service, kind):
    bad, checked = [], 0
    for path in sorted(LIVE.rglob("prepared.json.gz")):
        samples = int(os.getenv("TRIM_SAMPLES", "3"))
        found, n = drive(service, path, seed=7, trims=samples, kind=kind)
        bad += [(str(path.relative_to(LIVE)).replace("\\", "/"), *f) for f in found]
        checked += n
    if kind == "quantities":
        bad = without_tolerated(bad)
    assert not bad, (checked, len(bad), bad[:20])


def main():
    """Report mode: every violation of the saved readings, one JSON line each (flag as set)."""
    import tempfile

    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.services.curation import CurationService

    seed, trims = int(sys.argv[2]), int(sys.argv[3])
    only = sys.argv[4:] or None
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name in ("domain", "ontology", "data/canonical"):
            shutil.copytree(ROOT / name, tmp / name)
        registry = EvidenceRegistry(tmp / "data/index/evidence.sqlite")
        svc = CurationService(tmp, registry)
        try:
            for path in sorted(LIVE.rglob("prepared.json.gz")):
                rel = str(path.relative_to(LIVE)).replace("\\", "/")
                if only and not any(o in rel for o in only):
                    continue
                for kind in os.getenv("TRIM_KINDS", "quantities").split(","):
                    found, n = drive(svc, path, seed, trims, kind=kind)
                    row = {"file": rel, "kind": kind, "checked": n, "violations": found}
                    print(json.dumps(row), flush=True)
        finally:
            registry.db.close()


if __name__ == "__main__":
    main()


def test_the_tolerated_quantity_trims_are_exactly_the_listed_line_break_trims():
    cases = tolerated_cases()
    assert len(cases) == TOLERATED_COUNT
    assert all(crosses_a_printed_line_break(c) for c in cases)
    assert len({(c["package"], c["record_index"], c["trim_text"]) for c in cases}) == len(cases)
