"""
Alpaca API client for forward testing and paper trading
"""
import alpaca_trade_api as tradeapi
from typing import Optional, Dict, List
from datetime import datetime
import os

class AlpacaClient:
    """Wrapper for Alpaca API"""
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 base_url: Optional[str] = None):
        """
        Initialize Alpaca client
        
        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            base_url: Base URL (defaults to paper trading)
        """
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY')
        self.base_url = base_url or 'https://paper-api.alpaca.markets'
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API keys not provided")
        
        self.api = tradeapi.REST(
            self.api_key,
            self.secret_key,
            self.base_url,
            api_version='v2'
        )
    
    def get_account(self) -> Dict:
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'equity': float(account.equity),
                'portfolio_value': float(account.portfolio_value),
                'pattern_day_trader': account.pattern_day_trader,
            }
        except Exception as e:
            raise Exception(f"Error getting account: {str(e)}")
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            positions = self.api.list_positions()
            return [{
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'side': pos.side
            } for pos in positions]
        except Exception as e:
            raise Exception(f"Error getting positions: {str(e)}")
    
    def get_orders(self, status: str = 'all', limit: int = 100) -> List[Dict]:
        """
        Get orders
        
        Args:
            status: Order status ('all', 'open', 'closed', 'filled')
            limit: Maximum number of orders to return
        """
        try:
            orders = self.api.list_orders(status=status, limit=limit)
            return [{
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'order_type': order.order_type,
                'status': order.status,
                'filled_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at
            } for order in orders]
        except Exception as e:
            raise Exception(f"Error getting orders: {str(e)}")
    
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = 'market',
                   time_in_force: str = 'day', stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None) -> Dict:
        """
        Place an order
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            time_in_force: 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
        
        Returns:
            Order information
        """
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'status': order.status,
                'submitted_at': order.submitted_at
            }
        except Exception as e:
            raise Exception(f"Error placing order: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.api.cancel_order(order_id)
            return True
        except Exception as e:
            raise Exception(f"Error canceling order: {str(e)}")
    
    def get_latest_bar(self, symbol: str) -> Optional[Dict]:
        """Get latest bar for symbol"""
        try:
            bars = self.api.get_latest_bar(symbol)
            if bars:
                return {
                    'symbol': symbol,
                    'timestamp': bars.t,
                    'open': float(bars.o),
                    'high': float(bars.h),
                    'low': float(bars.l),
                    'close': float(bars.c),
                    'volume': float(bars.v)
                }
            return None
        except Exception as e:
            print(f"Error getting latest bar for {symbol}: {e}")
            return None

