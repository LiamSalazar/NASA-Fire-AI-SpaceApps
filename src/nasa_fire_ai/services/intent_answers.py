"""Document and terminology answer contracts; no experimental equivalence inference."""

import re


def render_intent_answer(bundle, detail_level="standard", *, registry=None):
    meta = bundle.retrieval_metadata
    conceptual = meta.get("conceptual_query", {})
    intent = meta.get("query_intent_v2", {})
    bibliographic = "Publication" in intent.get("targets", []) and not conceptual.get("active")
    if not conceptual.get("active") and not bibliographic:
        return None
    from nasa_fire_ai.services.scientific_synthesis import documentary_statements, normalize

    verifications = []

    def allowed(text, ids):
        if registry is None:
            return True
        valid = bool(ids) and all(
            (source := registry.resolve(eid))
            and normalize(text) in normalize(source.get("text", ""))
            for eid in ids
        )
        verifications.append(
            {
                "status": "SUPPORTED_WITH_LIMITATIONS" if valid else "UNSUPPORTED",
                "evidence_ids": ids,
                "support_spans": [{"text": text, "evidence_id": eid} for eid in ids],
                "limitations": ["Documentary wording; no experimental applicability inferred"],
            }
        )
        meta["claim_verification"] = verifications
        meta["final_emission_gate"] = {
            "enforced": True,
            "blocked": sum(v["status"] == "UNSUPPORTED" for v in verifications),
            "contract": "exact-documentary-span",
        }
        return valid

    if conceptual.get("active"):
        lines = [
            "The retrieved documentation does not establish that these terms are fully equivalent."
        ]
        for entity, aliases in conceptual.get("registry_matches", {}).items():
            lines.append(
                f"Approved registry terminology: {entity} ({', '.join(aliases)}). This is a vocabulary lookup, not a scientific equivalence claim."
            )
        for relation in conceptual.get("approved_relations", []):
            if registry is not None and not all(
                registry.resolve(eid) for eid in relation.get("evidence_ids", [])
            ):
                continue
            lines.append(
                f"{relation['subject']} — {relation['predicate']} — {relation['object']} [{', '.join(relation['evidence_ids'])}]"
            )
        rows = documentary_statements(bundle)
        for row in rows[:2]:
            if not allowed(row["text"], row["evidence_ids"]):
                continue
            lines.append(
                f"Documented wording: “{normalize(row['text'])}” [{', '.join(row['evidence_ids'])}]"
            )
        if not rows:
            terms = set(re.findall(r"[a-z]{4,}", meta.get("scientific_question", "").lower())) - {
                "does",
                "mean",
            }
            snippets = []
            for passage in bundle.evidence_passages:
                for line in passage.get("text", "").splitlines():
                    if 10 <= len(line.strip()) <= 240 and terms.intersection(
                        set(re.findall(r"[a-z]{4,}", line.lower()))
                    ):
                        snippets.append((line.strip(), passage["evidence_id"]))
            for text, eid in snippets[:3]:
                if not allowed(text, [eid]):
                    continue
                lines.append(f"Source terminology: “{text}” [{eid}].")
        if not rows and not snippets:
            lines.append(
                "No suitable terminology passage was recovered; a broader material-family relationship requires an authoritative source and review."
            )
        meta["scientific_synthesis"] = {
            "selected_claims": [],
            "contract": "conceptual-documentary-v1",
            "independent_scientific_review": None,
        }
        return "\n\n".join(lines)
    # Publication ranking uses documentary search candidates rather than every
    # graph publication admitted by an unconstrained publication target.
    candidate_ids = set(meta.get("selection_trace", {}).get("documentary_candidates", []))
    passages = [
        p
        for p in bundle.evidence_passages
        if not candidate_ids or p["evidence_id"] in candidate_ids
    ]
    query = meta.get("scientific_question", "")
    terms = {
        w
        for w in re.findall(r"[a-z]{5,}", query.lower())
        if w not in {"which", "publications", "discuss", "technique"}
    }
    passages.sort(
        key=lambda p: -len(terms & set(re.findall(r"[a-z]{5,}", p.get("text", "").lower())))
    )
    lines, seen = [], set()
    for p in passages:
        source = p.get("source_metadata") or p.get("source", {})
        sid = source.get("nasa_id") or source.get("source_id", p.get("document_id"))
        if sid in seen or not terms.intersection(
            set(re.findall(r"[a-z]{5,}", p.get("text", "").lower()))
        ):
            continue
        from nasa_fire_ai.services.investigation import (
            publication_topic_supported,
            topic_applicable,
        )

        if not publication_topic_supported(
            query, p.get("text", "") + " " + source.get("title", "")
        ):
            continue
        seen.add(sid)
        text = normalize(p.get("text", ""))
        # Full sentences containing a requested topic explain relevance without
        # inferring experimental conclusions from publication identity.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        relevant = next(
            (
                s
                for s in sentences
                if topic_applicable(query, s)
                and terms.intersection(set(re.findall(r"[a-z]{5,}", s.lower())))
                and len(s) <= 900
            ),
            "Matching topic wording occurs in the cited source passage.",
        )
        if not allowed(relevant, [p["evidence_id"]]):
            continue
        lines.append(
            f"- {source.get('title', p.get('document_id', 'NASA source'))}: {relevant} [{p['evidence_id']}] {source.get('url', '')}"
        )
        if len(lines) >= (8 if detail_level == "technical" else 5):
            break
    meta["scientific_synthesis"] = {
        "selected_claims": [],
        "contract": "bibliographic-documentary-v1",
        "publications_returned": len(lines),
        "independent_scientific_review": None,
    }
    return (
        "NASA publications recovered for this topic:\n\n" + "\n".join(lines)
        if lines
        else "No matching publication was recovered in this indexed corpus. This does not establish absence from the NASA literature."
    )
