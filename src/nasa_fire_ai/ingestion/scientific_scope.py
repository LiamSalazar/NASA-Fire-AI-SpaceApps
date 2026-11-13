"""Original logical sections and documentary scope certificates, never global aliases."""

import re
from itertools import pairwise

from nasa_fire_ai.ingestion.abbreviations import split_by_view
from nasa_fire_ai.ingestion.document_memo import document_memo
from nasa_fire_ai.ingestion.printed_layout import (
    _page_texts,
    referenced_captions,
    section_for_span,
    slide_deck,
)
from nasa_fire_ai.ingestion.scientific_facets import (
    PLAN_GOAL_ROLES,
    canonical_modality,
    plan_goal_facets_enabled,
    stated_modality,
)
from nasa_fire_ai.ingestion.source_spans import mentions, normalized, normalized_text, recover_span
from nasa_fire_ai.ingestion.study_attribution import cited_mention_outside_current_names


def norm(text):
    return normalized_text(text).lower().strip()


def contains(label, text):
    return bool(re.search(r"(?<![\w-])" + re.escape(norm(label)) + r"(?![\w-])", norm(text)))


STANDARD_SECTION = re.compile(
    r"^(?:abstract|introduction|background|nomenclature|experimental(?:\s+(?:description|setup|methods?|procedures?|approach))?|methods?|test\s+(?:configuration|objectives|results|methods?|procedure)|testing|results(?:\s+and\s+discussion)?|discussion|conclusions?|summary(?:\s+and\s+conclusions)?|references|acknowledg\w*)$",
    re.IGNORECASE,
)
ROMAN = re.compile(r"^[IVX]+[.)]\s+", re.IGNORECASE)


def logical_section(span, document):
    """A prominent title or numbered list does not override its parent section."""
    order, sources, majors = document_memo(
        document, "major_sections", lambda: major_sections(document)
    )
    if span["evidence_id"] not in sources:
        return "UNSPECIFIED"
    candidates = [
        h
        for h in majors[sources[span["evidence_id"]]]
        if (order[h["evidence_id"]], h["start"]) <= (order[span["evidence_id"]], span["start"])
    ]
    if candidates:
        return max(candidates, key=lambda h: (order[h["evidence_id"]], h["start"]))["title"]
    return "UNSPECIFIED"


def major_sections(document):
    """Page order, each page's source, and each source's major section headings."""
    order = {
        key: i
        for i, key in enumerate(dict.fromkeys(s["evidence_id"] for s in document["segments"]))
    }
    sources = {}
    for s in document["segments"]:
        sources.setdefault(s["evidence_id"], s["source_id"])
    return order, sources, {sid: source_majors(sid, document) for sid in set(sources.values())}


def source_majors(sid, document):
    headings = [h for h in document["sections"] if h.get("source_id") == sid]
    roman_mode = any(
        re.match(
            r"^(?:I[.)]\s+(?:Introduction|Background|Methods)|[IVX]{2,}[.)]\s+)",
            h["title"],
            re.IGNORECASE,
        )
        for h in headings
    )
    majors = []
    for h in headings:
        # Strip only an outline number ("3", "2.1.") or a punctuated letter/roman
        # numeral ("A.", "IV)"); an unpunctuated first word ("Results") is the title.
        body = re.sub(
            r"^(?:#+\s*|\d+(?:\.\d+)*[.)]?\s+|[A-Z][.)]\s+|[IVXLCDM]+[.)]\s+)",
            "",
            h["title"],
            flags=re.IGNORECASE,
        ).strip()
        if norm(body) == norm(document.get("package_title", "")):
            continue
        # A major heading printed alone on its line may be followed directly by
        # its first subsection title ("Experimental" then "Test Apparatus").
        first_line = body.split("\n", 1)[0].strip()
        standard = bool(STANDARD_SECTION.fullmatch(body) or STANDARD_SECTION.fullmatch(first_line))
        # In a Roman-numbered paper an unnumbered standard heading ("Experimental
        # Method" between "II." and "III.") is still a major section.
        major = (bool(ROMAN.match(h["title"])) or standard) if roman_mode else standard
        if re.fullmatch(r"references|acknowledg\w*|abstract|nomenclature", body, re.IGNORECASE):
            major = True
        if major:
            majors.append(h)
    return majors


def figure_group_support(subject, spans, entities, document):
    entity = entities.get(subject, {})
    if (
        entity.get("class_id") != "ExperimentFamily"
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
    ):
        return []
    if not re.search(
        r"\b(?:tests?|series|results?|comparison|experiments?|groups?)\b",
        entity["label"],
        re.IGNORECASE,
    ):
        return []
    proof = []
    for span in spans:
        if span["source_id"] != entity["source_id"]:
            return []
        if any(
            e.get("class_id") in {"ExperimentFamily", "ExperimentalRun"}
            and e.get("validation_status") == "SOURCE_SUPPORTED"
            and e.get("id") != entity.get("id")
            and contains(e["label"], span["quote"])
            for e in entities.values()
        ):
            return []
        referenced = referenced_captions(span, document)
        if not referenced:
            return []
        for captions in referenced.values():
            if len(captions) != 1:
                return []
            f = captions[0]
            # The name must start in the actual caption's first line, not in
            # neighboring prose accidentally included by layout extraction.
            first = f["quote"][: f["first_line_end"] - f["start"]]
            first_word = entity["label"].split()[0]
            if not contains(entity["label"], f["quote"]) or not contains(first_word, first):
                return []
            if re.search(
                r"\[\d|\b(?:reproduced|adapted|prior|previous)\b", f["quote"], re.IGNORECASE
            ):
                return []
            if any(
                e.get("class_id") == "ExperimentFamily"
                and e.get("validation_status") == "SOURCE_SUPPORTED"
                and e.get("id") != entity.get("id")
                and contains(e["label"], f["quote"])
                for e in entities.values()
            ):
                return []
            proof.append(
                {"evidence_id": f["evidence_id"], "quote": f["quote"], "start": f["start"]}
            )
    return list({(p["evidence_id"], p["start"]): p for p in proof}.values())


# A clause that makes what follows the object of a procedure or a time reference:
# "before re-attaching the valve", "after removing the cap", "while the unit ...".
PROCEDURAL_OR_TEMPORAL_LEAD = re.compile(
    r"\b(?:prior\s+to|before|after|until|while|during|upon|once|when|without|following)\b"
    r"|\b[a-z][a-z-]*ing\s+(?:the\s+|a\s+|an\s+)?(?:\w+\s+){0,2}$",
    re.IGNORECASE,
)


def acronym_names_local_subject(alias, quote):
    """Whether a sentence speaks about the item an acronym names (mandate decision 2).

    The acronym must be printed outside a procedural or temporal clause of its own
    sentence: "The XYZ outlet pressure stayed at 120 psia" speaks about the XYZ;
    "times were logged before re-attaching the XYZ" does not. Conservative: an
    acronym that only appears inside such a clause names nothing here.
    """
    for match in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z])", quote):
        clause = re.split(r"[.;:,]", quote[: match.start()])[-1]
        if not PROCEDURAL_OR_TEMPORAL_LEAD.search(clause):
            return True
    return False


def sentence_with(text, needle):
    """The printed sentence of ``text`` that contains ``needle``, or None."""
    for sentence in split_by_view(r"(?<=[.!?])\s+", text):
        if needle and needle in sentence:
            return sentence
    return None


def test_article_alias_review(subject, spans, entities, document):
    """Preserve a unique source-defined test-article acronym for REVIEW only."""
    entity = entities.get(subject, {})
    if (
        entity.get("class_id") != "Sample"
        or entity.get("study") != "current"
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
    ):
        return None
    literal = norm(entity["label"])
    identity = [
        s
        for s in entity.get("support", [])
        if re.search(
            r"(?:tested\s+(?:was|were)|test\s+article\s+(?:was|is))\s+(?:the\s+)?"
            + re.escape(literal),
            norm(s["quote"]),
        )
    ]
    if not identity:
        return None
    for alias in re.findall(r"\(([A-Z][A-Z0-9-]{1,9})\)", entity["label"]):
        if any(
            e.get("id") != entity.get("id")
            and e.get("class_id") == "Sample"
            and e.get("validation_status") == "SOURCE_SUPPORTED"
            and e.get("source_id") == entity["source_id"]
            and contains(alias, e["label"])
            for e in entities.values()
        ):
            continue
        versions = set(re.findall(r"\b\d+\.\d+\b", entity["label"]))
        valid = True
        for span in spans:
            section = logical_section(span, document)
            if span["source_id"] != entity["source_id"] or not contains(alias, span["quote"]):
                valid = False
                break
            if not re.search(
                r"\b(?:test|testing|experimental|configuration|methods?|disassembly|inspection|functional|conclusions?|results?)\b",
                section,
                re.IGNORECASE,
            ) or re.search(
                r"analysis|model|background|introduction|references", section, re.IGNORECASE
            ):
                valid = False
                break
            if any(
                v not in versions
                for v in re.findall(re.escape(alias) + r"\s*(\d+\.\d+)", span["quote"])
            ):
                valid = False
                break
            if any(
                e.get("class_id") == "Sample"
                and e.get("validation_status") == "SOURCE_SUPPORTED"
                and e.get("id") != entity.get("id")
                and contains(e["label"], span["quote"])
                for e in entities.values()
            ):
                valid = False
                break
        if valid:
            return {
                "basis": "UNIQUE_ORIGINAL_TEST_ARTICLE_ACRONYM_REQUIRES_SCOPE_REVIEW",
                "original_acronym": alias,
                "support": identity,
                "global_alias_activation": "NONE",
                "scientific_approval": "NONE",
            }
    return None


def test_article_named_by_acronym(subject, spans, entities, document, value=None):
    """The source-defined test article a passage names by its acronym, in context.

    Beyond the identity checks of ``test_article_alias_review`` (one current test
    article whose printed label defines the acronym, no other specimen sharing it,
    the passage in the study's own test or results text), every passage must speak
    about the article: the acronym is printed outside a procedural or temporal
    clause of its sentence. For a value, that sentence is the one printing it. The
    link is local to these passages; the acronym is never substituted globally.
    """
    review = test_article_alias_review(subject, spans, entities, document)
    if not review:
        return None
    alias = review["original_acronym"]
    for span in spans:
        sentence = sentence_with(span["quote"], value) if value else span["quote"]
        if sentence is None and value:
            continue  # the value is printed in another of the passages
        if not acronym_names_local_subject(alias, sentence):
            return None
    if value and not any(sentence_with(s["quote"], value) for s in spans):
        return None
    return {
        **review,
        "basis": "SOURCE_DEFINED_TEST_ARTICLE_ACRONYM_NAMES_LOCAL_SUBJECT",
        "local_link_only": True,
    }


def page_continuation_context(spans, evidence):
    """A lower-case continuation after a page break is not a whole proposition."""
    pages = list(evidence.values())
    counts = {}
    for page in pages:
        for line in set(page["text"].splitlines()):
            if line.strip():
                counts[line.strip()] = counts.get(line.strip(), 0) + 1

    def body(page):
        lines = page["text"].splitlines(keepends=True)
        left = 0
        right = len(page["text"])
        while lines and (
            not lines[0].strip()
            or lines[0].strip() == str(page.get("page"))
            or counts.get(lines[0].strip(), 0) > 1
        ):
            left += len(lines.pop(0))
        while lines and (
            not lines[-1].strip()
            or lines[-1].strip() == str(page.get("page"))
            or counts.get(lines[-1].strip(), 0) > 1
        ):
            right -= len(lines.pop())
        return left, right, page["text"][left:right].strip()

    for span in spans:
        current = evidence[span["evidence_id"]]
        if current.get("page") is None:
            continue
        previous = [
            p
            for p in pages
            if p["source_id"] == current["source_id"] and p.get("page") == current["page"] - 1
        ]
        if len(previous) != 1:
            continue
        begin, _, text = body(current)
        prev = previous[0]
        _, end, tail = body(prev)
        if (
            text
            and text[0].islower()
            and tail
            and tail[-1] not in ".!?:"
            and span["start"] <= begin < span["end"]
        ):
            start = prev["text"].rfind("\n\n", 0, end) + 2
            if start == 1:
                start = 0
            return {
                "basis": "ORIGINAL_SENTENCE_CONTINUES_FROM_PREVIOUS_PDF_PAGE",
                "evidence_id": prev["evidence_id"],
                "start": start,
                "end": end,
                "quote": prev["text"][start:end],
            }
    return None


def consolidate_validated_variants(records, entities, evidence, document):
    """One active exact assertion; original inference variants remain auditable."""
    primary = {}
    # A printed value already owned by a quantity, and an entity's exact support.
    value_owner, entity_by_support = {}, {}
    # A proposal with a known study owns its duplicates before one whose study
    # is unknown; a subject that passed the applicability check directly owns them
    # before one accepted there only through recovery, and a direct attribution
    # before any structural recovery (a recognized name form or a pronoun's
    # antecedent). The order never depends on judgments.
    for record in sorted(
        records,
        key=lambda r: (
            (r.get("proposal") or {}).get("study") == "unknown",
            r.get("subject_applicability") == "RECOVERED",
            bool(r.get("subject_recognition") or r.get("subject_antecedent")),
            r["id"],
        ),
    ):
        if record["status"] == "REJECTED":
            continue
        item = record["proposal"]
        kind = record["kind"]
        key = None
        if kind == "statements":
            body = item["text"]
            for span in record["support_spans"]:
                heading = document.get("layout_headings", {}).get(span["evidence_id"])
                if (
                    heading
                    and body.startswith(heading["quote"])
                    and any(
                        norm(e["label"]) == norm(heading["quote"])
                        and e["id"] in record.get("scope", [])
                        for e in entities.values()
                    )
                ):
                    body = body[len(heading["quote"]) :].lstrip()
            positions = []
            for span in record["support_spans"]:
                try:
                    located = recover_span(evidence[span["evidence_id"]]["text"], body)
                except ValueError:
                    continue
                if span["start"] <= located["start"] and located["end"] <= span["end"]:
                    positions.append((span["evidence_id"], located["start"], located["end"]))
            if positions:
                # The same printed sentence, role and study proposed from two
                # windows is one statement; its validated scopes are joined below.
                key = (
                    kind,
                    record["status"],
                    norm(body),
                    item["epistemic"],
                    canonical_modality(kind, item)
                    if plan_goal_facets_enabled() and item["epistemic"] in PLAN_GOAL_ROLES
                    else stated_modality(item),
                    item["study"],
                    tuple(sorted(set(positions))),
                    tuple(sorted(record["reasons"])),
                )
        elif (
            kind == "quantities"
            and item["epistemic"] == "experimental_configuration"
            and record.get("source_role") == "SPECIMEN_CHARACTERISTIC"
        ):
            subject = entities.get(item["subject"], {})
            if contains(item["expression"], subject.get("label", "")) and contains(
                item["unit"] or "", subject.get("label", "")
            ):
                key = (
                    kind,
                    record["status"],
                    record.get("subject"),
                    record.get("mapping", {}).get("source_accessor"),
                    item["expression"],
                    item["unit"],
                    stated_modality(item),
                    tuple(sorted(record["reasons"])),
                )
        if (
            kind == "relations"
            and record["status"] == "SOURCE_SUPPORTED"
            and record.get("subject")
            and record.get("object")
        ):
            # One relation between the same two entities, proposed by the model
            # and by the printed structure, is one assertion.
            key = (kind, record["status"], record["subject"], item["relation"], record["object"])
        binding = record.get("table_row_binding") or {}
        if key is None and kind == "quantities" and binding.get("rows"):
            # One table cell bound through the same printed row(s), proposed by
            # the model and by the printed structure, is one assertion.
            key = (
                kind,
                record["status"],
                record.get("subject"),
                norm(item["label"]),
                item["expression"],
                item["unit"],
                item["epistemic"],
                stated_modality(item),
                tuple(
                    sorted(
                        (r.get("page"), r.get("row_index"), r.get("column_index"))
                        for r in binding["rows"]
                    )
                ),
                tuple(sorted(record["reasons"])),
            )
        if key is None and kind == "quantities" and record.get("quantity_value_spans"):
            # The same printed value, subject, unit and role proposed twice is one
            # quantity, whatever each proposal called it ("O2" and "oxygen
            # concentration" for one printed "37% O2"): one printed value names
            # one quantity.
            base = (
                kind,
                record["status"],
                record.get("subject"),
                item["expression"],
                item["unit"],
                item["epistemic"],
                stated_modality(item),
                tuple(sorted(record["reasons"])),
            )
            values = [
                (v["evidence_id"], v["start"], v["end"]) for v in record["quantity_value_spans"]
            ]
            key = (*base, tuple(values))
            # A proposal that shares one printed value with another names the same
            # quantity, though either cites the value in more places.
            key = next((value_owner[(base, v)] for v in values if (base, v) in value_owner), key)
            for v in values:
                value_owner.setdefault((base, v), key)
        if key is None and kind == "entities" and record.get("entity_id"):
            same_support = (
                norm(item.get("label", "")),
                item.get("class_id"),
                tuple(
                    sorted(
                        (s["evidence_id"], s["start"], s["end"]) for s in record["support_spans"]
                    )
                ),
            )
            other = entity_by_support.get(same_support)
            studies = {item.get("study"), (other or {}).get("proposal", {}).get("study")}
            if other is not None and "cited" in studies and len(studies) > 1:
                # One printed name read as both the current and a cited study's:
                # the source span does not decide which, so one entity stays open.
                record["duplicate_of"] = other["id"]
                record["active_proposal"] = False
                other.setdefault("validated_variant_ids", []).append(record["id"])
                if other["status"] == "SOURCE_SUPPORTED":
                    other["status"] = "UNRESOLVED"
                if "CURRENT_OR_CITED_STUDY_CONFLICT_FOR_SAME_SOURCE_SPAN" not in other["reasons"]:
                    other["reasons"].append("CURRENT_OR_CITED_STUDY_CONFLICT_FOR_SAME_SOURCE_SPAN")
                continue
            entity_by_support.setdefault(same_support, record)
            # Two proposals that resolve to the same entity, class and study are one
            # entity ("Polycarbonate" and "polycarbonate"); an unknown study does not
            # make another entity of a current one. A cited proposal stays separate.
            key = (
                kind,
                record["status"],
                record["entity_id"],
                item.get("class_id"),
                "current" if item.get("study") in {"current", "unknown"} else item.get("study"),
            )
        if key is None:
            continue
        if key not in primary:
            primary[key] = record
            continue
        owner = primary[key]
        if kind == "statements" and record.get("scope"):
            # Each scope was validated on its own; one statement carries both.
            owner["scope"] = sorted(set(owner.get("scope", [])) | set(record["scope"]))
        record["duplicate_of"] = owner["id"]
        record["active_proposal"] = False
        owner.setdefault("validated_variant_ids", []).append(record["id"])
        existing = {(s["evidence_id"], s["start"], s["end"]) for s in owner["support_spans"]}
        for span in record["support_spans"]:
            k = (span["evidence_id"], span["start"], span["end"])
            if k not in existing:
                owner["support_spans"].append(span)
                existing.add(k)
        owner["support_spans"].sort(key=lambda s: (s["evidence_id"], s["start"], s["end"]))


RESEARCH_SECTION = re.compile(
    r"\b(?:results?|discussion|conclusions?|methods?|methodology|experimental|tests?|testing"
    r"|verification|disassembly|inspection|analysis)\b",
    re.IGNORECASE,
)
NON_RESEARCH_SECTION = re.compile(
    r"\b(?:prior|historical|literature|background|introduction|references)\b", re.IGNORECASE
)
# Slides that frame a talk rather than report its work.
PRESENTATION_FRAME = re.compile(
    r"\b(?:questions?|feedback|acknowledg\w*|agenda|outline|contents|thank\s+you)\b",
    re.IGNORECASE,
)


def original_research_passage(spans, document):
    """Documentary author attribution, never inheritance by every member run."""

    def research(span):
        section = section_for_span(span, document)
        if RESEARCH_SECTION.search(section) and not NON_RESEARCH_SECTION.search(section):
            return True
        # A slide deck is the presenter's own account: a slide reports their work
        # unless its own title names background or prior work, or frames the talk
        # (the title slide, an agenda, questions). Cited work is excluded below.
        return bool(
            slide_deck(document)
            and section != "UNSPECIFIED"
            and not NON_RESEARCH_SECTION.search(section)
            and not PRESENTATION_FRAME.search(section)
            and span["evidence_id"] != next(iter(_page_texts(document)), None)
        )

    if not spans or not all(research(s) for s in spans):
        return False
    text = " ".join(s["quote"] for s in spans)
    from nasa_fire_ai.ingestion.study_attribution import cited_attribution_nearby

    return (
        not re.search(
            # "prior to lighting", "prior to sealing", "prior to start
            # of the cycle" order a procedure; "prior work" or "prior to this
            # study" points at earlier research.
            r"\b(?:prior(?!\s+to\b(?!\s+(?:this|our|the\s+(?:present|current))\s+(?:study|work|investigation|research|paper|effort|program)))|previous|earlier|historical|reported\s+by|according\s+to)\b|\[\d",
            text,
            re.IGNORECASE,
        )
        and not re.search(
            r"\b[A-Z][a-z]+\s+et\s+al\b|\b(?!(?:Figure|Table|Equation|Test|Run)\d)[A-Z][a-z]+(?:[’']s)?\d{1,3}\b",
            text,
        )
        # A results section can still report a cited study's data by name.
        and not cited_attribution_nearby(spans, document)
    )


def outside_own_research(span, document):
    """Printed in a known section that is not the study's own research text. The
    study's own analysis is its research, and a passage under no recognized
    section is not known to be outside it."""
    return section_for_span(span, document) != "UNSPECIFIED" and not original_research_passage(
        [span], document
    )


def hold_mentioned_only_materials(records, document):
    """A material or specimen named only outside the study's own research text, and
    used by no supported relation, quantity or statement, is a mention, not the
    study's: "Fomblin" in the introduction, "WD-40 was initially chosen" but not used.
    """
    used = set()
    for record in records:
        if record["status"] != "SOURCE_SUPPORTED" or record.get("duplicate_of"):
            continue
        item = record["proposal"]
        if record["kind"] == "relations":
            used |= {item.get("subject"), item.get("object")}
        elif record["kind"] == "quantities":
            used.add(item.get("subject"))
        elif record["kind"] == "statements":
            used |= set(item.get("subjects") or []) | set(record.get("proposed_subjects") or [])
    for record in records:
        item = record["proposal"]
        if (
            record["kind"] == "entities"
            and record["status"] == "SOURCE_SUPPORTED"
            and not record.get("duplicate_of")
            and item.get("class_id") in {"Material", "Sample"}
            and item.get("study") == "current"
            and item.get("key") not in used
            and record["support_spans"]
            and all(outside_own_research(s, document) for s in record["support_spans"])
        ):
            record["status"] = "UNRESOLVED"
            record["reasons"].append("MATERIAL_ONLY_MENTIONED_OUTSIDE_OWN_RESEARCH")


def document_statement_scope(subject, spans, entities, document, cited_named=False):
    """The paper's own investigation scopes a passage of its own research text.

    A passage naming cited work is that work's, except a documentary passage
    (``cited_named``): saying where data came from names its sources.
    """
    entity = entities.get(subject, {})
    return (
        entity.get("class_id") == "Investigation"
        and entity.get("study") == "current"
        and entity.get("validation_status") == "SOURCE_SUPPORTED"
        and normalized(entity.get("label", "")) == normalized(document.get("package_title", ""))
        and all(s["source_id"] == entity["source_id"] for s in spans)
        and (
            original_research_passage(spans, document)
            # A documentary passage of the paper's own body (where its data come
            # from) needs no results section, only not the reference list.
            or (
                cited_named
                and not any(
                    re.search(
                        r"\b(?:references|bibliography|acknowledg\w*)\b",
                        section_for_span(s, document),
                        re.IGNORECASE,
                    )
                    for s in spans
                )
            )
        )
        and not any(
            not cited_named
            and e.get("study") == "cited"
            and cited_mention_outside_current_names(
                e["label"], " ".join(s["quote"] for s in spans), entities
            )
            for e in entities.values()
        )
    )


def subject_label_names_material(subject_label, material_label):
    """A specimen or group whose printed name is the material name plus a qualifier.

    "Alpha (Lot 1)" and "Alpha samples" are made of Alpha by construction of the
    name. "Alpha-500" or "Brass-filled Alpha" are different names, so nothing is
    inferred for them.
    """
    subject, material = normalized(subject_label), normalized(material_label)
    if len(material) < 3:
        return None
    qualifier = re.fullmatch(
        re.escape(material)
        + r"(?:\s*\((?P<paren>(?:batch|lot|group|series|set|run|sample|specimen)\b[^()]*|#?\d+[^()]*)\)"
        + r"|\s+(?P<noun>samples?|specimens?|coupons?|batch(?:es)?|lots?)\b.*)",
        subject,
    )
    if not qualifier:
        return None
    return {
        "basis": "SUBJECT_LABEL_NAMES_MATERIAL",
        "material_label": material_label,
        "qualifier": (qualifier.group("paren") or qualifier.group("noun")).strip(),
    }


def document_investigation(spans, entities, document, own_body=False):
    """The one current document investigation whose research section holds spans.

    ``own_body`` accepts any section of the paper's body but its reference
    list, for what the paper itself states as guidance or a requirement.

    Returns its entity key, or None when there is no such investigation, more
    than one, or the passage is not the paper's own research text.
    """
    roots = [
        key
        for key, e in entities.items()
        if e.get("class_id") == "Investigation"
        and e.get("study") == "current"
        and e.get("validation_status") == "SOURCE_SUPPORTED"
        and normalized(e.get("label", "")) == normalized(document.get("package_title", ""))
    ]
    if len({entities[k]["id"] for k in roots}) != 1:
        return None
    if not document_statement_scope(roots[0], spans, entities, document, cited_named=own_body):
        return None
    return roots[0]


def original_derivation_context(text, spans, evidence):
    """Retain a nearby explicit derivation only for the same original variable.

    A derived curve does not change every observation on its page. Require the
    immediately preceding original bullet/paragraph and a shared variable phrase.
    """

    def phrases(value):
        words = re.findall(r"[a-z]{3,}", value.lower())
        stop = {"the", "and", "was", "were", "are", "from", "with", "for", "that", "this"}
        words = [word for word in words if word not in stop]
        return set(pairwise(words))

    for span in spans:
        original = evidence[span["evidence_id"]]["text"]
        if normalized(text) not in normalized(span["quote"]):
            continue
        found = recover_span(
            original,
            text,
            span["start"] if normalized(text) == normalized(span["quote"]) else None,
        )
        prefix = original[: found["start"]].rstrip()
        starts = [m.end() for m in re.finditer(r"(?:^|\n)\s*•\s*\n|\n\s*\n", prefix)]
        start = starts[-1] if starts else 0
        preceding = prefix[start:]
        explicit = re.search(
            r"\b(?:derivative\s+of|(?:calculated|computed|derived|obtained)\s+from|from\s+(?:\w+\s+){0,2}fits?)\b",
            preceding,
            re.IGNORECASE,
        )
        if explicit and phrases(preceding) & phrases(text):
            return {"evidence_id": span["evidence_id"], "quote": preceding, "start": start}
    return None


def local_investigation_antecedent(subject, spans, entities, document):
    """Resolve explicit result/data anaphora only within one original paragraph.

    This never assigns a study-wide conclusion to an individual run. Multiple
    documentary study antecedents stay unresolved, including cited comparisons.
    """
    entity = entities.get(subject, {})
    if (
        entity.get("class_id") != "Investigation"
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
    ):
        return []
    for span in spans:
        if not re.match(
            r"\s*(?:the|these|our)\s+(?:results|data|findings|experiments|tests)\b",
            span["quote"],
            re.IGNORECASE,
        ):
            continue
        text = "".join(
            s["text"] for s in document["segments"] if s["evidence_id"] == span["evidence_id"]
        )
        begin = text.rfind("\n\n", 0, span["start"]) + 2
        if begin == 1:
            begin = 0
        begin = max(
            [
                begin,
                *[
                    h["end"]
                    for h in document["sections"]
                    if h["evidence_id"] == span["evidence_id"] and h["end"] <= span["start"]
                ],
            ]
        )
        prefix = text[begin : span["start"]]
        matches = {
            k: e
            for k, e in entities.items()
            if e["class_id"] == "Investigation"
            and e.get("validation_status") == "SOURCE_SUPPORTED"
            and e["source_id"] == span["source_id"]
            and mentions(e["label"], prefix)
        }
        # "ABC project" explicitly supplies the role of the nested name ABC;
        # this is a literal source construction, not approximate entity matching.
        for key, other in list(matches.items()):
            if any(
                k != key
                and normalized(e["label"])
                in {
                    normalized(other["label"]) + " " + role
                    for role in ("project", "study", "investigation", "experiment")
                }
                for k, e in matches.items()
            ):
                matches.pop(key, None)
        if set(matches) == {subject} and prefix.strip():
            leading = len(prefix) - len(prefix.lstrip())
            return [
                {
                    "evidence_id": span["evidence_id"],
                    "quote": prefix.strip(),
                    "start": begin + leading,
                }
            ]
    return []
