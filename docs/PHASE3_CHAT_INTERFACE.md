# Phase 3 chat interface

The Streamlit view calls `Phase3AssistantService`, not retrieval code directly. It presents a natural-language answer, no-direct warning, clarification when needed, nearby evidence IDs, expandable source passages, interpreted intent, evidence bundle, final answer, and execution trace. Follow-up context is restricted to validated query referents. Technical detail is collapsed by default.
