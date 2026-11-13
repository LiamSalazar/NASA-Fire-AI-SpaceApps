"""Original numeric-expression syntax; scientific meaning is decided elsewhere.

This module only states what a source expression literally says: its numbers,
qualifiers, bounds, ranges, ratios, footnote markers and adjacent unit literals.
It never decides what quantity a number represents, whether it was measured,
set, derived or estimated, or which experimental subject it belongs to.

Values are kept as exact decimal strings; nothing is converted or rounded.
A comma is a thousands separator or a decimal mark only when the document's own
numerals establish that convention. Otherwise every candidate reading is kept and
the expression is reported as AMBIGUOUS instead of guessed.
"""

import os
import re
from decimal import Decimal, InvalidOperation

MINUS = "−"
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"

SIGN = rf"[-+{MINUS}]"
# Thousands groups must be followed by a non-digit; "1,2500" is not a grouping.
GROUPED = r"\d{1,3}(?:,\d{3})+(?!\d)(?:\.\d+)?"
# Source finding never merges a bare comma decimal: in English NASA prose "3,4"
# is far more often a list than a number. Parsing a supplied expression does.
FIND_LITERAL = rf"(?:{GROUPED}|\d+(?:\.\d+)?|\.\d+)"
PARSE_LITERAL = rf"(?:{GROUPED}|\d+(?:[.,]\d+)?|[.,]\d+|\d+\.)"
EXPONENT = (
    rf"(?:[eE]{SIGN}?\d+"
    rf"|\s*[×xX·*]\s*10\s*(?:\^\s*{SIGN}?\d+|\*\*\s*{SIGN}?\d+|[⁻⁺]?[{_SUPERSCRIPT_DIGITS}]+"
    rf"|{SIGN}\d+)"
    # PDF text often flattens "×10³" to "×103". Only the multiplication sign
    # introduces this reading, never "x" (used for dimensions), and the result
    # is always reported as ambiguous.
    r"|\s*×\s*10[1-9]\d?(?![\d.,]))"
)
POWER_OF_TEN = rf"10\s*(?:\^\s*{SIGN}?\d+|[⁻⁺]?[{_SUPERSCRIPT_DIGITS}]+)"

APPROXIMATE = (
    r"~|∼|≈|≃|(?i:about|approximately|approx\.?|roughly|nearly|circa|ca\.|around|"
    r"on the order of|of the order of)(?=\s|\d|\.\d)"
)
INEQUALITY_WORDS = {
    "as high as": "<=",
    "as much as": "<=",
    "as many as": "<=",
    "as low as": ">=",
    "as little as": ">=",
    "as few as": ">=",
    "less than or equal to": "<=",
    "greater than or equal to": ">=",
    "no more than": "<=",
    "no greater than": "<=",
    "not more than": "<=",
    "no less than": ">=",
    "not less than": ">=",
    "less than": "<",
    "fewer than": "<",
    "greater than": ">",
    "more than": ">",
    "at least": ">=",
    "at most": "<=",
    "up to": "<=",
    "in excess of": ">",
    "exceeding": ">",
    "over": ">",
    "above": ">",
    "under": "<",
    "below": "<",
}
INEQUALITY_SYMBOLS = {
    "<=": "<=",
    ">=": ">=",
    "≤": "<=",
    "≥": ">=",
    "⩽": "<=",
    "⩾": ">=",
    "<": "<",
    ">": ">",
}
INEQUALITY = (
    "(?:"
    + "|".join(re.escape(s) for s in INEQUALITY_SYMBOLS)
    + "|(?i:"
    + "|".join(rf"{re.escape(w)}(?=\s)" for w in sorted(INEQUALITY_WORDS, key=len, reverse=True))
    + "))"
)
QUALIFIER = rf"(?:(?:{INEQUALITY})\s*(?:(?:{APPROXIMATE})\s*)?|(?:{APPROXIMATE})\s*)"

# Unit literals are recognition syntax only: they are never converted here and
# never establish a property. SI prefix/base composition follows the existing
# coverage inventory syntax; the word forms are common original spellings. The
# lowercase litre and the cubic or square foot are the forms the unit inventory
# (normalization.units) already interprets.
_PREFIX = r"(?:da|[yzafpnumµμcdhkMGTPEZY])?"
_BASE = r"(?:mol|kat|Hz|Pa|Wb|lm|lx|Bq|Gy|Sv|cd|m|g|s|A|K|N|J|W|C|V|F|Ω|S|T|H|L|l)"
_ATOM = rf"{_PREFIX}{_BASE}(?:\^?{SIGN}?\d+|[²³])?"
UNIT_LITERAL = (
    r"(?:%|‰|°\s?[CF]|ppm|ppb|psi[ag]?|atm|torr|Torr|bar|mbar|mmHg|inHg|RPM|rpm|"
    r"ft[-·‑]?lbf?s?|in[-·‑]lbf?s?|lbf|lbs?|ft/s|in/s|ft(?:\^?[23]|[²³])|ft|"
    r"(?i:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|percent|microns?|"
    r"lit(?:er|re)s?|joules?|watts?|kelvins?|pascals?|degC|degF)|"
    rf"{_ATOM}(?:[/*·]{_ATOM})*)(?![\w°])"
)
# One-letter or word-like literals that are a different word as often as a unit.
AMBIGUOUS_UNIT_LITERALS = {"g", "G", "a", "A", "in", "S", "T", "H", "C", "F", "L", "N", "V", "l"}

# Superscript digits are excluded: after a number they may be a flattened exponent.
FOOTNOTE_MARKERS = r"[*†‡§¶]+|[ᵃᵇᶜᵈᵉᶠ]+"

WORD = (
    r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|"
    r"seventy|eighty|ninety|hundred|thousand|million|half|quarter)"
)
WORDS = rf"{WORD}(?:[\s-]+(?:(?:and|to)\s+)?(?:a\s+)?{WORD})*"
_WORD_QUALIFIER = (
    r"(?:~\s*|≈\s*|[<>≤≥]\s*|(?:greater\s+than|less\s+than|more\s+than|at\s+least|"
    r"at\s+most|about|approximately|roughly|over|under)\s+)?"
)
RANGE_SEPARATOR = r"\s*(?:[-–—]|to|±|\+/-|\+-)\s*"


def _number(literal):
    return rf"(?:{SIGN}?{literal}(?:{EXPONENT})?|{POWER_OF_TEN})"


def numeric_expression_pattern():
    """Regular expression that finds original numeric expressions in source text.

    It is a superset of the earlier grammar: grouped thousands, the Unicode minus
    sign, scientific notation, inequality words, per-endpoint approximation and
    units inside ranges, `between`/`from` ranges and integer ratios are kept whole
    so that, for example, "10,000" is never split into "10" and "000".
    """
    number = _number(FIND_LITERAL)
    value = rf"(?:{number}|{WORDS})"
    endpoint = rf"(?:{QUALIFIER})?{value}"
    inner_unit = rf"(?:\s?{UNIT_LITERAL})?"
    ratio = r"\d+\s*/\s*\d+(?!\s*/\s*\d)"
    count_ratio = r"\d+\s+(?:of|out\s+of)\s+\d+"
    return (
        rf"(?:(?:between)\s+{endpoint}{inner_unit}\s+and\s+{endpoint}"
        rf"|from\s+{endpoint}{inner_unit}\s+to\s+{endpoint}"
        rf"|{ratio}|{count_ratio}"
        rf"|{endpoint}(?:{inner_unit}{RANGE_SEPARATOR}{endpoint})?)"
    )


def legacy_quantity_pattern():
    """The earlier accepted grammar; every expression it accepted stays accepted."""
    from nasa_fire_ai.query.numeric_mentions import NUMBER

    value = rf"(?:{NUMBER}|{WORDS})"
    return rf"{_WORD_QUALIFIER}{value}(?:\s*(?:[-–]|±|\+/-|to)\s*{value})?"


def decimal_convention(text):
    """POINT, COMMA or None from the document's own unambiguous numerals.

    Evidence for POINT: decimals such as 3.95 or 0.5, and groupings that combine
    both marks (1,250.5) or repeat (1,250,000). Evidence for COMMA is the mirror
    image. A convention is returned only when it clearly dominates; mixed or
    absent evidence returns None so that ambiguous expressions stay ambiguous.
    """
    edge = r"(?<![\d.,])"
    tail = r"(?![\d.,]*\d)"
    point = len(re.findall(rf"{edge}\d+\.(?:\d{{1,2}}|\d{{4,}}){tail}", text))
    point += len(re.findall(rf"{edge}\d{{1,3}}(?:,\d{{3}})+\.\d+{tail}", text))
    point += len(re.findall(rf"{edge}\d{{1,3}}(?:,\d{{3}}){{2,}}{tail}", text))
    comma = len(re.findall(rf"{edge}\d+,(?:\d{{1,2}}|\d{{4,}}){tail}", text))
    comma += len(re.findall(rf"{edge}\d{{1,3}}(?:\.\d{{3}})+,\d+{tail}", text))
    comma += len(re.findall(rf"{edge}\d{{1,3}}(?:\.\d{{3}}){{2,}}{tail}", text))
    if point >= 2 and comma * 10 <= point:
        return "POINT"
    if comma >= 2 and point * 10 <= comma:
        return "COMMA"
    return None


def _decimal_text(text):
    try:
        return str(Decimal(text))
    except InvalidOperation:
        return None


def _literal_candidates(literal, convention):
    """Exact decimal readings of one unsigned literal, plus any ambiguity code."""
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d+", literal):
        if convention == "COMMA":
            return [], "GROUPING_CONTRADICTS_DOCUMENT_DECIMAL_COMMA"
        return [literal.replace(",", "")], None
    if re.fullmatch(r"\d{1,3}(?:,\d{3}){2,}", literal):
        if convention == "COMMA":
            return [], "GROUPING_CONTRADICTS_DOCUMENT_DECIMAL_COMMA"
        return [literal.replace(",", "")], None
    if re.fullmatch(r"\d{1,3},\d{3}", literal):
        grouped, decimal = literal.replace(",", ""), literal.replace(",", ".")
        if convention == "POINT":
            return [grouped], None
        if convention == "COMMA":
            return [decimal], None
        return [grouped, decimal], "DIGIT_GROUPING_OR_DECIMAL_COMMA_UNRESOLVED"
    if "," in literal:
        decimal = literal.replace(",", ".")
        if convention == "COMMA":
            return [decimal], None
        return [decimal], "DECIMAL_COMMA_WITHOUT_ESTABLISHED_CONVENTION"
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", literal) and convention == "COMMA":
        return [literal.replace(".", "")], None
    return [literal], None


_NUMBER_PARTS = re.compile(
    rf"(?P<sign>{SIGN})?\s*(?P<literal>{PARSE_LITERAL})"
    rf"(?P<exponent>{EXPONENT})?"
    rf"|(?P<power>{POWER_OF_TEN})"
)


def _endpoint(text, convention, ambiguities):
    """One literal number, with its own approximation/inequality qualifier."""
    text = text.strip()
    qualifier = None
    match = re.match(rf"(?P<q>{QUALIFIER})", text)
    if match and match.group("q").strip():
        # The unstripped group keeps the whitespace that word qualifiers require.
        raw_q = match.group("q")
        approximate = re.search(rf"(?:{APPROXIMATE})\s*$", raw_q)
        inequality = re.match(rf"(?:{INEQUALITY})", raw_q)
        qualifier = {
            "literal": raw_q.strip(),
            "approximate": bool(approximate),
            "operator": None,
        }
        if inequality:
            token = inequality.group().lower()
            qualifier["operator"] = INEQUALITY_SYMBOLS.get(token) or INEQUALITY_WORDS.get(token)
        text = text[match.end() :].strip()
    number = _NUMBER_PARTS.fullmatch(text)
    if not number:
        return None
    if number["power"]:
        exponent = re.sub(r"^10\s*(?:\^\s*)?", "", number["power"]).translate(_SUPERSCRIPTS)
        exponent = exponent.replace(MINUS, "-").replace(" ", "")
        value = _decimal_text("1E" + exponent)
        return {
            "literal": text,
            "sign": None,
            "value_candidates": [value] if value else [],
            "exponent_basis": "EXPLICIT_POWER_OF_TEN",
            "qualifier": qualifier,
        }
    literal = number["literal"]
    literal = literal.removesuffix(".")
    candidates, ambiguity = _literal_candidates(literal, convention)
    if ambiguity:
        ambiguities.append(ambiguity)
    sign = number["sign"]
    signed = "-" if sign in {"-", MINUS} else ""
    exponent_text, exponent_basis = "", None
    if number["exponent"]:
        raw = number["exponent"].strip()
        if raw[0] in "eE":
            exponent_text, exponent_basis = raw[1:], "E_NOTATION"
        else:
            power = re.sub(r"^[×xX·*]\s*10\s*", "", raw)
            if power.startswith(("^", "**")):
                exponent_basis = "EXPLICIT_POWER_OF_TEN"
            elif any(c in power for c in _SUPERSCRIPT_DIGITS):
                exponent_basis = "SUPERSCRIPT_POWER_OF_TEN"
            else:
                exponent_basis = "FLATTENED_SUPERSCRIPT"
                ambiguities.append("FLATTENED_EXPONENT_UNCONFIRMED")
            exponent_text = power.lstrip("^*").translate(_SUPERSCRIPTS)
        exponent_text = exponent_text.replace(MINUS, "-").replace(" ", "")
    values = []
    for candidate in candidates:
        value = _decimal_text(
            signed + (candidate if not candidate.startswith(".") else "0" + candidate)
        )
        if value is not None and exponent_text:
            value = _decimal_text(value + "E" + exponent_text)
        if value is not None:
            values.append(value)
    return {
        "literal": text,
        "sign": sign,
        "value_candidates": values,
        "exponent_basis": exponent_basis,
        "qualifier": qualifier,
    }


def _strip_footnotes(text):
    """Trailing note symbols are annotations, never digits of the value.

    A trailing letter is deliberately not treated as a marker: "12a" is as often
    a specimen identifier as an annotated value.
    """
    markers = []
    while True:
        match = re.search(rf"(?<=[\d%])\s?({FOOTNOTE_MARKERS})$", text)
        if not match:
            break
        markers.insert(0, match.group(1))
        text = text[: match.start()].rstrip()
    return text, markers


def _result(original, status, form, endpoints, convention, **extra):
    return {
        "original": original,
        "status": status,
        "form": form,
        "endpoints": endpoints,
        "decimal_convention": convention,
        "syntax_only": True,
        "scientific_role": "NOT_DETERMINED_BY_SYNTAX",
        **extra,
    }


def parse_numeric_expression(expression, *, convention=None, table_cell=False):
    """Describe an original numeric expression without assigning scientific meaning.

    Returns a dict with status PARSED, AMBIGUOUS or NOT_NUMERIC. PARSED and
    AMBIGUOUS expressions are genuine numeric syntax. AMBIGUOUS keeps all
    candidate readings so a reviewer, not this parser, chooses between them.
    """
    original = expression
    text = re.sub(r"\s+", " ", (expression or "").strip())
    if not text:
        return _result(original, "NOT_NUMERIC", None, [], convention)
    text, markers = _strip_footnotes(text)
    ambiguities = []
    if table_cell and re.fullmatch(r"[–—‐‑]\s?\d[\d.,]*", text):
        # A lone table cell such as "–40" is typographically a negative value,
        # but a dash glyph is not a minus sign, so a reviewer must confirm it.
        text = "-" + text[1:].lstrip()
        ambiguities.append("DASH_GLYPH_SIGN_UNCONFIRMED")
    extra = {"footnote_markers": markers}

    def done(form, endpoints, **more):
        status = "AMBIGUOUS" if ambiguities else "PARSED"
        return _result(
            original,
            status,
            form,
            endpoints,
            convention,
            ambiguities=sorted(set(ambiguities)),
            **extra,
            **more,
        )

    ratio = re.fullmatch(r"(\d+)\s*/\s*(\d+)|(\d+)\s+(of|out of)\s+(\d+)", text)
    if ratio:
        numerator = ratio[1] or ratio[3]
        denominator = ratio[2] or ratio[5]
        return done(
            "RATIO",
            [
                {"role": "numerator", "literal": numerator, "value_candidates": [numerator]},
                {"role": "denominator", "literal": denominator, "value_candidates": [denominator]},
            ],
            ratio_basis="SLASH" if ratio[1] else "OF",
            scalar_value_asserted=False,
        )

    endpoint_unit = rf"(?:\s?(?P<inner>{UNIT_LITERAL}))?"
    for form, pattern in (
        ("BETWEEN", rf"between\s+(?P<a>.+?){endpoint_unit}\s+and\s+(?P<b>.+)"),
        ("FROM_TO", rf"from\s+(?P<a>.+?){endpoint_unit}\s+to\s+(?P<b>.+)"),
        ("PLUS_MINUS", rf"(?P<a>.+?){endpoint_unit}\s*(?:±|\+/-|\+-)\s*(?P<b>.+)"),
        (
            "RANGE",
            rf"(?P<a>.*?\d.*?){endpoint_unit}\s*(?:–|—|to|(?<=\d)-|(?<=\d)\s-\s)\s*(?P<b>.+)",
        ),
    ):
        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if not match:
            continue
        local = []
        lower = _endpoint(match["a"], convention, local)
        upper = _endpoint(match["b"], convention, local)
        if lower is None or upper is None:
            continue
        ambiguities.extend(local)
        if match["inner"]:
            lower["unit_literal"] = match["inner"]
        if form == "PLUS_MINUS":
            lower["role"], upper["role"] = "central_value", "plus_minus"
        else:
            lower["role"], upper["role"] = "first", "second"
        return done(
            form,
            [lower, upper],
            ordered_pair_meaning=(
                "INTERVAL_OR_CHANGE_NOT_DETERMINED_BY_SYNTAX" if form == "FROM_TO" else None
            ),
        )

    single = _endpoint(text, convention, ambiguities)
    if single is not None:
        single["role"] = "value"
        return done("SCALAR", [single])
    # "~.9 and 4.3" or "3, 4 and 5": separate values printed together. A comma
    # must be followed by a space, so digit grouping such as "1,500" never splits.
    parts = re.split(r"\s*,\s+(?:(?:and|or)\s+)?|\s+(?:and|or)\s+", text)
    if len(parts) > 1:
        local = []
        items = [_endpoint(part, convention, local) for part in parts]
        if all(item is not None for item in items):
            for index, item in enumerate(items, 1):
                item["role"] = f"item_{index}"
            ambiguities.extend([*local, "MULTIPLE_VALUES_IN_ONE_EXPRESSION"])
            return done("LIST", items, scalar_value_asserted=False)
    if re.fullmatch(legacy_quantity_pattern(), text):
        return done(
            "WORDS",
            [{"role": "value", "literal": text, "value_candidates": []}],
            numeric_value_asserted=False,
        )
    return _result(original, "NOT_NUMERIC", None, [], convention, **extra)


def same_unit(a, b):
    """Same original unit literal, ignoring only spacing, middle dots and hyphen glyphs.

    Case is significant: "Pa" and "pa", or "mS" and "ms", are different literals.
    """

    def key(text):
        return re.sub(r"\s+", "", (text or "")).replace("·", "").replace("‑", "-")

    return key(a) == key(b)


def split_embedded_unit(expression, declared_unit, *, convention=None):
    """Separate an original unit that a model copied into its numeric expression.

    Returns None when no deterministic split exists. A split is made only when the
    trailing text is a recognized unit literal and either equals the declared unit
    or no unit was declared and the literal is not ambiguous (for example "1-g"
    may name a gravity condition, so it is never split into one gram).
    Author-stated equivalents such as "50 ft-lbs (68J)" are preserved separately.
    """
    if expression is None:
        return None
    declared = None if declared_unit in {None, "", "null", "None"} else declared_unit.strip()
    text = expression.strip()
    equivalent = None
    tail = re.search(
        rf"\s*\(\s*(?P<value>{_number(PARSE_LITERAL)})\s*(?P<unit>{UNIT_LITERAL})\s*\)$", text
    )
    if tail:
        equivalent = {
            "original": tail.group().strip(),
            "value": tail["value"],
            "unit": tail["unit"],
            "basis": "AUTHOR_STATED_EQUIVALENT_NOT_SYSTEM_CONVERSION",
        }
        text = text[: tail.start()].rstrip()
        if declared:
            declared = re.sub(r"\s*\([^()]*\)$", "", declared).strip() or None
    match = re.fullmatch(rf"(?P<value>.*?\d[^\s]*?)(?:\s*[-‑]?\s*)(?P<unit>{UNIT_LITERAL})", text)
    if not match:
        return None
    unit = match["unit"]
    value = match["value"].rstrip()
    if parse_numeric_expression(value, convention=convention)["status"] == "NOT_NUMERIC":
        return None
    if declared:
        if not same_unit(unit, declared):
            return {"status": "UNIT_MISMATCH", "embedded_unit": unit, "declared_unit": declared}
    elif unit in AMBIGUOUS_UNIT_LITERALS:
        return None
    return {
        "status": "SPLIT",
        "expression": value,
        "unit": unit,
        "author_equivalent": equivalent,
        "basis": "ORIGINAL_UNIT_EMBEDDED_IN_EXPRESSION",
    }


class SourceMatch:
    """The parts of re.Match that existing callers use, for a located expression."""

    __slots__ = ("_end", "_start", "_text", "form")

    def __init__(self, text, start, end, form):
        self._text, self._start, self._end, self.form = text, start, end, form

    def group(self, index=0):
        return self._text

    def start(self, index=0):
        return self._start

    def end(self, index=0):
        return self._end

    def __repr__(self):
        return f"SourceMatch({self._text!r}, {self._start}, {self._end}, {self.form})"


_COMPILED = {}


def _compiled(name):
    if name not in _COMPILED:
        if name == "maximal":
            pattern = rf"(?<![\w.])({numeric_expression_pattern()})(?!\d|[.,]\d|[eE])"
        else:
            pattern = rf"(?<![\w.])({legacy_quantity_pattern()})(?![\d.eE])"
        _COMPILED[name] = re.compile(pattern)
    return _COMPILED[name]


def _dash_signed(text, start):
    """A number directly after a dash glyph that starts a token lost its sign."""
    if start == 0 or text[start - 1] not in "–—‐‑":
        return False
    return start == 1 or text[start - 2].isspace() or text[start - 2] in "([=:;,"


def source_numeric_matches(text, *, include_endpoints=True):
    """Locate original numeric expressions in source text without splitting numbers.

    Maximal expressions are returned first-class: "10,000" stays one number and
    "−40" keeps its sign. With include_endpoints, the earlier grammar's matches
    are added only when they are not fragments of one number or ratio. Thus the
    endpoints of "from 20% to 14.3%" stay locatable, as they were before, but
    "000" inside "10,000", the mantissa of "1.5 × 10^-3" and the parts of "2/20"
    never count as standalone source values. A number whose sign is a dash glyph
    at the start of a token is not returned at all, since its sign is unconfirmed.
    """
    maximal = []
    for m in _compiled("maximal").finditer(text):
        if _dash_signed(text, m.start(1)):
            continue
        form = parse_numeric_expression(m.group(1))["form"]
        maximal.append(SourceMatch(m.group(1), m.start(1), m.end(1), form))
    if not include_endpoints:
        return maximal
    result = list(maximal)
    # SCIENCE_NUMERIC_UNIT_RANGE (on by default; "0" turns it off): a maximal match that does not parse (a unit inside a range
    # whose end is a number word, "7 kg to nil") is no number, so its endpoints stay locatable
    # like those of "7 kg to 9".
    fragments = {"SCALAR", "RATIO", "WORDS"}
    if os.getenv("SCIENCE_NUMERIC_UNIT_RANGE", "1") == "0":
        fragments.add(None)
    for m in _compiled("legacy").finditer(text):
        start, end = m.start(1), m.end(1)
        # The earlier grammar could absorb sentence punctuation ("25.").
        end -= text[start:end].endswith(".")
        if _dash_signed(text, start) or any((x.start(), x.end()) == (start, end) for x in result):
            continue
        if any(x.start() <= start and end <= x.end() and x.form in fragments for x in maximal):
            continue
        result.append(SourceMatch(text[start:end], start, end, "ENDPOINT"))
    return sorted(result, key=lambda x: (x.start(), -x.end()))


def same_expression(source_text, expression):
    """Whether two writings denote the same original expression (see comparison_key)."""
    from nasa_fire_ai.ingestion.source_spans import normalized_with_offsets

    if normalized_with_offsets(source_text)[0] == normalized_with_offsets(expression)[0]:
        return True
    return comparison_key(source_text) == comparison_key(expression)


def comparison_key(text):
    """Key for comparing two writings of one original expression.

    Only glyph variants of the same symbol are unified: the Unicode minus sign
    with the hyphen-minus, and the tilde operator with the tilde. Case, spacing
    beyond whitespace runs, qualifiers, separators and markers must match the
    source exactly, so "1e-3" never stands in for an original "1E-3".
    """
    text = (text or "").replace(MINUS, "-").replace("∼", "~")
    return re.sub(r"\s+", " ", text).strip()
