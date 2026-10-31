import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


RAZORPAY_API = "https://api.razorpay.com/v1"


class RazorpayConfigurationError(ValueError):
    pass


class RazorpayGatewayError(RuntimeError):
    pass


def credentials() -> tuple[str, str]:
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    missing = [
        name
        for name, value in (
            ("RAZORPAY_KEY_ID", key_id),
            ("RAZORPAY_KEY_SECRET", key_secret),
        )
        if not value
    ]
    if missing:
        raise RazorpayConfigurationError(
            "Razorpay is not configured. Set " + " and ".join(missing) + "."
        )
    if not key_id.startswith("rzp_test_"):
        raise RazorpayConfigurationError(
            "Online checkout is restricted to Razorpay test-mode keys (rzp_test_*)."
        )
    return key_id, key_secret


def _request(method: str, endpoint: str, payload: dict | None = None) -> dict:
    key_id, key_secret = credentials()
    token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode("ascii")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{RAZORPAY_API}{endpoint}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            provider_error = json.loads(exc.read().decode("utf-8")).get("error", {})
            message = provider_error.get("description") or provider_error.get("reason")
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            message = None
        raise RazorpayGatewayError(
            message or f"Razorpay request failed with HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RazorpayGatewayError(
            "Could not reach Razorpay. Check the server connection and try again."
        ) from exc
    if not isinstance(result, dict):
        raise RazorpayGatewayError("Razorpay returned an invalid response.")
    return result


def create_order(amount: int, invoice_id: int) -> dict:
    return _request(
        "POST",
        "/orders",
        {
            "amount": amount,
            "currency": "INR",
            "receipt": f"invoice-{invoice_id}-{uuid4().hex[:16]}",
            "notes": {"invoice_id": str(invoice_id)},
        },
    )


def get_payment(payment_id: str) -> dict:
    return _request("GET", f"/payments/{payment_id}")
