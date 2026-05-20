from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

from shared.config.runtime import get_required_env, load_dotenv

BASE_URL = "https://app.asana.com/api/1.0"


class AsanaClient:
    """
    Minimal Asana client for OpenClaw.

    MVP policy:
    - Read-only by default
    - GET requests allowed
    - Non-GET requests blocked when ASANA_MODE=read_only
    """

    def __init__(self) -> None:
        load_dotenv()
        self.token = get_required_env("ASANA_ACCESS_TOKEN")
        self.mode = os.getenv("ASANA_MODE", "read_only")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _block_write(self, method: str) -> None:
        if self.mode == "read_only" and method.upper() != "GET":
            raise PermissionError(
                "Asana write actions are disabled because ASANA_MODE=read_only."
            )

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._block_write("GET")

        url = f"{BASE_URL}{path}"

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params=params or {},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Asana GET request failed: {response.status_code} {response.text}"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Asana request failed: {exc}") from exc

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._block_write("POST")
        raise NotImplementedError("POST is not implemented for the read-only MVP.")

    def put(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._block_write("PUT")
        raise NotImplementedError("PUT is not implemented for the read-only MVP.")

    def delete(self, path: str) -> Dict[str, Any]:
        self._block_write("DELETE")
        raise NotImplementedError("DELETE is not implemented for the read-only MVP.")

    def ensure_write_allowed(self) -> None:
        if (os.getenv("ASANA_MODE") or "read_only").strip() == "read_only":
            raise Exception("Write operations disabled")
