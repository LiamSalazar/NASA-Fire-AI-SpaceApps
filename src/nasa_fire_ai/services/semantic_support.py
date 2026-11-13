"""Independent English textual entailment, never a scientific authority.

Weights are explicitly provisioned by the operator; requests never download code
or models. Failure to load or entail a paraphrase leaves its sources accessible.
"""

import json
import re
from collections import OrderedDict
from difflib import get_close_matches
from pathlib import Path

import numpy as np

MODEL_REPOSITORY = "onnx-community/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7-ONNX"
MODEL_REVISION = "cdc8277b4682665e2f2e87cd83da7da07b153d75"


class LocalEntailment:
    def __init__(self, directory: Path, threshold=0.92):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "model.onnx"),
            options,
            providers=["CPUExecutionProvider"],
        )
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.labels = json.loads((directory / "config.json").read_text())["id2label"]
        self.threshold = threshold
        self.cache = OrderedDict()
        import snowballstemmer

        self.stemmer = snowballstemmer.stemmer("english")

    def _infer(self, premise, hypothesis):
        if premise.strip() and " ".join(premise.split()) == " ".join(hypothesis.split()):
            return {
                "supported": True,
                "deterministic_identity": True,
                "boundary": "Identical complete textual proposition; no model confidence assigned",
            }
        encoded = self.tokenizer.encode(premise, hypothesis)
        # Never silently truncate a relevant condition or an exception.
        if len(encoded.ids) > 512:
            return {"supported": False, "reason": "NLI context exceeds model window"}
        inputs = {
            "input_ids": [encoded.ids],
            "attention_mask": [encoded.attention_mask],
            "token_type_ids": [encoded.type_ids],
        }
        feed = {
            x.name: np.asarray(inputs[x.name], dtype=np.int64) for x in self.session.get_inputs()
        }
        scores = self.session.run(None, feed)[0][0]
        scores = np.exp(scores - np.max(scores))
        scores /= scores.sum()
        probabilities = {self.labels[str(i)].lower(): float(p) for i, p in enumerate(scores)}
        return {
            "supported": probabilities.get("entailment", 0) >= self.threshold,
            "probabilities": probabilities,
            "threshold": self.threshold,
        }

    def _changed_terms(self, premise, hypothesis):
        source_words = set(re.findall(r"[A-Za-z]{6,}", premise.lower()))
        changed_terms = []
        for word in set(re.findall(r"[A-Za-z]{6,}", hypothesis.lower())) - source_words:
            for near in get_close_matches(word, sorted(source_words), n=1, cutoff=0.86):
                # Ordinary adjective derivation can produce unequal Snowball
                # stems (e.g. a noun and its -al form). It is not a changed
                # scientific entity. Full entailment remains mandatory.
                adjectival = word == near + "al" or near == word + "al"
                if not adjectival and self.stemmer.stemWord(word) != self.stemmer.stemWord(near):
                    changed_terms.append({"source_term": near, "hypothesis_term": word})
        return changed_terms

    def check(self, premise, hypothesis):
        # Pure text/model decisions are reusable. Source identity, quantities and
        # applicability are still checked on every verify_paraphrase invocation.
        key = (premise, hypothesis, getattr(self, "threshold", 0.92))
        if not hasattr(self, "cache"):
            self.cache = OrderedDict()
        if key in self.cache:
            self.cache.move_to_end(key)
            return dict(self.cache[key])
        result = self._check_uncached(premise, hypothesis)
        self.cache[key] = dict(result)
        if len(self.cache) > 2048:
            self.cache.popitem(last=False)
        return result

    def _check_uncached(self, premise, hypothesis):
        raw = self._infer(premise, hypothesis)
        if raw.get("deterministic_identity"):
            return raw
        changes = self._changed_terms(premise, hypothesis)
        return {
            **raw,
            "supported": raw["supported"] and not changes,
            "potential_term_substitutions": changes,
        }


def canonical_numeric_text(text):
    """Compare printed dimensional quantities in common units, preserving other digits.

    Unit equivalence only; entity/property/role alignment still requires evidence and NLI.
    """
    from nasa_fire_ai.normalization.units import normalize

    # Explicit written fractions are quantities too. Apply the same lexical
    # normalization to claim and evidence; preserve the original source text.
    numerators = {
        word: i
        for i, word in enumerate(
            (
                "zero",
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
                "nine",
                "ten",
                "eleven",
                "twelve",
                "thirteen",
                "fourteen",
                "fifteen",
                "sixteen",
                "seventeen",
                "eighteen",
                "nineteen",
                "twenty",
            )
        )
    }
    denominators = {
        "half": 2,
        "halves": 2,
        "third": 3,
        "thirds": 3,
        "fourth": 4,
        "fourths": 4,
        "quarter": 4,
        "quarters": 4,
        "fifth": 5,
        "fifths": 5,
        "sixth": 6,
        "sixths": 6,
        "seventh": 7,
        "sevenths": 7,
        "eighth": 8,
        "eighths": 8,
        "ninth": 9,
        "ninths": 9,
        "tenth": 10,
        "tenths": 10,
    }
    numerator = "(?:" + "|".join(numerators) + "|a|an)"
    denominator = "(?:" + "|".join(sorted(denominators, key=len, reverse=True)) + ")"

    def fraction(match):
        if match["part"].lower() in {"a", "an"} and re.match(
            r"\s+(?:test|run|record|sample|session|campaign|investigation|study|trial)s?\b",
            text[match.end() :],
            re.IGNORECASE,
        ):
            return match[0]
        value = numerators.get(match["part"].lower(), 1) / denominators[match["den"].lower()]
        if match.groupdict().get("whole"):
            value += numerators[match["whole"].lower()]
        return f"{value:.10g}"

    text = re.sub(
        r"\b(?P<whole>"
        + "|".join(numerators)
        + r")\s+and\s+(?P<part>"
        + numerator
        + r")[ -]+(?P<den>"
        + denominator
        + r")\b",
        fraction,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?P<part>" + numerator + r")[ -]+(?P<den>" + denominator + r")\b",
        fraction,
        text,
        flags=re.IGNORECASE,
    )

    units = r"micrometers?|micrometres?|millimeters?|millimetres?|centimeters?|centimetres?|seconds?|minutes?|min|percent|mmHg|slpm|sccm|slm|ml/min|l/min|kg/s|g/s|mg/min|mg/s|cm/s|mm/s|m/s|kPa|MPa|Pa|atm|bar|ppm|µm|μm|mm|cm|°C|K|W|s|m|%"
    aliases = {
        "micrometer": "um",
        "micrometre": "um",
        "millimeter": "mm",
        "millimetre": "mm",
        "centimeter": "cm",
        "centimetre": "cm",
        "second": "s",
        "minute": "min",
        "percent": "%",
    }
    pattern = (
        rf"(?<![\w.])([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*(?:-\s*)?({units})(?![\w])"
    )

    def converted(match):
        unit = match[2]
        unit = aliases.get(unit.lower().rstrip("s"), unit)
        try:
            value, canonical = normalize(float(match[1]), unit)
        except ValueError:
            return match[0]
        return f"{value:.10g} {canonical}"

    return re.sub(pattern, converted, text, flags=re.IGNORECASE)


def numeric_tokens(text):
    text = canonical_numeric_text(text)
    number = r"[-+]?\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?"
    numbers = set(re.findall(r"(?<![\w])" + number, text))
    quantities = re.findall(
        r"(?<![\w])(" + number + r")\s*(?:-\s*)?(%|(?:[munpckMGTµμ]?(?:Pa|K|m|s|g|W|J|V|A|Hz)|mmHg|atm|torr|°C)(?:[²³]|\^?[23])?(?:/[a-zA-Z]+)?)(?![\w])",
        text,
    )
    return numbers | {value + unit for value, unit in quantities}


def unstructured_numeric_table(anchor):
    """Layout safeguard: unlabelled numeric columns cannot establish prose findings.

    Motivated by a reexamined report table falsely entailing a narrative
    relationship. Verified registry projections and exact quotations retain their
    existing paths. This is a document-structure rule, not domain vocabulary.
    """
    if anchor.get("projection_verified"):
        return False
    for span in anchor.get("spans", []):
        lines = [line.strip() for line in span["text"].splitlines() if line.strip()]
        scalars = sum(bool(re.fullmatch(r"[-+~<>=.\d%/, :–—]+", line)) for line in lines)
        if scalars >= 8 and scalars / max(1, len(lines)) >= 0.35:
            return True
    return False


def aligned_properties(text, definitions):
    """Resolve explicit curated aliases, leaving ambiguous aliases unresolved."""
    normalize = lambda value: " ".join(re.findall(r"[a-z0-9]+", value.lower()))
    surface = normalize(text)
    aliases = {}
    for pid, definition in definitions.items():
        for alias in definition.aliases:
            label = normalize(alias)
            if len(label) >= 3 or (
                len(label) == 2 and (alias != alias.lower() or any(c.isdigit() for c in alias))
            ):
                aliases.setdefault(label, set()).add(pid)
    occupied, result = [], set()
    for alias in sorted(aliases, key=len, reverse=True):
        if len(aliases[alias]) != 1:
            continue
        for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?:s)?(?!\w)", surface):
            if any(left <= match.start() and right >= match.end() for left, right in occupied):
                continue
            occupied.append(match.span())
            result.update(aliases[alias])
    return result


def mentioned_materials(text, entities):
    """Use approved material aliases only; a superclass is not an identity."""
    surface = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
    aliases = {}
    for identity, entry in entities.items():
        if entry.get("relation") != "hasMaterial":
            continue
        for alias in [identity, *entry.get("aliases", [])]:
            if len(alias) < 4 and not any(c.isdigit() for c in alias):
                continue
            label = " ".join(re.findall(r"[a-z0-9]+", alias.lower()))
            aliases.setdefault(label, set()).add(identity)
    return {
        next(iter(ids))
        for label, ids in aliases.items()
        if len(ids) == 1 and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", surface)
    }


def bibliographic_span(source, text):
    """Reference lists supply metadata, not the cited papers' findings."""
    original = source.get("text", "")
    heading = re.search(r"(?im)^\s*(?:\d+\.?\s+)?(?:references|bibliography)\s*$", original)
    return bool(heading and original.find(text) >= heading.end())


def source_role_errors(text, roles):
    if roles == {"Hypothesis"} and not re.search(
        r"\b(?:hypothes\w*|propos\w*|believ\w*|expect\w*|would|may|might|could|possibly)\b",
        text,
        re.IGNORECASE,
    ):
        return ["A source hypothesis must retain its hypothetical status"]
    if roles == {"Objective"} and not re.search(
        r"\b(?:objectives?|goals?|aim\w*|plan\w*|intend\w*|seek\w*|will)\b", text, re.IGNORECASE
    ):
        return ["A source objective must retain its intended status"]
    return []


def instrument_attribute_errors(text, anchors, registry):
    """Do not combine categorical facets belonging to different instruments.

    Facet names and values come from source-validated RDF descriptions. This
    only rejects an unsupported combination; matching facets never certify prose.
    """
    catalogue = getattr(registry, "scientific_instruments", {})
    descriptions = [
        description["attributes"]
        for anchor in anchors
        for span in anchor.get("spans", [])
        for description in catalogue.get(span["evidence_id"], [])
    ]
    if not descriptions:
        return []
    normalize = lambda value: " ".join(re.findall(r"[a-z0-9]+", value.casefold()))
    categories = {
        row["instrumentCategory"] for row in descriptions if row.get("instrumentCategory")
    }
    values = {}
    for row in descriptions:
        for key, value in row.items():
            if key != "instrumentCategory":
                values.setdefault(key, set()).add(value)

    def mentioned(value, phrase, plural=False):
        return bool(
            re.search(
                r"(?<!\w)" + re.escape(normalize(value)) + (r"s?" if plural else "") + r"(?!\w)",
                normalize(phrase),
            )
        )

    for sentence in re.split(r"[.!?;]", text):
        sentence_kinds = {kind for kind in categories if mentioned(kind, sentence, plural=True)}
        for clause in re.split(r"[,;]|\b(?:and|or|plus|whereas)\b", sentence, flags=re.IGNORECASE):
            kinds = {kind for kind in categories if mentioned(kind, clause, plural=True)}
            if not kinds and len(sentence_kinds) == 1:
                kinds = sentence_kinds
            surface = normalize(clause)
            occurrences = sorted(
                (match.start(), match.end(), key, value)
                for key, candidates in values.items()
                for value in candidates
                for match in re.finditer(
                    r"(?<!\w)" + re.escape(normalize(value)) + r"(?!\w)", surface
                )
            )
            groups = []
            for start, end, key, value in occurrences:
                if not groups or surface[groups[-1]["end"] : start].strip():
                    groups.append({"end": end, "fields": {}})
                groups[-1]["end"] = max(groups[-1]["end"], end)
                groups[-1]["fields"].setdefault(key, set()).add(value)
            for group in groups:
                requested = group["fields"]
                # A joint descriptor binds multiple facets. Isolated words can
                # be ordinary adverbs or refer to another part of the sentence.
                if len(requested) < 2:
                    continue
                for kind in kinds:
                    if not any(
                        row.get("instrumentCategory") == kind
                        and all(
                            candidates == {row.get(key)} for key, candidates in requested.items()
                        )
                        for row in descriptions
                    ):
                        return [
                            "Instrument attributes are not jointly established for any single source-described component"
                        ]
    return []


def _verify_paraphrase(text, anchors, registry, entailment):
    errors = []
    from nasa_fire_ai.services.document_sections import record_caption_errors

    errors.extend(record_caption_errors(text, anchors))
    # A retrieved package is a bounded backend selection. Source prose cannot
    # certify its contents or establish that a requested document is absent.
    if re.search(
        r"\b(?:supplied|retrieved|provided)\s+(?:[\w-]+\s+){0,2}(?:materials?|evidence|sources?|package|catalogue|catalog|context|text|records?|excerpts?|passages?)\b"
        r"|\bavailable\s+(?:materials?|evidence|sources?|package|catalogue|catalog|context|text|records?)\b|\bcorpus\b",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(?:do(?:es)? not|did not|no|cannot|can't|lacks?|missing|unavailable)\b",
        text,
        re.IGNORECASE,
    ):
        errors.append("Bounded retrieval cannot support a package-wide absence claim")
    originals, roles = [], set()
    for anchor in anchors:
        source_metadata = getattr(registry, "source_metadata", None)
        catalogue_source = bool(source_metadata) and any(
            "catalog"
            in str((source_metadata(span["evidence_id"]) or {}).get("source_type", "")).lower()
            for span in anchor.get("spans", [])
        )
        catalogue_source = catalogue_source or any(
            bibliographic_span(registry.resolve(span["evidence_id"]) or {}, span["text"])
            for span in anchor.get("spans", [])
        )
        if anchor.get("category") == "DISCOVERY" or catalogue_source:
            metadata_only = anchor.get("epistemic_type") == "catalogue_metadata" or catalogue_source
            catalogue_attribution = re.search(
                r"\b(?:catalogue|catalog|entry|listed|title|metadata|reference|figure|doi)\b",
                text,
                re.IGNORECASE,
            )
            factual_text = text
            if metadata_only:
                for span in anchor.get("spans", []):
                    try:
                        title = json.loads(
                            (registry.resolve(span["evidence_id"]) or {}).get("text", "")
                        ).get("title")
                        if isinstance(title, str) and title:
                            factual_text = factual_text.replace(title, "[registered title]")
                    except (ValueError, TypeError, AttributeError):
                        pass
            finding = re.search(
                r"\b(?:observ(?:e[sd]?|ing)|measur(?:e[sd]?|ing)|prov(?:e[sd]?|ing)|demonstrat(?:e[sd]?|ing)|caus(?:e[sd]?|ing)|recommend(?:s|ed|ing)?|certif(?:y|ies|ied|ying))\b",
                factual_text,
                re.IGNORECASE,
            )
            if not metadata_only or not catalogue_attribution or finding:
                errors.append("Unreviewed discovery cannot support a scientific assertion")
        for span in anchor["spans"]:
            original = registry.resolve(span["evidence_id"])
            if not original or " ".join(span["text"].split()) not in " ".join(
                original["text"].split()
            ):
                errors.append("Source span no longer resolves exactly")
            if span.get("scope") != "source_subject_context":
                originals.append(span["text"])
            role = (original or {}).get("structured_location", {}).get("field")
            if role:
                roles.add(role)
        if any(c.get("status") in {"CONFLICT", "CONFLICTED"} for c in anchor.get("conditions", [])):
            errors.append("Conflicted experimental conditions")
    # The abbreviation is not a scientific definition of missingness. Preserve
    # its literal form unless this source explicitly supplies the expansion.
    if re.search(r"\bn\s*/\s*a\b", " ".join(originals), re.IGNORECASE):
        expansions = re.findall(
            r"\b(?:not applicable|non-applicable|not available|not measured)\b", text, re.IGNORECASE
        )
        if any(expansion.lower() not in " ".join(originals).lower() for expansion in expansions):
            errors.append(
                "Ambiguous missing-value abbreviation cannot establish its expanded meaning"
            )
    errors.extend(source_role_errors(text, roles))
    errors.extend(instrument_attribute_errors(text, anchors, registry))
    from nasa_fire_ai.services.document_sections import TEST, registered_document_references

    requested_methods = set(TEST.findall(text))
    source_methods = {
        method for anchor in anchors for method in anchor.get("method_references", [])
    }
    if source_methods and requested_methods - source_methods:
        errors.append("Numbered test reference conflicts with the original section scope")
    source_text = "\n".join(originals)
    if (
        re.search(
            r"\b(?:is|are|was|were)\s+(?:an?|the)\s+(?:experimental|measured)\s+(?:observations?|results?)\b",
            text,
            re.IGNORECASE,
        )
        and not re.search(
            r"\b(?:experimental\s+(?:observations?|measurements?|results?)|"
            r"(?:was|were)\s+(?:observed|measured|recorded)|observations?\s+(?:show|indicate|reveal))\b",
            source_text,
            re.IGNORECASE,
        )
        and not any(
            field.get("role") == "reported_measurement"
            for anchor in anchors
            for field in anchor.get("typed_fields", [])
        )
    ):
        errors.append("A normative criterion does not establish an experimental observation")
    directive = r"\b(?:recommend\w*|should|shall|must|ought to)\b"
    explicit_directive = directive + r"|\b(?:requir\w*|necessary|criteria|criterion)\b"
    if re.search(directive, text, re.IGNORECASE) and not re.search(
        explicit_directive, " ".join(originals), re.IGNORECASE
    ):
        errors.append(
            "An observation does not establish a source-issued recommendation or requirement"
        )
    multi_record_comparison = re.search(
        r"\b(?:two|both|these|those)\s+(?:source\s+)?(?:records|runs|samples|sessions|experiments)\b",
        text,
        re.IGNORECASE,
    ) and re.search(r"\b(?:same|share|differ|higher|lower|equal)\b", text, re.IGNORECASE)
    if (
        multi_record_comparison
        and not any(anchor.get("epistemic_type") == "comparison_result" for anchor in anchors)
        and not any(" ".join(text.split()) in " ".join(original.split()) for original in originals)
    ):
        errors.append("Multi-record comparison requires an explicitly verified scoped comparison")
    typed_rows = {
        span["evidence_id"]
        for anchor in anchors
        if anchor.get("typed_fields")
        for span in anchor["spans"]
        if span.get("scope") != "table_field_definition"
    }
    if len(typed_rows) > 1:
        errors.append(
            "Different structured records require separate propositions or a verified comparison"
        )
    causal = r"\b(?:caus(?:e[sd]?|ing)|because|due to|led to|result(?:ed|s)? in|attribut(?:ed|able) to)\b"
    if re.search(causal, text, re.IGNORECASE) and not re.search(
        causal
        + r"|\b(?:therefore|thus|consequently|hence)\b|\bso\s+(?:the|these|this|those|it|they|we|a|an)\b",
        " ".join(originals),
        re.IGNORECASE,
    ):
        errors.append("Causal attribution requires explicit source-local causal support")
    if any(anchor.get("typed_fields") for anchor in anchors):
        # Typed table identifiers and formulas are exact source expressions,
        # rather than experimental magnitudes. An NLI score cannot substitute
        # another fuel formula, camera identifier or run label.
        token_pattern = r"(?<![\w])[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*(?![\w])"

        def identifiers(value):
            return {
                token.casefold()
                for token in re.findall(token_pattern, value)
                if any(char.isdigit() for char in token)
            }

        identity_context = " ".join(
            originals
            + [anchor.get("verified_context", "") for anchor in anchors]
            + [
                str(anchor.get(key) or "")
                for anchor in anchors
                for key in ("source_id", "document_id")
            ]
            + [
                alias
                for anchor in anchors
                for field in anchor.get("typed_fields", [])
                for alias in field.get("aliases", [])
            ]
        )
        if identifiers(text) - identifiers(identity_context):
            errors.append("Changed or unsupported structured identifier or chemical formula")
    observation_clauses = []
    previous_clause = ""
    for clause in re.split(r"[,;]|\b(?:and|but|while|whereas)\b", text, flags=re.IGNORECASE):
        # Coordinated predicates can elide their subject: "X was calculated,
        # but measured during ..." still asserts a measurement of X. A new
        # explicit subject or a different quantity keeps its own clause scope.
        if re.match(
            r"^\s*(?:(?:was|were|is|are)\s+)?(?:actually\s+)?(?:measured|observed)"
            r"(?:\s+(?:during|in|at|with|by|as|using|experimentally)\b|[.!?]?\s*$)",
            clause,
            re.IGNORECASE,
        ):
            clause = previous_clause + " " + clause
        previous_clause = clause
        affirmative = re.sub(
            r"\b(?:not|never|neither|nor|rather than|instead of|without)\s+"
            r"(?:(?:a|an|the|direct|directly|actual|experimental|experimentally|newly|reported)\s+){0,4}"
            r"(?:measured|observed)\b",
            "",
            clause,
            flags=re.IGNORECASE,
        )
        if re.search(r"\b(?:measured|observed)\b", affirmative, re.IGNORECASE):
            observation_clauses.append(affirmative)
    for anchor in anchors:
        for field in anchor.get("typed_fields", []):
            if field.get("role") in {
                "reported_measurement",
                "reported_duration",
                "reported_extinction_diameter",
            }:
                continue
            if any(
                re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", clause, re.IGNORECASE)
                for clause in observation_clauses
                for alias in field.get("aliases", [])
                if len(alias) >= 3
            ):
                errors.append(
                    "Recorded field role does not establish a measured or observed quantity"
                )
    if (
        re.search(r"\b(?:planned|scheduled|preassigned)\b", text, re.IGNORECASE)
        and any(
            field.get("role")
            in {
                "record_identifier",
                "original_record_identifier",
                "sample_identifier",
                "session_identifier",
            }
            for anchor in anchors
            for field in anchor.get("typed_fields", [])
        )
        and not re.search(
            r"\b(?:planned|scheduled|preassigned)\b", " ".join(originals), re.IGNORECASE
        )
    ):
        errors.append("A recorded identifier does not establish planning or scheduling status")
    if any(anchor.get("typed_fields") for anchor in anchors):
        from math import isclose

        from nasa_fire_ai.query.native_interpreter import parse_expression
        from nasa_fire_ai.query.numeric_mentions import literal_numeric_mentions
        from nasa_fire_ai.query.v2 import GenericValue, PropertyConstraintV2, SemanticRegistry

        definitions = getattr(registry, "scientific_properties", None)
        if definitions:
            property_ids = {
                field.get("property_id")
                for anchor in anchors
                for field in anchor.get("typed_fields", [])
            }
            properties = SemanticRegistry(
                [definitions[pid] for pid in property_ids if pid in definitions]
            )
            for mention in literal_numeric_mentions(text, properties):
                relevant = [
                    field
                    for anchor in anchors
                    for field in anchor.get("typed_fields", [])
                    if field.get("property_id") == mention["property_id"]
                ]
                if not relevant:
                    continue
                try:
                    operator, proposed = parse_expression(mention["expression"], "numeric", {})
                    normalized = properties.validate(
                        PropertyConstraintV2(
                            property_id=mention["property_id"], operator=operator, value=proposed
                        )
                    )
                    values = [GenericValue.model_validate(field["value"]) for field in relevant]
                    if normalized.lower is not None:
                        matches = any(
                            value.lower is not None
                            and isclose(normalized.lower, value.lower, rel_tol=1e-9, abs_tol=1e-12)
                            and isclose(normalized.upper, value.upper, rel_tol=1e-9, abs_tol=1e-12)
                            for value in values
                        )
                    else:
                        matches = any(
                            value.canonical_value is not None
                            and normalized.canonical_value is not None
                            and isclose(
                                normalized.canonical_value,
                                value.canonical_value,
                                rel_tol=1e-9,
                                abs_tol=1e-12,
                            )
                            for value in values
                        )
                    if not matches:
                        errors.append(
                            "Proposed quantity does not match this typed field and source record"
                        )
                except (ValueError, LookupError, TypeError):
                    errors.append("Proposed quantity has incompatible typed units or shape")
    # Overlapping windows are the same evidence, not independent repetitions.
    # Repetition can flip NLI from contradiction to entailment. Collapse only
    # containment within one immutable evidence location; keep the citations.
    premise_spans = [
        span
        for anchor in anchors
        for span in anchor["spans"]
        if span.get("scope") != "source_subject_context"
    ]
    retained = []
    normalize_span = lambda value: " ".join(value.split())
    for index, span in enumerate(premise_spans):
        normalized = normalize_span(span["text"])
        if any(
            other["evidence_id"] == span["evidence_id"]
            and normalized in normalize_span(other["text"])
            and (len(normalize_span(other["text"])) > len(normalized) or other_index < index)
            for other_index, other in enumerate(premise_spans)
            if other_index != index
        ):
            continue
        retained.append(span["text"])
    premise = "\n".join(dict.fromkeys(retained))
    # Reflow layout only for the probabilistic check; original spans stay intact.
    premise = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "-", premise)
    premise = " ".join(premise.split())
    verified_context = "\n".join(a.get("verified_context", "") for a in anchors)
    identity_context = "\n".join(
        dict.fromkeys(
            line
            for anchor in anchors
            for line in anchor.get("identity_context", "").splitlines()
            if line.strip()
        )
    )
    if identity_context.strip():
        premise += "\n" + identity_context
    if roles:
        premise += "\nOfficial source field roles: " + ", ".join(sorted(roles))
    if verified_context.strip():
        premise += (
            "\nVerified source projection or query comparison (preserves the original record role):\n"
            + verified_context
        )
    # Numbers in source identifiers are allowed only if the original identifiers
    # are supplied as immutable metadata, never borrowed from another anchor.
    numeric_source = (
        "\n".join(
            span["text"]
            for anchor in anchors
            for span in anchor["spans"]
            if span.get("scope")
            not in {
                "section_heading",
                "source_record_heading",
                "source_local_name_definition",
                "source_subject_context",
            }
        )
        + "\n"
        + "\n".join(a["text"] for a in anchors)
    )
    # Original tables often print units in column headers rather than after
    # each cell. Pair only backend-registered typed values with their reported
    # units before dimensional comparison; source/property/role/NLI checks
    # remain independent. This does not substitute normalized output values.
    numeric_source += "\n" + "\n".join(
        f"{field['value'].get('raw_expression') or field['value'].get('reported_value')} {field['value']['reported_unit']}"
        for anchor in anchors
        for field in anchor.get("typed_fields", [])
        if isinstance(field.get("value"), dict) and field["value"].get("reported_unit")
    )
    numeric_source = registered_document_references(numeric_source, anchors, registry)
    identity_pattern = r"\b[A-Z][A-Z0-9]{1,}(?:[-–−]\d+[A-Za-z0-9-]*|[ ]\d{3,}[A-Za-z0-9-]*)\b"
    numeric_text = registered_document_references(text, anchors, registry)
    if source_methods:
        numeric_text = TEST.sub(
            lambda match: "Test reference" if match[1] in source_methods else match[0], numeric_text
        )
        numeric_source = TEST.sub(
            lambda match: "Test reference" if match[1] in source_methods else match[0],
            numeric_source,
        )
    page_text = "\n".join(
        (registry.resolve(span["evidence_id"]) or {}).get("text", "")
        for anchor in anchors
        for span in anchor["spans"]
    )
    for match in re.finditer(
        r"\bNASA(?:/|-)(?:TM|TP|CP|CR|SP|STD)[-–−/]\d[A-Za-z0-9/-]*", text, re.IGNORECASE
    ):
        canonical = lambda value: re.sub(r"[–−]", "-", value).casefold()
        if canonical(match[0]) in canonical(page_text):
            numeric_text = numeric_text.replace(match[0], " ")
    # A backend-resolved source identifier is attribution, not a measured value.
    # Remove only the complete identifier of the cited anchor; another source's
    # identifier and altered measurements remain subject to the numeric guard.
    for anchor in anchors:
        for source_identifier in (
            anchor.get("source_id"),
            anchor.get("document_id"),
            *anchor.get("source_aliases", []),
        ):
            if source_identifier:
                numeric_text = re.sub(
                    r"(?<!\w)" + re.escape(str(source_identifier)) + r"(?!\w)",
                    " ",
                    numeric_text,
                    flags=re.IGNORECASE,
                )
    for match in re.finditer(identity_pattern, text):
        identity = match.group()
        canonical = lambda value: re.sub(r"[–−]", "-", value)
        page_text = "\n".join(
            (registry.resolve(span["evidence_id"]) or {}).get("text", "")
            for anchor in anchors
            for span in anchor["spans"]
        )
        # Only metadata-style identities are considered here. Experimental run
        # identities must be in the selected span, not borrowed from another run.
        identity_source = numeric_source if re.search(r"[-–−]\d", identity) else page_text
        if canonical(identity) in canonical(identity_source):
            numeric_text = numeric_text.replace(identity, " ")
    if numeric_tokens(numeric_text) - numeric_tokens(numeric_source):
        errors.append("Changed or unsupported numeric value/unit")
    raw_number_pattern = r"(?<![\w])[-+]?\d+(?:[.,]\d+)*"
    added_numbers = set(re.findall(raw_number_pattern, numeric_text)) - set(
        re.findall(raw_number_pattern, numeric_source)
    )
    if added_numbers:
        # Equivalent units do not authorize replacing the original expression.
        # A clearly labelled normalization may accompany a preserved original.
        original_quantity = re.search(
            r"\d+(?:\.\d+)?\s*(?:-\s*)?(?:cm/s|mm/s|m/s|mmHg|atm|bar|kPa|Pa|mm|cm|µm|μm|%)\b",
            numeric_source,
        )
        retains_original = original_quantity and " ".join(original_quantity[0].split()) in " ".join(
            numeric_text.split()
        )
        if (
            not (
                retains_original
                and re.search(r"\b(?:normalized|equivalent|corresponds)\b", text, re.IGNORECASE)
            )
            and "Changed or unsupported numeric value/unit" not in errors
        ):
            errors.append("Changed or unsupported numeric value/unit")
    negation = r"\b(?:not|no|never|neither|without|absent)\b"
    query_coverage = all(
        a.get("epistemic_type") in {"query_condition_comparison", "comparison_coverage"}
        for a in anchors
    )
    if (
        not query_coverage
        and re.search(negation, text, re.IGNORECASE)
        and not re.search(negation, "\n".join(originals), re.IGNORECASE)
    ):
        errors.append("Introduced negation or unsupported absence claim")
    definitions = getattr(registry, "scientific_properties", None)
    if definitions:
        scientific_source = "\n".join(originals) + "\n" + verified_context
        # Source-column aliases (e.g. "notes" or "fiber") describe typed
        # fields, not every occurrence of those words in narrative science.
        # Ontology quantity properties still guard documentary quantities.
        applicable = (
            definitions
            if any(anchor.get("typed_fields") for anchor in anchors)
            else {
                pid: definition
                for pid, definition in definitions.items()
                if not pid.startswith("source:")
            }
        )
        missing_properties = aligned_properties(text, applicable) - aligned_properties(
            scientific_source, applicable
        )
        if missing_properties:
            errors.append(
                "Source does not establish the claimed scientific properties: "
                + ", ".join(sorted(missing_properties))
            )
        claimed = aligned_properties(text, definitions)
        for anchor in anchors:
            for field in anchor.get("typed_fields", []):
                pid = field.get("property_id")
                if (
                    pid not in claimed
                    or pid not in definitions
                    or definitions[pid].datatype != "categorical"
                ):
                    continue
                raw = str((field.get("value") or {}).get("reported_value") or "")
                original_percentages = {
                    float(value) for value in re.findall(r"([-+]?\d+(?:\.\d+)?)\s*%", raw)
                }
                proposed_percentages = {
                    float(value) for value in re.findall(r"([-+]?\d+(?:\.\d+)?)\s*%", text)
                }
                if original_percentages and proposed_percentages - original_percentages:
                    errors.append("Percentage does not match the named categorical source field")
        entities = getattr(registry, "scientific_entities", {})
        if mentioned_materials(text, entities) - mentioned_materials(scientific_source, entities):
            errors.append(
                "Claimed material identity is not established in the selected source context"
            )
    # Deterministic provenance, identity, quantity and role failures cannot be
    # repaired by a high NLI score. Avoid expensive inference for known failures.
    if errors:
        return {"supported": False, "errors": errors}
    # Run the joint check once before searching for a modality-bearing sentence.
    # If it cannot entail the claim, sentence-level modality work cannot authorize
    # it and only consumes later propositions' latency budget.
    # Backend-bound attribution is an independently sourced identity, not an
    # additional experimental proposition for NLI to guess. Normalize only an
    # exact alias established for every selected source span; all scientific
    # content, quantities, modality and source-role checks remain intact.
    semantic_hypothesis = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "-", text)
    semantic_premise = premise
    attribution = re.fullmatch(r"For ([^,\n]+),\s*(.+)", text, re.DOTALL)
    grounded_attribution = bool(attribution) and all(
        anchor.get("scientific_subjects")
        and attribution[1].casefold()
        in {alias.casefold() for alias in anchor.get("source_aliases", [])}
        for anchor in anchors
    )
    if grounded_attribution:
        semantic_hypothesis = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "-", attribution[2])
        # Identity was established independently from the graph and exact
        # source scope. Alias lists are provenance metadata, not scientific
        # content; including them can corrupt otherwise faithful entailment.
        if identity_context.strip():
            semantic_premise = premise.replace("\n" + identity_context, "", 1)
    primary_originals = [
        span["text"]
        for anchor in anchors
        for span in anchor["spans"]
        if span.get("scope")
        not in {
            "section_heading",
            "source_record_heading",
            "source_local_name_definition",
            "source_subject_context",
        }
    ]
    pair = re.search(r"\bboth\s+([^.;!?]{1,90}?)\s+(?:are|were|have|had)\b", text, re.IGNORECASE)
    if pair:
        # A source about one member cannot certify a plural assertion merely
        # because the relationship wording is similar. Check the cardinality
        # component separately, using primary scientific content, not headings
        # or acronym definitions that only establish a name.
        primary_premise = " ".join("\n".join(primary_originals).split())
        printed_pair = " ".join(("both " + pair[1]).casefold().split())
        explicit_pair = printed_pair in primary_premise.casefold()
        cardinality = (
            {"supported": True, "basis": "same printed dual noun phrase"}
            if explicit_pair
            else entailment.check(primary_premise, f"There are two {pair[1]}.")
            if entailment is not None
            else {"supported": False}
        )
        if not cardinality.get("supported"):
            return {
                "supported": False,
                "errors": ["Primary source does not establish the claimed pair"],
                "cardinality_check": cardinality,
            }
    from nasa_fire_ai.services.source_definitions import registered_quotation_fragments

    # Multiple fragments require an actual curator-backed graph context, not
    # arbitrary concatenation of model-selected sentences or source documents.
    curated_parts = []
    if len(anchors) == 1 and anchors[0].get("graph_context_id"):
        curated_parts = registered_quotation_fragments(
            anchors[0].get("text", ""),
            {
                span["evidence_id"]
                for anchor in anchors
                for span in anchor["spans"]
                if span.get("scope")
                not in {
                    "section_heading",
                    "source_record_heading",
                    "source_local_name_definition",
                    "source_subject_context",
                }
            },
            registry,
            context_id=anchors[0]["graph_context_id"],
        )
    reflow = lambda value: " ".join(re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "-", value).split())
    exact_documentary = (
        len(anchors) == 1
        and anchors[0].get("epistemic_type") == "documentary_content"
        and (len(primary_originals) == 1 or bool(curated_parts))
        and reflow(semantic_hypothesis) == reflow("\n".join(primary_originals))
        and not anchors[0].get("semantic_required_scope")
    )
    if exact_documentary:
        return {
            "supported": True,
            "deterministic_identity": True,
            "boundary": "Exact documentary quotation; no experimental applicability inferred",
            "verification_mechanism": "source_scoped_registered_quotation"
            if grounded_attribution
            else "registered_quotation",
            "verified_attribution": attribution[1] if grounded_attribution else None,
        }
    semantic_verdict = (
        entailment.check(semantic_premise, semantic_hypothesis) if entailment is not None else None
    )
    if (
        semantic_verdict is not None
        and not semantic_verdict.get("supported")
        and not exact_documentary
    ):
        return {**semantic_verdict, "supported": False, "errors": errors}
    # Grammatical modality guards supplement NLI, which can over-entail a
    # tentative source sentence. These are English language controls, not a
    # vocabulary for recognizing combustion questions or choosing investigations.
    # Evaluate modality on the source proposition that can support this claim,
    # rather than on every sentence in a page-sized passage.  A future-plan
    # sentence must not make an unrelated, present-tense measurement uncertain.
    source_sentences = list(
        dict.fromkeys(
            sentence.strip()
            for original in originals
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(original.split()))
            if sentence.strip()
        )
    )
    supporting_sentences = []
    if entailment is not None and len(source_sentences) > 1:
        for sentence in source_sentences[:64]:
            check = entailment.check(sentence, semantic_hypothesis)
            if check.get("supported"):
                supporting_sentences.append(sentence)
    modality_source = " ".join(supporting_sentences or source_sentences or originals)
    actual_past = r"\b(?:observed|measured|used|was|were|had)\b"
    planning_status = (
        r"\b(?:will|would|plan\w*|propos\w*|intend\w*|predict\w*|expect\w*|design\w*)\b"
    )
    if (
        re.search(r"\bwill\b", modality_source, re.IGNORECASE)
        and not re.search(actual_past, modality_source, re.IGNORECASE)
        and re.search(actual_past, text, re.IGNORECASE)
        and not re.search(planning_status, text, re.IGNORECASE)
    ):
        errors.append("A future equipment plan does not establish actual past experimental use")
    if (
        re.search(r"\b(?:measured|observed)\b", text, re.IGNORECASE)
        and re.search(
            r"\b(?:simulat\w*|predict\w*|computed|calculated|numerical model)\b",
            modality_source,
            re.IGNORECASE,
        )
        and not re.search(r"\b(?:measured|observed|experimental)\b", modality_source, re.IGNORECASE)
    ):
        errors.append(
            "Computed, predicted or simulated content does not establish an observed measurement"
        )
    possibility = r"\b(?:may|might|could|possibly|possible|potentially|perhaps)\b"
    tentative_output = (
        possibility + r"|\b(?:aims?|objectives?|goals?|plans?|intends?|proposes?|seeks?)\b"
    )
    if re.search(possibility, modality_source, re.IGNORECASE) and not re.search(
        tentative_output, text, re.IGNORECASE
    ):
        errors.append("Source possibility must retain uncertainty or intended status")
    planned = r"\b(?:objectives?|planned|proposed|aims?|goals?)\b"
    attributed_plan = tentative_output + r"|\b(?:describes?|according to|described)\b"
    if re.search(planned, modality_source, re.IGNORECASE) and not re.search(
        attributed_plan, text, re.IGNORECASE
    ):
        errors.append(
            "Source objectives/plans must retain intended status or documentary attribution"
        )
    if errors:
        return {"supported": False, "errors": errors}
    if any(unstructured_numeric_table(anchor) for anchor in anchors):
        return {
            "supported": False,
            "errors": [
                "Unstructured numerical table requires labelled source projection or a separate supporting prose span"
            ],
        }
    if entailment is None:
        return {"supported": False, "errors": ["Independent semantic verifier unavailable"]}
    verdict = semantic_verdict
    # A bounded search cannot prove absence from a report. An unrelated negative
    # statement (for example an event not occurring) cannot authorize a claim
    # that measurements were not reported. Require explicit reporting-absence
    # language in a local source sentence in addition to semantic support.
    absence_checks = []
    document_absence = re.search(
        r"\b(?:source|report|document|documentation|evidence)\b.{0,45}\b(?:does|do|did)\s+not\s+"
        r"(?:report|provide|state|specify|include|contain|record|establish|give)\b",
        text,
        re.IGNORECASE,
    )
    if verdict.get("supported") and document_absence and not query_coverage:
        local_absence = r"\b(?:not\s+(?:reported|provided|stated|specified|included|recorded|available|given)|(?:does|do|did)\s+not\s+(?:report|provide|state|specify|include|contain|record|give))\b"
        for original in originals:
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(original.split())):
                if not re.search(local_absence, sentence, re.IGNORECASE):
                    continue
                check = entailment.check(sentence, semantic_hypothesis)
                reverse = (
                    entailment.check(text, sentence) if check["supported"] else {"supported": False}
                )
                absence_checks.append(
                    {"source_sentence": sentence, **check, "scope_equivalence": reverse}
                )
                if check["supported"] and reverse["supported"]:
                    break
            else:
                continue
            break
        else:
            return {
                **verdict,
                "supported": False,
                "errors": [
                    "Documentary absence claim lacks explicit source-local reporting-absence support"
                ],
                "documentary_absence_checks": absence_checks,
            }
    # A reduced remedial clause can falsely bind two independently supported
    # facts: an error in one measurement and a correction for another. Require
    # the proposed remedy/target relationship to survive a source-local check,
    # rather than allowing co-occurrence across passages to establish the link.
    remedial_checks = []
    if verdict.get("supported") and re.search(
        r"\b(?:addressed|corrected|mitigated|resolved|remedied)\s+by\b", text, re.IGNORECASE
    ):
        sentences = list(
            dict.fromkeys(
                sentence.strip()
                for original in originals
                for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(original.split()))
                if sentence.strip()
            )
        )
        for sentence in sentences[:24]:
            check = entailment.check(sentence, semantic_hypothesis)
            remedial_checks.append({"source_sentence": sentence, **check})
            if check["supported"] and not (numeric_tokens(text) - numeric_tokens(sentence)):
                break
        else:
            return {
                **verdict,
                "supported": False,
                "errors": [
                    "Remedy attribution lacks source-local support for the affected measurement"
                ],
                "remedial_relation_checks": remedial_checks,
            }
    # Applicability metadata is immutable and travels with each citation. A
    # summary need not entail the entire source paragraph in reverse: that would
    # reject faithful summaries merely for omitting unrelated source content.
    # Explicit semantic scope propositions, when supplied by the trusted service,
    # must still be retained; presentation warnings are not scope propositions.
    scope_checks = []
    for anchor in anchors:
        for limitation in anchor.get("semantic_required_scope", []):
            scope_checks.append(entailment.check(text, limitation))
    return {
        **verdict,
        "remedial_relation_checks": remedial_checks,
        "documentary_absence_checks": absence_checks,
        "scope_checks": scope_checks,
        "supported": verdict["supported"] and all(x["supported"] for x in scope_checks),
    }


def verify_paraphrase(text, anchors, registry, entailment):
    """Review cited support individually before letting unrelated context veto it.

    A source-supported summary need not describe every supplied anchor. Each
    alternative passes the same numbers, modality, identity and scope checks.
    This changes evidence selection, never the NLI threshold.
    """
    verdict = _verify_paraphrase(text, anchors, registry, entailment)
    if len(anchors) < 2 or "Conflicted experimental conditions" in verdict.get("errors", []):
        return verdict
    reviews = []
    for anchor in anchors[:8]:
        check = _verify_paraphrase(text, [anchor], registry, entailment)
        reviews.append({"support_id": anchor.get("support_id"), **check})
        if check["supported"]:
            return {
                **check,
                "support_review": reviews,
                "selected_support_ids": [anchor.get("support_id")],
                "initial_rejection": verdict,
            }
    # Retain a genuinely multi-source proposition only when no individual
    # anchor can support it.  This prevents unrelated supplied context from
    # becoming a citation for a claim already grounded by one source.
    evidence_sets = [{span["evidence_id"] for span in anchor["spans"]} for anchor in anchors]
    shared_location = bool(set.intersection(*evidence_sets))
    contradictions = [
        review
        for review in reviews
        if review.get("probabilities", {}).get("contradiction", 0)
        >= getattr(entailment, "threshold", 0.92)
    ]
    if verdict.get("supported") and shared_location and contradictions:
        return {
            **verdict,
            "supported": False,
            "errors": ["Joint entailment conflicts with a source-local contradiction"],
            "support_review": reviews,
        }
    return {**verdict, "support_review": reviews}
