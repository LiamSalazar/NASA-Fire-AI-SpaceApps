"""Bounded minimal linguistic proposals resolved against explicit registry authority."""

import re

from pydantic import BaseModel, ConfigDict

from nasa_fire_ai.query.v2 import (
    ComparisonV2,
    EntityConstraintV2,
    GenericValue,
    PropertyConstraintV2,
    QueryIntentV2,
)


class PropertyMention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    expression: str


class MinimalInterpretationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str = "search"
    targets: list[str] = []
    entities: list[str] = []
    properties: list[PropertyMention] = []
    requested_information: list[str] = []
    comparison_operands: list[str] = []
    sources: list[str] = []
    unknown: list[str] = []
    ambiguous: list[str] = []
    conversation_reference: str | None = None


PROMPT_VERSION = "phase3c-minimal-final-repair-v1"
SYSTEM_PROMPT = """Interpret the user's linguistic query. Return JSON only with these keys:
operation (search/compare/explain), targets (raw class mentions), entities (raw mentions),
properties (list of {label: raw property mention, expression: original numeric/categorical expression}),
requested_information (raw mentions), comparison_operands (raw mentions), sources (raw source IDs),
unknown (unrecognized terms), ambiguous (ambiguous terms), conversation_reference (string or null).
Do not invent canonical ontology IDs, perform unit conversions, or add scientific constraints.
Preserve numbers, units, inequalities, ranges, approximate wording and explicit +/- tolerance.
Use lists of strings, never objects, for all mention lists except properties.
Copy surface terms rather than classifying familiar terms as unknown. Omit absent mentions.
targets means the kind of object requested (e.g. experiments, publications), NOT materials
or the full query. entities contains separate material, investigation, gravity or run mentions.
requested_information contains only explicitly requested genres (observations, conclusions,
requirements, measurements, guidance, open questions); never repeat the entire question.
For a bare constraint search, targets and requested_information may both be empty.
Bare flow/velocity, Saffire and acrylic require ambiguity preservation. Airflow velocity is distinct from
flame-spread velocity. An unknown concept must remain unknown. No prose or additional keys.
sources contains only explicitly named source identifiers, never NASA, materials or investigations.
A numeric filter alone is not a request for measurements. Copy both comparison operands;
numeric filters are not operands. Preserve approximation words in expressions. Known
ordinary request words are not unknown science. Use search for evidence lookup,
compare only for genuine comparison, explain only for explicit explanation requests."""


def parse_expression(expression, datatype, operators):
    if datatype == "categorical":
        return "EQ", GenericValue(reported_value=expression, raw_expression=expression)
    text = expression.strip().lower()
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    range_match = re.search(rf"({number})\s*[-–]\s*({number})", text)
    nums = re.findall(number, text)
    from nasa_fire_ai.query.numeric_mentions import UNIT

    unit_matches = list(re.finditer(r"(?<![A-Za-z])" + UNIT, text, re.IGNORECASE))
    unit = unit_matches[0].group(0) if unit_matches else None
    unit = "%" if unit == "percent" else unit
    units = [match.group(0) for match in unit_matches]
    if len({"%" if u == "percent" else u for u in units}) > 1:
        raise ValueError("mixed-unit expression requires explicit normalization")
    if not nums:
        raise ValueError("numeric expression has no value")
    value = GenericValue(
        reported_value=float(nums[0]), reported_unit=unit, raw_expression=expression
    )
    if "between" in text or range_match or re.search(r"\d\s+to\s+\d", text):
        if range_match and "between" not in text:
            nums = list(range_match.groups())
        if len(nums) != 2:
            raise ValueError("range requires two values")
        value.reported_value = None
        value.lower, value.upper = map(float, nums)
        return "BETWEEN", value
    if any(
        x in text for x in ("about", "roughly", "approximately", "approx", "~", "≈", "±", "+/-")
    ):
        value.approximate = True
        if "±" in text or "+/-" in text:
            if len(nums) != 2:
                raise ValueError("tolerance requires two values")
            value.tolerance = float(nums[1])
        return "APPROX", value
    for mention in sorted(operators, key=len, reverse=True):
        if mention in text:
            return operators[mention], value
    return "EQ", value


def resolve_minimal(proposal, registry, language, context=None, query=None):
    if query:
        from nasa_fire_ai.query.numeric_mentions import literal_numeric_mentions

        literal = literal_numeric_mentions(query, registry)
        literal_ids = {row["property_id"] for row in literal}
        # Raw, explicitly scoped numeric text takes precedence over linguistic
        # proposals. Unknown unrelated properties remain unresolved.
        retained = []
        unsupported_numeric = []
        for mention in proposal.properties:
            status, pid = registry.resolve_property(mention.label)
            if status == "CANONICAL" and registry.properties[pid].datatype == "numeric":
                definition = registry.properties[pid]
                explicitly_named = any(
                    re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", query, re.IGNORECASE)
                    for alias in [pid, *definition.aliases]
                )
                if not explicitly_named:
                    if not literal:
                        unsupported_numeric.append("numeric_quantity_not_explicit_in_query")
                    continue
                if pid not in literal_ids and " ".join(
                    mention.expression.lower().split()
                ) not in " ".join(query.lower().split()):
                    unsupported_numeric.append(
                        "numeric_expression_or_unit_not_literal:" + mention.expression
                    )
                    continue
            same_surface = any(
                mention.label.lower() == row["label"].lower() + " velocity"
                and mention.expression == row["expression"]
                for row in literal
            )
            if pid not in literal_ids and not (status == "UNKNOWN" and same_surface):
                retained.append(mention)
        proposal = proposal.model_copy(
            update={
                "unknown": list(dict.fromkeys([*proposal.unknown, *unsupported_numeric])),
                "properties": retained
                + [
                    PropertyMention(label=row["label"], expression=row["expression"])
                    for row in literal
                ],
            }
        )
    language = {
        **language,
        "entity_mentions": {
            **language["entity_mentions"],
            **getattr(registry, "entity_mentions", {}),
        },
        "information_mentions": {
            **language["information_mentions"],
            **{
                cid: list(
                    dict.fromkeys(
                        [
                            *language["information_mentions"].get(cid, []),
                            *meta.get("query_terms", []),
                        ]
                    )
                )
                for cid, meta in registry.class_metadata.items()
                if meta.get("information") and meta.get("parent")
            },
        },
        "target_mentions": {
            **language.get("target_mentions", {}),
            **{
                cid: meta.get("query_terms", [])
                for cid, meta in registry.class_metadata.items()
                if meta.get("target") and meta.get("parent")
            },
        },
    }

    def contains(text, label):
        return bool(re.search(rf"(?<!\w){re.escape(label.lower())}(?!\w)", text.lower()))

    def known_entities(text):
        from nasa_fire_ai.query.record_identity import mask_deictic_references

        text = mask_deictic_references(text)
        matches = [
            (eid, meta)
            for eid, meta in language["entity_mentions"].items()
            if eid in registry.entities and any(contains(text, a) for a in [eid, *meta["aliases"]])
        ]
        # Suppress a shorter alias only when its occurrence is contained within
        # a longer approved alias. Separate mentions still retain both identities.
        spans = []
        for eid, meta in matches:
            for alias in [eid, *meta["aliases"]]:
                spans.extend(
                    (m.start(), m.end(), eid)
                    for m in re.finditer(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", text.lower())
                )
        retained = {
            eid
            for start, end, eid in spans
            if not any(
                a <= start and end <= b and (a < start or end < b)
                for a, b, other in spans
                if other != eid
            )
        }
        return [(eid, meta) for eid, meta in matches if eid in retained]

    # Minimal proposals can contain a compound surface phrase. Split only using
    # approved aliases, never language-model suggested scientific equivalence.
    if query:
        discovered = [eid for eid, _ in known_entities(query)]
        proposal = proposal.model_copy(
            update={"entities": list(dict.fromkeys(proposal.entities + discovered))}
        )

    def resolve_operand(mention):
        direct = [e for e in registry.entities if e.lower() == mention.lower()]
        if len(direct) == 1:
            return direct
        investigations = [
            e for e, meta in known_entities(mention) if meta["relation"] == "belongsToInvestigation"
        ]
        investigations += [
            e
            for e, meta in known_entities(query or "")
            if meta["relation"] == "belongsToInvestigation"
        ]
        if context and context.current_investigation:
            investigations.append(context.current_investigation)
        suffix = re.search(r"\b([a-z]+\d+)\s*$", mention, re.IGNORECASE)
        matches = [
            e
            for e in registry.entities
            if suffix
            and e.lower().endswith("-" + suffix[1].lower())
            and (not investigations or any(e.startswith(i + "-") for i in investigations))
        ]
        return matches if len(matches) == 1 else []

    unresolved = list(proposal.unknown)
    ambiguous = list(proposal.ambiguous)
    if query and literal and re.search(r"\b(?:or|either)\b", query, re.IGNORECASE):
        ambiguous.append("numeric_disjunction_requires_clarification")
    protected = {x.lower() for x in language.get("ambiguous_mentions", [])}
    entities = []
    for mention in proposal.entities:
        if mention.lower() in protected:
            ambiguous.append(mention)
            continue
        matches = known_entities(mention)
        if query:
            raw_ids = {eid for eid, _ in known_entities(query)}
            matches = [(eid, meta) for eid, meta in matches if eid in raw_ids]
        if matches:
            entities.extend(
                EntityConstraintV2(relation=meta["relation"], entity_id=eid)
                for eid, meta in matches
            )
        else:
            if not resolve_operand(mention):
                unresolved.append(mention)
    properties = []
    resolved_property_mentions = set()
    for mention in proposal.properties:
        if mention.label.lower() in protected:
            ambiguous.append(mention.label)
            continue
        status, pid = registry.resolve_property(mention.label)
        if status != "CANONICAL":
            (ambiguous if status == "AMBIGUOUS" else unresolved).append(mention.label)
            continue
        resolved_property_mentions.add(mention.label.strip().lower())
        try:
            expression = mention.expression
            if query and not any(
                w in expression.lower() for w in ("about", "roughly", "approx", "±", "+/-", "~")
            ):
                n = re.search(r"\d+(?:\.\d+)?", expression)
                if n and re.search(
                    rf"(?:about|roughly|approximately|approx\.?|~)\s*{re.escape(n[0])}(?!\d)",
                    query,
                    re.IGNORECASE,
                ):
                    expression = "approximately " + expression
            operator, value = parse_expression(
                expression, registry.properties[pid].datatype, language["operators"]
            )
            c = PropertyConstraintV2(property_id=pid, operator=operator, value=value)
            intrinsic_context = registry.properties[pid].context
            if intrinsic_context is not None:
                c.qualifiers["context"] = intrinsic_context
            elif query:
                for qualifier, aliases in language.get("context_mentions", {}).items():
                    if any(contains(query, a) for a in aliases):
                        c.qualifiers["context"] = qualifier
            registry.validate(c)
            properties.append(c)
        except ValueError:
            unresolved.append(mention.expression)
    information = []
    for mention in proposal.requested_information:
        matches = [
            cid
            for cid, aliases in language["information_mentions"].items()
            if cid != "ExperimentalRun" and any(contains(mention, a) for a in [cid, *aliases])
        ]
        if query:
            matches = [
                cid
                for cid in matches
                if any(contains(query, a) for a in [cid, *language["information_mentions"][cid]])
            ]
        if matches:
            information.extend(matches)
        elif not known_entities(mention):
            unresolved.append(mention)
    if query:
        information.extend(
            cid
            for cid, aliases in language["information_mentions"].items()
            if cid != "ExperimentalRun" and any(contains(query, a) for a in aliases)
        )
        if re.search(r"\bwhat\b.*\b(?:reported|reports|report)\b", query, re.IGNORECASE):
            information.extend(
                c
                for c in ("ReportedObservation", "Intervention", "NASAConclusion")
                if c in registry.information_classes
            )
    targets = []
    for mention in proposal.targets:
        matches = [cid for cid in registry.target_classes if cid.lower() == mention.lower()]
        matches += [
            cid
            for cid, aliases in {
                **language["information_mentions"],
                **language.get("target_mentions", {}),
            }.items()
            if cid in registry.target_classes and mention.lower() in {a.lower() for a in aliases}
        ]
        if matches:
            target = matches[0]
            # Information classes can also be target classes in the registry.
            # When the query carries run-level entity/property filters, those
            # filters scope experimental records; the requested-information
            # class controls which evidence is returned.
            if (
                target in information
                and not registry.class_metadata.get(target, {}).get("documentary")
                and (entities or properties)
            ):
                target = "ExperimentalRun"
            targets.append(target)
        elif (
            not known_entities(mention)
            and not resolve_operand(mention)
            and not any(
                contains(mention, a)
                for aliases in language["information_mentions"].values()
                for a in aliases
            )
        ):
            unresolved.append(mention)
    operands = []
    for mention in proposal.comparison_operands if proposal.operation.lower() == "compare" else []:
        if mention.lower() in protected:
            ambiguous.append(mention)
            continue
        matches = resolve_operand(mention)
        if len(matches) == 1:
            operands.extend(matches)
        else:
            unresolved.append(mention)
    conversation_reference = proposal.conversation_reference
    if context and query:
        candidates = [
            e
            for e in context.current_run_ids
            if re.search(rf"\b{re.escape(e.split('-')[-1])}\b", query, re.IGNORECASE)
        ]
        if (
            not candidates
            and re.search(r"\bsecond\b", query, re.IGNORECASE)
            and len(context.current_run_ids) >= 2
        ):
            candidates = [context.current_run_ids[1]]
        if len(candidates) == 1:
            conversation_reference = candidates[0]
            unresolved = [m for m in unresolved if not resolve_operand(m)]
    if conversation_reference and context and context.current_investigation:
        entities.append(
            EntityConstraintV2(
                relation="belongsToInvestigation", entity_id=context.current_investigation
            )
        )
    # An implicit run target is a linguistic default, not a scientific inference.
    # Explicit documentary targets take precedence and remain documentary searches.
    if not targets:
        documentary = [
            c for c in information if registry.class_metadata.get(c, {}).get("documentary")
        ]
        explicit_objects = [
            cid
            for cid, aliases in language.get("target_mentions", {}).items()
            if query and cid in registry.target_classes and any(contains(query, a) for a in aliases)
        ]
        targets = explicit_objects or documentary or ["ExperimentalRun"]
    if query:
        # Reject any canonical association for a protected raw mention even when
        # the language model replaced it with a plausible scientific identity.
        raw = query.lower()
        for mention in protected:
            if re.search(rf"(?<!\w){re.escape(mention)}(?!\w)", raw):
                qualified = any(
                    mention in alias.lower() and alias.lower() != mention and alias.lower() in raw
                    for p in registry.properties.values()
                    for alias in p.aliases
                ) or any(
                    mention in alias.lower() and alias.lower() != mention and alias.lower() in raw
                    for meta in language["entity_mentions"].values()
                    for alias in meta["aliases"]
                )
                if not qualified:
                    ambiguous.append(mention)
                    # Ambiguity blocks DIRECT; no silently invented identity.
                    scope = language.get("ambiguity_scopes", {}).get(mention, {})
                    entities = [e for e in entities if e.relation not in scope.get("relations", [])]
                    if scope.get("properties"):
                        properties = []
    exact_aliases = {
        a.lower()
        for eid, meta in language["entity_mentions"].items()
        for a in [eid, *meta["aliases"]]
    }
    unresolved = [
        x
        for x in unresolved
        if x.lower() not in exact_aliases and registry.resolve_property(x)[0] != "CANONICAL"
    ]
    entities = list({(e.relation, e.entity_id): e for e in entities}.values())
    # QueryIntentV2 has no union/disjunction operator. Multiple canonical
    # values in one relation slot therefore cannot safely be interpreted as
    # a conjunctive filter over one entity. Preserve the recognized values,
    # but require clarification unless the query already resolves an explicit
    # comparison. This is relation-generic, not material- or source-specific.
    relation_values: dict[str, set[str]] = {}
    for constraint in entities:
        relation_values.setdefault(constraint.relation, set()).add(constraint.entity_id)
    grouping_ambiguities = []
    if not (len(operands) >= 2 and proposal.operation.lower() == "compare"):
        grouping_ambiguities = [
            f"multiple_values_for_relation:{relation}"
            for relation, values in relation_values.items()
            if len(values) > 1
            and not (
                relation == registry.selection_policy.get("context", {}).get("preference_relation")
                and query
                and any(
                    term in query.lower()
                    for term in registry.selection_policy.get("context", {}).get(
                        "comparative_terms", []
                    )
                )
            )
        ]
        if (
            query
            and re.search(r"\b(?:family|series)\b", query, re.IGNORECASE)
            and len(relation_values.get("belongsToInvestigation", set())) == 1
            and "belongsToExperimentFamily" not in relation_values
            and "ExperimentFamily" not in targets
        ):
            grouping_ambiguities.append("investigation_group_scope_unestablished")
    # Reconcile contradictory slots using pre-existing authority and expressions
    # actually validated. This does not resolve new scientific terms.
    information_aliases = {
        a.lower()
        for cid, aliases in language["information_mentions"].items()
        for a in [cid, *aliases]
    }
    validated_expressions = {
        c.value.raw_expression.strip().lower() for c in properties if c.value.raw_expression
    }
    known = (
        exact_aliases
        | information_aliases
        | validated_expressions
        | {s.lower() for s in registry.source_ids}
        | {s.lower() for s in language.get("non_scientific_mentions", [])}
    )
    unresolved = [x for x in unresolved if x.strip().lower() not in known]
    normalized_ambiguous = []
    for mention in ambiguous:
        if mention == "numeric_disjunction_requires_clarification":
            normalized_ambiguous.append(mention)
            continue
        if len(operands) >= 2 and known_entities(mention):
            residual = mention.lower()
            for eid, meta in known_entities(mention):
                for alias in sorted([eid, *meta["aliases"]], key=len, reverse=True):
                    residual = re.sub(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", " ", residual)
            mentioned_operands = 0
            for operand in operands:
                suffix = operand.rsplit("-", 1)[-1]
                if contains(residual, suffix):
                    mentioned_operands += 1
                    residual = re.sub(rf"\b{re.escape(suffix.lower())}\b", " ", residual)
            residual = re.sub(r"\b(?:and|versus|vs|compare)\b|[\s,/]+", "", residual)
            if mentioned_operands == len(operands) and not residual:
                continue
        key = mention.strip().lower()
        property_status, _ = registry.resolve_property(mention)
        if key in resolved_property_mentions or property_status == "CANONICAL":
            continue
        if key in exact_aliases or key in information_aliases or key in known:
            continue
        if property_status == "UNKNOWN" and key not in protected:
            unresolved.append(mention)
            continue
        normalized_ambiguous.append(mention)
    ambiguous = list(dict.fromkeys([*normalized_ambiguous, *grouping_ambiguities]))
    unresolved = list(dict.fromkeys(unresolved))
    source_lookup = {s.lower(): s for s in registry.source_ids}
    sources = [
        source_lookup.get(s.lower(), s)
        for s in proposal.sources
        if s.lower() not in known or s.lower() in source_lookup
    ]
    if query:
        raw_sources = re.findall(r"\bsource\s+(?:id\s+)?([\w.-]+)", query, re.IGNORECASE)
        sources.extend(s for s in raw_sources if s in registry.source_ids)
    sources = list(dict.fromkeys(sources))
    from nasa_fire_ai.query.conceptual import is_conceptual_question

    if query and is_conceptual_question(query):
        # Existing EXPLAIN/documentary representation suffices. Unknown terms
        # remain in the original question; no material equivalence is asserted.
        return QueryIntentV2(
            operation="EXPLAIN",
            targets=["Publication"],
            source_constraints=sources,
            entity_constraints=[e for e in entities if e.relation == "belongsToInvestigation"],
        )
    from nasa_fire_ai.services.investigation import question_kind

    if query and question_kind(query, QueryIntentV2()) == "bibliographic":
        return QueryIntentV2(
            targets=["Publication"],
            requested_information=["Publication"],
            source_constraints=sources,
            entity_constraints=[e for e in entities if e.relation == "belongsToInvestigation"],
        )
    return QueryIntentV2(
        operation={"search": "SEARCH", "compare": "COMPARE", "explain": "EXPLAIN"}.get(
            proposal.operation.lower(), "SEARCH"
        ),
        targets=list(dict.fromkeys(targets)),
        entity_constraints=entities,
        property_constraints=properties,
        requested_information=list(dict.fromkeys(information)),
        comparison=ComparisonV2(operands=operands) if len(operands) >= 2 else None,
        source_constraints=sources,
        unresolved_mentions=list(dict.fromkeys(unresolved)),
        ambiguities=list(dict.fromkeys(ambiguous)),
        clarification_required=bool(ambiguous),
        conversation_reference=conversation_reference,
    )
