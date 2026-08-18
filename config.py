from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str) -> frozenset[str]:
    return frozenset(x.strip() for x in os.getenv(name, "").split(",") if x.strip())


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    telegram_api_id: int
    telegram_api_hash: str
    telegram_chat_id: int
    webhook_secret: str
    host: str
    port: int
    webhook_path: str
    log_level: str
    max_push_commits: int
    disable_workflow_notifications: bool
    disabled_workflow_names: frozenset[str]
    dedupe_ttl: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = _required("TELEGRAM_BOT_TOKEN")
        api_id = _int("API_ID", 0)
        if api_id <= 0:
            raise RuntimeError("API_ID must be a positive integer")
        api_hash = _required("API_HASH")
        chat_raw = _required("TELEGRAM_CHAT_ID")
        try:
            chat_id = int(chat_raw)
        except ValueError as exc:
            raise RuntimeError("TELEGRAM_CHAT_ID must be an integer") from exc
        return cls(
            telegram_bot_token=token,
            telegram_api_id=api_id,
            telegram_api_hash=api_hash,
            telegram_chat_id=chat_id,
            webhook_secret=_required("WEBHOOK_SECRET"),
            host=os.getenv("HOST", "0.0.0.0").strip() or "0.0.0.0",
            port=_int("PORT", 5000),
            webhook_path="/" + os.getenv("WEBHOOK_PATH", "/webhook").strip().lstrip("/"),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
            max_push_commits=max(1, _int("MAX_PUSH_COMMITS", 5)),
            disable_workflow_notifications=_bool("DISABLE_WORKFLOW_NOTIFICATIONS", False),
            disabled_workflow_names=_csv("DISABLE_WORKFLOW_NOTIFICATIONS_NAMES")
            or _csv("DISABLE_WORKFLOW_NOTIFICATIONS_NAME"),
            dedupe_ttl=max(60, _int("DELIVERY_DEDUPE_TTL", 86400)),
        )
