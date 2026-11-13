"""Follow-up request selection: which fields a window still lacks."""

import re

from nasa_fire_ai.ingestion.extraction_validation import validate_output
from nasa_fire_ai.ingestion.printed_layout import group_section_support
from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS
from nasa_fire_ai.ingestion.source_spans import locate, mentions
from nasa_fire_ai.ingestion.structural_candidates import heading_regions
from nasa_fire_ai.ingestion.subject_recognition import has_class

# Why a proposal was held, in plain words, for the fields the source may print.
MISSING_FIELD_WORDS = (
    ("SUBJECT", "its subject (the tested object, run or group it is about) is not resolved"),
    ("SEMANTICS_OR_UNIT", "what quantity the value is, or its unit, is not established"),
    ("UNIT_NOT_BOUND", "its unit is not bound to the printed value"),
    ("ROLE", "its role (condition, result, criterion or plan) is not established"),
    ("CURRENT_OR_CITED", "whether it is this study's or cited work is not resolved"),
)


MISSING_FIELDS_PER_WINDOW = 25


def missing_fields(
    output, package, document, semantic, windows, words=MISSING_FIELD_WORDS, detail=False
):
    """Per window, the held or rejected statements and values whose missing field the
    source may print, with the reason in plain words."""
    found = {}
    for record in validate_output(output, package, document, semantic)["records"]:
        if record["kind"] not in {"statements", "quantities"} or record["status"] not in {
            "UNRESOLVED",
            "REJECTED",
        }:
            continue
        reasons = sorted(
            {
                plain
                for reason in record.get("reasons") or []
                if (plain := next((p for cue, p in words if cue in reason), None))
            }
        )
        spans = record.get("support_spans") or []
        if not reasons or not spans:
            continue
        span = spans[0]
        for window in windows:
            if any(
                m["evidence_id"] == span["evidence_id"] and m["start"] <= span["start"] < m["end"]
                for m in window["members"]
            ):
                asked = found.setdefault(window["id"], [])
                if len(asked) >= MISSING_FIELDS_PER_WINDOW:
                    break  # bounded request; the rest stay held
                item = {
                    "kind": record["kind"],
                    "printed": (span.get("quote") or "")[:300],
                    "held_because": reasons,
                }
                if detail:
                    # What was proposed, so the answer can change the role, the
                    # modality or the study, and a value is told apart from its sibling.
                    proposal = record.get("proposal") or {}
                    item["proposed"] = {
                        k: proposal.get(k)
                        for k in ("epistemic", "modality", "study", "label", "expression", "unit")
                        if proposal.get(k) is not None
                    }
                asked.append(item)
                break
    return found


def grounded_entities(output, package, document, semantic, window, context=None):
    """Only independently validated same-source identities may cross stage boundaries."""
    validation = validate_output(output, package, document, semantic)
    entities = [
        e
        for e in validation["entities_by_key"].values()
        if e.get("validation_status") == "SOURCE_SUPPORTED"
        and e["source_id"] == window["members"][0]["source_id"]
    ]
    local_text = " ".join(s["text"] for s in window["members"])
    from nasa_fire_ai.ingestion.scientific_scope import test_article_alias_review

    figure_refs = set(re.findall(r"\b(?:Figures?|Figs?\.?)\s+(\d+)\b", local_text, re.IGNORECASE))
    text = local_text
    if context:
        text += " " + " ".join(a["quote"] for a in context["anchors"])
    from nasa_fire_ai.ingestion.table_continuity import printed_label_forms

    def named(label, passage):
        # A row group label may be printed with its legend-backed footnote marker.
        return any(mentions(form, passage) for form in printed_label_forms(label, document))

    entities.sort(
        key=lambda e: (
            not named(e["label"], local_text),
            e["class_id"] not in {"Investigation", "ExperimentFamily"},
            e["key"],
        )
    )
    selected = []
    for entity in entities:
        if (
            not named(entity["label"], text)
            and not (entity["class_id"] == "Investigation" and entity["study"] == "current")
            and not any(
                test_article_alias_review(
                    entity["key"],
                    [{**m, "quote": m["text"]}],
                    validation["entities_by_key"],
                    document,
                )
                for m in window["members"]
            )
            and not any(
                f["number"] in figure_refs
                and f["source_id"] == entity["source_id"]
                and mentions(entity["label"], f["quote"])
                for f in document.get("figures", [])
            )
            and not any(
                group_section_support(
                    entity["key"],
                    [
                        {
                            "source_id": m["source_id"],
                            "evidence_id": m["evidence_id"],
                            "start": m["start"],
                            "quote": "",
                        }
                    ],
                    validation["entities_by_key"],
                    document,
                )
                for m in window["members"]
            )
        ):
            continue
        supports = [s for s in entity["support"] if named(entity["label"], s["quote"])]
        local = [
            s
            for s in supports
            if any(s["evidence_id"] == m["evidence_id"] for m in window["members"])
        ]
        # The original precise identity location stays available; irrelevant
        # support attachments must not replicate the entire document in each task.
        # A validated identity never travels without its own anchor.
        chosen = (
            local
            or sorted(supports, key=lambda s: len(s["quote"]))[:1]
            or list(entity["support"][:1])
        )
        selected.append(
            {**{k: entity[k] for k in ("key", "label", "class_id", "study")}, "support": chosen}
        )
    return selected


def unlinked_group_subsections(output, package, document, semantic):
    """Groups whose subsection prints linkable entities that no accepted relation uses.

    Yields (group key, segments of its subsection) for each current, supported
    ExperimentFamily with a printed heading region holding the support of a
    current condition, material, sample or intervention, while no accepted
    relation has the group as subject.
    """
    checked = validate_output(output, package, document, semantic)
    supported = {
        r["proposal"]["key"]
        for r in checked["records"]
        if r["kind"] == "entities"
        and r["status"] == "SOURCE_SUPPORTED"
        and r["proposal"]["class_id"] == "ExperimentFamily"
        and r["proposal"].get("study") == "current"
    }
    linked = {
        r["proposal"]["subject"]
        for r in checked["records"]
        if r["kind"] == "relations"
        and r["status"] == "SOURCE_SUPPORTED"
        and r["proposal"]["relation"] in RELATION_ENDPOINTS
    }
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    linkable = [
        s
        for e in output["entities"]
        if e.get("study") == "current"
        and any(
            has_class(e["class_id"], base, semantic)
            for base in ("ExperimentalCondition", "Material", "Sample", "Intervention")
        )
        for s in locate(e["support"], evidence)
    ]
    regions = {}
    for group, _results, evidence_id, begin, stop in heading_regions(output, document):
        if group["class_id"] != "ExperimentFamily" or group["key"] not in supported:
            continue
        if group["key"] in linked:
            continue
        if any(s["evidence_id"] == evidence_id and begin <= s["start"] < stop for s in linkable):
            regions.setdefault(group["key"], []).append((evidence_id, begin, stop))
    for key, parts in regions.items():
        members = [
            segment
            for segment in document["segments"]
            if any(
                segment["evidence_id"] == evidence_id
                and segment["start"] < stop
                and segment["end"] > begin
                for evidence_id, begin, stop in parts
            )
        ]
        if members:
            yield key, members
