#!/usr/bin/env python3
"""Cache the current official standard and create conservative, page-backed safety records."""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.models import EvidenceReference, SafetyStatementRecord

STANDARD_URL = "https://standards.nasa.gov/sites/default/files/standards/NASA/B-w/CHANGE-3/3/2025_06_25_NASA-STD-6001B_w_Change_3_FINAL_Admin-Change-FINAL.pdf"
RAW = ROOT / "data/raw/nasa-std-6001-change3.pdf"


def evidence(evidence_id, source_id, page, section):
    return [
        EvidenceReference(evidence_id=evidence_id, source_id=source_id, page=page, section=section)
    ]


def statement(statement_id, statement_type, text, source, page, section, scope=None):
    return SafetyStatementRecord(
        statement_id=statement_id,
        statement_type=statement_type,
        normalized_text=text,
        source_document=source,
        source_page=page,
        source_section=section,
        scope_applicability=scope,
        evidence_refs=evidence(f"E-safety-{statement_id}", source, page, section),
    ).model_dump(mode="json")


def main():
    if not RAW.exists():
        request = urllib.request.Request(
            STANDARD_URL, headers={"User-Agent": "nasa-fire-ai-mvp/0.1"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            RAW.write_bytes(response.read())
    records = [
        {
            "type": "InterventionRecord",
            "id": "saffire-iv-flow-off-20s",
            "description": "For the Saffire-IV PMMA sample, we turned off the flow for 20 seconds.",
            "source_document": "ntrs-20205007829",
            "source_page": 16,
            "source_section": "Fire Suppression Requirements",
            "evidence_refs": [
                item.model_dump(mode="json")
                for item in evidence(
                    "E-safety-saffire-intervention",
                    "ntrs-20205007829",
                    16,
                    "Fire Suppression Requirements",
                )
            ],
        },
        {
            "type": "ObservationRecord",
            "id": "saffire-iv-flow-off-observation",
            "phenomenon": "Flame persistence",
            "text": "The fire didn’t extinguish and began to grow when we turned the flow back on.",
            "source_document": "ntrs-20205007829",
            "source_page": 16,
            "source_section": "Fire Suppression Requirements",
            "evidence_refs": [
                item.model_dump(mode="json")
                for item in evidence(
                    "E-safety-saffire-observation",
                    "ntrs-20205007829",
                    16,
                    "Fire Suppression Requirements",
                )
            ],
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "saffire-suppression-conclusion",
                "nasa_conclusion",
                "In a spacecraft, suppressant could have been used to ‘knock down’ the fire but wasn’t held at the desired concentration long enough for surface to cool.",
                "ntrs-20205007829",
                16,
                "Fire Suppression Requirements",
            ),
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "saffire-suppression-open-question",
                "open_question",
                "Additional focused tests may be required to develop guidance on these questions.",
                "ntrs-20205007829",
                16,
                "Fire Suppression Requirements",
                "Qualification of spacecraft fire suppression under micro- or partial-gravity and suppressant concentration/hold time",
            ),
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "suppression-system-implication",
                "safety_implication",
                "Given that a fire may propagate in spite of early detection and initial response, there is a possibility that an active fire suppression system will need to be activated.",
                "ntrs-20205007829",
                7,
                "Risks for Fire Safety",
                "Fire suppression",
            ),
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "std-6001-applicability",
                "requirement",
                "Materials intended for use in space vehicles, specified test facilities, and contractually specified Ground Support Equipment (GSE) shall meet the requirements of this NASA Technical Standard.",
                "nasa-std-6001",
                8,
                "1.2.1 Applicability",
                "Materials intended for stated uses",
            ),
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "std-6001-worst-case-test",
                "test_criterion",
                "Required tests shall be conducted on materials in their worst-case exposure conditions and representative use thicknesses and product forms.",
                "nasa-std-6001",
                17,
                "5 Applicable Material Tests",
                "Required material tests",
            ),
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "configuration-guidance",
                "guidance",
                "The document provides guidance in conducting the flammability assessments required for payload hardware by SSP 51700.",
                "ntrs-20150020937",
                2,
                "Preface",
                "Payload hardware flammability assessment",
            ),
        },
        {
            "type": "SafetyStatementRecord",
            **statement(
                "configuration-design-criterion",
                "design_criterion",
                "It means controlling the quantity and configuration of such materials to eliminate potential fire propagation paths and thus ensure that any fire would be small, localized, and isolated, and would self-extinguish without harm to the crew.",
                "ntrs-20150020937",
                1,
                "1.0 Introduction",
                "Crewed spacecraft fire control",
            ),
        },
    ]
    out = ROOT / "data/canonical/safety_records.json"
    out.write_text(json.dumps(records, indent=2))
    print(
        json.dumps(
            {
                "records": len(records),
                "standard_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
