# SMS Forwarder -> Telegram (Webhook)

Simple Python service that receives webhook payloads from
[`android_income_sms_gateway_webhook`](https://github.com/bogkonstantin/android_income_sms_gateway_webhook)
and forwards messages to Telegram chats/channels.

## Payload format

The endpoint expects:

```json
{
  "from": "%from%",
  "text": "%text%",
  "sentStamp": "%sentStamp%",
  "receivedStamp": "%receivedStamp%",
  "sim": "%sim%"
}
```

## Setup with `uv`

1. Create env file:

   ```bash
   cp .env.example .env
   ```

2. Fill values in `.env`:

   - `TELEGRAM_BOT_TOKEN` — token from BotFather
   - `LOG_LEVEL` — `INFO` (default) or `DEBUG` for more verbose logs
   - `DEFAULT_TARGET_CHAT_ID` — optional fallback destination
   - `SIM1_TARGET_CHAT_ID` / `SIM2_TARGET_CHAT_ID` — optional per-SIM destinations

3. Install dependencies:

   ```bash
   uv sync
   ```

4. Run:

   ```bash
   uv run uvicorn app:app --host 0.0.0.0 --port 8000
   ```

## Docker

Build image:

```bash
docker build -t sms-forwarder-telegram-webhook .
```

Run container:

```bash
docker run --rm -p 8000:8000 --env-file .env sms-forwarder-telegram-webhook
```

## Routing modes

### 1 SIM / single destination

Set only:

```env
DEFAULT_TARGET_CHAT_ID=-1001234567890
```

All messages go to one chat/channel regardless of `sim`.

### 2 SIM / different destinations

Set:

```env
SIM1_TARGET_CHAT_ID=-1001234567890
SIM2_TARGET_CHAT_ID=-1009876543210
```

If incoming `sim` resolves to SIM1/SIM2, message goes to mapped destination.
If a SIM is unknown and `DEFAULT_TARGET_CHAT_ID` is set, it uses fallback.

## Endpoints

- `GET /health` — liveness check
- `POST /webhook/sms` — receives SMS payload and forwards to Telegram

## Example webhook request

```bash
curl -X POST http://localhost:8000/webhook/sms \
  -H "Content-Type: application/json" \
  -d '{
    "from":"+1234567890",
    "text":"Your code is 1234",
    "sentStamp":"2026-06-11T12:00:00Z",
    "receivedStamp":"2026-06-11T12:00:05Z",
    "sim":"SIM1"
  }'
```
