"""Resolve explicit original record labels before interpreting experimental numbers.

Uses source adapter identifier headers and registered payloads, never question/answer
lists. An ambiguous source label retains every matching source record.
"""

import re


def mask_deictic_references(text):
    """Ordinary reference modifiers are not uppercase investigation acronyms."""
    pattern = (
        r"\b(?:the|this|that|these|those)\s+(same|previous|former|latter|aforementioned)(?![\w-])"
    )
    result = text
    for match in reversed(list(re.finditer(pattern, text, re.IGNORECASE))):
        if match[1].isupper():
            continue
        start, end = match.span(1)
        result = result[:start] + " " * (end - start) + result[end:]
    return result


def calendar_mentions(text, *, retain_invalid=False):
    """Parse complete, unambiguous calendar dates; never decode run counters."""
    from datetime import date

    names = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    months = {label: i for i, name in enumerate(names, 1) for label in (name, name[:3])}
    months["sept"] = 9
    month = "(?:" + "|".join(sorted(months, key=len, reverse=True)) + ")"
    patterns = [
        (rf"(?<!\w)(\d{{1,2}})\s+({month})[.]?[,]?\s+(\d{{4}})(?!\w)", (3, 2, 1)),
        (rf"(?<!\w)({month})[.]?\s+(\d{{1,2}})[,]?\s+(\d{{4}})(?!\w)", (3, 1, 2)),
        (rf"(?<!\w)(\d{{4}})[-/]({month}|\d{{1,2}})[-/](\d{{1,2}})(?!\w)", (1, 2, 3)),
    ]
    found = []
    for pattern, (yi, mi, di) in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match[mi].lower()
            try:
                parsed = date(
                    int(match[yi]), months[value] if value in months else int(value), int(match[di])
                )
            except ValueError:
                if retain_invalid:
                    found.append((None, match))
                continue
            found.append((parsed, match))
    return found


def source_calendar_date(subject, store):
    """Read only the already-curated year/month/day properties from one record."""
    from datetime import date

    components = []
    for pid in ("source:date_year", "source:date_month", "source:date_date"):
        records = store.value_records(subject, pid) if pid in store.registry.properties else []
        values = {str(record["value"].reported_value).strip() for record in records}
        if len(values) != 1:
            return None
        components.append(next(iter(values)))
    year, month, day = components
    # Calendar spellings are ordinary English normalization, not experiment data.
    if not month.isdigit():
        names = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        choices = {label: i for i, name in enumerate(names, 1) for label in (name, name[:3])}
        choices["sept"] = 9
        month = str(choices.get(month.lower().rstrip("."), ""))
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def investigation_scope_groups(text, mentions):
    """Keep coordinated investigation names together, retaining source positions."""
    longest = sorted(
        {
            (sid, start, end)
            for sid, start, end in mentions
            if not any(
                left <= start and right >= end and right - left > end - start
                for _, left, right in mentions
            )
        },
        key=lambda item: (item[1], item[2], item[0]),
    )
    groups = []
    for sid, start, end in longest:
        gap = text[groups[-1]["end"] : start] if groups else ""
        if groups and (
            start < groups[-1]["end"]
            or re.fullmatch(r"(?:\s|[,/&()]|\b(?:and|or|versus|vs)\b)+", gap, re.IGNORECASE)
        ):
            groups[-1]["ids"].add(sid)
            groups[-1]["end"] = max(end, groups[-1]["end"])
        else:
            groups.append({"ids": {sid}, "start": start, "end": end})
    return groups


def local_investigation_scope(text, groups, match):
    """Bind an explicit record to its own clause; preserve unresolved ambiguity."""
    separators = [
        m
        for m in re.finditer(
            r"[,;]|\b(?:and|or|vs|versus|with|against|whereas|while|to)\b", text, re.IGNORECASE
        )
        if not any(group["start"] <= m.start() and m.end() <= group["end"] for group in groups)
    ]
    left = max((m.end() for m in separators if m.end() <= match.start()), default=0)
    right = min((m.start() for m in separators if m.start() >= match.end()), default=len(text))
    local = [group for group in groups if left <= group["start"] and group["end"] <= right]
    if local:
        return set().union(*(group["ids"] for group in local))
    # A list of record labels may continue the preceding named scope until a
    # later clause explicitly introduces another investigation.
    previous = [group for group in groups if group["end"] <= match.start()]
    return previous[-1]["ids"] if previous else set()


def resolve_record_mentions(query, store, root):
    from nasa_fire_ai.ingestion.hackathon import TABLES
    from nasa_fire_ai.ingestion.psi_scientific import mappings
    from nasa_fire_ai.query.numeric_mentions import UNIT

    identifiers = {key.lower(): value[0] for key, value in TABLES.items()}
    identifiers.update(
        {key.lower(): p["identifier"] for key, p in mappings(root).items() if p.get("identifier")}
    )
    secondary = {
        key.lower(): [
            (header, field["property"])
            for header, field in profile["fields"].items()
            if field.get("role") == "original_record_identifier"
        ]
        for key, profile in mappings(root).items()
    }
    # Original identifier column names may themselves contain an investigation
    # abbreviation. Mask those labels before resolving investigation scope.
    scope_query = query
    for header in sorted(
        set(identifiers.values()) | {h for fields in secondary.values() for h, _ in fields},
        key=len,
        reverse=True,
    ):
        scope_query = re.sub(
            r"\b" + re.escape(header) + r"\s*#?\s*[A-Za-z0-9-]+",
            lambda match: " " * len(match[0]),
            scope_query,
            flags=re.IGNORECASE,
        )
    scope_query = mask_deictic_references(scope_query)
    mentions = []
    for investigation in sorted(set(identifiers) | {key.lower() for key in mappings(root)}):
        aliases = store.registry.entity_mentions.get(investigation, {}).get("aliases", [])
        for alias in [investigation, *aliases]:
            if alias:
                mentions.extend(
                    (investigation, match.start(), match.end())
                    for match in re.finditer(
                        r"(?<!\w)" + re.escape(alias) + r"(?!\w)", scope_query, re.IGNORECASE
                    )
                )
    scope_groups = investigation_scope_groups(scope_query, mentions)
    named_investigations = (
        set().union(*(group["ids"] for group in scope_groups)) if scope_groups else set()
    )

    # A numbered procedure inside a normative document namespace is not an
    # experimental record with a coincident numeric label. Mixed questions keep
    # the nearest explicit investigation and document contexts separate.
    document_mentions = list(
        re.finditer(
            r"\b(?:[A-Z]+[-/]STD[-/]\d[A-Za-z0-9/-]*|ASTM\s+[A-Z]?\s*\d+|ISO\s+\d+)",
            query,
            re.IGNORECASE,
        )
    )
    procedure_spans = []
    normative = bool(
        re.search(
            r"\b(?:standards?|requirements?|criteria|criterion|procedures?)\b", query, re.IGNORECASE
        )
    )
    for method in re.finditer(r"\bTest\s*#?\s*\d+\b", query, re.IGNORECASE):
        gap = lambda left, right: max(left[0] - right[1], right[0] - left[1], 0)
        document_gap = min(
            (gap(method.span(), item.span()) for item in document_mentions), default=float("inf")
        )
        investigation_gap = min(
            (gap(method.span(), (left, right)) for _, left, right in mentions), default=float("inf")
        )
        if document_gap < investigation_gap or (
            not named_investigations and (document_mentions or normative)
        ):
            procedure_spans.append(method.span())

    def procedure_number(match):
        return match is not None and any(
            left < match.end() and match.start() < right for left, right in procedure_spans
        )

    def bound_to(investigation, match):
        if len(named_investigations) < 2:
            return True
        local = local_investigation_scope(query, scope_groups, match)
        return not local or investigation in local

    candidates, descriptions = [], []
    date_spans = calendar_mentions(query, retain_invalid=True)
    dates = [(value, match) for value, match in date_spans if value is not None]
    query_words = set(re.findall(r"[a-z]{4,}", query.lower()))
    generic = {
        "fuel",
        "sample",
        "material",
        "bottle",
        "type",
        "test",
        "normal",
        "based",
        "blend",
        "mixture",
    }
    for subject in store.entities():
        payload = store.payload(subject)
        label = str(payload.get("reported_identifier") or "").strip()
        description = str(payload.get("reported_material_description") or "")
        if not label and not description and not dates:
            continue
        investigations = store.relations(subject, "belongsToInvestigation")
        for investigation in investigations:
            if named_investigations and investigation not in named_investigations:
                continue
            # Literal component names in a source-scoped description identify
            # candidate records, never pure-material identity or equivalence.
            if investigation in named_investigations:
                shared = set(re.findall(r"[a-z]{4,}", description.lower())) & query_words - generic
                if len(shared) >= 2:
                    descriptions.append(subject)
            if dates and investigation in named_investigations:
                calendar_date = source_calendar_date(subject, store)
                if calendar_date is None and identifiers.get(investigation) == "Test Date":
                    printed = calendar_mentions(label)
                    calendar_date = printed[0][0] if len(printed) == 1 else None
                for wanted_date, match in dates:
                    if calendar_date == wanted_date and bound_to(investigation, match):
                        candidates.append((subject, match))
            if not label:
                continue
            secondary_match = None
            for field_header, pid in secondary.get(investigation, []):
                for value in store.value_records(subject, pid):
                    raw = str(value["value"].reported_value).strip()
                    aliases = [field_header, *store.registry.properties[pid].aliases]
                    for alias in aliases:
                        match = re.search(
                            r"(?<!\w)"
                            + re.escape(alias)
                            + r"\s*#?\s*"
                            + re.escape(raw)
                            + r"(?!\w|\.(?=\w))",
                            query,
                            re.IGNORECASE,
                        )
                        if match:
                            secondary_match = match
                            break
            header = identifiers.get(investigation)
            # Accept explicit original field labels and ordinary record-reference grammar.
            prefix = (
                rf"(?:{re.escape(header)}|records?|runs?|tests?|samples?|sessions?)"
                if header
                else r"(?:records?|runs?|tests?|samples?|sessions?)"
            )
            explicit = re.search(
                rf"\b{prefix}\s*\#?\s*{re.escape(label)}(?!\w|\.(?=\w))", query, re.IGNORECASE
            )
            postposed = re.search(
                rf"(?<![\w.]){re.escape(label)}\s+(?:records?|runs?|tests?|samples?|sessions?|entries)\b",
                query,
                re.IGNORECASE,
            )
            explicit = explicit or postposed
            named = investigation in named_investigations
            bare = re.search(
                r"(?<![\w.])" + re.escape(label) + r"(?!\w|\.(?=\w))", query, re.IGNORECASE
            )
            if bare and any(match.start() <= bare.start() < match.end() for _, match in date_spans):
                bare = None
            if explicit and any(
                match.start() <= explicit.end() - len(label) < match.end()
                for _, match in date_spans
            ):
                explicit = None
            if (
                bare
                and re.fullmatch(r"[-+]?\d+(?:[.-]\d+)*", label)
                and re.match(r"\s*(?:" + UNIT + r")", query[bare.end() :], re.IGNORECASE)
            ):
                bare = None
            if procedure_number(secondary_match):
                secondary_match = None
            if procedure_number(explicit):
                explicit = None
            if procedure_number(bare):
                bare = None
            if secondary_match or explicit or (named and bare):
                match = secondary_match or explicit or bare
                if bound_to(investigation, match):
                    candidates.append((subject, match))
    if not candidates:
        return sorted(set(descriptions)), query
    masked = query
    for _, match in sorted(candidates, key=lambda row: row[1].start(), reverse=True):
        masked = (
            masked[: match.start()] + " " * (match.end() - match.start()) + masked[match.end() :]
        )
    return sorted({subject for subject, _ in candidates}), masked
