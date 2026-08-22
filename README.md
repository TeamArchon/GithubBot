# GitHub to Telegram — Python + Pyrogram

A production-oriented Python rewrite of the `agam778/github-to-telegram` project.

## Supported GitHub webhook events

- ⭐ Stars
- 📦 Push / commits
- 🍴 Forks
- 🐛 Issues (opened, closed, reopened, edited, labels, lock/unlock, etc.)
- 🔀 Pull requests (opened, closed, reopened, synchronize, labels, lock/unlock, etc.)
- 🚀 Releases
- ⚙️ GitHub Actions `workflow_run`
- 🔐 `X-Hub-Signature-256` verification
- 🔄 GitHub delivery de-duplication
- 🔘 Inline buttons for repository/commit/issue/PR/release/workflow

## Configuration

Copy `.env.example` to `.env` and replace every placeholder with your real values. Never commit `.env` to GitHub.

## Install

```bash
sudo apt update
sudo apt install -y python3 python3-venv
cd /root
git clone YOUR_REPOSITORY_URL github-to-telegram
cd github-to-telegram
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
nano .env
```

### Telegram variables

Create a bot with `@BotFather`. Put its token in `TELEGRAM_BOT_TOKEN`.
Pyrogram also needs your Telegram `API_ID` and `API_HASH` from `my.telegram.org`.
Add the bot to the target group/channel and give it permission to post.

`TELEGRAM_CHAT_ID` can be a group/channel ID such as `-1001234567890`. The bot must be a member/admin with permission to send messages.

## Test locally on VPS

```bash
source venv/bin/activate
python run.py
```

Health check:

```bash
curl http://127.0.0.1:5000/health
```

Expected:

```json
{"status":"ok","service":"github-to-telegram","version":"2026.1.1"}
```

## GitHub Webhook

Repository → Settings → Webhooks → Add webhook

- Payload URL: `https://YOUR-DOMAIN/webhook`
- Content type: `application/json`
- Secret: the exact `WEBHOOK_SECRET`
- Select individual events and enable Star, Push, Fork, Issues, Pull requests, Releases and Workflow runs.

GitHub sends `X-Hub-Signature-256`; the application verifies it before processing the payload.

## Run 24/7 with systemd

After creating `.env` and installing dependencies:

```bash
cp systemd/github-to-telegram.service /etc/systemd/system/github-to-telegram.service
systemctl daemon-reload
systemctl enable --now github-to-telegram
systemctl status github-to-telegram --no-pager
journalctl -u github-to-telegram -f
```

## HTTPS

GitHub requires a reachable webhook endpoint. Put Nginx/Caddy/Cloudflare Tunnel in front of the FastAPI server and expose HTTPS.

## Notes

Pyrogram is used exclusively for Telegram communication. FastAPI/uvicorn receives GitHub webhooks. The bot does not require a Telegram user session.
