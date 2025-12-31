# Schicchi - Intraday Trading Strategy Platform

A comprehensive Python Streamlit web application for backtesting, optimizing, forward testing, and tracking multiple intraday trading strategies on stocks.

## Features

- **Strategy Backtesting**: Test RSI Pullback and Bollinger Band Squeeze Breakout strategies on historical intraday data
- **Grid Search Optimization**: Automatically find optimal parameters targeting 55%+ win rates
- **Forward Testing**: Track live trades via TradingView webhook alerts
- **Real-time Monitoring**: View open positions with live price updates
- **Interactive Dashboard**: Beautiful charts and tables with daisyUI styling
- **Alpaca Integration**: Connect to Alpaca Paper Trading API for forward testing
- **TradingView Webhooks**: Receive trade alerts from TradingView strategies

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Git (for cloning the repository)
- SSH key set up for GitHub (for repository access)

### Installation

1. **Clone the repository** (using SSH):
   ```bash
   git clone git@github.com:Vortilon/schicchi.git
   cd schicchi
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up secrets** (for Alpaca API):
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   # Edit .streamlit/secrets.toml with your API keys (already configured with provided keys)
   ```

5. **Initialize the database**:
   The database will be automatically created on first run.

### Running Locally

**Start the Streamlit app**:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

**Start the webhook server** (optional, for TradingView alerts):
```bash
python webhook_server.py
```

The webhook server will run on `http://localhost:5000` by default.

### Default Login Credentials

- Username: `otto`
- Password: `otto`

## Project Structure

```
schicchi/
├── app.py                 # Main Streamlit application
├── webhook_server.py      # Flask server for TradingView webhooks
├── database.py            # SQLite database models and setup
├── strategies.py          # Trading strategy implementations
├── backtest.py            # Backtesting engine with optimization
├── data_fetcher.py        # Market data fetching (yfinance)
├── alpaca_client.py       # Alpaca API integration
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── .streamlit/
│   ├── secrets.toml       # API keys and configuration (not in git)
│   └── secrets.toml.template
└── README.md
```

## SSH Setup for GitHub (if needed)

If you haven't set up SSH keys for GitHub:

1. **Generate SSH key**:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter to accept default file location
   # Enter a passphrase (optional but recommended)
   ```

2. **Add SSH key to ssh-agent**:
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

3. **Copy public key**:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

4. **Add to GitHub**:
   - Go to GitHub.com → Settings → SSH and GPG keys
   - Click "New SSH key"
   - Paste your public key and save

5. **Test connection**:
   ```bash
   ssh -T git@github.com
   ```

## Deployment to Streamlit Cloud

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main  # or master, depending on your default branch
   ```

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select repository: `Vortilon/schicchi`
   - Main file path: `app.py`
   - Click "Deploy"

3. **Configure secrets on Streamlit Cloud**:
   - In your app settings, go to "Secrets"
   - Add the contents of `.streamlit/secrets.toml`:
     ```toml
     alpaca_api_key = "your_key"
     alpaca_secret_key = "your_secret"
     ```

## TradingView Webhook Setup

1. **Deploy webhook server** (on your server at 167.88.36.83):
   ```bash
   # On your server
   cd /path/to/schicchi
   python webhook_server.py
   # Or use a process manager like PM2, systemd, or supervisor
   ```

   **Using systemd** (recommended for production):
   ```bash
   # Copy the service template and edit paths
   sudo cp schicchi-webhook.service.template /etc/systemd/system/schicchi-webhook.service
   sudo nano /etc/systemd/system/schicchi-webhook.service
   # Update WorkingDirectory and paths as needed
   
   # Enable and start the service
   sudo systemctl enable schicchi-webhook
   sudo systemctl start schicchi-webhook
   sudo systemctl status schicchi-webhook
   ```

2. **Configure TradingView alert**:
   - In TradingView, create an alert with webhook URL:
     ```
     https://schicchi.noteify.us/api/webhook
     ```
   - Use this JSON format in your alert message:
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

3. **Strategy values**:
   - `rsi_pullback` for RSI Pullback strategy
   - `bb_squeeze` for Bollinger Band Squeeze Breakout strategy

## Using the Application

### Dashboard
- View summary statistics of forward test trades
- See performance by strategy and symbol
- Monitor open positions with real-time prices
- Export trades to CSV

### Backtesting
- Select a strategy and symbol
- Adjust parameters
- Run backtest on historical 5-minute data
- View equity curve and trade log
- Results are automatically saved

### Strategy Optimization
- Define parameter ranges for grid search
- Find optimal parameters targeting minimum win rate
- Compare results across different parameter combinations

### Forward Testing
- View Alpaca account status and positions
- Monitor trades received from TradingView alerts
- See real-time price updates for open positions

### TradingView Alerts
- Get webhook endpoint URL
- Test webhook with sample data
- View instructions for TradingView alert configuration

## Strategies

### RSI Pullback
- **Entry**: RSI oversold (< 40) with volume confirmation (> 1.5x average)
- **Exit**: RSI overbought (> 75) or stop/target hit
- **Default Parameters**:
  - RSI Period: 10
  - Oversold: 40
  - Overbought: 75
  - ATR Multiplier (Stop): 2.0
  - ATR Multiplier (Target): 3.0
  - Volume Filter: 1.5x

### Bollinger Band Squeeze Breakout
- **Entry**: Breakout above BB upper after volatility squeeze
- **Exit**: Price breaks below BB middle or stop/target hit
- **Default Parameters**:
  - BB Period: 20
  - BB Standard Deviation: 2.0
  - KC Period: 20
  - KC Multiplier: 1.5
  - ATR Multiplier (Stop): 2.0
  - ATR Multiplier (Target): 3.0
  - Volume Filter: 1.5x

## Data Sources

- **Historical Data**: yfinance (free, no API key required)
- **Real-time Prices**: yfinance (15-minute delayed for free tier)
- **Forward Testing**: Alpaca Paper Trading API

## Troubleshooting

### Database Issues
If you encounter database errors, delete `schicchi.db` and restart the app to recreate it.

### Webhook Server Not Receiving Alerts
- Ensure the server is running and accessible
- Check firewall rules for port 5000
- Verify TradingView alert webhook URL is correct
- Check server logs for errors

### Alpaca Connection Issues
- Verify API keys in `.streamlit/secrets.toml`
- Check that you're using paper trading API keys (not live)
- Ensure API keys have proper permissions

## License

This project is provided as-is for trading strategy development and testing purposes.

## Support

For issues or questions, please open an issue on the GitHub repository.

