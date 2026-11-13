"""Quantity naming, binding and derivation from printed text."""

import re
from itertools import pairwise

from nasa_fire_ai.ingestion.abbreviations import segmentation_view, split_by_view
from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.printed_layout import group_section_support, layout_heading
from nasa_fire_ai.ingestion.source_spans import mentions, normalized
from nasa_fire_ai.ingestion.subject_recognition import material_tested_here


def original_heading_scope(spans, entities, document):
    """An exact original group heading can establish scope, never name similarity."""
    explicit_section = any(
        group_section_support(key, [{**span, "quote": ""}], entities, document)
        for key in entities
        for span in spans
    )
    if explicit_section:
        candidates = [
            (key, proof)
            for key in entities
            if (proof := group_section_support(key, spans, entities, document))
        ]
        return candidates[0] if len(candidates) == 1 else None
    headers = [layout_heading(s, document) for s in spans]
    if not headers or any(h is None for h in headers):
        candidates = [
            (key, proof)
            for key in entities
            if (proof := group_section_support(key, spans, entities, document))
        ]
        return candidates[0] if len(candidates) == 1 else None
    labels = {normalized(h["quote"]) for h in headers}
    if len(labels) != 1:
        return None
    choices = {
        e["id"]: (key, e)
        for key, e in entities.items()
        if e["class_id"] == "ExperimentFamily"
        and e.get("validation_status") == "SOURCE_SUPPORTED"
        and normalized(e["label"]) in labels
        and e["source_id"] == spans[0]["source_id"]
    }
    if len(choices) != 1:
        return None
    key, group = next(iter(choices.values()))
    if any(
        e["class_id"] in {"ExperimentalRun", "ExperimentFamily"}
        and e["id"] != group["id"]
        and normalized(e["label"]) != normalized(group["label"])
        and any(mentions(e["label"], s["quote"]) for s in spans)
        for e in entities.values()
    ):
        return None
    return key, [{k: h[k] for k in ("evidence_id", "quote", "start")} for h in headers]


def source_dimension_adjectives(label, unit):
    """Local English dimensional syntax, never a new global semantic alias."""
    from nasa_fire_ai.normalization.units import normalize

    try:
        if normalize(1, unit or "")[1] != "m":
            return []
    except ValueError:
        return []
    stem = re.sub(r"^(?:sample|specimen)\s+", "", normalized(label))
    return {
        "width": ["wide"],
        "length": ["long"],
        "thickness": ["thick"],
        "diameter": ["diameter", "dia"],
    }.get(stem, [])


# Nouns that name a quantity of the unit's own dimension. They may complete a
# printed name ("a 1.4 m3 chamber" -> "chamber volume"), never replace one.
DIMENSION_NOUNS = {
    "length": {
        "length",
        "width",
        "height",
        "diameter",
        "thickness",
        "depth",
        "radius",
        "id",
        "od",
    },
    "volume": {"volume", "capacity"},
    "pressure": {"pressure"},
    "differential_pressure": {"pressure", "differential"},
    "fraction": {"concentration", "fraction", "content", "percentage", "level"},
    "temperature": {"temperature"},
    "time": {"time", "duration", "period"},
    "velocity": {"velocity", "speed"},
    "rotational_speed": {"speed", "rate", "rotation"},
    "mass_flow": {"flow", "rate"},
    "standard_volumetric_flow": {"flow", "rate"},
    "energy": {"energy"},
}
NAME_STOP_WORDS = {
    "by",
    "and",
    "or",
    "with",
    "where",
    "which",
    "that",
    "at",
    "for",
    "of",
    "in",
    "to",
    "was",
    "were",
    "is",
    "are",
    "from",
    "on",
    "under",
    "as",
    "the",
    "a",
    "an",
}


def printed_value_name(label, expression, unit, spans, epistemic=None):
    """The words printed right after a value that name it, separate from the label.

    "a 2.5 m3 (88 ft3) vessel" prints "vessel" after the value, so a label
    "vessel volume" is named by the source: "vessel" is printed and "volume" is
    the unit's own dimension. Every other label word must be printed in the same
    sentence. A value one of a printed pair ("3.5 cm by 9.0 cm coupons") is never
    named this way, since the source does not say which dimension it is.
    """
    from nasa_fire_ai.normalization.units import interpret

    meaning = interpret(unit) if unit else None
    if not meaning or not expression:
        return None
    if meaning["dimension"] == "fraction" and epistemic != "experimental_configuration":
        # "40% brass", "composed of 80% nickel": a percentage before a constituent
        # is a composition, and the printed words alone do not say whose.
        return None
    nouns = DIMENSION_NOUNS.get(meaning["dimension"], set())
    words = normalized(label).split()
    value = r"(?<![\w.])" + re.escape(expression) + r"\s*[-‑]?\s*" + re.escape(unit) + r"(?![\w])"
    for span in spans:
        quote = span["quote"]
        for match in re.finditer(value, quote):
            if re.search(
                r"\bby\s*$", quote[max(0, match.start() - 12) : match.start()], re.IGNORECASE
            ):
                continue
            rest = quote[match.end() :]
            # An author-stated equivalent between value and name: "2.5 m3 (88 ft3) vessel".
            rest = re.sub(r"^\s*\([^()]{1,30}\)", "", rest)
            if re.match(r"\s*by\b", rest, re.IGNORECASE):
                continue
            # "The vessel is 0.41 m3 in volume": the name follows "in".
            rest = re.sub(r"^\s*in\s+(?=[A-Za-z])", " ", rest, flags=re.IGNORECASE)
            head = []
            for token in re.findall(r"[A-Za-z][\w-]*|\S", rest[:80]):
                lowered = token.lower()
                if not re.match(r"[a-z]", lowered) or lowered in NAME_STOP_WORDS or len(head) == 4:
                    break
                head.append(lowered)
            printed = [w for w in words if w in head]
            if not printed:
                continue
            sentence_start = max(quote.rfind(". ", 0, match.start()) + 1, 0)
            sentence_end = quote.find(". ", match.end())
            sentence = quote[sentence_start : sentence_end if sentence_end >= 0 else len(quote)]
            completed = [w for w in words if w not in printed]
            if all(w in nouns or mentions(w, sentence) for w in completed):
                return {
                    "basis": "PRINTED_NAME_AFTER_VALUE",
                    "printed_name": " ".join(printed),
                    "printed_after_value": " ".join(head),
                    "label_words_from_unit_dimension": [w for w in completed if w in nouns],
                    "global_alias_activation": "NONE",
                }
    return None


# A setting printed with its own verb: "the drum was rotated at 12.5 RPM",
# "35uL was dispensed". The verb is the printed name of what was set.
SETTING_VERB_BEFORE = re.compile(r"\b([A-Za-z]{5,}ed)\s+(?:at|to)\s*[~≈]?\s*$", re.IGNORECASE)
SETTING_VERB_AFTER = re.compile(
    r"^\s*(?:of\s+[A-Za-z-]+\s+)?(?:was|were|is|are)\s+([A-Za-z]{5,}ed)\b", re.IGNORECASE
)
CONDITION_CLAUSE = re.compile(r"^\W*(?:if|unless|whether|when|whenever)\b", re.IGNORECASE)


def shared_stem(a, b):
    """Two forms of one word ("rotation", "rotated"): a common start of five letters or more."""
    size = 0
    for x, y in zip(a, b):
        if x != y:
            break
        size += 1
    return size >= 5


def setting_verb_of_unit_dimension(verb, unit):
    """Whether a setting verb is a form of a noun of the unit's own dimension."""
    from nasa_fire_ai.normalization.units import interpret

    meaning = interpret(unit) if unit else None
    nouns = DIMENSION_NOUNS.get(meaning["dimension"], set()) if meaning else set()
    return any(shared_stem(noun, verb.lower()) for noun in nouns)


def printed_setting_name(label, expression, unit, spans, epistemic):
    """The verb that sets a configuration value names it, when the label only spells it out.

    Every label word must be printed in the value's own clause, be a form of that
    verb, or be a noun of the unit's own dimension; a qualifier the clause does not
    print ("centrifuge rotation rate") leaves the name unprinted. Times and
    percentages are excluded: there the verb states a criterion or a composition.
    """
    from nasa_fire_ai.normalization.units import interpret

    meaning = interpret(unit) if unit else None
    if (
        epistemic != "experimental_configuration"
        or not meaning
        or not expression
        or meaning["dimension"] in {"time", "fraction"}
    ):
        return None
    nouns = DIMENSION_NOUNS.get(meaning["dimension"], set())
    words = [w for w in normalized(label).split() if w not in NAME_STOP_WORDS]
    if not words:
        return None
    value = r"(?<![\w.])" + re.escape(expression) + r"\s*[-‑]?\s*" + re.escape(unit) + r"(?![\w])"
    for span in spans:
        quote = span["quote"]
        for match in re.finditer(value, quote):
            start = max(
                quote.rfind(". ", 0, match.start()) + 1, quote.rfind(";", 0, match.start()) + 1, 0
            )
            end = min(
                [i for i in (quote.find(". ", match.end()), quote.find(";", match.end())) if i >= 0]
                or [len(quote)]
            )
            clause = quote[start:end]
            if CONDITION_CLAUSE.match(clause):
                continue
            verb = SETTING_VERB_BEFORE.search(
                quote[start : match.start()]
            ) or SETTING_VERB_AFTER.match(quote[match.end() : end])
            if not verb:
                continue
            form = verb.group(1).lower()
            if not any(shared_stem(w, form) for w in words):
                continue
            if all(w in nouns or shared_stem(w, form) or mentions(w, clause) for w in words):
                return {
                    "basis": "PRINTED_SETTING_VERB_NAMES_VALUE",
                    "printed_name": form,
                    "label_words_from_unit_dimension": [w for w in words if w in nouns],
                    "global_alias_activation": "NONE",
                }
    return None


def model_printed_name(item, spans):
    """The model's printed_name, when the support prints it in the value's own clause.

    The words must be copied exactly, hold a word that is not the value, its unit or
    a joining word, and share a clause with the value; the label stays the model's.
    """
    name = " ".join((item.get("printed_name") or "").split())
    if not name or not item.get("expression") or len(name.split()) > 6:
        return None
    words = [w for w in re.findall(r"[A-Za-z][\w-]*", name) if w.lower() not in NAME_STOP_WORDS]
    if (
        not words
        or any(w.lower() == (item.get("unit") or "").lower() for w in words)
        or re.search(r"\d", name)
    ):
        return None
    values = quantity_name_value_binding([name], item["expression"], item.get("unit"), spans)
    if not values:
        return None
    return {
        "basis": "MODEL_PRINTED_NAME_IN_VALUE_CLAUSE",
        "printed_name": name,
        "global_alias_activation": "NONE",
    }


def quantity_name_value_binding(
    labels, expression, unit, spans, adjacent_names=(), temporal_coordinate=False
):
    """Locate values in the named variable's clause, including repeated numbers."""
    separator = r";|(?<!\b[A-Z])[.!?](?!\d)(?=\s|$)|\b(?:and|while|whereas)\b(?=\s+(?:[A-Za-z][\w%-]*\s+){1,6}(?:was|were|is|are|=)\s+)"
    from nasa_fire_ai.ingestion.numeric_expressions import (
        same_expression,
        source_numeric_matches,
    )

    result = []
    pattern = rf"(?<![\w.])({quantity_expression_pattern()})(?![\d.eE])"
    for span in spans:
        boundaries = [0]
        for cut in re.finditer(separator, segmentation_view(span["quote"]), re.IGNORECASE):
            if cut.group().lower().startswith(("and", "while", "whereas")) and not re.search(
                pattern, span["quote"][boundaries[-1] : cut.start()]
            ):
                continue  # A noun list before its values is one parallel clause.
            boundaries.append(cut.end())
        boundaries.append(len(span["quote"]))
        for begin, end in pairwise(boundaries):
            clause = span["quote"][begin:end]
            if not any(mentions(label, clause) for label in labels):
                continue
            # Whole expressions keep "10,000" and "−40" intact; ordered parallel
            # values are counted on whole expressions only.
            matches = source_numeric_matches(clause, include_endpoints=False)
            if not (re.search(r"\brespectively\b", clause, re.IGNORECASE) and len(matches) > 1):
                matches = source_numeric_matches(clause)
            else:
                # Ordered parallel values are not interchangeable merely because
                # they share a unit and paragraph. Resolve the explicit noun list.
                prefix = clause[: matches[0].start()]
                parts = re.split(r",|\band\b", prefix, flags=re.IGNORECASE)
                parts = parts[-len(matches) :]
                positions = [
                    i
                    for i, part in enumerate(parts)
                    if any(mentions(label, part) for label in labels)
                ]
                matches = (
                    [matches[positions[0]]]
                    if len(parts) == len(matches) and len(positions) == 1
                    else []
                )
            for match in matches:
                if not same_expression(match.group(), expression):
                    continue
                if temporal_coordinate and not re.search(
                    r"\bat\s*(?:t\s*=\s*)?$|\bt\s*=\s*$", clause[: match.start()], re.IGNORECASE
                ):
                    continue
                finish = match.end()
                if unit:
                    adjacent = re.match(
                        r"\s*[-‑]?\s*" + re.escape(unit) + r"(?!\w)", clause[finish:]
                    )
                    if not adjacent:
                        continue
                    finish += adjacent.end()
                if adjacent_names and not re.match(
                    r"[\s‑-]*(?:in\s+)?(?:"
                    + "|".join(re.escape(n) for n in adjacent_names)
                    + r")\b",
                    clause[finish:],
                    re.IGNORECASE,
                ):
                    continue
                result.append(
                    {
                        "evidence_id": span["evidence_id"],
                        "start": span["start"] + begin + match.start(),
                        "end": span["start"] + begin + finish,
                        "quote": clause[match.start() : finish],
                    }
                )
    return result


PRONOUN_START = re.compile(
    r"\s*(?:it|they|this\s+(?:material|sample|specimen)|these\s+(?:materials|samples|specimens)|each)\b",
    re.IGNORECASE,
)


def continued_sentence(spans, evidence):
    """The sentence a page break cut, joined from the previous page's tail.

    Returns {"quote", "continuation"} or None. The joined text is only a reading
    aid for names and subjects; value positions always stay on the original page.
    """
    from nasa_fire_ai.ingestion.scientific_scope import page_continuation_context

    continuation = page_continuation_context(spans, evidence)
    if not continuation:
        return None
    for span in spans:
        if span["evidence_id"] == continuation["evidence_id"]:
            continue
        head = re.sub(r"^\s*\d+\s*\n", "", span["quote"])
        head = split_by_view(r"(?<=[.!?])\s", head, maxsplit=1)[0]
        tail = continuation["quote"].rstrip()
        joined = tail[:-1] + head.lstrip() if tail.endswith("-") else tail + " " + head.lstrip()
        return {"quote": joined, "continuation": continuation}
    return None


def anaphoric_subject(subject, expression, spans, entities, evidence, document=None):
    """A pronoun that opens the value's sentence names the one subject of the
    sentence before it, in the same paragraph and subsection ("Alpha was tested. It
    was ..."): a heading line between them is part of the value's sentence, so the
    pronoun no longer opens it."""
    entity = entities[subject]
    for span in spans:
        text = evidence[span["evidence_id"]]["text"]
        position = text.find(expression, span["start"], span["end"])
        if position < 0:
            continue
        starts = [m.end() for m in re.finditer(r"[.!?](?=\s)", segmentation_view(text)[:position])]
        if not starts:
            continue
        sentence = text[starts[-1] : position]
        previous = text[starts[-2] if len(starts) > 1 else 0 : starts[-1]]
        if not PRONOUN_START.match(sentence) or re.search(r"\n\s*\n", previous + sentence):
            continue
        named = [
            e
            for e in entities.values()
            if e.get("validation_status") == "SOURCE_SUPPORTED"
            and e["class_id"] in {"Material", "Sample", "ExperimentFamily", "ExperimentalRun"}
            and mentions(e["label"], previous)
            # A test value's antecedent is a tested subject: a material counts
            # only when this document's own tables show it tested here.
            and (
                e["class_id"] != "Material"
                or document is None
                or material_tested_here(e["label"], document)
            )
        ]
        if {e["id"] for e in named} == {entity["id"]}:
            return {
                "basis": "PRONOUN_SUBJECT_OF_PRECEDING_SENTENCE",
                "evidence_id": span["evidence_id"],
                "preceding_sentence": previous.strip(),
            }
    return None


def applied_column_value(table_binding, unit, document, evidence):
    """An applied test step that prints one of the bound column's values, if any.

    The printed value must carry a unit of the cell's own canonical unit, so a
    count ("in 15 of 15 coupons") never makes a results column a setting.
    """
    from nasa_fire_ai.ingestion.statement_integrity import APPLIED_STEP
    from nasa_fire_ai.ingestion.table_continuity import table_rows
    from nasa_fire_ai.normalization.units import interpret

    wanted = (interpret(unit) or {}).get("canonical_unit")
    if not wanted:
        return None
    headers = {(r["page"], r["column_header"]) for r in table_binding["rows"]}
    values = {
        number
        for row in table_rows(document)
        for cell in row["cells"]
        if (row["page"], cell["header"]) in headers
        for number in re.findall(r"\d[\d,]*(?:\.\d+)?", cell["original_value"] or "")
    }
    if not values:
        return None
    for e in evidence.values():
        for sentence in split_by_view(r"(?<=[.!?])\s+", e["text"]):
            step = APPLIED_STEP.search(sentence)
            if not step:
                continue
            for number, printed in re.findall(
                r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*([A-Za-z°%][\w°%/-]*)", sentence[step.end() :]
            ):
                if number in values and (interpret(printed) or {}).get("canonical_unit") == wanted:
                    return sentence.strip()[:300]
    return None


def value_is_applied_input(value_spans, evidence):
    """Whether each value follows an applied test step in its own clause."""
    from nasa_fire_ai.ingestion.statement_integrity import APPLIED_STEP, OUTCOME_CUE

    if not value_spans:
        return False
    for value in value_spans:
        text = evidence[value["evidence_id"]]["text"]
        clause = re.split(r"[.;!?](?=\s)", text[: value["start"]])[-1]
        steps = list(APPLIED_STEP.finditer(clause))
        if not steps or OUTCOME_CUE.search(clause[steps[-1].end() :]):
            return False
    return True


def value_sentences(value_spans, evidence):
    """The original sentence around each bound value, stopping at captions."""
    result = []
    for value in value_spans:
        text = evidence[value["evidence_id"]]["text"]
        view = segmentation_view(text)
        # The caption cut reads "fig." on the masked text as "fig" plus the mask.
        fig = r"fig\." if view is text else r"fig[.\u2024]"
        cuts = [
            m.end()
            for m in re.finditer(
                r"[.!?](?=\s)|\n\s*\n|\n(?=\s*(?:table|figure|" + fig + r")\s*\d)",
                view,
                re.IGNORECASE,
            )
        ]
        begin = max([c for c in cuts if c <= value["start"]], default=0)
        end = min([c for c in cuts if c >= value["end"]], default=len(text))
        result.append(text[begin:end])
    return result


NAME_VALUE_LINK = re.compile(
    r"\s*(?:\([^()]*\)\s*)?"
    # "dwell periods across the Run A1 cycle of ~250 msec": a short phrase
    # without numbers between the name and its "of".
    r"(?:\s*\b(?:during|for|in|at|over)\s+[^,.;:\d()]{1,40}?\s+(?=of\b))?"
    r"(?:=|:|[<>≤≥]|\b(?:was|were|is|are|of|averaged|reached|totall?ed|equall?ed"
    r"|ranged\s+(?:from|between)|ranging\s+(?:from|between)|varied\s+(?:from|between)"
    # "the char depth decreased in the second series from 4 mm": the starting value of
    # a printed change.
    r"|(?:decreased|increased|dropped|rose|fell)(?:\s+[^,.;:\d()]{1,40}?)?\s+from)\b"
    r"(?:\s+(?:approximately|about|roughly|nearly|around|only))?)\s*[~≈]?\s*$",
    re.IGNORECASE,
)


def staged_name_syntax(label, record, evidence):
    """How the printed text makes the label the name of the value, if it does."""
    basis = record.get("quantity_name_support", {}).get("basis")
    if basis in {
        "ORIGINAL_TABLE_COLUMN_HEADER",
        "EXPLICIT_POST_VALUE_DIMENSIONAL_ADJECTIVE",
        "SAME_SUBJECT_VALUE_UNDER_DOCUMENT_TABLE_COLUMN",
        "PRINTED_NAME_AFTER_VALUE",
        "PRINTED_SETTING_VERB_NAMES_VALUE",
    }:
        return basis
    if basis == "NAME_BEFORE_PAGE_BREAK_OF_SAME_SENTENCE" and record.get("sentence_continuation"):
        tail = record["sentence_continuation"]["quote"].rstrip()
        value = record["quantity_value_spans"][0]
        text = evidence[value["evidence_id"]]["text"]
        head = re.sub(r"^\s*\d+\s*\n", "", text[: value["start"]])
        before = tail[:-1] + head.lstrip() if tail.endswith("-") else tail + " " + head.lstrip()
        name = r"(?<![\w-])" + r"\s+".join(re.escape(w) for w in label.split()) + r"(?![\w-])"
        masked = segmentation_view(before)
        for match in re.finditer(name, before, re.IGNORECASE):
            if NAME_VALUE_LINK.fullmatch(masked[match.end() :]):
                return "PRINTED_NAME_LINKED_TO_VALUE_ACROSS_PAGE_BREAK"
        return None
    if basis == "EXPLICIT_SOURCE_TEMPORAL_COORDINATE":
        return None  # a time coordinate of an event, not a property of a subject
    name = r"(?<![\w-])" + r"\s+".join(re.escape(w) for w in label.split()) + r"(?![\w-])"
    for value in record.get("quantity_value_spans", []):
        text = evidence[value["evidence_id"]]["text"]
        before = text[max(0, value["start"] - 200) : value["start"]]
        masked = segmentation_view(before)
        for match in re.finditer(name, before, re.IGNORECASE):
            if NAME_VALUE_LINK.fullmatch(masked[match.end() :]):
                return "PRINTED_NAME_LINKED_TO_VALUE"
            # "char length < 8 cm": a bound printed with its comparator.
            # A bare word of magnitude ("an amount < 3 g") names no quantity.
            if (
                re.match(r"[<>≤≥]", value.get("quote") or "")
                and not before[match.end() :].strip()
                and not re.fullmatch(
                    r"(?:levels?|values?|amounts?|numbers?|quantity|quantities)",
                    label.strip(),
                    re.IGNORECASE,
                )
            ):
                return "PRINTED_NAME_BOUNDED_BY_VALUE"
            # "a gentle stream (~45 cm/s)": the value printed in parentheses after its name.
            if re.fullmatch(r"\s*\(\s*[~≈]?\s*", before[match.end() :]):
                return "PRINTED_NAME_WITH_PARENTHETICAL_VALUE"
        # "a 25 cm/s purge stream": the value printed as the modifier of its name.
        after = text[value["end"] : value["end"] + 120]
        # "a coating of 30% alumina and 70% silica", "100% wool felt": a percentage
        # printed right before a component names the component's fraction.
        if (
            (record.get("proposal") or {}).get("unit") == "%"
            and re.match(r"\s*" + name, after, re.IGNORECASE)
            # "the outer layer of the panel is 90% wool": the fraction is the part's,
            # not the whole's; it never names a fraction of the subject.
            and not re.search(
                r"\b(?:component|portion|part|layer|phase|core|shell|coating|filler|matrix)"
                r"\s+of\b",
                text[max(0, value["start"] - 160) : value["start"]],
                re.IGNORECASE,
            )
        ):
            return "PRINTED_PERCENT_OF_COMPONENT"
        # "0.41 m3 in volume": the value printed before "in" and its name.
        if re.match(r"\s*in\s+" + name, after, re.IGNORECASE):
            return "PRINTED_VALUE_IN_ITS_NAME"
        if (
            re.match(r"\s*" + name, after, re.IGNORECASE)
            # "a 25 cm/s purge stream", "a sliding 3.6 mm OD quartz pin".
            and re.search(
                r"\b(?:an?|the|its|their|his|her|our)\s+(?:[a-z][a-z-]+\s+)?$",
                text[max(0, value["start"] - 30) : value["start"]],
                re.IGNORECASE,
            )
            # "rather than the 9 mm sag limit": a value set aside is not named.
            and not re.search(
                r"\b(?:rather\s+than|instead\s+of|not|nor)\s+(?:an?|the)\s*$",
                text[max(0, value["start"] - 30) : value["start"]],
                re.IGNORECASE,
            )
        ):
            return "PRINTED_VALUE_MODIFIES_ITS_NAME"
        sentence = value_sentences([value], evidence)[0]
        prefix = sentence[: sentence.find(value["quote"])]
        named = list(re.finditer(name, prefix, re.IGNORECASE))
        if not (re.search(r"\brespectively\b", sentence, re.IGNORECASE) and named):
            continue
        # "Both length and width decrease (1.2 cm and 0.4 cm respectively)":
        # the values are the changes, so a bare "length" does not name them.
        change = (
            r"\b(?:decreas|increas|drop|grow|grew|shrink|shrank|ris|rose|fall|fell|declin|reduc)\w*"
        )
        if re.search(change, prefix[named[-1].end() :], re.IGNORECASE) and not re.search(
            change, label, re.IGNORECASE
        ):
            continue
        return "ORDERED_PARALLEL_NAMES_RESPECTIVELY"
    return None


# English state modifiers that name when or where the same physical quantity was
# read ("initial pressure"), never a different quantity ("vapor pressure").
STATE_QUALIFIERS = frozenset(
    {
        "initial",
        "final",
        "starting",
        "test",
        "system",
        "chamber",
        "ambient",
        "operating",
        "maximum",
        "max",
        "minimum",
        "min",
        "peak",
        "mean",
        "average",
        "nominal",
    }
)


def resolve_source_property(semantic, label, unit):
    """Reuse an approved alias with an explicit unit suffix, without adding aliases."""
    status, prop = semantic.resolve_property(label, unit)
    if prop or not unit:
        return status, prop
    stems = [label]
    for suffix in (unit, "(" + unit + ")", "[" + unit + "]"):
        if label.endswith(suffix):
            stem = label[: -len(suffix)].strip()
            stems.append(stem)
            candidate_status, candidate = semantic.resolve_property(stem, unit)
            if candidate:
                return candidate_status, candidate
    # "Initial Pressure (psia)" is an approved pressure read in a stated state; the
    # approved contract still checks the unit dimension. Other modifiers stay unknown.
    for stem in stems:
        words = normalized(stem).split()
        for cut in range(1, len(words)):
            if words[cut - 1] not in STATE_QUALIFIERS:
                break
            candidate_status, candidate = semantic.resolve_property(" ".join(words[cut:]), unit)
            if candidate:
                return "CANONICAL_STATE_QUALIFIED", candidate
    return status, prop


def property_proposal(item, subject, spans, semantic):
    """A staged, source-grounded property proposal; never an activated definition."""
    from nasa_fire_ai.normalization.units import interpret

    term = item["label"]
    for suffix in (item["unit"] or "", "(" + (item["unit"] or "") + ")"):
        if suffix and term.endswith(suffix):
            term = term[: -len(suffix)].strip()
    unit = interpret(item["unit"])
    candidates = []
    for prop in semantic.properties.values():
        try:
            from nasa_fire_ai.normalization.units import normalize

            same = bool(unit) and normalize(1, unit["original_unit"])[1] == prop.canonical_unit
        except ValueError:
            same = False
        if same:
            candidates.append(prop.property_id)
    return {
        "id": "property-proposal-" + identity([normalized(term), unit and unit["dimension"]])[:20],
        "kind": "property",
        "term": term,
        "dimension": unit["dimension"] if unit else None,
        "canonical_unit": unit["canonical_unit"] if unit else None,
        "original_units": [item["unit"]] if item["unit"] else [],
        "applicable_subject_classes": [subject["class_id"]],
        "approved_properties_examined": sorted(semantic.properties),
        # Same dimension is not the same quantity; these are only reviewer leads.
        "same_dimension_approved_properties": candidates,
        "evidence_ids": sorted({s["evidence_id"] for s in spans}),
        "activation": "NONE",
        "status": "STAGED_FOR_ONTOLOGY_REVIEW",
    }


def explicit_quantity_derivation(labels, values, spans):
    """Explicit derivation words bound to this variable/value, not its neighbors."""
    derived = re.compile(
        r"\b(?:calculated|computed|estimated|assumed|derived|predicted)\b|\b(?:best|least[- ]squares)\s+fits?\b",
        re.IGNORECASE,
    )
    for value in values:
        for span in spans:
            if (
                span["evidence_id"] != value["evidence_id"]
                or not span["start"] <= value["start"] < span["end"]
            ):
                continue
            before = span["quote"][: value["start"] - span["start"]]
            masked = segmentation_view(span["quote"])[: value["start"] - span["start"]]
            # Do not let a different preceding sentence or semicolon establish
            # the role of a later measured variable.
            boundary = max(
                [0, *[m.end() for m in re.finditer(r";|[.!?](?!\d)(?=\s|$)|\n\s*•\s*\n", masked)]]
            )
            before = before[boundary:]
            names = [
                m
                for label in labels
                for m in re.finditer(
                    r"(?<!\w)" + re.escape(label) + r"(?!\w)", before, re.IGNORECASE
                )
                if label
            ]
            if not names:
                continue
            name = max(names, key=lambda m: m.start())
            local = before[name.start() :]
            prefix = before[: name.start()]
            preceding = re.search(
                r"(?:calculated|computed|estimated|assumed|derived|predicted|best\s+fit)\s+$",
                prefix,
                re.IGNORECASE,
            )
            candidates = (
                [preceding.group()]
                if preceding
                and not re.search(
                    r"\b(?:not|rather\s+than|instead\s+of)\s*$",
                    prefix[: preceding.start()],
                    re.IGNORECASE,
                )
                else []
            )
            candidates += [
                m.group()
                for m in derived.finditer(local)
                if not re.search(
                    r"\b(?:not|rather\s+than|instead\s+of)\s*$", local[: m.start()], re.IGNORECASE
                )
            ]
            if candidates:
                return candidates
    return []


def native_quantity_expression(expression):
    from nasa_fire_ai.query.numeric_mentions import NUMBER

    return bool(
        re.fullmatch(
            rf"(?:~\s*|≈\s*|(?:about|approximately|roughly)\s+)?{NUMBER}(?:\s*[-–]\s*{NUMBER})?",
            expression,
        )
    )


def heading_binding(item, spans, entities, document, semantic):
    """Resolve only explicit typed header assignments, retaining original evidence."""
    subject, obj = entities[item["subject"]], entities[item["object"]]
    if subject["class_id"] != "ExperimentFamily" or item["relation"] not in {
        "hasMaterial",
        "hasGravityCondition",
    }:
        return None
    aliases = [obj["label"]]
    meta = getattr(semantic, "entity_mentions", {}).get(obj["id"], {})
    aliases.extend(meta.get("aliases", []))
    if meta:
        aliases.append(obj["id"])
    for span in spans:
        header = layout_heading(span, document)
        if (
            not header
            or normalized(header["quote"]) != normalized(subject["label"])
            or ":" not in header["quote"]
        ):
            continue
        prefix, suffix = header["quote"].split(":", 1)
        if re.search(
            r"\b(?:except|without|not|than|compared)\b",
            " ".join(s["quote"] for s in spans),
            re.IGNORECASE,
        ):
            continue
        if item["relation"] == "hasMaterial":
            matched = normalized(suffix) in {normalized(a) for a in aliases}
        else:
            conditions = {
                canonical
                for canonical, m in getattr(semantic, "entity_mentions", {}).items()
                if m.get("relation") == "hasGravityCondition"
                and any(mentions(a, prefix) for a in [canonical, *m.get("aliases", [])])
            }
            matched = len(conditions) == 1 and obj["id"] in conditions
        if matched:
            return {
                "status": "SUPPORTED",
                "basis": "EXPLICIT_ORIGINAL_TYPED_GROUP_HEADER",
                "support": [{k: header[k] for k in ("evidence_id", "quote", "start")}],
            }
    return None


def qualified_material_heading(label, document, semantic):
    """A context-qualified result heading does not name a new material substance."""
    if not any(
        normalized(h["quote"]) == normalized(label)
        for h in document.get("layout_headings", {}).values()
    ):
        return False
    if not re.search(r":|\b(?:results?|comparison|tests?|experiments?)\b", label, re.IGNORECASE):
        return False
    if ":" in label and re.search(
        r"\b(?:results?|comparison|tests?|experiments?|groups?|series|recap)\b",
        label.split(":", 1)[0],
        re.IGNORECASE,
    ):
        return True
    aliases = [
        a
        for canonical, meta in getattr(semantic, "entity_mentions", {}).items()
        if meta.get("relation") == "hasMaterial"
        for a in [canonical, *meta.get("aliases", [])]
    ]
    return any(mentions(a, label) and normalized(a) != normalized(label) for a in aliases)


def quantity_expression_pattern():
    """Source-finding grammar; see ingestion.numeric_expressions for its contract."""
    from nasa_fire_ai.ingestion.numeric_expressions import numeric_expression_pattern

    return numeric_expression_pattern()
