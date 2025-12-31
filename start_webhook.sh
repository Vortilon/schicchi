#!/bin/bash
# Startup script for webhook server
# Usage: ./start_webhook.sh

cd "$(dirname "$0")"
python3 webhook_server.py

