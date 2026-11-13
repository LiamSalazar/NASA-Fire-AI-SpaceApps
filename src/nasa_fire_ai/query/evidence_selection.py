"""Class/authority/topic selection; lexical context never establishes scientific identity."""

import os
import re


def words(text):
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def antecedent_context(trace, registry, limit=3):
    """Recover documentary context without approving questions or physical page numbers."""
    from nasa_fire_ai.ingestion.source_spans import recover_span

    found = {}
    for item in trace:
        if "question_content_requires_source_antecedent_review" not in item["excluded"]:
            continue
        for eid in item["evidence_ids"]:
            passage = registry.resolve(eid)
            found[eid] = {**passage, "context_status": "ANTECEDENT_REVIEW_REQUIRED"}
            source = registry.source_metadata(eid)["source_id"]
            rows = registry.db.execute(
                "SELECT p.evidence_id,p.text FROM passages p JOIN documents d USING(document_id) "
                "WHERE d.source_id=? AND p.text LIKE '%?%' ORDER BY p.evidence_id",
                (source,),
            )
            for row in rows:
                try:
                    recover_span(row["text"], passage["text"])
                except ValueError:
                    continue
                found[row["evidence_id"]] = {
                    **registry.resolve(row["evidence_id"]),
                    "context_status": "ANTECEDENT_REVIEW_REQUIRED",
                }
                if len(found) >= limit:
                    return list(found.values())
    return list(found.values())


def select_information(intent, query, store, evidence_registry):
    metadata = store.registry.class_metadata
    requested = {
        c
        for c in intent.requested_information
        if metadata.get(c, {}).get("information") and not metadata[c].get("documentary")
    }
    policy = store.registry.selection_policy
    if not requested:
        return [], []
    administrative = set(policy.get("stop_words", []))
    for meta in metadata.values():
        for term in meta.get("query_terms", []):
            administrative.update(words(term))
    topics = words(query) - administrative
    for constraint in intent.entity_constraints:
        topics.update(words(constraint.entity_id))
    for operand in intent.comparison.operands if intent.comparison else []:
        topics.update(words(operand))
    contexts = {}
    candidates = []
    selected = []
    for subject in store.entities():
        classes = store.classes(subject, include_ancestors=True)
        if not classes.intersection(requested):
            continue
        refs = store.evidence(subject)
        source_ok = not intent.source_constraints or bool(
            store.sources(subject).intersection(intent.source_constraints)
        )
        evidence_ok = bool(refs) and all(evidence_registry.resolve(e) is not None for e in refs)
        payload = store.payload(subject)
        text = " ".join(
            str(payload.get(k) or "")
            for k in (
                "text",
                "description",
                "normalized_text",
                "scope_applicability",
                "source_section",
            )
        )
        own = words(text)
        # A typed structured quantity has explicit scientific scope through its
        # hasMeasurement edge; absence of prose is not absence of run identity.
        from nasa_fire_ai.query.native import classify_native, measurement_scope

        structured_scope = measurement_scope(subject, store)
        if structured_scope != subject and intent.entity_constraints:
            status, _ = classify_native(subject, intent, store, related_policy=True)
            if status in {"DIRECT", "RELATED"}:
                own.update(topics)
        contextual = set()
        # Exact source/page links provide documentary context, not new KG facts.
        for eid in refs:
            p = evidence_registry.resolve(eid)
            if not p:
                continue
            key = (p["document_id"], p.get("page"))
            if key not in contexts:
                rows = evidence_registry.db.execute(
                    "SELECT text,section FROM passages WHERE document_id=? AND page IS ?", key
                ).fetchall()
                contexts[key] = words(
                    " ".join(str(r[0] or "") + " " + str(r[1] or "") for r in rows)
                )
            contextual.update(contexts[key])
        overlap = topics & (own | contextual)
        # Class-only queries have no topic filter. Topic queries need explicit
        # lexical/context overlap; no similarity-based scientific equivalence.
        topic_ok = not topics or bool(overlap)
        excluded = []
        if not source_ok:
            excluded.append("source_constraint")
        if not evidence_ok:
            excluded.append("missing_evidence")
        if not topic_ok:
            excluded.append("no_topic_overlap")
        # An anaphoric reference does not establish the content of a scientific question.
        # Preserve the historical path unless source enrichment is explicitly enabled.
        if (
            os.getenv("SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED", "false").lower() == "true"
            and any(metadata.get(c, {}).get("reject_anaphoric_only") for c in classes)
            and re.search(r"\b(?:these|those|such) questions\b", text, re.IGNORECASE)
            and "?" not in text
        ):
            excluded.append("question_content_requires_source_antecedent_review")
        if intent.clarification_required or intent.unresolved_mentions:
            excluded.append("unresolved_query")
        own_overlap = topics & own
        context_overlap = overlap - own
        # Same-page topic overlap is discovery context, not applicability of
        # the statement itself. An observation needs its own topical support.
        if topics and not own_overlap:
            excluded.append("topic_only_in_documentary_context")
        for topic, forms in policy.get("topical_wordforms", {}).items():
            if words(query).intersection(forms) and not own.intersection(forms):
                excluded.append(f"requested_topic_absent_from_statement_scope:{topic}")
        score = 3 * len(own_overlap) + len(context_overlap)
        topic_coverage = len(overlap) / len(topics) if topics else 1.0
        candidates.append(
            {
                "subject": subject,
                "classes": sorted(classes),
                "authority": "CANONICAL_REVIEWED",
                "evidence_ids": refs,
                "evidence_sources": [
                    {
                        "evidence_id": eid,
                        "location": {
                            "page": (passage := evidence_registry.resolve(eid)).get("page"),
                            "section": passage.get("section"),
                        },
                        "source": evidence_registry.source_metadata(eid),
                    }
                    for eid in refs
                    if evidence_registry.resolve(eid)
                ],
                "topic_terms": sorted(topics),
                "own_overlap": sorted(own_overlap),
                "context_overlap": sorted(context_overlap),
                "score": score,
                "topic_coverage": topic_coverage,
                "excluded": excluded,
            }
        )
        if not excluded:
            selected.append((score, subject))
    selected.sort(key=lambda x: (-x[0], x[1]))
    selected_rank = {subject: rank for rank, (_, subject) in enumerate(selected, 1)}
    for candidate in candidates:
        candidate["ranking"] = selected_rank.get(candidate["subject"])
        candidate["eligible"] = candidate["ranking"] is not None
        candidate["eligibility_reason"] = (
            "reviewed_class_source_evidence_and_topic_scope_passed"
            if candidate["eligible"]
            else ";".join(candidate["excluded"])
        )
    return [s for _, s in selected], candidates
