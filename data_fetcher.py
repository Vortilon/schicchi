"""
Data fetching module for market data (yfinance and real-time updates)
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import pytz

def fetch_intraday_data(symbol: str, period_months: int = 6, interval: str = '5m') -> pd.DataFrame:
    """
    Fetch intraday data using yfinance
    
    Args:
        symbol: Stock symbol (e.g., 'NVDA')
        period_months: Number of months of historical data
        interval: Data interval ('5m', '15m', '1h', '1d')
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Calculate period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_months * 30)
        
        # Fetch data
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")
        
        # Rename columns to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns in data for {symbol}")
        
        # Sort by index (datetime)
        df = df.sort_index()
        
        # Remove any NaN rows
        df = df.dropna()
        
        return df
    
    except Exception as e:
        raise Exception(f"Error fetching data for {symbol}: {str(e)}")

def get_latest_price(symbol: str) -> Optional[float]:
    """
    Get latest/last close price for a symbol
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Latest price or None if error
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.history(period='1d', interval='1m')
        if not info.empty:
            return float(info['Close'].iloc[-1])
        return None
    except Exception as e:
        print(f"Error getting latest price for {symbol}: {e}")
        return None

def get_current_price(symbol: str) -> Optional[float]:
    """
    Get current market price (15-min delayed for free tier)
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Current price or None if error
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d', interval='1m')
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return None
    except Exception as e:
        print(f"Error getting current price for {symbol}: {e}")
        return None

def validate_symbol(symbol: str) -> bool:
    """
    Validate if symbol is valid
    
    Args:
        symbol: Stock symbol to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return 'symbol' in info and info['symbol'] == symbol.upper()
    except:
        return False

