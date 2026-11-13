"""What a printed sentence says about one value or assertion, read from its governing clause.

Every facet check (plan, goal, criterion, not-done, modality) asks the same few
questions of the sentence that prints a value or a statement. This module answers
them in one place, by structure rather than by a growing list of phrases:

1. Discourse frames ("it should be noted that", "note that") and purpose clauses
   ("in order to ...", "so that ...", "to determine ...") are removed; they never
   carry the assertion's own tense or modality.
2. The sentence is cut into clauses (at semicolons, line breaks and coordinating
   commas); the governing clause is the one that holds the value's printed offset,
   or the main clause when no offset is given. A subordinate condition ("If X,")
   travels with the main clause it conditions.
3. The verb group of that clause is read: past, present, future or planned,
   normative modal, or epistemic modal ("must have", "may").

Each reading returns ``"uncertain"`` when the clause does not settle the question;
callers hold such a record for review (neither published nor rejected).
"""

import os
import re

from nasa_fire_ai.ingestion.abbreviations import (
    MASK,
    POINTER_ABBREVIATIONS,
    segmentation_view,
)
from nasa_fire_ai.ingestion.source_spans import normalized

DISCOURSE_FRAME = re.compile(
    r"\b(?:it\s+(?:should|must|is\s+worth|may)\s+be\s+(?:noted|emphasi[sz]ed|stressed|"
    r"remembered|recalled)\s+that|(?:please\s+)?note\s+that|as\s+(?:should|might|could|would)\s+"
    r"be\s+expected|as\s+(?:planned|proposed|scheduled|intended|expected))\b,?",
    re.IGNORECASE,
)
PURPOSE = re.compile(
    r"\b(?:in\s+order\s+to|so\s+as\s+to|so\s+that|to\s+(?:assure|ensure|insure)\s+that)\b[^,;.\n]*"
    r"|(?:^|,\s*)to\s+(?:determine|evaluate|assess|verify|confirm|check|measure|ensure|establish|"
    r"characteri[sz]e|quantify|identify|demonstrate)\b[^,;.\n]*",
    re.IGNORECASE,
)
CLAUSE_BREAK = re.compile(
    r";|\n|(?<=[.!?])\s+(?=[A-Z(])|"
    r",\s+(?=(?:and|but|while|whereas|although|though|which|where)\b)|"
    r",\s+(?=the\s+\w+\s+(?:proposed|planned|recommended)\b)",
    re.IGNORECASE,
)

EPISTEMIC = re.compile(
    r"\b(?:must|should|may|might|could|would)\s+have\b|\b(?:may|might)\b", re.IGNORECASE
)
NORMATIVE = re.compile(
    r"\b(?:shall|must|should)\b(?!\s+have\b)|\b(?:is|are)\s+required\s+to\b|"
    r"\b(?:is|are)\s+not\s+(?:to|allowed\s+to)\b",
    re.IGNORECASE,
)
FUTURE = re.compile(
    r"\bwill\b|\b(?:is|are)\s+(?:going|scheduled|expected|planned|due)\s+to\b|"
    r"\b(?:is|are)\s+to\s+be\b|\bplans?\s+to\b|\bwould\b[^.;]*\bif\b|\bif\b[^.;]*\bwould\b|"
    r"\b(?:future|upcoming|next)\s+(?:test|tests|series|run|runs|phase|campaign|year)\b",
    re.IGNORECASE,
)
CONDITION = re.compile(r"^\s*(?:if|unless|when|whenever|should\s+\w+\s+\w+)\b", re.IGNORECASE)
PAST = re.compile(
    r"\b(?:was|were|had\s+been|has\s+been|have\s+been)\b|\b(?:\w{3,}ed|burned|burnt|held|ran|took|"
    r"grew|fell|rose|kept|lost|showed|shown|made|set|began|began|became|did)\b",
    re.IGNORECASE,
)


PLANNING = re.compile(r"\b(?:planned|proposed|scheduled|intended|anticipated)\b", re.IGNORECASE)


SENTENCE_BREAK = re.compile(r"\n|(?<=[.!?])\s+(?=[A-Z(])")


def printed_line_bounds(text, start, end):
    """(start, end) of the printed line(s) the span ``[start, end)`` of ``text`` touches.

    A printed line is the piece between two cuts of SENTENCE_BREAK (a line break or a sentence
    end) on the segmentation view; there is no de-wrap layer, so a sentence wrapped over two
    printed lines is two lines. A span that touches several lines gives the union of them."""
    first, last, begin = None, None, 0
    probe = max(start, end - 1)
    for cut in SENTENCE_BREAK.finditer(segmentation_view(text)):
        if first is None and cut.start() >= start:
            first = begin
        if cut.start() >= probe:
            last = cut.start()
            break
        begin = cut.end()
    if first is None:
        first = begin
    return min(first, start), max(len(text) if last is None else last, end)


def locate_value(text, expression):
    """The offset of a printed value in ``text``: its first number, whole (``5`` is
    not inside ``15`` or ``2025``), with thousands separators normalized; ``None``
    when it is not printed there."""
    number = re.search(r"\d+(?:[.,]\d+)*", expression or "")
    if not number:
        return None
    digits = number.group().replace(",", "")
    for match in re.finditer(r"(?<![\d.,])\d+(?:[.,]\d+)*(?![\d])", text or ""):
        if match.group().replace(",", "") == digits:
            return match.start()
    return None


def strip_frames(sentence):
    """The sentence without discourse frames and purpose clauses."""
    text = DISCOURSE_FRAME.sub(" ", sentence or "")
    if os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
        return strip_purpose(text)
    view = segmentation_view(text)
    if view is not text:
        # Windows stop at sentence-ending periods only: found on the masked text, cut from
        # the printed one.
        for found in reversed(list(PURPOSE.finditer(view))):
            text = text[: found.start()] + " " + text[found.end() :]
        return text
    return PURPOSE.sub(" ", text)


def clauses(sentence):
    """(start, end, text) of each clause of the framed sentence, in order."""
    text = sentence or ""
    pieces, start = [], 0
    for cut in CLAUSE_BREAK.finditer(segmentation_view(text)):
        pieces.append((start, cut.start(), text[start : cut.start()]))
        start = cut.end()
    pieces.append((start, len(text), text[start:]))
    # A leading condition ("If ignition fails,") belongs to the clause it conditions.
    merged = []
    for piece in pieces:
        if merged and CONDITION.match(merged[-1][2]) and "," not in merged[-1][2].strip(" ,"):
            last = merged.pop()
            piece = (last[0], piece[1], last[2] + ", " + piece[2])
        merged.append(piece)
    return [p for p in merged if p[2].strip()]


def governing_clause(sentence, offset=None):
    """The clause that holds ``offset`` (a character position in ``sentence``), or the
    first clause that carries a verb when no offset is given; frames and purpose
    clauses removed."""
    parts = clauses(sentence)
    if not parts:
        return ""
    if offset is not None:
        for start, end, text in parts:
            if start <= offset <= end:
                return strip_frames(text)
        return ""
    for _start, _end, text in parts:
        clean = strip_frames(text)
        if PAST.search(clean) or FUTURE.search(clean) or NORMATIVE.search(clean):
            return clean
    return strip_frames(parts[0][2])


def execution(sentence, offset=None):
    """``"executed"``, ``"not_done"`` (future, planned, conditional or prescribed) or
    ``"uncertain"``, from the governing clause's verb group."""
    clause = governing_clause(sentence, offset)
    if not clause.strip():
        return "uncertain"
    clause = segmentation_view(clause)
    if os.getenv("SCIENCE_MODAL_29148", "1") == "1" and PERMISSION.search(clause):
        # A permission, like a requirement, prescribes: nothing was done.
        return "not_done"
    if EPISTEMIC.search(clause):
        return "uncertain"
    if FUTURE.search(clause) or NORMATIVE.search(clause):
        return "not_done"
    if CONDITION.match(clause):
        # Read from the clause the condition governs: in the past it was carried
        # out where the condition held; in the present it is a standing rule.
        governed = clause.split(",", 1)[1] if "," in clause else ""
        # A present passive ("is recorded") is the rule's tense, not a past one.
        governed = re.sub(r"\b(?:is|are|be)\s+\w+", " ", governed, flags=re.IGNORECASE)
        return "executed" if PAST.search(governed) else "uncertain"
    # A planning participle ("the planned series", "proposed pressure") names a plan;
    # it is not the clause's past verb.
    if PAST.search(PLANNING.sub(" ", clause)):
        return "executed"
    if PLANNING.search(clause):
        return "not_done"
    return "uncertain"


# A criterion is stated by a normative modal over a test or design outcome, or by a
# nominal frame that defines what passes, fails or is allowed.
CRITERION_FRAME = re.compile(
    r"\b(?:acceptance|pass(?:fail)?|fail(?:ure)?|test|design|qualification)\s+"
    r"(?:criterion|criteria|limit|requirement)s?\s*(?::|\b(?:is|was|are|were)\b)|"
    # Defined in the present after a qualifying phrase: "the X criterion for Y is
    # set by ...".
    r"\b(?:acceptance|pass(?:fail)?|fail(?:ure)?|test|design|qualification)\s+"
    r"(?:criterion|criteria|limit|requirement)s?\b[^.;]*?\b(?:is|are)\s+"
    r"(?:set|defined|determined|based|given|established|specified)\b|"
    r"\bthe\s+requirement\s+(?:is|was)\s+that\b|"
    r"\b(?:maximum|minimum)\s+allowable\b|\ballowable\b[^.;]*\b(?:is|was)\b|"
    r"\b\w+\s+limit\s+(?:is|was)\b|"
    r"\bconstitutes?\s+(?:a\s+)?(?:failure|pass)\b|"
    r"\b(?:fails?|passes)\s+the\s+test\b|"
    r"\b(?:passes|fails)\s+(?:if|when|unless)\b|"
    r"\bshall\s+be\s+(?:rejected|accepted)\b|"
    # A recording rule: a condition, then how the result is recorded ("if the sample
    # does not ignite, the result is recorded as a pass").
    r"\bif\b[^.;]*?\b(?:is|are)\s+(?:recorded|reported|scored|counted|rated|taken)\s+as\b",
    re.IGNORECASE,
)
# The same frame without its own recording copy: SCIENCE_RECORDING_RULE reads RECORDING_RULE.
_RECORDING_COPY = (
    r"|\bif\b[^.;]*?\b(?:is|are)\s+(?:recorded|reported|scored|counted|rated|taken)\s+as\b"
)
assert CRITERION_FRAME.pattern.endswith(_RECORDING_COPY)
CRITERION_FRAME_BASE = re.compile(CRITERION_FRAME.pattern[: -len(_RECORDING_COPY)], re.IGNORECASE)
# A participle after a present auxiliary is a present passive ("is recorded"), not a
# past event.
PRESENT_PASSIVE = re.compile(r"\b(?:is|are|be)\s+(?:not\s+)?\w{3,}ed\b", re.IGNORECASE)
# The criterion's existence is negated: "without a pass/fail criterion", "no criterion
# was defined", "the acceptance criterion is not stated / unknown".
CRITERION_ABSENT = re.compile(
    r"\b(?:without|no|not\s+(?:\w+\s+){0,3}?against)\s+(?:an?\s+|any\s+)?(?:\w+\s+){0,2}"
    r"criteri(?:on|a)\b|"
    r"\bcriteri(?:on|a)\s+(?:is|are|was|were)\s+(?:not\s+(?:stated|defined|given|specified|"
    r"known|available)|unknown|unspecified|undefined)\b",
    re.IGNORECASE,
)
# A result reported about a criterion is not a criterion ("are met by all panels").
CRITERION_RESULT = re.compile(
    r"\b(?:criteri(?:on|a)|requirements?)\s+(?:is|are|was|were)\s+(?:met|satisfied|exceeded|"
    r"achieved|passed)\b|\b(?:is|are|was|were)\s+acceptable\s*\.?\s*$",
    re.IGNORECASE,
)
OUTCOME_NOUN = re.compile(
    r"\b(?:pass\w*|fail\w*|accept\w*|reject\w*|exceed|limit\w*|allowable|self-extinguish\w*|"
    r"below|above|within|under|over|less|more|greater|lower|higher|maximum|minimum)\b|[<>≤≥]",
    re.IGNORECASE,
)


def _normalize_pass_fail(text):
    return re.sub(
        r"\bpass\s*(?:/|-|\s+or\s+)\s*fail\b", "passfail", text or "", flags=re.IGNORECASE
    )


def criterion(sentence):
    """``"criterion"``, ``"not_criterion"`` or ``"uncertain"``.

    A criterion needs a normative modal governing an outcome or limit ("shall
    self-extinguish within 10 s", "must not exceed 50 kPa"), or a nominal criterion
    frame ("acceptance criterion: ...", "the wall temperature limit is 40 C",
    "fails the test"). A negated criterion, a result about a criterion and a
    past-tense measured extreme are not criteria.
    """
    text = segmentation_view(_normalize_pass_fail(strip_frames(sentence)))
    if CRITERION_ABSENT.search(text) or CRITERION_RESULT.search(text):
        return "not_criterion"
    clause = governing_clause(text)
    if EPISTEMIC.search(clause):
        return "not_criterion"
    if os.getenv("SCIENCE_RECORDING_RULE", "1") == "1":
        framed = CRITERION_FRAME_BASE.search(text) or recording_rule(text)
    else:
        framed = CRITERION_FRAME.search(text)
    if framed:
        return "criterion"
    if NORMATIVE.search(clause) and OUTCOME_NOUN.search(clause):
        return "criterion"
    if PAST.search(PRESENT_PASSIVE.sub(" ", clause)) and not NORMATIVE.search(clause):
        return "not_criterion"
    return "uncertain"


def plan(sentence):
    """``"plan"``, ``"not_plan"`` (done, or "as planned") or ``"uncertain"``."""
    if re.search(
        r"\b(?:no|not)\s+(?:\w+\s+){0,2}(?:are|is)\s+planned\b", sentence or "", re.IGNORECASE
    ):
        return "not_plan"
    reading = execution(sentence)
    clause = segmentation_view(governing_clause(sentence))
    if reading == "not_done" and (FUTURE.search(clause) or PLANNING.search(clause)):
        return "plan"
    if reading == "executed":
        return "not_plan"
    return "uncertain"


GOAL = re.compile(
    r"\b(?:goals?|objectives?|aims?|purpose)\s+(?:of\s+[^.;]*?\s+)?(?:is|are|was|were)\s+to\b|"
    r"\b(?:goals?|objectives?|aims?)\s*:|\b(?:seek(?:s|ing)?|aims?|intends?|sets?\s+out)\s+to\b|"
    r"\btargets?\s+(?:is|are|was|were)\b|"
    # A goal noun that opens its own infinitive, as a heading or a list item.
    r"^[\W\d]*(?:goals?|objectives?|aims?)\s+to\b",
    re.IGNORECASE,
)


# A goal word outside a goal frame ("the aim of the run was met") names a goal
# without stating it.
GOAL_WORD = re.compile(
    r"\b(?:goals?|objectives?|aims?|purpose|intend\w*|seeks?|targets?)\b", re.IGNORECASE
)


# "a test series to assess ...": a purpose that may be the study's goal.
PURPOSE_INFINITIVE = re.compile(
    r"\bto\s+(?:determine|evaluate|assess|verify|confirm|measure|establish|characteri[sz]e|"
    r"quantify|identify|demonstrate|investigate|develop|understand)\b",
    re.IGNORECASE,
)


def goal(sentence):
    """``"goal"`` when a goal frame states one, ``"uncertain"`` when a goal word
    appears outside a frame, ``"not_goal"`` otherwise."""
    sentence = segmentation_view(sentence or "")
    if GOAL.search(sentence):
        return "goal"
    named = GOAL_WORD.search(sentence) or PURPOSE_INFINITIVE.search(sentence)
    return "uncertain" if named else "not_goal"


# --- Recording rule (SCIENCE_RECORDING_RULE) ------------------------------------------
# On by default after its replay passed; SCIENCE_RECORDING_RULE=0 turns it off.
# A decision rule (ISO/IEC 17025:2017, 3.7 and 7.8.6): a condition, then, in the main
# clause, a present passive of any past participle followed by "as" and a category, the marked predicative
# complement (Huddleston and Pullum 2002, ch. 4, complements; section to verify). No verb
# list: the participle is an -ed form or an irregular participle of this module.
_RECORDING_CONDITION = re.compile(r"\b(?:if|unless)\b[^.;]*?(?:,|\bthen\b)", re.IGNORECASE)
_RECORDING_PREDICATE = re.compile(r"\b(?:is|are)\s+(?:not\s+)?([^\W\d_]+)\s+as\b", re.IGNORECASE)


# A recording rule assigns a category ("as a pass", "as void"). A numeric complement ("as
# 0.9", "as 5 mm", "as T = 300") is an assumed or default value, not a classification;
# an inequality ("as >610 C") names an interval, a class of results, and is one. The
# numeric reading is numeric_expressions.source_numeric_matches, not a new pattern.
_SYMBOL_PREFIX = re.compile(r"[\s~≈±+\-−]*(?:[A-Za-z]\w*\s*=\s*)?")


def _past_participle(word):
    """-ed forms and the irregular participles only; a bare -en word ("open") is not one."""
    return word in _IRREGULAR_PARTICIPLES or (len(word) > 3 and word.endswith("ed"))


def _numeric_complement(text, start):
    """True when the complement that starts at ``start`` is a number, a number with a unit,
    or a symbol = value (the complement runs to a semicolon, comma or sentence end)."""
    from nasa_fire_ai.ingestion.numeric_expressions import source_numeric_matches

    complement = re.split(r"[;,\n]|\.(?!\d)", text[start:], maxsplit=1)[0].strip()
    found = source_numeric_matches(complement)
    if not found:
        return False
    # The located expression carries its own qualifier (">80", "above 40"): what precedes
    # its first digit must be only a sign, an approximation mark or "symbol =".
    lead = min(found, key=lambda m: m.start())
    digit = lead.start() + re.search(r"\d", lead.group()).start()
    return bool(_SYMBOL_PREFIX.fullmatch(complement[:digit]))


def recording_rule(text):
    text = segmentation_view(text or "")
    for condition in re.finditer(r"\b(?:if|unless)\b", text, re.IGNORECASE):
        found = _RECORDING_CONDITION.match(text, condition.start())
        if not found:
            continue
        stop = re.search(r"[.;]", text[found.end() :])
        end = found.end() + stop.start() if stop else len(text)
        for predicate in _RECORDING_PREDICATE.finditer(text, found.end(), end):
            if _past_participle(predicate.group(1).lower()) and not _numeric_complement(
                text, predicate.end()
            ):
                return True
    return False


# --- Normative modal vocabulary (SCIENCE_MODAL_29148) ---------------------------------
# On by default after its replay passed (it loses textiles statements-21 by design: "can"
# is capability, ISO/IEC/IEEE 29148); SCIENCE_MODAL_29148=0 turns it off.
# ISO/IEC/IEEE 29148 and the NASA Systems Engineering Handbook (NASA/SP-2016-6105 Rev 2,
# appendix C): "shall" a requirement, "should" a recommendation, "may" a permission,
# "will" a statement of fact or intent. ISO/IEC Directives Part 2 (clause 7): "can" is
# possibility and capability, never permission. One dictionary for the validator and
# the request.
PERMISSION = re.compile(
    r"\bmay\s+be\s+(?:used|applied|employed)\b|\b(?:is|are)\s+permitted\b", re.IGNORECASE
)
RECOMMENDATION = re.compile(r"\b(?:recommend\w*|advis\w*|guidance|should)\b", re.IGNORECASE)
NORMATIVE_MODALS = {
    "shall / must": "a requirement: normative_requirement, or a criterion if it states "
    "a pass or fail condition",
    "should": "a goal or recommendation: guidance",
    "may / is permitted": "a permission: guidance, never an executed step",
    "will / is planned": "a fact or an intent about the future: planned_activity or a "
    "value with modality proposed; never a requirement, never done",
    "can": "a capability or a possibility, never a permission: not guidance by itself",
}


def permission(text):
    return bool(PERMISSION.search(text or ""))


# --- Purpose clauses (SCIENCE_PURPOSE_READER) -----------------------------------------
# Purpose adjuncts (Quirk et al. 1985, adverbials of purpose; Huddleston and Pullum 2002,
# purpose adjuncts): a fronted or trailing infinitive of purpose, the marked forms, and a
# participle of aiming. "so that" is a purpose only with a modal; without one it is a
# result clause. A purpose ends with its clause: comma, semicolon, full stop or bullet.
# A purpose also ends before a coordinator ("and", "but"): what follows is a clause of its
# own, as for STEP_PURPOSE.
_CLAUSE = r"(?:(?!\s+(?:and|but)\b)(?:[^,;.\n]|(?<=\d)\.(?=\d)|\n(?![ \t]*(?:[•●▪◦*-]|\n))))*"
# A sentence start, or the start of the clause after a comma or semicolon, past an
# enumerator such as "(a)" or "2.".
_CLAUSE_START = r"(?:^|(?<=[.!?\n,;]))\s*(?:\(?\w{1,2}[.)]\s+)?[^\w\n]*"
# Words that, after "to", start a noun phrase rather than a verb ("to the", "to be"):
# determiners and the pronominal determiners (Huddleston and Pullum 2002, ch. 5,
# determinatives), plus the copula "be" and "date",
# which only heads a noun phrase here ("to date"), listed as an exception, not a class.
_NOT_A_VERB = (
    r"(?:the|a|an|this|that|these|those|its|their|our|his|her|my|your|date|some|each|all|"
    r"what|which|whom|be)\b"
)
# Words of degree or approximation: "to nearly 6 kN" gives a value, not a purpose
# (approximators, a subclass of downtoners: Quirk et al. 1985, ch. 8 on
# adjuncts; Huddleston and Pullum 2002, ch. 6, degree modifiers). Not a closed list in the
# grammars: an enumeration of the common members.
_APPROXIMATOR = (
    r"(?:nearly|approximately|about|around|roughly|almost|approx|virtually|varying|"
    r"various|some|certain)\b"
)
_NOT_A_PURPOSE_VERB = r"(?:" + _NOT_A_VERB + r"|" + _APPROXIMATOR + r")"
PURPOSE_FORMS = {
    "fronted": re.compile(
        r"(?:^|(?<=[.!?\n]))\s*[^\w\n]*to\s+(?!"
        + _NOT_A_PURPOSE_VERB
        + r")[a-z]+\b"
        + _CLAUSE
        + r"(?=,)",
        re.IGNORECASE,
    ),
    "trailing": re.compile(
        r"(?<=,)\s*to\s+(?!" + _NOT_A_PURPOSE_VERB + r")[a-z]+\b" + _CLAUSE, re.IGNORECASE
    ),
    "marked": re.compile(
        r"\b(?:in\s+order\s+(?:to(?!\s+(?:the|an?)\b)|that)|so\s+as\s+to)\b"
        + _CLAUSE
        + r"|"
        + _CLAUSE_START
        + r"to\s+(?:assure|ensure|insure)\s+that\b"
        + _CLAUSE
        + r"|\bso\s+that\b(?="
        + _CLAUSE
        + r"\b(?:can|could|may|might|will|would|shall|should)\b)"
        + _CLAUSE,
        re.IGNORECASE,
    ),
    "participle": re.compile(
        # Not after an auxiliary: "was attempting to hold" is a progressive main verb.
        r"(?<!\bwas\s)(?<!\bwere\s)(?<!\bis\s)(?<!\bare\s)(?<!\bbeen\s)(?<!\bbe\s)"
        r"\b(?:aiming|seeking|intending|striving|attempting)\s+(?:to|for|at)\b" + _CLAUSE,
        re.IGNORECASE,
    ),
    # Verbs of inquiry, what a study sets out to learn: a partial enumeration of the
    # verbs of assessment (Levin 1993, English Verb Classes and Alternations, class 34),
    # the verbs a research aim is stated with (the union of PURPOSE and
    # PURPOSE_INFINITIVE above). Anchored like every infinitive: a purpose stands at a
    # sentence start or after a comma or semicolon. After a control, permission or result
    # verb ("allowed to", "was able to", "was left to", "used to") the infinitive is that
    # verb's complement, never a purpose.
    "inquiry": re.compile(
        _CLAUSE_START
        + r"to\s+(?:assess|characteri[sz]e|check|confirm|demonstrate|determine|develop|"
        r"establish|evaluate|identify|investigate|measure|quantify|understand|verify)\b" + _CLAUSE,
        re.IGNORECASE,
    ),
}


def purpose_spans(text, forms=None):
    """(start, end) of each purpose clause of ``text``, merged, in order."""
    text = segmentation_view(text or "")
    found = sorted(
        (m.start(), m.end())
        for name, rx in PURPOSE_FORMS.items()
        if forms is None or name in forms
        for m in rx.finditer(text)
        if m.end() > m.start()
    )
    merged = []
    for start, end in found:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def strip_purpose(text):
    text = text or ""
    for start, end in reversed(purpose_spans(text)):
        text = text[:start] + " " + text[end:]
    return text


def in_purpose(text, offset):
    return offset is not None and any(a <= offset < b for a, b in purpose_spans(text))


# "tuned to lower X": the purpose right after a step verb, up to the end of its clause
# (moved unchanged from statement_integrity).
STEP_PURPOSE = re.compile(
    r"^\s+to\s+"
    r"(?!(?:the|a|an|its|their|each|this|that|these|those|be|ignition|failure|flame|fire)\b)"
    r"[a-z]+\b[^,.;]*?(?=\s+(?:and|but)\b|[,.;]|$)",
    re.IGNORECASE,
)


# --- The head of the subject of a passive (SCIENCE_PURPOSE_READER) --------------------
# No syntactic parser is installed. The relation "this noun heads the subject of that
# passive" is approximated clause by clause, with closed word classes only and no count
# of words (Huddleston and Pullum 2002, ch. 4 on the subject, ch. 5 on the noun phrase,
# ch. 16 on the passive):
#   1. A sentence splits into clauses at . ! ? ; : , a bullet line, a parenthesis, and
#      before a subordinator or relative word ("which", "that", "because", ...).
#   2. In a clause, the subject of a passive "was/were/is/are [then] <participle>" is the
#      run of words before the auxiliary back to the clause start, a coordinator or
#      another finite verb (an auxiliary or a modal), whichever is nearest.
#   3. Its head is the first noun of the class, with only determiners, numerals and
#      modifiers before it (no preposition: a noun after one sits in a complement), and
#      after it only post-head dependents: "of" or another preposition with its noun
#      phrase, a participle that opens a prepositional phrase ("cut from ..."), or a
#      numbered label. A determiner inside a noun phrase body starts a new phrase, which
#      only a clause can do here, so it breaks the relation.
_TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_][\w'-]*|\n[ \t]*(?:[•●▪◦*-]|\n)|[^\w\s]")
_CLAUSE_PUNCTUATION = {".", "!", "?", ";", ":", ",", "(", ")", "[", "]"}
SUBORDINATORS = frozenset(
    [
        "which",
        "that",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "whenever",
        "while",
        "whereas",
        "because",
        "although",
        "though",
        "if",
        "unless",
        "whether",
        "once",
        "until",
        "since",
        "after",
        "before",
        "as",
        "so",
    ]
)
COORDINATORS = frozenset(["and", "or", "but", "nor"])
FINITE_AUXILIARIES = frozenset(
    [
        "am",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "can",
        "could",
        "may",
        "might",
        "must",
    ]
)
PREPOSITIONS = frozenset(
    [
        "of",
        "from",
        "in",
        "into",
        "on",
        "onto",
        "at",
        "by",
        "with",
        "without",
        "for",
        "under",
        "over",
        "between",
        "among",
        "within",
        "through",
        "across",
        "along",
        "near",
        "per",
        "via",
        "to",
        "about",
        "above",
        "below",
        "inside",
        "outside",
        "beside",
        # Completed from the simple prepositions of Huddleston and Pullum 2002, The Cambridge
        # Grammar of the English Language: the unambiguous ones only (not after, before,
        # since, until, which also open a subordinate clause).
        "during",
        "upon",
        "against",
        "toward",
        "towards",
        "throughout",
        "beneath",
        "beyond",
        "behind",
        "around",
        "amid",
        "despite",
        "underneath",
    ]
)
DETERMINERS = frozenset(
    [
        "the",
        "a",
        "an",
        "this",
        "these",
        "those",
        "each",
        "every",
        "all",
        "both",
        "some",
        "several",
        "many",
        "few",
        "any",
        "no",
        "another",
        "other",
        "such",
        "its",
        "their",
        "our",
        "his",
        "her",
        "my",
        "your",
        "either",
        "neither",
    ]
)
# Irregular past participles that do not end in -ed or -en (Huddleston and Pullum 2002,
# ch. 3, inflection of irregular verbs).
# A subset of the irregular verbs, those that name an act done to a test article;
# the regular -ed / -en endings are tested in the code, not listed.
_IRREGULAR_PARTICIPLES = frozenset(
    [
        "cut",
        "made",
        "taken",
        "drawn",
        "built",
        "kept",
        "held",
        "set",
        "put",
        "cast",
        "grown",
        "spun",
        "sewn",
        "sawn",
        "shorn",
    ]
)
# Past passives only: "is/are" is a rule or a habit, not a test that was run.
_PASSIVE_AUXILIARY = frozenset({"was", "were"})
# The passive of a set-up step is a referenced class with two sources, not a phrase list:
# (a) operations on a measuring system: VIM, JCGM 200:2012, 2.39 (calibration) and 3.11
#     (adjustment of a measuring system);
# (b) verbs of putting: Levin 1993, English Verb Classes and Alternations, class 9.1 (put
#     verbs), restricted to the members that state where or how the apparatus was placed.
SETUP_VERBS = frozenset(
    [
        # VIM JCGM 200:2012 2.39, 3.11
        "calibrated",
        "adjusted",
        # Levin 1993, class 9.1
        "placed",
        "positioned",
        "mounted",
        "installed",
        "set",
        "put",
        "arranged",
        "situated",
        "lodged",
    ]
)
SETUP_PASSIVE = r"\b(?:was|were)\s+(?:" + "|".join(sorted(SETUP_VERBS)) + r")\b"
# A clause that opens with one of these is a condition or a report, not a statement.
_OPENING_SUBORDINATORS = frozenset({"if", "unless", "whether", "that"})
# A verb that reports or requires: what follows it is said, not done. Reporting verbs of
# academic prose are an open class (Hyland 1999, "Academic attributions", Applied
# Linguistics 20(3); Thompson and Ye 1991, "Evaluation in the reporting verbs used in
# academic papers", Applied Linguistics 12(4); Huddleston and Pullum 2002, ch. 11,
# reported speech), listed here by their forms.
REPORTING_VERBS = frozenset(
    [
        "show",
        "shows",
        "showed",
        "shown",
        "report",
        "reports",
        "reported",
        "found",
        "note",
        "notes",
        "noted",
        "state",
        "states",
        "stated",
        "suggest",
        "suggests",
        "suggested",
        "indicate",
        "indicates",
        "indicated",
        "assume",
        "assumes",
        "assumed",
        "require",
        "requires",
        "required",
    ]
)
_NEGATIVE_DETERMINERS = frozenset({"no", "neither"})
# A cited test: a numbered reference, "et al.", or an agent introduced by "by".
_CITATION = re.compile(r"\[\d|\bet\s+al\b")
_AGENT_BY = re.compile(r"\s+by\s+(?:the\s+)?[A-Z]")
_STEP_ADVERB = r"(?:(?:then|also|first|next|again|subsequently)\s+)?"


def _tokens(text):
    view = segmentation_view(text or "")
    # A period that closes an abbreviation is not a token: it breaks no clause.
    return [
        (m.group(0), m.start(), m.end())
        for m in _TOKEN.finditer(view)
        if view is text or m.group(0) != MASK
    ]


def passive_clauses(text):
    """Lists of (word, start, end), lower-cased words, one list per clause."""
    clauses_, current = [], []
    for word, start, end in _tokens(text):
        low = word.lower()
        if low in _CLAUSE_PUNCTUATION or low.startswith("\n"):
            clauses_.append(current)
            current = []
            continue
        if low in SUBORDINATORS:
            clauses_.append(current)
            current = []
        current.append((low, start, end))
    clauses_.append(current)
    return [c for c in clauses_ if c]


def _participle(word):
    return word in _IRREGULAR_PARTICIPLES or (len(word) > 3 and word.endswith(("ed", "en")))


def _noun_phrase_body(words, i):
    """End of the noun phrase that starts at ``i`` (determiners, then plain words), or
    None when there is no plain word or a determiner follows one."""
    while i < len(words) and words[i] in DETERMINERS:
        i += 1
    start = i
    while i < len(words) and words[i] not in PREPOSITIONS and words[i] not in DETERMINERS:
        i += 1
    if i == start or (i < len(words) and words[i] in DETERMINERS):
        return None
    return i


def _post_head(words):
    """True when every word after the head is one of its dependents."""
    i = 0
    while i < len(words):
        word = words[i]
        if word in PREPOSITIONS:
            i = _noun_phrase_body(words, i + 1)
            if i is None:
                return False
        elif (
            _participle(word)
            and i + 1 < len(words)
            and words[i + 1] in PREPOSITIONS
            or any(ch.isdigit() for ch in word)
        ):
            i += 1
        else:
            return False
    return True


def subject_head(words, nouns):
    """True when a noun of ``nouns`` (tuples of words) heads the subject ``words``."""
    for h in range(len(words)):
        if words[h] in PREPOSITIONS:
            return False
        if words[h] in _NEGATIVE_DETERMINERS:
            # "No specimens were heated": the subject is denied, not described.
            return False
        for noun in nouns:
            if tuple(words[h : h + len(noun)]) == noun:
                return _post_head(words[h + len(noun) :])
    return False


def _sentence_span(text, offset):
    start = 0
    for cut in SENTENCE_BREAK.finditer(segmentation_view(text)):
        if cut.start() >= offset:
            return start, cut.start()
        start = cut.end()
    return start, len(text)


def passive_subject_heads(text, nouns, verbs):
    """True when, in one clause of ``text``, a noun of ``nouns`` heads the subject of a
    passive whose participle matches the alternation ``verbs``."""
    nouns = [tuple(n.lower().split()) for n in nouns if n and n.split()]
    if not nouns or not verbs:
        return False
    verb = re.compile(r"\s+" + _STEP_ADVERB + r"(?:" + verbs + r")\b", re.IGNORECASE)
    text = text or ""
    for clause in passive_clauses(text):
        words = [w for w, _s, _e in clause]
        if words[0] in _OPENING_SUBORDINATORS:
            continue
        for i, (word, _start, end) in enumerate(clause):
            if word not in _PASSIVE_AUXILIARY:
                continue
            found = verb.match(text, end)
            if not found:
                continue
            # What a source reports or a method requires is not a test that was run.
            if any(w in REPORTING_VERBS for w in words[:i]):
                continue
            first_char, last_char = _sentence_span(text, end)
            if _CITATION.search(text[first_char:last_char]) or _AGENT_BY.match(text, found.end()):
                continue
            # The subject runs back to the clause start, a coordinator or another
            # finite verb, whichever is nearest.
            first = 0
            for j in range(i - 1, -1, -1):
                if words[j] in COORDINATORS or words[j] in FINITE_AUXILIARIES:
                    first = j + 1
                    break
            if subject_head(words[first:i], nouns):
                return True
    return False


# Self-referring determiners: the determiner slot of a label that points at the document
# itself. "our": self-mention (Hyland 2001, "Humble servants of the discipline? Self-mention
# in research articles", English for Specific Purposes 20(3)); "this": a demonstrative
# determinative (Huddleston and Pullum 2002); "the present", "the current": announcing the
# present research. As a blocking guard any head noun follows: a label opened by one of these
# is discourse-internal and never an external data source.
SELF_DEIXIS = re.compile(r"^\s*(?:this|our|(?:the\s+)?(?:present|current))\s+\S", re.IGNORECASE)

# Endophoric markers: nouns that point to another part of the same text (Hyland 2005,
# Metadiscourse: Exploring Interaction in Writing; Hyland and Tse 2004, "Metadiscourse in
# academic writing: a reappraisal", Applied Linguistics 25(2)), with the printed
# abbreviations of those nouns. Membership per the 1.4a spec; to verify against the item
# list of Hyland 2005 before the freeze.
POINTER_NOUNS = ("figure", "table", "section", "chapter", "page", "example", "part")
# Their printed abbreviations (Fig., Sec., Ch., p., pp.) are the shared class in
# abbreviations.py: a period or a numeral must follow, so that a word such as "p-type" or
# "ch4" is not read as a pointer.
ENDOPHORIC_MARKER = re.compile(
    r"^\s*(?:(?:"
    + "|".join(POINTER_NOUNS)
    + r")s?\b|(?:"
    + "|".join(POINTER_ABBREVIATIONS)
    + r")(?:\.|\s+\d))",
    re.IGNORECASE,
)


def heads_object_of_from(between):
    """Whether the label heads the noun phrase after "from", given the words printed
    between "from" and the label (Huddleston and Pullum 2002, noun-phrase head and
    dependents). Only determiners and plain modifiers may stand there; a preposition or
    a participle (or -ing form) makes the label a dependent of another head."""
    for word in re.findall(r"[\w-]+", between.lower()):
        if word in PREPOSITIONS or _participle(word) or (len(word) > 4 and word.endswith("ing")):
            return False
    return True


SETTING_CUE = (
    r"(?<![\w-])(?:at|in|under|within|during|into|to\s+achieve|exposed\s+to|subjected\s+to)"
    r"\s+(?:(?:the|an?)\s+)?(?:[a-z-]+\s+)?"
)


def setting_mention(label, text):
    """Whether the text prints the label as the setting of what it describes.

    A condition is a setting when a prepositional phrase introduces it ("exposed
    to a 25 cm/s purge stream", "to achieve lunar gravity", "at 2-g"); a bare
    mention ("besides the 2-g lateral load") attributes nothing.
    """
    return bool(
        re.search(
            SETTING_CUE + re.escape(normalized(label)) + r"(?![\w-])",
            normalized(text),
        )
    )
