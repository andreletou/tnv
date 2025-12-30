# paydunya.py
"""
PayDunya helper library (single-file) — v1.0
Usage: import PayDunya from this file and instantiate with your keys.

Features:
- create_payment_request (DMP)
- create_webpay_invoice
- get_payment_status
- verify_webhook (HMAC or basic signature helper)
- create_payout (single)
- create_batch_payout (batch; processed sequentially with optional concurrency)
- retry logic, configurable timeouts
- logging + exceptions

Dependencies:
- requests

Install: pip install requests

Notes:
- Verify endpoint paths and headers with your PayDunya account docs.
- Keep keys in env vars / secret manager, don't hardcode.
"""

import os
import time
import json
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Basic logger
logger = logging.getLogger("paydunya")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)


class PayDunyaError(Exception):
    pass


class PayDunya:
    """
    PayDunya client.

    Example:
        client = PayDunya(
            master_key=os.getenv("PAYDUNYA_MASTER_KEY"),
            private_key=os.getenv("PAYDUNYA_PRIVATE_KEY"),
            public_key=os.getenv("PAYDUNYA_PUBLIC_KEY"),
            base_url="https://api.paydunya.com/v1"  # configurable
        )

        # create DMP
        resp = client.create_payment_request(amount=5000, identifier="order-123", description="Achat", recipient_phone="+22890xxxxxx")

    Notes:
      - Adjust ENDPOINTS if PayDunya changes api paths.
      - By default this uses Authorization: Bearer <master_key>. If your account uses another header, change _default_headers.
    """

    # Default endpoints (modifiable if PayDunya changed them)
    ENDPOINTS = {
        "dmp_create": "/dmp/create",            # payment request (DMP)
        "webpay_create": "/webpay/v1/checkout", # WebPay (may vary)
        "invoice_status": "/invoices/{invoice_id}/status",
        "dmp_status": "/dmp/{identifier}/status",
        "payout_create": "/payouts/send",       # payout (may vary)
        "payout_status": "/payouts/{payout_id}/status",
        "balance": "/balance",
    }

    def __init__(
        self,
        master_key: str,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
        base_url: str = "https://api.paydunya.com/v1",
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        verify_ssl: bool = True,
    ):
        if not master_key:
            raise ValueError("master_key is required")

        self.master_key = master_key
        self.private_key = private_key
        self.public_key = public_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Session with retries
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # -------------------------
    # Helpers
    # -------------------------
    def _url(self, path_key: str, **kwargs) -> str:
        if path_key not in self.ENDPOINTS:
            raise PayDunyaError(f"Unknown endpoint key: {path_key}")
        path = self.ENDPOINTS[path_key].format(**kwargs)
        return f"{self.base_url}{path}"

    def _default_headers(self) -> Dict[str, str]:
        # Many PayDunya examples use 'Authorization: Bearer <MASTER_KEY>' — adjust here if needed.
        headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "paydunya-py/1.0",
        }
        return headers

    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", self.verify_ssl)
        headers = kwargs.pop("headers", {})
        merged_headers = {**self._default_headers(), **headers}
        try:
            resp = self.session.request(method, url, headers=merged_headers, **kwargs)
        except requests.RequestException as e:
            logger.exception("HTTP request failed")
            raise PayDunyaError(f"HTTP request failed: {e}") from e

        # Basic handling
        try:
            data = resp.json()
        except ValueError:
            text = resp.text or ""
            logger.error("Non-json response: %s", text[:500])
            raise PayDunyaError(f"Non-JSON response: HTTP {resp.status_code} - {text}")

        if not resp.ok:
            logger.error("API Error: %s %s", resp.status_code, data)
            # Normalize error message
            err = data.get("message") or data.get("errors") or data
            raise PayDunyaError(f"API Error ({resp.status_code}): {err}")

        return data

    # -------------------------
    # Core operations
    # -------------------------
    def create_payment_request(
        self,
        amount: int,
        identifier: str,
        description: Optional[str] = None,
        recipient_phone: Optional[str] = None,
        currency: str = "XOF",
        metadata: Optional[Dict[str, Any]] = None,
        send_notification: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a DMP (demande de paiement) / Payment Request.

        amount: integer (en centimes ou unité selon config; ici on expecte l'unité de la doc: ex: 5000)
        identifier: string unique (order id)
        recipient_phone: phone to send SMS (format international recommended)
        send_notification: whether to trigger SMS/email (if supported)

        Returns API response dict.
        """
        url = self._url("dmp_create")
        payload = {
            "amount": amount,
            "identifier": identifier,
            "currency": currency,
            "send_notification": 1 if send_notification else 0,
        }
        if description:
            payload["description"] = description
        if recipient_phone:
            payload["recipient_phone"] = recipient_phone
        if metadata:
            payload["metadata"] = metadata
        if extra:
            payload.update(extra)

        logger.info("Creating payment request %s amount=%s", identifier, amount)
        return self._request("POST", url, json=payload)

    def create_webpay_invoice(
        self,
        amount: int,
        identifier: str,
        description: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        split_rules: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a WebPay checkout invoice. Supports optional split_rules (if provider supports it).

        split_rules: list of dicts like [{"recipient": "merchant_account_id", "amount": 1000}, ...]
        """
        url = self._url("webpay_create")
        payload = {
            "amount": amount,
            "identifier": identifier,
        }
        if description:
            payload["description"] = description
        if return_url:
            payload["return_url"] = return_url
        if cancel_url:
            payload["cancel_url"] = cancel_url
        if metadata:
            payload["metadata"] = metadata
        if split_rules:
            payload["split_rules"] = split_rules
        if extra:
            payload.update(extra)

        logger.info("Creating webpay invoice %s amount=%s", identifier, amount)
        return self._request("POST", url, json=payload)

    def get_payment_status(self, identifier: Optional[str] = None, invoice_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check payment status.
        Provide either identifier (your id) or invoice_id (paydunya's invoice id).
        """
        if invoice_id and "invoice_status" in self.ENDPOINTS:
            url = self._url("invoice_status", invoice_id=invoice_id)
            logger.info("Checking invoice status invoice_id=%s", invoice_id)
            return self._request("GET", url)
        if identifier and "dmp_status" in self.ENDPOINTS:
            url = self._url("dmp_status", identifier=identifier)
            logger.info("Checking dmp status identifier=%s", identifier)
            return self._request("GET", url)
        raise ValueError("Provide either identifier or invoice_id to check status")

    # -------------------------
    # Payouts
    # -------------------------
    def create_payout(
        self,
        recipient_phone: str,
        amount: int,
        network: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a single payout (push to mobile money).
        network: e.g., 'MTN', 'ORANGEMONEY', 'FLOOZ', etc. Depending on provider.
        Returns API response dict.
        """
        url = self._url("payout_create")
        payload = {
            "recipient_phone": recipient_phone,
            "amount": amount,
        }
        if network:
            payload["network"] = network
        if metadata:
            payload["metadata"] = metadata

        logger.info("Creating payout to %s amount=%s", recipient_phone, amount)
        return self._request("POST", url, json=payload)

    def create_batch_payout(
        self,
        payouts: List[Dict[str, Any]],
        continue_on_error: bool = True,
        delay_between: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """
        Create multiple payouts. payouts: list of dicts each containing recipient_phone and amount (plus optional network/metadata).
        This function processes them sequentially with optional delay. Returns list of responses (or raises on fatal error depending on continue_on_error).
        """
        results = []
        for idx, p in enumerate(payouts):
            try:
                resp = self.create_payout(
                    recipient_phone=p["recipient_phone"],
                    amount=p["amount"],
                    network=p.get("network"),
                    metadata=p.get("metadata"),
                )
                results.append({"success": True, "response": resp, "index": idx})
            except Exception as e:
                logger.exception("Payout failed for index %s: %s", idx, e)
                results.append({"success": False, "error": str(e), "index": idx})
                if not continue_on_error:
                    raise
            time.sleep(delay_between)
        return results

    def get_payout_status(self, payout_id: str) -> Dict[str, Any]:
        if "payout_status" not in self.ENDPOINTS:
            raise PayDunyaError("payout_status endpoint not configured")
        url = self._url("payout_status", payout_id=payout_id)
        logger.info("Checking payout status %s", payout_id)
        return self._request("GET", url)

    # -------------------------
    # Balance
    # -------------------------
    def get_balance(self) -> Dict[str, Any]:
        if "balance" not in self.ENDPOINTS:
            raise PayDunyaError("balance endpoint not configured")
        url = self._url("balance")
        logger.info("Checking account balance")
        return self._request("GET", url)

    # -------------------------
    # Webhook / IPN verification helper
    # -------------------------
    def verify_webhook_hmac(self, raw_body: bytes, signature_header: str, secret: str) -> bool:
        """
        Verify a webhook signed by HMAC-SHA256. Many providers sign payloads.
        - raw_body: bytes received from request.body
        - signature_header: header value (e.g., 'sha256=...' or raw hex)
        - secret: your webhook secret (private key or configured secret)

        Returns True if signature matches.
        """
        if not secret:
            raise ValueError("secret is required to verify webhook")
        computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        # Accept header forms like 'sha256=abcd...' or plain hex
        sig = signature_header or ""
        if sig.startswith("sha256="):
            sig = sig.split("=", 1)[1]
        # timing-safe compare
        return hmac.compare_digest(computed, sig)

    def verify_signature_basic(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Example: some providers require computing signature from payload + private_key.
        This is a convenience helper — adapt to the exact algorithm in PayDunya docs.
        """
        if not self.private_key:
            raise ValueError("private_key required for this signature method")
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        computed = hmac.new(self.private_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    # -------------------------
    # Utilities
    # -------------------------
    def set_endpoint(self, key: str, path: str):
        """Override an endpoint path (useful if PayDunya updates routes)"""
        self.ENDPOINTS[key] = path

    def raw_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Make a raw request to base_url + path (path must start with '/').
        Useful for calling newer endpoints before updating this helper.
        """
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"
        return self._request(method, url, **kwargs)


# -------------------------
# Example usage (do not run in prod as-is)
# -------------------------
if __name__ == "__main__":
    # Example quick test (requires real keys)
    MASTER = os.getenv("PAYDUNYA_MASTER_KEY", "test_master_key")
    PRIVATE = os.getenv("PAYDUNYA_PRIVATE_KEY", "test_private_key")
    client = PayDunya(MASTER, PRIVATE, base_url="https://api.paydunya.com/v1")

    # 1) Create a payment request (DMP)
    try:
        resp = client.create_payment_request(
            amount=1000,
            identifier=f"order-{int(time.time())}",
            description="Test paiement",
            recipient_phone="+22890000000",
        )
        print("DMP response:", json.dumps(resp, indent=2))
    except Exception as e:
        print("DMP error:", e)

    # 2) Create a webpay invoice (example)
    try:
        inv = client.create_webpay_invoice(
            amount=2000,
            identifier=f"inv-{int(time.time())}",
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        print("WebPay invoice:", json.dumps(inv, indent=2))
    except Exception as e:
        print("WebPay error:", e)
