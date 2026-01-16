# Complete TradingView Setup Guide

## Step-by-Step Instructions

### 1. Open TradingView Pine Editor

1. Go to [TradingView.com](https://www.tradingview.com)
2. Click on **"Chart"** at the top
3. Click on **"Pine Editor"** tab at the bottom
4. If you don't see it, click the **"Pine Editor"** button in the toolbar

### 2. Create New Strategy

1. Click **"New"** → **"Blank Strategy"** (or click the "+" icon)
2. Delete all default code
3. Copy the entire code from `MA_CROSSOVER_STRATEGY.pine`
4. Paste into the editor
5. Click **"Save"** (or press Ctrl+S / Cmd+S)
6. Name it: **"Schicchi MA Crossover"**

### 3. Configure Strategy Parameters

In the Pine Editor, you'll see input fields at the top:

- **Fast MA Period**: `9` (default)
- **Slow MA Period**: `21` (default)
- **RSI Period**: `14` (default)
- **RSI Oversold**: `30` (default)
- **RSI Overbought**: `70` (default)
- **Use RSI Filter**: `true` (checked)
- **Strategy Name**: `ma_crossover` (for webhook - keep this!)
- **Fixed Quantity**: `10` (number of shares per trade)

**Adjust these as needed**, but keep **Strategy Name** as `ma_crossover` for the webhook.

### 4. Add Strategy to Chart

1. Click **"Add to Chart"** button (or press Ctrl+Enter / Cmd+Enter)
2. The strategy will appear on your chart
3. You should see:
   - Blue line (Fast MA)
   - Red line (Slow MA)
   - Green triangles (Long Entry signals)
   - Red triangles (Long Exit signals)
   - Orange triangles (Short Entry signals)
   - Blue triangles (Short Exit signals)

### 5. Test the Strategy

1. Add a stock symbol (e.g., NVDA, AAPL, TSLA)
2. Switch to a time frame (1H, 4H, or Daily recommended)
3. You should see signals appear on the chart
4. Check the strategy performance in the "Strategy Tester" panel (bottom)

### 6. Create Alerts

#### For Long Entry (Buy Signal)

1. **Right-click on the chart** → **"Add Alert"**
2. **Condition**: Select **"Schicchi MA Crossover"** → **"Long Entry"**
3. **Webhook URL**: `http://167.88.36.83:5000/api/webhook`
   - Or if using domain: `https://schicchi.noteify.us/api/webhook`
4. **Message**: Copy this JSON (exactly as shown):
```json
{"strategy":"ma_crossover","symbol":"{{ticker}}","price":{{close}},"instruction":"buy","qty":10,"timestamp":"{{time}}","alert_id":"{{time}}_{{ticker}}_long_entry"}
```
5. **Expiration**: Set to "Never" or your preferred duration
6. **Frequency**: Select **"Once Per Bar Close"** (recommended)
7. Click **"Create"**

#### For Long Exit (Sell Signal)

1. **Right-click on chart** → **"Add Alert"**
2. **Condition**: Select **"Schicchi MA Crossover"** → **"Long Exit"**
3. **Webhook URL**: Same as above: `http://167.88.36.83:5000/api/webhook`
4. **Message**:
```json
{"strategy":"ma_crossover","symbol":"{{ticker}}","price":{{close}},"instruction":"sell","qty":10,"timestamp":"{{time}}","alert_id":"{{time}}_{{ticker}}_long_exit"}
```
5. Click **"Create"**

#### For Short Entry (Short Signal)

1. **Right-click on chart** → **"Add Alert"**
2. **Condition**: Select **"Schicchi MA Crossover"** → **"Short Entry"**
3. **Webhook URL**: Same as above
4. **Message**:
```json
{"strategy":"ma_crossover","symbol":"{{ticker}}","price":{{close}},"instruction":"short","qty":10,"timestamp":"{{time}}","alert_id":"{{time}}_{{ticker}}_short_entry"}
```
5. Click **"Create"**

#### For Short Exit (Cover Signal)

1. **Right-click on chart** → **"Add Alert"**
2. **Condition**: Select **"Schicchi MA Crossover"** → **"Short Exit"**
3. **Webhook URL**: Same as above
4. **Message**:
```json
{"strategy":"ma_crossover","symbol":"{{ticker}}","price":{{close}},"instruction":"cover","qty":10,"timestamp":"{{time}}","alert_id":"{{time}}_{{ticker}}_short_exit"}
```
5. Click **"Create"**

### 7. Apply to Multiple Stocks

You can create alerts for multiple stocks:

1. **Change the chart symbol** (e.g., from NVDA to AAPL)
2. **Create the same 4 alerts** (Long Entry, Long Exit, Short Entry, Short Exit)
3. **Repeat for each stock** you want to trade

**Pro Tip**: You can also use TradingView's **"Alert Template"** feature to quickly create alerts for multiple symbols.

### 8. Verify Alerts Are Working

1. **Wait for a signal** to appear on the chart
2. **Check your server logs**:
   ```bash
   ssh root@167.88.36.83
   sudo journalctl -u schicchi-webhook -f
   ```
3. **Check your dashboard**: http://167.88.36.83:8501
4. **Login** with `otto` / `otto`
5. **View trades** in the Dashboard

## JSON Field Reference

Each alert sends this JSON structure:

```json
{
    "strategy": "ma_crossover",        // Fixed - matches strategy name
    "symbol": "{{ticker}}",            // Auto-filled by TradingView
    "price": {{close}},                // Auto-filled - current price
    "instruction": "buy",              // buy/sell/short/cover
    "qty": 10,                         // Fixed quantity
    "timestamp": "{{time}}",           // Auto-filled - timestamp
    "alert_id": "{{time}}_{{ticker}}_long_entry"  // Unique ID
}
```

### Instruction Values:
- `"buy"` - Open long position
- `"sell"` - Close long position
- `"short"` - Open short position
- `"cover"` - Close short position

## Troubleshooting

### Alerts Not Triggering?
1. Check that strategy is added to chart
2. Verify alert conditions are set correctly
3. Make sure "Frequency" is set to "Once Per Bar Close"
4. Check TradingView alert logs (click bell icon → "Alerts")

### Webhook Not Receiving?
1. Test webhook manually:
   ```bash
   curl -X POST http://167.88.36.83:5000/api/webhook \
     -H "Content-Type: application/json" \
     -d '{"strategy":"ma_crossover","symbol":"NVDA","price":150.50,"instruction":"buy","qty":10}'
   ```
2. Check server logs: `sudo journalctl -u schicchi-webhook -f`
3. Verify firewall allows port 5000: `sudo ufw allow 5000/tcp`

### JSON Format Errors?
- Make sure JSON is valid (no extra commas, proper quotes)
- TradingView variables like `{{ticker}}` must be lowercase
- Don't add extra spaces or line breaks in the JSON

## Quick Reference

**Webhook URL**: `http://167.88.36.83:5000/api/webhook`

**Strategy Name**: `ma_crossover` (keep this fixed in PineScript)

**Required JSON Fields**:
- `strategy` - Strategy identifier
- `symbol` - Stock ticker
- `price` - Entry/exit price
- `instruction` - buy/sell/short/cover
- `qty` - Quantity of shares

**Dashboard**: http://167.88.36.83:8501 (login: `otto` / `otto`)
