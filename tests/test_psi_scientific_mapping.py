"""Original PSI values, epistemic scope and registry-only cell lineage."""

import json
from pathlib import Path

import pytest

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import import_table, make_store
from nasa_fire_ai.ingestion.psi_scientific import cell_value
from nasa_fire_ai.ingestion.structured_provenance import round_trip
from nasa_fire_ai.query.native import NS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def mapped(tmp_path_factory):
    import csv

    store = make_store(ROOT)
    registry = EvidenceRegistry(
        tmp_path_factory.mktemp("psi-deep") / "evidence.sqlite", evidence_root=ROOT
    )
    campaigns = {
        r["accession"]: r
        for r in csv.DictReader((ROOT / "data/raw/hackathon-team/data/clean/campaigns.csv").open())
    }
    counts = {}
    for n in (107, 39, 22, 21, 20, 23, 106, 68, 47):
        accession = f"PSI-{n}"
        counts[n] = import_table(
            store,
            registry,
            ROOT,
            ROOT / f"data/raw/hackathon-psi/{accession}_experimental_table.csv",
            campaigns[accession],
        )
    yield store, registry, counts
    registry.db.close()


def test_official_publication_membership_is_searchable_metadata_not_scientific_findings(tmp_path):
    from types import SimpleNamespace

    from nasa_fire_ai.ingestion.hackathon import passage, register_source
    from nasa_fire_ai.ingestion.psi_scientific import import_documentation
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    store = make_store(ROOT)
    registry = EvidenceRegistry(tmp_path / "bibliography.sqlite", evidence_root=ROOT)
    try:
        sources = import_documentation(
            store,
            registry,
            ROOT / "data/raw/hackathon-psi/PSI-39_metadata.json",
            passage,
            register_source,
        )
        references = store.relations("psi-39", "hasPublicationReference")
        assert len(references) == 7
        assert any(source["depth"] == "C" for source in sources)
        for reference in references:
            assert store.payload(reference)["metadata_only"]
            eid = store.evidence(reference)[0]
            original = registry.resolve(eid)
            assert "/publications/" in original["structured_location"]["json_pointer"]
            assert (
                registry.source_metadata(eid)["source_type"]
                == "NASA PSI publication catalogue metadata"
            )
        eid = store.evidence(next(iter(references)))[0]
        source = registry.resolve(eid)
        anchor = {
            "text": source["text"],
            "spans": [{"evidence_id": eid, "text": source["text"]}],
            "category": "DISCOVERY",
            "epistemic_type": "catalogue_metadata",
            "conditions": [],
        }
        assert not verify_paraphrase(
            "The catalogue proves an experimental effect.",
            [anchor],
            registry,
            SimpleNamespace(check=lambda p, h: {"supported": True}),
        )["supported"]
    finally:
        registry.db.close()


def test_all_nine_tables_have_scientific_fields_and_honest_record_scopes(mapped):
    store, _, counts = mapped
    assert (
        sum(
            sum(
                v
                for k, v in c.items()
                if k
                in {
                    "ExperimentalRun",
                    "ExperimentalSession",
                    "ConfigurationSummary",
                    "SourceRecord",
                }
            )
            for c in counts.values()
        )
        == 678
    )
    assert all(c["curated_values"] > 0 for c in counts.values())
    assert "ExperimentalSession" in store.classes("psi-21-record-2")
    assert "ExperimentalRun" not in store.classes("psi-21-record-2")
    assert len(store.relations("psi-68", "hasSourceRecord")) == 8
    assert not store.relations("psi-68", "hasRun")
    assert not store.relations("psi-107", "hasRun")
    description = next(iter(store.relations("psi-21-record-3", "hasMaterialDescription")))
    assert store.payload(description)["text"] == "40% CH5"
    assert "Material" not in store.classes(description)
    assert store.evidence(description) == store.evidence("psi-21-record-3")


def test_real_source_values_units_and_instrument_capacity(mapped):
    store, _, _ = mapped
    assert store.values("psi-107-record-2", "source:nozzle_diameter")[
        0
    ].canonical_value == pytest.approx(0.0016002)
    assert store.values("psi-107-record-2", "source:fuel_mass_flow")[
        0
    ].canonical_value == pytest.approx(1.971e-6)
    assert store.values("psi-39-record-2", "Pressure")[0].canonical_value == 101325
    assert store.values("psi-39-record-2", "source:initial_nitrogen")[0].canonical_value == 0.79
    assert store.values("psi-21-record-2", "source:fuel_mfc_capacity")[
        0
    ].canonical_value == pytest.approx(0.1 * 0.001 / 60)
    assert not store.values("psi-21-record-2", "source:fuel_mass_flow")
    assert store.values("psi-22-record-2", "source:mesh_polarity")[0].reported_value == "negative"
    assert store.values("psi-23-record-2", "source:ignition_count")[0].canonical_value == 13
    assert store.values("psi-20-record-2", "source:ignition_count")[0].canonical_value == 10
    assert (
        "CH4" in store.values("psi-106-record-2", "source:material_description")[0].reported_value
    )
    assert (
        "P-Trak" in store.values("psi-47-record-2", "source:hardware_description")[0].reported_value
    )


def test_configuration_alternatives_are_not_simultaneous_runs(mapped):
    store, _, _ = mapped
    assert [v.canonical_value for v in store.values("psi-68-record-2", "OxygenConcentration")] == [
        0.17,
        0.21,
        0.25,
        0.3,
    ]
    assert (
        store.values("psi-68-record-2", "source:ambient_temperature")[0].canonical_value == 298.15
    )
    diameter = store.values("psi-68-record-2", "source:initial_droplet_diameter")[0]
    assert (diameter.lower, diameter.upper) == (0.0015, 0.005)
    assert not store.relations("psi-68-record-2", "hasMeasurement")


def test_every_curated_value_roundtrips_exact_original_cell(mapped):
    store, registry, _ = mapped
    rows = registry.db.execute(
        "SELECT v.value_id,c.locator_json FROM value_cells v JOIN structured_cells c ON v.evidence_id=c.evidence_id AND v.column_ordinal=c.column_ordinal"
    ).fetchall()
    assert len(rows) > 4000
    for row in rows:
        locator = json.loads(row["locator_json"])
        assert round_trip(locator, ROOT)
        assert (
            store.payload(row["value_id"])["qualifiers"]["original_value"]
            == locator["original_value"]
        )
    assert all(registry.resolve(str(e)) for e in store.graph.objects(None, NS.evidenceRef))


def test_duplicates_remain_distinct_source_records(mapped):
    store, _, _ = mapped
    assert store.evidence("psi-107-record-2") != store.evidence("psi-107-record-3")
    assert store.values("psi-107-record-2", "AirflowVelocity") == store.values(
        "psi-107-record-3", "AirflowVelocity"
    )


def test_quantity_parser_preserves_ambiguity_and_rejects_wrong_dimensions():
    field = {"unit": "mm"}
    with pytest.raises(ValueError):
        cell_value("10 s", field)
    with pytest.raises(ValueError):
        cell_value("fan number 42", field)
    assert cell_value(".7 cm", field).reported_unit == "cm"
    with pytest.raises(ValueError):
        cell_value("1; or missing", field)


def test_original_cell_projection_repairs_wording_without_accepting_altered_values(mapped):
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.structured_facts import structured_fact

    store, registry, _ = mapped
    fact = structured_fact("psi-39-record-3-field-6-0", store, registry)
    assert fact and "1207" in fact["text"] and "0.21 fraction" in fact["text"]
    original = registry.resolve(fact["evidence_ids"][0])
    anchor = {
        "support_id": "projection",
        "text": fact["text"],
        "deterministic_text": fact["text"],
        "structured_record_id": fact["record_id"],
        "projection_verified": True,
        "spans": [{"evidence_id": fact["evidence_ids"][0], "text": original["text"]}],
        "category": "DOCUMENTARY",
        "epistemic_type": "reported_quantity",
        "conditions": [],
    }
    service = ConversationService(SimpleNamespace(store=store, registry=registry))
    _, good = service._align_claim(fact["text"], ["projection"], {"projection": anchor})
    assert good["supported"] and good["verification_mechanism"] == "typed_original_cell_projection"
    _, altered = service._align_claim(
        fact["text"].replace("0.21", "0.31"), ["projection"], {"projection": anchor}
    )
    assert not altered["supported"]
    forged = {**anchor, "structured_record_id": "psi-39-record-2-field-6-0"}
    _, wrong_record = service._align_claim(fact["text"], ["projection"], {"projection": forged})
    assert not wrong_record["supported"]


def test_typed_numeric_check_does_not_borrow_identifier_digits_or_controller_units(mapped):
    from types import SimpleNamespace

    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    store, registry, _ = mapped
    registry.scientific_properties = store.registry.properties
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    for rid, claim in [
        ("psi-39-record-3-field-6-0", "The oxygen concentration is 1207 fraction."),
        ("psi-21-record-2-field-3-0", "Fuel MFC is 0.1 l/min."),
    ]:
        payload = store.payload(rid)
        eid = store.evidence(rid)[0]
        original = registry.resolve(eid)
        definition = store.registry.properties[payload["property_id"]]
        anchor = {
            "support_id": rid,
            "text": original["text"],
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
            "spans": [{"evidence_id": eid, "text": original["text"]}],
            "typed_fields": [
                {
                    "property_id": payload["property_id"],
                    "aliases": definition.aliases,
                    "role": payload["qualifiers"]["scientific_role"],
                    "value": payload["value"],
                }
            ],
        }
        result = verify_paraphrase(claim, [anchor], registry, optimistic)
        assert not result["supported"], result


def test_source_restatement_keeps_repair_identity_and_requested_record(mapped):
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.structured_facts import structured_fact

    store, registry, _ = mapped
    service = ConversationService(SimpleNamespace(store=store, registry=registry))
    service._explicit_record_subjects = {"psi-39-record-3"}
    rid = "psi-39-record-3-field-6-0"
    payload = store.payload(rid)
    fact = structured_fact(rid, store, registry)
    anchor = {
        "support_id": "typed",
        "document_id": "psi-39",
        "category": "DOCUMENTARY",
        "text": fact["text"],
        "deterministic_text": fact["text"],
        "structured_record_id": rid,
        "typed_fields": [
            {
                "property_id": payload["property_id"],
                "aliases": store.registry.properties[payload["property_id"]].aliases,
            }
        ],
    }
    failure = {
        "statement_id": "draft-7",
        "proposal": {
            "text": "The oxygen concentration is 1207 fraction.",
            "support_ids": ["typed"],
        },
        "feedback": {"matched_support_ids": ["typed"]},
    }
    recovery = service._source_restatements([failure], {"typed": anchor}, [])
    assert len(recovery) == 1 and recovery[0]["repair_of"] == "draft-7"
    assert "0.21 fraction" in recovery[0]["text"]


def test_scope_projection_reports_representation_without_claiming_physical_identity(mapped):
    from nasa_fire_ai.services.structured_facts import record_scope_fact

    store, registry, _ = mapped
    fact = record_scope_fact("psi-68-record-2", store, registry)
    assert fact and "configuration summary" in fact["text"]
    assert "not expanded into individual" in fact["text"]
    assert not record_scope_fact("psi-39-record-3-field-6-0", store, registry)
    from nasa_fire_ai.services.structured_facts import structured_fact

    capacity = structured_fact("psi-21-record-3-field-3-0", store, registry)
    assert capacity["definition_spans"]
    assert all(span["scope"] == "table_field_definition" for span in capacity["definition_spans"])
    assert len(capacity["evidence_ids"]) == 2


def test_literal_mixture_components_resolve_source_summaries_without_purity_inference(mapped):
    from nasa_fire_ai.query.record_identity import resolve_record_mentions

    store, _, _ = mapped
    subjects, _ = resolve_record_mentions(
        "PSI-68 propanol glycerol configuration summaries", store, ROOT
    )
    assert len(subjects) == 2
    assert all(
        "glycerol" in store.payload(subject)["reported_material_description"].lower()
        for subject in subjects
    )


def test_explicit_record_scope_and_cell_completion_do_not_borrow_another_run(mapped):
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.structured_alignment import complete_record_fields
    from nasa_fire_ai.services.structured_facts import structured_fact

    store, registry, _ = mapped
    search = SimpleNamespace(store=store, registry=registry)
    fact = structured_fact("psi-39-record-2-field-6-0", store, registry)
    eid = fact["evidence_ids"][0]
    anchor = {
        "support_id": "wrong",
        "structured_record_id": fact["record_id"],
        "deterministic_text": fact["text"],
        "text": fact["text"],
        "projection_verified": True,
        "spans": [{"evidence_id": eid, "text": registry.resolve(eid)["text"]}],
        "category": "DOCUMENTARY",
        "epistemic_type": "reported_quantity",
        "conditions": [],
    }
    service = ConversationService(
        search, entailment=SimpleNamespace(check=lambda p, h: {"supported": True})
    )
    service._explicit_record_subjects = {"psi-39-record-3"}
    assert not service._align_claim(fact["text"], ["wrong"], {"wrong": anchor})[1]["supported"]
    right = structured_fact("psi-39-record-3-field-6-0", store, registry)
    eid = right["evidence_ids"][0]
    anchor = {
        **anchor,
        "support_id": "right",
        "structured_record_id": right["record_id"],
        "deterministic_text": right["text"],
        "text": right["text"],
        "spans": [{"evidence_id": eid, "text": registry.resolve(eid)["text"]}],
    }
    inventory = {"right": anchor}
    proposals = complete_record_fields(
        [{"need": "oxygen concentration"}, {"need": "fiber status"}],
        inventory,
        search,
        [],
        {"psi-39-record-3"},
        SimpleNamespace(check=lambda p, h: {"supported": False}),
    )
    assert len(proposals) == 2
    assert all("1207" in proposal["text"] for proposal in proposals)


def test_predeclared_aliases_do_not_replace_source_backed_investigation_entities(tmp_path):
    import csv

    from pyshacl import validate
    from rdflib import Graph

    from nasa_fire_ai.query.native import node

    store = make_store(ROOT)
    registry = EvidenceRegistry(tmp_path / "evidence.sqlite", evidence_root=ROOT)
    campaigns = {
        r["accession"]: r
        for r in csv.DictReader((ROOT / "data/raw/hackathon-team/data/clean/campaigns.csv").open())
    }
    for accession in ("PSI-98", "PSI-25", "PSI-26"):
        import_table(
            store,
            registry,
            ROOT,
            ROOT / f"data/raw/hackathon-psi/{accession}_experimental_table.csv",
            campaigns[accession],
        )
        assert "Investigation" in store.classes(accession.lower())
        assert store.payload(accession.lower())["title"] == campaigns[accession]["title"]
    conforms, _, _ = validate(
        store.graph, shacl_graph=Graph().parse(ROOT / "ontology/psi_shapes.ttl")
    )
    assert conforms
    from rdflib import RDF

    store.graph.remove((node("psi-98"), RDF.type, node("Investigation")))
    conforms, _, _ = validate(
        store.graph, shacl_graph=Graph().parse(ROOT / "ontology/psi_shapes.ttl")
    )
    assert not conforms
    registry.db.close()


def test_configuration_alternatives_cannot_become_identified_physical_runs(mapped):
    from nasa_fire_ai.services.ontology_support import audit_relation

    store, evidence, _ = mapped
    # The HTTP service registers catalogue names before verification. Supply
    # that same original catalogue context to the table-only fixture.
    import csv

    with (ROOT / "data/raw/hackathon-team/data/clean/campaigns.csv").open() as source:
        campaign = next(row for row in csv.DictReader(source) if row["accession"] == "PSI-68")
    store.registry.entity_mentions[campaign["accession"].lower()] = {
        "relation": "belongsToInvestigation",
        "aliases": [campaign["accession"], campaign["title"], campaign["campaign"]],
    }
    result = audit_relation(
        "Every FLEX-2 oxygen and pressure alternative corresponds to a distinct identified physical run in the original summary table.",
        [],
        store,
        evidence,
    )
    assert result["scientific_status"] == "ONTOLOGY_INCOMPATIBLE"
    assert result["verification_mechanism"] == "source_record_identity_scope"
    # Ordinary lookup and the explicit conservative scope remain eligible for
    # independent source verification; ontology compatibility is not acceptance.
    for text in [
        "FLEX-2 lists pressure alternatives.",
        "FLEX-2 configuration alternatives do not enumerate identified physical runs.",
    ]:
        result = audit_relation(text, [], store, evidence)
        assert result.get("scientific_status") != "ONTOLOGY_INCOMPATIBLE"


def test_original_reference_link_is_checked_before_model_reference_rejection(tmp_path):
    import csv
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.structured_facts import structured_fact

    store = make_store(ROOT)
    evidence = EvidenceRegistry(tmp_path / "references.sqlite", evidence_root=ROOT)
    with (ROOT / "data/raw/hackathon-team/data/clean/campaigns.csv").open() as source:
        campaign = next(row for row in csv.DictReader(source) if row["accession"] == "PSI-142")
    import_table(
        store,
        evidence,
        ROOT,
        ROOT / "data/raw/hackathon-psi/PSI-142_experimental_table.csv",
        campaign,
    )
    try:
        descriptor = structured_fact("psi-142-record-2-field-2-0", store, evidence)
        reference = structured_fact("psi-142-record-2-field-3-0", store, evidence)
        assert descriptor and reference
        seed = {
            "support_id": "description",
            "text": descriptor["text"],
            "deterministic_text": descriptor["text"],
            "structured_record_id": descriptor["record_id"],
            "projection_verified": True,
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "spans": [
                {
                    "evidence_id": descriptor["evidence_ids"][0],
                    "text": evidence.resolve(descriptor["evidence_ids"][0])["text"],
                }
            ],
            "conditions": [],
        }

        def source_view(eid):
            return {**evidence.resolve(eid), "source": evidence.source_metadata(eid)}

        service = ConversationService(
            SimpleNamespace(store=store, registry=evidence, _evidence=source_view),
            entailment=SimpleNamespace(check=lambda p, h: {"supported": False}),
        )
        inventory = {"description": seed}
        trace = {"verification": [], "verification_stage": "draft"}
        accepted, rejected = service._accept_segments(
            [{"text": reference["text"], "support_ids": []}], inventory, trace, [], {}
        )
        assert accepted and not rejected
        altered = reference["text"].replace("2017.01.028", "2017.01.029")
        assert altered != reference["text"]
        accepted, rejected = service._accept_segments(
            [{"text": altered, "support_ids": []}],
            inventory,
            {"verification": [], "verification_stage": "draft"},
            [],
            {},
        )
        assert not accepted and rejected
    finally:
        evidence.db.close()


def test_long_answer_coverage_checks_the_communicated_source_fact_not_context_size(mapped):
    from types import SimpleNamespace

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.structured_facts import structured_fact

    store, evidence, _ = mapped
    candidates = [
        row[0]
        for row in evidence.db.execute(
            "SELECT value_id FROM value_cells WHERE value_id LIKE 'psi-39-record-2-%'"
        )
    ]
    rid = next(
        identity
        for identity in candidates
        if store.payload(identity).get("property_id") == "OxygenConcentration"
    )
    fact = structured_fact(rid, store, evidence)
    service = ConversationService(
        SimpleNamespace(store=store, registry=evidence),
        entailment=SimpleNamespace(
            check=lambda p, h: {"supported": False, "reason": "no entailment"}
        ),
    )
    service._explicit_record_subjects = {fact["subject"]}
    service._active_support_inventory = {"a": {"structured_record_id": rid}}
    need = {"need": "oxygen concentration in the source record"}
    statements = [
        {"text": fact["text"]},
        {"text": "Additional independently reviewed context. " * 600},
    ]
    assert service._need_is_communicated(need, statements)
    assert not service._need_is_communicated(need, [{"text": fact["text"].replace("0.21", "0.22")}])
    assert not service._need_is_communicated(
        need, [{"text": "See the oxygen source citation [1]."}]
    )
    assert not service._need_is_communicated({"need": "observed oxygen concentration"}, statements)


def test_table_definitions_are_recovered_without_carrier_row_conditions(mapped):
    from types import SimpleNamespace

    from nasa_fire_ai.services.structured_alignment import (
        expand_source_fields,
        record_anchor_allowed,
    )
    from nasa_fire_ai.services.structured_facts import structured_fact

    store, registry, _ = mapped
    subject = "psi-20-record-10"
    eid = store.evidence(subject)[0]
    source = registry.resolve(eid)
    inventory = {
        "selected": {
            "support_id": "selected",
            "document_id": source["document_id"],
            "text": source["text"],
            "spans": [{"evidence_id": eid, "text": source["text"]}],
        }
    }
    search = SimpleNamespace(store=store, registry=registry)
    expand_source_fields(inventory, search, definitions_only=True)
    assert set(inventory) == {
        "selected",
        "value-psi-20-record-2-field-8-0",
        "value-psi-20-record-3-field-8-0",
    }
    expand_source_fields(inventory, search)
    expand_source_fields(inventory, search)
    definitions = [
        a for a in inventory.values() if a.get("definition_scope") == "same_original_table"
    ]
    assert {a["structured_record_id"] for a in definitions} == {
        "psi-20-record-2-field-8-0",
        "psi-20-record-3-field-8-0",
    }
    for anchor in definitions:
        rid = anchor["structured_record_id"]
        assert [field["id"] for field in anchor["typed_fields"]] == [rid]
        assert record_anchor_allowed(anchor, search, {subject})
        assert not record_anchor_allowed(anchor, search, {"psi-22-record-11"})
        fact = structured_fact(rid, store, registry)
        assert fact["primary_span"]["text"] == store.payload(rid)["qualifiers"]["original_value"]
        assert (
            fact["primary_span"]["text"]
            in registry.resolve(fact["primary_span"]["evidence_id"])["text"]
        )
    assert not any(
        a.get("structured_record_id") == "psi-20-record-2-field-1-0" for a in inventory.values()
    )
    assert "scope-psi-20-record-2" not in inventory


def test_original_auxiliary_rows_are_scientific_records_not_combustion_runs(tmp_path):
    import csv

    store = make_store(ROOT)
    registry = EvidenceRegistry(tmp_path / "auxiliary.sqlite", evidence_root=ROOT)
    campaigns = {
        r["accession"]: r
        for r in csv.DictReader((ROOT / "data/raw/hackathon-team/data/clean/campaigns.csv").open())
    }
    try:
        counts = []
        for n in (98, 99, 26):
            accession = f"PSI-{n}"
            counts.append(
                import_table(
                    store,
                    registry,
                    ROOT,
                    ROOT / f"data/raw/hackathon-psi/{accession}_experimental_table.csv",
                    campaigns[accession],
                )
            )
        assert sum(c.get("DataProductReference", 0) for c in counts) == 4
        assert sum(c.get("SourceAnnotation", 0) for c in counts) == 4
        assert sum(c.get("MaintenanceRecord", 0) for c in counts) == 1
        for n, ordinals in ((98, (4, 5)), (99, (11, 12, 13, 14, 15, 16)), (26, (67,))):
            for ordinal in ordinals:
                record = f"psi-{n}-annotation-{ordinal}"
                assert "ExperimentalRun" not in store.classes(record, include_ancestors=True)
                assert "SourceRecord" in store.classes(record, include_ancestors=True)
                assert record in store.relations(f"psi-{n}", "hasSourceRecord")
                fields = store.relations(record, "hasRecordedField")
                assert fields
                for field in fields:
                    original = registry.resolve(store.evidence(field)[0])
                    assert original["structured_location"]["row_ordinal"] == ordinal
                    assert store.payload(field)["qualifiers"]["original_value"] in {
                        c["original_value"] for c in original["source_cells"]
                    }
        assert store.relations("psi-99-2-7", "hasSourceAnnotation") == {"psi-99-annotation-14"}
        assert store.relations("psi-99-2-8", "hasSourceAnnotation") == {
            "psi-99-annotation-15",
            "psi-99-annotation-16",
        }
        assert store.relations("psi-99-2-9", "hasSourceAnnotation") == {"psi-99-annotation-16"}
        assert not store.relations("psi-99-2-6", "hasSourceAnnotation")
        assert not store.relations("psi-26-annotation-67", "hasMaterial")
        quantity = store.value_records("psi-99-annotation-16", "source:regression_rate")[0]
        assert quantity["value"].lower == pytest.approx(0.00001)
        assert quantity["value"].upper == pytest.approx(0.00004)
        assert quantity["value"].canonical_unit == "m/s"
        from types import SimpleNamespace

        from nasa_fire_ai.services.structured_alignment import expand_source_fields
        from nasa_fire_ai.services.structured_facts import structured_fact

        fields = store.relations("psi-99-2-8", "hasRecordedField")
        selected = next(
            f
            for f in fields
            if store.payload(f)["qualifiers"].get("source_header") == "?-g Spread Length"
        )
        proof = structured_fact(selected, store, registry)
        inventory = {
            "selected": {
                "support_id": "selected",
                "structured_record_id": selected,
                "spans": [
                    {"evidence_id": e, "text": registry.resolve(e)["text"]}
                    for e in store.evidence(selected)
                ],
            }
        }
        search = SimpleNamespace(store=store, registry=registry)
        expand_source_fields(inventory, search, {"psi-99-2-8"}, definitions_only=True)
        note = inventory["value-psi-99-annotation-16-field-1-0"]
        assert note["annotation_record_ids"] == ["psi-99-2-8", "psi-99-2-9"]
        from nasa_fire_ai.services.structured_alignment import record_anchor_allowed

        assert record_anchor_allowed(note, search, {"psi-99-2-8"}, {"psi-99"})
        assert not record_anchor_allowed(note, search, {"psi-99-2-7"}, {"psi-99"})
        assert not record_anchor_allowed(note, search, set(), {"psi-98"})
        assert any(s["scope"] == "source_record_annotation" for s in proof["definition_spans"])
    finally:
        registry.db.close()
