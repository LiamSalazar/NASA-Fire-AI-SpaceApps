"""Exact numbered-section context from the same registered original document.

These are evidence locators, not new ontology entities or inferred procedures.
Only an explicit parent heading may supply a numbered test's identity.
"""

import re

SECTION = re.compile(
    r"(?m)^[ \t]*(?P<key>(?:[A-Z]\.\d+(?:\.\d+)*|\d+(?:\.\d+)+))[a-z]?[ \t]*(?:\n[ \t]*)?"
    r"(?P<title>(?!(?i:yes|no|true|false)[ \t\r]*(?:\n|$))[A-Z][^\n]{1,160})"
)
TEST = re.compile(r"\bTest\s+(\d+)\b", re.IGNORECASE)
DOCUMENT_REFERENCE = re.compile(
    r"\b(?:NASA(?:/|-)(?:TM|TP|CP|CR|SP|STD)[-–−/]\d[A-Za-z0-9/-]*"
    r"(?:\s+(?:(?:with|w/)\s*)?Change\s+\d+)?|NTRS[-\s]*\d{8,})",
    re.IGNORECASE,
)


def named_source_ids(text, registry):
    """Resolve printed document/version identifiers, never topical similarity."""

    def key(value):
        return re.sub(r"\bwith\b|w/|[^a-z0-9]", "", value.casefold())

    requested = {key(m[0]) for m in DOCUMENT_REFERENCE.finditer(text)}
    if not requested or not getattr(registry, "db", None):
        return set()
    names = getattr(registry, "_registered_source_reference_names", None)
    if names is None:
        rows = list(registry.db.execute("SELECT source_id,title FROM sources"))
        rows += list(
            registry.db.execute(
                "SELECT s.source_id,p.text AS title FROM sources s "
                "JOIN documents d ON d.source_id=s.source_id "
                "JOIN passages p ON p.document_id=d.document_id "
                "WHERE p.page=1 AND p.section='document'"
            )
        )
        names = {}
        for row in rows:
            row = dict(row)
            if source_id := row.get("source_id"):
                names.setdefault(source_id, set()).update(
                    key(m[0])
                    for m in DOCUMENT_REFERENCE.finditer(
                        source_id + "\n" + (row.get("title") or "")
                    )
                )
        registry._registered_source_reference_names = names
    return {
        source_id
        for source_id, references in names.items()
        if any(
            q == ref or re.fullmatch(re.escape(q) + r"change\d+", ref)
            for q in requested
            for ref in references
        )
    }


CASE_CAPTION = re.compile(
    r"(?im)^[ \t]*(?:Figure|Fig\.)\s+\d+[A-Za-z]?[.\u2014\u2013-]+\s*Test\s+"
    r"(?P<label>[A-Z][A-Z0-9]*(?:[-\u2212\u2013\u2010]\d+[A-Z0-9-]*|\d+[A-Z0-9]*))\."
)
SECTION_QUOTATION = re.compile(
    r"In source section “(?P<section>[^”]+)”, the report states: “(?P<body>.*)”", re.DOTALL
)


def quoted_section_content(text):
    """Unwrap a proposed quotation for locating, never for factual acceptance."""
    match = SECTION_QUOTATION.fullmatch(text)
    return match["body"] if match else None


def continued_source_list(original, span, limit=900):
    """Keep a printed enumeration with its lead-in, stopping at the next section."""
    start = original.find(span)
    if start < 0 or not span.rstrip().endswith(":"):
        return None
    after = start + len(span)
    if not re.match(r"\s*(?:\(\d+\)|\d+[.)]|[a-z][.)]|[•-])\s+", original[after:]):
        return None
    following = SECTION.search(original, after)
    end = following.start() if following else len(original)
    window = original[start:end].strip()
    # Never silently cut off a condition to fit the quotation budget.
    return window if len(window) <= limit else None


def add_section_subject_context(anchor, registry, cache, store):
    """Recover an explicitly named investigation from a parent section's intro.

    This is source identity evidence only. It supplies neither a measurement
    nor a conclusion for a descendant paragraph. Multiple named investigations
    remain ambiguous instead of acquiring a document-wide default identity.
    """
    from nasa_fire_ai.services.ontology_support import investigation_mentions

    document = anchor.get("document_id")
    if not document or anchor.get("typed_fields") or not getattr(registry, "db", None):
        return
    if document not in cache:
        cache[document] = section_index(registry, document)
    events = cache[document]
    additions = []
    for span in anchor.get("spans", []):
        if span.get("scope") in {
            "section_heading",
            "source_record_heading",
            "source_local_name_definition",
            "source_subject_context",
        }:
            continue
        original = registry.resolve(span["evidence_id"]) or {}
        if original.get("document_id") != document or original.get("page") is None:
            continue
        start = original.get("text", "").find(span["text"])
        if start < 0:
            continue
        position = (original["page"], start)
        preceding = [e for e in events if (e["page"], e["offset"]) <= position]
        if not preceding:
            continue
        leaf = preceding[-1]["key"]
        ancestors = []
        for event in preceding:
            prefix = (
                re.sub(r"\.0$", "", event["key"]) if event["key"].count(".") == 1 else event["key"]
            )
            if leaf == event["key"] or leaf.startswith(prefix + "."):
                ancestors.append(event)
        for event in reversed(ancestors):
            # Examine only the intro before its next printed heading, never
            # the entire parent section or another investigation's results.
            following = [
                e for e in events if e["page"] == event["page"] and e["offset"] > event["offset"]
            ]
            end = following[0]["offset"] if following else len(event["page_text"])
            intro = event["page_text"][event["offset"] : end].strip()
            if not 20 <= len(intro) <= 1800:
                continue
            owners = investigation_mentions(intro, store)
            if len(owners) != 1:
                continue
            additions.append(
                {
                    "evidence_id": event["evidence_id"],
                    "text": intro,
                    "scope": "source_subject_context",
                }
            )
            break
    anchor["spans"] = [
        *anchor.get("spans", []),
        *[s for s in additions if s not in anchor.get("spans", [])],
    ]


def add_record_caption_context(anchor, registry):
    """Keep a printed figure's local test reference; never reconcile a physical run."""
    if not getattr(registry, "resolve", None):
        return
    references, headings = set(), []
    for span in list(anchor.get("spans", [])):
        if span.get("scope") in {
            "section_heading",
            "source_record_heading",
            "source_local_name_definition",
            "source_subject_context",
        }:
            continue
        source = registry.resolve(span["evidence_id"]) or {}
        original = source.get("text", "")
        start = original.find(span["text"])
        if start < 0:
            continue
        end = start + len(span["text"])
        captions = list(CASE_CAPTION.finditer(original))
        for i, caption in enumerate(captions):
            scope_end = captions[i + 1].start() if i + 1 < len(captions) else len(original)
            if start < scope_end and end > caption.start():
                references.add(caption["label"])
                headings.append(
                    {
                        "evidence_id": span["evidence_id"],
                        "text": caption[0],
                        "scope": "source_record_heading",
                    }
                )
    if references:
        anchor["source_record_references"] = sorted(references)
        anchor["spans"] = [*anchor["spans"], *[s for s in headings if s not in anchor["spans"]]]


def record_caption_errors(text, anchors):
    """A case-specific observation cannot silently become a general method finding."""
    errors = []
    for anchor in anchors:
        for label in anchor.get("source_record_references", []):
            literal = re.escape(label).replace("\\-", r"[-\u2212\u2013\u2010]")
            present = bool(re.search(r"(?<!\w)" + literal + r"(?!\w)", text, re.IGNORECASE))
            numbered = re.fullmatch(r"([A-Za-z]+)[-\u2212\u2013\u2010](\d+)", label)
            if numbered:
                prefix, number = numbered[1], str(int(numbered[2]))
                present |= bool(
                    re.search(
                        r"\b"
                        + re.escape(prefix)
                        + r"(?:[-\u2212\u2013\u2010]|\s+test\s+)0*"
                        + number
                        + r"(?!\d)",
                        text,
                        re.IGNORECASE,
                    )
                )
            if not present:
                errors.append(
                    "Source figure describes a particular test; preserve its printed test reference"
                )
    return errors


def section_quotation(anchor, registry, cache=None):
    """Render an exact quotation with its independently reconstructed section.

    This communicates the printed context of a quotation, not an inferred
    measurement or a model-generated paraphrase. Case figures require their
    own explicit record attribution and are excluded from this renderer.
    """
    if anchor.get("category") != "DOCUMENTARY":
        return None
    primary = [
        span
        for span in anchor.get("spans", [])
        if span.get("scope")
        not in {
            "section_heading",
            "source_record_heading",
            "source_local_name_definition",
            "source_subject_context",
        }
    ]
    if len(primary) != 1:
        return None
    span = primary[0]
    original = registry.resolve(span["evidence_id"]) or {}
    if span["text"] not in original.get("text", ""):
        return None
    checked = {**anchor, "spans": [dict(span)]}
    checked.pop("scientific_sections", None)
    checked.pop("source_record_references", None)
    add_section_context(checked, registry, cache if cache is not None else {})
    if checked.get("source_record_references") or not checked.get("scientific_sections"):
        return None
    keys = [
        SECTION.match(title)["key"]
        for title in checked["scientific_sections"]
        if SECTION.match(title)
    ]

    def contains(parent, child):
        prefix = parent[:-2] if re.fullmatch(r"\d+\.0", parent) else parent
        return parent == child or child.startswith(prefix + ".")

    if any(not contains(a, b) and not contains(b, a) for a in keys for b in keys):
        # A passage crossing two branches has no single section attribution.
        return None
    heading = " / ".join(" ".join(title.split()) for title in checked["scientific_sections"])
    return {
        "text": f"In source section “{heading}”, the report states: “{span['text']}”",
        "quoted_text": span["text"],
        "anchor": checked,
    }


def section_index(registry, document):
    if not getattr(registry, "db", None):
        return []
    events = []
    for row in registry.db.execute(
        "SELECT evidence_id,page,text FROM passages WHERE document_id=? AND section='document' "
        "ORDER BY page,evidence_id LIMIT 512",
        (document,),
    ):
        # sqlite3.Row membership tests values, so inspect its column names.
        if "page" not in row.keys() or row["page"] is None:  # noqa: SIM118
            continue
        for match in SECTION.finditer(row["text"]):
            if "..." in match["title"]:
                continue
            end = match.end()
            # NASA report titles may wrap over several printed lines. Keep
            # those exact lines, ending before prose or the next section key.
            for continuation in row["text"][end:].splitlines(keepends=True):
                if not continuation.strip():
                    if continuation.strip("\r\n") == "" and end == match.end():
                        end += len(continuation)
                        continue
                    break
                words = re.findall(r"[A-Za-z]+", continuation)
                if (
                    len(continuation) > 140
                    or re.search(r"[.!?;]", continuation)
                    or not words
                    or re.match(r"\s*\d", continuation)
                    or not all(
                        word[0].isupper()
                        or word
                        in {"of", "for", "and", "in", "the", "to", "with", "from", "by", "on", "at"}
                        for word in words
                    )
                ):
                    break
                end += len(continuation)
            events.append(
                {
                    "page": row["page"],
                    "offset": match.start(),
                    "key": match["key"],
                    "evidence_id": row["evidence_id"],
                    "text": row["text"][match.start() : end].rstrip(),
                    "title": row["text"][match.start() : end].strip()[len(match["key"]) :].strip(),
                    "tests": TEST.findall(match["title"]),
                    "page_text": row["text"],
                }
            )
    return events


def add_section_context(anchor, registry, cache):
    document = anchor.get("document_id")
    if not document or anchor.get("typed_fields"):
        return
    add_record_caption_context(anchor, registry)
    if document not in cache:
        if len(cache) >= 64:
            cache.pop(next(iter(cache)))
        cache[document] = section_index(registry, document)
    events = cache[document]
    if not events:
        return
    original_spans = [
        s
        for s in anchor.get("spans", [])
        if s.get("scope")
        not in {
            "section_heading",
            "source_record_heading",
            "source_local_name_definition",
            "source_subject_context",
        }
    ]
    selected = []
    scientific = []
    for span in original_spans:
        source = registry.resolve(span["evidence_id"]) or {}
        page = source.get("page")
        if page is None:
            continue
        page_text = next((event["page_text"] for event in events if event["page"] == page), None)
        offset = page_text.find(span["text"]) if page_text is not None else 0
        local = list(SECTION.finditer(span["text"]))
        if offset < 0 and not local:
            # A derived quotation's offsets are not offsets in its source page.
            # Without an exact location or printed section, keep scope unknown.
            continue
        preceding = [
            event
            for event in events
            if event["page"] < page or (event["page"] == page and event["offset"] <= max(offset, 0))
        ]
        keys = {match["key"] for match in local}
        if preceding and (not local or local[0].start() > 0):
            keys.add(preceding[-1]["key"])
        for key in sorted(keys):
            parents = [
                event
                for event in events
                if event["page"] <= page
                and event["tests"]
                and (key == event["key"] or key.startswith(event["key"] + "."))
            ]
            if parents:
                selected.append(
                    max(
                        parents,
                        key=lambda event: (len(event["key"]), event["page"], event["offset"]),
                    )
                )
            else:

                def ancestor(parent, current_key=key):
                    prefix = parent["key"]
                    if re.fullmatch(r"\d+\.0", prefix):
                        prefix = prefix[:-2]
                    return current_key == parent["key"] or current_key.startswith(prefix + ".")

                within = [
                    event
                    for event in events
                    if event["page"] < page
                    or (
                        event["page"] == page
                        and event["offset"] <= max(offset, 0) + len(span["text"])
                    )
                ]
                related = [
                    event
                    for event in within
                    if event["key"].split(".")[0].isdigit()
                    and int(event["key"].split(".")[0]) > 0
                    and ancestor(event)
                    and not event["tests"]
                ]
                for parent_key in sorted({event["key"] for event in related}):
                    scientific.append(
                        max(
                            (event for event in related if event["key"] == parent_key),
                            key=lambda event: (event["page"], event["offset"]),
                        )
                    )
    if not selected and not scientific:
        return
    labels = sorted({label for event in selected for label in event["tests"]})
    if labels:
        anchor["method_references"] = labels
    if scientific:
        anchor["scientific_sections"] = list(dict.fromkeys(event["text"] for event in scientific))
    for event in [*selected, *scientific]:
        span = {
            "evidence_id": event["evidence_id"],
            "text": event["text"],
            "scope": "section_heading",
        }
        if span not in anchor["spans"]:
            anchor["spans"] = [*anchor["spans"], span]


def registered_document_references(text, anchors, registry):
    """Mask only complete, registered document/version references for quantities."""
    pattern = re.compile(
        r"\bNASA(?:/|-)(?:TM|TP|CP|CR|SP|STD)[-–−/]\d[A-Za-z0-9/-]*"
        r"(?:\s+(?:(?:with|w/)\s*)?Change\s+\d+)?",
        re.IGNORECASE,
    )

    def canonical(value):
        return re.sub(r"\bwith\b|w/|[^a-z0-9]", "", value.casefold())

    metadata = getattr(registry, "source_metadata", None)
    known = set()
    for anchor in anchors:
        for span in anchor.get("spans", []):
            source = registry.resolve(span["evidence_id"]) or {}
            title = (metadata(span["evidence_id"]) or {}).get("title", "") if metadata else ""
            for match in pattern.finditer(title + "\n" + source.get("text", "")):
                known.add(canonical(match[0]))
    return pattern.sub(lambda match: " " if canonical(match[0]) in known else match[0], text)


def requested_method_passages(registry, documents, question, cache):
    """Navigate explicit original parent sections, including their page continuations.

    These are additional registered evidence candidates. A section identity routes
    content; it never certifies the model's scientific statements.
    """
    requested = set(TEST.findall(question))
    if not requested or not getattr(registry, "db", None):
        return []
    found = []
    for document in sorted(documents):
        if document not in cache:
            cache[document] = section_index(registry, document)
        events = cache[document]
        parents = [event for event in events if requested & set(event["tests"])]
        if not parents:
            continue
        # A parent ends at the first heading outside its subtree. Repeated
        # section numbers in a later compliance matrix do not reopen it.
        ends = {}
        for parent in parents:
            following = [
                event
                for event in events
                if (event["page"], event["offset"]) > (parent["page"], parent["offset"])
                and not (
                    event["key"] == parent["key"] or event["key"].startswith(parent["key"] + ".")
                )
            ]
            ends[(parent["page"], parent["offset"])] = (
                (following[0]["page"], following[0]["offset"]) if following else (float("inf"), 0)
            )
        pages = registry.db.execute(
            "SELECT evidence_id,page,text FROM passages WHERE document_id=? AND section='document' ORDER BY page,evidence_id LIMIT 512",
            (document,),
        )
        for page in pages:
            if page["page"] is None:
                continue
            positions = [
                0,
                *[event["offset"] for event in events if event["page"] == page["page"]],
                len(page["text"]),
            ]
            intervals = []
            for start, end in zip(sorted(set(positions)), sorted(set(positions))[1:]):
                preceding = [
                    event
                    for event in events
                    if (event["page"], event["offset"]) <= (page["page"], start)
                ]
                if not preceding:
                    continue
                current = preceding[-1]
                matching = [
                    parent
                    for parent in parents
                    if (parent["page"], parent["offset"]) <= (page["page"], start)
                    and (page["page"], start) < ends[(parent["page"], parent["offset"])]
                    and (
                        current["key"] == parent["key"]
                        or current["key"].startswith(parent["key"] + ".")
                    )
                ]
                if matching:
                    intervals.append((start, end))
            if not intervals:
                continue
            # Merge adjacent child sections on a page so purpose, method and
            # qualifications reach generation together instead of heading-only hits.
            merged = []
            for start, end in intervals:
                if merged and merged[-1][1] == start:
                    merged[-1] = (merged[-1][0], end)
                else:
                    merged.append((start, end))
            for start, end in merged:
                text = page["text"][start:end]
                if not SECTION.sub("", text).strip() or len(text) > 10000:
                    continue
                found.append(
                    {
                        "document_id": document,
                        "evidence_id": page["evidence_id"],
                        "text": text,
                        "start": start,
                        "end": end,
                        "subsection_count": sum(
                            1
                            for event in events
                            if event["page"] == page["page"]
                            and start <= event["offset"] < end
                            and not event["tests"]
                        ),
                    }
                )
                if len(found) >= 24:
                    return found
    return found
