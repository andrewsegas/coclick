"""Discord webhook notifications for CoClick.

Stdlib-only (urllib): no extra dependency. The bot uses :func:`send`
(fire-and-forget, never raises, never blocks the farm loop); the GUI's
"Test" button uses :func:`send_test` to get an error message back.
"""

import json
import ssl
import threading
import urllib.request

_TIMEOUT = 10  # seconds


def _ssl_context():
    """Default verification minus Python 3.13's VERIFY_X509_STRICT.

    Antivirus/proxy HTTPS inspection uses root certs that the strict mode
    rejects (basicConstraints not marked critical) even though Windows trusts
    them; the chain is still fully verified against the system's trusted roots.
    """
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


def _post(webhook_url, message):
    """Synchronous POST to the webhook. Raises on failure."""
    data = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "CoClick"},
    )
    urllib.request.urlopen(req, timeout=_TIMEOUT, context=_ssl_context()).close()


def send(webhook_url, message):
    """Send in a background thread; swallow every error (a dead webhook or
    offline network must never interrupt the bot)."""
    webhook_url = (webhook_url or "").strip()
    if not webhook_url.startswith("http"):
        return

    def _worker():
        try:
            _post(webhook_url, message)
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def send_test(webhook_url):
    """Send a test message synchronously. Returns None on success or the
    error as a string (for the GUI to show)."""
    webhook_url = (webhook_url or "").strip()
    if not webhook_url.startswith("http"):
        return "Invalid webhook URL (must start with https://)."
    try:
        _post(webhook_url, "✅ CoClick conectado! As notificações do bot vão chegar aqui.")
        return None
    except Exception as exc:
        return str(exc)
