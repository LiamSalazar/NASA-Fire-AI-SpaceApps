"""The refusal fallback stays on by default; "0" keeps a decline as a recorded refusal."""

import os

from nasa_fire_ai.config import Settings


def test_on_unless_set_to_zero():
    expected = os.getenv("ANTHROPIC_SCIENCE_REFUSAL_FALLBACK", "1") == "1"
    assert Settings().anthropic_science_refusal_fallback is expected
    assert (
        Settings(anthropic_science_refusal_fallback=False).anthropic_science_refusal_fallback
        is False
    )
