"""Linguistic operation guard; contains no scientific identity mappings."""

import re


def is_conceptual_question(query):
    return bool(
        re.search(
            r"\b(?:does\s+.+?\s+mean\s+|(?:is|are)\s+.+?\s+(?:the same as|equivalent to|a kind of|a type of)\s+|"
            r"what\s+(?:does\s+.+?\s+mean|is\s+the\s+(?:meaning|definition)\s+of)|"
            r"relationship\s+between\s+|^\s*(?:define|what is meant by)\s+|"
            r"^\s*(?:is|are)\s+(?!there\b).+?\s+(?:a|an)\s+(?!experiment\b|run\b|test\b|measurement\b).+?\?)",
            query,
            re.IGNORECASE,
        )
    )


def approved_conceptual_support(query, store, evidence):
    """Inspect approved registry identities and provenance-bearing ontology edges."""
    from dataclasses import asdict

    from nasa_fire_ai.query.hierarchy import taxonomy_edges

    mentions = getattr(store.registry, "entity_mentions", {})
    spans = []
    for entity in store.registry.entities:
        aliases = [entity, *mentions.get(entity, {}).get("aliases", [])]
        for alias in aliases:
            for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", query, re.IGNORECASE):
                spans.append((match.start(), match.end(), entity, alias))
    matches = {}
    for start, end, entity, alias in spans:
        if any(a <= start and end <= b and (a < start or end < b) for a, b, _, _ in spans):
            continue
        matches.setdefault(entity, [])
        if alias not in matches[entity]:
            matches[entity].append(alias)
    approved, pending = taxonomy_edges(store, evidence)
    relations = [
        asdict(edge) for edge in approved if edge.subject in matches and edge.object in matches
    ]
    return {
        "registry_matches": matches,
        "approved_relations": relations,
        "pending_relations_not_used": sum(
            edge.subject in matches or edge.object in matches for edge in pending
        ),
        "interpretation_limit": "A registry alias lookup or specimen description does not establish a new family-to-polymer equivalence.",
    }


def technical_topic_supported(query, text):
    """Explicit linguistic topic modifiers cannot be satisfied by another topic.

    This checks wording only. It establishes no scientific identity, causal
    relation, applicability or equivalence, and cannot promote evidence.
    """
    modifiers = re.findall(r"\b([a-z]{6,})-(?:based|driven|induced)\b", query.lower())
    return not modifiers or all(term in " ".join(str(text).lower().split()) for term in modifiers)
