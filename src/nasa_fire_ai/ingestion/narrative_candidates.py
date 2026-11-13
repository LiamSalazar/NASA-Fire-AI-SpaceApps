"""Source-independent literal narrative anchors for model-free preparation.

Names, grouping phrases and quantities are candidates, never inferred executions.
Only explicit source clauses propose scientific applicability.
"""

import re

from nasa_fire_ai.ingestion.abbreviations import segmentation_input_view
from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.scientific_proposals import normative_instruction


def literal_candidates(segment, semantic):
    output = {k: [] for k in ("entities", "statements", "relations", "quantities", "concepts")}
    for match in re.finditer(
        r".+?(?:[.!?](?!\d)(?=\s|$)|$)", segmentation_input_view(segment["text"]), re.DOTALL
    ):
        quote = segment["text"][match.start() : match.end()].strip()
        if not 12 <= len(quote) <= 2400:
            continue
        span = {
            "evidence_id": segment["evidence_id"],
            "quote": quote,
            "start": segment["start"] + segment["text"].find(quote),
        }
        prior = bool(re.search(r"\b(?:previous|prior|earlier|historical)\b", quote, re.IGNORECASE))
        explicit = bool(
            re.search(
                r"\b(?:conducted|performed|tested|obtained|as\s+part\s+of)\b", quote, re.IGNORECASE
            )
            or re.search(
                r"\b(?:project|investigation|experiment|study)\s+(?:has\s+)?(?:achieved|completed)\b"
                r"[^.!?]{0,160}\b(?:tests?|experiments?|measurements?)\b",
                quote,
                re.IGNORECASE,
            )
        )
        study = (
            "cited"
            if prior
            else "current"
            if explicit and not normative_instruction(quote)
            else "unknown"
        )
        if re.search(
            r"introduction|background|references|acknowledg", segment["section"], re.IGNORECASE
        ):
            study = "cited" if prior or re.search(r"\[\d", quote) else "unknown"
        entities = []
        # Exact investigation names/acronyms and scientific group phrases.
        patterns = [
            (
                "Investigation",
                r"\b([A-Z][A-Z0-9-]{2,20})\s+(?:experiments?|investigation|project)\b",
            ),
            (
                "ExperimentFamily",
                r"\b((?:[A-Za-z]+[- ]flow|blowoff(?:\s+limit)?|quenching|ground|flight|drop|normal[- ]gravity|microgravity)\s+(?:tests|experiments|cases))\b",
            ),
            (
                "ExperimentalRun",
                r"\b(?i:run|case|test)\s+(?:(?i:number)\s+|(?i:no)\.?\s*|#\s*)?([A-Z]\d+(?:[-_.]\d+)*)\b",
            ),
            (
                "Sample",
                r"\b(?i:sample|specimen)\s+(?:(?i:number)\s+|(?i:no)\.?\s*|#\s*)?([A-Z]\d+(?:[-_.]\d+)*)\b",
            ),
        ]
        for cls, pattern in patterns:
            for named in re.finditer(pattern, quote):
                label = named.group(1)
                key = "literal-" + identity([segment["source_id"], cls, label.lower(), study])[:16]
                entities.append(
                    {"key": key, "label": label, "class_id": cls, "study": study, "support": [span]}
                )
        # Approved exact aliases identify concepts; mentions alone do not assign conditions.
        for canonical, meta in getattr(semantic, "entity_mentions", {}).items():
            cls = {"hasMaterial": "Material", "hasGravityCondition": "GravityCondition"}.get(
                meta.get("relation")
            )
            if not cls:
                continue
            for alias in [canonical, *meta.get("aliases", [])]:
                found = re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", quote, re.IGNORECASE)
                if found:
                    label = found.group()
                    key = "literal-" + identity([segment["source_id"], cls, canonical, study])[:16]
                    entities.append(
                        {
                            "key": key,
                            "label": label,
                            "class_id": cls,
                            "study": study,
                            "support": [span],
                        }
                    )
                    break
        output["entities"].extend(entities)
        subjects = [
            e
            for e in entities
            if e["class_id"] in {"Investigation", "ExperimentFamily", "ExperimentalRun", "Sample"}
        ]
        if explicit and not prior and not normative_instruction(quote):
            for subject in subjects:
                for obj in entities:
                    relation = {
                        "Material": "hasMaterial",
                        "GravityCondition": "hasGravityCondition",
                    }.get(obj["class_id"])
                    if relation and subject["key"] != obj["key"]:
                        output["relations"].append(
                            {
                                "subject": subject["key"],
                                "object": obj["key"],
                                "relation": relation,
                                "support": [span],
                            }
                        )
        # Retain nonmapped quantities as typed attribute candidates without fabricating subjects.
        for number in re.finditer(
            r"(?<![\w.])(~?\s*[-+]?\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?)\s*(cm/s|mm/s|m/s|kPa|Pa|psia|mmHg|cm|mm|microns|W|K|s|%)\b",
            quote,
        ):
            before = quote[: number.start()].lower()
            candidates = [
                (before.rfind(alias.lower()), prop, alias)
                for prop in semantic.properties.values()
                for alias in [prop.property_id, *prop.aliases]
                if alias.lower() in before[-100:]
            ]
            if not candidates or len(subjects) != 1:
                continue
            _, _prop, alias = max(candidates, key=lambda x: x[0])
            label = alias
            role = (
                "derived_quantity"
                if re.search(
                    r"\b(?:derived|calculated|simulat\w*|predict\w*)\b", quote, re.IGNORECASE
                )
                else "reported_quantity"
                if re.search(r"\b(?:measured|measurement|recorded)\b", quote, re.IGNORECASE)
                and not normative_instruction(quote)
                else "experimental_configuration"
            )
            output["quantities"].append(
                {
                    "subject": subjects[0]["key"],
                    "label": label,
                    "expression": number.group(1).strip(),
                    "unit": number.group(2),
                    "epistemic": role,
                    "support": [span],
                }
            )
        if re.search(r"results|discussion|conclusion", segment["section"], re.IGNORECASE):
            for term in re.finditer(r"\b([A-Z][a-z]+(?:[- ][A-Za-z]+)?\s+number)\b", quote):
                label = term.group(1)
                if semantic.resolve_property(label)[1] is None:
                    output["concepts"].append(
                        {
                            "kind": "property",
                            "term": label,
                            "definition": "Source uses this named quantity; its meaning and dimensional definition require source-context review",
                            "parent_or_existing": None,
                            "why_existing_insufficient": "No approved registry alias or property matches the literal named quantity; inspect existing value/condition predicates before extending",
                            "support": [span],
                        }
                    )
    return output
