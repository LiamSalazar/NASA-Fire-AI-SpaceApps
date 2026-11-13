"""Exact registry identity lookup; never substitutes semantic candidates."""

import re

from nasa_fire_ai.services.conversation import public_evidence
from nasa_fire_ai.services.research_console import card


def resolve_identifier(search, query):
    query = query.strip()
    matches = []
    for row in search.registry.db.execute(
        "SELECT source_id,title,doi,url,source_type,nasa_id FROM sources "
        "WHERE source_id = ? COLLATE NOCASE OR nasa_id = ? COLLATE NOCASE",
        (query, query),
    ):
        source = dict(row)
        evidence = search.registry.db.execute(
            "SELECT p.evidence_id FROM passages p JOIN documents d USING(document_id) "
            "WHERE d.source_id=? ORDER BY p.evidence_id LIMIT 20",
            (row["source_id"],),
        ).fetchall()
        matches.append({"kind": "source", **source, "evidence_ids": [e[0] for e in evidence]})
    row = search._evidence(query)
    if row:
        matches.append({"kind": "evidence", **public_evidence(row)})
    # The immutable graph inventory bounds this lookup. Preserve every matching
    # source-local record rather than inventing a global record identity.
    for subject in sorted(search.store.registry.entities):
        payload = search.store.payload(subject)
        if query.casefold() in {
            subject.casefold(),
            str(payload.get("reported_identifier", "")).casefold(),
        }:
            matches.append({"kind": "entity", **card(search, subject)})
    recognized = bool(matches) or bool(
        re.fullmatch(
            r"(?:psi-\d+|ntrs[-:]?\d+|\d{11,13}|E-[\w.-]+|[\w]+(?:-[\w]+)*-\d+[\w.-]*)",
            query,
            re.IGNORECASE,
        )
    )
    return {
        "query": query,
        "identifier": recognized,
        "items": matches[:100],
        "total": len(matches),
        "ambiguous": len(matches) > 1,
        "scope": "Exact registered identities; identity alone does not establish scientific support.",
    }
