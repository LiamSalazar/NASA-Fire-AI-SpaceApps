"""The phase-2 campaign configuration keeps the origin mark on (invented names only, B8)."""

import re
from pathlib import Path

CONFIG = (
    Path(__file__).resolve().parent.parent
    / "artifacts/phase1_generalizable_ingestion/v6/milestone14/campaign/PHASE2_CAMPAIGN_CONFIG.md"
)


def campaign_env():
    text = CONFIG.read_text(encoding="utf-8")
    block = re.search(r"```campaign-env\n(.*?)```", text, re.DOTALL)
    assert block, "the campaign configuration has no campaign-env block"
    pairs = [line.split("=", 1) for line in block.group(1).split("\n") if "=" in line]
    return {k.strip(): v.strip() for k, v in pairs}


def test_the_value_origin_mark_is_on_in_the_campaign():
    assert campaign_env().get("SCIENCE_VALUE_ORIGIN_MARK") == "1"


def test_the_flags_the_config_turns_on_are_read_by_the_code():
    root = Path(__file__).resolve().parent.parent / "src"
    source = " ".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
    for name in campaign_env():
        assert f'"{name}"' in source, name
