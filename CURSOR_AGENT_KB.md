# Cursor Agent Knowledge Base — Schicchi Forward Testing

This file is written so a Cursor coding agent (or any operator) can reliably generate **SSH instructions that work** for this project, without breaking other apps on the VPS.

---

## What this project is

- **Goal**: Forward-test TradingView strategies where **TradingView is only a signal generator**, and the app is the **system of record** for signals, orders, fills, positions, and performance.
- **Source of truth for executions/fills/positions**: **Alpaca** (paper now; live later via env switch).
- **Core flow**:
  - TradingView alert → `POST /api/webhook/tradingview` → store `signals` + create intended `orders`
  - App submits order to Alpaca with `client_order_id = trade_id`
  - App receives updates via Alpaca WebSocket (`trade_updates`) and/or pulls via sync endpoint
  - UI reads from app API; reporting is computed from **fills**

---

## Tech stack (must stay consistent)

- **Backend**: FastAPI (Python) + SQLModel + Postgres
- **Frontend**: Next.js (App Router) + Tailwind + shadcn/ui + `@tanstack/react-table`
- **Reverse proxy**: Caddy (routes `/api/auth/*` → `web`, `/api/*` → `api`)
- **Deployment**: Docker Compose

---

## Deployment layout on VPS (critical)

This app is designed to avoid interfering with other VPS services.

- **Project directory on VPS**: **`/opt/schicchi-ft`**
- There may be other unrelated directories in `/opt` (example: `/opt/schicchi`, `/opt/actracker`). Do **not** assume they contain this repo.

Common operator mistake (causes errors seen in logs):
- Running `git pull` or `docker compose ...` from **`/opt/schicchi`** → fails with:
  - `fatal: not a git repository`
  - `no configuration file provided`

Correct fix:
- `cd /opt/schicchi-ft` first, then run Docker Compose commands there.

---

## Compose files and ports (how not to conflict)

Base compose file:
- `docker-compose.yml` (defines `db`, `api`, `web`, `caddy`)

Overrides:
- **Safe ports mode (recommended on shared VPS)**:
  - `docker-compose.vps-ports.yml` publishes Caddy on **host port 8088** → container port 80
  - Access UI: `http://<domain-or-ip>:8088`
  - Avoids taking over 80/443 so it won’t interfere with existing Nginx/other sites
- Dev ports:
  - `docker-compose.dev-ports.yml` (local dev convenience)
- Prod ports:
  - `docker-compose.prod-ports.yml` (bind 80/443; only use if guaranteed free)

---

## Health endpoints and routing

- UI served by Next.js via Caddy.
- API served by FastAPI via Caddy.
- API health endpoint: `GET /api/health`
- Webhook endpoint: `POST /api/webhook/tradingview`
- Auth endpoints (handled by Next.js route handlers):
  - `POST /api/auth/login`
  - `POST /api/auth/logout`

Reverse proxy routing is in `Caddyfile`:
- `/api/auth/*` → `web:3000`
- `/api/*` → `api:8000`
- everything else → `web:3000`

---

## Environment variables (source of truth is `.env` on VPS)

The agent should never hardcode credentials; it should reference `.env` values.

Important keys:
- Postgres:
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - `DATABASE_URL` (should match above)
- TradingView:
  - `WEBHOOK_SECRET`
- Alpaca:
  - `ALPACA_KEY`, `ALPACA_SECRET`
  - `ALPACA_BASE_URL` (paper: `https://paper-api.alpaca.markets`)
  - `ALPACA_DATA_URL` (market data)
- UI login:
  - `UI_BASIC_AUTH_USER`, `UI_BASIC_AUTH_PASSWORD`
- Caddy:
  - `DOMAIN`

---

## “Start from scratch” database reset (safe procedure)

Preferred: drop only the `public` schema inside the project’s Postgres container, then restart API (it recreates tables on startup).

**Must be executed from `/opt/schicchi-ft`** and using the compose override you’re running (usually `docker-compose.vps-ports.yml`).

Robust reset command that uses `.env` variables (avoids mismatched DB names/users):

```bash
cd /opt/schicchi-ft
set -a; source ./.env; set +a

docker compose -f docker-compose.yml -f docker-compose.vps-ports.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $POSTGRES_USER; GRANT ALL ON SCHEMA public TO public;"

docker compose -f docker-compose.yml -f docker-compose.vps-ports.yml restart api
```

---

## Minimal SSH “no error” checklist (agent should emit this)

When giving SSH instructions, the agent should:

1) Verify the correct directory exists:
- `test -d /opt/schicchi-ft`

2) Verify compose files exist:
- `test -f /opt/schicchi-ft/docker-compose.yml`
- `test -f /opt/schicchi-ft/docker-compose.vps-ports.yml`

3) Only then run Docker Compose commands.

4) If directory is wrong/unknown, discover it:

```bash
sudo find /opt -maxdepth 3 -name docker-compose.yml -print
```

