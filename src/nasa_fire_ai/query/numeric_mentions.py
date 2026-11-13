"""Literal numeric mentions tied to registered property aliases, never unit guesses."""

import re

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
UNIT = r"(?:mg/min|mg/s|kg/s|g/s|slpm|sccm|slm|ml/min|l/min|°c|degc|celsius|sec|min|count|atm|bar|mm(?:2|²|\^2)/s|m(?:2|²|\^2)/s|cm/s|mm/s|m/s|mmhg|kpa|pa|fraction|percent|%|cm|mm|um|µm|μm|ppm|k|s|w|m)(?!\w)"
PREFIX = r"(?:less than or equal to|greater than or equal to|no more than|no greater than|no less than|not exceeding|does not exceed|at most|at least|less than|greater than|between|from|below|under|above|approximately|roughly|about|approx\.?|[<>]=?|=|~|≈)"
EXPRESSION = rf"(?:{PREFIX}\s*)?{NUMBER}\s*(?:{UNIT})?(?:\s*(?:±|\+/-|to|and|–|-)\s*{NUMBER}\s*(?:{UNIT})?)?(?:\s+(?:inclusive|exclusive))?"


def literal_numeric_mentions(query, registry):
    """Return exact substrings; require an approved property and explicit unit."""
    aliases = sorted(
        {
            a
            for p in registry.properties.values()
            if p.datatype == "numeric"
            for a in [p.property_id, *p.aliases]
        },
        key=len,
        reverse=True,
    )
    found, occupied = [], []
    for alias in aliases:
        status, pid = registry.resolve_property(alias)
        if status != "CANONICAL":
            continue
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        for mention in re.finditer(pattern, query, re.IGNORECASE):
            if any(a <= mention.start() and mention.end() <= b for a, b in occupied):
                continue
            occupied.append(mention.span())
            tail = query[mention.end() :]
            after = re.match(
                rf"\s*(?:(?:(?:is|was)\s+(?:reported|recorded|listed)\s+as|is|was|of|at|as|equals?|speed|velocity)\s+)?(?P<expression>{EXPRESSION})",
                tail,
                re.IGNORECASE,
            )
            before = None
            if after is None:
                before = re.search(
                    rf"(?P<expression>{EXPRESSION})\s*$", query[: mention.start()], re.IGNORECASE
                )
            match = after or before
            if match and re.search(UNIT, match["expression"], re.IGNORECASE):
                found.append(
                    {
                        "property_id": pid,
                        "label": alias,
                        "expression": match["expression"].strip(),
                        "property_span": [mention.start(), mention.end()],
                    }
                )
    return sorted(found, key=lambda r: r["property_span"])


class DeterministicMinimalInterpreter:
    """Native language option using existing registry authority, without an API."""

    def __init__(self, registry, language):
        self.registry = registry
        self.language = language

    def interpret_minimal(self, query):
        from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, PropertyMention

        operands = []
        compare = bool(re.search(r"\bcompare\b", query, re.IGNORECASE))
        if compare:
            for entity in sorted(self.registry.entities):
                suffix = entity.rsplit("-", 1)[-1]
                if (
                    re.fullmatch(r"[A-Za-z]+\d+", suffix)
                    and re.search(rf"\b{re.escape(suffix)}\b", query, re.IGNORECASE)
                    and suffix not in operands
                ):
                    operands.append(suffix)
        return MinimalInterpretationV2(
            operation="compare" if compare else "search",
            properties=[
                PropertyMention(label=r["label"], expression=r["expression"])
                for r in literal_numeric_mentions(query, self.registry)
            ],
            comparison_operands=operands,
            unknown=["unparsed_numeric_request"]
            if not literal_numeric_mentions(query, self.registry)
            and re.search(rf"(?<![\w-]){NUMBER}(?![\w-])", query)
            else [],
        )
