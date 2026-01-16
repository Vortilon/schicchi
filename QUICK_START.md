# 🚀 Quick Start - Get Everything Running in 5 Minutes

## Current Status Summary

✅ **Code is ready** - All files are in `/Users/carolynlepper/schicchi/schicchi`  
✅ **Webhook server** - Receives TradingView alerts and executes Alpaca orders  
✅ **Database** - Stores all trades automatically  
✅ **Dashboard** - View trades at http://167.88.36.83:8501  

## What You Need to Do Now

### 1. Connect to Server (30 seconds)

```bash
ssh root@167.88.36.83
# Password: ElNeneNunito135#
```

### 2. Check if Project Exists (10 seconds)

```bash
cd /opt/schicchi
ls -la
```

**If empty or doesn't exist:** Go to step 3  
**If files exist:** Skip to step 4

### 3. Copy Files to Server (2 minutes)

**Open a NEW terminal window on your Mac (don't close SSH):**

```bash
cd /Users/carolynlepper/schicchi/schicchi
./COPY_TO_SERVER.sh
```

### 4. Setup on Server (2 minutes)

**Back in your SSH session:**

```bash
cd /opt/schicchi
chmod +x setup_server.sh
./setup_server.sh
```

### 5. Start Services (30 seconds)

```bash
sudo systemctl start schicchi-webhook
sudo systemctl start schicchi-app
```

### 6. Test It Works (30 seconds)

```bash
# Test webhook
curl http://localhost:5000/health

# Should return: {"status":"ok","service":"schicchi-webhook"}
```

### 7. Access Dashboard

Open browser: **http://167.88.36.83:8501**  
Login: `otto` / `otto`

## TradingView Setup (5 minutes)

1. **Open TradingView** → Pine Editor
2. **Copy code from** `PINESCRIPT_EXAMPLE.pine`
3. **Paste and save** as "Schicchi RSI Pullback"
4. **Add to chart**
5. **Right-click chart** → Add Alert
6. **Webhook URL:** `http://167.88.36.83:5000/api/webhook`
7. **Message (for entry):**
```json
{"symbol":"{{ticker}}","action":"buy","price":{{close}},"strategy":"rsi_pullback","timestamp":"{{time}}","stop_loss":{{close}}*0.95,"take_profit":{{close}}*1.10,"quantity":10,"alert_id":"{{time}}_{{ticker}}"}
```

8. **Message (for exit):**
```json
{"symbol":"{{ticker}}","action":"close","price":{{close}},"strategy":"rsi_pullback","timestamp":"{{time}}","alert_id":"{{time}}_{{ticker}}_exit"}
```

## That's It! 🎉

Your automation is now running:
- ✅ TradingView → Webhook → Server
- ✅ Server → Database → Alpaca
- ✅ Alpaca → Database → Dashboard

## Quick Commands Reference

```bash
# Check services
sudo systemctl status schicchi-webhook
sudo systemctl status schicchi-app

# View logs
sudo journalctl -u schicchi-webhook -f
sudo journalctl -u schicchi-app -f

# Restart if needed
sudo systemctl restart schicchi-webhook
sudo systemctl restart schicchi-app
```

## Need Help?

See `COMPLETE_GUIDE.md` for detailed instructions.
