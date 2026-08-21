from __future__ import annotations

import json
from pathlib import Path

import pytest

from main import answer_question, setup_tracing


SMOKE_INPUTS: list[str] = json.loads(
    (Path(__file__).parent / "smoke_inputs.json").read_text(encoding="utf-8")
)

#used to log traces onto phoenix during test, this is not mandatory
@pytest.fixture(scope="module", autouse=True)
def phoenix_tracing() -> None:
    """Export the live smoke-test traces to Phoenix."""
    setup_tracing()


@pytest.mark.parametrize("query", SMOKE_INPUTS)
def test_live_municipal_question_returns_non_empty_text(query: str) -> None:
    """Liveness only: no assertion is made about factual answer quality."""
    answer = answer_question(query)

    assert isinstance(answer, str)
    assert answer.strip()
