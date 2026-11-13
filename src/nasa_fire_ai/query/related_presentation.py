"""Deterministic presentation groups; never changes scientific eligibility."""

import json


def group_related(items, store):
    groups = {}
    for item in items:
        dimensions = item.get("relationship_explanation", {}).get("dimensions", [])
        signature = json.dumps(
            [(d["dimension"], d["status"], d.get("actual")) for d in dimensions], sort_keys=True
        )
        if not dimensions:
            signature = json.dumps(
                {
                    "classification": {
                        key: item.get(key, [])
                        for key in ("matches", "differs", "unknown", "invalid")
                    },
                    "reported_values": {
                        property_id: [
                            value.model_dump(mode="json")
                            for value in store.values(item["id"], property_id)
                        ]
                        for property_id in store.registry.properties
                    },
                },
                sort_keys=True,
            )
        key = (
            tuple(sorted(store.relations(item["id"], "belongsToInvestigation"))),
            tuple(sorted(store.relations(item["id"], "hasMaterial"))),
            signature,
        )
        group = groups.setdefault(
            key,
            {
                "investigations": list(key[0]),
                "materials": list(key[1]),
                "representative_id": item["id"],
                "candidate_ids": [],
                "evidence_ids": [],
                "applicability_limit": "Grouped by requested conditions only; other reported conditions may differ. Inspect complete candidates before transferring findings.",
            },
        )
        group["candidate_ids"].append(item["id"])
        group["evidence_ids"] = sorted(
            set(group["evidence_ids"]) | set(item.get("evidence_ids", []))
        )
    return {
        "policy": "investigation_material_and_requested_condition_signature",
        "scientific_relevance": "REVIEW_REQUIRED",
        "complete_candidate_count": len(items),
        "groups": list(groups.values()),
    }
