from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    default_target_chat_id: str | None = Field(default=None, alias="DEFAULT_TARGET_CHAT_ID")
    sim1_target_chat_id: str | None = Field(default=None, alias="SIM1_TARGET_CHAT_ID")
    sim2_target_chat_id: str | None = Field(default=None, alias="SIM2_TARGET_CHAT_ID")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class SmsWebhookPayload(BaseModel):
    from_: str = Field(..., alias="from")
    text: str
    sent_stamp: str = Field(..., alias="sentStamp")
    received_stamp: str = Field(..., alias="receivedStamp")
    sim: str


@dataclass(frozen=True)
class SimRoute:
    normalized_key: str
    chat_id: str


def normalize_sim(sim: str) -> str:
    cleaned = "".join(ch for ch in sim.strip().lower() if ch.isalnum())
    if cleaned in {"1", "sim1", "slot1"}:
        return "sim1"
    if cleaned in {"2", "sim2", "slot2"}:
        return "sim2"
    return cleaned


def try_parse_timestamp(raw: str) -> str:
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw

    formatted = dt.strftime("%d %b %Y, %H:%M:%S")
    tz_offset = dt.strftime("%z")
    if tz_offset:
        tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}"
        return f"{formatted} {tz_offset}"
    return formatted


def build_message(payload: SmsWebhookPayload) -> str:
    sender = escape(payload.from_)
    sim = escape(payload.sim)
    received_stamp = escape(try_parse_timestamp(payload.received_stamp))
    text = escape(payload.text)

    return (
        "<b>📩 New SMS</b>\n"
        f"<b>👤 From:</b> <code>{sender}</code>\n"
        f"<b>📱 SIM:</b> <code>{sim}</code>\n"
        f"<b>🕒 Received:</b> <code>{received_stamp}</code>\n"
        "<b>💬 Text:</b>\n"
        f"<pre>{text}</pre>"
    )


def build_routes(settings: Settings) -> dict[str, SimRoute]:
    routes: dict[str, SimRoute] = {}
    if settings.sim1_target_chat_id:
        routes["sim1"] = SimRoute(normalized_key="sim1", chat_id=settings.sim1_target_chat_id)
    if settings.sim2_target_chat_id:
        routes["sim2"] = SimRoute(normalized_key="sim2", chat_id=settings.sim2_target_chat_id)
    return routes


def resolve_target_chat_id(payload: SmsWebhookPayload, settings: Settings, routes: dict[str, SimRoute]) -> str:
    normalized_sim = normalize_sim(payload.sim)
    if normalized_sim in routes:
        return routes[normalized_sim].chat_id
    if settings.default_target_chat_id:
        return settings.default_target_chat_id
    raise HTTPException(
        status_code=422,
        detail=(
            f"No chat mapping found for sim='{payload.sim}'. "
            "Set DEFAULT_TARGET_CHAT_ID or SIM1_TARGET_CHAT_ID/SIM2_TARGET_CHAT_ID."
        ),
    )


settings = Settings()
app = FastAPI(title="SMS Forwarder Telegram Webhook", version="0.1.0")
routes = build_routes(settings)
telegram_api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/sms")
async def sms_webhook(payload: SmsWebhookPayload) -> dict[str, Any]:
    target_chat_id = resolve_target_chat_id(payload, settings=settings, routes=routes)
    message = build_message(payload)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            telegram_api_url,
            json={
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Telegram API error: {response.text}")

    data = response.json()
    if not data.get("ok"):
        raise HTTPException(status_code=502, detail=f"Telegram API rejected message: {data}")

    return {"ok": True, "target_chat_id": target_chat_id}
