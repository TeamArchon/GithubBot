from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from collections import OrderedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from config import Settings
from .formatters import result
from .telegram import TelegramSender

settings = Settings.from_env()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("github-to-telegram")
sender = TelegramSender(settings)

# Delivery IDs are kept only in memory to prevent GitHub retry duplicates.
_seen: OrderedDict[str, float] = OrderedDict()


def _seen_delivery(delivery: str | None) -> bool:
    if not delivery:
        return False
    now = time.monotonic()
    cutoff = now - settings.dedupe_ttl
    while _seen and next(iter(_seen.values())) < cutoff:
        _seen.popitem(last=False)
    if delivery in _seen:
        return True
    _seen[delivery] = now
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    await sender.start()
    try:
        yield
    finally:
        await sender.stop()


app = FastAPI(title="GitHub to Telegram", version="2026.1.1", lifespan=lifespan)


def verify_signature(body: bytes, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        settings.webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


@app.get("/", response_class=PlainTextResponse)
async def root():
    return "GitHub to Telegram webhook is running. POST to /webhook."


@app.get("/health")
async def health():
    return {"status": "ok", "service": "github-to-telegram", "version": app.version}


@app.post(settings.webhook_path)
async def webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be an object")

    event = request.headers.get("x-github-event", "unknown").lower()
    delivery = request.headers.get("x-github-delivery")

    if _seen_delivery(delivery):
        return {"ok": True, "event": event, "duplicate": True}

    if event in {"ping", "installation", "installation_repositories", "meta"}:
        return {"ok": True, "event": event, "notified": False}

    if event == "workflow_run":
        run = payload.get("workflow_run") or {}
        workflow = payload.get("workflow") or {}
        workflow_name = run.get("name") or workflow.get("name")
        if settings.disable_workflow_notifications:
            return {"ok": True, "event": event, "ignored": "workflow_disabled"}
        if workflow_name and workflow_name in settings.disabled_workflow_names:
            return {"ok": True, "event": event, "ignored": "workflow_name_disabled"}

    formatted = result(payload, settings.max_push_commits)
    if not formatted:
        return {"ok": True, "event": event, "notified": False}

    text, button, url = formatted
    try:
        await sender.send(text, button, url)
    except Exception as exc:
        # Remove the delivery ID so GitHub's retry can be processed again.
        if delivery:
            _seen.pop(delivery, None)
        log.exception("Telegram delivery failed for %s", event)
        raise HTTPException(status_code=502, detail="Telegram delivery failed") from exc

    return {"ok": True, "event": event, "delivery": delivery, "notified": True}
