"""NovelKit provider seam — Hermes runtime_provider configuration.

Phase 4 of the migration (Task 11.1, finding D6). The legacy NovelKit provider
stack — ``llm_config.py`` + ``gemini_key_pool.py`` + ``gemini_pool_status.py`` +
``google_genai_compat.py`` plus the hand-rolled failover chain — is **removed**,
not ported. Provider resolution (18+ providers, credential pools, aliases) is
delegated to Hermes ``runtime_provider``. This package only declares the
creative-lane policy + ordered failover preference (``config/provider.json``)
and exposes a thin resolver that turns that declaration into an ordered provider
chain for Hermes to execute.
"""

from provider.resolver import (
    PROVIDER_CONFIG_PATH,
    ProviderProfile,
    creative_lane_requires_style_audit,
    is_placeholder_credential,
    load_provider_config,
    resolve_provider_chain,
)

__all__ = [
    "PROVIDER_CONFIG_PATH",
    "ProviderProfile",
    "creative_lane_requires_style_audit",
    "is_placeholder_credential",
    "load_provider_config",
    "resolve_provider_chain",
]
