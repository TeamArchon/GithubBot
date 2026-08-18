from __future__ import annotations

import asyncio
import logging

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger(__name__)


class TelegramSender:
    def __init__(self, settings):
        self.chat_id = settings.telegram_chat_id
        self.client = Client(
            "github_to_telegram_bot",
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            bot_token=settings.telegram_bot_token,
            in_memory=True,
        )

    async def start(self) -> None:
        await self.client.start()
        me = await self.client.get_me()
        log.info("Telegram bot started as @%s", me.username or me.id)

    async def stop(self) -> None:
        try:
            await self.client.stop()
        except Exception:
            log.exception("Error while stopping Telegram client")

    async def send(self, text: str, button_text: str | None = None, button_url: str | None = None) -> None:
        markup = None
        if button_text and button_url:
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(button_text, url=button_url)]]
            )

        for attempt in range(4):
            try:
                await self.client.send_message(
                    self.chat_id,
                    text,
                    parse_mode="html",
                    disable_web_page_preview=True,
                    reply_markup=markup,
                )
                return
            except FloodWait as exc:
                delay = int(exc.value) + 1
                log.warning("Telegram FloodWait: sleeping %ss", delay)
                await asyncio.sleep(delay)
            except RPCError:
                if attempt >= 3:
                    raise
                delay = 2 ** attempt
                log.warning("Telegram RPC error; retrying in %ss", delay, exc_info=True)
                await asyncio.sleep(delay)
