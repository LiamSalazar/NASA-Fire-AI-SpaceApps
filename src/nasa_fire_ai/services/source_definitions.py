"""Source-local acronym definitions as additional registered evidence.

This resolves a name, never a quantity or experimental relation. Definitions
must be printed in the same original document; every added span is cited.
"""

import re

_DEFINITION = re.compile(
    r"([A-Za-z][A-Za-z–−-]*(?:\s+[A-Za-z][A-Za-z–−-]*){1,11})"
    r"\s*\(([A-Z][A-Z0-9]{1,7})\)"
)


def registered_quotation_fragments(text, evidence_ids, registry, *, context_id=None):
    """Locate a curated quotation across original pages without inventing a span.

    Only exact source substrings may cover the quotation, in original page
    order, within one document. Inter-page whitespace is the sole join operation.
    """
    # Explicit curator-declared fragments may share a page (for example,
    # multi-column report text separated by a footnote). Never guess omitted
    # words: the snapshot registry supplies each original fragment and locator.
    import sqlite3

    db = getattr(registry, "db", None)
    if (
        context_id
        and isinstance(db, sqlite3.Connection)
        and db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='curated_quotation_parts'"
        ).fetchone()
    ):
        rows = db.execute(
            "SELECT * FROM curated_quotation_parts WHERE context_id=? ORDER BY part_ordinal",
            (context_id,),
        ).fetchall()
        if rows:
            allowed, documents, spans = set(evidence_ids), set(), []
            for ordinal, row in enumerate(rows):
                original = registry.resolve(row["evidence_id"])
                if (
                    row["part_ordinal"] != ordinal
                    or row["evidence_id"] not in allowed
                    or not original
                    or row["source_checksum"] != original.get("checksum")
                    or row["passage_start"] < 0
                    or row["passage_end"] <= row["passage_start"]
                    or original["text"][row["passage_start"] : row["passage_end"]]
                    != row["part_text"]
                ):
                    return []
                documents.add(original.get("document_id"))
                spans.append(
                    {
                        "evidence_id": row["evidence_id"],
                        "text": row["part_text"],
                        "scope": "curated_quotation_part",
                    }
                )
            if (
                None in documents
                or len(documents) != 1
                or " ".join(text.split())
                != " ".join("\n".join(span["text"] for span in spans).split())
            ):
                return []
            return spans
    sources = [source for eid in evidence_ids if (source := registry.resolve(eid))]
    if (
        not sources
        or not sources[0].get("document_id")
        or len({source.get("document_id") for source in sources}) != 1
    ):
        return []
    sources.sort(key=lambda source: (source.get("page") or 0, source["evidence_id"]))
    remaining, spans = text, []
    for source in sources:
        low, high = 0, len(remaining)
        while low < high:
            middle = (low + high + 1) // 2
            if remaining[:middle] in source["text"]:
                low = middle
            else:
                high = middle - 1
        if not low:
            continue
        spans.append({"evidence_id": source["evidence_id"], "text": remaining[:low]})
        remaining = remaining[low:]
        remaining = remaining.removeprefix("\n")
        if not remaining:
            break
    normalized = lambda value: " ".join(value.split())
    if remaining or normalized("\n".join(span["text"] for span in spans)) != normalized(text):
        return []
    return spans


def document_definitions(registry, document_id):
    if not getattr(registry, "db", None):
        return []
    found = []
    for row in registry.db.execute(
        "SELECT evidence_id,text FROM passages WHERE document_id=? ORDER BY page,evidence_id LIMIT 256",
        (document_id,),
    ):
        for match in _DEFINITION.finditer(row["text"]):
            words = list(re.finditer(r"[A-Za-z][A-Za-z–−-]*", match[1]))
            for start in range(len(words)):
                initials = "".join(word[0][0].upper() for word in words[start:])
                if initials != match[2] or any(not word[0][0].isupper() for word in words[start:]):
                    continue
                begin = match.start(1) + words[start].start()
                found.append(
                    {
                        "long_name": row["text"][begin : match.end(1)],
                        "acronym": match[2],
                        "evidence_id": row["evidence_id"],
                        "text": row["text"][begin : match.end()],
                        "scope": "source_local_name_definition",
                    }
                )
                break
    normalized = lambda value: " ".join(re.findall(r"[a-z0-9]+", value.casefold()))
    distinct = {}
    meanings = {}
    for definition in found:
        key = (definition["acronym"], normalized(definition["long_name"]))
        distinct.setdefault(key, definition)
        meanings.setdefault(key[0], set()).add(key[1])
    # An ambiguous acronym is not reconciled across experimental contexts.
    return [definition for key, definition in distinct.items() if len(meanings[key[0]]) == 1]


def add_source_definitions(text, anchor, registry, cache):
    """Add only a matching name bridge, retaining all primary source spans."""
    document = anchor.get("document_id")
    if (
        not document
        or anchor.get("epistemic_type") != "documentary_content"
        or anchor.get("typed_fields")
    ):
        return
    if document not in cache:
        if len(cache) >= 64:
            cache.pop(next(iter(cache)))
        cache[document] = document_definitions(registry, document)
    original = " ".join(span["text"] for span in anchor["spans"])
    normalize = lambda value: " ".join(value.casefold().split())
    for definition in cache[document]:
        long_name = normalize(definition["long_name"])
        acronym = definition["acronym"]
        bridge = (
            long_name in normalize(text)
            and re.search(r"(?<!\w)" + re.escape(acronym) + r"(?!\w)", original)
        ) or (
            long_name in normalize(original)
            and re.search(r"(?<!\w)" + re.escape(acronym) + r"(?!\w)", text)
        )
        span = {key: definition[key] for key in ("evidence_id", "text", "scope")}
        if bridge and span not in anchor["spans"]:
            anchor["spans"] = [*anchor["spans"], span]
