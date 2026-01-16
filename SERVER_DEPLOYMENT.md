# Full Server Deployment - Accessible from Anywhere

This guide sets up everything on the server so it can be accessed from anywhere in the world.

## Server Setup

### 1. Create Directory and Copy Files

**On the SERVER:**
```bash
mkdir -p /opt/schicchi
cd /opt/schicchi
```

**From your LOCAL machine, copy all files:**
```bash
cd /Users/carolynlepper/schicchi/schicchi
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude 'schicchi.db' --exclude '*.log' \
  ./ root@167.88.36.83:/opt/schicchi/
```

### 2. Install Dependencies on Server

**On the SERVER:**
```bash
cd /opt/schicchi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Set Environment Variables

**On the SERVER, create a startup script:**
```bash
cd /opt/schicchi
cat > .env << EOF
ALPACA_API_KEY=PK2GOVNPOKMT4BXY3OFFWOVHBS
ALPACA_SECRET_KEY=3QtrLXygY7ztrP5am1gr6FBUCDq1QAJizvqCP2BuEME2
WEBHOOK_PORT=5000
STREAMLIT_PORT=8501
EOF
```

### 4. Create Systemd Services

**Streamlit App Service:**
```bash
cat > /etc/systemd/system/schicchi-app.service << 'EOF'
[Unit]
Description=Schicchi Streamlit Trading App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/schicchi
Environment="PATH=/opt/schicchi/venv/bin"
EnvironmentFile=/opt/schicchi/.env
ExecStart=/opt/schicchi/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Webhook Server Service:**
```bash
cat > /etc/systemd/system/schicchi-webhook.service << 'EOF'
[Unit]
Description=Schicchi TradingView Webhook Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/schicchi
Environment="PATH=/opt/schicchi/venv/bin"
EnvironmentFile=/opt/schicchi/.env
ExecStart=/opt/schicchi/venv/bin/python webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 5. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable schicchi-app
sudo systemctl enable schicchi-webhook
sudo systemctl start schicchi-app
sudo systemctl start schicchi-webhook
sudo systemctl status schicchi-app
sudo systemctl status schicchi-webhook
```

### 6. Configure Nginx (for public access)

**Install nginx if not already installed:**
```bash
sudo apt update
sudo apt install nginx -y
```

**Create nginx configuration:**
```bash
cat > /etc/nginx/sites-available/schicchi << 'EOF'
# Streamlit App
server {
    listen 80;
    server_name schicchi.noteify.us;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}

# Webhook API
server {
    listen 80;
    server_name schicchi.noteify.us;

    location /api/webhook {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/schicchi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Configure Firewall

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow direct access to ports (if not using nginx)
sudo ufw allow 8501/tcp
sudo ufw allow 5000/tcp
```

## Access Your App

Once set up, access from anywhere:

- **Streamlit App:** http://schicchi.noteify.us (or http://167.88.36.83:8501)
- **Webhook Endpoint:** https://schicchi.noteify.us/api/webhook (or http://167.88.36.83:5000/api/webhook)

## Management Commands

**Check status:**
```bash
sudo systemctl status schicchi-app
sudo systemctl status schicchi-webhook
```

**View logs:**
```bash
sudo journalctl -u schicchi-app -f
sudo journalctl -u schicchi-webhook -f
```

**Restart services:**
```bash
sudo systemctl restart schicchi-app
sudo systemctl restart schicchi-webhook
```

**Stop services:**
```bash
sudo systemctl stop schicchi-app
sudo systemctl stop schicchi-webhook
```

## Security Notes

1. **Change default password** in the app (currently "otto"/"otto")
2. **Set up SSL/HTTPS** using Let's Encrypt for secure access
3. **Restrict access** if needed using nginx authentication or firewall rules

