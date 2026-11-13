"""The phrase that holds one printed value, cut by structure.

A sentence can print a value of this study beside a value of cited work ("the smolder time was 9 s,
compared with 12 s in [2]"). The citation marker of the second value says nothing about the first:
each value is read in its own phrase. The phrase is found on the tokens of ``clause_cues`` and its
closed classes (subordinators, coordinators, finite auxiliaries, prepositions); no phrase of a
source is listed.

Cuts, in the order the grammar gives them (Quirk et al. 1985 ch. 14-15; Huddleston and Pullum 2002
ch. 11 and 13):

1. a semicolon, a colon or the end of the sentence;
2. a comma followed by a subordinator or a coordinator, except a relative pronoun: a relative clause
   stays with the noun it modifies;
3. a coordinator without a comma, when a finite verb stands both before and after it (two clauses);
4. a comparison or likeness head ("compared with", "unlike", "versus", "similar to", "as in", ...);
5. a comma followed by a non-finite verb (a supplementive clause), and a parenthetical that holds
   more than a bare marker. Both are set aside when they close again, and the host resumes after.

A sentence that opens with a preposition, a participle or a subordinator has a fronted adjunct that
runs to its first comma; it frames the first host phrase and is not part of it.
"""

import re
import statistics

from nasa_fire_ai.ingestion import clause_cues
from nasa_fire_ai.ingestion.clause_cues import (
    COORDINATORS,
    FINITE_AUXILIARIES,
    PREPOSITIONS,
    SUBORDINATORS,
    _tokens,
)

RELATIVES = frozenset({"which", "who", "whom", "whose", "where"})
# Heads of a comparison or a likeness (lower case token runs).
COMPARISON_HEADS = (
    ("compared", "with"),
    ("compared", "to"),
    ("in", "comparison", "with"),
    ("in", "comparison", "to"),
    ("in", "contrast", "with"),
    ("in", "contrast", "to"),
    ("unlike",),
    ("versus",),
    ("vs",),
    ("relative", "to"),
    ("as", "opposed", "to"),
    ("similar", "to"),
    ("consistent", "with"),
    ("in", "agreement", "with"),
    ("as", "in"),
    ("cf",),
)
# Heads that cut only after a comma.
COMMA_HEADS = (("against",),)
_PARTICIPLE_END = ("ing", "ed")
_NOT_NON_FINITE = frozenset({"during", "string", "thing", "bed", "red", "need", "speed", "feed"})
NP_STOPS = PREPOSITIONS | FINITE_AUXILIARIES | COORDINATORS | SUBORDINATORS
NP_PUNCTUATION = {"-", "/", "%", "°", "'", "’"}
OPENING = {"(": ")", "[": "]"}


def measure(block):
    """The measure of a block of text: the median length of its lines.

    In typography the measure is the line length of a text block (Bringhurst, The Elements of
    Typographic Style, ch. 2.1); a wrapped paragraph fills it on every line but its last. The
    evidence keeps no coordinates, so the measure is read from the text: the median line length
    of the block, which the lines of a wrapped paragraph set and a short last line does not move.
    With page layout (a block's right margin and a line's right edge) the same comparison would
    be made on those edges instead.
    """
    lengths = [len(line.rstrip()) for line in block.splitlines() if line.strip()]
    return statistics.median(lengths) if lengths else 0


def _wrapped(text, cut, line_measure):
    """Whether a line break is only the page wrapping a sentence.

    The line before fills the measure of its block (the first word of the next line would not have
    fitted on it) and runs on in the middle of a sentence (it ends in a lowercase letter or a
    comma); the line after continues it (it opens in lowercase, a digit or a bracket). A short line
    that ends a paragraph, a table row, a list item or a heading fails one of the three.
    """
    if text[cut.start() : cut.end()] != "\n":
        return False
    before = text[: cut.start()].rstrip(" ")
    line = before[before.rfind("\n") + 1 :]
    after = text[cut.end() :]
    first_word = re.match(r"\S+", after)
    return bool(
        first_word
        and len(line) + 1 + len(first_word.group()) > line_measure
        and re.search(r"[a-z,]$", line)
        and re.match(r"[a-z0-9(]", after)
    )


def sentence_bounds(text, offset, block=None):
    """The printed sentence holding ``offset``: (start, end) in ``text``.

    Cut at a sentence end or a line break, except after an abbreviation and except where the
    line break only wraps a sentence over two lines. ``block`` is the text block the lines belong
    to (its paragraph on the page); without it the measure is taken from ``text`` itself.
    """
    line_measure = measure(block if block else text)
    start = 0
    for cut in clause_cues.SENTENCE_BREAK.finditer(clause_cues.segmentation_view(text)):
        if _wrapped(text, cut, line_measure):
            continue
        if cut.start() >= offset:
            return start, cut.start()
        start = cut.end()
    return start, len(text)


def _word(token):
    return token[0].lower()


def _head_at(tokens, i, after_comma=False):
    """The comparison head that starts at token ``i`` (its token count), or 0."""
    words = tuple(_word(t) for t in tokens[i : i + 3])
    for head in COMPARISON_HEADS + (COMMA_HEADS if after_comma else ()):
        if words[: len(head)] == head:
            return len(head)
    if words[:1] == ("than",):
        nxt = tokens[i + 1][0] if i + 1 < len(tokens) else ""
        if not re.match(r"[\d~≈<>]", nxt):
            return 1
    return 0


def _non_finite(tokens, i):
    word = _word(tokens[i])
    if word in _NOT_NON_FINITE or not word.isalpha() or len(word) < 4:
        return False
    return word.endswith(_PARTICIPLE_END) or word in clause_cues._IRREGULAR_PARTICIPLES


def _reporting(tokens, i):
    """A complement that attributes content ("as reported in", "according to", "reported by")."""
    if i >= len(tokens):
        return False
    word = _word(tokens[i])
    if word == "as" and i + 1 < len(tokens):
        return _word(tokens[i + 1]) in clause_cues.REPORTING_VERBS
    return word in clause_cues.REPORTING_VERBS or word == "according"


def _is_segment_opener(tokens, i):
    if _reporting(tokens, i):
        return False
    if _head_at(tokens, i, after_comma=True):
        return True
    # A participle that a finite auxiliary follows is a gerund subject, not a supplement.
    follows = _word(tokens[i + 1]) if i + 1 < len(tokens) else ""
    return _non_finite(tokens, i) and follows not in FINITE_AUXILIARIES


def _paren_close(tokens, i):
    """The index of the token that closes the bracket opened at ``i``, or None."""
    depth = 0
    for k in range(i, len(tokens)):
        if tokens[k][0] in OPENING:
            depth += 1
        elif tokens[k][0] in {")", "]"}:
            depth -= 1
            if depth == 0:
                return k
    return None


def _marker_only(text):
    """Whether the bracket content is a bare marker: a number, a note, or an author-year."""
    inner = re.sub(r"[()\[\]]", "", text).strip()
    inner = re.sub(r"^(?:see|cf|e\.g|i\.e)\.?\s+", "", inner, flags=re.IGNORECASE)
    return bool(
        re.fullmatch(r"\d+[a-z]?(?:\s*[,;–-]\s*(?:pp?\.\s*)?\d+[a-z]?)*", inner)
        or re.fullmatch(r"[A-Z][\w'’-]+(?:\s+et\s+al\.?)?,?\s*(?:19|20)\d\d[a-z]?", inner)
    )


def _finite(tokens, lo, hi):
    return any(_word(tokens[k]) in FINITE_AUXILIARIES for k in range(lo, hi))


def value_phrase(sentence, offset):
    """The phrase of the value printed at ``offset`` of ``sentence`` (one printed sentence).

    Returns ``{"start", "end", "excised", "framing", "own_np", "kind"}`` in characters of
    ``sentence``: the phrase, the ranges set aside inside it, the fronted adjunct that frames it
    (or None), the noun phrase of the value itself, and how the phrase was found (``host``,
    ``fronted``, ``set_aside``).
    """
    tokens = _tokens(sentence)
    n = len(tokens)
    if not n:
        return {
            "start": 0,
            "end": len(sentence),
            "excised": [],
            "framing": None,
            "own_np": (0, len(sentence)),
            "kind": "host",
        }
    v = next((k for k in range(n) if tokens[k][2] > offset), n - 1)

    def span(lo, hi):  # token indexes lo..hi (exclusive) as characters
        if lo >= hi:
            return (tokens[min(lo, n - 1)][1], tokens[min(lo, n - 1)][1])
        return (tokens[lo][1], tokens[hi - 1][2])

    # Parentheticals that hold more than a marker, and supplementive or comparison segments.
    sets = []  # (open index, close index inclusive, tail)
    depth_at = [0] * n
    k = 0
    while k < n:
        word = tokens[k][0]
        if word == "[":
            close = _paren_close(tokens, k)
            if close is not None:
                for j in range(k, close + 1):
                    depth_at[j] = 1
                k = close + 1
                continue
        if word == "(":
            close = _paren_close(tokens, k)
            if close is not None:
                text = sentence[tokens[k][1] : tokens[close][2]]
                if not _marker_only(text):
                    sets.append((k, close, False, "paren"))
                for j in range(k, close + 1):
                    depth_at[j] = 1
                k = close + 1
                continue
        k += 1
    k = 0
    while k < n:
        if tokens[k][0] == "," and depth_at[k] == 0 and k + 1 < n:
            nxt = k + 1
            if _word(tokens[nxt]) not in RELATIVES | COORDINATORS | SUBORDINATORS and (
                _is_segment_opener(tokens, nxt)
            ):
                close = next(
                    (
                        j
                        for j in range(nxt + 1, n)
                        if depth_at[j] == 0 and tokens[j][0] in {",", ";", ":", ".", "!", "?"}
                    ),
                    None,
                )
                if close is not None and tokens[close][0] == ",":
                    sets.append((k, close, False, "comma"))
                    k = close
                    continue
                sets.append((k, (close - 1) if close is not None else n - 1, True, "comma"))
                break
        k += 1
    # A comparison head without a comma starts a tail segment too.
    for k in range(n):
        if depth_at[k] == 0 and _head_at(tokens, k) and not any(a <= k <= b for a, b, _, _ in sets):
            end = next(
                (
                    j
                    for j in range(k + 1, n)
                    if depth_at[j] == 0 and tokens[j][0] in {",", ";", ":", ".", "!", "?"}
                ),
                n,
            )
            sets.append((k, end - 1, True, "head"))
    sets.sort()
    inside = next((s for s in sets if s[0] <= v <= s[1]), None)

    # The fronted adjunct F.
    first = _word(tokens[0])
    framing = None
    frame_end = -1
    if (
        first in PREPOSITIONS
        or first in SUBORDINATORS
        or _head_at(tokens, 0)
        or (_non_finite(tokens, 0) and not tokens[0][0][0].islower())
    ):
        for k in range(1, n):
            if (
                tokens[k][0] == ","
                and depth_at[k] == 0
                and not (k + 1 < n and _word(tokens[k + 1]) in RELATIVES)
            ):
                frame_end = k
                break
        if frame_end > 0 and frame_end < n - 1:
            framing = span(0, frame_end)
    if inside is None and frame_end > 0 and v < frame_end:
        s, e = span(0, frame_end)
        return {
            "start": s,
            "end": e,
            "excised": [],
            "framing": None,
            "own_np": _own_np(tokens, v, span),
            "kind": "fronted",
        }
    if inside is not None:
        lo, hi = inside[0], inside[1]
        s, e = span(lo + 1 if tokens[lo][0] in {",", "("} else lo, hi + 1)
        return {
            "start": s,
            "end": e,
            "excised": [],
            "framing": framing,
            "own_np": _own_np(tokens, v, span),
            "kind": "set_aside",
        }

    # Host phrase: scan right then left from the value.
    def in_set(k):
        return next((s for s in sets if s[0] <= k <= s[1]), None)

    right = n
    k = v + 1
    while k < n:
        hit = in_set(k)
        if hit is not None:
            if hit[2]:  # a tail segment cuts the phrase
                right = hit[0]
                break
            k = hit[1] + 1
            continue
        word = tokens[k][0]
        if word in {";", ":", ".", "!", "?"} and depth_at[k] == 0:
            right = k
            break
        if word == "," and k + 1 < n:
            nxt = _word(tokens[k + 1])
            if nxt in (COORDINATORS | SUBORDINATORS) - RELATIVES and not _reporting(tokens, k + 1):
                right = k
                break
        if _word(tokens[k]) in COORDINATORS and (
            _finite(tokens, 0, k) and _finite(tokens, k + 1, n)
        ):
            right = k
            break
        k += 1

    def scan_left(cut_at_set):
        k = v - 1
        while k >= 0:
            hit = in_set(k)
            if hit is not None:
                if cut_at_set and hit[3] == "comma" and hit[2] is False and k == hit[1]:
                    return k + 1
                k = hit[0] - 1
                continue
            word = tokens[k][0]
            if word in {";", ":"} and depth_at[k] == 0:
                return k + 1
            if (
                word == ","
                and k + 1 < n
                and _word(tokens[k + 1]) in ((COORDINATORS | SUBORDINATORS) - RELATIVES)
                and not _reporting(tokens, k + 1)
            ):
                return k + 1
            if _word(tokens[k]) in COORDINATORS and (
                _finite(tokens, 0, k) and _finite(tokens, k + 1, n)
            ):
                return k + 1
            k -= 1
        return 0

    left = scan_left(True)
    # The clause of the value: the same cuts, but a set-aside segment does not end it.
    clause_left = scan_left(False)
    if frame_end > 0:
        left = max(left, frame_end + 1)
    s, e = span(left, right)
    excised = [span(a, b + 1) for a, b, _, _ in sets if left <= a and b < right]
    return {
        "start": s,
        "end": e,
        "excised": excised,
        "framing": framing,
        "own_np": _own_np(tokens, v, span),
        "kind": "host",
        "clause": span(max(clause_left, frame_end + 1 if frame_end > 0 else 0), right),
    }


def _own_np(tokens, v, span):
    """The run of tokens around the value that no verb, preposition or punctuation interrupts."""
    n = len(tokens)

    def stop(k):
        word = tokens[k][0]
        return (
            _word(tokens[k]) in NP_STOPS
            or (not word[0].isalnum() and word not in NP_PUNCTUATION)
            or _head_at(tokens, k) > 0
        )

    lo = v
    while lo > 0 and not stop(lo - 1):
        lo -= 1
    hi = v + 1
    while hi < n and not stop(hi):
        hi += 1
    return span(lo, hi)
