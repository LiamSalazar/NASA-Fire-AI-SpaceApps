"""Proposal states and the vocabulary extensions a source needs; nothing here is activated.

A validated record is in exactly one of these states. The last two are reached only
through curation (review, then authorized publication), never by extraction:

- REJECTED: unsupported by the source; kept for audit.
- STRUCTURALLY_WELL_FORMED: parsed and anchored, but a source or scientific check is
  still open.
- SOURCE_SUPPORTED: supported by the source with the approved vocabulary.
- PROPOSED_ONTOLOGY_EXTENSION: supported by the source except that a class, statement
  class or relation it uses is not in the approved vocabulary; the term is staged as
  an extension proposal beside it.
- SCIENTIFICALLY_REVIEWED, AUTHORIZED_PUBLISHED: set by curation.
"""

import re
import unicodedata

from nasa_fire_ai.ingestion.extraction_schema import PROPOSE_NEW_CLASS, PROPOSE_NEW_RELATION
from nasa_fire_ai.ingestion.scientific_facets import PLAN_GOAL_ROLES, profile

PROPOSAL_STATES = (
    "REJECTED",
    "STRUCTURALLY_WELL_FORMED",
    "SOURCE_SUPPORTED",
    "PROPOSED_ONTOLOGY_EXTENSION",
    "SCIENTIFICALLY_REVIEWED",
    "AUTHORIZED_PUBLISHED",
)

# A reason that only says the approved vocabulary lacks a term, by kind of term. A
# concept the model proposed explicitly names its own kind (class, property,
# relation or alias).
VOCABULARY_REASONS = {
    "UNREGISTERED_CLASS_NEEDS_SEMANTIC_REVIEW": "class",
    "UNREGISTERED_INFORMATION_CLASS": "information_class",
    "UNREGISTERED_RELATION": "relation",
    "ONTOLOGY_EXTENSION_REVIEW": "concept",
}


def _plain_words(term):
    """The words of a printed name in ASCII: accents dropped, Greek letters by name
    ("α-phase" is "alpha phase"), CamelCase split ("IgniterCoil" is two words)."""
    out = []
    for ch in unicodedata.normalize("NFKD", term or ""):
        if unicodedata.combining(ch):
            continue
        if ch.isascii():
            out.append(ch)
            continue
        greek = re.match(r"GREEK (?:SMALL|CAPITAL) LETTER (\w+)", unicodedata.name(ch, ""))
        out.append(f" {greek.group(1).lower()} " if greek else " ")
    return [
        part
        for token in re.findall(r"[A-Za-z0-9]+", "".join(out))
        for part in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", token)
    ]


def _singular(word):
    """A generic final plural only: "shrouds" is "shroud"; "glass", "apparatus",
    "analysis" keep their s."""
    low = word.lower()
    if len(low) > 3 and low.endswith("s") and not low.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def identifier(term, kind):
    """A printed concept name as a vocabulary identifier; the printed name is kept apart.

    One normalization for every proposal: a class is CamelCase with its head noun
    singular ("porous radiative shields" and "Porous radiative shield" are both
    ``PorousRadiativeShield``, "shroud" is ``Shroud``); a property is lowerCamel
    with a singular head; a relation is lowerCamel as printed ("ignites sample" is
    ``ignitesSample``, "Ignites" is ``ignites``).
    """
    words = _plain_words(term)
    if not words:
        return ""
    if kind != "relation":
        words[-1] = _singular(words[-1])
    name = "".join(w[:1].upper() + w[1:].lower() if not w.isupper() else w for w in words)
    if kind in {"relation", "property"}:
        name = name[:1].lower() + name[1:]
    return name


def term_of(record, kind):
    """The (kind, term) a vocabulary reason of this kind refers to."""
    item = record.get("proposal") or {}
    if kind == "concept":
        concept_kind = item.get("kind") or "class"
        return concept_kind, identifier(item.get("term"), concept_kind)
    return kind, item.get("relation") if kind == "relation" else item.get("class_id")


def extension_proposal_id(kind, term):
    return f"{kind}-proposal-{term}"


# Entailment is checked against the printed wording of approved relations only, so
# an unregistered relation always needs it reviewed; that review is the proposal's.
FOLLOWS_FROM_UNREGISTERED = {"UNREGISTERED_RELATION": {"RELATION_ENTAILMENT_REQUIRES_REVIEW"}}


def proposal_state(record):
    if record["status"] == "REJECTED":
        return "REJECTED"
    if record["status"] == "SOURCE_SUPPORTED":
        return "SOURCE_SUPPORTED"
    reasons = set(record.get("reasons") or [])
    for reason, follows in FOLLOWS_FROM_UNREGISTERED.items():
        if reason in reasons:
            reasons -= follows
    if reasons and reasons <= set(VOCABULARY_REASONS):
        return "PROPOSED_ONTOLOGY_EXTENSION"
    return "STRUCTURALLY_WELL_FORMED"


# Rejections that say the proposal was malformed, not that the science was wrong.
STRUCTURAL_REJECTIONS = (
    "INVALID_",
    "UNKNOWN_",
    "PROPOSED_TERM_",
    "UNEXPECTED_",
    "MISSING_",
)


def vocabulary_terms(record):
    """The unapproved terms a record needs, as (kind, term) pairs."""
    return sorted(
        {
            term_of(record, kind)
            for reason in record.get("reasons") or []
            if (kind := VOCABULARY_REASONS.get(reason))
        }
    )


def state_dimensions(record, approved_terms=(), published=False):
    """The five separate states of one record (mandate §5 decision 1).

    - ``completeness``: COMPLETE (a full structured extraction, possibly with a
      staged term), EVIDENCE_RETAINED (the sentence kept as documentary context, not
      interpreted), INCOMPLETE (an open source or scientific question) or REJECTED.
    - ``evidence``: SOURCE_SUPPORTED, OPEN or UNSUPPORTED.
    - ``structure``: VALID or INVALID (malformed, not scientifically wrong).
    - ``extension``: NOT_NEEDED (approved vocabulary only), STAGED, or
      APPROVED_IN_WORKSPACE when every term it needs was approved in review.
    - ``publication``: AUTHORIZED only for a complete record of the active version
      that needs no term still staged; staging never publishes.

    ``approved_terms`` names the terms approved in this workspace; ``published`` says
    whether this exact version is the active one. Neither is ever written here.
    """
    reasons = set(record.get("reasons") or [])
    terms = vocabulary_terms(record)
    structure = record.get("provenance_structure") or {}
    # A provenance record rests on a staged term: staged, never published.
    if structure.get("relation_state") == "STAGED":
        terms = terms + [("relation", structure.get("relation_term"))]
    if structure.get("source_state") == "STAGED":
        terms = terms + [("class", structure.get("source_class"))]
    item = record.get("proposal") or {}
    if record.get("duplicate_of") or record.get("active_proposal") is False:
        # Another record owns this assertion; this one is never counted or
        # published. The losing reading of a current/cited conflict stays open.
        return {
            "completeness": "DUPLICATE",
            "evidence": "UNSUPPORTED" if record.get("status") == "REJECTED" else "OPEN",
            "structure": "VALID",
            "extension": "NOT_NEEDED",
            "publication": "NOT_AUTHORIZED",
        }
    if record.get("kind") == "concepts":
        # A proposed concept is a staging proposal, never a complete datum: its
        # evidence is its printed anchors, and it is never published by a record
        # (the extension itself is approved and activated in review). The same
        # reading whatever state an older receipt stored.
        rejected = record.get("status") == "REJECTED"
        return {
            "completeness": "REJECTED" if rejected else "STAGED_PROPOSAL",
            "evidence": "UNSUPPORTED" if rejected else "SOURCE_SUPPORTED",
            "structure": "VALID",
            "extension": "NOT_NEEDED" if "EXISTING_CONCEPT_REUSE_REQUIRED" in reasons else "STAGED",
            "publication": "NOT_AUTHORIZED",
        }
    state = record.get("proposal_state") or proposal_state(record)
    if {"UNREGISTERED_RELATION", "RELATION_ENTAILMENT_REQUIRES_REVIEW"} <= reasons:
        # Nobody has yet checked that the source states this unregistered relation:
        # it is staged for review, not a supported extraction.
        state = "STRUCTURALLY_WELL_FORMED"
    if state == "REJECTED":
        structural = any(r.startswith(STRUCTURAL_REJECTIONS) for r in reasons)
        return {
            "completeness": "REJECTED",
            "evidence": "OPEN" if structural else "UNSUPPORTED",
            "structure": "INVALID" if structural else "VALID",
            "extension": "NOT_NEEDED",
            "publication": "NOT_AUTHORIZED",
        }
    supported = state in {"SOURCE_SUPPORTED", "PROPOSED_ONTOLOGY_EXTENSION"}
    if not supported:
        completeness = "INCOMPLETE"
    elif record.get("kind") == "statements" and item.get("epistemic") == "documentary_context":
        # A sentence kept as context is retained evidence, not an interpreted goal,
        # plan, criterion or configuration.
        completeness = "EVIDENCE_RETAINED"
    else:
        completeness = "COMPLETE"
    approved = set(approved_terms)
    if not terms:
        extension = "NOT_NEEDED"
    elif all(term in approved for _, term in terms):
        extension = "APPROVED_IN_WORKSPACE"
    else:
        extension = "STAGED"
    return {
        "completeness": completeness,
        "evidence": "SOURCE_SUPPORTED" if supported else "OPEN",
        "structure": "VALID",
        "extension": extension,
        "publication": "AUTHORIZED"
        if published and completeness != "INCOMPLETE" and extension != "STAGED"
        else "NOT_AUTHORIZED",
    }


IDENTIFIER = r"[A-Za-z][A-Za-z0-9]*"


def _words(term):
    import re

    return [w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", term)]


def _equivalence_key(term):
    """Case, separators and a final plural do not make another term."""
    import re

    key = re.sub(r"[^a-z0-9]", "", term.lower())
    return key[:-1] if key.endswith("s") and len(key) > 3 else key


def approved_alias_index(semantic):
    """Every approved alias (class query terms, property and relation aliases) by its
    equivalence key, pointing at the approved term it names."""
    index = {}
    for cls, meta in semantic.class_metadata.items():
        for alias in meta.get("query_terms") or []:
            index.setdefault(_equivalence_key(alias), cls)
    for pid, prop in semantic.properties.items():
        for alias in getattr(prop, "aliases", None) or []:
            index.setdefault(_equivalence_key(alias), pid)
    for rid, rel in semantic.relations.items():
        for alias in getattr(rel, "aliases", None) or []:
            index.setdefault(_equivalence_key(alias), rid)
    return index


def reuse_analysis(proposal, approved):
    """Directive cases A-C and the §6 distinctions, decided from the terms themselves.

    A: the term is an approved term written differently: reuse it, never extend.
    B: the term names an approved class with a qualifier (a subclass or a contextual
       attribute of it), or a relation between endpoints an approved relation already
       links (a new relation or that relation with qualifiers): review decides.
    C: genuinely new vocabulary.
    A term carrying digits, or a class named after its only instance, names an
    instance, not a class.
    """
    kind, term = proposal.get("kind"), proposal.get("term") or ""
    terms = approved.get(kind, set())
    errors = []
    equivalent = sorted(t for t in terms if _equivalence_key(t) == _equivalence_key(term))
    if equivalent and term not in equivalent:
        errors.append("TERM_EQUIVALENT_TO_AN_APPROVED_TERM")
    analysis = {"equivalent_approved_terms": equivalent}
    if kind != "relation":
        words = _words(term)
        if len(proposal.get("instances") or []) == 1 and _equivalence_key(
            proposal["instances"][0]
        ) == _equivalence_key(term):
            errors.append("TERM_NAMES_AN_INSTANCE")
        elif any(w.isdigit() for w in words):
            # Digits may name one item ("Coil3") or a legitimate grade or alloy class
            # ("Steel316"): review decides; it is not an error by itself.
            analysis["warnings"] = ["TERM_MAY_NAME_AN_INSTANCE_REQUIRES_REVIEW"]
        qualified = sorted(
            t
            for t in terms
            if len(_words(t)) < len(words) and words[-len(_words(t)) :] == _words(t)
        )
        analysis["approved_class_it_qualifies"] = qualified[-1] if qualified else None
        analysis["similar_approved_terms"] = sorted(
            t
            for t in terms
            if _words(t) and words and _words(t)[-1] == words[-1] and t not in qualified
        )
    else:
        endpoints = approved.get("relation_endpoints", {})
        domain, range_ = set(proposal.get("domain") or []), set(proposal.get("range") or [])
        # An approved relation whose endpoints are not known is no evidence that it
        # links these classes: only known, overlapping endpoints count.
        analysis["approved_relations_with_compatible_endpoints"] = sorted(
            r
            for r, (d, g) in endpoints.items()
            if domain and range_ and d and g and domain & set(d) and range_ & set(g)
        )
    if equivalent:
        case = "A_REUSE_APPROVED_TERM"
    elif analysis.get("approved_class_it_qualifies") or analysis.get(
        "approved_relations_with_compatible_endpoints"
    ):
        case = "B_PARTIAL_EXTENSION_REVIEW"
    else:
        case = "C_NEW_VOCABULARY"
    analysis["case"] = case
    return analysis, errors


def structural_validation(proposal, approved):
    """Whether a staged vocabulary proposal is well formed, checked apart from the baseline.

    ``approved`` maps each kind to the approved terms of that kind. Placement in the
    hierarchy is a scientific decision, so a class without an established parent is
    well formed but marked as needing placement.
    """
    import re

    errors = []
    term = proposal.get("term") or ""
    if not re.fullmatch(IDENTIFIER, term):
        errors.append("TERM_IS_NOT_AN_IDENTIFIER")
    known = {t.lower(): t for t in approved.get(proposal.get("kind"), ())}
    if term.lower() in known:
        errors.append(
            "TERM_ALREADY_APPROVED"
            if known[term.lower()] == term
            else "TERM_DIFFERS_FROM_AN_APPROVED_TERM_ONLY_BY_CASE"
        )
    evidence = proposal.get("evidence") or []
    if not evidence or not all(e.get("evidence_id") and e.get("quote") for e in evidence):
        errors.append("EVIDENCE_ANCHORS_MISSING")
    if proposal.get("kind") == "relation" and not (
        proposal.get("domain") and proposal.get("range")
    ):
        errors.append("RELATION_DOMAIN_OR_RANGE_UNKNOWN")
    kind = proposal.get("kind")
    targets = proposal.get("alias_of") or []
    targets = [targets] if isinstance(targets, str) else list(targets)
    if kind == "alias":
        if len(set(targets)) > 1:
            # Two printed uses make it a variant of different approved terms.
            errors.append("ALIAS_TARGET_CONFLICT")
        if not targets or not all(
            any(t in approved.get(k, ()) for k in ("class", "relation", "property"))
            for t in targets
        ):
            # A terminology variant names an approved term; otherwise it is a new term.
            errors.append("ALIAS_TARGET_NOT_APPROVED")
        # The variant's own words must not already name another approved term.
        named = approved.get("aliases", {}).get(_equivalence_key(term)) or next(
            (
                t
                for k in ("class", "relation", "property")
                for t in approved.get(k, ())
                if _equivalence_key(t) == _equivalence_key(term)
            ),
            None,
        )
        if named and named not in targets:
            errors.append("ALIAS_NAMES_ANOTHER_APPROVED_TERM")
    elif term:
        # An approved term of any kind with the same identifier is a reuse, not a
        # new term of another kind (property "flameSpread" beside class FlameSpread).
        other_kinds = sorted(
            t
            for k in ("class", "information_class", "relation", "property")
            if k != kind
            for t in approved.get(k, ())
            if _equivalence_key(t) == _equivalence_key(term)
        )
        if other_kinds:
            errors.append("TERM_EQUIVALENT_TO_AN_APPROVED_TERM_OF_ANOTHER_KIND")
    parent = proposal.get("parent") if kind in {"class", "information_class"} else None
    if parent and parent not in approved.get("class", ()):
        # An unapproved parent is not a placement; review decides it. Without the
        # approved vocabulary nothing can be checked, so nothing is placed.
        errors.append("PARENT_NOT_APPROVED")
        parent = None
    if proposal.get("activation") != "NONE":
        errors.append("EXTENSION_ACTIVATED_OUTSIDE_REVIEW")
    if proposal.get("definition") not in {None, "NOT_ESTABLISHED_BY_SOURCE"} and not proposal.get(
        "definition_evidence"
    ):
        errors.append("DEFINITION_WITHOUT_SOURCE_EVIDENCE")
    analysis, reuse_errors = reuse_analysis(proposal, approved)
    errors += [e for e in reuse_errors if e not in errors]
    if (
        "TERM_ALREADY_APPROVED" in errors
        or "TERM_DIFFERS_FROM_AN_APPROVED_TERM_ONLY_BY_CASE" in errors
    ):
        errors = [e for e in errors if e != "TERM_EQUIVALENT_TO_AN_APPROVED_TERM"]
    if kind in {"class", "information_class"}:
        parent = parent or analysis.get("approved_class_it_qualifies")
    placement = {
        "relation": "RELATION",
        "property": "PROPERTY",
        "alias": "ALIAS_OF_APPROVED_TERM",
    }.get(
        kind,
        "PARENT_CANDIDATE_REQUIRES_REVIEW" if parent else "PARENT_NOT_ESTABLISHED_REQUIRES_REVIEW",
    )
    return {
        "well_formed": not errors,
        "errors": errors,
        "reuse_analysis": analysis,
        "placement": placement,
        **(
            {"parent_candidate": parent}
            if parent and kind in {"class", "information_class"}
            else {}
        ),
    }


def vocabulary_extension_proposals(records, entity_classes, approved=None):
    """One staged proposal per missing term, with the evidence of every record that uses it.

    The proposal names the term, its documentary instances and, for a relation, the
    classes it was used between. It never supplies a definition the source does not
    print; scientific review decides placement and meaning.
    """
    proposals = {}
    approved_keys = {
        _equivalence_key(t): t
        for k in ("class", "information_class", "relation", "property")
        for t in (approved or {}).get(k, ())
    }
    for record in records:
        if record.get("proposal_state") != "PROPOSED_ONTOLOGY_EXTENSION" or record.get(
            "duplicate_of"
        ):
            continue
        item = record["proposal"]
        for reason in record["reasons"]:
            if reason not in VOCABULARY_REASONS:
                continue
            kind, term = term_of(record, VOCABULARY_REASONS[reason])
            if kind != "alias" and _equivalence_key(term) in approved_keys:
                # An approved term in its printed words ("experimental run") is that
                # term: the record is linked to it and nothing new is staged.
                record["reuses_approved_term"] = approved_keys[_equivalence_key(term)]
                continue
            key = (kind, _equivalence_key(term))
            if key in proposals and term != proposals[key]["term"]:
                # "Shroud" and "Shrouds": one proposal, every printed variant kept.
                variants = proposals[key].setdefault("term_variants", [])
                if term not in variants:
                    variants.append(term)
                proposals[key]["term"] = min(proposals[key]["term"], term)
                proposals[key]["id"] = extension_proposal_id(kind, proposals[key]["term"])
            proposal = proposals.setdefault(
                key,
                {
                    "id": extension_proposal_id(kind, term),
                    "kind": kind,
                    "term": term,
                    "definition": "NOT_ESTABLISHED_BY_SOURCE",
                    "instances": [],
                    "supporting_records": [],
                    "evidence": [],
                    "activation": "NONE",
                    "status": "STAGED_FOR_ONTOLOGY_REVIEW",
                    "proposal_state": "PROPOSED_ONTOLOGY_EXTENSION",
                    **({"domain": [], "range": []} if kind == "relation" else {}),
                },
            )
            proposal["supporting_records"].append(record["id"])
            if record.get("facets") and item.get("epistemic") in PLAN_GOAL_ROLES:
                # A plan or goal class is reviewed with the role's own profile, never
                # with whichever supporting record comes first or the modality it stated.
                proposal.setdefault("facet_profile", dict(profile("statements", item["epistemic"])))
            if record.get("kind") == "concepts":
                # The model named the concept itself: its printed name, its own
                # wording of the meaning and why approved terms do not fit are kept
                # for review, apart from a definition the source establishes.
                proposal.setdefault("printed_labels", [])
                if item.get("term") and item["term"] not in proposal["printed_labels"]:
                    proposal["printed_labels"].append(item["term"])
                proposal.setdefault("proposed_definition", item.get("definition"))
                proposal.setdefault(
                    "why_existing_insufficient", item.get("why_existing_insufficient")
                )
                if kind == "alias":
                    # Every target any printed use names, never the last one only.
                    target = item.get("parent_or_existing")
                    proposal.setdefault("alias_of", [])
                    if target and target not in proposal["alias_of"]:
                        proposal["alias_of"].append(target)
                        proposal["alias_of"].sort()
            parent = (record.get("proposed_term") or {}).get("parent") or (
                item.get("parent_or_existing") if record.get("kind") == "concepts" else None
            )
            if parent and parent not in proposal.setdefault("proposed_parents", []):
                # The approved term the model said this one refines: a candidate
                # placement for review, never a decided one.
                proposal["proposed_parents"].append(parent)
                if kind != "relation" and len(proposal["proposed_parents"]) == 1:
                    proposal["parent"] = parent
                elif kind != "relation":
                    proposal.pop("parent", None)
            label = item.get("label") or item.get("text") or ""
            if label and kind != "relation" and label not in proposal["instances"]:
                proposal["instances"].append(" ".join(label.split())[:160])
            if kind == "relation":
                for side, key in (("domain", "subject"), ("range", "object")):
                    cls = entity_classes.get(record.get(key))
                    if cls and cls not in proposal[side]:
                        proposal[side].append(cls)
            for span in record.get("support_spans") or []:
                anchor = {k: span[k] for k in ("evidence_id", "start", "end", "quote") if k in span}
                if anchor not in proposal["evidence"]:
                    proposal["evidence"].append(anchor)
    for proposal in proposals.values():
        for key in ("instances", "domain", "range"):
            if key in proposal:
                proposal[key].sort()
        proposal["structural_validation"] = structural_validation(proposal, approved or {})
    return [proposals[k] for k in sorted(proposals)]


def adopt_proposed_term(kind, item, record, semantic):
    """Use the model's explicitly proposed term in place of the sentinel.

    The term is then unregistered, so validation stages it as an ontology extension
    proposal; the parent must be approved vocabulary ("NONE" for a relation that
    qualifies no approved relation). A sentinel without a term names nothing.
    """
    field, sentinel, slot, approved = {
        "entities": ("proposed_class", PROPOSE_NEW_CLASS, "class_id", semantic.class_metadata),
        "relations": ("proposed_relation", PROPOSE_NEW_RELATION, "relation", semantic.relations),
    }.get(kind, (None, None, None, None))
    if field is None or item.get(slot) != sentinel:
        return
    proposed = item.get(field)
    if not proposed:
        raise ValueError("PROPOSED_TERM_NOT_NAMED")
    if proposed["term"] in approved:
        # An approved term chosen through the sentinel is just that term.
        item[slot] = proposed["term"]
        return
    if proposed["parent"] not in approved and not (
        kind == "relations" and proposed["parent"] == "NONE"
    ):
        raise ValueError("PROPOSED_TERM_PARENT_NOT_APPROVED")
    item[slot] = proposed["term"]
    record["proposed_term"] = {
        "term": proposed["term"],
        "parent": None if proposed["parent"] == "NONE" else proposed["parent"],
        "basis": "MODEL_PROPOSED_TERM_WITH_APPROVED_PARENT",
    }
