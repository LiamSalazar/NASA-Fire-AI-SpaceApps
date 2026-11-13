"""Printed layout: running headers, page edges, headings, captions and sentence lines."""

import os
import re
from dataclasses import dataclass

from nasa_fire_ai.ingestion.document_memo import document_memo
from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.source_spans import mentions, normalized


def running_headers(evidence):
    """Lines a document prints at the top or bottom of most of its pages.

    Only lines of four or more words count, compared without page numbers.
    """
    from collections import Counter

    pages = list(evidence.values())
    counts = Counter()
    for page in pages:
        lines = [line.strip() for line in page.get("text", "").splitlines() if line.strip()]
        edge = {
            normalized(re.sub(r"\d+", " ", line))
            for line in lines[:3] + lines[-3:]
            if len(re.findall(r"[A-Za-z]{2,}", line)) >= 4
        }
        counts.update(edge)
    floor = max(3, int(0.4 * len(pages)))
    return sorted(line for line, n in counts.items() if n >= floor and line)


PRINTED_CAPTION_LINE = re.compile(r"\s*(?:Figure|Fig\.|Table)\s+\d+[A-Za-z]?\s*[-–—:.]\s*\S")


# The caption reader (SCIENCE_CAPTION_READER). Float labels are the numbered
# figure and table labels of scientific and technical reports (ANSI/NISO
# Z39.18-2005, sections 5.4.3 and 5.4.4). A label followed by a lower-case word
# ("Figure 3 shows ...") is a reference inside a sentence, not a caption.
_FLOAT_NUMBER = r"(?:\d+[A-Za-z]?|[IVXLC]+)"
CAPTION_HEAD = re.compile(
    r"[ \t]*(?P<label>(?i:figure|fig|table))\.?[ \t]*[-–—]?[ \t]*(?P<number>"
    + _FLOAT_NUMBER
    + r")(?:[ \t]*[-–—:.|]|[ \t]+(?=[A-Z])|[ \t]*$)"
)
ELEMENT_REFERENCE = re.compile(
    r"\b(?P<label>(?i:figures?|figs?|tables?))\b\.?[ \t]*(?P<numbers>"
    + _FLOAT_NUMBER
    + r"(?:[ \t]*(?:,|&|-|–|to|and)[ \t]*\d+[A-Za-z]?)*)"
)
CAPTION_PREFIX = r"(?:figure|fig\.?|table)\s*[-–—]?\s*" + _FLOAT_NUMBER.lower() + r"\s*[-–—:.]?\s*"


def caption_reader_enabled():
    return os.getenv("SCIENCE_CAPTION_READER", "1") != "0"


@dataclass(frozen=True)
class CaptionHead:
    kind: str
    number: str
    start: int
    head_end: int
    text_after: str


def caption_head(line):
    """The caption head a line opens with, or None.

    A float label, an optional dash, a number, then a separator (a dash, colon,
    full stop or bar) or white space before a capital letter. Offsets are
    relative to the line.
    """
    m = CAPTION_HEAD.match(line)
    if not m:
        return None
    kind = "table" if m.group("label").lower() == "table" else "figure"
    return CaptionHead(
        kind=kind,
        number=m.group("number"),
        start=m.start("label"),
        head_end=m.end(),
        text_after=line[m.end() :].strip(),
    )


def caption_lines(text):
    """Captions in a text: a head and its continuation lines.

    A caption runs to a blank line or the next caption head.
    """
    found, position, current = [], 0, None
    for line in text.split("\n"):
        head = caption_head(line)
        if current is not None and (head or not line.strip()):
            current["end"] = current.pop("last")
            found.append(current)
            current = None
        if head:
            current = {
                "kind": head.kind,
                "number": head.number,
                "start": position + head.start,
                "first_line_end": position + len(line),
                "last": position + len(line),
            }
        elif current is not None:
            current["last"] = position + len(line)
        position += len(line) + 1
    if current is not None:
        current["end"] = current.pop("last")
        found.append(current)
    for caption in found:
        caption["quote"] = text[caption["start"] : caption["end"]]
    return found


def element_references(text):
    """Figure and table references inside running text ("Figures 11 and 12")."""
    return [
        {
            "kind": "table" if m.group("label").lower().startswith("table") else "figure",
            "numbers": re.findall(r"\d+[A-Za-z]?|[IVXLC]+", m.group("numbers")),
            "start": m.start(),
            "end": m.end(),
        }
        for m in ELEMENT_REFERENCE.finditer(text)
    ]


def caption_prefixed(label, normalized_text):
    """Whether a label is printed right after a caption head (the inline form)."""
    return bool(re.search(CAPTION_PREFIX + re.escape(label), normalized_text, re.IGNORECASE))


def is_caption_line(line):
    """A printed caption line with its text: the old pattern, or the reader's."""
    if not caption_reader_enabled():
        return bool(PRINTED_CAPTION_LINE.match(line))
    head = caption_head(line.lstrip("\n"))
    return bool(head and head.text_after)


def opens_with_float_label(quote):
    """A quote that opens with a caption head or a figure or table reference."""
    if not caption_reader_enabled():
        return bool(re.match(r"\s*(?:Fig(?:ure)?\.?|Table)\s+\d", quote, re.IGNORECASE))
    first = quote.lstrip().split("\n", 1)[0]
    if caption_head(first):
        return True
    return any(r["start"] == 0 for r in element_references(first))


def statement_caption(text):
    """A caption head on a line after the first line of a statement, or None.

    A bare head ("Figure 4.") counts only when the line before does not visibly
    continue (a comma, colon, open bracket, hyphen or a function word), and
    nothing follows it; otherwise it is the wrapped object of the sentence.
    """
    lines = text.split("\n")
    previous = ""
    for index, line in enumerate(lines):
        if index and line.strip():
            head = caption_head(line)
            if head and head.text_after:
                return head
            if head and not any(x.strip() for x in lines[index + 1 :]):
                last = re.findall(r"[A-Za-z]+$", previous)
                if not (
                    previous[-1:] in {",", ";", ":", "(", "-", "–"}
                    or (last and last[0].lower() in CONTINUING_WORDS)
                ):
                    return head
        if line.strip():
            previous = line.rstrip()
    return None


def previous_page_ends_a_sentence(spans, evidence):
    """Whether the body of the page before each span's page ends with a full stop."""
    headers = set(running_headers(evidence))
    for span in spans:
        current = evidence[span["evidence_id"]]
        previous = [
            p
            for p in evidence.values()
            if p["source_id"] == current["source_id"]
            and current.get("page") is not None
            and p.get("page") == current["page"] - 1
        ]
        if len(previous) != 1:
            continue
        lines = [line.strip() for line in previous[0]["text"].splitlines() if line.strip()]
        while lines:
            if re.fullmatch(r"\d{1,4}", lines[-1]) or (
                normalized(re.sub(r"\d+", " ", lines[-1])) in headers
            ):
                lines.pop()
                continue
            # A figure caption at the foot of the page, with its wrapped line.
            caption = [
                i for i in range(max(0, len(lines) - 2), len(lines)) if is_caption_line(lines[i])
            ]
            if not caption:
                break
            del lines[caption[-1] :]
        if lines and lines[-1][-1] not in ".!?:":
            return False
    return True


def page_edge_prefix(text, evidence, spans=()):
    """The running header, page number and caption lines that open a passage, if any.

    Only a prefix that starts with a running header of the document counts, and a
    whole sentence of at least five words must follow it, not the rest of one
    begun on the previous page.
    """
    headers = set(running_headers(evidence))
    lines = text.split("\n")
    consumed, header_seen = 0, False
    for line in lines[:-1]:
        stripped = line.strip()
        if not stripped or re.fullmatch(r"\d{1,4}", stripped):
            consumed += 1
        elif normalized(re.sub(r"\d+", " ", stripped)) in headers:
            consumed += 1
            header_seen = True
        elif header_seen and is_caption_line(stripped):
            consumed += 1
        else:
            break
    if not header_seen:
        return ""
    prefix = "\n".join(lines[:consumed]) + "\n"
    rest = text[len(prefix) :]
    lead = len(rest) - len(rest.lstrip())
    # A lowercase start continues a sentence from the previous page, and a caption
    # alone is no sentence: both keep the header hold.
    # 'Cooling Loop Unit” (CLU)': a quotation closed before it opens.
    closes_first = "”" in rest and ("“" not in rest or rest.find("”") < rest.find("“"))
    if (
        len(re.findall(r"[A-Za-z]{2,}", rest)) < 5
        or not re.match(r"[A-Z]", rest.lstrip())
        or is_caption_line(rest.lstrip())
        or closes_first
        or not previous_page_ends_a_sentence(spans, evidence)
    ):
        return ""
    return prefix + rest[:lead]


def page_edge_lines(evidence):
    """Lines of any length a document prints at the edge of most of its pages.

    Compared without digits, so a date or page number does not make them differ;
    used only next to a running header, where a short date line is page furniture.
    """
    from collections import Counter

    pages = list(evidence.values())
    counts = Counter()
    for page in pages:
        lines = [line.strip() for line in page.get("text", "").splitlines() if line.strip()]
        counts.update(
            {
                normalized(re.sub(r"\d+", " ", line))
                for line in lines[:3] + lines[-3:]
                if re.search(r"[A-Za-z]{2,}", line)
            }
        )
    floor = max(3, int(0.4 * len(pages)))
    return {line for line, n in counts.items() if n >= floor and line}


def page_edge_suffix(text, evidence):
    """The running footer and what follows it, when they close a passage after its sentence.

    "• Panel-scale burn screening ... one-polymer trials / 9th
    Symposium on Habitat Engineering / May 3-7, 2026 / 5 /
    Examples of ...": the footer, its date and page number end the sentence, and
    the slide's next block is not part of it. A sentence that continues after the
    footer (a lowercase word, as across a page break) is not cut.
    """
    headers = set(running_headers(evidence))
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if normalized(re.sub(r"\d+", " ", lines[index].strip())) not in headers:
            continue
        before = "\n".join(lines[:index])
        if len(re.findall(r"[A-Za-z]{2,}", before)) < 5:
            return ""
        edge = page_edge_lines(evidence)
        after = index + 1
        while after < len(lines) and (
            not lines[after].strip()
            or re.fullmatch(r"\d{1,4}", lines[after].strip())
            or normalized(re.sub(r"\d+", " ", lines[after].strip())) in headers | edge
        ):
            after += 1
        rest = "\n".join(lines[after:]).strip()
        if rest and not re.match(r"[A-Z•\-–]", rest):
            return ""
        return text[len(before.rstrip()) :]
    return ""


OUTLINE_MARKER = re.compile(r"^((?:\d+(?:\.\d+)*[.)]?)|(?:[A-Z][.)])|(?:[IVXLCDM]+[.)]))\s+(\S.*)$")


def outline_marker_kind(marker):
    if re.fullmatch(r"\d+(?:\.\d+)*[.)]?", marker):
        return "number"
    if re.fullmatch(r"[IVXLCDM]+[.)]", marker):
        return "roman"
    return "letter"


def heading_outline_name(label, document):
    """The printed name of a label that copies its heading's outline marker, if any.

    "B. Delta Test Center (DTC) Reduced Load Trials" for the printed
    heading "B. Delta Test ...": the marker numbers the heading, it is not part of
    the name. Only a marker that is printed on the heading, and that another
    heading of the document continues as a sequence (A./B., 2.1/2.2, III./IV.),
    counts; a lone initial ("J. Smith Apparatus") is part of a name.
    """
    sections = [h.get("title", "").strip() for h in document.get("sections", [])]
    for title in sections:
        m = OUTLINE_MARKER.match(title)
        if not m or normalized(title) != normalized(label):
            continue
        kind = outline_marker_kind(m.group(1))
        siblings = [
            o.group(1)
            for other in sections
            if other != title and (o := OUTLINE_MARKER.match(other))
        ]
        if any(outline_marker_kind(x) == kind and x != m.group(1) for x in siblings):
            return re.sub(r"\s+", " ", m.group(2)).strip()
    return None


def acronym_printed_form(label, quotes):
    """The printed name a label abbreviates with its acronym, if a quote prints it.

    "MFV 4.1, unit 17" abbreviates the printed "Main Feed Valve (MFV)
    4.1, unit 17": the label starts with the acronym the text defines.
    """
    words = label.split()
    if not words or not re.fullmatch(r"[A-Z][A-Z0-9-]{1,9}", words[0]):
        return None
    rest = r"\s+".join(re.escape(w) for w in words[1:])
    pattern = (
        r"(?:[A-Z][\w-]*\s+){1,8}\(\s*"
        + re.escape(words[0])
        + r"\s*\)"
        + (r"\s+" + rest if rest else "")
        + r"(?![\w-])"
    )
    for quote in quotes:
        m = re.search(pattern, quote)
        if m:
            return re.sub(r"\s+", " ", m.group())
    return None


def caption_only_label(label, evidence):
    """Whether every printing of a label is the body of a figure or table caption.

    "Figure 4: Wool blend cloth (Brand-Q), 6.5 kPa limiting oxygen data" names a
    plot, not a group of experiments; a group the text itself names is printed
    outside its captions too.
    """
    key = re.escape(normalized(label)[:40])
    if not key:
        return False
    total = captioned = 0
    for ev in evidence.values():
        text = normalized(ev.get("text", ""))
        total += len(re.findall(key, text, re.IGNORECASE))
        if caption_reader_enabled():
            captioned += len(re.findall(CAPTION_PREFIX + key, text, re.IGNORECASE))
        else:
            captioned += len(
                re.findall(
                    r"(?:figure|fig\.?|table)\s*\d+\s*[-–—:.]?\s*" + key, text, re.IGNORECASE
                )
            )
    return bool(captioned) and captioned == total


CONTINUING_WORDS = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "or",
    "to",
    "with",
    "in",
    "at",
    "by",
    "for",
    "from",
    "as",
    "than",
    "on",
    "into",
    "under",
    "between",
}


def line_units(text):
    """The text with line breaks that end a slide or caption line marked as ``;``.

    A break before a capitalized or bulleted line ends the unit unless the
    previous line visibly continues (a hyphen, comma or open parenthesis, or a
    function word such as "with" or "the").
    """
    lines = text.split("\n")
    out = lines[0]
    for line in lines[1:]:
        previous = out.rstrip()
        last = re.findall(r"[A-Za-z]+$", previous)
        continues = (
            not previous
            or previous[-1] in ",;:(-–"
            or (last and last[0].lower() in CONTINUING_WORDS)
        )
        # Only lines of words (a slide bullet, a caption), never table cells.
        words = (
            len(re.findall(r"[A-Za-z]{2,}", previous.split(";")[-1])) >= 3
            and len(re.findall(r"[A-Za-z]{2,}", line)) >= 3
        )
        if not continues and words and re.match(r"[ \t]*[•A-Z]", line):
            out = previous + ";" + line
        else:
            out = out + "\n" + line
    return out


# List items (SCIENCE_LIST_ITEMS). Markers: the Unicode bullet characters
# (U+2022, U+2023, U+2043, U+25AA, U+25CF, U+25E6), the Symbol-font private-use
# bullets that PDF text layers emit (U+F0B7, U+F0A7), and arabic, latin or roman
# enumerators (ANSI/NISO Z39.18-2005, section 5.3.4, lists).
LIST_GLYPHS = "•‣⁃▪●◦"
LIST_MARKER = re.compile(
    rf"[ \t]*(?P<marker>[{LIST_GLYPHS}]|\(?(?:\d{{1,2}}|[a-z]|[ivx]{{1,4}})[.)](?=[ \t]))"
)
LONE_MARKER = re.compile(
    rf"[ \t]*(?P<marker>[{LIST_GLYPHS}]|\(?(?:\d{{1,2}}|[a-z]|[ivx]{{1,4}})[.)])[ \t]*"
)
SENTENCE_END = re.compile(r"[.!?][”\"]?\s*$")


def list_items_mode():
    """SCIENCE_LIST_ITEMS: "0" off, "1" version 1, "2" version 2 (see list_lead_with_items)."""
    value = os.getenv("SCIENCE_LIST_ITEMS", "2")
    return value if value in {"1", "2"} else "0"


def list_items_enabled():
    return list_items_mode() != "0"


def item_has_clause(text):
    """Whether a list item holds a clause: a finite auxiliary or a regular past form.

    Finite auxiliaries are the closed class of clause_cues (Huddleston and Pullum
    2002); the past form is the regular inflection of a lexical verb (ch. 3). A
    bare present-tense lexical verb reads as clause-less, which is why the
    callers use it for the documentary role only.
    """
    from nasa_fire_ai.ingestion.clause_cues import FINITE_AUXILIARIES

    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    return any(w.lower() in FINITE_AUXILIARIES for w in words) or any(
        re.fullmatch(r"[a-z]{3,}ed", w) for w in words
    )


def list_items(text):
    """Items of a list: a line that opens with a marker, or follows a lone marker.

    An item runs to the next marker or a blank line. The level is the
    indentation of its marker line.
    """
    items, position, pending, current = [], 0, None, None
    for line in text.split("\n"):
        end = position + len(line)
        marker = LIST_MARKER.match(line) if line.strip() else None
        lone = LONE_MARKER.fullmatch(line)
        if not line.strip():
            if current:
                items.append(current)
            current = pending = None
        elif lone:
            if current:
                items.append(current)
            current, pending = None, (position, lone.group("marker"), lone.start("marker"))
        elif marker or pending:
            if current:
                items.append(current)
            if marker:
                start, glyph, level = position, marker.group("marker"), marker.start("marker")
            else:
                start, glyph, level = pending
            current, pending = {"start": start, "end": end, "marker": glyph, "level": level}, None
        elif current:
            current["end"] = end
        position = end + 1
    if current:
        items.append(current)
    return items


def list_lead_with_items(text, *, only_lead=False):
    """A line ending in a colon followed by at least two items or label lines.

    A label line holds no clause and no sentence-final punctuation (the labels
    of a flowchart); it counts only when the statement opens with its lead, so
    that front matter ("Paper ID:") is not read as one. An item is marked, or
    follows a lone marker.

    With only_lead (SCIENCE_LIST_ITEMS=2) the statement must end at the lead: a
    line before the lead, or a line after it that ends a sentence and is no item, is something the
    statement asserts besides the list, and nothing is returned.
    """
    lines = text.strip().split("\n")
    for index, line in enumerate(lines[:-1]):
        if line.rstrip().endswith(":"):
            items, marked = 0, False
            other = sum(1 for x in lines[:index] if x.strip())
            for rest in (x.strip() for x in lines[index + 1 :]):
                if not rest:
                    continue
                if LONE_MARKER.fullmatch(rest):
                    marked = True
                    continue
                if (
                    marked
                    or LIST_MARKER.match(rest)
                    or (index == 0 and not item_has_clause(rest) and not SENTENCE_END.search(rest))
                ):
                    items += 1
                elif SENTENCE_END.search(rest):
                    # A sentence that ends: the statement asserts it besides the list.
                    other += 1
                marked = False
            if items >= 2 and not (only_lead and other):
                return {"lead": line.strip(), "items": items}
    return None


def heading_title(printed):
    """A printed heading without its numbering ("B. GRC Testing" -> "GRC Testing")."""
    return re.sub(r"^(?:#+\s*|(?:[A-Z]|\d+(?:\.\d+)*|[IVXLCDM]+)[.)]\s+)", "", printed)


def printed_heading_before(span, document, *, same_source=False):
    """The nearest printed heading at or before the span, in document order."""
    order = {s["evidence_id"]: i for i, s in enumerate(document["segments"])}
    if span["evidence_id"] not in order:
        return None
    preceding = [
        h
        for h in document["sections"]
        if h["evidence_id"] in order
        and (not same_source or h.get("source_id") == span["source_id"])
        and (order[h["evidence_id"]], h["start"]) <= (order[span["evidence_id"]], span["start"])
    ]
    if not preceding:
        return None
    return max(preceding, key=lambda h: (order[h["evidence_id"]], h["start"]))


def layout_heading(span, document):
    """The heading a page prints in its layout for the span's evidence, if any."""
    return document.get("layout_headings", {}).get(span["evidence_id"])


def referenced_captions(span, document):
    """For each figure number the span cites, the captions the document prints for it."""
    refs = re.findall(r"\b(?:Figures?|Figs?\.?)\s+(\d+)\b", span["quote"], re.IGNORECASE)
    return {
        ref: [
            f
            for f in document.get("figures", [])
            if f["source_id"] == span["source_id"] and f["number"] == ref
        ]
        for ref in refs
    }


DEFAULT_STEPS = (
    "sentence",
    "subsection_heading",
    "major_heading",
    "layout_heading",
    "referenced_caption",
)


def evidence_path(span, document, *, steps=DEFAULT_STEPS):
    """The printed structural parents of a span, nearest first.

    Each step is {kind, evidence_id, start, end, quote}. The sentence is the
    span; the subsection heading, the governing major heading and the page's
    layout heading follow; one referenced_caption step is built for each caption
    of a figure the span cites. Every walker that needs a parent of a span reads
    this path, and keeps its own acceptance test.
    """
    path = []
    if "sentence" in steps:
        path.append(
            {
                "kind": "sentence",
                "evidence_id": span["evidence_id"],
                "start": span["start"],
                "end": span.get("end", span["start"] + len(span.get("quote", ""))),
                "quote": span.get("quote", ""),
            }
        )
    if "subsection_heading" in steps:
        h = printed_heading_before(span, document)
        if h:
            path.append(_heading_step("subsection_heading", h))
    if "major_heading" in steps:
        h = governing_major(span, document)
        if h:
            path.append(_heading_step("major_heading", h))
    if "layout_heading" in steps:
        h = layout_heading(span, document)
        if h:
            path.append(_heading_step("layout_heading", h))
    if "referenced_caption" in steps:
        for ref, captions in referenced_captions(span, document).items():
            for f in captions:
                path.append(
                    {
                        "kind": "referenced_caption",
                        "number": ref,
                        "evidence_id": f["evidence_id"],
                        "start": f["start"],
                        "end": f["end"],
                        "first_line_end": f["first_line_end"],
                        "quote": f["quote"],
                    }
                )
    return path


def _heading_step(kind, heading):
    quote = heading.get("title") or heading.get("quote") or ""
    return {
        "kind": kind,
        "evidence_id": heading["evidence_id"],
        "start": heading["start"],
        "end": heading.get("end", heading["start"] + len(quote)),
        "quote": quote,
        "heading": heading,
    }


def path_step(path, kind):
    """The first step of a kind in an evidence path, or None."""
    return next((step for step in path if step["kind"] == kind), None)


def subsection_heading_of(span, document):
    """The nearest printed heading before the span, read from its evidence path."""
    step = path_step(
        evidence_path(span, document, steps=("subsection_heading",)), "subsection_heading"
    )
    return step["heading"] if step else None


# Section roles a scientific paper uses for what is not its own experiment.
BACKGROUND_SECTION_ROLE = re.compile(
    r"\b(?:introduction|background|theory|theoretical|analysis|analyses|analytical|"
    r"model(?:s|ing|ling)?|literature|previous\s+work|prior\s+work|references)\b",
    re.IGNORECASE,
)
# A printed equation's number closes its own line ("... (Eq. 7)"); a reference
# inside a sentence ("the drift (Eq. 3) that follows from") does not.
PRINTED_EQUATION = re.compile(
    r"\(\s*Eq(?:uation)?s?\.?\s*\d+\s*\)[ \t]*$", re.IGNORECASE | re.MULTILINE
)


def background_or_analysis_span(span, document):
    """Whether the span's own printed section is background, theory or analysis.

    The nearest printed section (a slide's title in a deck) is such when its
    title names that role, or when it prints numbered equations ("(Eq. 7)"):
    what it describes is not this study's own experiment, whatever it is called.
    """
    heading = printed_heading_before(span, document)
    if not heading:
        return False
    # Only a paper's numbered major sections run across pages; in a slide deck
    # a heading governs its own page ("Background" on slide 2 is not slide 6's).
    paged = not any(
        re.match(r"^[IVX]+[.)]\s", h["title"].strip()) for h in document.get("sections", [])
    )
    if paged and heading["evidence_id"] != span["evidence_id"]:
        return False

    def key(h):
        return (h["evidence_id"], h["start"])

    if BACKGROUND_SECTION_ROLE.search(heading_title(heading["title"])):
        return True
    # In a paper, a subsection of a background or analysis section is one too.
    major = section_for_span(span, document)
    if not paged and major and BACKGROUND_SECTION_ROLE.search(major):
        return True
    return key(heading) in equation_headings(document)


# The headings under which a numbered equation is printed, per document object;
# kept outside the document so that nothing is added to what it serializes.
_EQUATION_HEADINGS = {}


def equation_headings(document):
    cached = _EQUATION_HEADINGS.get(id(document))
    if cached and cached[0] is document:
        return cached[1]
    found = set()
    for segment in document.get("segments", []):
        for match in PRINTED_EQUATION.finditer(segment.get("text", "")):
            at = printed_heading_before(
                {
                    "evidence_id": segment["evidence_id"],
                    "start": segment.get("start", 0) + match.start(),
                },
                document,
            )
            if at:
                found.add((at["evidence_id"], at["start"]))
    if len(_EQUATION_HEADINGS) > 64:
        _EQUATION_HEADINGS.clear()
    _EQUATION_HEADINGS[id(document)] = (document, found)
    return found


def under_group_heading(span, entities, document):
    """Whether the nearest heading before the span names a proposed group."""
    heading = subsection_heading_of(span, document)
    if not heading:
        return False
    title = heading_title(heading["title"])
    return any(
        e["class_id"] == "ExperimentFamily" and normalized(e["label"]) == normalized(title)
        for e in entities.values()
    )


def subsection_group(spans, entities, document):
    """The one current group whose own printed subsection holds every span, if any."""
    keys = set()
    for span in spans:
        heading = subsection_heading_of(span, document)
        if not heading:
            return None
        title = normalized(heading_title(heading["title"]))
        found = [
            key
            for key, e in entities.items()
            if e["class_id"] == "ExperimentFamily"
            and e.get("validation_status") == "SOURCE_SUPPORTED"
            and e.get("source_id") == span.get("source_id")
            and normalized(e["label"]) == title
        ]
        if len(found) != 1:
            return None
        keys.add(found[0])
    return keys.pop() if len(keys) == 1 else None


def table_column_prints_value(document, expression, unit=None, label=None):
    """Whether a detected table prints this value under a column named by its unit or variable.

    A method-section value that the document's own tables also print per row
    ("Impact energy (ft-lbs)" with 72 in every row) is attributed by those rows,
    the narrowest printed subjects, not to the whole investigation.
    """
    wanted = normalized(expression or "")
    unit_name, label_name = normalized(unit or ""), normalized(label or "")
    if not wanted or not (unit_name or label_name):
        return False
    for table in document.get("detected_tables", []):
        header = table.get("header") or []
        rows = table.get("cells") or []
        if rows and rows[0] == header:
            rows = rows[1:]
        for column, printed in enumerate(header):
            name = normalized(printed or "")
            if not name or not (
                (unit_name and unit_name in name) or (label_name and label_name in name)
            ):
                continue
            # The cell prints the value, alone or with its unit and a conversion
            # ("72 ft-lbs (98J)"), never as a prefix of a longer number.
            printed_value = re.compile(
                re.escape(wanted)
                + (r"(?:\s*" + re.escape(unit_name) + ")?" if unit_name else "")
                + r"(?![\d.])"
            )
            if any(
                column < len(row) and printed_value.match(normalized(row[column] or ""))
                for row in rows
            ):
                return True
    return False


def group_section_support(subject, spans, entities, document):
    """Exact original subsection scope, including continuation across PDF pages.

    This is a documentary heading certificate, never evidence that each member
    run shares a result. Explicit competing groups/runs remain unresolved.
    """
    entity = entities.get(subject, {})
    if (
        entity.get("class_id") != "ExperimentFamily"
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
    ):
        return []
    proof = []
    for span in spans:
        if span["source_id"] != entity["source_id"]:
            return []
        # PDF floats may appear under the following section. Their placement
        # alone cannot certify that the depicted data belong to that group.
        if opens_with_float_label(span["quote"]):
            return []
        heading = printed_heading_before(span, document, same_source=True)
        if not heading:
            return []
        label = re.sub(
            r"^(?:#+\s*|(?:[A-Z]|\d+(?:\.\d+)*|[IVXLCDM]+)[.)]\s+)",
            "",
            heading["title"],
            flags=re.IGNORECASE,
        )
        if normalized(label) != normalized(entity["label"]):
            return []
        for key, other in entities.items():
            if (
                key == subject
                or other["id"] == entity["id"]
                or other.get("validation_status") != "SOURCE_SUPPORTED"
            ):
                continue
            if other["class_id"] == "ExperimentalRun" and mentions(other["label"], span["quote"]):
                return []
            if other["class_id"] == "ExperimentFamily":
                markers = [other["label"], *re.findall(r"\(([A-Z]{2,8})\)", other["label"])]
                own_markers = set(re.findall(r"\(([A-Z]{2,8})\)", entity["label"]))
                if any(mentions(m, span["quote"]) for m in markers if m not in own_markers):
                    return []
        proof.append(
            {
                "evidence_id": heading["evidence_id"],
                "quote": heading["title"],
                "start": heading["start"],
            }
        )
    return list({identity(p): p for p in proof}.values())


def document_conclusion_scope(subject, spans, entities, document):
    """Current authors' article scope; never an individual experimental run."""
    entity = entities.get(subject, {})
    if (
        entity.get("class_id") != "Investigation"
        or entity.get("study") != "current"
        or entity.get("validation_status") != "SOURCE_SUPPORTED"
        or normalized(entity.get("label", "")) != normalized(document.get("package_title", ""))
    ):
        return False
    if any(s["source_id"] != entity["source_id"] for s in spans):
        return False
    conclusions = [
        s for s in spans if re.search(r"conclusions?", section_for_span(s, document), re.IGNORECASE)
    ]
    if not conclusions:
        return False
    text = " ".join(s["quote"] for s in conclusions)
    if re.search(r"\b(?:prior|previous|earlier|reported\s+by)\b|\[\d", text, re.IGNORECASE):
        return False
    if any(
        e["class_id"] == "Investigation" and e["study"] == "cited" and mentions(e["label"], text)
        for e in entities.values()
    ):
        return False
    return not re.search(
        r"\b(?!(?:Figure|Table|Equation|Test|Run)\d)[A-Z][a-z]+(?:[’']s)?\d{1,3}\b", text
    )


def page_title(span, document):
    """The first line of a page's own text, after its running header and page number.

    A slide deck prints no section headings the structure reader recognizes; each
    slide's title is the section of its page.
    """
    titles = document_memo(document, "page_titles", dict)
    if span["evidence_id"] not in titles:
        titles[span["evidence_id"]] = first_page_line(span["evidence_id"], document)
    return titles[span["evidence_id"]]


def first_page_line(evidence_id, document):
    text = _page_texts(document).get(evidence_id, "")
    headers = document_memo(
        document,
        "running_headers",
        lambda: running_headers({e: {"text": t} for e, t in _page_texts(document).items()}),
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:4]:
        if re.fullmatch(r"\d{1,4}", line) or line in {"•", "-"}:
            continue
        if len(re.findall(r"[A-Za-z]{2,}", line)) >= 4 and any(
            normalized(re.sub(r"\d+", " ", line)) == h for h in headers
        ):
            continue
        return line
    return ""


def slide_deck(document):
    """Whether most pages open with a short title line, as presentation slides do."""
    return document_memo(document, "slide_deck", lambda: titled_pages(document))


def titled_pages(document):
    pages = list(_page_texts(document))
    if len(pages) < 4:
        return False
    titles = set()
    for evidence_id in pages:
        title = page_title({"evidence_id": evidence_id}, document)
        words = re.findall(r"[A-Za-z]{2,}", title)
        if title and 1 <= len(words) <= 6 and not title.rstrip().endswith("."):
            titles.add(normalized(title))
    # The same short line atop every page is a running header (a paper's number),
    # not a slide title: slides have titles of their own.
    return len(titles) >= 0.6 * len(pages)


def _page_texts(document):
    return document_memo(document, "page_texts", lambda: joined_page_texts(document))


def joined_page_texts(document):
    texts = {}
    for s in document.get("segments", []):
        texts[s["evidence_id"]] = texts.get(s["evidence_id"], "") + s.get("text", "")
    return texts


SENTENCE_VERB = re.compile(
    r"\b(?:is|are|was|were|has|have|had|does|did|will|shall|must|should)\b",
    re.IGNORECASE,
)


def reads_as_sentence(title):
    """A numbered or lettered line that is a sentence or list item, not a heading."""
    body = re.sub(r"^(?:#+|\d+(?:\.\d+)*|[A-Za-z]|[IVXLCDM]+)[.)]?\s+", "", title.strip())
    return not body or body.endswith((".", "!", "?")) or bool(SENTENCE_VERB.search(body))


def governing_major(span, document):
    """The major heading logical_section names for the span, with its position."""
    from nasa_fire_ai.ingestion.scientific_scope import major_sections

    order, sources, majors = document_memo(
        document, "major_sections", lambda: major_sections(document)
    )
    if span["evidence_id"] not in sources:
        return None
    here = (order[span["evidence_id"]], span["start"])
    before = [
        h
        for h in majors[sources[span["evidence_id"]]]
        if (order[h["evidence_id"]], h["start"]) <= here
    ]
    return max(before, key=lambda h: (order[h["evidence_id"]], h["start"]), default=None)


def heading_level(heading, document):
    """1 for a major heading, deeper for a numbered or lettered subsection."""
    from nasa_fire_ai.ingestion.scientific_scope import source_majors

    title = heading["title"].strip()
    if marks := re.match(r"#+(?=\s)", title):
        return len(marks.group())
    if outline := re.match(r"(\d+(?:\.\d+)*)[.)]?\s", title):
        return outline.group(1).count(".") + 1
    majors = document_memo(
        document,
        "majors_by_source",
        lambda: {
            sid: {(h["evidence_id"], h["start"]) for h in source_majors(sid, document)}
            for sid in {h.get("source_id") for h in document.get("sections", [])}
        },
    )
    if (heading["evidence_id"], heading["start"]) in majors.get(heading.get("source_id"), set()):
        return 1
    return 2


def heading_scheme(heading, document):
    """The numbering scheme a heading uses; levels compare only within one scheme."""
    title = heading["title"].strip()
    if re.match(r"#+\s", title):
        return "markdown"
    if re.match(r"\d+(?:\.\d+)*\.?[.)]?\s", title):
        return "outline"
    if re.match(r"[IVXLCDM]+[.)]\s", title) and heading_level(heading, document) == 1:
        return "roman"
    if re.match(r"[A-Za-z][.)]\s", title):
        return "letter"
    return "plain"


# A printed numbering the structure reader may not emit as a section: "3.1 Title" (no
# trailing dot), "3.1.1. Title", "## Title", "III. Title", "B. Title".
NUMBERED_HEADING_LINE = re.compile(
    r"(?:#+\s+\S|\d+(?:\.\d+)+\.?\s+[A-Z]|[IVXLCDM]+[.)]\s+[A-Z]|[A-Z][.)]\s+[A-Z])"
)


def page_headings(evidence_id, document):
    """The headings of one page: the reader's sections and numbered heading lines."""

    def compute():
        sources = {}
        for segment in document.get("segments", []):
            sources.setdefault(segment["evidence_id"], segment.get("source_id"))
        result = {}
        for ev, source_id in sources.items():
            known = [h for h in document.get("sections", []) if h["evidence_id"] == ev]
            spans = [(h["start"], h.get("end", h["start"])) for h in known]
            detected, offset = [], 0
            for raw in _page_texts(document).get(ev, "").splitlines(keepends=True):
                begin, offset = offset, offset + len(raw)
                line = raw.strip()
                start = begin + len(raw) - len(raw.lstrip())
                if (
                    line
                    and len(line) <= 100
                    and not line.endswith((".", "!", "?"))
                    and NUMBERED_HEADING_LINE.match(line)
                    and not any(begin <= s < offset for s, _ in spans)
                ):
                    detected.append(
                        {
                            "title": line,
                            "evidence_id": ev,
                            "source_id": source_id,
                            "start": start,
                            "end": start + len(line),
                        }
                    )
            result[ev] = sorted(known + detected, key=lambda h: h["start"])
        return result

    return document_memo(document, "page_headings", compute).get(evidence_id, [])


def section_for_span(span, document):
    from nasa_fire_ai.ingestion.scientific_scope import logical_section

    if slide_deck(document):
        return slide_heading(span, document) or "UNSPECIFIED"
    return logical_section(span, document)


def slide_heading(span, document):
    """The heading a span of a slide sits under: its own slide's, never an earlier one.

    A slide's number printed before its title ("2 Background") is not an outline
    number: a heading governs its own slide only, and a slide without one is the
    section its own title names. Validation (``section_for_span``) and the request
    (``SCIENCE_SLIDE_HEADING_SCOPE``) read this one function.
    """
    own = [
        h
        for h in document.get("sections", [])
        if h["evidence_id"] == span["evidence_id"] and h["start"] <= span.get("start", 0)
    ]
    if own:
        return max(own, key=lambda h: h["start"])["title"]
    return page_title(span, document)
