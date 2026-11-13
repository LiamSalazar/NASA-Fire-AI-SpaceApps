import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.models import ConversationContext
from nasa_fire_ai.services import Phase3AssistantService

st.set_page_config(page_title="NASA Fire Safety Evidence", layout="wide")
st.title("NASA spacecraft fire-safety evidence assistant")
st.caption(
    "Evidence assistant only — scientists make scientific interpretation and applicability judgments."
)
mode = st.radio("Workspace", ["Scientific questions", "Incorporate research"], horizontal=True)
if mode == "Incorporate research":
    from curation_view import show_curation

    show_curation(Path(__file__).resolve().parents[1])
    st.stop()
if "phase3_context" not in st.session_state:
    st.session_state.phase3_context = None
q = st.text_input(
    "Natural-language query", placeholder="Find microgravity PMMA evidence below 18% O2"
)
if q:
    workspace = Path(__file__).resolve().parents[1]
    if os.getenv("NASA_CURATION_DEVELOPMENT", "false").lower() == "true":
        workspace = Path(os.environ.get("NASA_CURATION_WORKSPACE", str(workspace)))
    service = Phase3AssistantService(root=workspace, settings=Settings(root=workspace))
    response = service.answer_query(q, st.session_state.phase3_context)
    st.session_state.phase3_context = ConversationContext(
        current_investigation=(response.validated_intent.intent.investigations or [None])[0],
        current_material=(response.validated_intent.intent.materials or [None])[0],
        current_gravity=(response.validated_intent.intent.gravity_conditions or [None])[0],
        comparison_targets=response.validated_intent.comparison_targets,
        previous_intent=response.validated_intent,
    )
    st.subheader("Answer")
    st.write(response.rendered_answer)
    if response.validated_intent.clarification_required:
        st.info(response.validated_intent.clarification)
    if response.evidence_bundle.no_direct_evidence:
        st.warning(
            "No direct matching evidence was found in the indexed corpus. This is not a NASA-identified knowledge gap."
        )
    with st.expander("Interpreted query", expanded=False):
        st.json(response.validated_intent.model_dump())
    for label, items in [
        ("Direct Evidence", response.evidence_bundle.direct_evidence),
        ("Related Evidence", response.evidence_bundle.related_evidence),
        (
            "Safety Knowledge",
            response.evidence_bundle.nasa_conclusions
            + response.evidence_bundle.safety_implications
            + response.evidence_bundle.requirements
            + response.evidence_bundle.guidance
            + response.evidence_bundle.design_test_criteria,
        ),
        ("NASA-Identified Open Questions", response.evidence_bundle.nasa_identified_open_questions),
    ]:
        if items:
            st.subheader(label)
            st.write(items)
    st.subheader("Sources")
    for p in response.evidence_bundle.evidence_passages:
        with st.expander(f"{p['evidence_id']} · page {p['page']}"):
            st.write(p["text"])
            st.caption(
                f"Document: {p['document_id']} · section: {p.get('section') or 'not indexed'}"
            )
            if source := p.get("source_metadata"):
                st.caption(
                    f"NASA source: {source.get('title') or source.get('nasa_id') or source['source_id']}"
                )
                if source.get("url"):
                    st.link_button("Official NASA source", source["url"])
    with st.expander("Technical evidence and execution trace", expanded=False):
        st.json(response.evidence_bundle.model_dump())
        st.json(response.answer.model_dump())
        st.json(response.trace.model_dump())
