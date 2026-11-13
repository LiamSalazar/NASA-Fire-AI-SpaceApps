"""Whether a value's own sentence prints the subject the model proposed for it.

The validator holds a value whose proposed subject its passage does not name. Some
passages do name it, in a form the plain label match misses. This module recognizes
those forms by document structure only, and only ever *accepts* the subject that was
proposed: it never chooses, substitutes or broadens a subject, and it never falls back
to the investigation. Another class, zero or several candidates in the sentence, or a
plain co-occurrence leave the value held.

Forms (each returns a basis that is recorded on the value):

- ``SUBJECT_NAME_SPLIT_BY_LAYOUT``: the name is printed whole only once a hyphenated line
  break, or a page-number line inside it, is rejoined.
- ``SUBJECT_PRINTED_AS_QUALIFIED_NAME``: "Base (Qualifier)" printed as the base name and
  its qualifier in the same sentence, the qualifier nearest the value being this one's.
- ``SUBJECT_PRINTED_AS_SHORT_FORM``: a code-like final token of the name (with a digit or
  in capitals) that names no other entity.
"""

import os
import re

from nasa_fire_ai.ingestion.abbreviations import segmentation_view, split_by_view
from nasa_fire_ai.ingestion.clause_cues import locate_value
from nasa_fire_ai.ingestion.printed_layout import (
    _page_texts,
    document_conclusion_scope,
    governing_major,
    group_section_support,
    heading_level,
    heading_scheme,
    heading_title,
    layout_heading,
    line_units,
    page_headings,
    reads_as_sentence,
    section_for_span,
    slide_deck,
)
from nasa_fire_ai.ingestion.scientific_scope import original_research_passage
from nasa_fire_ai.ingestion.source_spans import mentions, normalized

SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"“])")
# The classes a value's subject can be when it is recognized here.
SUBJECT_CLASSES = frozenset({"Material", "Sample", "ExperimentalRun", "ExperimentFamily"})


def rejoin_layout(text):
    """Text with a page-number line inside a hyphenated word removed and hyphenated
    line breaks rejoined; other line breaks become spaces."""
    text = re.sub(r"-[ \t]*\n[ \t]*\d{1,4}[ \t]*\n[ \t]*", "-", text or "")
    text = re.sub(r"-[ \t]*\n[ \t]*(?=[a-z])", "-", text)
    return re.sub(r"\s+", " ", text)


def _sentence(window, quote, repair):
    joined = rejoin_layout(window) if repair else re.sub(r"\s+", " ", window)
    pieces = split_by_view(SENTENCE_END, joined)
    head = (rejoin_layout(quote) if repair else re.sub(r"\s+", " ", quote))[:40]
    for i in range(len(pieces) - 1, -1, -1):
        if head and head in " ".join(pieces[i:]):
            return " ".join(pieces[i:]).strip()
    return pieces[-1].strip()


def value_sentence(span, page_text, headings=()):
    """(as printed, layout rejoined): the sentence that ends with the span, from the
    last sentence end or section heading before it."""
    start, end = span["start"], span["end"]
    begin = max([0, *[h for h in headings if h <= start]])
    window = page_text[max(begin, start - 600) : end]
    quote = span.get("quote") or ""
    return _sentence(window, quote, False), _sentence(window, quote, True)


def _words(text):
    return re.findall(r"[\w®™#.-]+", (text or "").lower())


def _printed(phrase, text):
    return bool(
        re.search(r"(?<![\w-])" + re.escape(phrase.lower()) + r"(?![\w-])", (text or "").lower())
    )


QUALIFIED = re.compile(r"^(?P<base>.+?)\s*\((?P<qualifier>[^()]+)\)\s*$")


def _qualifier_forms(qualifier):
    """A qualifier as printed, and without its number sign ("Run #3" → "run 3")."""
    q = qualifier.strip().lower()
    plain = re.sub(r"\s*(?:#|no\.?)\s*", " ", q).strip()
    return list(dict.fromkeys([q, plain]))


def _positions(forms, text):
    return [
        m.start()
        for form in forms
        for m in re.finditer(r"(?<![\w-])" + re.escape(form) + r"(?![\w-])", text.lower())
    ]


def recognize_printed_subject(subject, entities, sentences, expression=None):
    """The basis on which the value's sentence prints entity ``subject``, or None.

    ``sentences`` is (as printed, layout rejoined)."""
    raw, joined = sentences
    entity = entities.get(subject) or {}
    label = (entity.get("label") or "").strip()
    if not label or not joined or entity.get("class_id") not in SUBJECT_CLASSES:
        return None
    others = [e for key, e in entities.items() if key != subject and e.get("label")]
    qualified = QUALIFIED.match(label)
    base = qualified["base"].strip().lower() if qualified else None
    # Any other subject-class entity printed in the sentence (other than a sibling
    # of the same qualified base, decided below by its qualifier) leaves it held.
    rivals = [
        o
        for o in others
        if o.get("class_id") in SUBJECT_CLASSES
        and _printed(o["label"], joined)
        # A substance printed only as the test's medium ("in a X environment") is
        # not a rival subject.
        and not test_medium_only(o["label"], [{"quote": joined}])
        and not label.lower().startswith(o["label"].strip().lower())
        and not (base and o["label"].strip().lower().startswith(base))
    ]
    if rivals:
        return None
    if _printed(label, joined) and not _printed(label, raw):
        return "SUBJECT_NAME_SPLIT_BY_LAYOUT"
    if qualified and _printed(qualified["base"], joined):
        offset = locate_value(joined, expression) if expression else None
        own = _positions(_qualifier_forms(qualified["qualifier"]), joined)
        siblings = []
        for other in others:
            match = QUALIFIED.match(other["label"].strip())
            if match and match["base"].strip().lower() == base:
                siblings += _positions(_qualifier_forms(match["qualifier"]), joined)
        if own and offset is not None:
            nearest = min(abs(p - offset) for p in own)
            if not siblings or nearest < min(abs(p - offset) for p in siblings):
                return "SUBJECT_PRINTED_AS_QUALIFIED_NAME"
        elif own and not siblings:
            return "SUBJECT_PRINTED_AS_QUALIFIED_NAME"
    tokens = label.split()
    if len(tokens) > 1 and not _printed(label, joined):
        last = tokens[-1].strip(",.;:")
        code_like = re.search(r"\d", last) or (last.isupper() and len(last) >= 2)
        if (
            code_like
            and _printed(last, joined)
            and not any(last.lower() in _words(o["label"]) for o in others)
        ):
            return "SUBJECT_PRINTED_AS_SHORT_FORM"
    return None


def binding_clauses(quote):
    """The clauses of a quote, one statement each, shared by the binding rules."""
    # Lines of a slide or caption list are separate statements: a line break
    # before a capitalized or bulleted line ends the unit unless the previous
    # line visibly continues ("... compared with" / "Brass-").
    return split_by_view(
        r";|\n\s*\n|(?<!\b[A-Z])[.!?](?!\d)(?=\s|$)|,?\s+\b(?:whereas|while|but)\b"
        # "a 3.1 cm ID ... glass channel where coupons were burned": a
        # relative clause names another thing than the value's noun phrase.
        r"|(?:\([^()]*\))?\s+\b(?:where|wherein|in\s+which|into\s+which|on\s+which)\b",
        line_units(quote),
    )


def printed_rival_text(clause, printed_clauses):
    """The text a rival subject is searched in: the clause of the printed line(s) that holds
    ``clause`` (the whole line(s) when none does); ``clause`` itself without a printed line."""
    if not printed_clauses:
        return clause
    key = normalized(clause)
    for wide in printed_clauses:
        if key in normalized(wide):
            return wide
    return " ".join(printed_clauses)


def local_binding(subject, value, spans, entities, printed=None):
    """A multi-subject span cannot transfer a result between its subjects.

    ``printed`` (SCIENCE_EVIDENCE_VETO_QUANTITIES) is the printed line(s) of each span, in
    order (``None`` for one not located): the binding is still required in the quote's clause,
    but a competing subject is searched in the clause of the printed line(s) that holds it."""
    label = entities[subject]["label"]
    for index, span in enumerate(spans):
        line = printed[index] if printed and index < len(printed) else None
        wide = binding_clauses(line["quote"]) if line else None
        for clause in binding_clauses(span["quote"]):
            if mentions(label, clause) and mentions(value, clause):
                rival_text = printed_rival_text(clause, wide)
                competing = [
                    e
                    for k, e in entities.items()
                    if k != subject
                    and e["id"] != entities[subject]["id"]
                    and normalized(e["label"]) != normalized(label)
                    and e["class_id"] == entities[subject]["class_id"]
                    and mentions(e["label"], rival_text)
                ]
                embedded_specimen_attribute = (
                    entities[subject]["class_id"] == "Sample"
                    and mentions(value, label)
                    and not any(mentions(value, e["label"]) for e in competing)
                )
                if not competing or embedded_specimen_attribute:
                    return True
    return False


def label_binding_enabled():
    return os.getenv("SCIENCE_LABEL_BINDING", "0") == "1"


def printed_label_binding(subject, expression, unit, spans, entities):
    """SCIENCE_LABEL_BINDING: the value is printed inside the subject's own label.

    For any entity class: a clause prints the subject's label, the value
    (expression with its unit) is printed inside that label as a single value
    (no other number with that unit, no list or range member), it is printed
    nowhere else in any clause of any span, and inside no other entity's label
    the clause prints. The value's own expression and unit stay its fields; the
    label is never rewritten. A value is never handed from one named subject to
    another. It overlaps local_binding's Sample-only embedded_specimen_attribute;
    the two are to be unified later.
    """
    entity = entities.get(subject) or {}
    if entity.get("validation_status") != "SOURCE_SUPPORTED" or not (unit or "").strip():
        return None
    label = entity["label"]
    forms = [f"{expression} {unit}", f"{expression}{unit}"]
    if not any(mentions(form, label) for form in forms):
        return None
    text = normalized(label)
    number = r"(?<![\w.,-])\d[\d.,]*\s*" + re.escape(normalized(unit)) + r"(?![\w-])"
    if len(re.findall(number, text)) != 1:
        return None
    for form in forms:
        for hit in re.finditer(r"(?<![\w-])" + re.escape(normalized(form)) + r"(?![\w-])", text):
            if re.search(r"\d\s*(?:,|/|&|-|–|—|and|or|to)\s*$", text[: hit.start()]):
                return None
    others = [
        e
        for key, e in entities.items()
        if key != subject
        and e.get("id") != entity.get("id")
        and normalized(e["label"]) != normalized(label)
    ]
    found = None
    for span in spans:
        for clause in binding_clauses(span["quote"]):
            printed = mentions(label, clause)
            if printed and any(
                mentions(e["label"], clause) and any(mentions(f, e["label"]) for f in forms)
                for e in others
            ):
                return None
            rest = re.sub(r"(?<![\w-])" + re.escape(text) + r"(?![\w-])", " ", normalized(clause))
            if (printed and mentions(expression, rest)) or any(mentions(f, rest) for f in forms):
                return None
            if printed and found is None:
                found = {
                    "basis": "VALUE_PRINTED_INSIDE_SUBJECT_LABEL",
                    "label": label,
                    "expression": expression,
                    "unit": unit,
                    "clause": clause.strip(),
                }
    return found


def heading_names_subject(subject, spans, entities, document, printed=None):
    """The base rule (heading_rule_accepts), vetoed by SCIENCE_HEADING_SUBJECT_V3."""
    accepted = heading_rule_accepts(subject, spans, entities, document, printed)
    if (
        accepted
        and heading_subject_v3_enabled()
        and heading_subject_conflict(subject, spans, entities, document)
    ):
        return None
    return accepted


def heading_rule_accepts(subject, spans, entities, document, printed=None):
    """The governing heading names the proposed subject, and nothing else competes.

    Accepted only for the proposed subject (never a substitute), never the
    investigation: a validated subject entity that the one heading governing every
    span names, while no other validated entity is named in that heading or in the
    spans' own text. ``printed`` (SCIENCE_EVIDENCE_VETO_QUANTITIES) adds the printed line(s) of
    the spans to that text.
    """
    entity = entities.get(subject) or {}
    if (
        entity.get("class_id") not in SUBJECT_CLASSES
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
    ):
        return None
    headings = {section_for_span(s, document) for s in spans} - {"", "UNSPECIFIED"}
    if len(headings) != 1:
        return None
    (heading,) = headings
    forms = subject_forms(entity)
    if not any(mentions(form, heading) for form in forms):
        return None
    passage = " ".join(s.get("quote") or "" for s in [*spans, *(p for p in printed or () if p)])
    if any(
        key != subject
        and other.get("validation_status") == "SOURCE_SUPPORTED"
        and other.get("class_id") != "Investigation"
        and (mentions(other["label"], heading) or mentions(other["label"], passage))
        for key, other in entities.items()
    ):
        return None
    return {"basis": "GOVERNING_HEADING_NAMES_PROPOSED_SUBJECT", "heading": heading}


def heading_subject_v3_enabled():
    # On by default after its replay passed; SCIENCE_HEADING_SUBJECT_V3=0 turns it off.
    return os.getenv("SCIENCE_HEADING_SUBJECT_V3", "1") == "1"


HEADING_SUBJECT_CONFLICT = "HEADING_SUBJECT_CONFLICT"


def heading_subject_conflict(subject, spans, entities, document):
    """SCIENCE_HEADING_SUBJECT_V3: the subsection heading that names another entity.

    Between the governing major heading and a span, the nearest open subsection
    heading (a printed heading line below the major level: never a list lead, an
    inline label, a caption or a numbered list item) that names a validated entity
    governs. When it names one other than the proposed subject, its title is
    returned and the record is held; the other entity is never substituted. A
    subsection that names no entity is transparent. Slide decks are out of scope.
    """
    entity = entities.get(subject) or {}
    if not entity or slide_deck(document):
        return None
    others = [
        e
        for key, e in entities.items()
        if key != subject
        and e.get("id") != entity.get("id")
        and normalized(e["label"]) != normalized(entity["label"])
        and e.get("validation_status") == "SOURCE_SUPPORTED"
        and e.get("class_id") != "Investigation"
    ]
    if not others:
        return None
    order = {
        ev: i for i, ev in enumerate(dict.fromkeys(s["evidence_id"] for s in document["segments"]))
    }
    for span in spans:
        major = governing_major(span, document)
        if major is None or span["evidence_id"] not in order:
            continue
        low = (order[major["evidence_id"]], major["start"])
        high = (order[span["evidence_id"]], span["start"])
        between = sorted(
            (
                h
                for ev in order
                for h in page_headings(ev, document)
                if h.get("source_id") == span.get("source_id")
                and low < (order[ev], h["start"]) < high
                # Level 1 between a major and its span is an enumerated item.
                and heading_level(h, document) > 1
                and not reads_as_sentence(h["title"])
            ),
            key=lambda h: (order[h["evidence_id"]], h["start"]),
            reverse=True,
        )
        floor = None
        for h in between:
            level, scheme = heading_level(h, document), heading_scheme(h, document)
            if floor is not None and floor[0] == scheme and level >= floor[1]:
                continue  # a closed sibling
            floor = (scheme, level)
            title = v2_title(h["title"])
            if any(names_entity(e, title) for e in others):
                return h["title"]
            if names_entity(entity, title):
                break
    return None


def subject_forms(entity):
    """The label, and the short form a label defines with an acronym ("Xy Zz (XZ) 4")."""
    forms = [entity["label"]]
    defined = re.match(r"(?:[\w-]+\s+)+\(([A-Z][A-Z0-9-]{1,9})\)\s*([^,]*)", entity["label"])
    if defined:
        forms.append(" ".join(part for part in defined.groups() if part.strip()))
    return forms


def names_entity(entity, text):
    """Whether a form of the entity is printed in the text, not as the prefix of "X 2.1"."""
    return any(
        re.search(
            r"(?<![\w-])" + re.escape(normalized(form)) + r"(?![\w-])(?!\.\d)", normalized(text)
        )
        for form in subject_forms(entity)
    )


def v2_title(printed):
    """A heading without its numbering, including an outline number with no trailing dot."""
    return heading_title(re.sub(r"^\d+(?:\.\d+)+\s+", "", printed.strip()))


def applicable(subject, spans, entities, document):
    """Require an independently readable subject anchor, not merely a valid ID.

    An explicit universal experimental methods clause may carry context across
    sections; a title or a gravity keyword alone cannot.
    """
    entity = entities.get(subject)
    if (
        not entity
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
        or any(s["source_id"] != entity["source_id"] for s in spans)
    ):
        return False
    if (
        entity["class_id"] == "Sample"
        and not re.fullmatch(r"[A-Za-z]+\d+(?:[-_.]\w+)*", entity["label"])
        and not any(
            s["evidence_id"] == anchor["evidence_id"] for s in spans for anchor in entity["spans"]
        )
    ):
        # Identical material/specimen names in comparison sections do not identify
        # one physical specimen. Cross-section correspondence requires review.
        return False
    if entity["class_id"] == "Sample":
        peers = [
            e
            for key, e in entities.items()
            if key != subject
            and e["class_id"] == "Sample"
            and normalized(e["label"]) == normalized(entity["label"])
            and e["source_id"] == entity["source_id"]
        ]

        def overlaps(anchors):
            return any(
                a["evidence_id"] == s["evidence_id"]
                and a["start"] < s["end"]
                and a["end"] > s["start"]
                for a in anchors
                for s in spans
            )

        if peers and (not overlaps(entity["spans"]) or any(overlaps(e["spans"]) for e in peers)):
            return False
    from nasa_fire_ai.ingestion.table_continuity import printed_label_forms

    # A row group label may be printed with its legend-backed footnote marker.
    if any(
        mentions(form, s["quote"])
        for form in printed_label_forms(entity["label"], document)
        for s in spans
    ):
        return True
    if group_section_support(subject, spans, entities, document) or document_conclusion_scope(
        subject, spans, entities, document
    ):
        return True
    from nasa_fire_ai.ingestion.scientific_scope import figure_group_support

    if figure_group_support(subject, spans, entities, document):
        return True
    if entity["class_id"] == "ExperimentFamily":
        for span in spans:
            heading = layout_heading(span, document)
            if (
                heading
                and normalized(heading["quote"]) == normalized(entity["label"])
                and not any(
                    e["class_id"] == "ExperimentFamily"
                    and normalized(e["label"]) != normalized(entity["label"])
                    and mentions(e["label"], span["quote"])
                    for e in entities.values()
                )
            ):
                return True
    if entity["class_id"] not in {"Investigation", "ExperimentFamily"}:
        return False
    if (
        entity["class_id"] == "Investigation"
        and entity["study"] == "current"
        and any(
            re.search(r"conclusions?", section_for_span(s, document), re.IGNORECASE) for s in spans
        )
        and any(
            re.search(r"\b(?:conducted|performed|as\s+part\s+of)\b", s["quote"], re.IGNORECASE)
            for s in entity.get("spans", [])
        )
    ):
        return True
    for anchor in document["context_anchors"]:
        if anchor["source_id"] != spans[0]["source_id"]:
            continue
        if mentions(entity["label"], anchor["quote"]) and re.search(
            r"\b(?:all\s+(?:tests|experiments)|experiments?\s+(?:were|was)\s+(?:performed|conducted))\b",
            anchor["quote"],
            re.IGNORECASE,
        ):
            return True
    return False


def printed_subject_recognition(item, spans, entities, document):
    """The basis on which the sentence that prints a value names its proposed subject
    in a form the label match misses, or None (``subject_recognition``)."""
    from nasa_fire_ai.ingestion.subject_recognition import (
        recognize_printed_subject,
        value_sentence,
    )

    texts = _page_texts(document)
    pages = list(dict.fromkeys(s["evidence_id"] for s in document.get("segments", [])))
    for span in spans:
        text = texts.get(span["evidence_id"])
        if not text or span.get("start") is None:
            continue
        headings = [
            h["start"]
            for h in document.get("sections", [])
            if h.get("evidence_id") == span["evidence_id"]
        ]
        if (
            not headings
            and not re.search(r"[.!?]\s", segmentation_view(text)[: span["start"]])
            and span["evidence_id"] in pages
            and pages.index(span["evidence_id"]) > 0
        ):
            # The sentence began on the previous page: prepend that page's last,
            # unfinished sentence.
            previous = texts.get(pages[pages.index(span["evidence_id"]) - 1], "")
            tail = split_by_view(r"(?<=[.!?])\s+", previous.rstrip())[-1]
            if not re.search(r"[.!?]$", segmentation_view(tail.strip())):
                shift = len(tail) + 1
                text = tail + "\n" + text
                span = {**span, "start": span["start"] + shift, "end": span["end"] + shift}
        sentence = value_sentence(span, text, headings)
        basis = recognize_printed_subject(
            item["subject"], entities, sentence, item.get("expression")
        )
        if basis:
            return basis
    return None


def resolve_explicit_scopes(output, document):
    """Resolve only explicit names or a documented current-study conclusion scope.

    Conclusions scope to the identified investigation, never to every run. Prior
    studies and ambiguous/multiple current investigations remain unresolved.
    """
    experiments = [
        e
        for e in output["entities"]
        if e["class_id"] in {"Investigation", "ExperimentalRun", "ExperimentFamily"}
    ]
    current = {
        e["key"]: e
        for e in experiments
        if e["class_id"] == "Investigation"
        and e["study"] == "current"
        and any(
            re.search(r"\b(?:conducted|performed|as\s+part\s+of)\b", s["quote"], re.IGNORECASE)
            for s in e["support"]
        )
    }
    for statement in output["statements"]:
        if statement["subjects"]:
            continue
        named = {
            e["key"]: e
            for e in experiments
            if mentions(e["label"], statement["text"]) and e["study"] != "unknown"
        }
        if len(named) == 1:
            item = next(iter(named.values()))
            statement["subjects"] = [item["key"]]
            statement["study"] = item["study"]
        elif (
            len(current) == 1
            and statement["epistemic"]
            in {"author_reported_conclusion", "tentative_interpretation", "hypothesis"}
            and not re.search(
                r"\b(?:prior|previous|earlier)\b|\[\d", statement["text"], re.IGNORECASE
            )
        ):
            span = statement["support"][0]
            if span.get("start") is not None and re.search(
                r"conclusions?", section_for_span(span, document), re.IGNORECASE
            ):
                statement["subjects"] = list(current)
                statement["study"] = "current"
        if (
            not statement["subjects"]
            and statement["study"] != "cited"
            and statement["epistemic"]
            in {
                "author_reported_conclusion",
                "tentative_interpretation",
                "hypothesis",
            }
        ):
            roots = [
                e
                for e in experiments
                if e["class_id"] == "Investigation"
                and e["study"] == "current"
                and normalized(e["label"]) == normalized(document.get("package_title", ""))
            ]
            if len(roots) == 1 and not re.search(
                r"\b(?:prior|previous|earlier|reported\s+by)\b|\[\d",
                statement["text"],
                re.IGNORECASE,
            ):
                span = statement["support"][0]
                if re.search(r"conclusions?", section_for_span(span, document), re.IGNORECASE):
                    statement["subjects"] = [roots[0]["key"]]
                    statement["study"] = "current"
        if (
            not statement["subjects"]
            and statement["study"] != "cited"
            and original_research_passage(statement["support"], document)
        ):
            roots = [
                e
                for e in experiments
                if e["class_id"] == "Investigation"
                and e["study"] == "current"
                and normalized(e["label"]) == normalized(document.get("package_title", ""))
            ]
            text = statement["text"]
            if len(roots) == 1 and not any(
                e["study"] == "cited" and mentions(e["label"], text) for e in experiments
            ):
                statement["subjects"] = [roots[0]["key"]]
                statement["study"] = "current"


IDENTITY_BASES = (
    "Investigation",
    "ExperimentFamily",
    "ExperimentalRun",
    "Sample",
    "Material",
    "ExperimentalCondition",
    "GravityCondition",
    "Intervention",
    "CombustionPhenomenon",
)


def identity_classes(semantic):
    """The approved classes the identity stage chooses an entity's class among."""
    return sorted(
        c
        for c in semantic.class_metadata
        if any(has_class(c, base, semantic) for base in IDENTITY_BASES)
    )


def has_class(class_id, expected, semantic):
    from nasa_fire_ai.ingestion.semantic import class_ancestors

    return expected in class_ancestors(class_id, semantic.class_metadata)


def tested_material_entity(entity, document):
    """A current, source-supported material this document shows tested here."""
    return (
        entity["class_id"] == "Material"
        and entity.get("study") == "current"
        and entity.get("validation_status") == "SOURCE_SUPPORTED"
        and material_tested_here(entity["label"], document)
    )


MEDIUM_BEFORE = re.compile(
    r"\b(?:pressuri[sz]ed|purged|flushed|cooled|chilled|submerged|immersed"
    r"|bathed|operated)\b(?:\s+[\w-]+){0,6}?\s+(?:with|in|by)\s+(?:a\s+|an\s+|the\s+)?$",
    re.IGNORECASE,
)
MEDIUM_AFTER = re.compile(
    r"^(?:\s+or\s+[\w/-]+)?\s+(?:environments?|atmospheres?|modes?|baths?|media|medium)\b",
    re.IGNORECASE,
)


def test_medium_only(label, spans):
    """Whether every support passage names the substance only as the test's medium."""
    pattern = re.compile(rf"(?<![\w-]){re.escape(label)}(?![\w-])", re.IGNORECASE)
    found = False
    for span in spans:
        quote = re.sub(r"\s+", " ", span.get("quote", ""))
        for match in pattern.finditer(quote):
            found = True
            before = re.sub(r"\b\w+\s+or\s+$", "", quote[: match.start()])
            if not (MEDIUM_BEFORE.search(before) or MEDIUM_AFTER.match(quote[match.end() :])):
                return False
    return found


def material_tested_here(label, document):
    """Whether this document prints table rows for the material and none is cited."""
    from nasa_fire_ai.ingestion.table_continuity import group_lineage, material_row_labels

    lineage = group_lineage(material_row_labels(label, document), document)
    return bool(lineage and lineage["status"] == "NOT_CONTRADICTED")


def quantity_scope_eligible(entity, semantic):
    if entity["class_id"] in {"Investigation", "ExperimentFamily", "ExperimentalRun", "Sample"}:
        return True
    return (
        has_class(entity["class_id"], "ExperimentalCondition", semantic)
        and not has_class(entity["class_id"], "GravityCondition", semantic)
        and getattr(semantic, "entity_mentions", {}).get(entity["id"], {}).get("relation")
        != "hasGravityCondition"
    )
