"""Whole-statement integrity checks read from the original page text.

These checks never repair or reinterpret a statement. They mark, for review,
statements that are not one whole source proposition (cut at an abbreviation or
at a page break), observations whose own source prints a conflicting count, and
one source span accepted with incompatible epistemic roles.
"""

import re

from nasa_fire_ai.ingestion.abbreviations import ViewPattern, segmentation_view
from nasa_fire_ai.ingestion.scientific_facets import ROLES, role_families

ABBREVIATION_END = re.compile(
    r"(?:\b(?:i\.\s?e|e\.\s?g|vs|cf|approx|ca|Figs?|Eqs?|No|Refs?)\.|\bet\s+al\.)\s*$",
    re.IGNORECASE,
)
TERMINAL = re.compile(r"[.!?:;\"”’)\]]\s*$")
CONTINUING_TAIL = re.compile(
    r"(?:[,(–—-]|\b(?:of|the|a|an|and|or|nor|to|in|for|with|by|from|as|at|on|that|which|than"
    r"|whose|its|their|be|been|being|was|were|is|are|has|have|had|not|will|would|could"
    r"|should|may|might|can)\b)\s*$",
    re.IGNORECASE,
)
OBSERVATION_CUE = re.compile(
    r"\b(?:test\w*|react\w*|pass(?:ed|es)?|fail\w*|impact\w*|ignit\w*|burn\w*|flam\w*|extinguish\w*"
    r"|measur\w*|observ\w*|shown|show(?:s|ed|ing)?|result\w*|data|record\w*|detect\w*|seen"
    r"|pictur\w*|photo\w*|imag\w*|produc\w*|perform\w*|exhibit\w*|found|reach\w*|increas\w*"
    r"|decreas\w*|rose|fell|remain\w*|became|occur\w*|spread\w*|grew|shrank|reduc\w*)\b",
    re.IGNORECASE,
)
PURPOSE = re.compile(r"\b(?:in\s+order\s+to|so\s+as\s+to)\b", re.IGNORECASE)
POINTER = ViewPattern(
    re.compile(
        r"\b(?:are|is|were|was)\s+(?:shown|presented|listed|given|summarized|tabulated|plotted"
        r"|depicted)\s+in\s+(?:Table|Figure|Fig\.?|Appendix)\b"
        # "The closed symbols at ~25 cm/s are the centrifuge data": what a plot's
        # marks stand for, not a result.
        r"|^\s*the\s+(?:[\w-]+\s+){0,3}(?:symbols?|circles?|squares?|triangles?|markers?|lines?|curves?"
        r"|bars?|points?)\b[^.;]*\b(?:are|is|represents?|denotes?|indicates?|shows?)\s+(?:the\s+)?"
        r"(?:[\w-]+\s+){0,4}(?:data|results?|values?|tests?|limits?|fit)\b",
        re.IGNORECASE,
    )
)
RULE_OR_CAVEAT = ViewPattern(
    re.compile(
        r"\b(?:(?:cannot|can\s+only)(?!\s+be\s+(?:seen|observed|detected|distinguished|resolved|identified|measured)\b)|must|shall|should|ought\s+to|(?:is|are)\s+only\s+valid"
        r"|(?:is|are)\s+(?:not\s+)?(?:required|necessary|permitted|allowed))\b",
        re.IGNORECASE,
    )
)
VALIDITY_CAVEAT = re.compile(
    r"\b(?:is|are|was|were)\s+(?:only\s+)?(?:valid|applicable)(?:\s+only)?\s+(?:for|when|if"
    r"|within|below|above|under|between|up\s+to)\b",
    re.IGNORECASE,
)
# The passive verbs of the applied-step class, kept apart from the auxiliary so that other
# checks read the same class: what was done to the test article, then the set-up steps.
APPLIED_STEP_VERBS = (
    r"impacted|struck|tested|exposed|subjected|heated|pressurized|loaded"
    r"|placed|positioned|submerged|immersed|purged|sealed|prepared|cooled|dropped|mounted"
    r"|set\s*up|switched|configured|installed|connected|injected|adjusted|performed|executed"
)
APPLIED_STEP = re.compile(
    r"\b(?:was|were)\s+(?:then\s+|also\s+|first\s+|next\s+|again\s+|subsequently\s+)?"
    r"(?:"
    + APPLIED_STEP_VERBS
    +
    # A step that was planned ("was to perform 60 tests").
    r"|to\s+(?:perform|conduct|run|test))\b",
    re.IGNORECASE,
)
OUTCOME_CUE = re.compile(
    r"\b(?:react\w*|pass(?:ed|es)?|fail\w*|ignit\w*|burn\w*|flam\w*|extinguish\w*|observ\w*"
    r"|shown|show(?:s|ed|ing)?|result\w*|detect\w*|seen|found|produc\w*|exhibit\w*"
    # "performed nominally" judges an outcome; "were performed manually" is a step.
    r"|perform\w*\s+(?:well|poorly|nominally|normally|satisfactorily|adequately|as\s+expected"
    r"|better|worse)"
    r"|increas\w*|decreas\w*|rose|fell|remain\w*|became|occur\w*|spread\w*|grew|shrank|reduc\w*"
    # "trials were run with typical dwell periods near ~250 msec" reports values.
    r"|typical(?:ly)?"
    r"|no\s+(?:reaction|ignition|flash|change)s?|zero)\b",
    re.IGNORECASE,
)
FRONT_MATTER = re.compile(
    r"(?:Available\s+online|Paper\s+ID|Published\s+[A-Z0-9]|doi:|©|Vol\.?\s*[\w]+,\s*No\.)",
    re.IGNORECASE,
)
CAPTION_LINE = re.compile(
    r"^\s*(?:Figure|Fig\.?|Table)\s*[-–—]?\s*\d+\s*[-–—:.]\s*[^\n]*\n\s*\S", re.IGNORECASE
)
CRITERION = ViewPattern(
    re.compile(
        r"\b(?:is|are)\s+said\s+to\b|\bpass/fail\b|\bcriteri(?:on|a)\b"
        r"|\bif\b[^.;]*\b(?:then|is\s+recorded|are\s+recorded|must|shall)\b"
        # "If it extinguished before the end of the drop, it was identified as
        # non-flammable": how an outcome is classified, not an outcome seen.
        r"|\bif\b[^.;]*,\s*(?:it|they|the\s+\w+)\s+(?:was|were|is|are)\s+(?:deemed|identified|considered"
        r"|classified|declared|judged|counted|called|rated)\b"
        # "The limit (black circle) is the highest concentration where ...": a definition.
        r"|^\s*the\s+[\w-]+(?:\s+\([^()]*\))?\s+(?:is|was)\s+(?:defined\s+as\s+)?the\s+(?:highest|lowest"
        r"|maximum|minimum)\b[^.;]*\b(?:where|at\s+which|for\s+which)\b"
        # "The indication of autogenous ignition was the rapid increase of ...":
        # what counts as the event, not an event seen.
        r"|^\s*the\s+indications?\s+of\b[^.;]*?\b(?:was|were|is|are)\s+(?:the|a|an)\b",
        re.IGNORECASE,
    )
)
EXAMINATION_STEP = re.compile(
    r"\b(?:was|were)\s+(?:analy[sz]ed|examined|inspected|checked|evaluated|conducted|performed)"
    r"\s+(?:for|to|by|using|with|at|in|under)\b",
    re.IGNORECASE,
)
INTERPRETIVE_CUE = re.compile(
    r"\b(?:suggest\w*|indicat\w*|conclu\w*|appear\w*|likely|probabl\w*|due\s+to|because"
    r"|therefore|thus|hence|demonstrat\w*|superior|outperform\w*|better|worse|compatib\w*"
    r"|sensitiv\w*|reactiv\w*|perform\w*|safe\w*|recommend\w*|attribut\w*|explain\w*)\b",
    re.IGNORECASE,
)
WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
EVENT = r"(?:react\w*|ignit\w*|fail\w*|burn\w*)"
NEGATED_COUNT = re.compile(
    rf"\b(?:no|zero|none|neither|not\s+any|without\s+any)\b[^.;]*?\b{EVENT}[^.;]*?"
    r"\b(?:out\s+of|of)\s+(?:the\s+)?(?:[a-z]+\s+){0,2}?(\d[\d,]*)\b",
    re.IGNORECASE,
)
POSITIVE_COUNT = re.compile(
    r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:of|out\s+of)\s+(?:the\s+)?"
    rf"(?:[a-z]+\s+){{0,3}}?(\d[\d,]*)\b[^.;]*?\b{EVENT}",
    re.IGNORECASE,
)
ROLE_FAMILY = role_families()


def _body_bounds(text):
    """Page text without a leading or trailing page-number line."""
    begin = re.match(r"\s*\d{1,4}\s*\n", text)
    end = re.search(r"\n\s*\d{1,4}\s*$", text)
    return (begin.end() if begin else 0), (end.start() if end else len(text.rstrip()))


def fragment_context(text, location, evidence):
    """Why a statement is not one whole source sentence, or None.

    ``location`` is the statement's exact original span: evidence_id, start, end.
    """
    if ABBREVIATION_END.search(text.strip()):
        return {"basis": "STATEMENT_ENDS_AT_ABBREVIATION", "quote": text.strip()[-12:]}
    if CAPTION_LINE.match(text) or (caption_reader_enabled() and statement_caption(text)):
        # A figure or table caption line glued to the sentence that follows it.
        return {"basis": "STATEMENT_INCLUDES_A_CAPTION_LINE", "quote": text.strip()[:60]}
    if text.count("\n") >= 3 and FRONT_MATTER.search(text):
        # Journal front matter (byline, placeholders, URL) is not one proposition.
        return {"basis": "STATEMENT_IS_FRONT_MATTER", "quote": text.strip()[:60]}
    page = evidence[location["evidence_id"]]
    begin, end = _body_bounds(page["text"])
    stripped = text.lstrip()
    if stripped[:1].islower() and not re.match(r"(?:pH\b|[a-z][-\d])", stripped):
        # A lower-case start after text that did not end a sentence is the tail
        # of the previous sentence ("temperature  This sought to ...").
        before = page["text"][: location["start"]].rstrip()
        if before and not TERMINAL.search(before) and not re.search(r"\n\s*\d{1,4}\s*$", before):
            return {
                "basis": "STATEMENT_STARTS_MID_SENTENCE",
                "quote": before[-40:] + " | " + stripped[:40],
            }
    pages = [
        p
        for p in evidence.values()
        if p["source_id"] == page["source_id"] and p.get("page") is not None
    ]
    after = [p for p in pages if p.get("page") == (page.get("page") or 0) + 1]
    # A slide bullet may end a page without punctuation; only a word that needs
    # its continuation ("of", "the", a comma), or a next page that resumes in
    # lower case, shows the sentence goes on.
    if after and not TERMINAL.search(text) and not page["text"][location["end"] : end].strip():
        following = after[0]["text"]
        resumed = following[_body_bounds(following)[0] :].lstrip()[:1].islower()
        if CONTINUING_TAIL.search(text) or resumed:
            return {"basis": "SENTENCE_CONTINUES_ON_NEXT_PDF_PAGE", "quote": text.strip()[-60:]}
    before = [p for p in pages if p.get("page") == (page.get("page") or 0) - 1]
    if before and not page["text"][begin : location["start"]].strip():
        previous = before[0]["text"]
        tail = previous[: _body_bounds(previous)[1]].rstrip()
        if CONTINUING_TAIL.search(tail):
            return {"basis": "SENTENCE_STARTS_ON_PREVIOUS_PDF_PAGE", "quote": tail[-60:]}
    return None


def _count(value):
    value = value.lower().replace(",", "")
    return WORD_NUMBERS.get(value, int(value) if value.isdigit() else None)


def count_conflict(location, evidence, window=600):
    """A nearby source sentence giving a non-zero count of the same total.

    "None ... produced a flash in all 45 drops" next to "Three of the
    further 45 Beta foam coupons flashed" is a conflict printed by the source;
    both statements stay for review instead of one being accepted.
    """
    text = evidence[location["evidence_id"]]["text"]
    own = text[location["start"] : location["end"]]
    nearby = text[max(0, location["start"] - window) : location["end"] + window]
    # The counts' windows stop at sentence ends only: found on the masked text, quoted
    # from the printed one.
    own_view, nearby_view = segmentation_view(own), segmentation_view(nearby)
    for negated in NEGATED_COUNT.finditer(own_view):
        total = _count(negated.group(1))
        for positive in POSITIVE_COUNT.finditer(nearby_view):
            if _count(positive.group(2)) == total and (_count(positive.group(1)) or 0) > 0:
                quote = nearby[positive.start() : positive.end()]
                return {"basis": "SOURCE_PRINTS_CONFLICTING_COUNTS", "quote": quote}
    for positive in POSITIVE_COUNT.finditer(own_view):
        if not (_count(positive.group(1)) or 0) > 0:
            continue
        total = _count(positive.group(2))
        for negated in NEGATED_COUNT.finditer(nearby_view):
            if _count(negated.group(1)) == total:
                quote = nearby[negated.start() : negated.end()]
                return {"basis": "SOURCE_PRINTS_CONFLICTING_COUNTS", "quote": quote}
    return None


def observation_cue(text):
    """Whether a passage reports testing or an observed result, not a procedure.

    A purpose clause ("a picture was taken in order to show ...") describes
    what was done, not what was observed.
    """
    return bool(OBSERVATION_CUE.search(text or "")) and not purpose_marked(text)


def purpose_marked(text):
    """Whether a passage carries a marked purpose ("in order to", "so as to"; with
    SCIENCE_PURPOSE_READER, every marked form of the one reader)."""
    import os

    from nasa_fire_ai.ingestion import clause_cues

    if os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
        return bool(clause_cues.purpose_spans(text, forms=("marked",)))
    return bool(PURPOSE.search(text or ""))


def stated_criterion(text):
    """Whether a passage states an acceptance or recording rule."""
    return bool(CRITERION.search(text or ""))


def documentary_pointer(text):
    """Whether a passage only points at where results are printed."""
    return bool(POINTER.search(text or ""))


def rule_or_caveat(text):
    """Whether a passage states a rule, requirement or validity caveat."""
    return bool(RULE_OR_CAVEAT.search(text or ""))


def validity_caveat(text):
    """Whether a passage states the conditions under which a value or comparison holds."""
    return bool(VALIDITY_CAVEAT.search(text or ""))


def step_adverb_enabled():
    return os.getenv("SCIENCE_STEP_ADVERB", "1") != "0"


# SCIENCE_STEP_ADVERB: a manner adverb between the auxiliary and the participle ("was directly
# heated") does not make the clause something other than a step (Quirk et al. 1985, 8.15: adverbs
# of manner and degree in medial position), so the slot takes any -ly adverb, not a list.
APPLIED_STEP_ADVERB = re.compile(
    APPLIED_STEP.pattern.replace(
        r"(?:then\s+|also\s+|first\s+|next\s+|again\s+|subsequently\s+)?",
        r"(?:(?:then|also|first|next|again|subsequently|[a-z]{3,}ly)\s+)?",
    ),
    re.IGNORECASE,
)
# An agent or instrument noun built on an outcome stem ("igniter", "burner", "reactor") names the
# apparatus, not the event (derivational -er / -or, Quirk et al. 1985, App. I.18).
INSTRUMENT_NOUN_END = ("er", "ers", "or", "ors")


def outcome_cue(text, instruments=False):
    """The first outcome word of a passage; with ``instruments`` an apparatus noun is no outcome."""
    for found in OUTCOME_CUE.finditer(text):
        if instruments:
            word = found.group() + re.match(r"\w*", text[found.end() :]).group()
            if word.lower().endswith(INSTRUMENT_NOUN_END):
                continue
        return found
    return None


def procedure_without_outcome(text):
    """Whether a passage only says what was done to the specimens, with no outcome.

    "Each was struck with 60 J at 7,000 kPa" is a test step; it becomes an
    observation only when the passage also reports what happened. The purpose of a
    step ("tuned to lower the casing heat") is not its outcome.
    """
    text = text or ""
    adverbs = step_adverb_enabled()
    steps = list((APPLIED_STEP_ADVERB if adverbs else APPLIED_STEP).finditer(text))
    if not steps:
        return False
    # The purpose right after a step verb is not an outcome, nor is a pointer to
    # where the step is pictured ("As shown in Figure 12, X was adjusted").
    for match in reversed(steps):
        text = text[: match.end()] + STEP_PURPOSE.sub("", text[match.end() :], count=1)
    return not outcome_cue(FIGURE_POINTER.sub("", text), instruments=adverbs)


FIGURE_POINTER = re.compile(
    r"\bas\s+(?:shown|seen|illustrated|plotted|depicted)\s+in\s+(?:Figure|Fig\.?|Table)s?\s*\d+\w*",
    re.IGNORECASE,
)


# "tuned to lower X": the purpose of a step, up to the end of its clause.
# "heated to the point of ignition" and "exposed to flame and burned" keep their
# outcome: a determiner or an outcome word after "to" is not a purpose, and the
# purpose stops at "and" or "but".
import os
import unicodedata

from nasa_fire_ai.ingestion.clause_cues import STEP_PURPOSE
from nasa_fire_ai.ingestion.printed_layout import (
    caption_reader_enabled,
    is_caption_line,
    statement_caption,
)
from nasa_fire_ai.ingestion.scientific_facets import facet_errors
from nasa_fire_ai.ingestion.scientific_proposals import normative_instruction

DETECTION_METHOD = ViewPattern(
    re.compile(
        r"^\s*the\s+detection\s+of\b[^.;]*?\b(?:was|were|is|are)\s+(?:indicated|determined|made|signall?ed)\s+by\b",
        re.IGNORECASE,
    )
)
DATA_PROVENANCE = ViewPattern(
    re.compile(
        r"\b(?:data|results?|values?)\b[^.;]*?\b(?:were|was|are|is)\s+(?:obtained|taken|collected"
        r"|gathered|compiled|drawn|acquired|sourced)\b",
        re.IGNORECASE,
    )
)


DOCUMENTED_OBSERVATION = re.compile(
    r"\b(?:shows?|showed|reveals?|revealed)\s+that\b"
    r"|\bcan(?:not)?\s+be\s+seen\b(?!\s+in\s+(?:Table|Figure|Fig\.?)\b)",
    re.IGNORECASE,
)


def documented_observation(text):
    """Whether a passage reports what a picture or record shows, not where it is."""
    text = text or ""
    return bool(
        DOCUMENTED_OBSERVATION.search(text)
        and re.search(
            r"\b(?:pictures?|photo\w*|images?|micrographs?|figures?|can(?:not)?\s+be\s+seen)\b",
            text,
            re.IGNORECASE,
        )
        and not POINTER.search(text)
    )


def reported_outcome(text):
    """Whether a passage reports what happened, not only what was done, used or sourced.

    "The detection of a reaction was indicated by a photodiode" says how an
    outcome is detected, and "The data ... were obtained by ..." where data came
    from; neither reports an outcome.
    """
    text = text or ""
    return bool(
        OUTCOME_CUE.search(text)
        and not DETECTION_METHOD.search(text)
        and not DATA_PROVENANCE.search(text)
    )


def procedure_without_interpretation(text):
    """Whether a passage only says what was done to or with the specimens.

    "After several series of tests were conducted ..., the samples were
    analyzed for signs of combustion" is a step of the method; it interprets
    nothing.
    """
    text = text or ""
    return bool(
        (
            APPLIED_STEP.search(text)
            or EXAMINATION_STEP.search(text)
            or re.search(
                r"\b(?:was|were)\s+(?:used|employed|started|added|installed)\b", text, re.IGNORECASE
            )
        )
        and not INTERPRETIVE_CUE.search(text)
    )


def _span_groups(records, eligible=None):
    groups = {}
    for record in records:
        if not (eligible or (lambda r: r["status"] == "SOURCE_SUPPORTED"))(record):
            continue
        if record["kind"] == "quantities" and record.get("quantity_value_spans"):
            key = (
                "quantities",
                record.get("subject"),
                tuple(
                    (v["evidence_id"], v["start"], v["end"]) for v in record["quantity_value_spans"]
                ),
            )
            groups.setdefault(key, []).append(record)
        elif record["kind"] == "statements" and record.get("statement_location"):
            located = record["statement_location"]
            key = (located["evidence_id"], located["start"], located["end"])
            groups.setdefault(key, []).append(record)
    return groups


def conflicting_modalities(records):
    """Accepted readings of one source span that disagree on whether it was done (one
    as done, another as proposed, prescribed or conditional): all are held, whatever
    their order, since the span cannot settle which is right."""
    from nasa_fire_ai.ingestion.scientific_facets import facets

    def reading(record):
        # An accepted reading, or one held only because its clause does not
        # settle the facet it claims: it still competes with the other readings.
        return record["status"] == "SOURCE_SUPPORTED" or (
            record["status"] == "UNRESOLVED"
            and bool(record["reasons"])
            and all(r.endswith("_READING_UNCERTAIN_REQUIRES_REVIEW") for r in record["reasons"])
        )

    held = set()
    for members in _span_groups(records, reading).values():
        statuses = {
            (facets(r["kind"], r["proposal"]) or {}).get("execution_status") for r in members
        }
        if len(statuses) > 1:
            held.update(r["id"] for r in members)
    return held


def printed_value_key(record, evidence):
    """SCIENCE_EVIDENCE_VETO_QUANTITIES: where and what a quantity record reads: its subject, the
    printed line(s) of its value spans (current splitter) and the value as printed there, read from
    the evidence at the located span, never from the proposal or the quote. Two trims of one value
    share it; two different values of one sentence do not. The name is not part of it: one printed
    value read under two names is the conflict."""
    from nasa_fire_ai.ingestion.clause_cues import printed_line_bounds

    printed = []
    for v in record["quantity_value_spans"]:
        text = (evidence.get(v["evidence_id"]) or {}).get("text")
        if text is None or not 0 <= v["start"] < v["end"] <= len(text):
            return None
        lo, hi = printed_line_bounds(text, v["start"], v["end"])
        printed.append((v["evidence_id"], lo, hi, re.sub(r"\s+", "", text[v["start"] : v["end"]])))
    return ("quantities", record.get("subject"), tuple(printed))


def conflicting_roles(records, evidence=None):
    """Accepted statements or quantity values on one source span with incompatible roles.

    Returns the ids of the records to hold for review. With ``evidence`` and
    SCIENCE_EVIDENCE_VETO_QUANTITIES a quantity is keyed by `printed_value_key`, not by the exact
    span of its value.
    """
    printed = evidence is not None and os.getenv("SCIENCE_EVIDENCE_VETO_QUANTITIES", "1") != "0"
    groups = {}
    for record in records:
        if record["status"] != "SOURCE_SUPPORTED":
            continue
        if record["kind"] == "quantities" and record.get("quantity_value_spans"):
            # One printed value read both as a set-up input and as a result.
            key = (printed and printed_value_key(record, evidence)) or (
                "quantities",
                record.get("subject"),
                tuple(
                    (v["evidence_id"], v["start"], v["end"]) for v in record["quantity_value_spans"]
                ),
            )
            groups.setdefault(key, []).append(record)
            continue
        if record["kind"] != "statements":
            continue
        located = record.get("statement_location")
        if not located:
            continue
        key = (located["evidence_id"], located["start"], located["end"])
        groups.setdefault(key, []).append(record)
    held = set()
    for members in groups.values():
        families = {
            ROLE_FAMILY.get(r["proposal"]["epistemic"], r["proposal"]["epistemic"]) for r in members
        }
        if len(families) > 1:
            held.update(r["id"] for r in members)
    return held


def role_errors(statement):
    """The errors of the facet review and of every check the statement's role is bound to.

    The checks run in the order of ``ROLE_CHECKS``; ``scientific_facets.ROLES`` says which
    of them each role takes (its ``checks``).
    """
    role = statement["epistemic"]
    errors = facet_errors("statements", statement)
    bound = ROLES[role].checks if role in ROLES else ("multiple_bullets",)
    for name, check in ROLE_CHECKS.items():
        if name in bound:
            errors.extend(check(statement["text"]))
    return errors


def _open_question_explicit(text):
    open_cue = r"\?|\b(?:unknown|unclear|uncertain|unresolved|open\s+question|not\s+(?:yet\s+)?(?:known|understood|clear)|remains?\s+to\s+be)\b"
    if not re.search(open_cue, text, re.IGNORECASE):
        return ["OPEN_QUESTION_NOT_EXPLICIT_IN_SOURCE"]
    return []


def _guidance_explicit(text):
    if os.getenv("SCIENCE_MODAL_29148", "1") == "1":
        # ISO/IEC/IEEE 29148: "should" recommends, "may" permits; "can" is capability
        # (ISO/IEC Directives Part 2), never guidance.
        from nasa_fire_ai.ingestion import clause_cues

        guided = (
            clause_cues.RECOMMENDATION.search(text)
            or re.search(r"^(?:Use|Avoid|Ensure|Keep|Do not)\b", text)
            or clause_cues.permission(text)
        )
    else:
        guided = re.search(
            r"\b(?:recommend\w*|advis\w*|guidance|should)\b|^(?:Use|Avoid|Ensure|Keep|Do not)\b"
            # A permission is guidance ("may", ISO/IEC/IEEE 29148; NASA Systems Engineering
            # Handbook): "may be applied", "is permitted".
            r"|\b(?:may|can)\s+be\s+(?:used|applied|employed)\b|\b(?:is|are)\s+permitted\b",
            text,
            re.IGNORECASE,
        )
    return [] if guided else ["GUIDANCE_NOT_EXPLICIT_IN_SOURCE"]


def _normative_explicit(text):
    if os.getenv("SCIENCE_RECORDING_RULE", "1") == "1":
        from nasa_fire_ai.ingestion import clause_cues

        stated_rule = re.search(
            r"\b(?:required|requires?|mandatory)\b|^(?:Record|Measure|Maintain|Ensure|Use|Avoid|Do not|Keep|Verify)\b",
            text,
            re.IGNORECASE,
        ) or clause_cues.recording_rule(text)
    else:
        stated_rule = re.search(
            r"\b(?:required|requires?|mandatory)\b|^(?:Record|Measure|Maintain|Ensure|Use|Avoid|Do not|Keep|Verify)\b"
            # An explicit conditional recording rule: "If X, then Y is recorded as Z".
            r"|\bif\b[^.;]*\bthen\b[^.;]*\b(?:is|are)\s+(?:recorded|reported|classified|considered)\s+as\b",
            segmentation_view(text),
            re.IGNORECASE,
        )
    if not normative_instruction(text) and not stated_rule:
        return ["NORMATIVE_ROLE_NOT_EXPLICIT_IN_SOURCE"]
    return []


def _observation_must_be(text):
    if re.search(r"\bmust\s+be\b", text, re.IGNORECASE) and not normative_instruction(text):
        return ["SCIENTIFIC_INFERENCE_IS_NOT_OBSERVATION"]
    return []


def _observed_or_concluded_claims(text):
    errors = []
    if normative_instruction(text):
        errors.append("NORMATIVE_IS_NOT_OBSERVATION")
    # "To make sure the lamp starts, a spare cap was added": the
    # purpose of a step is not a plan or a counterfactual result.
    if os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
        from nasa_fire_ai.ingestion import clause_cues

        unpurposed = clause_cues.strip_purpose(text)
    else:
        unpurposed = text
        for found in reversed(
            list(
                re.finditer(
                    r"\b(?:in\s+order\s+to|so\s+that|so\s+as\s+to|to\s+(?:assure|ensure|insure)\s+that)\b[^,;.]*",
                    segmentation_view(text),
                    re.IGNORECASE,
                )
            )
        ):
            unpurposed = unpurposed[: found.start()] + unpurposed[found.end() :]
    if re.search(r"\b(?:will|would|planned|proposed|future\s+work)\b", unpurposed, re.IGNORECASE):
        errors.append("PLANNED_OR_COUNTERFACTUAL_IS_NOT_OBSERVATION")
    if re.search(r"\b(?:goals?|objectives?|aims?)\s+(?:is\s+|are\s+)?to\b", text, re.IGNORECASE):
        errors.append("SOURCE_GOAL_IS_NOT_ESTABLISHED_RESULT")
    if re.search(
        r"\b(?:may|might|hypothes\w*|likely|possibly|not\s+clear|suggest\w*|(?:seem|appear)(?:s|ed)?\s+to)\b",
        text,
        re.IGNORECASE,
    ):
        errors.append("UNCERTAINTY_CANNOT_BECOME_CONFIRMED")
    return errors


def _observation_inferred(text):
    errors = []
    if re.search(r"\b(?:thus|hence|thereby|therefore)\s+indicat\w*\b", text, re.IGNORECASE):
        errors.append("INFERRED_INTERPRETATION_IS_NOT_DIRECT_OBSERVATION")
    if re.search(
        r"\b(?:model|simulation|analysis|prediction)\s+(?:confirmed|showed|shows|indicated|predicts|predicted|found)\b",
        text,
        re.IGNORECASE,
    ):
        errors.append("MODEL_RESULT_IS_NOT_DIRECT_OBSERVATION")
    return errors


def _multiple_bullets(text):
    if len(re.findall(r"(?m)^\s*[•●▪◦]", text)) > 1:
        return ["MULTIPLE_BULLETS_REQUIRE_SEPARATE_EPISTEMIC_REVIEW"]
    return []


def _observation_layout(text):
    errors = []
    lines = [line.strip() for line in text.splitlines() if line.strip() not in {"", "•"}]
    symbolic_lines = sum(
        bool(re.fullmatch(r"[A-Za-zΑ-ω_]{1,6}", unicodedata.normalize("NFKC", line)))
        and (
            unicodedata.normalize("NFKC", line) != line
            or "_" in line
            or (len(line) == 1 and line.lower() not in {"a", "i"})
        )
        for line in lines
    )
    if (
        len(lines) >= 3
        and symbolic_lines >= 2
        and not re.search(r"\d", text)
        and all(len(re.findall(r"[A-Za-z]{3,}", line)) <= 1 for line in lines)
    ):
        errors.append("FIGURE_LABEL_BLOCK_IS_NOT_OBSERVATION")
    if (
        len(lines) == 1
        and is_caption_line(lines[0])
        and not OUTCOME_CUE.search(lines[0])
    ):
        # "Figure 8 - Pre-Impact Functional Test" names what a figure shows; it
        # reports no outcome of its own.
        errors.append("FIGURE_CAPTION_IS_NOT_OBSERVATION")
    if re.search(
        r"\b(?:therefore|hence|thus|so)\b.*\b(?:approximat\w*|infer\w*|assum\w*)\b",
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        errors.append("INFERRED_APPROXIMATION_IS_NOT_DIRECT_OBSERVATION")
    return errors


def _observation_derived(text):
    errors = []
    observation_text = text
    if re.search(
        r"\b(?:burned|burning|measured|tests?\s+(?:performed|conducted))\b", text, re.IGNORECASE
    ):
        observation_text = re.sub(
            r"\bsimulated\s+(?:[\w-]+\s+){0,3}gravity\b",
            "physical analog gravity",
            text,
            flags=re.IGNORECASE,
        )
    if re.search(
        r"\b(?:simulat\w*|predict\w*|numerical\s+(?:model|result)|calculated|computed|estimated|assumed|derived|derivative|(?:best|linear|quadratic|regression|curve|polynomial|least[- ]squares)\s+fits?)\b",
        observation_text,
        re.IGNORECASE,
    ):
        errors.append("DERIVED_IS_NOT_OBSERVATION")
    if re.search(
        r"\b(?:relationship|model|analysis|prediction)\s+(?:is|was|are|were)\s+(?:compared|validated)\b",
        text,
        re.IGNORECASE,
    ):
        errors.append("COMPARISON_METHOD_IS_NOT_MEASURED_OBSERVATION")
    if re.search(
        r"\b(?:measured|obtained|determined|estimated)\s+(?:using|from|via)\b[^\n]*\bcorrelations?\b",
        text,
        re.IGNORECASE,
    ):
        errors.append("CORRELATION_ESTIMATE_IS_NOT_DIRECT_OBSERVATION")
    return errors


def _configuration_objective(text):
    if (
        re.search(r"\bObjectives?\s*\n", text, re.IGNORECASE)
        and re.search(r"\b(?:Demonstrate|Obtain|Determine|Develop)\b", text)
        and not re.search(
            r"\b(?:was|were|conducted|performed|maintained|installed)\b", text, re.IGNORECASE
        )
    ):
        return ["SOURCE_OBJECTIVE_IS_NOT_ESTABLISHED_CONFIGURATION"]
    return []


# The structural checks a role may be bound to (``Role.checks``), in the order they run.
ROLE_CHECKS = {
    "open_question_explicit": _open_question_explicit,
    "guidance_explicit": _guidance_explicit,
    "normative_explicit": _normative_explicit,
    "observation_must_be": _observation_must_be,
    "observed_or_concluded_claims": _observed_or_concluded_claims,
    "observation_inferred": _observation_inferred,
    "multiple_bullets": _multiple_bullets,
    "observation_layout": _observation_layout,
    "observation_derived": _observation_derived,
    "configuration_objective": _configuration_objective,
}


# --- Instrument set-up read as an observation (SCIENCE_INSTRUMENT_OBSERVATION) -------------
# The measuring system is method, not result (JCGM 200:2012, VIM 3.2 and 3.3). A clause whose
# only outcome word is a verb of perceiving or recording (Levin 1993, ch. 30 "verbs of perception";
# recording verbs, ch. 25 verbs of image creation) and which names the instrument it was done with
# says how the run was watched, not what happened. An event nominal as the thing observed, or a
# complement that reports it ("observed to ignite", "observed that"), is an outcome.
PERCEPTION_RECORDING_FORM = re.compile(
    r"\b(?:observ|view|watch|film|record|photograph|imag|captur|monitor|track|log|video(?:tap)?|scann?)"
    r"(?:ed|ing)\b",
    re.IGNORECASE,
)
INSTRUMENT_COMPLEMENT = re.compile(
    r"\b(?:observ|view|watch|film|record|photograph|imag|captur|monitor|track|log|video(?:tap)?|scann?)"
    r"ed\s+(?:\w+ly\s+)?(?:with|using|by\s+means\s+of|via)\b",
    re.IGNORECASE,
)
EVENT_NOMINAL = re.compile(r"\b\w{3,}(?:ing|ion|ions|ence|ance|ment)\b", re.IGNORECASE)


def instrument_observation_enabled():
    return os.getenv("SCIENCE_INSTRUMENT_OBSERVATION", "1") != "0"


def instrument_setup(text):
    """Whether a passage only says that something was watched or recorded with an instrument."""
    text = FIGURE_POINTER.sub("", text or "")
    match = INSTRUMENT_COMPLEMENT.search(text)
    if not match:
        return False
    cues = [m.group() for m in OUTCOME_CUE.finditer(text)]
    if any(not PERCEPTION_RECORDING_FORM.fullmatch(c) for c in cues):
        return False
    before, after = text[: match.start()], text[match.end() :]
    # The subject names the thing watched; an event nominal there is the outcome itself.
    subject = re.sub(r"\b(?:was|were|is|are|been|being)\s*$", "", before.strip())
    return (
        not EVENT_NOMINAL.search(subject)
        and not re.search(
            r"\b(?:that|to\s+\w+|burning|igniting|spreading|extinguishing)\b", after, re.IGNORECASE
        )
        or False
    )


# --- A documentary statement that reports an activity (SCIENCE_DOCUMENTARY_ACTIVITY) -------------
# Documentary context only says what the document is or points to. A main clause in the progressive
# ("has been procuring", "is building"; auxiliary be or have been plus an -ing form, Quirk et al.
# 1985, 4.27-4.28) reports an activity of the work under way, which is not documentary. A pointer
# to a figure, table or section is not an agent's activity and is never held.
PROGRESSIVE = re.compile(
    r"\b(?:am|is|are|was|were|(?:has|have|had)\s+been)\s+(?:[a-z]{3,}ly\s+){0,2}[a-z]{3,}ing\b",
    re.IGNORECASE,
)
DOCUMENT_POINTER_START = re.compile(
    r"^\s*(?:figures?|fig\.?|tables?|sections?|chapters?|appendi(?:x|ces)|pages?|slides?)\b",
    re.IGNORECASE,
)
PARTICIPIAL_ADJECTIVE = frozenset(
    {"following", "interesting", "promising", "surprising", "remaining", "missing", "existing"}
)


def progressive_clause(text):
    """Whether the governing clause of a passage is progressive (be or have been plus -ing)."""
    from nasa_fire_ai.ingestion import clause_cues

    clause = clause_cues.governing_clause(re.sub(r"\s*\n\s*", " ", text or ""))
    return any(
        found.group().split()[-1].lower() not in PARTICIPIAL_ADJECTIVE
        for found in PROGRESSIVE.finditer(clause)
    )


def documentary_activity_enabled():
    return os.getenv("SCIENCE_DOCUMENTARY_ACTIVITY", "1") != "0"


def documentary_activity(text, previous=None):
    """Whether a documentary statement's main clause reports an activity under way."""
    if DOCUMENT_POINTER_START.match(text or ""):
        return False

    return progressive_clause(text)


# --- A request is not an execution (SCIENCE_DIRECTIVE_EXECUTION) --------------------------------
# "The vendor was asked to test the cord": a governing verb of ordering, requesting, tasking or
# requiring that takes an infinitive complement (Levin 1993, English Verb Classes and
# Alternations, ch. 37 (verbs of communication); membership to verify before the freeze) says
# what was to be done, not that it was done. The frame constrains the axes
# only: a record that states the run as executed (an executed role, no stated modality) and whose
# only support is that complement, with no separate clause reporting completion, is held. The
# frame never picks a role.
DIRECTIVE = re.compile(
    r"\b(?:was|were|is|are|been|being)\s+(?:[a-z]{3,}ly\s+)?(?:requested|asked|tasked|instructed"
    r"|directed|required|ordered|told|commanded)\s+to\s+[a-z]+"
    r"|\b(?:request(?:s|ed)?|ask(?:s|ed)?|task(?:s|ed)?|instruct(?:s|ed)?|direct(?:s|ed)?"
    r"|order(?:s|ed)?|command(?:s|ed)?)\s+(?:the\s+|an?\s+)[a-z-]+\s+to\s+[a-z]+",
    re.IGNORECASE,
)
COMPLETION = re.compile(
    r"\b(?:was|were|has\s+been|have\s+been)\s+(?:then\s+|later\s+)?(?:completed|finished|done"
    r"|carried\s+out|accomplished)\b|\b(?:completed|finished|accomplished)\b",
    re.IGNORECASE,
)


def directive_execution_enabled():
    return os.getenv("SCIENCE_DIRECTIVE_EXECUTION", "0") == "1"


def directive_not_executed(text, previous=None, context=None):
    """Whether a record that claims execution rests on a directive and nothing reports completion."""
    from nasa_fire_ai.ingestion.scientific_facets import stated_modality

    item = (context or {}).get("item") or {}
    if stated_modality(item):
        return False  # the record itself says it was intended, proposed or prescribed
    return bool(DIRECTIVE.search(text or "") and not COMPLETION.search(text or ""))


# --- A clause qualifier the record drops (SCIENCE_QUALIFIER_CHECK) -------------------------------
# A negation, a hedge or a condition in the clause that governs a statement, printed outside the
# words the record kept, is dropped when the record states an unqualified role: a hedged clause
# kept as an unhedged conclusion, a negated clause kept as an observation of the opposite, a
# conditional kept as a plain setting. The printed clause is read, not the model's quote.
NEGATION = re.compile(r"\b(?:not|no|never|neither|nor|none|cannot|without)\b|n't\b", re.IGNORECASE)


def qualifier_check_enabled():
    return os.getenv("SCIENCE_QUALIFIER_CHECK", "0") == "1"


def qualifiers_dropped(text, previous=None, context=None):
    """Whether the printed clause carries a negation, hedge or condition the statement lacks."""
    from nasa_fire_ai.ingestion import clause_cues
    from nasa_fire_ai.ingestion.scientific_facets import stated_modality

    clause = (context or {}).get("clause", lambda: "")()
    if not clause:
        return False
    stated = stated_modality((context or {}).get("item") or {})
    kept = text or ""
    if NEGATION.search(clause) and not NEGATION.search(kept):
        return True
    if not stated:
        if clause_cues.EPISTEMIC.search(clause) and not clause_cues.EPISTEMIC.search(kept):
            return True
        if clause_cues.CONDITION.match(clause) and not clause_cues.CONDITION.match(kept):
            return True
    return False


def value_qualifier_dropped(clause, item):
    """Whether the clause of a value prints a hedge or a condition its record does not state."""
    from nasa_fire_ai.ingestion import clause_cues
    from nasa_fire_ai.ingestion.scientific_facets import stated_modality

    if stated_modality(item):
        return False
    return bool(
        clause_cues.EPISTEMIC.search(clause or "") or clause_cues.CONDITION.match(clause or "")
    )


# The checks that hold a statement for review (``Role.holds``): name -> (test, reason, enabled).
HOLD_CHECKS = {
    "instrument_setup": (
        lambda text, previous, context: instrument_setup(text),
        "OBSERVATION_DESCRIBES_A_PROCEDURE",
        instrument_observation_enabled,
    ),
    "documentary_activity": (
        lambda text, previous, context: documentary_activity(text),
        "DOCUMENTARY_DESCRIBES_AN_ACTIVITY",
        documentary_activity_enabled,
    ),
    "directive_not_executed": (
        directive_not_executed,
        "EXECUTION_NOT_SUPPORTED_BY_DIRECTIVE",
        directive_execution_enabled,
    ),
    "qualifiers_preserved": (
        qualifiers_dropped,
        "QUALIFIER_DROPPED_FROM_CLAUSE",
        qualifier_check_enabled,
    ),
}
