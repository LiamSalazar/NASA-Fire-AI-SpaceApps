"""Synthetic operational/scientific regressions; no live endpoint or invented NASA data."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import (
    ExtractionBudget,
    parse_stage_output,
    stage_schema,
)
from nasa_fire_ai.ingestion.document_structure import model_windows, structure
from nasa_fire_ai.ingestion.extraction_resources import ProviderEnvelope, segment_size, split_window
from nasa_fire_ai.llm.scientific_provider import ScientificTransportError, complete_scientific
from nasa_fire_ai.services.curation import CurationService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def service(tmp_path):
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, tmp_path / name)
    registry = EvidenceRegistry(tmp_path / "data/index/evidence.sqlite")
    yield CurationService(tmp_path, registry)
    registry.db.close()


def submitted(service, text):
    return service.submit(
        "Synthetic adaptive study", "Synthetic test only", [("source.md", text.encode())], "tester"
    )["package"]


def response(raw, finish="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=json.dumps(raw)), finish_reason=finish)
        ],
        usage=None,
    )


def test_twelve_experiments_are_not_capped_at_four(service):
    text = "\n".join(f"Run A{i} was tested at pressure {i} Pa." for i in range(1, 13))
    p = submitted(service, text)
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        if request["stage"] == "identity":
            for i in range(1, 13):
                a = next(a for a in request["source_anchors"] if f"Run A{i} " in a["quote"])
                result["entities"].append(
                    {
                        "key": f"a{i}",
                        "label": f"A{i}",
                        "class_id": "ExperimentalRun",
                        "study": "current",
                        "support": [a["id"]],
                    }
                )
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    runs = [
        r
        for r in result["package"]["scientific_extraction"]["records"]
        if r["kind"] == "entities"
        and r["proposal"]["class_id"] == "ExperimentalRun"
        and r["status"] == "SOURCE_SUPPORTED"
    ]
    assert len(runs) == 12
    assert all("maxItems" not in prop for prop in stage_schema("identity")["properties"].values())
    assert result["processing"]["status"] == "PARTIAL_MODEL_COVERAGE"
    assert (
        result["package"]["scientific_extraction"]["scientific_coverage"]["scientific_completeness"]
        != "COMPLETE"
    )


def test_density_sizing_preserves_full_original_partitions(service):
    text = "\n".join(
        f"Run A{i} was tested at pressure {i} Pa. A{i} flame extinguished." for i in range(400)
    )
    p = submitted(service, text)
    chars = segment_size(p, ExtractionBudget(), ProviderEnvelope())
    doc = structure(p, service.root, chars)
    assert "".join(s["text"] for s in doc["segments"]) == text
    window = model_windows(doc, chars)[0]
    children = split_window(window)
    assert children
    assert "".join(s["text"] for child in children for s in child["members"]) == "".join(
        s["text"] for s in window["members"]
    )
    for child in children:
        for segment in child["members"]:
            assert p["evidence"][0]["text"][segment["start"] : segment["end"]] == segment["text"]


def test_coherent_sparse_section_can_use_available_provider_context(service):
    text = "Coherent original scientific documentary context " * 500
    p = submitted(service, text)
    size = segment_size(p, ExtractionBudget(), ProviderEnvelope())
    assert size >= len(text) > 12000
    document = structure(p, service.root, size)
    assert len(model_windows(document, size)) == 1
    assert document["coverage"]["source_characters"] == len(text)


def test_pdf_heading_changes_do_not_force_tiny_model_calls():
    document = {
        "segments": [
            {
                "id": str(i),
                "source_id": "same-original",
                "text": "Original section text.",
                "section": f"Section {i}",
                "layout_heading": {"quote": f"Section {i}"},
            }
            for i in range(20)
        ]
    }
    windows = model_windows(document, 6000)
    assert len(windows) == 1
    assert len(windows[0]["members"]) == 20


@pytest.mark.parametrize("failure,retries", [("transient_server", 0), ("deadline", 2)])
def test_scientific_model_and_finite_fallback_preserve_task(service, failure, retries):
    p = submitted(service, "Run A1 was tested in microgravity.")
    c = Mock()
    requests = []

    def respond(**kwargs):
        requests.append(kwargs)
        if kwargs["model"] == "science-primary":
            raise ScientificTransportError(failure)
        payload = json.loads(kwargs["messages"][1]["content"])
        return response({k: [] for k in payload["schema"]["properties"]})

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"],
        Settings(
            root=service.root,
            nvidia_extraction_model="science-primary",
            nvidia_phase3_model="query-only",
            nvidia_science_fallback_models=("science-backup",),
        ),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(retries=retries, max_model_calls=2),
    )
    assert [r["model"] for r in requests] == ["science-primary", "science-backup"]
    assert requests[0]["messages"] == requests[1]["messages"]
    assert requests[0]["response_format"] == requests[1]["response_format"]
    assert result["processing"]["model"] == "science-primary"
    attempts = [
        json.loads(row[0])
        for row in service.registry.db.execute(
            "SELECT payload_json FROM phase3_cache WHERE cache_kind='scientific_document_attempt'"
        )
    ]
    assert {a["requested_model"] for a in attempts} == {"science-primary", "science-backup"}
    assert all("response_format" in a for a in attempts)


def test_original_pdf_image_identity_and_mutation_guard(service):
    import hashlib

    import pymupdf

    from nasa_fire_ai.ingestion.scientific_media import table_page_images

    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 50), "Synthetic derived table; fits, not measurements.")
        data = pdf.tobytes()
    p = service.submit(
        "Synthetic PDF", "Image provenance regression", [("source.pdf", data)], "tester"
    )["package"]
    sha = hashlib.sha256(data).hexdigest()
    tables = [{"input_sha256": sha, "physical_pdf_page": 1}]
    images, receipts = table_page_images(p, service.root, tables)
    assert len(images) == len(receipts) == 1
    assert images[0].startswith("data:image/png;base64,")
    assert receipts[0]["pdf_sha256"] == sha
    assert receipts[0]["physical_pdf_page"] == 1
    assert receipts[0]["evidence_id"] == p["evidence"][0]["evidence_id"]
    assert "data:image" not in json.dumps(receipts)
    (service.root / p["inputs"][0]["stored_input"]).write_bytes(b"changed synthetic test copy")
    with pytest.raises(ValueError, match="Original PDF changed"):
        table_page_images(p, service.root, tables)


def test_statement_omission_inventory_does_not_count_entity_as_recovery(service):
    from nasa_fire_ai.ingestion.scientific_coverage import statement_candidates

    p = submitted(service, "The results show that the specimen remained intact.")
    document = structure(p, service.root)
    missing = statement_candidates(p, document, {"records": []})
    assert len(missing) == 1
    assert missing[0]["state"] == "NOT_STRUCTURED"
    assert missing[0]["quote"] in p["evidence"][0]["text"]


def test_named_project_completion_is_explicit_execution_not_objective_completion(service):
    from nasa_fire_ai.ingestion.narrative_candidates import literal_candidates

    def candidate(text):
        p = submitted(service, text)
        segment = structure(p, service.root)["segments"][0]
        return next(
            e
            for e in literal_candidates(segment, service.semantic)["entities"]
            if e["label"] == "ABC"
        )

    assert (
        candidate("The ABC project completed combustion tests in reduced gravity.")["study"]
        == "current"
    )
    assert candidate("The ABC project achieved its scientific objectives.")["study"] == "unknown"
    assert (
        candidate("The previous ABC project completed combustion tests in reduced gravity.")[
            "study"
        ]
        == "cited"
    )


def test_transient_retry_and_attempt_journal_are_production_behavior(service, monkeypatch):
    p = submitted(service, "Run A1 was tested in microgravity.")
    c = Mock()
    count = [0]

    def respond(**kwargs):
        count[0] += 1
        if count[0] == 1:
            raise ScientificTransportError("rate_limit", retry_after="1")
        request = json.loads(kwargs["messages"][1]["content"])
        return response({k: [] for k in request["schema"]["properties"]})

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    delays = []
    monkeypatch.setattr("nasa_fire_ai.ingestion.document_extraction.time.sleep", delays.append)
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert result["processing"]["new_model_calls"] == 4
    assert delays and delays[0] >= 1
    journal = service.registry.db.execute(
        "SELECT payload_json FROM phase3_cache WHERE cache_kind='scientific_document_attempt'"
    ).fetchall()
    assert len(journal) == 4
    assert all(json.loads(r[0])["state"] == "FINISHED" for r in journal)
    assert (
        result["package"]["scientific_extraction"]["scientific_coverage"]["model_proposed_items"]
        == 0
    )
    assert (
        result["package"]["scientific_extraction"]["scientific_coverage"]["scientific_completeness"]
        == "NOT_ESTABLISHED"
    )


def test_long_provider_retry_after_defers_and_replays_without_sleep(service, monkeypatch):
    p = submitted(service, "Run A1 was tested in microgravity.")
    c = Mock()
    c.client.with_options.return_value.chat.completions.create.side_effect = (
        ScientificTransportError("rate_limit", retry_after="3600")
    )
    delays = []
    monkeypatch.setattr("nasa_fire_ai.ingestion.document_extraction.time.sleep", delays.append)
    first = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert first["processing"]["new_model_calls"] == 1
    assert not delays
    calls = first["processing"]["outcomes"]
    assert calls[0]["recovery"] == "DEFERRED_PROVIDER_RETRY_AFTER"
    replay = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert replay["processing"]["new_model_calls"] == 0
    assert c.client.with_options.return_value.chat.completions.create.call_count == 1


def test_output_limit_grows_and_keeps_grounded_items(service):
    p = submitted(service, "Run A1 was tested at pressure 20 Pa.")
    c = Mock()
    sizes = []

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        if request["stage"] == "identity":
            sizes.append(kwargs["max_tokens"])
            a = next(a for a in request["source_anchors"] if "Run A1" in a["quote"])
            result["entities"] = [
                {
                    "key": "a1",
                    "label": "A1",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [a["id"]],
                }
            ]
            if len(sizes) == 1:
                return response(result, "length")
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert len(sizes) == 2 and sizes[1] > sizes[0]
    assert (
        next(o for o in result["processing"]["outcomes"] if o["stage"] == "identity")["model"]
        == "COMPLETE"
    )
    assert (
        result["package"]["scientific_extraction"]["scientific_coverage"]["model_proposed_items"]
        >= 1
    )


def test_stream_prefix_and_long_request_timeout_are_retained():
    c = Mock()

    class Events:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            yield SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content='{"entities":['), finish_reason=None
                    )
                ],
                usage=None,
            )
            raise ScientificTransportError("network")

    c.client.with_options.return_value.chat.completions.create.return_value = Events()
    progress = []
    with pytest.raises(ScientificTransportError) as e:
        complete_scientific(
            c,
            model="synthetic",
            system="synthetic",
            payload="{}",
            max_tokens=16000,
            timeout=420,
            on_progress=lambda p, m: progress.append((p, m)),
        )
    assert e.value.content == '{"entities":['
    assert progress[-1][0] == e.value.content
    timeout = c.client.with_options.call_args.kwargs["timeout"]
    assert timeout.read == 420


def test_unrelated_json_layout_is_not_coerced_into_science():
    raw = {"identity": {"investigation": "invented"}, "propositions": [], "relationships": []}
    parsed, errors = parse_stage_output(json.dumps(raw), "identity", {}, "stop")
    assert not any(parsed.values())
    assert any(e["error"] == "UNEXPECTED_STAGE_KEY" for e in errors)


def test_schema_fallback_does_not_relax_source_verification(service, monkeypatch):
    p = submitted(service, "Run A1 was tested.")
    c = Mock()
    formats = []

    def respond(**kwargs):
        formats.append(kwargs["response_format"]["type"])
        if formats == ["json_schema"]:
            raise ScientificTransportError("request_rejected", metadata={"http_status": 400})
        request = json.loads(kwargs["messages"][1]["content"])
        return response({k: [] for k in request["schema"]["properties"]})

    monkeypatch.setattr("nasa_fire_ai.ingestion.document_extraction.time.sleep", lambda _: None)
    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert formats[:2] == ["json_schema", "json_object"]
    assert result["package"]["scientific_extraction"]["scientific_approval"] == "NONE"
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0


def test_compact_literal_statements_and_quarantine_do_not_starve_later_tasks(service):
    p = submitted(service, "Run A1 was tested. A1 flame extinguished.")
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        if request["stage"] == "identity":
            a = next(a for a in request["source_anchors"] if "Run A1" in a["quote"])
            result["entities"] = [
                {
                    "key": "run",
                    "label": "A1",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [a["id"]],
                },
                {
                    "key": "bad",
                    "label": "invented",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [a["id"]],
                },
            ]
        elif request["stage"] == "propositions":
            a = next(a for a in request["source_anchors"] if "A1 flame extinguished" in a["quote"])
            key = next(e["key"] for e in request["known_entities"] if e["label"] == "A1")
            result["statements"] = [
                {
                    "anchor": a["id"],
                    "epistemic": "measured_observation",
                    "subjects": [key],
                    "study": "current",
                }
            ]
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    prepared = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert prepared["processing"]["new_model_calls"] == 3
    records = prepared["package"]["scientific_extraction"]["records"]
    assert any(
        r["proposal"].get("label") == "invented" and r["status"] == "REJECTED" for r in records
    )
    assert any(
        r["kind"] == "statements"
        and r["proposal"]["text"] == "A1 flame extinguished."
        and r["status"] == "SOURCE_SUPPORTED"
        for r in records
    )
    replay = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert replay["processing"]["new_model_calls"] == 0
    assert replay["digest"] == prepared["digest"]


@pytest.mark.parametrize(
    "item",
    [
        {
            "anchor": "invented",
            "epistemic": "measured_observation",
            "subjects": [],
            "study": "current",
        },
        {
            "anchor": "A1",
            "epistemic": "measured_observation",
            "subjects": [],
            "study": "current",
            "text": "fabricated override",
        },
    ],
)
def test_compact_statement_cannot_create_or_override_source_support(item):
    anchors = {"A1": {"evidence_id": "synthetic", "quote": "Original source sentence.", "start": 0}}
    output, errors = parse_stage_output(
        json.dumps({"statements": [item], "quantities": [], "concepts": []}),
        "propositions",
        anchors,
        "stop",
    )
    assert not output["statements"]
    assert any(e["error"] == "INVALID_LITERAL_STATEMENT_REFERENCE" for e in errors)


@pytest.mark.parametrize("material_name", ["PMMA", "SyntheticPolymerQ"])
def test_scoped_material_heading_is_resolved_as_group_through_runtime(service, material_name):
    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page(width=1000)
    page.insert_text((50, 110), "Oxygen concentration was measured at 20%.", fontsize=12)
    page.insert_text((50, 50), f"Reduced-pressure results: {material_name}", fontsize=28)
    p = service.submit(
        "Synthetic scope study", "Synthetic fixture only", [("source.pdf", pdf.tobytes())], "tester"
    )["package"]
    pdf.close()
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        head = next(
            a
            for a in request["source_anchors"]
            if a["quote"] == f"Reduced-pressure results: {material_name}"
        )
        if request["stage"] == "identity":
            result["entities"] = [
                {
                    "key": "group",
                    "label": head["quote"],
                    "class_id": "ExperimentFamily" if request["focus"] else "Material",
                    "study": "current",
                    "support": [head["id"]],
                }
            ]
            result["entities"].append(
                {
                    "key": "material",
                    "label": material_name,
                    "class_id": "Material",
                    "study": "current",
                    "support": [head["id"]],
                }
            )
        elif request["stage"] == "propositions":
            group = next(
                e for e in request["known_entities"] if e["class_id"] == "ExperimentFamily"
            )
            a = next(a for a in request["source_anchors"] if "20%" in a["quote"])
            result["quantities"] = [
                {
                    "subject": group["key"],
                    "label": "Oxygen concentration",
                    "expression": "20",
                    "unit": "%",
                    "epistemic": "reported_quantity",
                    "support": [a["id"]],
                }
            ]
        else:
            group = next(
                e for e in request["known_entities"] if e["class_id"] == "ExperimentFamily"
            )
            material = next(
                e
                for e in request["known_entities"]
                if e["class_id"] == "Material" and e["label"] == material_name
            )
            result["relations"] = [
                {
                    "subject": group["key"],
                    "relation": "hasMaterial",
                    "object": material["key"],
                    "support": [head["id"]],
                }
            ]
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    records = result["package"]["scientific_extraction"]["records"]
    assert any(
        r["kind"] == "entities"
        and r["proposal"]["class_id"] == "ExperimentFamily"
        and r["status"] == "SOURCE_SUPPORTED"
        for r in records
    )
    assert all(
        r["status"] == "REJECTED"
        for r in records
        if r["proposal"].get("label") == f"Reduced-pressure results: {material_name}"
        and r["proposal"].get("class_id") == "Material"
    )
    assert any(r["kind"] == "quantities" and r["status"] == "SOURCE_SUPPORTED" for r in records)
    assert any(
        r["kind"] == "relations"
        and r["status"] == "SOURCE_SUPPORTED"
        and r["context_resolution"]["basis"] == "EXPLICIT_ORIGINAL_TYPED_GROUP_HEADER"
        for r in records
    )
    assert service.validate_originals(result["package"]) == []
    assert service.registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0] == 0


def test_nonempty_response_omission_triggers_targeted_quantity_recovery(service):
    p = submitted(
        service, "Run A1 was tested at pressure 20 Pa. A1 oxygen concentration was measured at 21%."
    )
    c = Mock()
    targeted = []

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        if request["stage"] == "identity":
            a = next(a for a in request["source_anchors"] if "Run A1" in a["quote"])
            result["entities"] = [
                {
                    "key": "a1",
                    "label": "A1",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [a["id"]],
                }
            ]
        elif request["stage"] == "propositions":
            focused = request["focus"] == "quantities"
            if focused:
                targeted.extend(request["unstructured_quantity_candidates"])
                assert request["unstructured_quantity_candidates"][0][
                    "source_applicable_subjects"
                ] == [request["known_entities"][0]["key"]]
            label, expression, unit = (
                ("oxygen concentration", "21", "%") if focused else ("pressure", "20", "Pa")
            )
            a = next(a for a in request["source_anchors"] if label in a["quote"])
            result["quantities"] = [
                {
                    "subject": request["known_entities"][0]["key"],
                    "label": label,
                    "expression": expression,
                    "unit": unit,
                    "epistemic": "reported_quantity" if focused else "experimental_configuration",
                    "support": [a["id"]],
                }
            ]
            if focused:
                result["quantities"] = [
                    {
                        "quantity_ref": request["unstructured_quantity_candidates"][0]["id"],
                        "subject": request["known_entities"][0]["key"],
                        "label": label,
                        "epistemic": "reported_quantity",
                    }
                ]
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    result = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=c
    )
    assert result["processing"]["new_model_calls"] == 4
    assert [q["original_expression_with_unit"] for q in targeted] == ["21%"]
    coverage = result["package"]["scientific_extraction"]["scientific_coverage"]
    assert coverage["detected_quantity_occurrences_structured"] == 2
    replay = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(max_model_calls=0),
    )
    assert replay["processing"]["new_model_calls"] == 0
    assert replay["digest"] == result["digest"]


def test_interrupted_package_save_recovers_validated_stages_without_new_calls(service, monkeypatch):
    from nasa_fire_ai.ingestion import document_extraction as module

    p = submitted(service, "Run A1 was tested at pressure 20 Pa.")
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        anchor = next(a["id"] for a in request["source_anchors"] if "Run A1" in a["quote"])
        if request["stage"] == "identity":
            result["entities"] = [
                {
                    "key": "run",
                    "label": "A1",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [anchor],
                }
            ]
        elif request["stage"] == "propositions":
            result["quantities"] = [
                {
                    "subject": request["known_entities"][0]["key"],
                    "label": "pressure",
                    "expression": "20",
                    "unit": "Pa",
                    "epistemic": "experimental_configuration",
                    "support": [anchor],
                }
            ]
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    save = service.save
    monkeypatch.setattr(service, "save", Mock(side_effect=OSError("Synthetic storage failure")))
    with pytest.raises(OSError, match="Synthetic storage failure"):
        service.prepare_scientific(
            p["id"], Settings(root=service.root), model_enabled=True, client=c
        )
    monkeypatch.setattr(service, "save", save)
    assert "scientific_extraction" not in service.get(p["id"])["package"]
    monkeypatch.setitem(
        module.STAGE_INSTRUCTIONS,
        "identity",
        module.STAGE_INSTRUCTIONS["identity"] + "\nReturn strict JSON.",
    )
    resumed = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(recovery_only=True, max_model_calls=0),
    )
    assert resumed["processing"]["new_model_calls"] == 0
    assert resumed["processing"]["recovered_cached_proposals_after_source_validation"] >= 2
    records = resumed["package"]["scientific_extraction"]["records"]
    assert any(
        r["kind"] == "quantities"
        and r["status"] == "SOURCE_SUPPORTED"
        and r["proposal"]["expression"] == "20"
        for r in records
    )
    other = submitted(service, "Run B2 was tested at pressure 99 Pa.")
    isolated = service.prepare_scientific(
        other["id"],
        Settings(root=service.root),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(recovery_only=True, max_model_calls=0),
    )
    assert not any(
        r["kind"] == "quantities" and r["proposal"]["expression"] == "20"
        for r in isolated["package"]["scientific_extraction"]["records"]
    )


def test_original_quantity_reference_cannot_change_values_units_or_support():
    anchors = {"A1": {"evidence_id": "synthetic", "quote": "A1 pressure was ~1.20 Pa.", "start": 0}}
    quantities = {"Q1": {"expression": "~1.20", "unit": "Pa", "support": ["A1"]}}
    item = {
        "quantity_ref": "Q1",
        "subject": "K1",
        "label": "pressure",
        "epistemic": "reported_quantity",
    }
    raw = json.dumps({"statements": [], "quantities": [item], "concepts": []})
    output, errors = parse_stage_output(raw, "propositions", anchors, "stop", quantities)
    assert not errors
    assert output["quantities"][0]["expression"] == "~1.20"
    assert output["quantities"][0]["unit"] == "Pa"
    assert output["quantities"][0]["support"][0]["quote"] == anchors["A1"]["quote"]
    for bad in (
        {**item, "quantity_ref": "invented"},
        {**item, "expression": "1.2"},
        {**item, "unit": "kPa"},
    ):
        rejected, errors = parse_stage_output(
            json.dumps({"statements": [], "quantities": [bad], "concepts": []}),
            "propositions",
            anchors,
            "stop",
            quantities,
        )
        assert not rejected["quantities"]
        assert any(e["error"] == "INVALID_ORIGINAL_QUANTITY_REFERENCE" for e in errors)
    partial = '{"quantities":[' + json.dumps(item) + ',{"quantity_ref":'
    salvaged, errors = parse_stage_output(partial, "propositions", anchors, "length", quantities)
    assert salvaged["quantities"][0]["expression"] == "~1.20"
    assert errors


def test_transport_records_served_model_reasoning_and_only_safe_headers():
    c = Mock()

    class Events:
        response = SimpleNamespace(
            headers={
                "x-request-id": "synthetic-request",
                "x-ratelimit-remaining-requests": "9",
                "authorization": "secret-must-not-persist",
            }
        )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            yield SimpleNamespace(
                model="synthetic-served",
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content='{"entities":[]}', reasoning="synthetic reasoning"
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(
                    model_dump=lambda: {
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    }
                ),
            )

    c.client.with_options.return_value.chat.completions.create.return_value = Events()
    result = complete_scientific(
        c,
        model="synthetic-requested",
        system="Synthetic test",
        payload="{}",
        max_tokens=32768,
        reasoning_budget=2048,
        timeout=600,
    )
    assert result.metadata["served_models"] == ["synthetic-served"]
    assert result.metadata["reasoning_characters"] > 0
    assert result.metadata["response_headers"] == {
        "x-request-id": "synthetic-request",
        "x-ratelimit-remaining-requests": "9",
    }
    assert "secret-must-not-persist" not in json.dumps(result.metadata)
    request = c.client.with_options.return_value.chat.completions.create.call_args.kwargs
    assert request["extra_body"]["reasoning_budget"] == 2048
    assert request["max_tokens"] == 32768


def test_split_recovery_is_replayable_with_zero_new_call_budget(service):
    text = (
        "Alpha specimen was tested.\n"
        + "Documentary background context. " * 45
        + "\nBeta specimen was tested."
    )
    p = submitted(service, text)
    c = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        result = {k: [] for k in request["schema"]["properties"]}
        if request["stage"] == "identity":
            local = [a for a in request["source_anchors"] if a["in_task"]]
            labels = [
                name
                for name in ("Alpha specimen", "Beta specimen")
                if any(name in a["quote"] for a in local)
            ]
            if len(labels) == 2:
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content='{"entities":['), finish_reason="length"
                        )
                    ],
                    usage=None,
                )
            result["entities"] = [
                {
                    "key": name,
                    "label": name,
                    "class_id": "Sample",
                    "study": "current",
                    "support": [next(a["id"] for a in local if name in a["quote"])],
                }
                for name in labels
            ]
        return response(result)

    c.client.with_options.return_value.chat.completions.create.side_effect = respond
    first = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(max_output_tokens=256),
    )
    assert {
        r["proposal"]["label"]
        for r in first["package"]["scientific_extraction"]["records"]
        if r["kind"] == "entities"
    } == {"Alpha specimen", "Beta specimen"}
    replay = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        client=c,
        budget=ExtractionBudget(max_output_tokens=256, max_model_calls=0),
    )
    assert replay["processing"]["new_model_calls"] == 0
    assert replay["digest"] == first["digest"]


def test_stream_deadline_interrupts_heartbeat_only_reader():
    import threading
    import time

    import httpx

    released = threading.Event()
    closed = []

    class Socket:
        def shutdown(self, _):
            released.set()

    class Events:
        response = SimpleNamespace(
            headers={},
            extensions={"network_stream": SimpleNamespace(get_extra_info=lambda _: Socket())},
            close=lambda: closed.append(True),
        )

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            # An SSE comment heartbeat does not yield an SDK event, and can reset
            # the HTTP inactivity timeout indefinitely. Simulate that pending read.
            released.wait(1)
            raise httpx.ReadError("closed socket")
            yield  # pragma: no cover

    client = Mock()
    client.client.with_options.return_value.chat.completions.create.return_value = Events()
    start = time.monotonic()
    with pytest.raises(ScientificTransportError) as failure:
        complete_scientific(
            client,
            model="synthetic",
            system="test",
            payload="{}",
            max_tokens=100,
            timeout=0.03,
            stream=True,
        )
    assert failure.value.kind == "deadline"
    assert time.monotonic() - start < 0.8
    assert released.is_set() and closed


def test_provider_stream_error_preserves_sanitized_diagnostic():
    import httpx
    from openai import APIError

    client = Mock()
    client.client.api_key = "synthetic-secret-value"
    client.client.with_options.return_value.chat.completions.create.side_effect = APIError(
        "provider stream error",
        request=httpx.Request("POST", "https://example.invalid"),
        body={"message": "backend error synthetic-secret-value"},
    )
    with pytest.raises(ScientificTransportError) as failure:
        complete_scientific(
            client,
            model="synthetic",
            system="test",
            payload="{}",
            max_tokens=100,
            timeout=120,
            stream=True,
        )
    assert failure.value.kind == "provider_stream_error"
    assert "[REDACTED]" in failure.value.metadata["provider_message"]
    assert "synthetic-secret-value" not in json.dumps(failure.value.metadata)
