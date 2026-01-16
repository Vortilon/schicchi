# Complete Setup Guide - From Zero to Full Automation

## 📍 Where We Are Now

### What We've Built:
1. ✅ **Streamlit Trading App** (`app.py`) - Dashboard for viewing trades, backtesting, optimization
2. ✅ **Webhook Server** (`webhook_server.py`) - Receives TradingView alerts and executes Alpaca orders
3. ✅ **Database** (SQLite) - Stores all trades, strategies, backtest results
4. ✅ **Alpaca Integration** - Connects to Alpaca Paper Trading API
5. ✅ **Strategy Implementations** - RSI Pullback and Bollinger Band Squeeze Breakout

### Current Status:
- Code is ready locally at: `/Users/carolynlepper/schicchi/schicchi`
- Server path: `/opt/schicchi` (on 167.88.36.83)
- GitHub repo: `git@github.com:Vortilon/schicchi.git`
- Webhook URL: `http://167.88.36.83:5000/api/webhook` (or `https://schicchi.noteify.us/api/webhook`)

## 🎯 What We Need to Complete

### Full Automation Flow:
```
TradingView (PineScript) 
  → Webhook POST 
  → Server receives 
  → Database record created 
  → Alpaca order executed 
  → Alpaca response received 
  → Database updated with order status
  → Dashboard shows live trades
```

## 📋 Step-by-Step Instructions

### STEP 1: Connect to Server and Check Status

**SSH to server:**
```bash
ssh root@167.88.36.83
# Password: ElNeneNunito135#
```

**Check if project exists:**
```bash
cd /opt/schicchi
ls -la
```

**If directory doesn't exist or is empty, go to STEP 2. If files exist, skip to STEP 3.**

### STEP 2: Copy Files to Server (If Needed)

**From your LOCAL Mac terminal (new window, NOT SSH):**
```bash
cd /Users/carolynlepper/schicchi/schicchi
./COPY_TO_SERVER.sh
```

**Or manually:**
```bash
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude 'schicchi.db' --exclude '*.log' \
  ./ root@167.88.36.83:/opt/schicchi/
```

### STEP 3: Setup on Server

**Back on the SERVER (SSH session):**
```bash
cd /opt/schicchi
chmod +x setup_server.sh
./setup_server.sh
```

This installs dependencies and creates systemd services.

### STEP 4: Start Services

**On SERVER:**
```bash
# Start webhook server (receives TradingView alerts)
sudo systemctl start schicchi-webhook

# Start Streamlit app (dashboard)
sudo systemctl start schicchi-app

# Check status
sudo systemctl status schicchi-webhook
sudo systemctl status schicchi-app
```

**Check if running:**
```bash
# Webhook should be on port 5000
curl http://localhost:5000/health

# Streamlit should be on port 8501
curl http://localhost:8501
```

### STEP 5: Configure Firewall (If Needed)

**On SERVER:**
```bash
# Allow webhook port
sudo ufw allow 5000/tcp

# Allow Streamlit port
sudo ufw allow 8501/tcp

# Check firewall status
sudo ufw status
```

### STEP 6: Test Webhook Endpoint

**From your LOCAL machine or browser:**
```bash
curl -X POST http://167.88.36.83:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NVDA",
    "action": "buy",
    "price": 150.50,
    "strategy": "rsi_pullback",
    "quantity": 10,
    "stop_loss": 145.00,
    "take_profit": 160.00
  }'
```

**Expected response:**
```json
{
  "status": "success",
  "trade_id": 1,
  "alpaca_order_id": "abc123...",
  "message": "Trade executed and recorded for NVDA"
}
```

## 📊 TradingView PineScript Strategy Setup

### Create a PineScript Strategy

**In TradingView, create a new strategy:**

1. **Open TradingView** → Pine Editor
2. **Paste this example strategy:**

```pinescript
//@version=5
strategy("RSI Pullback Strategy", overlay=true, initial_capital=100000, default_qty_type=strategy.percent_of_equity, default_qty_value=10)

// Strategy Parameters
rsi_period = input.int(10, title="RSI Period", minval=1)
oversold = input.int(40, title="Oversold Level", minval=1, maxval=100)
overbought = input.int(75, title="Overbought Level", minval=1, maxval=100)
volume_filter = input.float(1.5, title="Volume Filter", minval=1.0)

// Calculate RSI
rsi = ta.rsi(close, rsi_period)

// Calculate ATR for stops
atr_period = 14
atr = ta.atr(atr_period)

// Volume filter
avg_volume = ta.sma(volume, 20)
volume_condition = volume > avg_volume * volume_filter

// Entry condition
long_condition = rsi < oversold and volume_condition and close > close[1]

// Exit condition
exit_condition = rsi > overbought

// Strategy logic
if (long_condition)
    strategy.entry("Long", strategy.long)
    stop_loss_price = close - (atr * 2.0)
    take_profit_price = close + (atr * 3.0)
    strategy.exit("Exit", "Long", stop=stop_loss_price, limit=take_profit_price)

if (exit_condition)
    strategy.close("Long")

// Alert conditions
alertcondition(long_condition, title="Long Entry", message="BUY")
alertcondition(exit_condition, title="Long Exit", message="CLOSE")
```

3. **Save and add to chart**

### Configure TradingView Alert

1. **Right-click on chart** → Add Alert
2. **Condition:** Select your strategy (e.g., "RSI Pullback Strategy")
3. **Alert Settings:**
   - **Webhook URL:** `http://167.88.36.83:5000/api/webhook`
   - **Message:** Use the JSON format below

### Webhook Message Format

**For ENTRY (Buy):**
```json
{
    "symbol": "{{ticker}}",
    "action": "buy",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}",
    "stop_loss": {{close}} - ({{ta.atr(14)}} * 2.0),
    "take_profit": {{close}} + ({{ta.atr(14)}} * 3.0),
    "quantity": 10,
    "alert_id": "{{time}}_{{ticker}}_entry"
}
```

**For EXIT (Close):**
```json
{
    "symbol": "{{ticker}}",
    "action": "close",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}",
    "alert_id": "{{time}}_{{ticker}}_exit"
}
```

**Note:** TradingView may not support all PineScript functions in JSON. Use this simpler version:

**Simplified ENTRY:**
```json
{
    "symbol": "{{ticker}}",
    "action": "buy",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}",
    "stop_loss": {{close}} * 0.95,
    "take_profit": {{close}} * 1.10,
    "quantity": 10,
    "alert_id": "{{time}}_{{ticker}}"
}
```

**Simplified EXIT:**
```json
{
    "symbol": "{{ticker}}",
    "action": "close",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}",
    "alert_id": "{{time}}_{{ticker}}_exit"
}
```

## 🔄 Complete Automation Flow Explained

### 1. TradingView Detects Signal
- PineScript strategy triggers alert condition
- TradingView sends POST request to webhook URL

### 2. Webhook Server Receives (`webhook_server.py`)
- Validates JSON data
- Parses symbol, action, price, strategy
- Creates database record (status: "open")
- Executes Alpaca order

### 3. Alpaca Order Execution
- Places market order via Alpaca API
- Receives order confirmation or error
- Returns order ID or error message

### 4. Database Update
- Trade record updated with:
  - Alpaca order ID
  - Order status
  - Entry price confirmation
  - Timestamp

### 5. Dashboard Display (`app.py`)
- Shows open positions
- Real-time P&L updates
- Strategy performance metrics
- Trade history

## 🗄️ Database Schema

**Trades Table:**
- `id` - Unique trade ID
- `symbol` - Stock ticker (NVDA, AAPL, etc.)
- `strategy_name` - Strategy identifier
- `side` - "long" or "short"
- `entry_price` - Entry price
- `exit_price` - Exit price (null if open)
- `quantity` - Number of shares
- `status` - "open", "closed", "stopped"
- `pnl` - Profit/Loss
- `alpaca_order_id` - Alpaca order confirmation
- `entry_time` - When trade opened
- `exit_time` - When trade closed

## 🔍 Verify Everything Works

### Check Webhook Server Logs:
```bash
sudo journalctl -u schicchi-webhook -f
```

### Check Streamlit App Logs:
```bash
sudo journalctl -u schicchi-app -f
```

### Test from Command Line:
```bash
# Test webhook
curl -X POST http://167.88.36.83:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"NVDA","action":"buy","price":150.50,"strategy":"rsi_pullback","quantity":10}'

# Check database
cd /opt/schicchi
source venv/bin/activate
python3 -c "from database import get_session, Trade; s = get_session(); trades = s.query(Trade).all(); print(f'Total trades: {len(trades)}'); [print(f\"{t.id}: {t.symbol} {t.status} {t.pnl}\") for t in trades[-5:]]"
```

### Access Dashboard:
- Open browser: `http://167.88.36.83:8501`
- Login: `otto` / `otto`
- Check Dashboard for trades

## 📝 Quick Reference

**Server Info:**
- IP: `167.88.36.83`
- User: `root`
- Password: `ElNeneNunito135#`
- Project Path: `/opt/schicchi`

**URLs:**
- Webhook: `http://167.88.36.83:5000/api/webhook`
- Dashboard: `http://167.88.36.83:8501`
- Domain (if configured): `https://schicchi.noteify.us`

**GitHub:**
- Repo: `git@github.com:Vortilon/schicchi.git`

**Services:**
- Webhook: `schicchi-webhook`
- App: `schicchi-app`

**Commands:**
```bash
# Start services
sudo systemctl start schicchi-webhook
sudo systemctl start schicchi-app

# Stop services
sudo systemctl stop schicchi-webhook
sudo systemctl stop schicchi-app

# Restart services
sudo systemctl restart schicchi-webhook
sudo systemctl restart schicchi-app

# View logs
sudo journalctl -u schicchi-webhook -f
sudo journalctl -u schicchi-app -f

# Check status
sudo systemctl status schicchi-webhook
sudo systemctl status schicchi-app
```

## ✅ Next Steps Checklist

- [ ] SSH to server and verify `/opt/schicchi` exists
- [ ] Copy files if needed
- [ ] Run `setup_server.sh`
- [ ] Start both services
- [ ] Test webhook endpoint
- [ ] Create PineScript strategy in TradingView
- [ ] Configure TradingView alert with webhook URL
- [ ] Test alert from TradingView
- [ ] Verify trade appears in database
- [ ] Check Alpaca order execution
- [ ] View trade in dashboard
