"""Stable, public origin metadata for NovelKit V2 Lite.

This module does not collect or transmit data.  It exposes a passive provenance
identifier so an unmodified deployment can be matched to the canonical source.
"""

from __future__ import annotations

from typing import Final

PROVENANCE_ID: Final = "NOVELKIT-V2-LITE-DN0428-20260828-12A133B9E572"
CANONICAL_REPOSITORY: Final = (
    "https://github.com/danielnguyen0428/Novelkit_v2_lite"
)
ORIGIN_COMMIT: Final = "12a133b9e5729ac221c014a2ec14cb6af251fef4"
COPYRIGHT_NOTICE: Final = "Copyright (c) 2026 Daniel Nguyen"
LICENSE_ID: Final = "LicenseRef-NovelKit-V2-Lite-NC-ND-1.0"


def public_provenance() -> dict[str, str | bool]:
    """Return non-secret provenance metadata; no runtime data is collected."""

    return {
        "product": "NovelKit V2 Lite",
        "version": "2.0.0-lite",
        "provenance_id": PROVENANCE_ID,
        "copyright": COPYRIGHT_NOTICE,
        "copyright_contact": "danielnguyen0428@gmail.com",
        "canonical_repository": CANONICAL_REPOSITORY,
        "origin_commit": ORIGIN_COMMIT,
        "license": LICENSE_ID,
        "telemetry": False,
    }
