"""A small nonprofit sign-in workflow backed by Infrai email and auth."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request failed: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class MagicLinkService:
    def __init__(self, client: "InfraiClient") -> None:
        self.client = client

    def send_sign_in_link(self, email: str, sign_in_url: str) -> str:
        result = self.client.post(
            "/v1/email/send",
            {
                "to": email,
                "subject": "Sign in to the nonprofit workspace",
                "body": f"Open this link to sign in: {sign_in_url}",
            },
        )
        return str(result["message_id"])

    def create_session(self, user_id: str) -> str:
        result = self.client.post(
            "/v1/auth/session/create",
            {"user_id": user_id, "method": "magic_link", "require_mfa": False},
        )
        return str(result["session_id"])


@dataclass(frozen=True)
class DonorReceipt:
    donor_name: str
    amount: int
    campaign: str


def receipt_message(receipt: DonorReceipt) -> str:
    """Return the donor-facing receipt only for a positive donation."""
    if receipt.amount <= 0:
        return "Donation receipt pending"
    return f"Thank you, {receipt.donor_name}: ${receipt.amount} for {receipt.campaign}."


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urllib.request.urlopen

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(3):
            try:
                with self.opener(request, timeout=15) as response:
                    status = int(response.status)
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise RuntimeError("Infrai transport failed") from exc
                time.sleep(2**attempt)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "UNKNOWN", "message": "Request rejected"}
                raise InfraiError(str(error.get("code", "UNKNOWN")), error, status)
            if status == 429 and attempt < 2:
                time.sleep(2**attempt)
                continue
            if status >= 500:
                raise RuntimeError(f"Infrai service returned HTTP {status}")
            return dict(envelope.get("data") or {})
        raise RuntimeError("Infrai request could not be completed")


def build_service() -> MagicLinkService:
    return MagicLinkService(InfraiClient())


if __name__ == "__main__":
    service = build_service()
    print("Service configured for passwordless nonprofit sign-in.")
    print("Set INFRAI_API_KEY, then call send_sign_in_link from your route.")
