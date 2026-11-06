"""Shared HTTP source for firmware release catalogs and manifests."""

from __future__ import annotations

from typing import Any

import requests


class ReleaseSource:
    """Fetch GitHub release catalogs and JSON manifests from their source URLs."""

    RELEASES_URL = "https://api.github.com/repos/happydasch/nspanel_haui/releases?per_page=100"

    @staticmethod
    def fetch_json(url: str, timeout: float) -> Any:
        """GET ``url`` and decode its JSON body.

        Raises:
            requests.exceptions.RequestException: On a network/HTTP failure.
            ValueError: When the body is not JSON.
        """
        response = requests.get(url, timeout=timeout)
        return response.json()
