"""Scientific review widgets over the actual versioned backend, with no frontend schema copy."""

import os
from pathlib import Path

import httpx
import streamlit as st

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget
from nasa_fire_ai.llm.scientific_correction import generate_clarifications, interpret_correction
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy


def show_curation(root):
    st.subheader("Incorporate an investigation")
    development = os.getenv("NASA_CURATION_DEVELOPMENT", "false").lower() == "true"
    # No browser-entered identity grants authority. This is explicitly an isolated test deployment.
    workspace = Path(os.environ.get("NASA_CURATION_WORKSPACE", str(root)))
    if development and workspace.resolve() == Path(root).resolve():
        st.error(
            "Development review requires an isolated NASA_CURATION_WORKSPACE. Public publication is disabled."
        )
        return
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    principal = "development-scientist" if development else "local-draft-creator"
    policy = ReviewPolicy(frozenset({principal}) if development else frozenset(), development)
    service = CurationService(workspace, registry, policy)
    if development:
        st.info(
            "Isolated development review. Test approval does not represent NASA institutional authorization."
        )
    else:
        st.caption(
            "Preparation and review are available. Publication authority is supplied by deployment configuration."
        )
    with st.form("submit_investigation"):
        title = st.text_input("Investigation title")
        purpose = st.text_area("Scientific purpose")
        ntrs_id = st.text_input("Official NTRS citation ID (optional)")
        files = st.file_uploader(
            "Research materials",
            type=["pdf", "csv", "tsv", "txt", "md", "json"],
            accept_multiple_files=True,
        )
        model_extraction = st.checkbox(
            "Use configured Nemotron for scientific interpretation", value=False
        )
        limit_calls = st.checkbox("Set a session call ceiling", value=False)
        call_limit = st.number_input(
            "Session call ceiling", min_value=1, value=50, disabled=not limit_calls
        )
        submitted = st.form_submit_button("Prepare investigation")
    if submitted:
        try:
            saved = (
                service.submit_ntrs(ntrs_id.strip(), principal)
                if ntrs_id.strip()
                else service.submit(
                    title, purpose, [(f.name, f.getvalue()) for f in files], principal
                )
            )
            saved = service.prepare_scientific(
                saved["package"]["id"],
                Settings(root=workspace),
                model_enabled=model_extraction,
                budget=ExtractionBudget(max_model_calls=int(call_limit) if limit_calls else None),
            )
            st.session_state.curation_id = saved["package"]["id"]
            generated = generate_clarifications(
                service, saved["package"]["id"], Settings(root=workspace), model_enabled=False
            )
            st.session_state.curation_questions = {"digest": saved["digest"], **generated}
            st.success(
                "Previously submitted package opened."
                if saved.get("duplicate")
                else "Scientific draft prepared."
            )
        except (ValueError, UnicodeError, httpx.HTTPError) as error:
            st.error(str(error))
    packages = service.list_packages()
    if not packages:
        return
    titles = {p["package_id"]: service.get(p["package_id"])["package"]["title"] for p in packages}
    chosen = st.selectbox(
        "Prepared investigations",
        [p["package_id"] for p in packages],
        format_func=lambda x: titles[x],
        index=next(
            (
                i
                for i, p in enumerate(packages)
                if p["package_id"] == st.session_state.get("curation_id")
            ),
            0,
        ),
    )
    if st.button("Continue scientific preparation with configured Nemotron"):
        with st.spinner("Interpreting original evidence and resuming saved progress"):
            service.prepare_scientific(
                chosen,
                Settings(root=workspace),
                model_enabled=True,
                budget=ExtractionBudget(recovery_only=True),
            )
        st.rerun()
    current = service.get(chosen)
    package = current["package"]
    labels = {e["id"]: e["label"] for e in package["entities"]}
    readiness = service.validate(package)
    st.markdown("### " + package["title"])
    st.write(package["purpose"])
    st.caption(
        f"Prepared version {package['version']} · {len(package['entities'])} scientific entities · {len(package['relations'])} proposed relationships"
    )
    if package.get("scientific_extraction"):
        extraction = package["scientific_extraction"]
        with st.expander("Document coverage and scientific preparation"):
            st.json(extraction.get("scientific_coverage", {}))
            st.json(extraction["processing"])
            st.json(extraction["document"]["coverage"])
            st.json(extraction["document"]["limitations"])
            st.json(extraction["semantic_mappings"])
            st.json(extraction["review_requirements"])
        with st.expander("Original table attributes and detected scientific tables"):
            st.json(extraction.get("table_quantity_proposals", []))
            st.json(extraction.get("structured_table_records", []))
    st.success("Ready for exact-version approval") if readiness["ready"] else st.warning(
        f"{len(readiness['errors'])} decisions or validation blockers remain"
    )
    for heading, rows in [
        (
            "Experimental groups",
            [e for e in package["entities"] if e["class_id"] == "ExperimentFamily"],
        ),
        ("Runs and materials", package["entities"][1:]),
        ("Conditions and measurements", package["values"]),
        ("Observations, conclusions and open questions", package["statements"]),
    ]:
        with st.expander(heading):
            for row in rows:
                if "text" in row:
                    st.write(row["epistemic"].replace("_", " ").capitalize() + ": " + row["text"])
                    st.caption(
                        "Applies to: " + ", ".join(labels.get(x, x) for x in row.get("scope", []))
                    )
                elif "value" in row:
                    st.write(
                        labels.get(row["subject"], row["subject"])
                        + ": "
                        + row["property_id"]
                        + " = "
                        + str(row["value"]["raw_expression"])
                        + " "
                        + str(row["value"].get("reported_unit") or "")
                    )
                else:
                    st.write(row["label"] + " · " + row["class_id"])
    st.markdown("### Essential scientific clarifications")
    generated = st.session_state.get("curation_questions", {})
    review_questions = (
        generated.get("questions", readiness["questions"])
        if generated.get("digest") == current["digest"]
        else readiness["questions"]
    )
    for question in review_questions:
        with st.expander(question["question"], expanded=False):
            st.caption(f"One decision affects {question['affected_records']} records")
            for eid in question["evidence_ids"]:
                evidence = next(e for e in package["evidence"] if e["evidence_id"] == eid)
                st.write(evidence["text"])
                st.caption(f"{evidence['filename']} · location {evidence['page']}")
            options = {o["selection"]: o["label"] for o in question["options"]}
            selection = st.selectbox(
                "Scientific meaning",
                list(options),
                format_func=lambda x, meanings=options: meanings[x],
                key="select" + question["id"],
            )
            reason = st.text_input(
                "Scientific explanation (optional for a listed choice)",
                key="reason" + question["id"],
            )
            scopes = (
                st.multiselect(
                    "Applicable groups or runs (optional multiple selection)",
                    [x for x in question["alternatives"] if x != "documentary"],
                    format_func=lambda x: labels.get(x, x),
                    key="scopes" + question["id"],
                )
                if question["allows_multiple"]
                else []
            )
            reported_unit = (
                st.text_input(
                    "Unit explicitly stated in the source header (optional; % means percent)",
                    key="unit" + question["id"],
                )
                if question["kind"] == "mapping"
                else ""
            )
            if st.button("Apply this shared decision", key="apply" + question["id"]):
                try:
                    if selection == "another":
                        result = interpret_correction(
                            service,
                            chosen,
                            reason,
                            principal,
                            Settings(root=workspace),
                            model_enabled=True,
                        )
                        if "proposal" in result:
                            st.session_state.curation_preview = result["proposal"]
                            st.rerun()
                        else:
                            st.error("; ".join(result["blocked"]))
                        continue
                    service.clarification(
                        chosen,
                        question["id"],
                        scopes or selection,
                        reason,
                        principal,
                        reported_unit or None,
                    )
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    st.markdown("### Scientific connections")
    if package["decisions"]:
        with st.expander("Revise an earlier scientific decision"):
            prior = st.selectbox(
                "Earlier decision",
                list(package["decisions"]),
                format_func=lambda x: x.rsplit(":", 1)[-1],
            )
            explanation = st.text_input("Reason for revisiting this decision")
            if st.button("Reopen this decision in a new version"):
                try:
                    service.reopen_decision(chosen, prior, explanation, principal)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    # Graphviz is supported by Streamlit; no independent graph-editor framework.
    import json

    edges = package["relations"]
    graph = ["digraph study { rankdir=LR;"]
    for entity in package["entities"]:
        graph.append(json.dumps(entity["id"]) + " [label=" + json.dumps(entity["label"]) + "];")
    for reference in {r["object"] for r in edges} - set(labels):
        graph.append(
            json.dumps(reference)
            + " [label="
            + json.dumps(reference + " (published reference)")
            + ",style=filled,fillcolor=lightgray];"
        )
    for relation in edges:
        graph.append(
            json.dumps(relation["subject"])
            + " -> "
            + json.dumps(relation["object"])
            + " [label="
            + json.dumps(relation["relation"])
            + "];"
        )
    graph.append("}")
    st.graphviz_chart("\n".join(graph))
    templates = service.templates(package)
    with st.expander("Correct a relationship or scientific scope"):
        action = st.selectbox(
            "Correction",
            [
                "Add relationship",
                "Remove relationship",
                "Restrict statement scope",
                "Retain only as source context",
                "Correct entity label",
                "Refine scientific class",
                "Correct quantity meaning",
                "Correct source value",
                "Correct epistemic classification",
            ],
        )
        editable = (
            list(labels)
            + [s["id"] for s in package["statements"]]
            + [v["id"] for v in package["values"]]
        )
        subject = st.selectbox(
            "New scientific item",
            editable,
            format_func=lambda x: labels.get(
                x, next((s["text"][:80] for s in package["statements"] if s["id"] == x), x)
            ),
        )
        relation = st.selectbox(
            "Relationship meaning", [r["relation_id"] for r in templates["relations"]]
        )
        target = st.selectbox(
            "Related item",
            list(labels) + sorted(service.semantic.entities),
            format_func=lambda x: labels.get(x, x),
        )
        scope = st.multiselect("Applicable runs", list(labels), format_func=lambda x: labels[x])
        label = st.text_input("Corrected source label")
        scientific_class = st.selectbox("Scientific class", sorted(templates["classes"]))
        prop = st.selectbox("Quantity meaning", [p["property_id"] for p in templates["properties"]])
        corrected_expression = st.text_input("Corrected expression from the original source")
        corrected_unit = st.text_input("Original unit for the corrected value")
        epistemic_role = st.selectbox("Scientific status", list(templates["epistemic_roles"]))
        evidence_ids = st.multiselect(
            "Source support",
            [e["evidence_id"] for e in package["evidence"]],
            format_func=lambda x: next(
                e["filename"] + " · " + str(e["page"])
                for e in package["evidence"]
                if e["evidence_id"] == x
            ),
        )
        explanation = st.text_area("Explain the scientific correction")
        if st.button("Preview guided correction"):
            op = {"subject": subject, "evidence_ids": evidence_ids}
            if action in {"Add relationship", "Remove relationship"}:
                op.update(
                    action="add_relation" if action == "Add relationship" else "remove_relation",
                    relation=relation,
                    object=target,
                )
            elif action == "Restrict statement scope":
                op.update(action="scope", objects=scope)
            elif action == "Correct entity label":
                op.update(action="entity_label", label=label)
            elif action == "Refine scientific class":
                if subject in {s["id"] for s in package["statements"]}:
                    statement = next(s for s in package["statements"] if s["id"] == subject)
                    op.update(
                        action="classify_statement",
                        class_id=scientific_class,
                        epistemic=statement["epistemic"],
                    )
                else:
                    op.update(action="entity_class", class_id=scientific_class)
            elif action == "Correct quantity meaning":
                op.update(action="value", object=target, property_id=prop)
            elif action == "Correct source value":
                definition = service.property_registry(package).properties[prop]
                op.update(
                    action="value",
                    object=target,
                    property_id=prop,
                    value=service.parse_value(
                        corrected_expression, corrected_unit or None, definition
                    ),
                )
            elif action == "Correct epistemic classification":
                op.update(
                    action="classify_statement", **templates["epistemic_roles"][epistemic_role]
                )
            else:
                op.update(action="exclude", reason=explanation)
            try:
                st.session_state.curation_preview = service.preview_correction(
                    chosen, [op], explanation, principal
                )
            except (ValueError, StopIteration) as error:
                st.error(str(error))
    instruction = st.text_area(
        "Explain a correction naturally",
        placeholder="These observations apply only to runs S1 and S2.",
    )
    model_enabled = st.checkbox(
        "Interpret the scientific explanation", value=bool(Settings(root=workspace).nvidia_api_key)
    )
    if st.button("Preview natural-language correction"):
        result = interpret_correction(
            service, chosen, instruction, principal, Settings(root=workspace), model_enabled
        )
        if "proposal" in result:
            st.session_state.curation_preview = result["proposal"]
        else:
            st.error("; ".join(result["blocked"]))
            if result.get("follow_up"):
                st.write(result["follow_up"]["question"])
    preview = st.session_state.get("curation_preview")
    if preview and preview["package_id"] == chosen:
        st.write("Proposed scientific changes")
        for operation in preview["operations"]:
            st.write(
                operation["action"].replace("_", " ")
                + ": "
                + labels.get(operation["subject"], operation["subject"])
                + " → "
                + labels.get(
                    operation.get("object"),
                    str(operation.get("objects", operation.get("label", ""))),
                )
            )
        st.caption("Original instruction: " + preview["instruction"])
        if st.button("Approve and apply these corrections"):
            try:
                service.apply_correction(preview, principal)
                del st.session_state.curation_preview
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    with st.expander("Propose a scientific class or relationship"):
        import re

        draft_registry = service.property_registry(package)
        category = st.selectbox(
            "Scientific addition",
            ["class", "object_property"],
            format_func=lambda x: "Scientific class" if x == "class" else "Scientific relationship",
        )
        name = st.text_input("Scientific name")
        definition = st.text_area("Meaning and definition")
        purpose = st.text_area("Scientific purpose and why existing vocabulary is insufficient")
        known = sorted(draft_registry.target_classes | draft_registry.information_classes)
        parent = st.selectbox("Parent scientific class", known)
        source_kinds = st.multiselect("Permitted source kinds", known)
        target_kinds = st.multiselect("Permitted target kinds", known)
        scope_definition = st.text_input("Relationship applicability and evidence requirements")
        instances = st.text_input("Source-identified intended instances")
        aliases = st.text_input("Scientist-reviewed search expressions (comma-separated)")
        concept_support = st.multiselect(
            "Original evidence supporting this meaning",
            [e["evidence_id"] for e in package["evidence"]],
        )
        if st.button("Prepare compatible scientific addition"):
            proposal = {
                "kind": category,
                "id": re.sub(r"[^A-Za-z0-9]", "", name),
                "name": name,
                "definition": definition,
                "purpose": purpose,
                "why_existing_insufficient": purpose,
                "evidence_ids": concept_support,
                "impact": "Compatible addition; existing identities retained",
                "constraints": {},
            }
            if category == "class":
                proposal.update(
                    parent=parent,
                    intended_instances=[x.strip() for x in instances.split(",") if x.strip()],
                    query_terms=[x.strip() for x in aliases.split(",") if x.strip()],
                )
            else:
                proposal.update(
                    domain=source_kinds,
                    range=target_kinds,
                    direction="source_to_target",
                    scope=scope_definition,
                    evidence_requirements=scope_definition,
                    transitive=False,
                )
            try:
                service.propose_extension(chosen, proposal, principal)
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    with st.expander("Propose a new scientific quantity"):
        concept = st.text_input("Quantity name")
        definition = st.text_area("Scientific definition")
        insufficiency = st.text_area("Why established quantities are insufficient")
        unit = st.text_input("Compatible canonical unit")
        dimension = st.text_input("Physical dimension")
        domain = st.selectbox(
            "Applies to", [c for c, m in templates["classes"].items() if m.get("target")]
        )
        support = st.multiselect(
            "Quantity source support", [e["evidence_id"] for e in package["evidence"]]
        )
        if st.button("Prepare quantity extension"):
            try:
                service.propose_extension(
                    chosen,
                    {
                        "property": {
                            "property_id": concept,
                            "dimension": dimension,
                            "canonical_unit": unit,
                            "aliases": [],
                        },
                        "definition": definition,
                        "why_existing_insufficient": insufficiency,
                        "domain": domain,
                        "range": "numeric",
                        "evidence_ids": support,
                        "impact": "Compatible addition; existing identities and contracts retained",
                        "validation_contract": "SemanticRegistry.validate",
                    },
                    principal,
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        for extension in package["extensions"]:
            st.write(extension["definition"])
            if (
                not extension["approved"]
                and development
                and st.button(
                    "Authorize this compatible quantity addition",
                    key=extension.get("id", extension.get("property", {}).get("property_id")),
                )
            ):
                service.approve_extension(
                    chosen,
                    extension.get("id", extension.get("property", {}).get("property_id")),
                    principal,
                )
                st.rerun()
    if st.button("Regenerate after corrections"):
        service.regenerate(package)
        service.save(package, principal)
        st.rerun()
    with st.expander("Original source evidence"):
        for evidence in package["evidence"]:
            st.caption(evidence["filename"] + " · " + str(evidence["page"]))
            st.write(evidence["text"])
    st.markdown("### Publication impact")
    st.download_button(
        "Download portable research package",
        service.export_package(chosen),
        file_name="research-package.zip",
        mime="application/zip",
    )
    preview_question = st.text_input("Preview a scientific question about this draft")
    if st.button("Ask using this draft") and preview_question:
        try:
            st.write(service.preview_query(chosen, preview_question).rendered_answer)
        except (ValueError, LookupError) as error:
            st.error("Resolve structural blockers before preview: " + str(error))
    st.write(
        f"Adds or amends {len(package['entities'])} entities, {len(package['relations'])} relationships and {len(package['values'])} condition records. Published reference entities remain unchanged. The reviewed version becomes available to ordinary scientific queries."
    )
    st.caption("Exact prepared version digest: " + current["digest"])
    approve = st.checkbox(
        "I reviewed the scientific meaning and authorize this exact prepared version",
        key="approval-" + current["digest"],
    )
    if st.button(
        "Approve and incorporate", disabled=not (development and readiness["ready"] and approve)
    ):
        try:
            receipt = service.approve_and_publish(chosen, current["digest"], principal)
            st.success("Approved knowledge activated in the existing scientific system.")
            st.json(receipt)
        except (ValueError, PermissionError, RuntimeError) as error:
            st.error(str(error))
    with st.expander("Review diagnostics"):
        st.json(readiness)
        st.json(templates)
