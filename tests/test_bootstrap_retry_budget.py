"""The bootstrap retry ladder must not re-walk an exhausted failover chain.

``_bootstrap_one_file`` retries three escalating token budgets, and
``LLMClient.complete`` walks the standby chain inside each of those attempts. The
two loops multiply: with 5 endpoints that is 15 HTTP attempts for one file, and
``run_step`` holds the per-novel run lock for all of it.

The escalation exists for ONE failure mode — the answer was cut off at the token
ceiling. When instead *no endpoint answered at all*, a bigger budget cannot help,
so the ladder must stop after the first pass.
"""

from __future__ import annotations

from pathlib import Path

from integrations.autonovel.llm_loop import LLMAutoNovelLoop
from provider.llm_client import (
    LLMChainExhausted,
    LLMConfig,
    LLMError,
    LLMTruncated,
)


class _CountingClient:
    """Stands in for LLMClient, counting completes and raising a fixed error."""

    def __init__(self, error: Exception | None):
        self.config = LLMConfig(
            base_url="https://p.example/v1", model="m", api_key="k", max_tokens=8192
        )
        self.error = error
        self.calls = 0

    def complete(self, **_kw) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return "Nội dung thật."


def _run(loop: LLMAutoNovelLoop) -> tuple[str, str]:
    return loop._bootstrap_one_file(
        "Bạn là World Builder.",
        "Logline: thiếu niên trùng sinh.",
        "",
        "Tiếng Việt",
        "database/characters/main.md",
        "nhân vật chính",
    )


def _loop(error: Exception | None) -> tuple[LLMAutoNovelLoop, _CountingClient]:
    client = _CountingClient(error)
    return LLMAutoNovelLoop(client=client), client  # type: ignore[arg-type]


def test_exhausted_chain_stops_the_budget_ladder():
    """Nothing answered — escalating tokens cannot change that."""
    loop, client = _loop(LLMChainExhausted("every endpoint failed"))

    body, error = _run(loop)

    assert body == ""
    assert "every endpoint failed" in error
    assert client.calls == 1, (
        f"expected to stop after the exhausted chain, made {client.calls} passes"
    )


def test_truncation_still_escalates_the_budget():
    """The ladder's real purpose must survive the fix."""
    loop, client = _loop(LLMTruncated("cắt ở trần token", partial="Một phần."))

    body, error = _run(loop)

    assert client.calls == 3, "truncation must still escalate through all budgets"
    # The longest partial is salvaged rather than stubbing the file.
    assert body == "Một phần."
    assert error == ""


def test_single_endpoint_error_still_retries():
    """A plain LLMError (no chain involved) keeps the existing retry behaviour."""
    loop, client = _loop(LLMError("gateway timeout"))

    body, error = _run(loop)

    assert client.calls == 3
    assert body == ""
    assert "gateway timeout" in error


def test_success_on_the_first_attempt_makes_one_call():
    loop, client = _loop(None)

    body, error = _run(loop)

    assert (body, error) == ("Nội dung thật.", "")
    assert client.calls == 1
