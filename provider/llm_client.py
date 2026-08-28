"""OpenAI-compatible LLM client (chat/completions) — the real generation path.

The migration deferred LLM resolution to "Hermes runtime_provider"; this module
is the concrete client that makes the system actually generate prose. It speaks
the OpenAI ``/v1/chat/completions`` shape, so one code path serves OpenAI,
OpenRouter, Gemini's OpenAI-compatible endpoint, and local servers (LM Studio,
Ollama's OpenAI shim, vLLM) — just change ``base_url`` + ``model`` + ``api_key``.

Security: the API key lives only in the in-memory config and the gitignored
settings file / environment. It is never logged, echoed, or returned by the API.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import httpx

_LOG = logging.getLogger("novelkit.provider.llm_client")

#: HTTP statuses that mean "this provider cannot serve the request right now",
#: as opposed to "this request is wrong". Only these trigger failover.
#:
#: - 401/403: key revoked or lacks entitlement for the model
#: - 402: payment required — the managed key ran out of credit
#: - 404: gateway does not host this model
#: - 408/409: upstream timeout / conflict
#: - 429: quota or rate limit exhausted
#: - 5xx: gateway is down or the upstream vendor is failing
#:
#: 400 and 422 are excluded on purpose: a malformed prompt fails identically
#: everywhere, so retrying it just spends the standby's quota for nothing.
FAILOVER_STATUS = frozenset({401, 402, 403, 404, 408, 409, 429}) | frozenset(
    range(500, 600)
)


class LLMError(RuntimeError):
    """Raised when a completion call fails (network, auth, or API error)."""


class LLMNotConfigured(LLMError):
    """Raised when no API key / model / base_url is configured."""


class LLMFailover(LLMError):
    """Internal marker: this endpoint failed in a way a standby could survive.

    Never escapes :meth:`LLMClient.complete` — it is caught there to advance to
    the next endpoint in the chain. When the whole chain is exhausted it is
    re-raised as :class:`LLMChainExhausted`, which is still an :class:`LLMError`
    so existing callers behave as before, but is distinguishable for callers that
    must not re-walk the chain.
    """


class LLMChainExhausted(LLMError):
    """Every endpoint in the failover chain failed with a provider-level fault.

    Subclasses :class:`LLMError`, so existing ``except LLMError`` handlers keep
    working unchanged. Callers that wrap :meth:`LLMClient.complete` in their OWN
    retry ladder should catch this and stop: the two loops otherwise MULTIPLY
    (5 endpoints x 3 token budgets = 15 HTTP attempts), and ``run_step`` holds the
    per-novel run lock for every second of it — which the UI surfaces as the next
    click being silently rejected as ``alreadyRunning``.

    Retrying is pointless here for a second reason: the chain already tried every
    configured vendor, so a bigger token budget cannot help when nothing answered.
    """


#: Smallest per-endpoint timeout slice, in seconds. The chain shares ONE call
#: budget instead of granting every endpoint the full timeout, but a slice that is
#: too small would abort a request the provider was about to answer — turning a
#: slow success into a guaranteed failure. When the configured timeout cannot be
#: divided without going below this floor, fewer endpoints are attempted rather
#: than giving each an unusable slice.
MIN_ENDPOINT_TIMEOUT = 30.0


class LLMTruncated(LLMError):
    """Raised when the model stopped because it hit the token ceiling.

    ``finish_reason == "length"`` means the answer was cut off mid-stream, so
    the visible text is incomplete even when it is non-empty. The partial text
    is preserved on :attr:`partial` so callers can retry with a bigger budget
    (or salvage the fragment) instead of silently writing a truncated file.
    """

    def __init__(self, message: str, partial: str = ""):
        super().__init__(message)
        self.partial = partial


@dataclass
class LLMConfig:
    """Connection + sampling config for an OpenAI-compatible endpoint."""

    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    temperature: float = 0.8
    # Output ceiling per call. Set near the model's max output so long canon
    # files / chapter prose are not truncated mid-document. If a specific model
    # rejects a value this high the gateway clamps it; the truncation-retry in
    # the loop then salvages/escalates, so no visible text is silently lost.
    max_tokens: int = 16384
    timeout: float = 600.0
    extra_headers: dict[str, str] = field(default_factory=dict)
    # Optional metering hook. When set, each successful completion invokes it
    # with (input_tokens, output_tokens) parsed from the response ``usage``
    # block. Managed-provider mode uses this to debit the user's credit balance;
    # the creative pipeline stays unaware of billing (it just calls complete()).
    usage_sink: Optional[Callable[[int, int], None]] = None
    # Ordered standby endpoints tried when THIS config fails with a provider-level
    # error (see :data:`FAILOVER_STATUS`). Only the managed "gói NovelKit" lane
    # populates this: a user's own key has nowhere to fall back to, and silently
    # sending their prompt to a different vendor would be wrong. Each entry is a
    # complete config (own base_url/model/key), so a standby may be a different
    # vendor entirely. ``usage_sink`` is inherited from this config at call time
    # so credit is still metered when a standby serves the request.
    fallbacks: list["LLMConfig"] = field(default_factory=list)

    @property
    def configured(self) -> bool:
        """True when there is enough to attempt a call (key + model + url)."""
        return bool(self.api_key and self.model and self.base_url)

    def masked(self) -> dict[str, Any]:
        """Public view: key reduced to a fingerprint, never the secret."""
        key = self.api_key or ""
        if len(key) <= 8:
            fingerprint = "set" if key else ""
        else:
            fingerprint = f"{key[:3]}…{key[-4:]}"
        return {
            "base_url": self.base_url,
            "model": self.model,
            "api_key_set": bool(key),
            "api_key_fingerprint": fingerprint,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "configured": self.configured,
        }


_FULL_ENDPOINT_SUFFIXES = (
    "/chat/completions",
    "/completions",
    "/messages",
    "/responses",
    "/api/chat",
)


def validate_llm_base_url(base_url: str) -> str:
    """Return a trimmed LLM endpoint URL when its transport is safe.

    Production traffic must use HTTPS. Local HTTP endpoints are available only
    behind an explicit server-side development flag and only for loopback hosts.
    """
    value = (base_url or "").strip()
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("LLM base URL must be an absolute URL without credentials")
    if parsed.scheme.lower() == "https":
        return value
    loopback_hosts = {"localhost", "127.0.0.1", "::1"}
    if (
        os.environ.get("NOVELKIT_ALLOW_INSECURE_LLM_URLS") == "1"
        and parsed.scheme.lower() == "http"
        and parsed.hostname.lower() in loopback_hosts
    ):
        return value
    raise ValueError(
        "LLM base URL must use HTTPS; loopback HTTP requires "
        "NOVELKIT_ALLOW_INSECURE_LLM_URLS=1"
    )


def resolve_endpoint(base_url: str) -> str:
    """Return a POST URL — full endpoint as-is, or base + ``/chat/completions``."""
    url = base_url.rstrip("/")
    if any(url.endswith(suffix) for suffix in _FULL_ENDPOINT_SUFFIXES):
        return url
    if ":generateContent" in url:
        return url
    return f"{url}/chat/completions"


class LLMClient:
    """Thin synchronous OpenAI-compatible chat client (httpx-backed).

    Construct with an :class:`LLMConfig`. Use :func:`provider.settings.load_config`
    to build one from the saved secrets file / environment.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        if config is None:
            from . import settings as _settings

            config = _settings.load_config()
        self.config = config

    @property
    def configured(self) -> bool:
        return self.config.configured

    def _endpoint(self) -> str:
        return resolve_endpoint(self.config.base_url)

    def complete(
        self,
        *,
        system: Optional[str] = None,
        user: str = "",
        messages: Optional[list[dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Run one chat completion and return the assistant text.

        Provide either ``messages`` or ``system`` + ``user``. Raises
        :class:`LLMError` on any failure (never leaks the key in the message).

        When :attr:`LLMConfig.fallbacks` is populated (managed lane only) and the
        primary endpoint fails with a *provider-level* fault — exhausted quota,
        revoked key, gateway 5xx, network timeout — the same request is retried on
        each standby in order. A run therefore survives the managed key running
        dry instead of hard-failing mid-chapter.

        Deliberately NOT failed over: :class:`LLMTruncated` and empty content.
        Both mean the provider answered and the tokens were spent; the cause is
        the token budget, so another vendor would fail identically while charging
        the user twice. Those stay with the caller's existing escalate/salvage.
        """
        if not self.config.configured:
            raise LLMNotConfigured(
                "LLM is not configured — set base_url, model and API key in Settings."
            )
        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})

        chain, slice_timeout = self._plan_chain()
        last: LLMError | None = None
        for index, cfg in enumerate(chain):
            try:
                return self._attempt(
                    cfg,
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    usage_sink=self.config.usage_sink,
                    timeout=slice_timeout,
                )
            except LLMFailover as exc:
                last = exc
                remaining = len(chain) - index - 1
                _LOG.warning(
                    "provider %s/%s failed (%s) — %s",
                    index + 1, len(chain), exc,
                    f"trying standby {index + 2}/{len(chain)}" if remaining
                    else "no standby left",
                )
                continue
        # Every endpoint in the chain raised a failover-class error. Reported as
        # LLMChainExhausted so an outer retry ladder can stop instead of walking
        # the whole chain again for each of its own attempts.
        raise LLMChainExhausted(
            str(last) if last else "LLM request failed"
        ) from None

    def _usable_fallbacks(self) -> list[LLMConfig]:
        """Configured standby endpoints, skipping incomplete ones."""
        return [cfg for cfg in (self.config.fallbacks or []) if cfg.configured]

    def _plan_chain(self) -> tuple[list[LLMConfig], float]:
        """The endpoints to try and the per-endpoint timeout slice.

        The chain shares ONE time budget — the configured ``timeout`` — instead of
        granting each endpoint the full value. Without this, adding standbys
        multiplies the worst case of a failing call (5 x 600s = 50 minutes), and
        ``run_step`` holds the per-novel run lock throughout.

        The slice never drops below :data:`MIN_ENDPOINT_TIMEOUT`; when the budget
        cannot cover every endpoint at that floor, the chain is truncated instead,
        because a slice too short to complete a request converts a slow success
        into a certain failure.
        """
        chain = [self.config, *self._usable_fallbacks()]
        budget = float(self.config.timeout or 0) or MIN_ENDPOINT_TIMEOUT
        if len(chain) == 1:
            return chain, budget
        affordable = max(1, int(budget // MIN_ENDPOINT_TIMEOUT))
        if affordable < len(chain):
            _LOG.warning(
                "timeout budget %.0fs fits only %s of %s endpoints at the %.0fs "
                "floor — trying the first %s",
                budget, affordable, len(chain), MIN_ENDPOINT_TIMEOUT, affordable,
            )
            chain = chain[:affordable]
        return chain, budget / len(chain)

    def _attempt(
        self,
        cfg: LLMConfig,
        messages: list[dict[str, str]],
        *,
        temperature: Optional[float],
        max_tokens: Optional[int],
        usage_sink: Optional[Callable[[int, int], None]],
        timeout: Optional[float] = None,
    ) -> str:
        """One completion against ONE endpoint.

        Raises :class:`LLMFailover` for faults another endpoint could plausibly
        serve, and plain :class:`LLMError` / :class:`LLMTruncated` for faults that
        are about this request rather than this provider.

        ``timeout`` is this endpoint's slice of the shared chain budget (see
        :meth:`_plan_chain`); it falls back to the config value when called
        directly.
        """
        try:
            endpoint = resolve_endpoint(validate_llm_base_url(cfg.base_url))
        except ValueError as exc:
            raise LLMError(str(exc)) from None
        api_key = (cfg.api_key or "").strip()
        payload: dict[str, Any] = {
            "model": cfg.model,
            "messages": messages,
            "temperature": (
                temperature if temperature is not None else cfg.temperature
            ),
            "max_tokens": max_tokens or cfg.max_tokens,
            # Some OpenAI-compatible gateways default to SSE when omitted; we need
            # a single JSON object so resp.json() can read choices[0].message.content.
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **cfg.extra_headers,
        }
        try:
            # A local desktop runtime must not inherit host proxy variables.
            # Besides routing private prompts unexpectedly, an unbracketed IPv6
            # entry such as ``::1`` in NO_PROXY makes some httpx versions reject
            # client construction with ``Invalid port: ':1'``.
            with httpx.Client(
                timeout=cfg.timeout if timeout is None else timeout,
                trust_env=False,
            ) as client:
                resp = client.post(endpoint, headers=headers, json=payload)
        except httpx.HTTPError as exc:  # network/timeout — scrub any key echo
            raise LLMFailover(f"LLM request failed: {type(exc).__name__}") from None

        if resp.status_code >= 400:
            detail = _safe_error_detail(resp)
            if resp.status_code == 401:
                detail = (
                    f"{detail} — kiểm tra API key đúng provider (C-PROVIDER: key từ ckey.vn; "
                    "S-PROVIDER: key ShopAIKey), model đúng catalog (vd. claude-sonnet-4.6), "
                    "và đã Save sau khi đổi tab."
                )
            message = f"LLM API error {resp.status_code}: {detail}"
            if resp.status_code in FAILOVER_STATUS:
                raise LLMFailover(message)
            raise LLMError(message)

        try:
            data = _parse_completion_json(resp)
            choice = data["choices"][0]
            message_obj = choice["message"]
            content = message_obj.get("content") or ""
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            # A malformed body means this gateway is misbehaving, not that the
            # request is bad — a standby can serve it.
            raise LLMFailover(
                f"Unexpected LLM response shape: {type(exc).__name__}"
            ) from None

        finish = choice.get("finish_reason") if isinstance(choice, dict) else None
        message = message_obj

        # Meter token usage before any raise: the tokens were already spent by
        # the gateway even when the answer is empty/truncated. Managed mode uses
        # this to debit credit; failures in the sink must never break the call.
        if usage_sink is not None:
            usage = data.get("usage") if isinstance(data, dict) else None
            if isinstance(usage, dict):
                try:
                    in_tok = int(usage.get("prompt_tokens") or 0)
                    out_tok = int(usage.get("completion_tokens") or 0)
                    usage_sink(in_tok, out_tok)
                except Exception:  # noqa: BLE001 — metering must not break generation
                    pass

        # Reasoning models (e.g. DeepSeek "pro"/"flash") spend tokens on a hidden
        # ``reasoning_content`` field; if the budget is exhausted before any
        # visible answer, ``content`` comes back empty. Surface that clearly
        # (instead of silently returning "") so callers can raise max_tokens.
        if not content.strip():
            hint = (
                " (model trả lời rỗng — có thể đã dùng hết token cho 'reasoning'; "
                "hãy tăng max_tokens)"
                if message.get("reasoning_content") or finish == "length"
                else ""
            )
            raise LLMError(f"LLM returned empty content{hint}")

        # ``finish_reason == "length"`` with *non-empty* content means the answer
        # was cut off mid-stream: the trailing part of the document is missing.
        # Previously this branch fell through to ``return content`` and the
        # truncated text was written to disk silently. Raise so the caller can
        # retry with a larger budget (the partial text is preserved for salvage).
        if finish == "length":
            raise LLMTruncated(
                "LLM output bị cắt do chạm trần token (finish_reason=length); "
                "hãy tăng max_tokens.",
                partial=content,
            )
        return content

    def test_connection(self) -> dict[str, Any]:
        """Cheap liveness probe — a tiny completion. Returns {ok, detail}."""
        try:
            text = self.complete(
                system="You are a connectivity probe.",
                user="Reply with the single word: OK",
                max_tokens=256,
                temperature=0,
            )
            return {"ok": True, "detail": (text or "").strip()[:40] or "OK"}
        except LLMError as exc:
            return {"ok": False, "detail": str(exc)}


def _parse_completion_json(resp: httpx.Response) -> dict[str, Any]:
    """Parse a chat completion body — plain JSON or SSE ``data:`` chunks."""
    content_type = (resp.headers.get("content-type") or "").lower()
    text = resp.text
    if "text/event-stream" not in content_type and not text.lstrip().startswith("data:"):
        parsed = resp.json()
        if not isinstance(parsed, dict):
            raise TypeError("completion body is not a JSON object")
        return parsed

    last: Optional[dict[str, Any]] = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        chunk = json.loads(payload)
        if isinstance(chunk, dict):
            last = chunk
    if last is None:
        raise json.JSONDecodeError("no SSE data chunk", text, 0)
    return last


def _safe_error_detail(resp: httpx.Response) -> str:
    """Extract a short error message without ever surfacing request headers."""
    try:
        body = resp.json()
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])[:200]
            if isinstance(err, str):
                return err[:200]
        return json.dumps(body)[:200]
    except (json.JSONDecodeError, ValueError):
        return resp.text[:200]
