"""Resumable Phase 3C receipts; immutable inputs and scientific approval are preserved."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "artifacts/phase3c_generalization_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    with (DIRECTORY / name).open("x") as handle:
        json.dump(value, handle, indent=2)


def freeze():
    files = {}
    for folder in ("data/raw", "data/canonical", "evals", "ontology", "domain", "src", "app"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                files[str(path.relative_to(ROOT))] = {
                    "bytes": path.stat().st_size,
                    "sha256": sha(path),
                }
    for path in sorted((ROOT / "artifacts/phase3c_curation_v1").rglob("*")):
        if path.is_file():
            files[str(path.relative_to(ROOT))] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    files["data/index/evidence.sqlite"] = {"sha256": sha(ROOT / "data/index/evidence.sqlite")}
    write(
        "baseline.json",
        {"files": files, "raw_policy": "immutable", "historical_metrics": "not new execution"},
    )
    db = sqlite3.connect(f"file:{ROOT / 'data/index/evidence.sqlite'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    # Membership is selected using metadata only, before adapting extraction.
    # Conservative lineage key groups versions sharing a normalized title.
    import re

    sources = [
        dict(row)
        for row in db.execute(
            "SELECT source_id,title,nasa_id,sha256 FROM sources ORDER BY source_id"
        )
    ]
    groups = {}
    for source in sources:
        key = re.sub(r"[^a-z0-9]", "", (source["title"] or source["source_id"]).lower())
        groups.setdefault(key, []).append(source)
    membership = []
    for key, members in sorted(groups.items()):
        number = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 10
        partition = "holdout" if number == 0 else "validation" if number == 1 else "development"
        for member in members:
            membership.append({**member, "lineage_key": key, "partition": partition})
    write(
        "evaluation_split.json",
        {
            "version": 1,
            "membership": membership,
            "selection": "metadata-only deterministic title-lineage grouping before development",
            "limitations": [
                "Prior historical model/source exposure cannot be excluded.",
                "Title lineage requires expert reconciliation; cross-publication investigation leakage remains unmeasured.",
                "No independent scientific gold labels exist; final evaluation measures incorporation contracts only.",
            ],
        },
    )
    db.close()
    print(
        json.dumps(
            {
                "frozen_files": len(files),
                "sources": len(membership),
                "holdout_sources": sum(r["partition"] == "holdout" for r in membership),
            }
        )
    )


def integrity():
    baseline = json.loads((DIRECTORY / "baseline.json").read_text())["files"]
    immutable = {
        key: value
        for key, value in baseline.items()
        if key.startswith(
            ("data/raw/", "data/canonical/", "evals/", "artifacts/phase3c_curation_v1/")
        )
        or key == "data/index/evidence.sqlite"
    }
    changes = [
        key
        for key, value in immutable.items()
        if not (ROOT / key).exists() or sha(ROOT / key) != value["sha256"]
    ]
    write(
        "preservation.json", {"checked": len(immutable), "changed": changes, "passed": not changes}
    )
    print(json.dumps({"checked": len(immutable), "changed": changes}))


def index(revision=1):
    filename = "artifact_index.json" if revision == 1 else f"artifact_index_v{revision}.json"
    paths = sorted(p for p in DIRECTORY.rglob("*") if p.is_file() and p.name != filename)
    write(
        filename,
        {
            "artifacts": [
                {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}
                for p in paths
            ],
            "reports": [
                {
                    "path": "docs/PHASE3C_GENERALIZATION_V1.md",
                    "bytes": (ROOT / "docs/PHASE3C_GENERALIZATION_V1.md").stat().st_size,
                    "sha256": sha(ROOT / "docs/PHASE3C_GENERALIZATION_V1.md"),
                }
            ],
        },
    )


def quality(revision=1):
    import subprocess

    results = []
    suffix = "" if revision == 1 else f"_v{revision}"
    for label, command in [
        ("format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("pytest", ["uv", "run", "pytest", "-q"]),
    ]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        with (DIRECTORY / (label + "_final" + suffix + ".txt")).open("x") as handle:
            handle.write(result.stdout + result.stderr)
        results.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "receipt": label + "_final" + suffix + ".txt",
            }
        )
        print(json.dumps(results[-1]), flush=True)
    write(
        "quality_receipt" + suffix + ".json",
        {
            "fresh_execution": True,
            "commands": results,
            "passed": all(r["exit_code"] == 0 for r in results),
        },
    )
    if not all(r["exit_code"] == 0 for r in results):
        raise RuntimeError("Quality gates failed; do not freeze final evaluation")
    paths = sorted(
        p
        for name in ("src", "app", "domain", "ontology", "tests")
        for p in (ROOT / name).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    write(
        "contract_freeze.json",
        {
            "stage": "implementation frozen before final source evaluation",
            "split_sha256": sha(DIRECTORY / "evaluation_split.json"),
            "files": {str(p.relative_to(ROOT)): sha(p) for p in paths},
        },
    )


def audit():
    import os
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "app"))
    from pyshacl import validate
    from rdflib import Graph
    from streamlit.testing.v1 import AppTest

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.semantic import project_legacy
    from nasa_fire_ai.query.native import NS
    from nasa_fire_ai.services.curation import extension_shapes

    workspace = DIRECTORY / "pilot/workspace"
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    store = project_legacy(workspace, registry)
    shapes = Graph().parse(ROOT / "ontology/semantic_shapes.ttl") + extension_shapes(store)
    native = validate(store.graph, shacl_graph=shapes)[0]
    canonical = validate(
        Graph().parse(ROOT / "data/canonical/graph.ttl"),
        shacl_graph=str(ROOT / "ontology/shapes.ttl"),
    )[0]
    evidence = {str(e) for e in store.graph.objects(None, NS.evidenceRef)}
    missing = sorted(eid for eid in evidence if not registry.resolve(eid))
    write(
        "scientific_integrity.json",
        {
            "native_shacl": native,
            "canonical_shacl": canonical,
            "graph_evidence_ids": len(evidence),
            "missing_evidence": missing,
            "sqlite": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": [list(r) for r in registry.db.execute("PRAGMA foreign_key_check")],
            "fts_missing": registry.db.execute(
                "SELECT count(*) FROM passages WHERE evidence_id NOT IN (SELECT evidence_id FROM passages_fts)"
            ).fetchone()[0],
            "vectors": "disabled; enabled-vector publication not demonstrated",
        },
    )
    os.environ["NASA_CURATION_DEVELOPMENT"] = "true"
    os.environ["NASA_CURATION_WORKSPACE"] = str(workspace.resolve())
    app = AppTest.from_string(
        f"from curation_view import show_curation\nfrom pathlib import Path\nshow_curation(Path({str(ROOT)!r}))",
        default_timeout=30,
    ).run()
    write(
        "ui_receipt.json",
        {
            "exceptions": [e.message for e in app.exception],
            "buttons": [b.label for b in app.button],
            "graphs": len(app.get("graphviz_chart")),
            "boundary": "Actual rendering and backend tests; no independent scientist usability evaluation",
        },
    )
    Settings()
    secrets = [
        os.environ.get(k)
        for k in ("NVIDIA_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY")
        if os.environ.get(k)
    ]
    leaked = []
    env_files = []
    for path in DIRECTORY.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".env":
            env_files.append(str(path.relative_to(ROOT)))
        if secrets and any(value.encode() in path.read_bytes() for value in secrets):
            leaked.append(str(path.relative_to(ROOT)))
    write(
        "secret_exclusion.json",
        {"configured_secret_values_found": bool(leaked), "paths": leaked, "env_files": env_files},
    )
    registry.db.close()
    print(
        json.dumps(
            {
                "native_shacl": native,
                "canonical_shacl": canonical,
                "missing_evidence": len(missing),
                "ui_errors": len(app.exception),
                "secrets_found": bool(leaked),
            }
        )
    )


def corpus(live=False, final=False, revision=1):
    """Process eligible originals in isolated registry; checkpoint each source independently."""
    import re
    import sys
    from collections import Counter

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from curate_research import initialize_workspace

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.scientific_proposals import extract_source
    from nasa_fire_ai.ingestion.semantic import load_semantic_registry
    from nasa_fire_ai.services.curation import CurationService

    split = json.loads((DIRECTORY / "evaluation_split.json").read_text())
    if final:
        frozen = json.loads((DIRECTORY / "contract_freeze.json").read_text())
        if frozen["split_sha256"] != sha(DIRECTORY / "evaluation_split.json") or any(
            sha(ROOT / p) != value for p, value in frozen["files"].items()
        ):
            raise ValueError("Final evaluation requires unchanged frozen contracts and membership")
    membership = {row["source_id"]: row for row in split["membership"]}
    workspace = initialize_workspace(
        DIRECTORY / ("holdout_workspace" if final else "corpus_workspace")
    )
    original = sqlite3.connect(f"file:{ROOT / 'data/index/evidence.sqlite'}?mode=ro", uri=True)
    original.row_factory = sqlite3.Row
    destination = workspace / "data/index/evidence.sqlite"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        copied = sqlite3.connect(destination)
        original.backup(copied)
        copied.close()
    registry = EvidenceRegistry(destination)
    semantic = load_semantic_registry(workspace / "domain/semantic_registry.yaml")
    curator = CurationService(workspace, registry)
    settings = Settings(root=workspace)
    sources = [dict(r) for r in original.execute("SELECT * FROM sources ORDER BY source_id")]
    fts = {r[0] for r in original.execute("SELECT evidence_id FROM passages_fts")}
    receipts = DIRECTORY / ("holdout_sources" if final else "corpus_sources")
    receipts.mkdir(parents=True, exist_ok=True)
    source_hashes = {}
    ledger = []
    new_calls = 0
    for source in sources:
        sid = source["source_id"]
        title = source.get("title") or ""
        candidate = bool(
            re.search(
                r"microgravity|combustion|flame|spacecraft.{0,30}fire|fire.{0,30}(spacecraft|suppress)|saffire|burning and suppression",
                title,
                re.IGNORECASE,
            )
            or sid.startswith("psi-")
            or "6001" in str(source.get("nasa_id", ""))
        )
        outside = bool(
            re.search(
                r"solar flare|supernova|stellar|gas turbine|jet engine|scramjet|rocket engine",
                title,
                re.IGNORECASE,
            )
        )
        row = {
            "source_id": sid,
            "title": title,
            "url": source.get("url"),
            "candidate": candidate,
            "domain_relevance": "OUTSIDE_PRIMARY_DOMAIN"
            if outside
            else "DOMAIN_CANDIDATE_REVIEW_REQUIRED"
            if candidate
            else "NOT_SELECTED",
            "partition": membership[sid]["partition"],
            "scientific_relevance_authority": "heuristic triage; no independent gold",
        }
        path = ROOT / (source.get("filename") or "unavailable")
        if not path.is_file():
            matches = list(
                (ROOT / "data/raw").rglob(Path(source.get("filename") or "unavailable").name)
            )
            path = matches[0] if len(matches) == 1 else None
        row["acquired"] = bool(path and path.is_file())
        actual = sha(path) if row["acquired"] else None
        row["sha256"] = actual
        row["digest_verified"] = bool(actual and actual == source.get("sha256"))
        row["duplicate_of"] = source_hashes.get(actual) if actual else None
        if actual:
            source_hashes.setdefault(actual, sid)
        pages = [
            dict(r)
            for r in original.execute(
                "SELECT p.evidence_id,p.text FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
                (sid,),
            )
        ]
        row["parsed"] = bool(pages)
        row["searchable"] = bool(pages) and all(p["evidence_id"] in fts for p in pages)
        row["representation"] = (
            "METADATA_ONLY"
            if path and path.suffix.lower() == ".json" and sid.startswith("psi-")
            else "SOURCE_CONTENT"
            if pages
            else "NO_ACCESSIBLE_TEXT"
        )
        row["source_category"] = (
            "SAFETY_GUIDANCE_CANDIDATE"
            if re.search(r"standard|guideline|requirement|safety", title, re.IGNORECASE)
            else "EXPERIMENTAL_OR_RELATED_STUDY_CANDIDATE"
        )
        row["superseded"] = source.get("status") == "SUPERSEDED_DOCUMENT"
        eligible = (
            candidate
            and not outside
            and row["digest_verified"]
            and row["parsed"]
            and not row["superseded"]
            and not row["duplicate_of"]
        )
        partition_eligible = (
            row["partition"] == "holdout" if final else row["partition"] != "holdout"
        )
        if eligible and partition_eligible:
            filename = hashlib.sha256(sid.encode()).hexdigest()[:20] + ".json"
            receipt_path = receipts / filename
            if (
                revision > 1
                and receipt_path.exists()
                and json.loads(receipt_path.read_text()).get("failure_type")
            ):
                receipt_path = receipts / (
                    filename.removesuffix(".json") + f"_retry_v{revision}.json"
                )
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text())
                if receipt["source_sha256"] != actual:
                    raise ValueError("Original changed; start a new versioned batch")
                row["batch_execution"] = "CHECKPOINT_REPLAY"
            else:
                try:
                    extraction = extract_source(
                        sid,
                        registry,
                        semantic,
                        settings,
                        model_enabled=live
                        and new_calls < 3
                        and row["representation"] == "SOURCE_CONTENT",
                        max_items=64,
                    )
                    new_calls += extraction.get("new_model_calls", 0)
                    package = curator.submit(
                        title or sid,
                        "Source-backed draft; scope, identity and epistemic review required",
                        [(path.name, path.read_bytes())],
                        "corpus-preparation",
                    )
                    validation = curator.validate(package["package"])
                    receipt = {
                        "source_id": sid,
                        "source_sha256": actual,
                        "extraction": extraction,
                        "package_id": package["package"]["id"],
                        "draft_digest": package["digest"],
                        "entities": len(package["package"]["entities"]),
                        "values": len(package["package"]["values"]),
                        "statements": Counter(
                            s["epistemic"] for s in package["package"]["statements"]
                        ),
                        "clarifications": validation["questions"],
                        "errors": validation["errors"],
                        "scientific_publication": "NOT_AUTHORIZED",
                        "structured_completeness": "PARTIAL_BOUNDED_EXTRACTION",
                    }
                except (ValueError, LookupError, TypeError, OSError, sqlite3.Error) as error:
                    receipt = {
                        "source_id": sid,
                        "source_sha256": actual,
                        "failure_type": type(error).__name__,
                        "scientific_publication": "NOT_AUTHORIZED",
                    }
                with receipt_path.open("x") as handle:
                    json.dump(receipt, handle, indent=2)
                row["batch_execution"] = "FRESH_PROCESSING"
            row["receipt"] = str(receipt_path.relative_to(ROOT))
            row["outcome"] = (
                "FAILED" if receipt.get("failure_type") else "STAGED_REVIEWABLE_PACKAGE"
            )
            row["propositions"] = len(receipt.get("extraction", {}).get("items", []))
            row["draft_entities"] = receipt.get("entities", 0)
            row["draft_values"] = receipt.get("values", 0)
            row["draft_statements"] = receipt.get("statements", {})
        else:
            row["outcome"] = (
                "FROZEN_HOLDOUT"
                if eligible and not partition_eligible and not final
                else "NOT_ELIGIBLE"
            )
        ledger.append(row)
    name = (
        "holdout_coverage.json"
        if final
        else "corpus_coverage.json"
        if revision == 1
        else f"corpus_coverage_v{revision}.json"
    )
    write(
        name,
        {
            "ledger": ledger,
            "counts": {
                "registry_sources": len(ledger),
                "domain_candidates": sum(r["candidate"] for r in ledger),
                "outcomes": Counter(r["outcome"] for r in ledger),
                "candidate_acquired": sum(r["candidate"] and r["acquired"] for r in ledger),
                "candidate_searchable": sum(r["candidate"] and r["searchable"] for r in ledger),
                "draft_entities": sum(r.get("draft_entities", 0) for r in ledger),
                "draft_values": sum(r.get("draft_values", 0) for r in ledger),
                "propositions": sum(r.get("propositions", 0) for r in ledger),
                "fresh_model_calls": new_calls,
                "new_scientific_publications": 0,
            },
            "limits": [
                "Metadata/title triage is not expert scientific relevance.",
                "Packages and propositions are staged, not approved scientific findings.",
                "Bounded extraction does not mean full-document scientific completeness.",
            ],
        },
    )
    print(
        json.dumps(
            {
                "sources": len(ledger),
                "outcomes": Counter(r["outcome"] for r in ledger),
                "fresh_model_calls": new_calls,
            }
        )
    )
    registry.db.close()
    original.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["freeze", "integrity", "index", "corpus", "holdout", "quality", "audit"]
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--revision", type=int, default=1)
    args = parser.parse_args()
    {
        "freeze": freeze,
        "integrity": integrity,
        "index": lambda: index(args.revision),
        "quality": lambda: quality(args.revision),
        "audit": audit,
        "corpus": lambda: corpus(args.live, revision=args.revision),
        "holdout": lambda: corpus(args.live, final=True),
    }[args.action]()
