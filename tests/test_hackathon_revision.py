"""Versioned scientific corrections, with real original NASA table cells."""

import shutil
from pathlib import Path

import pytest

from nasa_fire_ai.ingestion.hackathon import TABLES, build_snapshot, verify_snapshot
from nasa_fire_ai.ingestion.structured_provenance import table_cells
from nasa_fire_ai.services.search import ScientificSearchService

ROOT = Path(__file__).resolve().parents[1]


def test_mapped_columns_exist_in_original_psi_headers():
    for accession, (identifier, material, mappings) in TABLES.items():
        source = ROOT / f"data/raw/hackathon-psi/{accession}_experimental_table.csv"
        headers, _, _ = table_cells(source, ROOT)
        assert {identifier, material, *mappings}.issubset({header.strip() for header in headers})


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    snapshot = tmp_path_factory.mktemp("revision") / "snapshot"
    build_snapshot(ROOT, snapshot)
    service = ScientificSearchService(snapshot, ROOT)
    yield service
    service.close()


def test_reported_results_are_separate_from_conditions(engine):
    store = engine.store
    assert store.relations("psi-98-S1", "hasMeasurement") == {"psi-98-S1-value-9"}
    record = store.payload("psi-98-S1-value-9")
    assert record["qualifiers"]["source_header"] == "Burn Time (s)"
    assert record["value"]["canonical_value"] == 420
    assert store.payload("psi-69-20CAL08-value-11")["qualifiers"]["original_value"] == "0.89"
    assert "Measurement" in store.classes("psi-69-20CAL08-value-11")
    assert "Measurement" not in store.classes("psi-69-20CAL08-value-10")


def test_original_acme_source_cells_keep_initial_and_approximate_conditions(engine):
    store = engine.store
    oxygen = store.value_records("psi-159-21088A1", "OxygenConcentration")
    assert [(row["qualifiers"]["context"], row["value"].raw_expression) for row in oxygen] == [
        ("initial", "0.3939"),
        ("final", "0.389822946"),
    ]
    pressure = store.value_records("psi-159-21088A1", "Pressure")
    assert len(pressure) == 1
    assert pressure[0]["value"].reported_unit == "bar"
    assert pressure[0]["value"].approximate


@pytest.mark.parametrize("identifier", ["NASA-STD-6001", "NASA-STD-6001B", "ABC-1234"])
def test_document_numbers_are_not_magnitudes(engine, identifier):
    intent = engine.interpret(identifier + " requirements")
    assert "unparsed_numeric_request" not in intent.unresolved_mentions
    assert not intent.property_constraints


def test_campaign_membership_does_not_prove_extinction_relevance(engine):
    result = engine.search("FLEX extinction", limit=3)
    assert not result.direct
    assert not result.related
    assert result.discovery


def test_secondary_identifiers_and_investigator_attribution_are_source_queryable(engine):
    from nasa_fire_ai.ingestion.structured_provenance import table_cells

    headers, rows, _ = table_cells(
        ROOT / "data/raw/hackathon-psi/PSI-69_experimental_table.csv", ROOT
    )
    row = dict(zip(headers, rows[0], strict=False))
    identifier = row["FLEX Test #"].strip()
    records = engine.source_records("psi-69", identifier)
    assert records["items"]
    assert row["FLEX Identifier"].strip() in {
        record["record"]["reported_identifier"] for record in records["items"]
    }
    intent = engine.interpret("FLEX test number " + identifier)
    assert intent.subject_ids
    assert "unparsed_numeric_request" not in intent.unresolved_mentions
    b1 = engine.source_records("psi-25", "B1")["items"][0]
    assert any(
        field["property_id"] == "source:principal_investigator_label" for field in b1["fields"]
    )


def test_physical_quantities_do_not_become_coincident_original_identifiers(engine):
    intent = engine.interpret("CFI oxygen concentration 1207 ppm")
    assert not intent.subject_ids
    assert any(
        constraint.property_id == "OxygenConcentration"
        for constraint in intent.property_constraints
    )


def test_reported_findings_keep_original_context_and_campaign_relationships(engine):
    store = engine.store
    assert "acme-cld-finding" in store.relations("psi-21", "hasReportedFinding")
    assert "preliminary" in store.payload("acme-cld-finding")["text"].lower()
    assert store.relations("acme-cld-finding", "hasFindingContext") == {"acme-cld-method"}
    assert all(engine.registry.resolve(eid) for eid in store.evidence("acme-cld-finding"))
    assert len(store.relations("acme-iss-2017-2022", "hasInvestigation")) == 6
    bre = store.payload("acme-bre-finding")["text"]
    assert bre.startswith("It was found that low-momentum")
    assert "arc discharges" not in bre
    assert "Table A.6" in store.payload("bass-pi-matrix-scope")["text"]


def test_portable_snapshot_and_rebuild(engine, tmp_path):
    root = tmp_path / "relocated"
    # Copy the authorized corpus and contracts, not user databases or credentials.
    for directory in ("data/raw", "domain", "ontology", "src"):
        shutil.copytree(ROOT / directory, root / directory)
    shutil.copytree(ROOT / "artifacts/hackathon", root / "artifacts/hackathon")
    output = tmp_path / "rebuilt"
    rebuilt = build_snapshot(root, output)
    assert rebuilt["artifacts"] == engine.manifest["artifacts"]
    assert rebuilt["snapshot_id"] == engine.manifest["snapshot_id"]
    service = ScientificSearchService(output, root)
    try:
        evidence = service.search("Saffire I airflow 20 cm/s").direct[0]["evidence"][0]
        assert Path(evidence["raw_file"]).is_relative_to(root)
        assert Path(evidence["raw_file"]).is_file()
        original = root / "data/raw/hackathon-psi/PSI-98_experimental_table.csv"
        original.write_bytes(original.read_bytes() + b"\n")
        with pytest.raises(ValueError, match="checksum"):
            verify_snapshot(output, root)
    finally:
        service.close()


def test_source_documented_abbreviation_preserves_investigation_scope(engine):
    intent = engine.interpret("CFI-G 21088A1 peak burner temperature")
    assert intent.subject_ids
    assert {c.entity_id for c in intent.entity_constraints} == {"psi-159"}
    assert all(
        engine.store.relations(subject, "belongsToInvestigation") == {"psi-159"}
        for subject in intent.subject_ids
    )


def test_graph_candidates_cover_inverse_sample_links_and_both_scopes(engine):
    result = engine.search(
        "How do Saffire-I and Saffire-III report specimen dimensions and flow direction?",
        limit=20,
        research=True,
    )
    rows = result.documentary + result.discovery
    sources = {row["source"]["source_id"] for row in rows}
    assert {"psi-98", "psi-100"} <= sources
    assert any(
        route["strategy"] == "graph_record_fields"
        for row in rows
        if row["source"]["source_id"] in {"psi-98", "psi-100"}
        for route in row.get("retrieval_routes", [])
    )


def test_publication_references_have_question_dependent_routing(engine):
    def metadata_rows(result):
        return [
            row
            for row in result.candidates
            if "publication" in row.get("source", {}).get("source_type", "").lower()
            and "metadata" in row.get("source", {}).get("source_type", "").lower()
        ]

    scientific = engine.search("FLEX camera radiometer diagnostics", limit=20, research=True)
    bibliography = engine.search("FLEX publication references", limit=20, research=True)
    content_metadata = metadata_rows(scientific)
    requested_metadata = metadata_rows(bibliography)
    assert content_metadata and requested_metadata
    assert all(row["publication_metadata_routing_weight"] < 1 for row in content_metadata)
    assert all(row["publication_metadata_routing_weight"] == 1 for row in requested_metadata)
    assert any(
        row["source"]["source_id"] == "ntrs-20150023456"
        for row in scientific.documentary + scientific.discovery
    )


def test_documentary_identifiers_come_from_evidence_backed_graph_scope(engine):
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    result = engine.search("PSI-60 modeling methods", limit=40, research=True)
    service = ConversationService(engine)
    anchors, _ = service._inventory([result], question="PSI-60 modeling methods")
    anchor = next(
        a
        for a in anchors
        if a.get("source_id") == "documentation-psi-60" and "image processing" in a["text"]
    )
    assert anchor["scientific_subjects"] == ["psi-60"]
    assert "psi-60" in anchor["source_aliases"]
    source_sentence = anchor["text"].split(". ")[0].rstrip(".") + "."
    optimistic = SimpleNamespace(check=lambda premise, hypothesis: {"supported": True})
    positive = "For PSI-60, " + source_sentence
    assert verify_paraphrase(positive, [anchor], engine.registry, optimistic)["supported"]
    assert not verify_paraphrase(
        positive.replace("PSI-60", "PSI-62"), [anchor], engine.registry, optimistic
    )["supported"]


def test_explicit_record_supplies_structured_evidence_without_lexical_candidates(engine):
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.structured_alignment import complete_record_fields

    question = "For SAME-R test 51a, give inlet velocity, duration and net aging time."
    result = engine.search(question, limit=5)
    assert result.intent.subject_ids == ["psi-101-51a"]
    isolated = result.model_copy(update={"documentary": [], "discovery": [], "candidates": []})
    service = ConversationService(engine)
    selected, _ = service._inventory([isolated], question=question)
    inventory = {anchor["support_id"]: anchor for anchor in selected}
    assert any(anchor.get("structured_record_id") for anchor in selected)
    needs = [
        {"need": "recorded " + name + " for SAME-R test 51a"}
        for name in ["inlet velocity", "duration", "net aging time"]
    ]
    proposals = complete_record_fields(
        needs,
        inventory,
        engine,
        [],
        {"psi-101-51a"},
        SimpleNamespace(check=lambda premise, hypothesis: {"supported": False}),
    )
    properties = {
        engine.store.payload(inventory[p["support_ids"][0]]["structured_record_id"])["property_id"]
        for p in proposals
    }
    assert {"AirflowVelocity", "source:test_duration", "source:net_aging_time"} <= properties


def test_calendar_lookup_uses_original_complete_session_components(engine):
    from nasa_fire_ai.query.record_identity import source_calendar_date

    intent = engine.interpret("For BRE on 20 February 2019, give burner size and ignition count.")
    assert intent.subject_ids
    assert all(
        source_calendar_date(subject, engine.store).isoformat() == "2019-02-20"
        for subject in intent.subject_ids
    )
    for subject in intent.subject_ids:
        assert engine.store.relations(subject, "belongsToInvestigation") == {"psi-20"}
        assert all(
            engine.registry.resolve(eid)["source_cells"] for eid in engine.store.evidence(subject)
        )


def test_reported_shared_apparatus_has_source_backed_instrument_routes(engine):
    store = engine.store
    shared = store.relations("psi-107", "usesApparatus") & store.relations(
        "psi-106", "usesApparatus"
    )
    assert "spice-slice-shared-hardware" in shared
    components = store.relations("spice-slice-shared-hardware", "hasInstrument")
    assert len(components) == 3
    for component in components:
        assert "Instrument" in store.classes(component)
        assert component in store.relations("psi-107", "usesInstrument")
        assert component in store.relations("psi-106", "usesInstrument")
        payload = store.payload(component)
        assert "no serial physical-device identity" in payload["identity_scope"]
        assert all(
            payload["text"] in engine.registry.resolve(eid)["text"]
            for eid in store.evidence(component)
        )
    assert store.registry.relations["hasInstrument"].domain == ["Apparatus"]
    assert store.registry.relations["hasInstrument"].range == ["Instrument"]
