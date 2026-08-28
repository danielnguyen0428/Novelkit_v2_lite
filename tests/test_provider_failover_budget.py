"""The failover chain must not multiply the wall clock of a failing step.

``LLMClient.complete`` walks the standby chain, and callers in the creative loop
wrap ``complete`` in their OWN retry ladder (e.g. ``_bootstrap_one_file`` retries
three token budgets). Those two loops MULTIPLY: 5 endpoints x 3 budgets = 15 HTTP
attempts, each previously allowed the full per-endpoint timeout.

That matters beyond wasted time. ``run_step`` holds the per-novel run lock for the
whole request, so every extra second is a second where the next click is rejected
as ``alreadyRunning`` — which the UI renders as nothing at all. These tests pin
two guarantees:

* an exhausted chain reports itself, so a caller's retry ladder can stop instead
  of re-walking every endpoint;
* the whole chain fits inside ONE per-call time budget rather than each endpoint
  getting the full timeout.
"""

from __future__ import annotations

import httpx
import pytest

from provider.llm_client import (
    MIN_ENDPOINT_TIMEOUT,
    LLMChainExhausted,
    LLMClient,
    LLMConfig,
    LLMError,
)


def _chain(n: int, **kw) -> LLMConfig:
    """A primary config with ``n - 1`` standbys."""
    return LLMConfig(
        base_url="https://p1.example/v1", model="m1", api_key="k1",
        fallbacks=[
            LLMConfig(base_url=f"https://p{i}.example/v1", model=f"m{i}",
                      api_key=f"k{i}")
            for i in range(2, n + 1)
        ],
        **kw,
    )


class _Probe:
    """Records the timeout handed to each httpx.Client and always fails 503."""

    def __init__(self, response: httpx.Response | None = None):
        self.timeouts: list[float] = []
        self.hosts: list[str] = []
        self._response = response

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.hosts.append(request.url.host)
        if self._response is not None:
            return self._response
        return httpx.Response(503, json={"error": "upstream down"})

    def install(self, monkeypatch):
        transport = httpx.MockTransport(self._handler)
        original = httpx.Client

        def _client(*_a, **kw):
            self.timeouts.append(kw.get("timeout"))
            kw.pop("transport", None)
            return original(transport=transport, **kw)

        monkeypatch.setattr(httpx, "Client", _client)
        return self


def test_exhausted_chain_raises_a_distinguishable_error(monkeypatch):
    """A caller must be able to tell "every endpoint failed" from "this one did".

    Without this, an outer retry ladder re-walks all 5 endpoints for every one of
    its own attempts.
    """
    probe = _Probe().install(monkeypatch)

    with pytest.raises(LLMChainExhausted):
        LLMClient(_chain(5)).complete(user="viết đi")

    assert len(probe.hosts) == 5, probe.hosts
    # Still an LLMError, so every existing `except LLMError` keeps working.
    assert issubclass(LLMChainExhausted, LLMError)


def test_chain_shares_one_time_budget(monkeypatch):
    """Each endpoint gets a SLICE of the call budget, not the full timeout.

    Five endpoints at the 600s production default is a 50-minute worst case for a
    single completion, and the run lock is held for all of it.
    """
    probe = _Probe().install(monkeypatch)

    with pytest.raises(LLMError):
        LLMClient(_chain(5, timeout=600.0)).complete(user="viết đi")

    assert len(probe.timeouts) == 5
    # The whole chain must fit in the configured timeout, not 5x it.
    assert sum(probe.timeouts) <= 600.0 + 1e-6, probe.timeouts
    # And no slice may be so short the request cannot realistically finish.
    assert min(probe.timeouts) >= MIN_ENDPOINT_TIMEOUT, probe.timeouts


def test_single_endpoint_keeps_the_full_timeout(monkeypatch):
    """A user's own key (no standbys) must not be given a shortened timeout."""
    probe = _Probe(
        httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"},
                               "finish_reason": "stop"}]},
        )
    ).install(monkeypatch)

    solo = LLMConfig(base_url="https://only.example/v1", model="m",
                     api_key="k", timeout=600.0)
    assert LLMClient(solo).complete(user="x") == "ok"
    assert probe.timeouts == [600.0]


def test_chain_truncated_rather_than_sliced_below_the_floor(monkeypatch):
    """A short timeout must not hand every endpoint an unusable slice.

    Slicing 60s across 5 endpoints would give each 12s — long enough to guarantee
    a timeout on a real generation, turning a slow success into 5 certain
    failures. Trying fewer endpoints properly beats trying all of them uselessly.
    """
    probe = _Probe().install(monkeypatch)

    with pytest.raises(LLMError):
        LLMClient(_chain(5, timeout=60.0)).complete(user="x")

    assert len(probe.timeouts) == 2, probe.timeouts
    assert min(probe.timeouts) >= MIN_ENDPOINT_TIMEOUT, probe.timeouts
