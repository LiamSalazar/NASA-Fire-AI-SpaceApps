"""Source applicability negatives and repairs; all fixtures explicitly synthetic."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import test_curation

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.scientific_proposals import deterministic_propositions
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.scientific_correction import interpret_correction

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "artifacts/phase3c_rc_baseline/correction_negative_cases.json").read_text()
)["cases"]
REASONS = {
    "gravity_add_conflict": "Conflicting hasGravityCondition",
    "gravity_replace_contradiction": "Source row gravity attribution",
    "group_replace_wrong_row": "Source row group attribution",
    "measurement_wrong_run": "Quantity subject/table-row membership",
    "measurement_numeric_fabrication": "Reported numeric value differs",
    "conclusion_scope_wrong_run": "Statement applicability/table-row membership",
    "observation_scope_wrong_run": "Statement applicability/table-row membership",
    "hypothesis_to_observation": "Uncertain source statements",
    "observation_to_conclusion": "Source-backed statement role",
}


@pytest.fixture
def curator(tmp_path):
    yield from test_curation.curator.__wrapped__(tmp_path)


@pytest.fixture
def audited(curator):
    data = (
        b"Run,Group,Material,Gravity,Airflow (cm/s),Observation,Conclusion,Hypothesis,Open question\n"
        b"A1,B,PMMA,microgravity,20,Nomex extinguished in two of four tests.,The authors conclude extinction occurred for A1 only.,A hypothesis remains untested.,Further research is required.\n"
        b"A2,C,PMMA,normal-gravity,10,PMMA flame continued to burn.,The authors conclude flame persistence for A2 only.,A hypothesis remains untested.,Further research is required.\n"
    )
    saved = curator.submit(
        "Explicit synthetic RC adversarial fixture",
        "Not NASA data",
        [("synthetic.csv", data)],
        "test-scientist",
    )
    saved = curator.clarification(
        saved["package"]["id"],
        "table-role:" + saved["package"]["tables"][0]["id"],
        "ExperimentalRun",
        "Synthetic executed-run fixture",
        "test-scientist",
    )
    assert curator.validate(saved["package"])["ready"]
    return saved


@pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
def test_exact_audit_negatives_and_model_parity(curator, audited, case):
    package = audited["package"]
    name = case["case"]
    if "operations" not in case:
        changed = copy.deepcopy(package)
        next(s for s in changed["statements"] if "two of four" in s["text"])["text"] = (
            "Nomex extinguished in all four tests."
        )
        result = curator.validate(changed)
        assert not result["ready"]
        assert any("not an original source span" in e for e in result["errors"])
        return
    # Exact baseline IDs and operations, not unrelated unknown endpoints.
    ops = case["operations"]
    with pytest.raises(ValueError, match=REASONS[name]):
        curator.preview_correction(
            package["id"], ops, "Synthetic negative " + name, "test-scientist"
        )
    adapter = MagicMock()
    adapter.client.with_options.return_value.chat.completions.create.return_value = SimpleNamespace(
        usage=None,
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "operations": ops,
                            "needs_clarification": False,
                            "clarification_question": None,
                        }
                    )
                )
            )
        ],
    )
    with patch(
        "nasa_fire_ai.llm.scientific_correction.NvidiaStructuredClient", return_value=adapter
    ):
        result = interpret_correction(
            curator,
            package["id"],
            "Synthetic negative " + name,
            "test-scientist",
            Settings(root=curator.root, nvidia_api_key="mock-only"),
            True,
        )
    assert result["receipt"]["outcome"] == "REJECTED_CORRECTION"
    assert any(REASONS[name] in reason for reason in result["blocked"])
    assert curator.get(package["id"])["digest"] == audited["digest"]


@pytest.mark.parametrize(
    "case",
    [
        c
        for c in CASES
        if c["case"]
        in {
            "gravity_replace_contradiction",
            "group_replace_wrong_row",
            "measurement_wrong_run",
            "conclusion_scope_wrong_run",
            "observation_scope_wrong_run",
            "observation_to_conclusion",
        }
    ],
    ids=lambda c: c["case"],
)
def test_alternate_mutation_cannot_approve_or_publish(curator, audited, case):
    pid = audited["package"]["id"]
    curator.approve_and_publish(pid, audited["digest"], "test-scientist")
    forged = {
        "package_id": pid,
        "base_digest": audited["digest"],
        "instruction": "Bypass forged preview",
        "operations": case["operations"],
        "validation": {"ready": True},
    }
    with pytest.raises(ValueError, match=REASONS[case["case"]]):
        curator.apply_correction(forged, "test-scientist")
    changed = copy.deepcopy(audited["package"])
    curator.apply_operations(changed, case["operations"])
    saved = curator.save(changed, "test-scientist")
    assert not curator.validate(saved["package"])["ready"]
    with pytest.raises(ValueError, match="Publication blocked"):
        curator.approve(pid, saved["digest"], "test-scientist")
    with pytest.raises((ValueError, PermissionError)):
        curator.publish(pid, saved["digest"], "test-scientist")
    changed["corrections"].append({"operations": case["operations"]})
    curator.regenerate(changed)
    assert not curator.validate(changed)["ready"]
    assert (
        curator.registry.db.execute(
            "SELECT digest FROM research_active WHERE package_id=?", (pid,)
        ).fetchone()[0]
        == audited["digest"]
    )


@pytest.mark.parametrize(
    "kind", ["gravity", "group", "measurement", "observation", "conclusion", "role"]
)
def test_original_evidence_repairs_wrong_initial_extraction(curator, audited, kind):
    package = copy.deepcopy(audited["package"])
    runs = [e["id"] for e in package["entities"] if e["class_id"] == "ExperimentalRun"]
    if kind in {"gravity", "group"}:
        relation = "hasGravityCondition" if kind == "gravity" else "belongsToExperimentFamily"
        first = next(
            r for r in package["relations"] if r["subject"] == runs[0] and r["relation"] == relation
        )
        original = copy.deepcopy(first)
        first["object"] = next(
            r["object"]
            for r in package["relations"]
            if r["subject"] == runs[1] and r["relation"] == relation
        )
        ops = [{"action": "remove_relation", **first}, {"action": "add_relation", **original}]
    elif kind == "measurement":
        value = package["values"][0]
        value["subject"] = runs[1]
        ops = [{"action": "value", "subject": value["id"], "object": runs[0]}]
    else:
        statement = next(
            s
            for s in package["statements"]
            if s["scope"] == [runs[0]]
            and s["epistemic"]
            == ("author_reported_conclusion" if kind == "conclusion" else "measured_observation")
        )
        if kind == "role":
            statement.update(class_id="NASAConclusion", epistemic="hypothesis")
            ops = [
                {
                    "action": "classify_statement",
                    "subject": statement["id"],
                    "class_id": "ReportedObservation",
                    "epistemic": "measured_observation",
                    "evidence_ids": statement["evidence_ids"],
                }
            ]
        else:
            statement["scope"] = [runs[1]]
            ops = [{"action": "scope", "subject": statement["id"], "objects": [runs[0]]}]
    curator.save(package, "test-scientist")
    assert not curator.validate(package)["ready"]
    for _ in range(3):
        preview = curator.preview_correction(
            package["id"],
            ops,
            "Repair against original source, not initial extraction",
            "test-scientist",
        )
        assert preview["validation"]["ready"]
        current = curator.apply_correction(preview, "test-scientist")
        assert curator.validate(current["package"])["ready"]
        curator.regenerate(current["package"])
        current = curator.save(current["package"], "test-scientist")
        curator.approve_and_publish(package["id"], current["digest"], "test-scientist")
        assert project_legacy(curator.root, curator.registry).entities()
        curator.rollback(package["id"], "test-scientist")
        curator.publish(package["id"], current["digest"], "test-scientist")


def test_original_identity_and_column_metadata_tampering(curator, audited):
    for field, value in [
        ("document_id", "another-document"),
        ("page", 99),
        ("locator", {"row": 99}),
    ]:
        package = copy.deepcopy(audited["package"])
        package["evidence"][0][field] = value
        assert not curator.validate(package)["ready"]
    package = copy.deepcopy(audited["package"])
    next(c for c in package["tables"][0]["columns"] if c["label"] == "Observation")[
        "statement_role"
    ] = "conclusion"
    curator.regenerate(package)
    assert any("Source-backed statement role" in e for e in curator.validate(package)["errors"])


def test_material_and_quantity_unit_source_binding(curator, audited):
    package = copy.deepcopy(audited["package"])
    relation = next(r for r in package["relations"] if r["relation"] == "hasMaterial")
    original = copy.deepcopy(relation)
    relation["object"] = "SIBAL Fabric"
    bad = curator.save(package, "test-scientist")
    assert any("Source row material" in e for e in curator.validate(bad["package"])["errors"])
    preview = curator.preview_correction(
        package["id"],
        [{"action": "remove_relation", **relation}, {"action": "add_relation", **original}],
        "Original cell explicitly reports PMMA",
        "test-scientist",
    )
    corrected = curator.apply_correction(preview, "test-scientist")
    assert curator.validate(corrected["package"])["ready"]
    quantity = corrected["package"]["values"][0]
    with pytest.raises(ValueError, match="expression/unit differs from original source cell"):
        curator.preview_correction(
            package["id"],
            [
                {
                    "action": "value",
                    "subject": quantity["id"],
                    "value": {**quantity["value"], "reported_unit": "m/s"},
                    "evidence_ids": quantity["evidence_ids"],
                }
            ],
            "Same numeric expression is not the original unit",
            "test-scientist",
        )


def test_procedural_instruction_is_normative_not_observation(curator):
    text = "Flame jets and sparks emanating from the specimen during combustion shall be observed and recorded."
    proposals = deterministic_propositions(
        [{"text": text, "evidence_id": "synthetic"}], curator.semantic
    )
    assert proposals[0]["class_id"] == "Requirement"
    saved = curator.submit(
        "Synthetic procedure", "Not NASA data", [("procedure.txt", text.encode())], "test-scientist"
    )
    package = saved["package"]
    statement = package["statements"][0]
    statement.update(
        class_id="ReportedObservation", epistemic="measured_observation", scope=[package["id"]]
    )
    result = curator.validate(package)
    assert not result["ready"]
    assert any("Normative source instruction" in e for e in result["errors"])


def test_context_role_review_and_ambiguous_narrative(curator):
    text = "The following is the author's interpretation of the outcome.\nThe material continued to burn under the tested conditions."
    saved = curator.submit(
        "Synthetic author context",
        "Not NASA data",
        [("context.txt", text.encode())],
        "test-scientist",
    )
    package = saved["package"]
    statement = package["statements"][0]
    op = {"action": "scope", "subject": statement["id"], "objects": [package["id"]]}
    with pytest.raises(ValueError, match="Scientific review required"):
        curator.preview_correction(
            package["id"], [op], "Unreviewed applicability", "test-scientist"
        )
    question = next(q for q in curator.questions(package) if q["kind"] == "scope")
    curator.clarification(
        package["id"],
        question["id"],
        package["id"],
        "The submitted source describes its own tested conditions",
        "test-scientist",
    )
    op = {
        "action": "classify_statement",
        "subject": statement["id"],
        "class_id": "NASAConclusion",
        "epistemic": "author_reported_conclusion",
        "evidence_ids": statement["evidence_ids"],
    }
    with pytest.raises(ValueError, match="author-conclusion role"):
        curator.preview_correction(
            package["id"], [op], "Author context requires review", "test-scientist"
        )
    spans = [
        {
            "evidence_id": statement["evidence_ids"][0],
            "text": "The following is the author's interpretation of the outcome.",
        }
    ]
    with pytest.raises(PermissionError):
        curator.review_statement_role(
            package["id"],
            statement["id"],
            "author_reported_conclusion",
            spans,
            "Explicit contextual author attribution",
            "unauthorized",
        )
    curator.review_statement_role(
        package["id"],
        statement["id"],
        "author_reported_conclusion",
        spans,
        "Author identifies the following outcome as the interpretation; original scope preserved",
        "test-scientist",
    )
    preview = curator.preview_correction(
        package["id"], [op], "Reviewed contextual author attribution", "test-scientist"
    )
    assert preview["validation"]["ready"]


def test_procedural_table_role_can_be_corrected_from_source(curator):
    saved = curator.submit(
        "Synthetic procedural table",
        "Not NASA data",
        [("procedure.csv", b"Run,Observation\nR1,Flame jets shall be observed and recorded.\n")],
        "test-scientist",
    )
    package = saved["package"]
    saved = curator.clarification(
        package["id"],
        "table-role:" + package["tables"][0]["id"],
        "ExperimentalRun",
        "Explicit synthetic executed-run context; instruction remains normative",
        "test-scientist",
    )
    statement = saved["package"]["statements"][0]
    assert not curator.validate(saved["package"])["ready"]
    preview = curator.preview_correction(
        package["id"],
        [
            {
                "action": "classify_statement",
                "subject": statement["id"],
                "class_id": "Requirement",
                "epistemic": "normative_requirement",
                "evidence_ids": statement["evidence_ids"],
            }
        ],
        "Original shall instruction is normative, despite initial observation extraction",
        "test-scientist",
    )
    current = curator.apply_correction(preview, "test-scientist")
    assert curator.validate(current["package"])["ready"]
