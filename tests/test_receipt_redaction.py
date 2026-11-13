import importlib.util
import json
from pathlib import Path

import pytest

from nasa_fire_ai.llm.scientific_provider import redact_provider_text

ROOT = Path(__file__).resolve().parents[1]
# A synthetic key, built at run time so no key-shaped literal is committed.
KEY = "nvapi" + "-" + "synthetic0value"
MESSAGE = (
    "{'status': 404, 'title': 'Not Found', 'detail': \"Function 'f0': "
    "Not found for account 'AbC_-123xyz'\"}"
)


def live_run_script():
    spec = importlib.util.spec_from_file_location(
        "phase1_exposed_live_run", ROOT / "scripts" / "phase1_exposed_live_run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provider_text_hides_the_key_and_the_account_identifier():
    text = redact_provider_text(MESSAGE + " key " + KEY, KEY)
    assert "AbC_-123xyz" not in text and KEY not in text
    assert "account '[REDACTED]'" in text
    # The function identifier and the status stay: they diagnose the failure.
    assert "Function 'f0'" in text and "404" in text


def test_other_wording_is_left_as_written():
    for text in ("the accountant's note", "account was opened", "per account basis", ""):
        assert redact_provider_text(text) == text


def test_receipts_never_keep_an_account_identifier_or_a_key(tmp_path):
    script = live_run_script()
    script.write(tmp_path / "attempts.json", {"provider_message": MESSAGE})
    written = (tmp_path / "attempts.json").read_text(encoding="utf-8")
    assert "AbC_-123xyz" not in written
    assert json.loads(written)["provider_message"].endswith("account '[REDACTED]'\"}")
    with pytest.raises(RuntimeError):
        script.write(tmp_path / "key.json", {"note": KEY})
