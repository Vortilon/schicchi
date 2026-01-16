# Server Setup Instructions

## Step 4: Deploy Webhook Server on 167.88.36.83

### SSH into your server:
```bash
ssh root@167.88.36.83
```

### On the server, clone/navigate to the project:
```bash
cd /opt  # or your preferred location
git clone git@github.com:Vortilon/schicchi.git
cd schicchi
```

### Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Set environment variables:
```bash
export ALPACA_API_KEY="PK2GOVNPOKMT4BXY3OFFWOVHBS"
export ALPACA_SECRET_KEY="3QtrLXygY7ztrP5am1gr6FBUCDq1QAJizvqCP2BuEME2"
export WEBHOOK_PORT=5000
```

### Start webhook server (test first):
```bash
python webhook_server.py
```

### Set up as systemd service (for auto-start):
```bash
# Copy and edit the service file
sudo cp schicchi-webhook.service.template /etc/systemd/system/schicchi-webhook.service
sudo nano /etc/systemd/system/schicchi-webhook.service
# Update paths in the service file to match your installation

# Enable and start
sudo systemctl enable schicchi-webhook
sudo systemctl start schicchi-webhook
sudo systemctl status schicchi-webhook
```

### Configure nginx (if using):
Add to your nginx config to forward webhook requests:
```nginx
location /api/webhook {
    proxy_pass http://localhost:5000/api/webhook;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Step 5: Configure TradingView Alerts

1. Go to TradingView and create an alert
2. Set webhook URL: `https://schicchi.noteify.us/api/webhook` (or `http://167.88.36.83:5000/api/webhook` if not using domain)
3. In the alert message, use this JSON:

```json
{
    "symbol": "{{ticker}}",
    "action": "buy",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}",
    "stop_loss": 145.00,
    "take_profit": 160.00,
    "quantity": 10,
    "alert_id": "{{time}}_{{ticker}}"
}
```

See WEBHOOK_INFO.md for complete details.

## Testing the Webhook

Test from command line:
```bash
curl -X POST http://167.88.36.83:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NVDA",
    "action": "buy",
    "price": 150.50,
    "strategy": "rsi_pullback",
    "quantity": 10
  }'
```

You should see a response like:
```json
{
  "status": "success",
  "trade_id": 1,
  "alpaca_order_id": "abc123",
  "message": "Trade executed and recorded for NVDA"
}
```

