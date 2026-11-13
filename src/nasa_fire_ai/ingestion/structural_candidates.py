"""Structural candidates recovered from the printed structure of a document."""

import re

from nasa_fire_ai.ingestion.abbreviations import segmentation_view
from nasa_fire_ai.ingestion.clause_cues import setting_mention
from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.printed_layout import (
    _page_texts,
    acronym_printed_form,
    is_caption_line,
    section_for_span,
)
from nasa_fire_ai.ingestion.scientific_scope import (
    NON_RESEARCH_SECTION,
    subject_label_names_material,
)
from nasa_fire_ai.ingestion.source_spans import mentions, normalized
from nasa_fire_ai.ingestion.subject_recognition import material_tested_here


def recover_group_classes(output, document):
    """A printed "<material> (qualifier)" group proposed as a Material is a group of it.

    "Copper-filled resin (Lot #2)" printed as a table row group, beside a
    proposed "Copper-filled resin" material, names a lot of that material, not
    another substance; it is revalidated as a Sample, with its provenance.
    Returns the output (copied when changed) and {entity key: recovery}.
    """
    from nasa_fire_ai.ingestion.table_continuity import label_variants, row_group_identity

    materials = [e["label"] for e in output["entities"] if e["class_id"] == "Material"]
    recovered = {}
    entities = []
    for e in output["entities"]:
        if (
            e["class_id"] == "Material"
            and row_group_identity(e["label"], document)
            and any(
                subject_label_names_material(form, m) and normalized(form) != normalized(m)
                for form in label_variants(e["label"], document)
                for m in materials
            )
        ):
            recovered[e["key"]] = {
                "proposed_class_id": "Material",
                "recovered_class_id": "Sample",
                "basis": "PRINTED_ROW_GROUP_NAMES_A_GROUP_OF_A_PROPOSED_MATERIAL",
            }
            e = {**e, "class_id": "Sample"}
        entities.append(e)
    from nasa_fire_ai.ingestion.table_continuity import printed_in_material_column

    material_names = {
        normalized(other["label"])
        for other in output["entities"]
        if other["class_id"] == "Material"
    }
    for index, e in enumerate(entities):
        if (
            e["key"] not in recovered
            and (
                (
                    e["class_id"] == "ExperimentFamily"
                    and printed_in_material_column(e["label"], document)
                )
                # A "sample" named exactly as a material, with no qualifier, is
                # that material ("Copper-filled resin", "Fluoron® B").
                or (
                    e["class_id"] == "Sample"
                    and (
                        printed_in_material_column(e["label"], document)
                        or normalized(e["label"]) in material_names
                    )
                )
            )
            # "Alpha (Batch #1)" names a group of Alpha, not another substance.
            and not any(
                subject_label_names_material(form, other["label"])
                and normalized(form) != normalized(other["label"])
                for form in label_variants(e["label"], document)
                for other in output["entities"]
            )
        ):
            # "TFX-Quartex® (QX)" printed in a table's Material column is the
            # substance tested, not a family of experiments.
            recovered[e["key"]] = {
                "proposed_class_id": e["class_id"],
                "recovered_class_id": "Material",
                "basis": "PRINTED_MATERIAL_COLUMN_NAMES_A_MATERIAL"
                if printed_in_material_column(e["label"], document)
                else "SAMPLE_NAMED_EXACTLY_AS_A_PROPOSED_MATERIAL",
            }
            entities[index] = {**e, "class_id": "Material"}
    # "Forty Wet Cold Drop Tests", "First ... Drop Test Series": a printed
    # name of several tests is a group of runs, whatever class the model proposed;
    # it is revalidated as an ExperimentFamily under its printed name.
    printed = " ".join(s.get("text", "") for s in document.get("segments", []))
    for index, e in enumerate(entities):
        if (
            e["key"] not in recovered
            and e["class_id"] == "ExperimentalRun"
            and SERIES_NAME.search(e["label"])
            and mentions(e["label"], printed)
        ):
            recovered[e["key"]] = {
                "proposed_class_id": "ExperimentalRun",
                "recovered_class_id": "ExperimentFamily",
                "basis": "PRINTED_NAME_OF_SEVERAL_TESTS_IS_A_GROUP",
            }
            entities[index] = {**e, "class_id": "ExperimentFamily"}
    if not recovered:
        return output, {}
    return {**output, "entities": entities}, recovered


# The printed plural of a test unit names a series, never one run ("Run 3", "Test A").
SERIES_NAME = re.compile(
    r"\b(?:tests|test\s+series|impact\s+series|series|runs|trials|experiments)\b", re.IGNORECASE
)


def structure_entity_candidates(output, package, document):
    """Entities the printed source itself names, for the same validator.

    "<material> samples" printed in the text, for a current material this
    document's own tables show tested here, is that material's specimen
    collection; the cells of a "... Condition(s)" column in this study's rows of
    a group already proposed are its conditions. Candidates are never facts.
    """
    from nasa_fire_ai.ingestion.table_continuity import (
        _key,
        label_variants,
        reference_authors,
        row_lineage,
        table_rows,
    )

    known = {(normalized(e["label"]), e["class_id"]) for e in output["entities"]}
    candidates = []

    def add(label, class_id, evidence_id, start, quote):
        if (normalized(label), class_id) in known:
            return
        known.add((normalized(label), class_id))
        candidates.append(
            {
                "key": "structure-" + identity([label, class_id, evidence_id, start])[:16],
                "label": label,
                "class_id": class_id,
                "study": "current",
                "support": [{"evidence_id": evidence_id, "quote": quote, "start": start}],
            }
        )

    for material in output["entities"]:
        if (
            material["class_id"] != "Material"
            or material["study"] != "current"
            or not material_tested_here(material["label"], document)
        ):
            continue
        name = r"\s+".join(re.escape(w) for w in material["label"].split())
        for e in package["evidence"]:
            m = re.search(rf"(?<![\w-])({name})\s+(samples|specimens)\b", e["text"], re.IGNORECASE)
            if m:
                view = segmentation_view(e["text"])
                begin = max([0] + [x.end() for x in re.finditer(r"[.!?]\s", view[: m.start()])])
                end = re.search(r"[.!?](?=\s|$)", view[m.end() :])
                stop = m.end() + end.end() if end else len(e["text"])
                sentence = e["text"][begin:stop]
                lead = len(sentence) - len(sentence.lstrip())
                add(m.group(), "Sample", e["evidence_id"], begin + lead, sentence.strip())
                break
    # "Custom flame-proof tabs stitched onto inner liner cloth burned at 29%
    # O2 and 61 kPa": a thing the source itself prints as tested at settings
    # is a specimen of this study when no proposed subject names it. The name
    # is its printed line, with the line before it when the line continues it.
    # A proposed specimen or group named by part of the line is the same thing;
    # so is a material that heads the line ("Alpha seals" are Alpha's). A material
    # printed later in the line ("... stitched onto inner liner cloth") is only a
    # constituent and never hides the specimen the line names.
    subjects = [
        e["label"] for e in output["entities"] if e["class_id"] in {"Sample", "ExperimentFamily"}
    ]
    materials = [e["label"] for e in output["entities"] if e["class_id"] == "Material"]
    for e in package["evidence"]:
        text = e["text"]
        for m in re.finditer(
            r"(?<![\w-])(?:(?:was|were|are|is)\s+)?tested\s+at\s+(?=[~≈]?\d)",
            text,
            re.IGNORECASE,
        ):
            before = text[: m.start()]
            cut = max([0] + [x.end() for x in re.finditer(r"[.;:!?•]|\n\s*\n", before)])
            lines = [ln.strip() for ln in before[cut:].split("\n") if ln.strip()]
            if not lines:
                continue
            name = lines[-1]
            if len(lines) > 1 and re.match(r"(?:[a-z]|\d)", name):
                name = lines[-2] + " " + name
            name = re.sub(r"^\W+", "", name)
            words = name.split()
            if (
                len(words) < 2
                or len(name) > 120
                or re.match(
                    r"(?:the|an?|each|all|these|those|this|both|some|several|most|many"
                    r"|every|our|their|its|it|they|which|that|and|or)\b",
                    name,
                    re.IGNORECASE,
                )
                or not re.match(r"[A-Za-z0-9]", name)
                or any(mentions(s, name) or mentions(name, s) for s in subjects)
                or any(
                    mentions(form, m)
                    or re.match(re.escape(normalized(m)) + r"(?![\w-])", normalized(form))
                    # The printed line itself, before a continued line is joined:
                    # "100% aramid weave cloth coupons" under a bullet "Flame-proof
                    # tabs" is headed by the material, so it names no new specimen.
                    for form in (name, re.sub(r"^\W+", "", lines[-1]))
                    for m in materials
                )
            ):
                continue
            start = before.rfind(lines[-1] if len(words) == len(lines[-1].split()) else lines[-2])
            quote = text[start : m.end() + 60]
            add(name, "Sample", e["evidence_id"], start, quote.strip())
            subjects.append(name)
    authors = reference_authors(document)
    pages = {e["page"]: e for e in package["evidence"]}
    tested = [
        m["label"]
        for m in output["entities"]
        if m["class_id"] == "Material"
        and m["study"] == "current"
        and material_tested_here(m["label"], document)
    ]
    for row in table_rows(document):
        # "Copper-filled resin (Lot #2)" printed as a current row group of a
        # material tested here names a group of its specimens.
        label = row["group_label"]
        if not label or row_lineage(row, authors):
            continue
        named = [
            m
            for m in tested
            if (q := subject_label_names_material(label, m))
            and normalized(label) != normalized(m)
            and "(" in label
            and q["qualifier"]
        ]
        page = pages.get(row["page"])
        printed = row["group_label_original"] or label
        position = page["text"].find(printed) if page and named else -1
        # A group the model already named as a group keeps its own record.
        if position >= 0 and not any(
            e["class_id"] in {"Sample", "ExperimentFamily"} and _key(v) == _key(label)
            for e in output["entities"] + candidates
            for v in label_variants(e["label"], document)
        ):
            add(re.sub(r"\s+", " ", label), "Sample", page["evidence_id"], position, printed)
        elif (
            not named
            and page
            and row["cells"]
            and re.search(r"\bmaterials?\b", row["cells"][0].get("header") or "", re.IGNORECASE)
            and not any(
                _key(v) == _key(label) and e.get("study") == "current"
                for e in output["entities"] + candidates
                for v in label_variants(e["label"], document)
            )
            and not re.match(
                r"(?:phase|step|stage|part|section|table|figure|test|option)\b",
                label,
                re.IGNORECASE,
            )
            # A data row: its own cells print measured or set values.
            and any(re.search(r"\d", c.get("original_value") or "") for c in row["cells"][1:])
            and (position := page["text"].find(printed)) >= 0
        ):
            # A name this study's own rows print in a Material column is a
            # material tested here ("aAlgoflon® E2" under "Material"), even when
            # the model proposed it as cited work.
            known.discard((normalized(re.sub(r"\s+", " ", label)), "Material"))
            add(re.sub(r"\s+", " ", label), "Material", page["evidence_id"], position, printed)
    # "Figure 6 - Manifold Pressures Across the Opening Damp Drop Test
    # Series (~90 msec ...)": a caption that prints the data as taken during a
    # named series of tests names that group of this study's experiments. A
    # caption that cites its source ("excerpted from (3)", "[2]", "et al.")
    # names another study's work. A group already proposed keeps its record,
    # unless captions print two or more series that its name only shares in
    # ("First ... Test Series", "second ... Test Series"): those are distinct.
    series = []
    for e in package["evidence"]:
        lines = e["text"].split("\n")
        for index, line in enumerate(lines):
            if not is_caption_line(line):
                continue
            # A caption wrapped onto its next line, unless that line opens another.
            following = lines[index + 1] if index + 1 < len(lines) else ""
            caption = line
            if following.strip() and not is_caption_line(following):
                caption = line + "\n" + following
            if re.search(
                r"\b(?:from|after|courtesy\s+of)\s*[\[(]\d|\[\d+\]|\(\d+\)|\bet\s+al\b",
                caption,
                re.IGNORECASE,
            ):
                continue
            m = re.search(
                r"\bDuring\s+(?:the\s+)?((?:[\w#&/-]+\s+){1,9}?(?:Test\s+Series|Series|Tests|Runs))\b",
                caption,
                re.IGNORECASE,
            )
            if not m or len(m.group(1).split()) < 3:
                continue
            at = e["text"].find(caption)
            series.append(
                (
                    re.sub(r"\s+", " ", m.group(1)),
                    e["evidence_id"],
                    at + len(caption) - len(caption.lstrip()),
                    caption.strip(),
                )
            )
    for label, evidence_id, start, quote in series:
        if any(mentions(label, s) for s in subjects) or any(
            mentions(s, label) and sum(mentions(s, other[0]) for other in series) < 2
            for s in subjects
        ):
            continue
        add(label, "ExperimentFamily", evidence_id, start, quote)
        subjects.append(label)
    groups = {
        _key(v)
        for g in output["entities"] + candidates
        if g["class_id"] in {"Sample", "ExperimentFamily"} and g["study"] == "current"
        for v in label_variants(g["label"], document)
    }
    for row in table_rows(document):
        if _key(row["group_label"]) not in groups or row_lineage(row, authors):
            continue
        for cell in row["cells"][1:]:
            text = (cell["original_value"] or "").strip()
            if not text or not re.search(r"\bconditions?\b", cell["header"] or "", re.IGNORECASE):
                continue
            page = pages.get(row["page"])
            position = page["text"].find(text) if page else -1
            if position >= 0:
                add(text, "ExperimentalCondition", page["evidence_id"], position, text)
    return candidates


def structure_quantity_candidates(output, package, document):
    """Quantities the printed structure itself names, for the same validator.

    A value applied in a test step ("It was struck with 60 J") that one
    subject's own table rows print under a column is proposed with that column's
    name for each nearby current subject; a standard-deviation column of a
    subject's current rows is proposed as a derived dispersion statistic. The
    validator decides subject, name and role exactly as for model proposals.
    """
    from nasa_fire_ai.ingestion.statement_integrity import APPLIED_STEP, OUTCOME_CUE
    from nasa_fire_ai.ingestion.table_continuity import (
        _key,
        label_variants,
        material_row_labels,
        reference_authors,
        row_lineage,
        subject_columns_printing,
        table_rows,
    )
    from nasa_fire_ai.normalization.units import interpret

    subjects = [
        e
        for e in output["entities"]
        if e["study"] == "current"
        and (
            e["class_id"] in {"Sample", "ExperimentFamily"}
            or (e["class_id"] == "Material" and material_tested_here(e["label"], document))
        )
    ]

    def rows_of(e):
        return (
            material_row_labels(e["label"], document)
            if e["class_id"] == "Material"
            else label_variants(e["label"], document)
        )

    # Only candidates are deduplicated here; a model proposal of the same value
    # may be rejected, and validated duplicates are consolidated afterwards.
    proposed = set()
    candidates = []
    value = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*([A-Za-z°%][\w°%/-]*)")
    for e in package["evidence"]:
        text = e["text"]
        starts = [0] + [m.end() for m in re.finditer(r"[.!?](?=\s)", segmentation_view(text))]
        for begin, end in zip(starts, starts[1:] + [len(text)]):
            sentence = text[begin:end]
            steps = list(APPLIED_STEP.finditer(sentence))
            if not steps:
                continue
            context = starts[starts.index(begin) - 1] if starts.index(begin) > 0 else begin
            if re.search(r"\n\s*\n", text[context:begin]):
                context = begin  # never across a paragraph break
            previous = text[context:begin]
            for m in value.finditer(sentence, steps[0].end()):
                if OUTCOME_CUE.search(sentence[steps[0].end() : m.start()]) or not interpret(m[2]):
                    continue
                for subject in subjects:
                    if not (
                        mentions(subject["label"], sentence) or mentions(subject["label"], previous)
                    ):
                        continue
                    if (subject["key"], m[1], m[2]) in proposed:
                        continue
                    for name in subject_columns_printing(rows_of(subject), m[1], m[2], document):
                        proposed.add((subject["key"], m[1], m[2]))
                        candidates.append(
                            {
                                "subject": subject["key"],
                                "label": name,
                                "expression": m[1],
                                "unit": m[2],
                                "epistemic": "experimental_configuration",
                                "support": [
                                    {
                                        "evidence_id": e["evidence_id"],
                                        "quote": text[context:end].strip(),
                                        "start": context
                                        + len(text[context:end])
                                        - len(text[context:end].lstrip()),
                                    }
                                ],
                            }
                        )
    authors = reference_authors(document)
    pages = {e["page"]: e for e in package["evidence"]}
    for subject in subjects:
        keys = {_key(v) for v in rows_of(subject)}
        for row in table_rows(document):
            if _key(row["group_label"]) not in keys or row_lineage(row, authors):
                continue
            own_row = _key(row["group_label"]) in {
                _key(v) for v in label_variants(subject["label"], document)
            }
            for cell in row["cells"][1:]:
                header = re.sub(r"\s+", " ", cell["header"] or "").strip()
                unit = re.search(r"\(([^()]*)\)\s*$", header)
                number = (cell["original_value"] or "").strip()
                if re.search(r"\bstandard\s+deviations?\b", header, re.IGNORECASE):
                    epistemic = "derived_quantity"
                elif (
                    # A current row's own measured or set value under a column
                    # whose header prints its unit ("Peak Temp (°C)", "Hold
                    # Load (kN)"): the validator decides subject and role.
                    own_row and unit and re.fullmatch(r"[<>≤≥]?\s*\d[\d,]*(?:\.\d+)?", number)
                ):
                    epistemic = (
                        "experimental_configuration"
                        # A set-up value or a specimen's own dimension is how the
                        # test was configured; anything else is read as reported.
                        if re.search(
                            r"\b(?:initial|set|nominal|applied|thickness|diameter|length|width"
                            r"|mass|weight|size)\b",
                            header,
                            re.IGNORECASE,
                        )
                        else "reported_quantity"
                    )
                else:
                    continue
                page = pages.get(row["page"])
                position = page["text"].find(number) if page and number else -1
                if position < 0 or (subject["key"], number, unit and unit[1]) in proposed:
                    continue
                proposed.add((subject["key"], number, unit and unit[1]))
                candidates.append(
                    {
                        "subject": subject["key"],
                        "label": re.sub(r"\s*\([^()]*\)\s*$", "", header).strip(),
                        "expression": number,
                        "unit": unit[1] if unit else None,
                        "epistemic": epistemic,
                        "support": [
                            {"evidence_id": page["evidence_id"], "quote": number, "start": position}
                        ],
                    }
                )
    # "100% aramid weave cloth coupons burned at 29% O2 and 61 kPa": the settings
    # a subject is printed as tested at are its configuration, named by an
    # approved property the printed unit or species establishes.
    texts = _page_texts(document)
    for subject in subjects:
        for evidence_id, start, clause in tested_at_clauses(subject["label"], texts):
            for m in value.finditer(clause):
                meaning = interpret(m[2]) or {}
                if re.match(r"\s*(?:O2|O₂|oxygen)\b", clause[m.end() :]):
                    label = "O2"
                elif meaning.get("dimension") in {"pressure", "temperature"}:
                    label = meaning["dimension"]
                else:
                    continue
                if (subject["key"], m[1], m[2]) in proposed:
                    continue
                proposed.add((subject["key"], m[1], m[2]))
                candidates.append(
                    {
                        "subject": subject["key"],
                        "label": label,
                        "expression": m[1],
                        "unit": m[2],
                        "epistemic": "experimental_configuration",
                        "support": [
                            {
                                "evidence_id": evidence_id,
                                "quote": texts[evidence_id][start : start + 240].strip(),
                                "start": start,
                            }
                        ],
                    }
                )
    candidates.extend(group_subsection_quantity_candidates(output, document, proposed))
    return candidates


DIMENSION_NOUN = (
    r"(?:diameter|I\.?D\.?|O\.?D\.?|length|width|height|thickness|depth|radius|volume|area"
    r"|velocity|speed|flow(?:\s+rate)?|pressure|temperature|duration|time|rate|mass|weight"
    r"|concentration)"
)
GROUP_VALUE = re.compile(r"(?<![\w.])([~≈]?\d[\d,]*(?:\.\d+)?)\s*([A-Za-z°µμ%][\w°/³²µμ%-]*)")


METHOD_SECTION = re.compile(
    r"\b(?:experimental|methods?|methodology|procedures?|apparatus|set-?up|configuration"
    r"|facilit(?:y|ies)|test\s+(?:description|hardware|article|cell|rig))\b",
    re.IGNORECASE,
)


def heading_regions(output, document):
    """The text under each printed heading, with the subject the heading names.

    A heading that names a group proposed as this study's own ExperimentFamily
    owns its subsection ("B. Delta Test Center (DTC) Reduced Load
    Trials"). A heading in the paper's own method or test-configuration section
    that names no group describes the investigation itself ("Experimental
    Method", "V. Test Configuration"), when the document proposes exactly one
    current investigation. Yields (subject, in_results, evidence_id, begin,
    stop) per page text; a sentence outside every region has no subject here.
    """
    groups = {
        normalized(e["label"]): e
        for e in output["entities"]
        if e["class_id"] == "ExperimentFamily" and e.get("study") == "current"
    }
    investigations = [
        e
        for e in output["entities"]
        if e["class_id"] == "Investigation" and e.get("study") == "current"
    ]
    investigation = investigations[0] if len(investigations) == 1 else None
    order = {seg["evidence_id"]: i for i, seg in enumerate(document.get("segments", []))}
    texts = _page_texts(document)
    headings = sorted(
        (h for h in document.get("sections", []) if h["evidence_id"] in order),
        key=lambda h: (order[h["evidence_id"]], h["start"]),
    )
    for index, heading in enumerate(headings):
        title = re.sub(
            r"^(?:#+\s*|(?:[A-Z]|\d+(?:\.\d+)*|[IVXLCDM]+)[.)]\s+)", "", heading["title"]
        )
        section = section_for_span(heading, document)
        subject = groups.get(normalized(title))
        if not subject:
            # The method section's own text, outside any group's subsection,
            # configures the one investigation; results and prior work do not.
            if (
                not investigation
                or not (METHOD_SECTION.search(title) or METHOD_SECTION.search(section))
                or NON_RESEARCH_SECTION.search(title)
                or NON_RESEARCH_SECTION.search(section)
                or re.search(r"\b(?:results?|discussion|conclusions?)\b", section, re.IGNORECASE)
            ):
                continue
            subject = investigation
        end = headings[index + 1] if index + 1 < len(headings) else None
        results = bool(re.search(r"\bresults?\b", section, re.IGNORECASE))
        for evidence_id, text in texts.items():
            position = order.get(evidence_id, -1)
            if position < order[heading["evidence_id"]] or (
                end and position > order[end["evidence_id"]]
            ):
                continue
            begin = (
                heading["start"] + len(heading["title"])
                if evidence_id == heading["evidence_id"]
                else 0
            )
            stop = end["start"] if end and evidence_id == end["evidence_id"] else len(text)
            if stop > begin:
                yield subject, results, evidence_id, begin, stop


def group_subsection_quantity_candidates(output, document, proposed):
    """Values the paper prints inside a group's own subsection, named by its syntax.

    "B. Delta Test Center (DTC) Reduced Load Trials ... The vessel
    is 0.41 m3 in volume with an I.D. of 64.5 cm": the subsection heading names the
    group; the printed syntax names each value ("an I.D. of 64.5 cm", "0.41 m3 in
    volume", "a 3.6 mm OD quartz pin"). The method section's own text names the
    investigation's configuration the same way ("tests at the planned cabin
    setpoint of 61.0 kPa"). Candidates only: the validator decides name, role
    and scope exactly as for model proposals.
    """
    from nasa_fire_ai.normalization.units import interpret

    texts = _page_texts(document)
    out = []
    for group, results, evidence_id, begin, stop in heading_regions(output, document):
        text = texts[evidence_id]
        region = text[begin:stop]
        # A single capital before a period is an abbreviation ("I.D."), not an end.
        starts = [0] + [
            m.end() for m in re.finditer(r"(?<!\b[A-Z])[.!?](?=\s)", segmentation_view(region))
        ]
        for a, b in zip(starts, starts[1:] + [len(region)]):
            sentence = region[a:b]
            for m in GROUP_VALUE.finditer(sentence):
                if not interpret(m[2]):
                    continue
                before = sentence[: m.start()]
                after = sentence[m.end() :]
                name = None
                link = re.search(
                    r"(?:\b(?:an?|the)\s+)?(?P<name>[A-Za-z][\w.-]*(?:\s+[A-Za-z][\w.-]*){0,2})"
                    r"\s+(?:of|is|was|were)\s*[~≈]?\s*$",
                    before,
                )
                if link and re.search(DIMENSION_NOUN + r"$", link["name"], re.IGNORECASE):
                    # "with a bore of 12.5 cm": the name without its lead-in words.
                    name = re.sub(
                        r"^(?:(?:with|and|a|an|the|its|their|whose)\s+)+",
                        "",
                        link["name"],
                        flags=re.IGNORECASE,
                    )
                # "a sliding 3.6 mm OD quartz pin": the dimension and the
                # thing it measures; a bare "BD by 20 cm ..." names no thing.
                modifier = re.match(
                    r"\s+(?P<name>(?:[A-Za-z-]+\s+){0,1}?"
                    + DIMENSION_NOUN
                    + r"(?:\s+(?!by\b|and\b|of\b|at\b|in\b|to\b|was\b|were\b|on\b|the\b|an?\b"
                    + r"|for\b|with\b|from\b|that\b|which\b|is\b|are\b|per\b|or\b|under\b"
                    + r"|during\b|over\b|than\b|as\b|before\b|after\b)[a-z][a-z-]+){0,2})\b",
                    after,
                    re.IGNORECASE,
                )
                if (
                    not name
                    and modifier
                    and not re.fullmatch(r"(?:I\.?D\.?|O\.?D\.?)", modifier["name"].strip())
                    and re.search(r"\b(?:an?|the)\s+(?:[A-Za-z-]+\s+)?$", before, re.IGNORECASE)
                ):
                    name = modifier["name"]
                inside = re.match(
                    r"\s+in\s+(?P<name>" + DIMENSION_NOUN + r")\b", after, re.IGNORECASE
                )
                if not name and inside:
                    name = inside["name"]
                if not name:
                    continue
                key = (group["key"], m[1], m[2])
                if key in proposed:
                    continue
                proposed.add(key)
                lead = len(sentence) - len(sentence.lstrip())
                out.append(
                    {
                        "subject": group["key"],
                        "label": re.sub(r"\s+", " ", name).strip(),
                        "expression": m[1],
                        "unit": m[2],
                        "epistemic": "reported_quantity"
                        if results
                        else "experimental_configuration",
                        "support": [
                            {
                                "evidence_id": evidence_id,
                                "quote": sentence.strip(),
                                "start": begin + a + lead,
                            }
                        ],
                    }
                )
    return out


def structure_relation_candidates(output, document):
    """Relations the printed structure itself proposes, for the same validator.

    A group printed as "<material> (qualifier)" is made of that material; a
    group whose own table rows print a condition was tested under it. These are
    candidates, never facts: every one is validated like a model proposal.
    """
    from nasa_fire_ai.ingestion.table_continuity import group_rows_printing, label_variants

    groups = [e for e in output["entities"] if e["class_id"] in {"Sample", "ExperimentFamily"}]
    # A model proposal of the same relation does not replace the printed one:
    # the model's own support may not hold it, the printed structure does.
    proposed = set()
    candidates = []
    for group in groups:
        for other in output["entities"]:
            relation = None
            if other["class_id"] == "Material" and any(
                subject_label_names_material(form, other["label"])
                for form in label_variants(group["label"], document)
            ):
                relation = "madeOf"
            elif (
                other["class_id"] == "Investigation"
                and other["study"] == "current"
                and group["study"] == "current"
                and any(
                    re.search(
                        re.escape(normalized(group["label"]))
                        + r"\s+(?:discussed|described|tested|evaluated|studied)\s+in\s+this\s+(?:paper|study|report|work|investigation)\b",
                        normalized(s["quote"]),
                    )
                    for s in group["support"]
                )
            ):
                relation = "belongsToInvestigation"
            elif (
                other["class_id"] == "Investigation"
                and other["study"] == "current"
                and group["class_id"] == "Sample"
                and group["study"] == "current"
                and any(
                    re.search(
                        r"\b(?:tested|evaluated|examined)\s+(?:was|were)\s+(?:the\s+)?"
                        + re.escape(normalized(name))
                        + "|"
                        + re.escape(normalized(name))
                        + r"\s+(?:was|were)\s+(?:tested|evaluated|examined)\b",
                        normalized(s["quote"]),
                    )
                    for s in group["support"]
                    for name in (
                        group["label"],
                        acronym_printed_form(group["label"], [s["quote"]]) or group["label"],
                    )
                )
            ):
                # "The valve under test was the Main Feed Valve (MFV) 4.1".
                relation = "usesSample"
            elif (
                other["class_id"] == "ExperimentalCondition"
                and other["study"] == group["study"]
                and group_rows_printing(
                    label_variants(group["label"], document), other["label"], document
                )
            ):
                relation = "hasCondition"
            if relation and (group["key"], relation, other["key"]) not in proposed:
                proposed.add((group["key"], relation, other["key"]))
                # The investigation uses its specimen: usesSample points from it.
                subject, obj = (
                    (other["key"], group["key"])
                    if relation == "usesSample"
                    else (group["key"], other["key"])
                )
                candidates.append(
                    {
                        "subject": subject,
                        "relation": relation,
                        "object": obj,
                        "support": list(group["support"])
                        + ([] if relation == "madeOf" else list(other["support"])),
                    }
                )
    conditions = [
        e
        for e in output["entities"]
        if e["class_id"].endswith("Condition") and e.get("study") == "current"
    ]
    texts = _page_texts(document)
    names = {
        g["key"]: [g["label"]] + re.findall(r"\(([A-Z][A-Z0-9-]{1,9})\)", g["label"])
        for g in groups
        if g["study"] == "current"
    }

    def add_condition(group, condition, printed=()):
        key = (group["key"], "hasCondition", condition["key"])
        if key in proposed:
            return
        proposed.add(key)
        candidates.append(
            {
                "subject": group["key"],
                "relation": "hasCondition",
                "object": condition["key"],
                "support": list(group["support"]) + list(printed) + list(condition["support"]),
            }
        )

    # A condition this study prints as a setting inside a group's own
    # subsection ("B. Light Load Runs ... To reach the target spin,
    # the rotor was turned") is a condition of that group, unless its
    # sentence names another group ("close to that of the depot").
    for group, results, evidence_id, begin, stop in heading_regions(output, document):
        if group["class_id"] != "ExperimentFamily":
            continue
        region = texts[evidence_id][begin:stop]
        cuts = [0] + [m.end() for m in re.finditer(r"[.!?](?=\s)", segmentation_view(region))]
        sentences = [
            (head, region[head:tail]) for head, tail in zip(cuts, cuts[1:] + [len(region)])
        ]
        for condition in conditions:
            # Its name printed as a setting there ("To reach the target spin,
            # the rotor was turned").
            printed = [
                (head, sentence)
                for head, sentence in sentences
                if setting_mention(condition["label"], sentence)
            ]
            for head, sentence in printed:
                if any(
                    mentions(name, sentence)
                    for other, forms in names.items()
                    if other != group["key"]
                    for name in forms
                ):
                    continue
                lead = len(sentence) - len(sentence.lstrip())
                add_condition(
                    group,
                    condition,
                    [
                        {
                            "evidence_id": evidence_id,
                            "quote": sentence.strip(),
                            "start": begin + head + lead,
                        }
                    ],
                )
                break
    # "Custom flame-proof tabs stitched onto inner liner cloth burned at 29%
    # O2 and 61 kPa": the settings a thing is printed as tested at are its
    # conditions when the document proposes them as conditions.
    for group in groups:
        if group["study"] != "current":
            continue
        for _evidence_id, _start, clause in tested_at_clauses(group["label"], texts):
            for condition in conditions:
                if mentions(condition["label"], clause):
                    add_condition(group, condition)
    return candidates


def tested_at_clauses(label, texts):
    """Where the text prints "<label> tested at <settings>", and those settings.

    Yields (evidence_id, start of the label, the settings clause) for each
    printing; the clause ends at the sentence, bullet or blank line.
    """
    name = r"\s+".join(re.escape(w) for w in label.split())
    for evidence_id, text in texts.items():
        for m in re.finditer(
            r"(?<![\w-])" + name + r"\s+(?:(?:was|were|are|is)\s+)?tested\s+at\s+(?=[~≈]?\d)",
            text,
            re.IGNORECASE,
        ):
            tail = text[m.end() : m.end() + 160]
            # A slide's next item starts a capitalized word on its own line; a
            # wrapped clause continues with a unit, a species or a lowercase word.
            cut = re.search(r"[.;!?](?=\s|$)|\n\s*\n|•|\n(?=\s*[A-Z][a-z])", tail)
            yield evidence_id, m.start(), tail[: cut.start()] if cut else tail
