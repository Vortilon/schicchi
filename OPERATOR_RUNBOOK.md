# Operator Runbook (No Coding)

This guide assumes you can SSH to the VPS using:

```bash
ssh actracker-vps
```

It deploys the new forward-testing app into **`/opt/schicchi-ft`** so it does not touch other projects on the same VPS.

---

## Preconditions (confirm these first)

- You have **Docker + Docker Compose plugin** installed on the VPS:

```bash
docker --version
docker compose version
```

- You have decided whether this app should use ports **80/443** (may conflict with other sites).
  - If you are not sure, use the **safe ports mode** (runs on `:8088` / `:8444`).

---

## 1) SSH in and create the app directory

```bash
ssh actracker-vps
sudo mkdir -p /opt/schicchi-ft
sudo chown -R $USER:$USER /opt/schicchi-ft
cd /opt/schicchi-ft
```

---

## 1.5) Safety checks (read-only; won’t change anything)

Run these on the VPS **before** starting anything, to confirm what’s already running and which ports are in use:

```bash
# What is already in /opt?
ls -lah /opt

# Which services are listening on 80/443 (and other common ports)?
ss -tulpn | sed -n '1,5p'
ss -tulpn | egrep ':(80|443|3000|8000|8080|8088|8501|5000)\b' || true

# What reverse proxy is installed/running (nginx/caddy/apache)?
systemctl --no-pager --type=service --state=running | egrep -i 'nginx|caddy|apache|traefik' || true

# Any existing Docker containers (so we don’t collide)?
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
```

If you paste the output here, I’ll tell you definitively whether we should use **safe ports** or if 80/443 are truly free.

---

## 2) Copy the project to the VPS (choose one)

### Option A (recommended): rsync from your laptop

Run this on your laptop (not on the VPS):

```bash
cd /Users/carolynlepper/schicchi/schicchi
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude '*.db' --exclude '*.log' \
  ./ actracker-vps:/opt/schicchi-ft/
```

### Option B: git clone on the VPS

If you have this repo in GitHub and the VPS has access:

```bash
cd /opt/schicchi-ft
git clone <YOUR_REPO_SSH_URL> .
```

---

## 3) Create the environment file (this is where “login credentials” live)

On the VPS:

```bash
cd /opt/schicchi-ft
cp ENV.example .env
nano .env
```

Edit at minimum:

- `POSTGRES_PASSWORD` (pick a strong password)
- `DATABASE_URL` (make sure the password inside matches `POSTGRES_PASSWORD`)
- `WEBHOOK_SECRET` (this is the token TradingView must send)
- `UI_BASIC_AUTH_PASSWORD` (this is your web UI password)
- `ALPACA_KEY` / `ALPACA_SECRET` (paper trading keys)
- `DOMAIN`
  - If using safe ports mode: set `DOMAIN=YOUR_DOMAIN_OR_IP` (e.g. `schicchi.noteify.us` or `167.88.36.83`)

Save and exit.

---

## 4) Start the stack (choose one)

### Safe ports mode (recommended when VPS hosts other sites)

This avoids taking over ports 80/443:

```bash
cd /opt/schicchi-ft
docker compose -f docker-compose.yml -f docker-compose.vps-ports.yml up -d --build
```

### Standard mode (uses 80/443)

Only use this if nothing else on the VPS needs ports 80/443:

```bash
cd /opt/schicchi-ft
docker compose -f docker-compose.yml -f docker-compose.prod-ports.yml up -d --build
```

---

## Local dev ports (optional)

If running locally and you want direct port access:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev-ports.yml up -d --build
```

---

## 5) Verify containers are running

```bash
docker compose ps
docker compose logs -n 200 --no-log-prefix caddy
docker compose logs -n 200 --no-log-prefix api
docker compose logs -n 200 --no-log-prefix web
```

---

## 6) “Logging in” (what you type in the browser)

The web UI uses **Basic Auth** credentials:

- **Username**: `UI_BASIC_AUTH_USER` (from `.env`)
- **Password**: `UI_BASIC_AUTH_PASSWORD` (from `.env`)

### URLs to open

If you used **safe ports mode**:

- UI: `http://<YOUR_DOMAIN_OR_IP>:8088`
- API health: `http://<YOUR_DOMAIN_OR_IP>:8088/api/health`

If you used **standard 80/443 mode**:

- UI: `https://<YOUR_DOMAIN>/`
- API health: `https://<YOUR_DOMAIN>/api/health`

---

## 7) Webhook URL to paste into TradingView

Use:

`https://schicchi.noteify.us/api/webhook/tradingview`

If you used **safe ports mode** temporarily:

`http://<YOUR_DOMAIN_OR_IP>:8088/api/webhook/tradingview`

---

## 8) Stop / restart (safe commands)

From `/opt/schicchi-ft`:

```bash
docker compose down
docker compose up -d
docker compose restart
```

