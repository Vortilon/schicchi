# Quick Deployment Guide - Everything on Server

## Step 1: Copy Files to Server

**From your LOCAL machine:**
```bash
cd /Users/carolynlepper/schicchi/schicchi
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude 'schicchi.db' --exclude '*.log' \
  ./ root@167.88.36.83:/opt/schicchi/
```

## Step 2: Run Setup on Server

**SSH to server:**
```bash
ssh root@167.88.36.83
```

**Run setup script:**
```bash
cd /opt/schicchi
chmod +x setup_server.sh
./setup_server.sh
```

## Step 3: Start Services

```bash
sudo systemctl start schicchi-app
sudo systemctl start schicchi-webhook
```

## Step 4: Access from Anywhere

- **App:** http://167.88.36.83:8501
- **Webhook:** http://167.88.36.83:5000/api/webhook

## Optional: Configure Domain (schicchi.noteify.us)

If you want to use the domain name, set up nginx (see SERVER_DEPLOYMENT.md)

## That's It!

Your app is now running on the server and accessible from anywhere in the world.

**Login credentials:**
- Username: `otto`
- Password: `otto`

