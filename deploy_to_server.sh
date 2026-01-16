#!/bin/bash
# Deploy script - runs commands on server
ssh root@167.88.36.83 << 'ENDSSH'
cd /opt/schicchi
git pull
source venv/bin/activate
pip install -r requirements.txt
echo "Deployment complete!"
ENDSSH
