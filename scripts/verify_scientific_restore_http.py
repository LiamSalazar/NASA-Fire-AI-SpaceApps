"""Exercise isolated restored assets over TCP, without a generation API key."""

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.api import create_app
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.snapshot_vectors import SnapshotVectors
from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.search import ScientificSearchService


def exercise(factory, port, action):
    server = uvicorn.Server(
        uvicorn.Config(create_app(factory), host="127.0.0.1", port=port, log_level="critical")
    )
    worker = threading.Thread(target=server.run, daemon=True)
    worker.start()
    while not server.started:
        if not worker.is_alive():
            raise RuntimeError("TCP server failed")
        time.sleep(0.05)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=180) as client:
            return action(client)
    finally:
        server.should_exit = True
        worker.join(timeout=30)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--snapshot-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = args.root / "data/snapshots" / args.snapshot_name

    def factory():
        return ConversationService(
            ScientificSearchService(snapshot, args.root), provider=None, entailment=None
        )

    def inspect(client):
        ready = client.get("/api/v1/readiness")
        ready.raise_for_status()
        state = ready.json()
        assert state["scientific_mode"] == "partial"
        assert state["channels"]["vector"] == "NOT_PROVISIONED"
        records = []
        for accession in (39, 107, 21, 47, 68, 25, 99, 102):
            response = client.get(
                "/api/v1/records", params={"investigation": f"psi-{accession}", "limit": 2}
            )
            response.raise_for_status()
            result = response.json()
            assert result["items"] and all(row["fields"] for row in result["items"])
            records.append(
                {
                    "investigation": f"psi-{accession}",
                    "records": len(result["items"]),
                    "registered_records": result["total"],
                }
            )
        response = client.post(
            "/api/v1/search",
            json={"query": "CFI Flex Number 1207 oxygen concentration 0.21 fraction", "limit": 5},
        )
        response.raise_for_status()
        search = response.json()
        response = client.post(
            "/api/v1/search",
            json={
                "query": "In the PSI-115 report and its data-organization document, what particle formation was modeled?",
                "limit": 5,
            },
        )
        response.raise_for_status()
        documentary_scope = response.json()
        assert any(
            c["entity_id"] == "psi-115" and c["relation"] == "belongsToInvestigation"
            for c in documentary_scope["intent"]["entity_constraints"]
        )
        response = client.get(
            "/api/v1/records", params={"investigation": "psi-159", "identifier": "21088 D1"}
        )
        response.raise_for_status()
        fields = response.json()["items"][0]["fields"]
        tad = next(
            field for field in fields if field["property_id"] == "source:adiabatic_temperature"
        )
        response = client.post(
            "/api/v1/ontology/navigate",
            json={"start": tad["id"], "steps": [{"relation": "hasTermDefinition"}]},
        )
        response.raise_for_status()
        term_definition = response.json()
        assert term_definition["results"]
        assert (
            "adiabatic flame temperature" in term_definition["results"][0]["entity_details"]["text"]
        )
        for edge in term_definition["results"][0]["path"]:
            assert len(edge["evidence_ids"]) >= 2
            for eid in edge["evidence_ids"]:
                client.get("/api/v1/evidence/" + eid).raise_for_status()
        response = client.post(
            "/api/v1/ontology/navigate",
            json={
                "start": "psi-107",
                "steps": [{"relation": "usesApparatus"}, {"relation": "hasInstrument"}],
            },
        )
        response.raise_for_status()
        instruments = response.json()
        assert len(instruments["results"]) == 3
        attributes = [
            path["entity_details"]["instrument_attributes"] for path in instruments["results"]
        ]
        assert {tuple(sorted(row.items())) for row in attributes} == {
            tuple(
                sorted(
                    {
                        "instrumentCategory": "camera",
                        "signalFormat": "digital",
                        "acquisitionMode": "still",
                    }.items()
                )
            ),
            tuple(
                sorted(
                    {
                        "instrumentCategory": "camera",
                        "signalFormat": "analog",
                        "acquisitionMode": "video",
                    }.items()
                )
            ),
            tuple(
                sorted({"instrumentCategory": "radiometer", "detectorType": "thermopile"}.items())
            ),
        }
        for path in instruments["results"]:
            assert len(path["path"]) == 2
            assert path["classification"] == "RELATED"
            for edge in path["path"]:
                for eid in edge["evidence_ids"]:
                    client.get("/api/v1/evidence/" + eid).raise_for_status()
        scientific_paths = []
        for accession in (107, 39, 22, 21, 20, 23, 106, 68, 47):
            first = "hasRun" if accession == 39 else "hasSourceRecord"
            reached = []
            for relation in (
                "hasRecordedField",
                "hasCondition",
                "hasMeasurement",
                "hasMaterialDescription",
            ):
                response = client.post(
                    "/api/v1/ontology/navigate",
                    json={
                        "start": f"psi-{accession}",
                        "steps": [{"relation": first}, {"relation": relation}],
                        "budget": 32,
                    },
                )
                response.raise_for_status()
                route = response.json()
                for path in route["results"][:2]:
                    assert len(path["path"]) == 2
                    for edge in path["path"]:
                        for eid in edge["evidence_ids"]:
                            original = client.get("/api/v1/evidence/" + eid)
                            original.raise_for_status()
                            assert original.json()["text"]
                if route["results"]:
                    reached.append(
                        {
                            "relation": relation,
                            "returned": len(route["results"]),
                            "truncated": route["truncated"],
                            "examples": route["results"][:2],
                        }
                    )
            assert reached, f"No scientific fields reached for PSI-{accession}"
            scientific_paths.append({"investigation": f"psi-{accession}", "routes": reached})
        response = client.post(
            "/api/v1/comparisons",
            json={
                "subjects": ["psi-39-record-2", "psi-39-record-3"],
                "dimensions": ["Pressure", "OxygenConcentration"],
            },
        )
        response.raise_for_status()
        comparison = response.json()
        response = client.post(
            "/api/v1/chat",
            json={"message": "For CFI Flex Number 1207, quote its fuel entry.", "max_queries": 1},
        )
        response.raise_for_status()
        answer = response.json()
        resolved = []
        for citation in answer["citations"]:
            response = client.get("/api/v1/evidence/" + citation["evidence_id"])
            response.raise_for_status()
            assert response.json()["text"]
            resolved.append(citation["evidence_id"])
        assert resolved
        return {
            "shared_apparatus_instruments": instruments,
            "source_backed_scientific_paths": scientific_paths,
            "readiness": state,
            "records": records,
            "search": search,
            "documentary_investigation_scope": documentary_scope,
            "original_field_to_source_nomenclature": term_definition,
            "comparison": comparison,
            "no_key_chat": answer,
            "resolved_citations": resolved,
        }

    result = exercise(factory, 8770, inspect)

    def missing():
        return ConversationService(
            ScientificSearchService(args.root / "missing-snapshot", args.root)
        )

    result["missing_snapshot_http_status"] = exercise(
        missing, 8771, lambda client: client.get("/api/v1/readiness").status_code
    )
    assert result["missing_snapshot_http_status"] == 503

    def incompatible():
        directory = args.root / "data/index" / (args.snapshot_name + "-vectors")
        metadata = json.loads((directory / "documentary.metadata.json").read_text())

        class IdentityOnly:
            def model_identity(self):
                return metadata["model_id"]

        registry = EvidenceRegistry(
            snapshot / "evidence.sqlite", read_only=True, evidence_root=args.root
        )
        try:
            SnapshotVectors(directory, registry, "incorrect-snapshot-identity", IdentityOnly())
        finally:
            registry.db.close()

    result["incompatible_vectors_http_status"] = exercise(
        incompatible, 8772, lambda client: client.get("/api/v1/readiness").status_code
    )
    assert result["incompatible_vectors_http_status"] == 503
    result["boundary"] = (
        "Actual restored sources, lexical/structured/KG HTTP paths; no fresh LLM or vector query API call. Vector artifacts verified separately at restore."
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
