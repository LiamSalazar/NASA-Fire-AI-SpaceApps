"""Scholarly abbreviations, as referenced classes shared by every reading that needs them.

Reference: The Chicago Manual of Style, 17th ed. (University of Chicago Press, 2017),
chapter 10 (abbreviations). Membership is copied from that chapter's list of scholarly
and bibliographic abbreviations, never from the documents under study; a member the
chapter does not list does not belong here. The section numbers inside the chapter are
to be verified against the printed edition before the freeze.

Two classes live here today:

- ``BIBLIOGRAPHIC_ABBREVIATIONS``: the abbreviations a citation is made of (volume,
  number, page, "et al.", editor, translator, revised, "vs.", figure). Read by
  ``document_structure.FRAGMENT_END`` to tell that a line ends a reference fragment.
- ``POINTER_ABBREVIATIONS``: the printed abbreviations of the nouns that point to another
  part of the same text (Fig., Sec., Ch., p., pp.), read by
  ``clause_cues.ENDOPHORIC_MARKER``.

``SCHOLARLY_ABBREVIATIONS`` is their union and the class that sentence segmentation
extends (list 5: cf., e.g., i.e., viz., ca., etc., Eq., Ref., and so on, with the
AIP Style Manual for physics cross-reference labels). Extend this module there; a
reading that needs a subset keeps its own named subclass, so that adding a member for one
reading does not silently change another.
"""

import os
import re

# What a citation is made of (Chicago 17, ch. 10). "al" is the abbreviated word of
# "et al."; initials and years are not abbreviations and are read by their shape.
BIBLIOGRAPHIC_ABBREVIATIONS = (
    "vol",
    "no",
    "p",
    "pp",
    "al",
    "ed",
    "eds",
    "trans",
    "rev",
    "fig",
    "vs",
)

# The printed abbreviations of the endophoric nouns figure, section, chapter, page.
POINTER_ABBREVIATIONS = ("fig", "figs", "sec", "ch", "p", "pp")

SCHOLARLY_ABBREVIATIONS = tuple(
    sorted(set(BIBLIOGRAPHIC_ABBREVIATIONS) | set(POINTER_ABBREVIATIONS))
)


def alternation(members):
    """A regex alternation of ``members``, longest first so that no member shadows a
    longer one that starts with it."""
    return "|".join(re.escape(m) for m in sorted(set(members), key=lambda m: (-len(m), m)))


# --- Sentence segmentation (list 5) -----------------------------------------------------
# References: The Chicago Manual of Style, 17th ed. (2017), chapter 10 (scholarly
# abbreviations); the AIP Style Manual, for the cross-reference labels Fig., Eq., Ref.
# Matching normalises internal spaces ("e. g.", "op. cit."). Case: e.g., i.e., etc., et al.,
# ibid., op. cit. and the labels fig/eq/sec/ch/vol/ref/p/ed/n are case-insensitive; cf., viz.,
# vs., ca. are lower case or first capital only ("CA" is a state); "no." is "no." or "No."
# ("NO" is nitric oxide).
#
# Groups, by what a period after the member means (details in ``abbreviation_period``):
# - never an end: e.g., i.e., cf., viz., vs., ca.
# - can end: etc., et al., ibid., op. cit.
# - lettered labels (fig, eq, sec, ch, vol) and numbered labels (ref, no, n, p, ed).
SEGMENTATION_FLAG = "SCIENCE_ABBREVIATION_SEGMENTATION"
SEGMENTATION_INPUT_FLAG = "SCIENCE_ABBREVIATION_SEGMENTATION_INPUT"
MASK = "․"

# Members come from the named classes above where they overlap. "trans" and "rev" are
# bibliographic (BIBLIOGRAPHIC_ABBREVIATIONS) but are left out here: the list-5 class names
# no segmentation use for them, and "rev." before a numeral is too often a word.
_ALL = set(BIBLIOGRAPHIC_ABBREVIATIONS) | set(POINTER_ABBREVIATIONS)
# Labels that may also be followed by a one-letter or roman label ("Fig. A", "Vol. IV").
_LETTERED = (_ALL & {"fig", "figs", "sec", "ch", "vol"}) | {"vols", "eq", "eqs"}
# Labels followed only by a numeral or "(" and a numeral.
_NUMBERED = (_ALL & {"p", "pp", "ed", "eds"}) | {"n", "nn", "ref", "refs"}
# "no." is a label only as "no." or "No." (never "NO", nitric oxide).
_NUMBERED_CASED = ("No", "no", "Nos", "nos")

_NEVER_END = r"(?i:e\.\s*g|i\.\s*e)|[Cc]f|[Vv]iz|[Vv]s|[Cc]a"
_CAN_END = r"(?i:etc|et\s+al|ibid|op\.\s*cit)"
_LETTER = r"[^\W\d_]"
_MEMBER = re.compile(
    r"(?<!" + _LETTER + r")(?:(?P<never>" + _NEVER_END + r")|(?P<can>" + _CAN_END + r")|"
    r"(?P<lettered>(?i:" + alternation(_LETTERED) + r"))|"
    r"(?P<numbered>(?i:" + alternation(_NUMBERED) + r")|" + alternation(_NUMBERED_CASED) + r"))\."
)
_ROMAN = r"(?:xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)|(?:XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)"
_NUMERAL_NEXT = re.compile(r"[ \t]*(?:\([ \t]*)?\d")
_LETTERED_NEXT = re.compile(
    r"[ \t]*(?:\([ \t]*)?(?:\d|(?:" + _ROMAN + r"|[A-Za-z])(?!" + _LETTER + r"|\d))"
)
# After a can-end member a number is a year or a reference number closed by punctuation;
# any other number starts the next sentence.
_YEAR_OR_REFERENCE = re.compile(r"(?:(?:1[89]|20)\d\d|\d{1,3}(?=[,;:.)\]]))(?!\d)")
_ET_AL = re.compile(r"et\s+al", re.IGNORECASE)


def _closes_member(text, member):
    """True when the final period of ``member`` (a match of ``_MEMBER`` in ``text``)
    closes an abbreviation, that is, does not end a sentence."""
    end = member.end()
    if member.group("never"):
        return True
    if member.group("numbered"):
        return _NUMERAL_NEXT.match(text, end) is not None
    if member.group("lettered"):
        # "after 60 sec. A flame": a unit of time after a number, not a label.
        if member.group("lettered").lower() == "sec" and re.search(
            r"\d[ \t]*$", text[max(0, member.start() - 8) : member.start()]
        ):
            return False
        return _LETTERED_NEXT.match(text, end) is not None
    tail = text[end:]
    gap = tail[: len(tail) - len(tail.lstrip())]
    rest = tail[len(gap) :]
    if not rest or "\n" in gap:
        return False
    if not gap:
        return True
    if rest[0].isupper():
        return False
    if rest[0].isdigit():
        return _YEAR_OR_REFERENCE.match(rest) is not None
    return not (rest[0] == "(" and not _ET_AL.match(member.group("can")))


def abbreviation_period(text, i):
    """True when the period at ``text[i]`` closes a member of the class, so that it does
    not end a sentence; False for any other period and for any other character.

    It reads the mask: the period is an abbreviation's exactly when
    ``mask_abbreviation_periods`` masks it. The decision: find the member whose period is
    ``i`` (its final period, or the inner period of "e.g." and "op. cit."), then read what
    follows. An inner period always belongs to its member. A final period belongs to it by
    group:
    - never an end (e.g., i.e.; cf., viz., vs., ca. in lower case or first capital);
    - labels not before a line break: fig/eq/sec/ch/vol before a numeral, "(" and a
      numeral, a roman numeral or a one-letter label; ref, no, n, p, ed only before a
      numeral or "(" and a numeral; "sec." after a number is a unit and ends;
    - can end (etc., et al., ibid., op. cit.): an end at the end of the text, at a line
      break, before a capital, before a number that is not a year or a reference number
      closed by punctuation; also before "(" except after "et al."."""
    if not isinstance(text, str) or not 0 <= i < len(text) or text[i] != ".":
        return False
    return mask_abbreviation_periods(text)[i] == MASK


def mask_abbreviation_periods(text):
    """``text`` with the periods that close a member of the class replaced by U+2024, one
    character each: same length, same offsets, quotes never altered."""
    text = text or ""
    if "." not in text:
        return text
    chars = None
    for member in _MEMBER.finditer(text):
        masked = [k for k in range(member.start(), member.end() - 1) if text[k] == "."]
        if _closes_member(text, member):
            masked.append(member.end() - 1)
        if masked:
            chars = chars or list(text)
            for k in masked:
                chars[k] = MASK
    return "".join(chars) if chars else text


def segmentation_view(text):
    """``text`` for finding sentence boundaries: with SCIENCE_ABBREVIATION_SEGMENTATION on (the
    default; "0" turns it off) its abbreviation periods are masked (same offsets; slice the
    original text), else ``text`` itself, unchanged."""
    if os.getenv(SEGMENTATION_FLAG, "1") == "1":
        return mask_abbreviation_periods(text)
    return text


def segmentation_input_view(text):
    """The same for the readings that change model input
    (SCIENCE_ABBREVIATION_SEGMENTATION_INPUT=1)."""
    if os.getenv(SEGMENTATION_INPUT_FLAG, "0") == "1":
        return mask_abbreviation_periods(text)
    return text


def split_by_view(pattern, text, maxsplit=0, flags=0):
    """``re.split`` of ``text`` at ``pattern`` (no capturing group), the cuts found on
    ``segmentation_view(text)`` and the pieces cut from ``text``. With the flag off it is
    ``re.split`` itself."""
    view = segmentation_view(text)
    if view is text:
        return re.split(pattern, text, maxsplit=maxsplit, flags=flags)
    rx = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
    pieces, last = [], 0
    for cut in rx.finditer(view):
        if maxsplit and len(pieces) >= maxsplit:
            break
        pieces.append(text[last : cut.start()])
        last = cut.end()
    pieces.append(text[last:])
    return pieces


class PrintedMatch:
    """A match found on the masked text that reads its groups from the printed text:
    ``group``, ``m[name]``, ``start``, ``end`` and ``span`` as for ``re.Match``."""

    def __init__(self, match, text):
        self._match, self._text = match, text

    def __getattr__(self, name):
        return getattr(self._match, name)

    @property
    def string(self):
        return self._text

    def groups(self, default=None):
        n = self._match.re.groups
        return tuple(
            self._printed(k) if self._match.span(k)[0] >= 0 else default for k in range(1, n + 1)
        )

    def groupdict(self, default=None):
        return {
            k: (self._printed(k) if self._match.span(k)[0] >= 0 else default)
            for k in self._match.re.groupindex
        }

    def expand(self, template):
        # Groups are read from the masked match and the mask is read back as a period.
        return self._match.expand(template).replace(MASK, ".")

    def group(self, *keys):
        keys = keys or (0,)
        found = [self._printed(k) for k in keys]
        return found[0] if len(found) == 1 else tuple(found)

    def __getitem__(self, key):
        return self._printed(key)

    def _printed(self, key):
        start, end = self._match.span(key)
        return None if start < 0 else self._text[start:end]


class ViewPattern:
    """A compiled pattern whose windows (``[^.;]*`` and the like) stop only at periods that
    end a sentence: it matches on ``segmentation_view(text)`` and gives its matches as
    ``PrintedMatch``, so offsets and groups are those of ``text``. With the flag off it is
    the compiled pattern itself. Everything else (``pattern``, ``flags``, ...) is the
    compiled pattern's own."""

    def __init__(self, compiled):
        self._compiled = compiled

    def __getattr__(self, name):
        return getattr(self._compiled, name)

    def _wrap(self, found, string):
        return None if found is None else PrintedMatch(found, string)

    def search(self, string, *args):
        view = segmentation_view(string)
        found = self._compiled.search(view, *args)
        return found if view is string else self._wrap(found, string)

    def match(self, string, *args):
        view = segmentation_view(string)
        found = self._compiled.match(view, *args)
        return found if view is string else self._wrap(found, string)

    def fullmatch(self, string, *args):
        view = segmentation_view(string)
        found = self._compiled.fullmatch(view, *args)
        return found if view is string else self._wrap(found, string)

    def finditer(self, string, *args):
        view = segmentation_view(string)
        if view is string:
            return self._compiled.finditer(string, *args)
        return (PrintedMatch(m, string) for m in self._compiled.finditer(view, *args))

    def sub(self, repl, string, count=0):
        """``re.sub`` on the printed text, the matches found on the masked text, with the
        same template (or callable) semantics for ``repl`` as with the flag off."""
        view = segmentation_view(string)
        if view is string:
            return self._compiled.sub(repl, string, count=count)
        out, last = [], 0
        for n, found in enumerate(self._compiled.finditer(view), 1):
            out.append(string[last : found.start()])
            printed = PrintedMatch(found, string)
            out.append(repl(printed) if callable(repl) else printed.expand(repl))
            last = found.end()
            if count and n >= count:
                break
        out.append(string[last:])
        return "".join(out)
