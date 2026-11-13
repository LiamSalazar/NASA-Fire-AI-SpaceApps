# Query interpreter corrective root-cause analysis

The input/output chain was inspected using persisted live minimal proposals:
raw proposal → deterministic registry resolution → validated QueryIntentV2.
No new model calls were needed to isolate this deterministic layer. Original
gold and historical predictions remain unchanged; the versioned receipts retain
all three representations.

Generic defects found and corrected:

- A canonical property alias could remain in `ambiguities` after successful
  property resolution.
- Model-labeled unknown terms such as an unregistered material could be kept as
  ambiguity instead of `unresolved_mentions`.
- A non-documentary information class such as Measurement could be returned as
  the query target despite run-level entity/property constraints.
- `ExperimentalRun` was listed as a target class and could also leak into
  `requested_information`; it is now excluded from that information slot.
- Topic words such as “suppression” and generic “safety” incorrectly implied
  the epistemic class SafetyImplication. Class aliases now identify the
  requested genre, not merely the scientific topic.
- Exact metric comparison was sensitive to retained raw expressions and empty
  qualifier objects. The semantic comparator now ignores those representational
  details while receipts preserve the raw expression.

Latest frozen re-resolution (`artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl`):
101 intents were schema/semantically valid. Exact semantic match was 11/41
standalone (26.8%), 10/30 historical composition (33.3%), and 28/30 new
composition (93.3%). The separate categories are not pooled as a single score.
Operation accuracy was 98/101. Requested-information set precision/recall/F1
was 34/34, 34/50, and 0.8095. Entity-constraint F1 was 0.957; property
constraint F1 0.763.

For numeric-bearing properties, values were 55/60, operators 58/60, units
58/60, and range endpoints 15/26. Explicit approximation/tolerance semantics
were preserved in 13/13 cases; comparison semantics were correct in 6/6
(SMALL_N). The 6 comparisons include only the gold cases explicitly requiring
comparison; they should not be read as broad comparison generalization. Range
performance and standalone exactness remain weak enough that QueryInterpreterV2
is not ready as the default interface.

No new LLM latency is reported: this pass re-resolved persisted live proposals.
Native service latency is measured separately. Fresh model-call latency and
human conversational-context correctness remain unmeasured in this repair pass.
