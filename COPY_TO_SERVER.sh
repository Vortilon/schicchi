#!/bin/bash
# Copy files from local machine to server
# Run this from your LOCAL machine (in the schicchi/schicchi directory)

SERVER="root@167.88.36.83"
REMOTE_PATH="/opt/schicchi"

echo "Creating remote directory..."
ssh $SERVER "mkdir -p $REMOTE_PATH"

echo "Copying files to server..."
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude 'schicchi.db' --exclude '*.log' \
  ./ $SERVER:$REMOTE_PATH/

echo ""
echo "Files copied! Now SSH to server and run setup:"
echo "ssh $SERVER"
echo "cd $REMOTE_PATH"
echo "chmod +x setup_server.sh"
echo "./setup_server.sh"
echo ""
echo "Then start services:"
echo "sudo systemctl start schicchi-app"
echo "sudo systemctl start schicchi-webhook"
echo ""
echo "Access app at: http://167.88.36.83:8501"

