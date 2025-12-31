# TradingView Webhook Configuration

## Webhook URL

**Your webhook endpoint:**
```
https://schicchi.noteify.us/api/webhook
```

Or if running on your server at 167.88.36.83:
```
http://167.88.36.83:5000/api/webhook
```

## Expected JSON Format

Send a POST request to the webhook URL with the following JSON structure:

```json
{
    "symbol": "NVDA",
    "action": "buy",
    "price": 150.50,
    "strategy": "rsi_pullback",
    "timestamp": "2024-01-01T10:00:00Z",
    "stop_loss": 145.00,
    "take_profit": 160.00,
    "quantity": 10,
    "alert_id": "unique_alert_id_123"
}
```

### Field Descriptions

- **symbol** (required): Stock ticker symbol (e.g., "NVDA", "AAPL", "PLTR")
- **action** (required): 
  - `"buy"` or `"long"` - Opens a long position (executes Alpaca buy order)
  - `"sell"` or `"short"` - Opens a short position (executes Alpaca sell order)
  - `"close"` - Closes the existing open position for this symbol/strategy (executes opposite Alpaca order)
- **price** (required): Current price at time of alert
- **strategy** (required): Strategy identifier
  - `"rsi_pullback"` - Maps to "RSI Pullback" strategy
  - `"bb_squeeze"` - Maps to "Bollinger Band Squeeze Breakout" strategy
- **timestamp** (optional): ISO format timestamp (defaults to current time if not provided)
- **stop_loss** (optional): Stop loss price
- **take_profit** (optional): Take profit price
- **quantity** (optional): Number of shares (defaults to 1 if not provided)
- **alert_id** (optional): Unique identifier for the alert (auto-generated if not provided)

## TradingView Alert Setup

In TradingView, when creating an alert:

1. Set the webhook URL to: `https://schicchi.noteify.us/api/webhook`

2. In the alert message, use this format (TradingView JSON syntax):
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

### TradingView Variables

- `{{ticker}}` - The symbol (e.g., "NVDA")
- `{{close}}` - The closing price
- `{{time}}` - The timestamp
- You can use other TradingView variables as needed

## Example Alerts

### Entry Alert (Long)
```json
{
    "symbol": "{{ticker}}",
    "action": "buy",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}",
    "stop_loss": {{close}} * 0.95,
    "take_profit": {{close}} * 1.10,
    "quantity": 10
}
```

### Exit Alert (Close Position)
```json
{
    "symbol": "{{ticker}}",
    "action": "close",
    "price": {{close}},
    "strategy": "rsi_pullback",
    "timestamp": "{{time}}"
}
```

## How It Works

1. **TradingView sends alert** → POST to webhook URL with JSON data
2. **Webhook server receives alert** → Parses JSON and validates data
3. **Alpaca order executed** → Places market order based on action:
   - `buy` → Alpaca buy order
   - `sell` → Alpaca sell order (short)
   - `close` → Alpaca order to close existing position
4. **Database updated** → Trade record created/updated with:
   - Entry/exit prices and times
   - P&L calculations
   - Strategy association
   - Order status
5. **Dashboard updates** → Position visible in Streamlit dashboard with real-time P&L

## Server Setup

To run the webhook server on your server (167.88.36.83):

1. **Set environment variables:**
   ```bash
   export ALPACA_API_KEY="PK2GOVNPOKMT4BXY3OFFWOVHBS"
   export ALPACA_SECRET_KEY="3QtrLXygY7ztrP5am1gr6FBUCDq1QAJizvqCP2BuEME2"
   export WEBHOOK_PORT=5000
   ```

2. **Start the webhook server:**
   ```bash
   python webhook_server.py
   ```

3. **Or use systemd service** (see README.md for details)

4. **Configure nginx/reverse proxy** to forward `schicchi.noteify.us/api/webhook` to `localhost:5000/api/webhook`

## Testing

Use the test endpoint to verify webhook is working:
```bash
curl -X GET http://167.88.36.83:5000/api/webhook/test
```

Send a test alert:
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

