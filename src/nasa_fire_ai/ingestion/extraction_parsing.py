"""Model output parsing and merging into the wire schema."""

import copy
import json
import re

from pydantic import ValidationError

from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.extraction_request import STAGES, unique_json_fields
from nasa_fire_ai.ingestion.extraction_schema import (
    CONTRACT,
    Concept,
    Entity,
    Output,
    Quantity,
    Relation,
    Statement,
)
from nasa_fire_ai.ingestion.scientific_facets import (
    BACKGROUND_FACET_FIELDS,
    PROVENANCE_ROLE,
    STATEMENT_CLASSES,
    background_facets_enabled,
    role_definitions_v2_enabled,
    structured_provenance_enabled,
    value_origin_mark_enabled,
)
from nasa_fire_ai.ingestion.source_spans import locate, normalized


def proposal_identity(kind, item):
    """A proposal's stable id; an unset facet does not make it another proposal.

    Records written before facets existed have no ``modality`` key, so a parsed item
    whose modality is unset keeps the id the same proposal always had.
    """
    return "proposal-" + identity([CONTRACT, kind, without_unset_modality(item)])[:24]


def without_unset_modality(item):
    if item.get("modality", ...) in {None, "actual"}:
        return {k: v for k, v in item.items() if k != "modality"}
    return item


def merge_output(target, output):
    for kind in ("entities", "statements", "relations", "quantities", "concepts"):

        def item_id(item, kind=kind):
            return (
                identity([item["key"], normalized(item["label"]), item["class_id"], item["study"]])
                if kind == "entities"
                # An unset modality is the same proposal as one written before
                # facets existed (see ``proposal_identity``).
                else identity(without_unset_modality(item))
            )

        by_identity = {item_id(item): item for item in target[kind]}
        for item in output[kind]:
            key = item_id(item)
            if kind == "entities" and key in by_identity:
                existing = by_identity[key]
                spans = {identity(s): s for s in existing["support"] + item["support"]}
                by_identity[key] = {**existing, "support": list(spans.values())}
            else:
                by_identity[key] = item
        target[kind] = list(by_identity.values())


def stable_entity_keys(output, package):
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    remap = {}
    for entity in output["entities"]:
        spans = locate(entity["support"], evidence)
        key = (
            "entity-"
            + identity(
                [
                    spans[0]["source_id"],
                    entity["class_id"],
                    normalized(entity["label"]),
                    entity["study"],
                    sorted((s["evidence_id"], s["start"], s["end"]) for s in spans)
                    if entity["class_id"] == "Sample"
                    and not re.fullmatch(r"[A-Za-z]+\d+(?:[-_.]\w+)*", entity["label"])
                    else None,
                ]
            )[:20]
        )
        remap[entity["key"]] = key
        entity["key"] = key
    for kind in ("statements", "relations", "quantities"):
        for item in output[kind]:
            for field in ("subject", "object"):
                if field in item:
                    item[field] = remap.get(item[field], item[field])
            if "subjects" in item:
                item["subjects"] = [remap.get(k, k) for k in item["subjects"]]


def parse_model_output(content):
    """A malformed item cannot discard unrelated valid extraction work."""
    raw = json.loads(content, object_pairs_hook=unique_json_fields)
    if not isinstance(raw, dict):
        raise TypeError("Model output must be an object")
    result, errors = Output().model_dump(), []
    schemas = {
        "entities": Entity,
        "statements": Statement,
        "relations": Relation,
        "quantities": Quantity,
        "concepts": Concept,
    }
    for key in set(raw) - schemas.keys():
        errors.append({"kind": "top_level", "error": "UNEXPECTED_KEY", "key": str(key)[:100]})
    for kind, schema in schemas.items():
        items = raw.get(kind, [])
        if not isinstance(items, list):
            errors.append({"kind": kind, "error": "INVALID_ITEM_ARRAY"})
            continue
        for index, item in enumerate(items):
            try:
                if (
                    kind == "statements"
                    and isinstance(item, dict)
                    and not structured_provenance_enabled()
                    and item.get("epistemic") == PROVENANCE_ROLE
                ):
                    errors.append(
                        {
                            "kind": kind,
                            "index": index,
                            "errors": [{"location": ["epistemic"], "type": "literal_error"}],
                        }
                    )
                    continue
                if (
                    kind == "statements"
                    and isinstance(item, dict)
                    and not background_facets_enabled()
                    and any(field in item for field in BACKGROUND_FACET_FIELDS)
                ):
                    # Without the flag these fields are not part of the contract.
                    errors.append(
                        {
                            "kind": kind,
                            "index": index,
                            "errors": [
                                {"location": [field], "type": "extra_forbidden"}
                                for field in BACKGROUND_FACET_FIELDS
                                if field in item
                            ],
                        }
                    )
                    continue
                if (
                    kind in {"statements", "quantities"}
                    and isinstance(item, dict)
                    and "basis" in item
                    and not role_definitions_v2_enabled()
                ):
                    # Without the flag the evidence basis is not part of the contract.
                    errors.append(
                        {
                            "kind": kind,
                            "index": index,
                            "errors": [{"location": ["basis"], "type": "extra_forbidden"}],
                        }
                    )
                    continue
                if (
                    kind == "quantities"
                    and isinstance(item, dict)
                    and "study" in item
                    and not value_origin_mark_enabled()
                ):
                    # Without the flag the value's own study is not part of the contract.
                    errors.append(
                        {
                            "kind": kind,
                            "index": index,
                            "errors": [{"location": ["study"], "type": "extra_forbidden"}],
                        }
                    )
                    continue
                parsed = schema.model_validate(item).model_dump()
                if kind == "quantities" and parsed.get("study") is None:
                    parsed.pop("study", None)
                if kind in {"statements", "quantities"} and parsed.get("basis") is None:
                    parsed.pop("basis", None)
                for field in BACKGROUND_FACET_FIELDS:
                    if field in parsed and parsed[field] is None:
                        del parsed[field]
                result[kind].append(parsed)
            except ValidationError as error:
                errors.append(
                    {
                        "kind": kind,
                        "index": index,
                        "errors": [
                            {"location": list(e["loc"]), "type": e["type"]} for e in error.errors()
                        ],
                    }
                )
    return result, errors


def completed_json_prefix(content):
    """Recover only fully closed items in an output-limit prefix, never repair an item.

    This recognizes the actual top-level object/array grammar. It does not scan
    arbitrary braces or ignore garbage preceding JSON. Always remains incomplete.
    """
    decoder, result, pos = json.JSONDecoder(object_pairs_hook=unique_json_fields), {}, 0

    def skip(index):
        while index < len(content) and content[index].isspace():
            index += 1
        return index

    pos = skip(pos)
    if content[pos : pos + 1] != "{":
        raise ValueError("INVALID_JSON_PREFIX")
    pos += 1
    try:
        while True:
            key, pos = decoder.raw_decode(content, skip(pos))
            if not isinstance(key, str) or key in result:
                raise ValueError("INVALID_OR_DUPLICATE_ARRAY_KEY")
            pos = skip(pos)
            if content[pos : pos + 1] != ":":
                break
            pos = skip(pos + 1)
            if content[pos : pos + 1] != "[":
                break
            result[key] = []
            pos = skip(pos + 1)
            while content[pos : pos + 1] != "]":
                item, pos = decoder.raw_decode(content, pos)
                result[key].append(item)
                pos = skip(pos)
                if content[pos : pos + 1] == ",":
                    pos = skip(pos + 1)
                elif content[pos : pos + 1] != "]":
                    return result
            pos = skip(pos + 1)
            if content[pos : pos + 1] != ",":
                break
            pos = skip(pos + 1)
    except json.JSONDecodeError:
        pass
    return result


def expand_entity_refs(parsed, wire_entities):
    """Exact scoped lookup; unresolved names stay unresolved, including prefixes."""
    for kind in ("statements", "relations", "quantities"):
        for item in parsed[kind]:
            for field in ("subject", "object"):
                if field in item:
                    item[field] = wire_entities.get(item[field], item[field])
            if "subjects" in item:
                item["subjects"] = [wire_entities.get(k, k) for k in item["subjects"]]


def parse_stage_output(content, stage, anchors, finish_reason, quantities=None):
    errors = []
    try:
        raw = json.loads(content, object_pairs_hook=unique_json_fields)
    except json.JSONDecodeError:
        if finish_reason != "length":
            raise
        raw = completed_json_prefix(content)
        errors.append({"kind": "response", "error": "TRUNCATED_JSON_PREFIX"})
    if not isinstance(raw, dict):
        raise TypeError("Model output must be an object")
    allowed = STAGES[stage]
    for key in raw.keys() - set(allowed):
        errors.append({"kind": "top_level", "error": "UNEXPECTED_STAGE_KEY", "key": key})
    expanded = {}
    for kind in allowed:
        if kind not in raw:
            errors.append({"kind": kind, "error": "MISSING_STAGE_ARRAY"})
        items = raw.get(kind, [])
        if not isinstance(items, list):
            errors.append({"kind": kind, "error": "INVALID_ITEM_ARRAY"})
            continue
        expanded[kind] = []
        for index, original in enumerate(items):
            item = copy.deepcopy(original)
            if kind == "statements" and isinstance(item, dict) and "anchor" in item:
                if (
                    set(item)
                    - {"modality"}
                    - (set(BACKGROUND_FACET_FIELDS) if background_facets_enabled() else set())
                    - ({"basis"} if role_definitions_v2_enabled() else set())
                    != {"anchor", "epistemic", "subjects", "study"}
                    or not isinstance(item["anchor"], str)
                    or item["anchor"] not in anchors
                    or anchors[item["anchor"]].get("statement_eligible") is False
                    or item["epistemic"] not in STATEMENT_CLASSES
                    or (
                        item["epistemic"] == PROVENANCE_ROLE and not structured_provenance_enabled()
                    )
                ):
                    errors.append(
                        {
                            "kind": kind,
                            "index": index,
                            "error": "INVALID_LITERAL_STATEMENT_REFERENCE",
                        }
                    )
                    continue
                anchor = item.pop("anchor")
                item.update(
                    text=anchors[anchor]["quote"],
                    class_id=STATEMENT_CLASSES[item["epistemic"]],
                    support=[anchor],
                )
            if kind == "quantities" and isinstance(item, dict) and "quantity_ref" in item:
                if (
                    set(item)
                    - {"printed_name", "modality"}
                    - ({"study"} if value_origin_mark_enabled() else set())
                    - ({"basis"} if role_definitions_v2_enabled() else set())
                    != {"quantity_ref", "subject", "label", "epistemic"}
                    or not isinstance(item["quantity_ref"], str)
                    or item["quantity_ref"] not in (quantities or {})
                ):
                    errors.append(
                        {
                            "kind": kind,
                            "index": index,
                            "error": "INVALID_ORIGINAL_QUANTITY_REFERENCE",
                        }
                    )
                    continue
                quantity = quantities[item.pop("quantity_ref")]
                item.update({k: quantity[k] for k in ("expression", "unit", "support")})
            refs = item.get("support") if isinstance(item, dict) else None
            if (
                not isinstance(refs, list)
                or not refs
                or not all(isinstance(ref, str) and ref in anchors for ref in refs)
            ):
                errors.append({"kind": kind, "index": index, "error": "INVALID_SOURCE_ANCHORS"})
                continue
            item["support"] = [
                {k: anchors[ref][k] for k in ("evidence_id", "quote", "start")} for ref in refs
            ]
            expanded[kind].append(item)
    parsed, schema_errors = parse_model_output(json.dumps(expanded))
    if finish_reason != "stop":
        errors.append({"kind": "response", "error": "INCOMPLETE_FINISH", "reason": finish_reason})
    return parsed, errors + schema_errors
