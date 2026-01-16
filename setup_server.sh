#!/bin/bash
# Complete server setup script
# Run this on the server after copying files

set -e

echo "Setting up Schicchi on server..."

cd /opt/schicchi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "Creating environment file..."
cat > .env << EOF
ALPACA_API_KEY=PK2GOVNPOKMT4BXY3OFFWOVHBS
ALPACA_SECRET_KEY=3QtrLXygY7ztrP5am1gr6FBUCDq1QAJizvqCP2BuEME2
WEBHOOK_PORT=5000
STREAMLIT_PORT=8501
EOF

# Create systemd services
echo "Creating systemd services..."

# Streamlit app service
cat > /tmp/schicchi-app.service << 'EOF'
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

# Webhook service
cat > /tmp/schicchi-webhook.service << 'EOF'
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

# Copy services to systemd
sudo cp /tmp/schicchi-app.service /etc/systemd/system/
sudo cp /tmp/schicchi-webhook.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable schicchi-app
sudo systemctl enable schicchi-webhook

echo "Setup complete!"
echo ""
echo "To start services:"
echo "  sudo systemctl start schicchi-app"
echo "  sudo systemctl start schicchi-webhook"
echo ""
echo "To check status:"
echo "  sudo systemctl status schicchi-app"
echo "  sudo systemctl status schicchi-webhook"

