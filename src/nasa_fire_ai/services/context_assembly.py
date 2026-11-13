"""Question-responsive allocation of existing source anchors, never scientific validation.

General document/routing rule motivated by the saved conversation page losses:
plan needs before allocating context, reward new content and preserve identities.
Lexical routing explicitly leaves content sufficiency to source examination and
verification; a matching word cannot establish a scientific relationship.
"""

import json
import math
import re
from collections import Counter

import snowballstemmer

from nasa_fire_ai.services.investigation import topic_terms


def desired_source_roles(text):
    """Scientific information-type routing, never factual certification."""
    patterns = {
        "SourceReportedFinding": r"\b(?:findings?|results?|preliminary|observations?|behavio[u]?rs?|outcomes?)\b",
        "DocumentaryMethod": r"\b(?:methods?|approach\w*|configurations?|diagnostics?|techniques?|model(?:ed|led|ing)?|simulat\w*|uncertain\w*|error\s+(?:analysis|bars?))\b",
        "ResearchObjective": r"\b(?:objectives?|goals?|aims?|purposes?)\b",
        "ResearchHypothesis": r"\bhypothes\w*\b",
        "Instrument": r"\b(?:instruments?|cameras?|sensors?|radiometers?|diagnostics?)\b",
        "SourceFieldDefinition": r"\b(?:notes?|definitions?|meaning|units?|basis|alternatives|simultaneous|summary)\b",
        "Apparatus": r"\b(?:apparatus|hardware|instruments?|diagnostics?)\b",
    }
    return {role for role, pattern in patterns.items() if re.search(pattern, text, re.IGNORECASE)}


def proposition_records(anchor):
    """Return execution-time propositions without asserting new domain facts.

    Each record is a source sentence paired with immutable anchor provenance.
    These records are an alignment aid for coverage and verification; they are
    not additions to the RDF ontology or scientific interpretations.
    """
    records = []
    for span in anchor.get("spans", []):
        text = " ".join(str(span.get("text") or "").split())
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
            if sentence.strip()
        ] or ([text] if text else [])
        for index, sentence in enumerate(sentences[:32]):
            records.append(
                {
                    "id": f"{anchor['support_id']}:{span['evidence_id']}:{index}",
                    "text": sentence,
                    "support_id": anchor["support_id"],
                    "evidence_id": span["evidence_id"],
                    "source_id": anchor.get("source_id") or anchor.get("document_id"),
                    "document_id": anchor.get("document_id"),
                    "subject": anchor.get("subject"),
                    "conditions": anchor.get("conditions", []),
                    "epistemic_type": anchor.get("epistemic_type"),
                    "category": anchor.get("category"),
                }
            )
    return records


def generation_evidence(anchor):
    """One shared serialization for budget accounting and the provider boundary."""
    return {
        "support_id": anchor["support_id"],
        "category": anchor["category"],
        "epistemic_type": anchor["epistemic_type"],
        "source_role": anchor.get("source_role"),
        "source_roles": anchor.get("source_roles", []),
        **(
            {"annotation_reference_scope": anchor["annotation_reference_scope"]}
            if anchor.get("annotation_reference_scope")
            else {}
        ),
        **(
            {"annotation_record_ids": anchor["annotation_record_ids"]}
            if anchor.get("annotation_record_ids")
            else {}
        ),
        **(
            {"definition_scope": anchor["definition_scope"]}
            if anchor.get("definition_scope")
            else {}
        ),
        **(
            {
                "method_references": anchor.get("method_references", []),
                "source_sections": [
                    span["text"]
                    for span in anchor.get("spans", [])
                    if span.get("scope") == "section_heading"
                ],
            }
            if anchor.get("method_references") or anchor.get("scientific_sections")
            else {}
        ),
        **(
            {"source_record_references": anchor["source_record_references"]}
            if anchor.get("source_record_references")
            else {}
        ),
        "source_title": anchor.get("source_title"),
        "scientific_subjects": anchor.get("scientific_subjects", []),
        "investigation_identity": anchor.get("identity_context", ""),
        "document_id": anchor.get("document_id"),
        "subject": anchor.get("subject"),
        "text": anchor.get("context_window") or anchor["text"],
        "conditions": anchor.get("conditions", []),
        "typed_fields": anchor.get("typed_fields", []),
        "source_fact": anchor.get("deterministic_text"),
        "required_scope": anchor.get("required_scope", []),
        "information_need_ids": anchor.get("information_need_ids", []),
        "propositions": proposition_records(anchor),
    }


def information_needs(question, proposed=None):
    """Bound model search directions; offline clauses are routing, never ontology."""
    valid = []
    if isinstance(proposed, list):
        for row in proposed[:12]:
            if not isinstance(row, dict) or not isinstance(row.get("need"), str):
                continue
            need = row["need"].strip()[:600]
            terms = row.get("search_terms", [])
            if not need or not isinstance(terms, list):
                continue
            terms = [t[:120] for t in terms[:16] if isinstance(t, str) and t.strip()]
            valid.append({"id": f"need-{len(valid) + 1}", "need": need, "search_terms": terms})
    if not valid:
        clauses = re.split(r"[?;]|\b(?:and|versus)\b", question, flags=re.IGNORECASE)
        valid = [
            {"id": f"need-{i + 1}", "need": text.strip(), "search_terms": []}
            for i, text in enumerate(c for c in clauses if c.strip())
        ][:12]
    return valid or [{"id": "need-1", "need": question, "search_terms": []}]


def allocate_context(inventory, question, needs, budget):
    """Marginal content coverage within the actual serialized evidence budget.

    No source quota or experimental eligibility test is used. Repetition reduces
    priority, never changes evidence values or subjects. All decisions are saved.
    """
    stemmer = snowballstemmer.stemmer("english")

    def terms(text):
        return set(stemmer.stemWords(topic_terms(text)))

    from nasa_fire_ai.services.document_sections import TEST

    requested_methods = set(TEST.findall(question))
    question_terms = terms(question)
    requested_roles = desired_source_roles(question + " " + " ".join(n["need"] for n in needs))
    need_terms = [terms(n["need"] + " " + " ".join(n["search_terms"])) for n in needs]
    texts, text_terms, features = [], [], []
    for anchor in inventory:
        text = anchor.get("context_window") or anchor["text"]
        texts.append(text)
        identity_context = " ".join(
            [
                anchor.get("source_title") or "",
                *[
                    span["text"]
                    for span in anchor.get("spans", [])
                    if span.get("scope") == "section_heading"
                ],
                *anchor.get("source_aliases", []),
                *[
                    alias
                    for field in anchor.get("typed_fields", [])
                    for alias in field.get("aliases", [])
                ],
            ]
        )
        text_terms.append(terms(text + " " + identity_context))
        # Numeric variants of a repeated caption are still similar prose.
        # Values remain intact in text/spans; this affects routing priority only.
        tokens = re.findall(r"[a-z]{2,}", text.lower())
        feature_set = set(zip(tokens, tokens[1:], tokens[2:], tokens[3:]))
        if anchor.get("typed_fields"):
            # Different experimental records retain novelty even when their prose
            # headers repeat. This affects routing, never scientific verification.
            feature_set.add(
                (
                    "source_record",
                    *[span["evidence_id"] for span in anchor["spans"]],
                    *[field.get("id", "") for field in anchor["typed_fields"]],
                )
            )
        features.append(feature_set)
    frequencies = Counter(t for ts in text_terms for t in ts)
    weights = {t: 1 + math.log((1 + len(inventory)) / (1 + f)) for t, f in frequencies.items()}

    def overlap(ts, wanted):
        return sum(weights.get(t, 1) for t in ts & wanted) / max(
            1, sum(weights.get(t, 1) for t in wanted)
        )

    base, costs, need_matches = [], [], []
    for anchor, ts in zip(inventory, text_terms):
        matches = [ts & wanted for wanted in need_terms]
        ids = [n["id"] for n, matched in zip(needs, matches) if matched]
        anchor["information_need_ids"] = ids
        anchor["question_term_matches"] = sorted(ts & question_terms)
        scores = [overlap(ts, wanted) for wanted in need_terms]
        score = max(scores, default=0) + overlap(ts, question_terms)
        # Verified structured comparisons remain available without borrowing
        # documentary conditions. Their identity and constraints stay intact.
        if anchor.get("projection_verified") or anchor.get("epistemic_type") in {
            "query_condition_comparison",
            "comparison_coverage",
        }:
            score += 0.35
        if anchor.get("routing_scope") == "MATCH":
            score += 1
        elif anchor.get("routing_scope") == "DIFFERENT":
            score *= 0.15
        if requested_roles & set(anchor.get("source_roles", [])):
            score += 0.8 if anchor.get("routing_scope") != "DIFFERENT" else 0
        if requested_methods and anchor.get("method_references"):
            if requested_methods & set(anchor["method_references"]):
                score += 1.5
            else:
                score *= 0.15
        anchor["selection_score"] = score
        base.append(score)
        need_matches.append(matches)
        costs.append(len(json.dumps(generation_evidence(anchor), ensure_ascii=False)))

    selected, remaining, decisions = [], set(range(len(inventory))), {}
    used, represented, source_counts, page_counts = 2, set(), Counter(), Counter()
    covered = [Counter() for _ in needs]
    # Reserve one complete source section per explicitly requested procedure
    # before cheap isolated headings consume the context. This is source
    # navigation, not a determination that any answer need has been met.
    method_groups = {}
    for i, anchor in enumerate(inventory):
        if anchor.get("method_section_context") and anchor.get("section_subsection_count", 0):
            for method in requested_methods & set(anchor.get("method_references", [])):
                method_groups.setdefault((method, anchor.get("document_id")), []).append(i)
    seeds = {i for i, anchor in enumerate(inventory) if anchor.get("graph_context_id")}
    seeds.update(
        {
            max(
                indices,
                key=lambda i: (base[i], inventory[i]["section_subsection_count"], -costs[i]),
            )
            for indices in method_groups.values()
        }
    )
    for i in sorted(seeds, key=lambda i: (-base[i], inventory[i]["support_id"])):
        if used + costs[i] + 2 > budget:
            continue
        anchor = inventory[i]
        selected.append(anchor)
        remaining.remove(i)
        used += costs[i] + 2
        represented.update(features[i])
        for counts, matched in zip(covered, need_matches[i]):
            counts.update(matched)
        source_counts[anchor.get("source_id") or anchor.get("document_id")] += 1
        page_counts[tuple(s["evidence_id"] for s in anchor["spans"])] += 1
        decisions[anchor["support_id"]] = (
            "selected_source_backed_graph_context"
            if anchor.get("graph_context_id")
            else "selected_numbered_method_context"
        )
    while remaining:
        best, utility = None, 0
        for i in remaining:
            if used + costs[i] + 2 > budget or base[i] <= 0:
                continue
            anchor = inventory[i]
            novelty = len(features[i] - represented) / max(1, len(features[i]))
            marginal = sum(
                sum(weights.get(t, 1) / (1 + counts[t]) for t in matched)
                / max(1, sum(weights.get(t, 1) for t in wanted))
                for counts, matched, wanted in zip(covered, need_matches[i], need_terms)
            )
            page = tuple(s["evidence_id"] for s in anchor["spans"])
            source = anchor.get("source_id") or anchor.get("document_id")
            diversity = 1 / (1 + 0.12 * source_counts[source] + 0.18 * page_counts[page])
            value = (base[i] * 0.25 + marginal) * (0.08 + novelty) * diversity
            # Cost matters smoothly; no clipping of scientific text to fit.
            value /= math.sqrt(max(200, costs[i]))
            if value > utility or (
                value == utility
                and best is not None
                and anchor["support_id"] < inventory[best]["support_id"]
            ):
                best, utility = i, value
        if best is None:
            break
        remaining.remove(best)
        a = inventory[best]
        selected.append(a)
        used += costs[best] + 2
        represented.update(features[best])
        for counts, matched in zip(covered, need_matches[best]):
            counts.update(matched)
        source_counts[a.get("source_id") or a.get("document_id")] += 1
        page_counts[tuple(s["evidence_id"] for s in a["spans"])] += 1
        decisions[a["support_id"]] = "selected_marginal_coverage"
    for i in remaining:
        decisions[inventory[i]["support_id"]] = (
            "no_routing_match" if base[i] <= 0 else "context_budget_after_diversity_ranking"
        )
    selected_ids = {a["support_id"] for a in selected}
    routing = []
    for need in needs:
        candidate = [a["support_id"] for a in inventory if need["id"] in a["information_need_ids"]]
        supplied = [identity for identity in candidate if identity in selected_ids]
        routing.append(
            {
                **need,
                "candidate_support_ids": candidate,
                "supplied_support_ids": supplied,
                "status": "CANDIDATES_SUPPLIED" if supplied else "UNRESOLVED_ROUTING",
                "sufficiency": "Not established by terminology matching; inspect source content",
            }
        )
    return selected, {
        "context_characters": len(
            json.dumps([generation_evidence(a) for a in selected], ensure_ascii=False)
        ),
        "allocation_needs": routing,
        "selection_decisions": [
            {
                "support_id": a["support_id"],
                "evidence_ids": [s["evidence_id"] for s in a["spans"]],
                "information_need_ids": a["information_need_ids"],
                "reason": decisions[a["support_id"]],
            }
            for a in inventory
        ],
    }


def generation_comparison(comparison, question, properties):
    """Keep actual comparison rows and explicitly requested unavailable dimensions.

    The public comparison remains complete. Generation does not need dozens of
    unrelated empty columns, nor a second copy of every value in summary maps.
    """
    if not comparison:
        return comparison
    from nasa_fire_ai.services.semantic_support import aligned_properties

    requested = aligned_properties(question, properties)
    return {
        "run_ids": comparison.get("run_ids", []),
        "matrix": [
            row
            for row in comparison.get("matrix", [])
            if row.get("status") != "UNKNOWN" or row.get("dimension") in requested
        ],
        "unknown_or_unavailable_conditions": [
            dimension
            for dimension in comparison.get("unknown_or_unavailable_conditions", [])
            if dimension in requested
        ],
        "limitations": comparison.get("limitations", []),
        "epistemic_status": "Backend comparison of cited original values; not a source-reported causal finding.",
    }
