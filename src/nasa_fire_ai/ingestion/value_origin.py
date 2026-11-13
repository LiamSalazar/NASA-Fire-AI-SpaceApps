"""Does the study that produced a value agree with what its own phrase prints? (SCIENCE_ORIGIN_CHECK)

A value carries an origin: this study (``current``) or cited work (``cited``). The mark is the value's
own ``study`` when the model set it, else the study of its subject, else none. The check reads only
the phrase that holds the value (``value_phrase``) and the citation markers printed in it, by the
typographic conventions of citing (Chicago Manual of Style 17 ch. 14-15; APA 7 section 8.17-8.21):

- a ``current`` value is held when a marker is a constituent of its own clause (after the value or its
  unit, the object of a preposition, an author noun phrase) or of its own noun phrase;
- a ``cited`` value is kept only when its own phrase prints a marker, or names a cited investigation;
  it is held when the phrase carries a self-mention (Hyland 2001: "we", "our", "here", "this study");
- an unmarked value is held when its sentence prints any anchor.

The check can only hold. It never rejects, never moves a subject and never writes ``study``.

Final round (FINAL_ROUND_ACCEPTANCE.md, fixes 1, 2, 4-7; fix 3, line breaks through the de-wrap layer,
is pending): a marker or a reference-list author in the value's phrase or in a locating fronted
adjunct cancels the self-mention exemption; a superscript after punctuation is a marker; every
printed occurrence of the value in its paragraph is judged; a sentence that opens a page is read
with the head printed on the page before; a value span counts only where the value is printed.
A reference-list surname is an anchor when it is the subject of a finite verb, or is followed by
"et al.", "and colleagues", a year in parentheses or a bracketed number, or a possessive (N1, rule corrected); a
surname that also prints in lowercase in the document needs one of the explicit signals at the sentence
start; "Name's noun" held by the repo's own vocabulary is a term, not an author.
"""

import os
import re

from nasa_fire_ai.ingestion import abbreviations, clause_cues
from nasa_fire_ai.ingestion.clause_cues import PREPOSITIONS, _tokens
from nasa_fire_ai.ingestion.scientific_facets import ORIGIN_MARKS
from nasa_fire_ai.ingestion.scientific_scope import page_continuation_context
from nasa_fire_ai.ingestion.source_spans import mentions
from nasa_fire_ai.ingestion.study_attribution import (
    THIRD_PARTY,
    reference_authors,
    reference_text,
)
from nasa_fire_ai.ingestion.value_phrase import (
    _NOT_NON_FINITE,
    _head_at,
    sentence_bounds,
    value_phrase,
)

# Nouns that name the document itself or its own work, and the adjectives of an earlier time. Both are
# open classes (Hyland 2001, self-mention); they hold words of grammar, never of a source.
SELF_DEICTIC = frozenset(
    {
        "study",
        "work",
        "paper",
        "report",
        "article",
        "investigation",
        "experiment",
        "experiments",
        "test",
        "tests",
        "research",
        "series",
        "campaign",
        "manuscript",
        "survey",
        "trial",
        "trials",
    }
)
PRIOR_TIME = frozenset({"earlier", "previous", "prior", "former", "past", "preceding"})
FIRST_PERSON = frozenset({"we", "our", "us"})
CITED_CLASSES = frozenset({"Investigation", "ExperimentFamily", "Publication"})
_SUPERSCRIPTS = "¹²³⁰⁴⁵⁶⁷⁸⁹†‡"
_PARTICLES = r"(?:(?:van|von|de|der|den|di|du|le|la)\s+)*"
_SURNAME = _PARTICLES + r"[A-Z][\w'’-]+"
_NUMBER = r"\d+[a-z]?"
SHAPES = (
    (
        "bracket",
        re.compile(r"\[\s*" + _NUMBER + r"(?:\s*[,;–-]\s*(?:pp?\.\s*)?" + _NUMBER + r")*\s*\]"),
    ),
    (
        "author_year",
        re.compile(
            r"\(\s*" + _SURNAME + r"(?:\s+(?:et\s+al\.?|and|&)\s*(?:" + _SURNAME + r")?)?,?\s+"
            r"(?:19|20)\d\d[a-z]?\s*\)"
        ),
    ),
    (
        "author_year",
        re.compile(_SURNAME + r"(?:\s+et\s+al\.?)?\s*\(\s*(?:19|20)\d\d[a-z]?\s*\)"),
    ),
    ("et_al", re.compile(r"\bet\s+al\b\.?")),
    ("reference", re.compile(r"\bRefs?\.\s*\d+(?:\s*[,–-]\s*\d+)*")),
    ("ibid", re.compile(r"\b(?:ibid|op\.\s*cit)\.?", re.IGNORECASE)),
)
AUTHOR_SHAPES = frozenset({"author_year", "et_al", "reference", "ibid"})
_EQUATION_BEFORE = re.compile(r"\b(?:Eqs?|Equations?)\.?\s*$")


def origin_check_enabled():
    return os.getenv("SCIENCE_ORIGIN_CHECK", "1") != "0"


def validator_locator_enabled():
    """ORIGIN reads the value place with the evidence validator's own locator (on by default)."""
    return os.getenv("SCIENCE_ORIGIN_VALIDATOR_LOCATOR", "1") != "0"


def numbered_references(document):
    """The numbers the document's own reference list gives its entries (``n.`` or ``[n]``)."""
    text = reference_text(document)
    if not text:
        return set()
    return {int(n) for n in re.findall(r"(?m)^\s*\[?(\d{1,3})[.\]]", text)}


def _attach(sentence, start):
    """The word a marker at ``start`` is attached to: (text, start, end), or None."""
    before = sentence[:start]
    # A chain of markers ("(7) (8)") is attached to the word before the first.
    before = re.sub(r"(?:\s*(?:\[[^\]]*\]|\(\d{1,3}\)))+\s*$", "", before)
    tokens = _tokens(before)
    if not tokens:
        return None
    return tokens[-1]


def citation_anchors(sentence, document):
    """Citation markers and weak attributions printed in one sentence.

    Each anchor is ``{shape, text, start, end, strength, attach}`` with offsets in ``sentence``;
    ``attach`` is the word the marker stands on (None for a free-standing or author marker).
    """
    anchors = []
    taken = []

    def add(shape, start, end, strength="strong", attach=True):
        anchors.append(
            {
                "shape": shape,
                "text": sentence[start:end],
                "start": start,
                "end": end,
                "strength": strength,
                "attach": _attach(sentence, start) if attach else None,
            }
        )
        taken.append((start, end))

    for shape, rx in SHAPES:
        for m in rx.finditer(sentence):
            if not any(a <= m.start() < b for a, b in taken):
                add(shape, m.start(), m.end(), attach=shape == "bracket")
    numbers = numbered_references(document)
    for m in re.finditer(r"\((\d{1,3})\)", sentence):
        if (
            int(m.group(1)) in numbers
            and not _EQUATION_BEFORE.search(sentence[: m.start()])
            and not any(a <= m.start() < b for a, b in taken)
        ):
            add("numbered", m.start(), m.end())
    text = reference_text(document) or ""
    for m in re.finditer(r"\[([A-Z][A-Za-z]+\d{2,4}[a-z]?)\]", sentence):
        if f"[{m.group(1)}]" in text and not any(a <= m.start() < b for a, b in taken):
            add("keyed", m.start(), m.end())
    for m in re.finditer(r"([^\W\d_][\w'’-]*?)([" + _SUPERSCRIPTS + r"]+)(?!\w)", sentence):
        word = m.group(1)
        if len(word) >= 3 and not any(a <= m.start(2) < b for a, b in taken):
            add("superscript", m.start(2), m.end(2))
    # A superscript note that follows the punctuation of its clause ("... 12 s.2", "..., 12 s,2")
    # stands for the same note as one that follows a word (fix 2 of the final round).
    for m in re.finditer(r"(?<=[^\W_][.,;:])([" + _SUPERSCRIPTS + r"]+)(?!\w)", sentence):
        if not any(a <= m.start(1) < b for a, b in taken):
            add("superscript", m.start(1), m.end(1))
    for m in re.finditer(r"(?<=[^\W\d_]\))([" + _SUPERSCRIPTS + r"]+)(?!\w)", sentence):
        if _closes_phrase(sentence, m.start(1) - 1) and not any(
            a <= m.start(1) < b for a, b in taken
        ):
            add("superscript", m.start(1), m.end(1))
    strong = list(taken)
    # Surnames from the document's own reference list are anchors (fix 7); a name that opens the
    # sentence counts only where it stands as an author (a common word is capitalized there too).
    for name in sorted(reference_authors(document)):
        for m in re.finditer(rf"\b{re.escape(name)}\b", sentence):
            if any(a <= m.start() < b for a, b in strong):
                continue
            after = sentence[m.end() :]
            if _eponymous_term(name, after):
                continue
            if m.start() > 0 or _agent_position(sentence, m.end(), name, document):
                add("reference_author", m.start(), m.end(), strength="weak", attach=False)
    for m in THIRD_PARTY.finditer(sentence):
        if not any(a <= m.start() < b for a, b in strong):
            add("third_party", m.start(), m.end(), strength="weak", attach=False)
    anchors.sort(key=lambda a: a["start"])
    return anchors


def _closes_phrase(sentence, close):
    """Whether the ``)`` at ``close`` closes a parenthesis of words, not a squared expression.

    "(m/s)2" is a unit or an expression raised to a power; "(Okafor and Varga)2" is a note.
    """
    depth = 0
    for k in range(close, -1, -1):
        if sentence[k] == ")":
            depth += 1
        elif sentence[k] == "(":
            depth -= 1
            if depth == 0:
                inner = sentence[k + 1 : close]
                return bool(re.search(r"[^\W\d_]{2,}", inner)) and not re.search(
                    r"[/*^+×·=<>−]", inner
                )
    return False


_COLLEAGUES = re.compile(r"\s+and\s+(?:colleagues|co-?workers)\b")
_YEAR_PAREN = re.compile(r"\s*\(\s*(?:19|20)\d\d[a-z]?\s*\)")
_CO_AUTHOR = re.compile(r"\s*(?:,\s*)?(?:and|&)\s+" + _SURNAME + r"\b")
_ET_AL_AFTER = re.compile(r"\s+" + abbreviations._ET_AL.pattern + r"\b", re.IGNORECASE)
_NOT_AGENT_PREPOSITIONS = frozenset({"to", "by", "from"})


def _finite_after(after):
    """Whether the words that follow a capitalized name read as the finite verb of its clause
    (the name is the subject), by the closed classes of ``clause_cues`` and by form, never by a
    list of verbs: a finite auxiliary or modal; a reporting verb; a past form (-ed, an irregular
    participle) followed by the start of its object, a complement or the end of the clause; or any
    other word that is followed by a determiner (the verb of a transitive clause). A noun that
    modifies a following noun ("Long exposure raised ...") is none of these."""
    tokens = _tokens(after)
    k = 0
    # One adverb or negation may stand between the subject and the verb.
    if len(tokens) > 1 and (
        tokens[0][0].lower().endswith("ly") or tokens[0][0].lower() in {"also", "not"}
    ):
        k = 1
    if k >= len(tokens) or not tokens[k][0][0].isalpha() or not tokens[k][0][0].islower():
        return False
    word = tokens[k][0].lower()
    ahead = tokens[k + 1][0].lower() if k + 1 < len(tokens) else None
    if word in clause_cues.FINITE_AUXILIARIES or word in clause_cues.REPORTING_VERBS:
        return True
    if word not in _NOT_NON_FINITE and (
        word in clause_cues._IRREGULAR_PARTICIPLES or (len(word) > 3 and word.endswith("ed"))
    ):
        return (
            ahead is None
            or ahead[0].isdigit()
            or ahead in clause_cues.DETERMINERS
            or ahead in clause_cues.SUBORDINATORS
            or (ahead in PREPOSITIONS and ahead not in _NOT_AGENT_PREPOSITIONS)
            or not ahead[0].isalnum()
        )
    return ahead is not None and ahead in clause_cues.DETERMINERS


_BRACKET_AFTER = re.compile(r"\s*\[\s*\d")
_POSSESSIVE = re.compile(r"['’]s\s+([^\W\d_][\w-]*)")


def _registry_term_keys():
    """Normalized terms of the repo's own vocabulary: the approved ontology and semantic registry,
    the seed lexicon and the unit registry. Read once; empty when the repo files are absent."""
    global _TERM_KEYS
    if _TERM_KEYS is None:
        keys = set()
        try:
            from pathlib import Path

            from nasa_fire_ai.ingestion.seed_terms import approved_term_keys, seed_term_keys
            from nasa_fire_ai.ingestion.semantic import load_semantic_registry
            from nasa_fire_ai.normalization import units

            root = Path(__file__).resolve().parents[3]
            registry = load_semantic_registry(root / "domain/semantic_registry.yaml")
            keys = approved_term_keys(registry) | seed_term_keys(root)
            keys |= {_term_key(u) for u in list(units.TABLE) + list(units.AFFINE)}
        except (OSError, ValueError, LookupError, TypeError, ImportError):
            keys = set()
        _TERM_KEYS = keys
    return _TERM_KEYS


_TERM_KEYS = None


def _term_key(term):
    return re.sub(r"[^a-z0-9]+", " ", str(term).casefold()).strip()


def _eponymous_term(name, after):
    """Whether "Name's noun" is a term the repo's vocabulary, ontology, semantic registry or unit
    registry already holds (a modulus or number named after a person), so the name is no author."""
    m = _POSSESSIVE.match(after)
    if not m:
        return False
    keys = _registry_term_keys()
    noun = m.group(1)
    return _term_key(f"{name}'s {noun}") in keys or _term_key(f"{name} {noun}") in keys


def _lowercase_in_document(name, document):
    """Whether the surname also prints in lowercase anywhere in the document (a common word)."""
    low = name.lower()
    if low == name:
        return False
    rx = re.compile(r"(?<![\w])" + re.escape(low) + r"(?![\w])")
    return any(rx.search(s.get("text", "")) for s in document.get("segments", []))


def _agent_position(sentence, end, name=None, document=None):
    """Whether a capitalized name that opens a sentence stands as an author there (fix 7, N1): it
    is followed by "et al.", "and colleagues / co-workers", a year in parentheses or a number in
    brackets (an explicit citation signal), or it is the subject of a finite verb (alone or with
    co-authors: "A and B found ...") or a possessive ("Name's data showed ..."). When the same
    surname also prints in lowercase in the document, only an explicit citation signal counts."""
    after = sentence[end:]
    if (
        _ET_AL_AFTER.match(after)
        or _COLLEAGUES.match(after)
        or _YEAR_PAREN.match(after)
        or _BRACKET_AFTER.match(after)
    ):
        return True
    if name is not None and document is not None and _lowercase_in_document(name, document):
        return False
    if _POSSESSIVE.match(after):
        return True
    while True:
        co = _CO_AUTHOR.match(after)
        if not co:
            break
        after = after[co.end() :]
    return _finite_after(after)


def binders(sentence, anchors):
    """Self-mentions (Hyland 2001) printed in a sentence, each ``{text, start, void}``.

    A binder is void when its noun phrase carries an adjective of an earlier time, or when a strong
    anchor follows it directly ("the present study [2]"); a void binder is a weak anchor instead.
    """
    tokens = _tokens(sentence)
    found = []
    strong_starts = [a["start"] for a in anchors if a["strength"] == "strong"]
    for i, (word, start, end) in enumerate(tokens):
        low = word.lower()
        if low == "here" or low in FIRST_PERSON:
            ahead = [t[0].lower() for t in tokens[i + 1 : i + 3]]
            found.append({"text": word, "start": start, "void": bool(PRIOR_TIME & set(ahead))})
        elif low in {"this", "present", "current"}:
            for j in range(i + 1, min(i + 4, len(tokens))):
                head = tokens[j][0].lower()
                if head in SELF_DEICTIC:
                    between = {t[0].lower() for t in tokens[i + 1 : j]}
                    follows = sentence[tokens[j][2] :]
                    direct = any(
                        0 <= s - tokens[j][2] <= len(follows) - len(follows.lstrip())
                        for s in strong_starts
                    )
                    found.append(
                        {
                            "text": sentence[start : tokens[j][2]],
                            "start": start,
                            "void": bool(PRIOR_TIME & between) or direct,
                        }
                    )
                    break
                if not tokens[j][0][0].isalpha():
                    break
    return found


def _locating_frame(sentence, frame, anchor):
    """Whether ``anchor`` stands in a fronted adjunct that opens with in / from / according
    (not a comparison head: "in contrast to", "as in", "similar to")."""
    if not (frame[0] <= anchor["start"] < frame[1]):
        return False
    tokens = _tokens(sentence[frame[0] : frame[1]])
    return bool(
        tokens and tokens[0][0].lower() in {"in", "from", "according"} and not _head_at(tokens, 0)
    )


def _clause_level(anchor, sentence, own_np, label_span):
    """Whether a strong marker is a constituent of the value's clause or noun phrase."""
    if anchor["shape"] in AUTHOR_SHAPES:
        return True
    after = sentence[anchor["end"] :]
    # The antecedent of a relative clause, or the subject of a reporting verb or an auxiliary.
    if re.match(r"\s*,\s*(?:which|who|whom|whose|where)\b", after):
        return True
    attach = anchor["attach"]
    standalone = (
        attach is None
        or not attach[0][0].isalnum()
        or attach[0].lower()
        in (
            clause_cues.SUBORDINATORS
            | PREPOSITIONS
            | clause_cues.COORDINATORS
            | clause_cues.DETERMINERS
        )
    )
    following = re.match(r"\s*([A-Za-z]+)", after)
    if (
        standalone
        and following
        and following.group(1).lower()
        in (clause_cues.REPORTING_VERBS | clause_cues.FINITE_AUXILIARIES)
    ):
        return True
    if attach is None:
        return True
    word, s, e = attach
    if word.lower() in PREPOSITIONS | {"see", "cf", "by", "in", "as"} or not word[0].isalnum():
        return True
    if own_np[0] <= s and e <= own_np[1]:
        return True
    if label_span and label_span[0] <= s and e <= label_span[1]:
        return True
    # A surname stands for its author; a designation or a common noun names a method or apparatus.
    return word[0].isupper() and word.isalpha() and len(word) >= 3


def _occurrences(quote, expression):
    number = re.search(r"\d+(?:[.,]\d+)*", expression or "")
    if not number:
        return []
    digits = number.group().replace(",", "")
    return [
        m.start()
        for m in re.finditer(r"(?<![\d.,])\d+(?:[.,]\d+)*(?![\d])", quote or "")
        if m.group().replace(",", "") == digits
    ]


def effective_mark(item, entities):
    """(mark, source, subject_study): the value's own mark, else its subject's, else none."""
    subject = entities.get(item.get("subject")) or {}
    subject_study = subject.get("study")
    if item.get("study") in ORIGIN_MARKS:
        return item["study"], "quantity", subject_study
    if subject_study in ORIGIN_MARKS:
        return subject_study, "subject", subject_study
    return None, "none", subject_study


def _evidence_text(evidence, document, evidence_id):
    """The printed text of one evidence page: from the run's evidence, else from the document."""
    found = (evidence or {}).get(evidence_id)
    if found and found.get("text"):
        return found["text"]
    return "".join(
        s.get("text", "")
        for s in (document or {}).get("segments", [])
        if s.get("evidence_id") == evidence_id
    )


def _block(text, start):
    """The text block (paragraph) of the page that holds ``start``, for the measure of its lines."""
    first = text.rfind("\n\n", 0, start)
    last = text.find("\n\n", start)
    return text[0 if first < 0 else first + 2 : len(text) if last < 0 else last]


def _label_span(subject_label, sentence):
    if not subject_label:
        return None
    m = re.search(
        r"(?<![\w-])" + re.escape(subject_label.strip()) + r"(?![\w-])", sentence, re.IGNORECASE
    )
    return (m.start(), m.end()) if m else None


def _page_head(text, s0, s1, evidence_id, evidence):
    """The head of a sentence that opens its page (fix 5): the sentence of the page before that
    runs on into it, as ``page_continuation_context`` reads the two pages, or None."""
    # A sentence continues the page before only if a line of it opens in lower case.
    if not re.search(r"(?:^|\n)[a-z]", text[s0:s1]):
        return None
    try:
        found = page_continuation_context(
            [{"evidence_id": evidence_id, "start": s0, "end": s1}], evidence or {}
        )
    except (KeyError, TypeError, AttributeError):
        return None
    if not found:
        return None
    previous = (evidence or {}).get(found["evidence_id"], {}).get("text", "")
    end = found["end"]
    if not previous or not (0 < end <= len(previous)):
        return None
    h0, _ = sentence_bounds(previous, end - 1, _block(previous, end - 1))
    return {"evidence_id": found["evidence_id"], "start": h0, "end": end, "text": previous[h0:end]}


def _decide(
    mark, subject_study, item, text, offset, entities, document, evidence_id=None, evidence=None
):
    """One value occurrence in the printed ``text`` at ``offset``: the decision and what it read.

    The sentence is cut from the printed page, never from the quote the model chose: a quote that
    stops before a marker does not hide it. A sentence that opens its page is read with the head
    printed on the page before.
    """
    s0, s1 = sentence_bounds(text, offset, _block(text, offset))
    sentence = text[s0:s1]
    rel = offset - s0
    head = _page_head(text, s0, s1, evidence_id, evidence)
    if head:
        sentence = head["text"].rstrip() + " " + sentence
        rel += len(sentence) - (s1 - s0)
    anchors = citation_anchors(sentence, document)
    receipt = {
        "evidence_id": evidence_id,
        "sentence": {"start": s0, "end": s1},
        "continued_from": ({k: head[k] for k in ("evidence_id", "start", "end")} if head else None),
        "anchors": [{k: a[k] for k in ("shape", "text", "start", "strength")} for a in anchors],
        "binder": None,
    }
    phrase = value_phrase(sentence, rel)
    receipt["phrase"] = {"start": phrase["start"], "end": phrase["end"]}
    subject = entities.get(item.get("subject")) or {}
    label_span = _label_span(subject.get("label"), sentence)

    def inside(a):
        return phrase["start"] <= a["start"] < phrase["end"] and not any(
            s <= a["start"] < e for s, e in phrase["excised"]
        )

    strong_in = [a for a in anchors if a["strength"] == "strong" and inside(a)]
    strong_any = [a for a in anchors if a["strength"] == "strong"]
    # Surnames from the document's own reference list (fix 7).
    named = [a for a in anchors if a["shape"] == "reference_author"]
    all_binders = binders(sentence, anchors)
    frame = phrase.get("framing") or (0, 0)
    clause = phrase.get("clause") or (phrase["start"], phrase["end"])
    live = [
        b
        for b in all_binders
        if not b["void"]
        and (phrase["start"] <= b["start"] < phrase["end"] or frame[0] <= b["start"] < frame[1])
        and b["start"] < rel
    ]
    # A self-mention anywhere in the value's own clause (a set-aside segment does not end it).
    bound = any(
        not b["void"]
        and b["start"] < rel
        and (clause[0] <= b["start"] < clause[1] or frame[0] <= b["start"] < frame[1])
        for b in all_binders
    )
    if live:
        receipt["binder"] = {"text": live[0]["text"], "start": live[0]["start"]}
    voided = [b for b in all_binders if b["void"]]

    def out(decision, row, basis=None):
        receipt.update(decision=decision, row=row, basis=basis)
        return receipt

    if mark == "current":
        if subject_study == "cited" and item.get("study") == "current":
            return out("HOLD", 1, "ORIGIN_MARK_CONFLICTS_WITH_SUBJECT")
        at_clause = [
            a for a in strong_in if _clause_level(a, sentence, phrase["own_np"], label_span)
        ]
        if at_clause:
            return out("HOLD", 3, "CITATION_IN_VALUE_PHRASE")
        # Broad rule (SPEC 7.4): a citation marker anywhere in the value's sentence holds a value
        # marked current, unless the sentence binds the value to this study in its own clause.
        # The binding does not clear a marker (or a reference-list author) that stands inside the
        # value's own phrase, nor one in a fronted adjunct that locates the content ("In [2], we
        # reported ...", "From [2] ..."; fix 1): the clause is then reported, not performed.
        cancelled = bool(
            [a for a in strong_in + [n for n in named if inside(n)]]
            or [a for a in strong_any + named if _locating_frame(sentence, frame, a)]
        )
        if (strong_any or named) and (not bound or cancelled):
            return out("HOLD", 4, "CITATION_IN_VALUE_SENTENCE")
        return out("PASS", 2)
    if mark == "cited":
        if live:
            return out("HOLD", 5, "SELF_REFERENCE_IN_VALUE_PHRASE")
        phrase_text = sentence[phrase["start"] : phrase["end"]]
        names_cited = any(
            e.get("study") == "cited"
            and e.get("class_id") in CITED_CLASSES
            and e.get("label")
            and mentions(e["label"], phrase_text)
            for e in entities.values()
        )
        if strong_in or names_cited:
            return out("PASS", 6)
        return out("HOLD", 7, "NO_CITATION_IN_VALUE_PHRASE")
    if anchors or voided:
        return out("HOLD", 8, "ORIGIN_UNMARKED_IN_CITING_SENTENCE")
    return out("PASS", 9)


REASONS = {
    "ORIGIN_MARK_CONFLICTS_WITH_SUBJECT": "ORIGIN_MARK_CONFLICTS_WITH_SUBJECT",
    "CITATION_IN_VALUE_PHRASE": "ORIGIN_MARK_CONTRADICTED",
    "CITATION_IN_VALUE_SENTENCE": "ORIGIN_MARK_CONTRADICTED",
    "SELF_REFERENCE_IN_VALUE_PHRASE": "ORIGIN_MARK_CONTRADICTED",
    "NO_CITATION_IN_VALUE_PHRASE": "ORIGIN_MARK_CONTRADICTED",
    "ORIGIN_UNMARKED_IN_CITING_SENTENCE": "ORIGIN_UNMARKED_IN_CITING_SENTENCE",
    "SPAN_NOT_LOCATED_IN_EVIDENCE": "ORIGIN_SPAN_NOT_LOCATED",
}


def _validator_finds(quote, expression, anchored=False):
    """Offsets in ``quote`` of the value, found by the evidence validator's own locator (the
    numeric matcher and the expression comparison that ``validate_quantity`` uses to find the
    value in its support). ``anchored`` keeps only a match that starts the quote."""
    from nasa_fire_ai.ingestion.numeric_expressions import same_expression, source_numeric_matches

    return [
        m.start(1)
        for m in source_numeric_matches(quote or "")
        if same_expression(m.group(1), expression or "") and (not anchored or m.start(1) <= 1)
    ]


def _printed_at(text, value, expression):
    """Whether the located value span prints the value there (fix 6): the number of the expression
    stands at the span. A span that points at other text is not a place of the value."""
    start = value.get("start", -1)
    if not (isinstance(start, int) and 0 <= start < len(text)):
        return False
    if validator_locator_enabled():
        end = value.get("end")
        end = end if isinstance(end, int) and end > start else start + len(value.get("quote") or "")
        if _validator_finds(text[start:end], expression, anchored=True):
            return True
    number = re.search(r"\d+(?:[.,]\d+)*", expression or "")
    if not number:
        return False
    end = value.get("end")
    end = end if isinstance(end, int) and end > start else start + len(number.group())
    printed = re.match(r"\d+(?:[.,]\d+)*", text[start:end])
    return bool(
        printed
        and (start == 0 or not re.match(r"[\d.,]", text[start - 1]))
        and printed.group().replace(",", "") == number.group().replace(",", "")
    )


def _block_range(text, offset):
    first = text.rfind("\n\n", 0, offset)
    last = text.find("\n\n", offset)
    return (0 if first < 0 else first + 2), (len(text) if last < 0 else last)


def _other_occurrences(item, text, offset):
    """Offsets of the other printed occurrences of the value in the paragraph of ``offset``.

    An occurrence is the same number followed by the same unit; a value with no unit is read where
    the same word follows the number. A number inside a bracket marker is not a value."""
    number = re.search(r"\d+(?:[.,]\d+)*", item.get("expression") or "")
    if not number:
        return []
    digits = number.group().replace(",", "")
    unit = (item.get("unit") or "").strip()
    here = re.match(r"\d+(?:[.,]\d+)*", text[offset:])
    if unit:
        follow = r"[ \u00a0]?" + re.escape(unit) + r"(?![^\W\d_])"
    else:
        word = re.match(r"\s*([^\W\d_]+)", text[offset + (len(here.group()) if here else 0) :])
        if not word:
            return []
        follow = r"\s*" + re.escape(word.group(1)) + r"\b"
    lo, hi = _block_range(text, offset)
    found = []
    for m in re.finditer(r"(?<![\d.,\[])\d+(?:[.,]\d+)*(?!\d)", text[lo:hi]):
        if m.group().replace(",", "") != digits:
            continue
        a = lo + m.start()
        if a != offset and re.match(follow, text[lo + m.end() : hi]):
            found.append(a)
    return found


def _occurrences_in_evidence(span, expression, evidence, document):
    """Offsets of the value in the printed page text, or None when it cannot be located there."""
    text = _evidence_text(evidence, document, span.get("evidence_id"))
    quote = span.get("quote", "")
    start = span.get("start")
    if not text or not quote:
        return text, None
    if start is None or text[start : start + len(quote)] != quote:
        start = text.find(quote)
    if start < 0:
        return text, None
    offsets = [start + o for o in _occurrences(quote, expression)]
    if not offsets and validator_locator_enabled():
        offsets = [start + o for o in _validator_finds(quote, expression)]
    return text, offsets or None


def origin_check(item, record, spans, entities, document, evidence=None):
    """Write the ``origin`` receipt on a quantity record and hold it when its mark is contradicted.

    Runs only on a record that is still ``SOURCE_SUPPORTED``; any other status is left as it is.
    A value that cannot be located in the printed evidence is held (the check fails closed).
    """
    mark, source, subject_study = effective_mark(item, entities)
    origin = {
        "mark": mark,
        "mark_source": source,
        "subject_study": subject_study,
        "decision": "NOT_RUN",
        "occurrences": [],
    }
    record["origin"] = origin
    if record.get("status") != "SOURCE_SUPPORTED":
        return
    # Where the value is printed: the located value spans of the record, else its occurrences in
    # the support quotes. A support span that holds only context (a heading, a neighbour sentence)
    # adds no occurrence and is not a reason to hold.
    places = []
    for value in record.get("quantity_value_spans") or []:
        text = _evidence_text(evidence, document, value.get("evidence_id"))
        if text and _printed_at(text, value, item.get("expression")):
            places.append((value["evidence_id"], text, value["start"]))
    if not places:
        for span in spans:
            text, offsets = _occurrences_in_evidence(
                span, item.get("expression"), evidence, document
            )
            places += [(span.get("evidence_id"), text, o) for o in offsets or []]
    # Every printed occurrence of the value (its number and unit) in the paragraph of each place is
    # read as well (fix 4): the model quotes one, the page may print the same number as cited work
    # and as its own in one paragraph.
    judged = {(eid, offset) for eid, _, offset in places}
    extra = []
    for evidence_id, text, offset in places:
        for other in _other_occurrences(item, text, offset):
            if (evidence_id, other) not in judged:
                judged.add((evidence_id, other))
                extra.append((evidence_id, text, other))
    found = [
        dict(
            _decide(mark, subject_study, item, text, offset, entities, document, eid, evidence),
            extra=False,
        )
        for eid, text, offset in places
    ] + [
        dict(
            _decide(mark, subject_study, item, text, offset, entities, document, eid, evidence),
            extra=True,
        )
        for eid, text, offset in extra
    ] or [
        {
            "evidence_id": (spans[0].get("evidence_id") if spans else None),
            "decision": "HOLD",
            "row": 0,
            "basis": "SPAN_NOT_LOCATED_IN_EVIDENCE",
            "anchors": [],
        }
    ]
    origin["occurrences"] = found
    held = [f for f in found if f["decision"] == "HOLD"]
    held.sort(key=lambda f: bool(f.get("extra")))
    origin["decision"] = "HOLD" if held else "PASS"
    # The hold that only the every-occurrence rule makes: the quoted occurrence passes alone.
    origin["held_by_other_occurrence"] = bool(held and held[0].get("extra"))
    if held:
        reason = REASONS[held[0]["basis"]]
        record["status"] = "UNRESOLVED"
        if reason not in record["reasons"]:
            record["reasons"].append(reason)
        origin["basis"] = held[0]["basis"]
        origin["row"] = held[0]["row"]


ORIGIN_AUDIT_SEED = 20261028
CONTROL_SAMPLE = 30


def _anchor_level(origin):
    shapes = [
        a["strength"] for occurrence in origin.get("occurrences", []) for a in occurrence["anchors"]
    ]
    return "strong" if "strong" in shapes else "weak" if shapes else "none"


def origin_audit(records, seed=ORIGIN_AUDIT_SEED):
    """What the origin check saw in one run, for the manual count of cited values published as current.

    ``counts`` is by status, mark, where the mark came from, the strongest anchor printed in the
    value's sentence, and the decision. ``review_queue`` lists every supported value marked current
    whose sentence prints an anchor; ``control_sample`` draws up to 30 supported current values per
    source whose sentence prints none, with a fixed seed, to estimate what the queue cannot see.
    """
    import random

    counts = {}
    queue, pool = [], {}
    for r in records:
        origin = r.get("origin")
        if r.get("kind") != "quantities" or origin is None:
            continue
        level = _anchor_level(origin)
        key = "|".join(
            [r["status"], str(origin["mark"]), origin["mark_source"], level, origin["decision"]]
        )
        counts[key] = counts.get(key, 0) + 1
        if r["status"] == "SOURCE_SUPPORTED" and origin["mark"] == "current":
            spans = r.get("support_spans") or [{}]
            source = spans[0].get("source_id")
            item = {
                "id": r["id"],
                "source_id": source,
                "expression": r["proposal"].get("expression"),
            }
            if level != "none":
                queue.append(item)
            else:
                pool.setdefault(source, []).append(item)
    sample = []
    for source in sorted(pool, key=str):
        ordered = sorted(pool[source], key=lambda x: x["id"])
        sample += random.Random(f"{seed}:{source}").sample(
            ordered, min(CONTROL_SAMPLE, len(ordered))
        )
    return {
        "counts": dict(sorted(counts.items())),
        "review_queue": sorted(queue, key=lambda x: x["id"]),
        "control_sample": sorted(sample, key=lambda x: x["id"]),
        "seed": seed,
    }
