"""Phase 1 evaluation protocol v2: evidence-anchored finders and separate outcome states.

The frozen v4 targets, their historical scores, the earlier finders and scorers and
every prior adjudication are left as they are; this protocol reads them and adds a
second, versioned reading (mandate 2026-10-25 §14, decisions 1, 3 and 5). It is not
frozen yet; once frozen, any change is a new version.

A *finder* matches records to a target by its frozen original anchor (evidence id
and character range), not by literal similarity: a record is a candidate when it is
of the target's kind, is the active reading (never a duplicate or an inactive
variant) and one of its supporting spans overlaps the target's printed passage.
Kind-specific checks keep different things apart:

- an entity's label is the printed identity, whole words, shorter or longer form;
- a quantity's value and unit are the target's own (``±``, ranges, thousands
  separators and spacing normalized);
- a statement's text carries the target's printed words.

The *outcome* of a target is read from the separate states of its candidates
(``proposal_states.state_dimensions``): COMPLETE, COMPLETE_WITH_STAGED_EXTENSION,
EVIDENCE_RETAINED, INCOMPLETE, REJECTED or OMITTED. Whether a complete candidate is
*correct* is an adjudication, never decided here; each record credits at most one
target, and a record two targets share is an ambiguity for review.

A target whose finder cannot pick one reading is put in a general ambiguity group
(decision 5): SAME_VALUE_IN_SEVERAL_PASSAGES, SUBJECT_OR_RELATION, DIFFERENT_SCOPE,
MISSING_ENDPOINTS, SHARED_RECORD.

Precision is read from record judgments (correct, incorrect, critical) over the
active supported records; critical errors are counted apart.
"""

import re
from collections import Counter

from nasa_fire_ai.ingestion.proposal_states import state_dimensions

PROTOCOL_VERSION = "phase1-evaluation-v2.1"
OUTCOME_ORDER = (
    "COMPLETE",
    "COMPLETE_WITH_STAGED_EXTENSION",
    "EVIDENCE_RETAINED",
    "INCOMPLETE",
    "REJECTED",
    "OMITTED",
)
COMPLETE = {"COMPLETE", "COMPLETE_WITH_STAGED_EXTENSION"}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def value_key(expression):
    """A printed value with spacing, ``+/-`` and thousands separators normalized."""
    text = (expression or "").replace("+/-", "±").replace("−", "-").replace("–", "-")
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    return re.sub(r"\s+", "", text)


def unit_key(unit):
    return re.sub(r"[\s.]+", "", (unit or "").lower())


# Prefix letters whose case is their meaning (milli and mega, pico and peta, ...).
CASE_PREFIXES = frozenset("mpzyg")


def _same_unit(a, b):
    a, b = re.sub(r"[\s.]+", "", a), re.sub(r"[\s.]+", "", b)
    if a == b:
        return True
    return (
        a.lower() == b.lower() and bool(a) and (a[0] == b[0] or a[0].lower() not in CASE_PREFIXES)
    )


def unit_matches(target_unit, record_unit):
    """The record prints the target's unit: the same unit (spacing, and case except
    a prefix's, ignored), or the same base unit where only one side adds a printed
    qualifier ("% O2" and "%", "mm OD" and "mm"). Two different qualifiers differ."""
    if not target_unit:
        return True
    if _same_unit(target_unit, record_unit or ""):
        return True
    a, b = target_unit.split(), (record_unit or "").split()
    if not a or not b or not _same_unit(a[0], b[0]):
        return False
    qa, qb = [w.lower() for w in a[1:]], [w.lower() for w in b[1:]]
    return not qa or not qb or qa == qb


def active(record):
    return not record.get("duplicate_of") and record.get("active_proposal") is not False


def overlaps(span, target):
    return (
        span.get("evidence_id") == target.get("evidence_id")
        and span.get("start") is not None
        and target.get("start") is not None
        and span["start"] < target["end"]
        and target["start"] < span.get("end", span["start"])
    )


def _contains_words(longer, shorter):
    words, inner = _tokens(longer), _tokens(shorter)
    return bool(inner) and any(
        words[i : i + len(inner)] == inner for i in range(len(words) - len(inner) + 1)
    )


def matches(target, record):
    """Whether a record, on the target's passage, is a reading of this target."""
    item = record.get("proposal") or {}
    kind = target["kind"]
    if kind == "entities":
        label, quote = item.get("label"), target["quote"]
        return _contains_words(quote, label) or _contains_words(label, quote)
    if kind == "quantities":
        if target.get("expression") is not None:
            if value_key(item.get("expression")) != value_key(target["expression"]):
                return False
            return unit_matches(target.get("unit"), item.get("unit"))
        return bool(set(_tokens(item.get("expression"))) & set(_tokens(target["quote"])))
    if kind == "statements":
        quote, text = set(_tokens(target["quote"])), set(_tokens(item.get("text")))
        return bool(quote) and len(quote & text) >= 0.6 * len(quote)
    return True


def anchors(record):
    """Where a record is printed: a quantity's own printed value when the record
    carries it (a support span may hold several passages that print the same value),
    otherwise its supporting spans."""
    if record.get("kind") == "quantities" and record.get("quantity_value_spans"):
        return record["quantity_value_spans"]
    return record.get("support_spans") or []


def candidates(target, records):
    """Active records of the target's kind on the target's passage that read it."""
    return [
        record
        for record in records
        if record.get("kind") == target["kind"]
        and active(record)
        and any(overlaps(s, target) for s in anchors(record))
        and matches(target, record)
    ]


def _occurrences(value, text):
    if not value:
        return 0
    pattern = r"(?<![\d.,])" + re.escape(value) + r"(?![\d]|[.,]\d)"
    normalized = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text or "")
    return len(re.findall(pattern, normalized))


def ambiguity(target, found, document_text=""):
    """The general ambiguity group of a target's finder, or None when it is unique."""
    kind = target["kind"]
    live = [r for r in found if r.get("status") != "REJECTED"]
    if kind == "relations":
        if not found:
            return None  # nothing was read: an omission, not missing endpoints
        if not any(r.get("subject") and r.get("object") for r in found):
            return "MISSING_ENDPOINTS"
        return None
    subjects = {
        tuple(sorted((r.get("proposal") or {}).get("subjects") or []))
        or (r.get("proposal") or {}).get("subject")
        for r in live
    }
    if len(subjects) > 1:
        return "SUBJECT_OR_RELATION"
    studies = {(r.get("proposal") or {}).get("study") for r in live} - {None}
    if len(studies) > 1:
        return "DIFFERENT_SCOPE"
    if kind == "quantities" and document_text:
        value = value_key(target.get("expression"))
        number = re.match(r"[\d.]+", value.lstrip("<>~≈≤≥"))
        if number and _occurrences(number.group(), document_text) > 1:
            return "SAME_VALUE_IN_SEVERAL_PASSAGES"
    return None


def outcome(found, approved_terms=()):
    """The best state among a target's candidates, in the protocol's order."""
    if not found:
        return "OMITTED"
    best = len(OUTCOME_ORDER) - 1
    for record in found:
        dims = state_dimensions(record, approved_terms=approved_terms)
        if dims["completeness"] == "COMPLETE":
            state = (
                "COMPLETE_WITH_STAGED_EXTENSION" if dims["extension"] == "STAGED" else "COMPLETE"
            )
        elif dims["completeness"] == "EVIDENCE_RETAINED":
            state = "EVIDENCE_RETAINED"
        elif dims["completeness"] in {"INCOMPLETE", "STAGED_PROPOSAL", "DUPLICATE"}:
            state = "INCOMPLETE"
        else:
            state = "REJECTED"
        best = min(best, OUTCOME_ORDER.index(state))
    return OUTCOME_ORDER[best]


JUDGMENTS = ("correct", "incorrect", "critical")


def _judgments(judgments):
    normalized = {}
    for record_id, value in (judgments or {}).items():
        verdict = str(value).strip().lower()
        if verdict not in JUDGMENTS:
            raise ValueError(f"Unknown judgment {value!r} for {record_id}")
        normalized[record_id] = verdict
    return normalized


def _assign(complete_by_target):
    """A deterministic maximum assignment of complete records to targets, one record
    per target and one target per record (targets and records taken in id order).

    Returns the record assigned to each target whose connected group of targets and
    records is fully assigned; a group where some target must go without is left to
    the one-record-one-target rule (a record two targets share is not credited)."""
    match = {}

    def augment(target, seen):
        for record_id in sorted(complete_by_target[target]):
            if record_id in seen:
                continue
            seen.add(record_id)
            if record_id not in match or augment(match[record_id], seen):
                match[record_id] = target
                return True
        return False

    for target in sorted(complete_by_target):
        augment(target, set())
    assigned = {t: r for r, t in match.items()}
    # Connected groups of targets that share records.
    group_of, groups = {}, []
    for target in sorted(complete_by_target):
        if target in group_of or not complete_by_target[target]:
            continue
        group, stack = set(), [target]
        while stack:
            t = stack.pop()
            if t in group:
                continue
            group.add(t)
            for record_id in complete_by_target[t]:
                stack.extend(
                    o for o, rs in complete_by_target.items() if record_id in rs and o not in group
                )
        groups.append(group)
        for t in group:
            group_of[t] = len(groups) - 1
    return {t: assigned[t] for group in groups if all(t in assigned for t in group) for t in group}


def evaluate(
    targets,
    records,
    judgments=None,
    document_text="",
    approved_terms=(),
    historical_correct_targets=None,
    historical_run_id=None,
    run_id=None,
    corrections=None,
):
    """Every accessible target's protocol reading, precision and critical errors.

    ``judgments`` maps a record id to ``"correct"``, ``"incorrect"`` or
    ``"critical"`` (an adjudication of that record; case and spacing ignored, any
    other value refused). ``historical_correct_targets`` is the form the earlier
    adjudications take (target ids judged correctly recovered in one run); it is
    accepted only with ``historical_run_id`` naming that run and equal to
    ``run_id``, the identity of the run evaluated. ``approved_terms`` are the terms
    approved in the run's ontology version. ``corrections`` is a separately
    versioned set of target field corrections (each with its ``rationale``); the
    frozen targets are never modified.
    """
    judgments = _judgments(judgments)
    if historical_correct_targets is not None:
        if not historical_run_id:
            raise ValueError("Historical target judgments must name the run they judge")
        if run_id != historical_run_id:
            raise ValueError(
                f"Historical judgments of {historical_run_id} cannot judge run {run_id}"
            )
    historical = set(historical_correct_targets or ())
    corrections = corrections or {}
    accessible = []
    for t in targets:
        if t.get("outcome") == "inaccessible" or t["kind"] not in {
            "entities",
            "statements",
            "quantities",
            "relations",
        }:
            continue
        fix = corrections.get(t["id"])
        accessible.append({**t, **{k: v for k, v in fix.items() if k != "rationale"}} if fix else t)
    found_by_target = {t["id"]: candidates(t, records) for t in accessible}
    complete_by_target = {
        tid: [r for r in found if outcome([r], approved_terms) in COMPLETE]
        for tid, found in found_by_target.items()
    }
    uses = Counter(r["id"] for found in complete_by_target.values() for r in found)
    assigned = _assign({tid: {r["id"] for r in found} for tid, found in complete_by_target.items()})
    rows = []
    for target in accessible:
        found = found_by_target[target["id"]]
        complete = complete_by_target[target["id"]]
        if target["id"] in assigned:
            own = [r for r in complete if r["id"] == assigned[target["id"]]]
        else:
            own = [r for r in complete if uses[r["id"]] == 1]
        group = ambiguity(target, found, document_text)
        if complete and not own:
            # Every complete reading is also another target's and no assignment
            # gives each target its own: the assignment goes to review.
            group = "SHARED_RECORD"
        verdicts = {judgments.get(r["id"]) for r in own}
        if not complete:
            correctness = None
        elif own and ("correct" in verdicts or (historical_run_id and target["id"] in historical)):
            correctness = "CORRECT"
        elif own and verdicts and verdicts <= {"incorrect", "critical"}:
            correctness = "INCORRECT"
        else:
            correctness = "PENDING_ADJUDICATION"
        rows.append(
            {
                "target": target["id"],
                "kind": target["kind"],
                "outcome": outcome(found, approved_terms),
                "correctness": correctness,
                "ambiguity": group,
                "candidates": sorted(r["id"] for r in found),
                **(
                    {"correction": corrections[target["id"]].get("rationale")}
                    if target["id"] in corrections
                    else {}
                ),
            }
        )
    # Every record that can be credited as recall is also in the precision population.
    supported = [
        r
        for r in records
        if active(r)
        and (r.get("status") == "SOURCE_SUPPORTED" or outcome([r], approved_terms) in COMPLETE)
    ]
    judged = [judgments[r["id"]] for r in supported if r["id"] in judgments]
    unjudged = len(supported) - len(judged)
    return {
        "protocol": PROTOCOL_VERSION,
        **({"historical_run_id": historical_run_id} if historical_run_id else {}),
        "targets": rows,
        "counts": {
            "accessible": len(rows),
            "by_outcome": dict(Counter(r["outcome"] for r in rows)),
            "recalled": sum(r["correctness"] == "CORRECT" for r in rows),
            "pending_adjudication": sum(r["correctness"] == "PENDING_ADJUDICATION" for r in rows),
            "by_ambiguity": dict(Counter(r["ambiguity"] for r in rows if r["ambiguity"])),
        },
        "precision": {
            "supported_records": len(supported),
            "judged": len(judged),
            "correct": judged.count("correct"),
            "critical": judged.count("critical"),
            "unjudged": unjudged,
            "unjudged_records": sorted(r["id"] for r in supported if r["id"] not in judgments),
            # The gate's value: defined only when every such record is judged.
            "value": judged.count("correct") / len(supported)
            if supported and not unjudged
            else None,
        },
    }
