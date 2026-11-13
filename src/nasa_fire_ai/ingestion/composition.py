"""Material composition read from a document's own wording, staged for review.

A source can say that one material is made of others: "The composition of X is
40% A and 60% B", "X is made up of 90% A, 8% B, and 2% C", "X uses A filler in
B", "A-filled B", "the percentage of A in X is not known". This module reads
those statements generically, from wording and nothing else, and stages each
as a component assertion:

* a candidate ``hasComponent`` relation (Material to Material), which the
  approved ontology does not define (``madeOf`` relates a sample or a run to
  its material, not a material to its constituents);
* the component's documented role (``filler``) as a characteristic of that one
  assertion, never as a global property;
* its documented proportion, with the basis (mass, volume, molar) only when the
  source states it, and a documented unknown kept as unknown.

Nothing here is published to the ontology, the baseline or the graph. Every
assertion carries its literal source sentence and starts as
``SOURCE_SUPPORTED_PENDING_REVIEW``; ``VALIDATED`` and ``APPROVED`` are set only
by a scientist. Explanations are rendered from the structured assertions, so a
sentence can never say more than the record it was built from.
"""

import hashlib
import json
import os
import re

from nasa_fire_ai.ingestion.abbreviations import ViewPattern, segmentation_view
from nasa_fire_ai.ingestion.clause_cues import _APPROXIMATOR, DETERMINERS

LIFECYCLE = ("PROPOSED", "SOURCE_SUPPORTED_PENDING_REVIEW", "VALIDATED", "APPROVED")
NAME = r"[A-Z][\w®™.+-]*(?:\s+(?:[A-Z][\w®™.+-]*|\d+[\w®™-]*))*|[a-z][a-z-]{2,}"
ITEM = re.compile(rf"(?P<value>\d+(?:\.\d+)?)\s*%\s*(?:of\s+)?(?P<name>{NAME})")
BASIS = (
    (
        re.compile(
            r"\b(?:by\s+(?:weight|mass)|wt\.?\s*%|weight\s+(?:percent|fraction)|mass\s+fraction)",
            re.IGNORECASE,
        ),
        "MASS",
    ),
    (
        re.compile(r"\b(?:by\s+volume|vol\.?\s*%|volume\s+(?:percent|fraction))", re.IGNORECASE),
        "VOLUME",
    ),
    (re.compile(r"\b(?:mol(?:e|ar)?\s*%|mole\s+fraction)", re.IGNORECASE), "MOLAR"),
)
LIST = re.compile(
    r"(?:the\s+)?composition\s+of\s+(?P<subject>.+?)\s+(?:is|was)\s+(?P<items>.+)"
    r"|(?P<subject2>.+?)\s+(?:is|are|was|were)\s+(?:made\s+up|composed|comprised|formed)\s+of\s+(?P<items2>.+)"
    r"|(?P<subject3>.+?)\s+consists?\s+of\s+(?P<items3>.+)",
    re.IGNORECASE,
)
COMPONENT_OF = re.compile(
    rf"^(?:the\s+)?(?P<component>{NAME})\s+component\s+of\s+(?P<parent>.+)$", re.IGNORECASE
)
FILLER_IN = re.compile(
    rf"(?P<subject>{NAME})\s+(?:uses|contains|incorporates)\s+(?:a\s+)?(?P<component>{NAME})\s+fillers?\s+in\s+(?P<host>{NAME})",
)
WITH_FILLER = ViewPattern(
    re.compile(
        rf"(?:formulation|compound|grade|version)\s+of\s+(?P<host>[^.,;]+?)\s+with\s+(?P<component>{NAME})\s+fillers?\b",
        re.IGNORECASE,
    )
)
FILLED_NAME = re.compile(r"(?<![\w-])(?P<component>[A-Z][\w®™]*)-filled\s+(?P<host>[A-Z][\w®™()]*)")
UNKNOWN = ViewPattern(
    re.compile(
        rf"(?:percentage|fraction|proportion|amount)\s+of\s+(?P<component>{NAME})\s+in\s+(?:the\s+)?(?P<subject>[^.,;]+?)\s+is\s+(?:not\s+known|unknown|not\s+reported)",
        re.IGNORECASE,
    )
)
DESCRIPTOR = ViewPattern(
    re.compile(
        r"\b(?:an?\s+)?(?:similar\s+|new\s+)?(?P<descriptor>[\w\s-]{0,40}?\b(?:compound|composite|blend|mixture|formulation|alloy))\s+(?:named|called)\s+(?P<name>[^.,;]+)",
        re.IGNORECASE,
    )
)


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").replace("­", "")).strip()


def _name(text):
    """A printed name without the sentence punctuation that follows it."""
    return re.sub(r"[.,;:]+$", "", _norm(text))


def _key(text):
    return re.sub(r"[^a-z0-9%]+", "", _norm(text).lower())


def _sentences(text):
    joined = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "-", text)
    starts = [0] + [
        m.end() for m in re.finditer(r"(?<!\b[A-Z])[.!?](?=\s)", segmentation_view(joined))
    ]
    for begin, end in zip(starts, starts[1:] + [len(joined)]):
        sentence = joined[begin:end].strip()
        if sentence:
            yield sentence


def _basis(sentence):
    for pattern, basis in BASIS:
        if pattern.search(sentence):
            return basis
    return "UNSPECIFIED_IN_SOURCE"


def _entity(name, entities):
    """The supported entity a printed name refers to, if any."""
    key = _key(name)
    if not key:
        return None
    exact = [e for e in entities if _key(e["label"]) == key]
    if exact:
        return exact[0]
    # "Quartex-B®." or "the Copper-filled resin coupons" around a known name.
    contained = sorted(
        (
            e
            for e in entities
            if _key(e["label"]) and _key(e["label"]) in key and e["class_id"] == "Material"
        ),
        key=lambda e: -len(_key(e["label"])),
    )
    return contained[0] if contained else None


def _reference(name, entities):
    name = _name(name)
    entity = _entity(name, entities)
    if entity:
        return {"label": entity["label"], "entity_id": entity["id"], "class_id": entity["class_id"]}
    return {
        "label": _norm(name),
        "entity_id": None,
        "class_id": "Material",
        "entity_status": "STAGED_ENTITY_PROPOSAL",
    }


def _identity(*parts):
    return hashlib.sha256(
        json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:20]


def composition_assertions(evidence, entities):
    """Component assertions the document itself states, with their evidence.

    ``evidence`` is the package evidence list; ``entities`` are the validated,
    source-supported entities (``id``, ``label``, ``class_id``).
    """
    found = {}

    def add(
        subject,
        component,
        sentence,
        page_evidence,
        role=None,
        host=None,
        value=None,
        basis=None,
        proportion_status=None,
        context=None,
        descriptor=None,
        descriptors=None,
    ):
        subject_ref = _reference(subject, entities)
        component_ref = _reference(component, entities)
        # The subject is a material the document's validated record names, or
        # a component of one ("the Bronze component of X").
        if (
            not context
            and subject_ref["class_id"] != "Material"
            or (not context and subject_ref["entity_id"] is None)
        ):
            return
        if _key(subject_ref["label"]) == _key(component_ref["label"]):
            return
        key = (_key(subject_ref["label"]), _key(component_ref["label"]), _key(context or ""))
        record = found.setdefault(
            key,
            {
                "id": "composition-" + _identity(*key),
                "relation_candidate": "hasComponent",
                "subject": subject_ref,
                "component": component_ref,
                "context": context,
                "role": None,
                "role_host": None,
                "proportion": None,
                "source_descriptor": None,
                "evidence": [],
                "lifecycle": "SOURCE_SUPPORTED_PENDING_REVIEW",
                "activation": "NONE",
            },
        )
        if role and not record["role"]:
            record["role"] = role
            record["role_host"] = _reference(host, entities) if host else None
        if value is not None and not record["proportion"]:
            record["proportion"] = {
                "value": value,
                "unit": "%",
                "basis": basis,
                "status": "REPORTED",
            }
        if proportion_status and not record["proportion"]:
            record["proportion"] = {
                "value": None,
                "unit": None,
                "basis": None,
                "status": proportion_status,
            }
        descriptor = descriptor or next(
            (d for k, d in (descriptors or {}).items() if k.startswith(_key(subject_ref["label"]))),
            None,
        )
        if descriptor and not record["source_descriptor"]:
            record["source_descriptor"] = descriptor
        quote = {
            "evidence_id": page_evidence["evidence_id"],
            "page": page_evidence.get("page"),
            "quote": sentence,
        }
        if quote not in record["evidence"]:
            record["evidence"].append(quote)

    for page in evidence:
        for sentence in _sentences(page.get("text", "")):
            flat = _norm(sentence)
            descriptors = {
                _key(m["name"]): _norm(m["descriptor"]) for m in DESCRIPTOR.finditer(flat)
            }
            listed = LIST.search(flat)
            if listed:
                subject = listed["subject"] or listed["subject2"] or listed["subject3"]
                items = listed["items"] or listed["items2"] or listed["items3"]
                subject = subject.strip()
                context = None
                nested = COMPONENT_OF.match(subject)
                if nested:
                    # "The Copper component of Quartex-B® consists of ...": the
                    # copper of that formulation, not the substance in general.
                    context = _reference(nested["parent"], entities)["label"]
                    subject = nested["component"]
                parts = list(ITEM.finditer(items))
                if parts:
                    basis = _basis(flat)
                    for part in parts:
                        add(
                            subject,
                            part["name"],
                            flat,
                            page,
                            value=float(part["value"]),
                            basis=basis,
                            context=context,
                            descriptors=descriptors,
                        )
            for m in FILLER_IN.finditer(flat):
                add(
                    m["subject"],
                    m["component"],
                    flat,
                    page,
                    role="filler",
                    host=m["host"],
                    descriptors=descriptors,
                )
                add(m["subject"], m["host"], flat, page, descriptors=descriptors)
            for m in WITH_FILLER.finditer(flat):
                host = re.sub(r"\s*\([^()]*\)\s*$", "", m["host"]).strip()
                named = [
                    e
                    for e in entities
                    if e["class_id"] == "Material"
                    and re.fullmatch(
                        rf"{re.escape(m['component'])}-filled\s+.+", e["label"], re.IGNORECASE
                    )
                ]
                for subject in named:
                    add(subject["label"], m["component"], flat, page, role="filler", host=host)
            for m in UNKNOWN.finditer(flat):
                add(
                    m["subject"],
                    m["component"],
                    flat,
                    page,
                    proportion_status="NOT_KNOWN_PER_SOURCE",
                )
    # A material whose printed name is "A-filled B" names A as its filler in B.
    for e in entities:
        m = FILLED_NAME.fullmatch(_norm(e["label"])) if e["class_id"] == "Material" else None
        if not m:
            continue
        for page in evidence:
            for sentence in _sentences(page.get("text", "")):
                # A sentence of the text, not a title block or a table run.
                if _key(e["label"]) in _key(sentence) and len(_norm(sentence)) <= 300:
                    add(
                        e["label"],
                        m["component"],
                        _norm(sentence),
                        page,
                        role="filler",
                        host=m["host"],
                    )
                    add(e["label"], m["host"], _norm(sentence), page)
                    break
            else:
                continue
            break
    assertions = sorted(found.values(), key=lambda r: r["id"])
    by_subject = {}
    for record in assertions:
        by_subject.setdefault(
            (_key(record["subject"]["label"]), _key(record["context"] or "")), []
        ).append(record)
    for group in by_subject.values():
        values = [
            r["proportion"]["value"]
            for r in group
            if r["proportion"] and r["proportion"]["value"] is not None
        ]
        for record in group:
            if record["proportion"] and record["proportion"]["value"] is not None:
                # Recorded, never inferred from: the source's own figures.
                record["proportion"]["listed_components_sum"] = round(sum(values), 6)
    return assertions


# Scorable composition (SCIENCE_SCORABLE_COMPOSITION, off by default): an assertion between
# validated materials is also a relation record in staging, with its printed share.
# Two classes, each with a general reference; no member comes from a development document.
# (i) Negators: Huddleston and Pullum 2002, The Cambridge Grammar of the English Language,
# ch. 9 (negation): not, no, never, neither, nor, none, nothing, nobody, nowhere, and
# "without" as a negative preposition. "no longer" is "no" plus a time adjunct.
# (ii) Prepositions of exception and replacement: Quirk et al. 1985, A Comprehensive Grammar
# of the English Language (prepositions): except, excluding, instead of, in place of,
# rather than, and unlike (a preposition of contrast; kept as a safety member, its place in
# Quirk's list is not re-verified: dropping it could make the constituent after it read as a
# component). The sections are not cited here; the membership follows the design note.
NEGATORS = r"(?:not|no|never|neither|nor|none|nothing|nobody|nowhere|without)"
EXCEPTION_REPLACEMENT = r"(?:except|excluding|instead\s+of|in\s+place\s+of|rather\s+than|unlike)"
CONTRAST_CUES = r"(?:" + NEGATORS + r"|" + EXCEPTION_REPLACEMENT + r")"


def scorable_composition_enabled():
    return os.getenv("SCIENCE_SCORABLE_COMPOSITION", "0") == "1"


def class_nouns(semantic):
    """The words that name a material as a kind: the labels, aliases and query terms of the
    registry's ``Material`` class and of every class below it, as one alternation. None
    when the registry names no such class, so a trailing class noun is then never removed."""
    metadata = getattr(semantic, "class_metadata", None) or {}
    from nasa_fire_ai.ingestion.semantic import class_ancestors

    terms = set()
    for cls, meta in metadata.items():
        if "Material" in class_ancestors(cls, metadata):
            meta = meta or {}
            terms.update([cls, meta.get("label"), *meta.get("aliases", [])])
            terms.update(meta.get("query_terms", []))
    terms.update(getattr(semantic, "target_mentions", {}).get("Material", []))
    terms = sorted(
        {t.strip().lower() for t in terms if t and t.strip()}, key=lambda t: (-len(t), t)
    )
    return "(?:" + "|".join(re.escape(t) for t in terms) + ")" if terms else None


CLAUSE_END = re.compile(
    r"\s*;|\s+(?:whereas|which|while|but|and\s+whereas)\s+|,(?!\s*(?:and\s+)?(?:\d|the\s+balance))"
)
# A printed share that follows one of these is a bound, not an exact value. Subclasses:
# (i) structural comparative before "than" (Huddleston and Pullum 2002, ch. 13, comparative
# constructions): an -er form, "more", "less", "fewer";
# (ii) approximators: the class in clause_cues (Quirk et al. 1985, ch. 8; Huddleston and
# Pullum 2002, ch. 6), reused, not copied;
# (iii) relation signs of ISO 80000-2:2019 (items not re-verified here): < > <= >= approx, plus-minus;
# (iv) numeral modification (Huddleston and Pullum 2002, ch. 5; section not re-verified):
# at least, at most, up to, as much/little/many as.
# Fallback (structural, not a list): a share is exact only when nothing but a determiner or
# article stands between the previous list separator (or the start of the list) and its
# numeral (``_unqualified``). Any other preceding word or sign makes it a bound, so a
# qualifier that no class names still never reads as an exact value.
BOUND_CUE = re.compile(
    r"(?:\b(?:\w+er|more|less|fewer)\s+than\b|\b"
    + _APPROXIMATOR
    + r"\.?|\bat\s+(?:least|most)\b|\bup\s+to\b|\bas\s+(?:much|little|many)\s+as\b"
    + r"|[<>≤≥≈±])\s*(?:of\s+)?$",
    re.IGNORECASE,
)
RANGE_BEFORE = re.compile(r"\d+(?:\.\d+)?\s*(?:%\s*)?(?:-|–|—|to|±)\s*$", re.IGNORECASE)
CITATION = re.compile(
    r"\[\d+(?:\s*[,–-]\s*\d+)*\]|\bet\s+al\b|\breported\s+by\b|\baccording\s+to\b"
    r"|\(\s*[A-Z][A-Za-z-]+(?:\s+(?:and|&)\s+[A-Z][\w-]+)?,?\s+\d{4}[a-z]?\s*\)"
    r"|[¹²³⁰-⁹]|\^\d+|\b(?:earlier|previous|prior)\s+(?:study|studies|work)\b",
    re.IGNORECASE,
)


def _subject_matches(printed, label, nouns=None):
    """The printed subject is the formulation itself: at most a leading determiner and a
    trailing class noun around its name, never a longer phrase that merely contains it."""
    text = _name(printed)
    bare = re.sub(r"^(?:the|this|that|a|an)\s+", "", text, flags=re.IGNORECASE)
    bare_noun = re.sub(rf"\s+{nouns}$", "", bare, flags=re.IGNORECASE) if nouns else bare
    return _key(label) in {_key(text), _key(bare), _key(bare_noun)} and bool(_key(label))


LIST_SEPARATOR = re.compile(r"[,;&]|\b(?:and|or)\b", re.IGNORECASE)


def _qualifier(items, start, previous_end):
    """The words standing immediately before a numeral in its list item, after the last list
    separator, that are neither a determiner nor an article. Empty when the share is bare."""
    segment = items[previous_end:start]
    tail = LIST_SEPARATOR.split(segment)[-1]
    words = tail.split()
    return " ".join(w for w in words if w.lower() not in DETERMINERS and w.lower() != "of") or None


def _list_shares(sentence, subject_label, component_label, nouns=None):
    """Printed shares for the component in a composition list whose grammatical subject is
    exactly the formulation. None when the sentence is not such a list for this pair."""
    flat = _norm(sentence)
    listed = LIST.search(flat)
    if not listed:
        return None
    group = next(g for g in ("items", "items2", "items3") if listed[g])
    subject = (listed["subject"] or listed["subject2"] or listed["subject3"]).strip()
    nested = COMPONENT_OF.match(subject)
    if nested:
        subject = nested["component"]
    if not _subject_matches(subject, subject_label, nouns):
        return None
    begin = listed.start(group)
    items = listed[group]
    end = CLAUSE_END.search(items)
    items = items[: end.start()] if end else items
    shares = []
    previous_end = 0
    for m in ITEM.finditer(items):
        qualifier = _qualifier(items, m.start(), previous_end)
        previous_end = m.end()
        if _key(m["name"]) != _key(component_label):
            continue
        before = flat[max(0, begin + m.start() - 40) : begin + m.start()].rstrip()
        cue = BOUND_CUE.search(before) or RANGE_BEFORE.search(before)
        printed = flat[begin + m.start() : begin + m.end()]
        if cue:
            printed = before[cue.start() :] + " " + printed
        elif qualifier:
            # No class names the qualifier: still a bound, held as qualified, never exact.
            printed = qualifier + " " + printed
        shares.append((float(m["value"]), bool(cue or qualifier), printed.strip(" .,;")))
    return shares


def _classify(quote, a, nouns=None):
    """How a quote reads this assertion's pair: LIST, FILLER or UNKNOWN when its wording
    states it for exactly this formulation, REJECT when it matches a pattern the
    formulation is not the subject of, None when no pattern reads it (a compound name)."""
    subject, component = a["subject"]["label"], a["component"]["label"]
    flat = _norm(quote)
    kinds = []
    if LIST.search(flat):
        shares = _list_shares(flat, subject, component, nouns)
        kinds.append("LIST" if shares else "REJECT")
    for m in FILLER_IN.finditer(flat):
        if _subject_matches(m["subject"], subject, nouns) and _key(component) in {
            _key(m["component"]),
            _key(m["host"]),
        }:
            kinds.append("FILLER")
        elif _key(component) in {_key(m["component"]), _key(m["host"])}:
            kinds.append("REJECT")
    for m in UNKNOWN.finditer(flat):
        if _key(m["component"]) == _key(component):
            ok = _subject_matches(m["subject"], subject, nouns)
            kinds.append("UNKNOWN" if ok else "REJECT")
    if WITH_FILLER.search(flat) and a["role"]:
        kinds.append("WITH_FILLER")
    for kind in ("LIST", "FILLER", "UNKNOWN", "WITH_FILLER"):
        if kind in kinds:
            return kind
    return "REJECT" if "REJECT" in kinds else None


def _pair_quote(assertion, nouns=None):
    """The sentence that prints the pair and whether its wording states it for exactly
    this formulation. (None, False) when only a sentence about something else matched."""
    quotes = [q["quote"] for q in assertion["evidence"]]
    kinds = [(q, _classify(q, assertion, nouns)) for q in quotes]
    role = bool(assertion["role"])
    good = ("FILLER", "WITH_FILLER") if role else ("LIST", "FILLER", "UNKNOWN")
    for q, kind in kinds:
        if kind in good:
            return q, True
    if any(kind == "REJECT" for _, kind in kinds) and not role:
        return None, False
    return quotes[0], False


def _share_quote(assertion, pair, nouns=None):
    """The sentence that prints the share, when it is not the pair's own."""
    proportion = assertion["proportion"] or {}
    for q in assertion["evidence"]:
        if q["quote"] == pair:
            continue
        if proportion.get("value") is not None:
            if _list_shares(
                q["quote"],
                assertion["subject"]["label"],
                assertion["component"]["label"],
                nouns,
            ):
                return q
        elif (
            proportion.get("status") == "NOT_KNOWN_PER_SOURCE"
            and _classify(q["quote"], assertion, nouns) == "UNKNOWN"
        ):
            return q
    return None


def _cited(quote, evidence, evidence_id):
    """The sentence carries a citation marker, or follows an author attribution."""
    if CITATION.search(quote):
        return True
    page = evidence.get(evidence_id) or {}
    text = page.get("text") or ""
    at = text.find(quote)
    return at > 0 and bool(re.search(r"\bet\s+al\.?\s*$", text[max(0, at - 25) : at]))


def _contrasted(sentence, label):
    """The constituent sits after a negation or contrast cue in its sentence."""
    sentence = UNKNOWN.sub(" ", sentence)
    cue = re.search(r"\b" + CONTRAST_CUES + r"\b", sentence, re.IGNORECASE)
    return bool(cue and _key(label) in _key(sentence[cue.end() :]))


def composition_records(assertions, entities_by_key, supported, evidence, locate, semantic=None):
    """One staged relation record per assertion whose two ends are validated entities."""
    by_id = {e["id"]: (key, e) for key, e in entities_by_key.items() if e.get("id")}
    nouns = class_nouns(semantic)
    records = []
    for a in assertions:
        subject, component = a["subject"], a["component"]
        if not (subject["entity_id"] in by_id and component["entity_id"] in by_id):
            continue
        if a.get("context") and not _entity(a["context"], supported):
            continue
        pair, direct = _pair_quote(a, nouns)
        if pair is None or _contrasted(pair, component["label"]):
            continue
        share = _share_quote(a, pair, nouns)
        # A negated share sentence gives no share (the pair stays, its proportion is unstated).
        if share and _contrasted(share["quote"], component["label"]):
            share = None
        try:
            pair_spans = locate([{"evidence_id": _evidence_of(a, pair), "quote": pair}], evidence)
            share_spans = (
                locate([{"evidence_id": share["evidence_id"], "quote": share["quote"]}], evidence)
                if share
                else []
            )
        except (ValueError, KeyError):
            continue
        subject_key, subject_entity = by_id[subject["entity_id"]]
        object_key, _ = by_id[component["entity_id"]]
        proportion = a["proportion"] or {}
        source = share["quote"] if share else pair
        shares = (
            _list_shares(source, subject["label"], component["label"], nouns)
            if proportion.get("value") is not None
            else None
        )
        held_bound = False
        if shares:
            value, bounded, printed_text = shares[0]
            if bounded:
                # A bound, approximation or range is a printed qualifier, never an exact value.
                printed = {
                    "status": "BOUND_OR_RANGE_REQUIRES_REVIEW",
                    "value": None,
                    "qualifier": printed_text,
                }
                held_bound = True
            else:
                printed = {"value": value, "unit": proportion["unit"], "status": "REPORTED"}
            basis = proportion.get("basis") or "UNSPECIFIED_IN_SOURCE"
        elif proportion.get("status") == "NOT_KNOWN_PER_SOURCE":
            printed = {"status": "NOT_KNOWN_PER_SOURCE", "value": None}
            basis = "UNSPECIFIED_IN_SOURCE"
        else:
            printed = {"status": "NOT_STATED_IN_SOURCE"}
            basis = "UNSPECIFIED_IN_SOURCE"
            share_spans = []
        study = subject_entity.get("study")
        reasons = ["UNREGISTERED_RELATION"]
        if not direct or held_bound:
            reasons.append("RELATION_ENTAILMENT_REQUIRES_REVIEW")
        sources = [(_evidence_of(a, pair), pair)]
        if share:
            sources.append((share["evidence_id"], share["quote"]))
        cited = any(_cited(quote, evidence, evidence_id) for evidence_id, quote in sources)
        if study != "current" or cited:
            reasons.append("CURRENT_OR_CITED_STUDY_UNRESOLVED")
        spans = [dict(s, role="pair") for s in pair_spans] + [
            dict(s, role="proportion") for s in share_spans
        ]
        records.append(
            {
                "id": "proposal-" + _identity("composition", a["id"]),
                "kind": "relations",
                "proposal": {
                    "relation": "hasComponent",
                    "subject": subject_key,
                    "object": object_key,
                    "support": [
                        {"evidence_id": s["evidence_id"], "quote": s["quote"], "start": s["start"]}
                        for s in pair_spans
                    ],
                },
                "subject": subject["entity_id"],
                "object": component["entity_id"],
                "support_spans": pair_spans,
                "status": "UNRESOLVED",
                "reasons": reasons,
                "candidate_origin": "COMPOSITION_READER",
                "composition": {
                    "formulation": subject["label"],
                    "constituent": component["label"],
                    "role": a["role"] or "NOT_STATED_IN_SOURCE",
                    "role_host": a["role_host"],
                    "proportion": printed,
                    "basis": basis,
                    "applicability": {"study": study, "context": a.get("context")},
                    "evidence": [
                        {k: s[k] for k in ("evidence_id", "start", "end", "quote", "role")}
                        for s in spans
                    ],
                    "assertion_id": a["id"],
                },
            }
        )
    return records


def link_projected_duplicates(projected, records):
    """A model relation between the same two entities on the same span: the supported one
    stays the active reading, otherwise the projected record is and the model's defers."""
    for new in projected:
        for old in records:
            if (
                old["kind"] != "relations"
                or (old.get("proposal") or {}).get("relation") != "hasComponent"
                or (old.get("subject"), old.get("object")) != (new["subject"], new["object"])
                or old.get("duplicate_of")
                or not any(
                    a["evidence_id"] == b["evidence_id"]
                    and a["start"] < b["end"]
                    and b["start"] < a["end"]
                    for a in old["support_spans"]
                    for b in new["support_spans"]
                )
            ):
                continue
            if old["status"] == "SOURCE_SUPPORTED":
                new["duplicate_of"] = old["id"]
            else:
                old["duplicate_of"] = new["id"]


def _evidence_of(assertion, quote):
    return next(q["evidence_id"] for q in assertion["evidence"] if q["quote"] == quote)


def ontology_extension_proposals(assertions, semantic_relations):
    """The vocabulary the staged assertions would need, for ontology review."""
    if not assertions or "hasComponent" in semantic_relations:
        return []
    return [
        {
            "id": "relation-proposal-hasComponent",
            "kind": "relation",
            "term": "hasComponent",
            "domain": "Material",
            "range": "Material",
            "definition": "The subject material contains the object material as a constituent, as the source states.",
            "assertion_characteristics": {
                "role": "The component's documented function in this material (e.g. filler); a characteristic of one assertion, not a global property.",
                "proportion": "The documented share of the component, with its documented basis (mass, volume, molar) or UNSPECIFIED_IN_SOURCE.",
                "context": "The material in which a nested component is described (the bronze of one formulation).",
            },
            "approved_relations_examined": sorted(semantic_relations),
            "why_existing_relations_do_not_fit": "madeOf relates a sample, run or experiment family to its material; no approved relation links a material to its constituents.",
            "supporting_assertions": [a["id"] for a in assertions],
            "activation": "NONE",
            "status": "STAGED_FOR_ONTOLOGY_REVIEW",
        }
    ]


def _number(value):
    return f"{value:g}"


def explain(assertion):
    """Natural-language sentences rendered only from one structured assertion."""
    subject = assertion["subject"]["label"]
    component = assertion["component"]["label"]
    where = f" (as used in {assertion['context']})" if assertion.get("context") else ""
    lines = []
    if assertion.get("source_descriptor"):
        lines.append(f"The source describes {subject} as a {assertion['source_descriptor']}.")
    lines.append(f"{subject}{where} contains {component} as a component.")
    if assertion.get("role"):
        host = assertion.get("role_host")
        lines.append(
            f"{component} acts as the {assertion['role']} of {subject}"
            + (f", in {host['label']}" if host and host["label"] != subject else "")
            + "."
        )
    proportion = assertion.get("proportion")
    if proportion and proportion["status"] == "REPORTED":
        basis = {
            "MASS": "by mass",
            "VOLUME": "by volume",
            "MOLAR": "on a molar basis",
        }.get(proportion["basis"], "on a basis the source does not state")
        lines.append(
            f"The reported share of {component} in {subject}{where} is {_number(proportion['value'])}% {basis}."
        )
    elif proportion and proportion["status"] == "NOT_KNOWN_PER_SOURCE":
        lines.append(f"The source states that the share of {component} in {subject} is not known.")
    pages = sorted({e["page"] for e in assertion["evidence"] if e.get("page") is not None})
    lines.append(
        f"Status: {assertion['lifecycle']}; relation hasComponent is a staged proposal, not approved vocabulary"
        + (f"; source page {', '.join(str(p) for p in pages)}." if pages else ".")
    )
    return lines
