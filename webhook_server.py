"""
Flask webhook server to receive TradingView alerts and execute Alpaca orders
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from database import get_session, Trade, Strategy
from alpaca_client import AlpacaClient
import json
import os
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for TradingView requests

# Default strategy mapping (can be extended)
DEFAULT_STRATEGY_MAP = {
    'rsi_pullback': 'RSI Pullback',
    'bb_squeeze': 'Bollinger Band Squeeze Breakout',
}

def get_alpaca_client():
    """Get Alpaca client instance"""
    try:
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        if api_key and secret_key:
            return AlpacaClient(api_key, secret_key)
    except Exception as e:
        print(f"Warning: Could not initialize Alpaca client: {e}")
    return None

def parse_tradingview_alert(data: dict) -> dict:
    """
    Parse TradingView webhook alert data
    
    Expected format from TradingView:
    {
        "symbol": "NVDA",
        "action": "buy" or "sell" or "close",
        "price": 150.50,
        "strategy": "rsi_pullback",
        "timestamp": "2024-01-01 10:00:00",
        "stop_loss": 145.00,
        "take_profit": 160.00,
        "quantity": 10,
        ... other fields
    }
    """
    return {
        'symbol': data.get('symbol', '').upper(),
        'action': data.get('action', 'buy').lower(),
        'price': float(data.get('price', 0)),
        'strategy': data.get('strategy', 'rsi_pullback'),
        'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
        'stop_loss': float(data.get('stop_loss', 0)) if data.get('stop_loss') else None,
        'take_profit': float(data.get('take_profit', 0)) if data.get('take_profit') else None,
        'quantity': float(data.get('quantity', 1)),
        'alert_id': data.get('alert_id', data.get('id', str(datetime.utcnow().timestamp())))
    }

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'schicchi-webhook'})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """
    TradingView webhook endpoint
    
    Receives trading alerts from TradingView, executes Alpaca orders, and stores them as trades
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # Parse alert data
        alert = parse_tradingview_alert(data)
        
        # Validate required fields
        if not alert['symbol'] or alert['price'] <= 0:
            return jsonify({'error': 'Invalid symbol or price'}), 400
        
        # Map strategy name
        strategy_name = DEFAULT_STRATEGY_MAP.get(alert['strategy'], alert['strategy'])
        
        session = get_session()
        alpaca = get_alpaca_client()
        
        try:
            # Handle close actions - close existing open positions
            instruction = alert['instruction']
            if instruction in ['close', 'sell', 'cover']:
                # Find open trade for this symbol and strategy
                # For 'sell', close long positions; for 'cover', close short positions
                if instruction == 'sell':
                    open_trade = session.query(Trade).filter_by(
                        symbol=alert['symbol'],
                        strategy_name=strategy_name,
                        side='long',
                        status='open',
                        forward_test=True
                    ).first()
                elif instruction == 'cover':
                    open_trade = session.query(Trade).filter_by(
                        symbol=alert['symbol'],
                        strategy_name=strategy_name,
                        side='short',
                        status='open',
                        forward_test=True
                    ).first()
                else:  # 'close' - close any open position
                    open_trade = session.query(Trade).filter_by(
                        symbol=alert['symbol'],
                        strategy_name=strategy_name,
                        status='open',
                        forward_test=True
                    ).first()
                
                if open_trade:
                    # Execute sell order via Alpaca
                    order_result = None
                    if alpaca:
                        try:
                            # Get current position quantity
                            positions = alpaca.get_positions()
                            position = next((p for p in positions if p['symbol'] == alert['symbol']), None)
                            
                            if position:
                                qty = abs(position['qty'])
                                # For 'sell' (close long), use 'sell'. For 'cover' (close short), use 'buy'
                                alpaca_close_side = 'sell' if instruction == 'sell' else 'buy'
                                order_result = alpaca.place_order(
                                    symbol=alert['symbol'],
                                    qty=qty,
                                    side=alpaca_close_side,
                                    order_type='market'
                                )
                        except Exception as e:
                            print(f"Error executing Alpaca close order: {e}")
                    
                    # Update trade record
                    open_trade.exit_price = alert['price']
                    open_trade.exit_time = datetime.utcnow()
                    open_trade.status = 'closed'
                    
                    # Calculate P&L
                    if open_trade.side == 'long':
                        open_trade.pnl = (open_trade.exit_price - open_trade.entry_price) * open_trade.quantity
                    else:
                        open_trade.pnl = (open_trade.entry_price - open_trade.exit_price) * open_trade.quantity
                    
                    open_trade.pnl_percent = (open_trade.pnl / (open_trade.entry_price * open_trade.quantity)) * 100
                    
                    session.commit()
                    
                    return jsonify({
                        'status': 'success',
                        'trade_id': open_trade.id,
                        'action': 'closed',
                        'alpaca_order_id': order_result.get('id') if order_result else None,
                        'message': f"Trade closed for {alert['symbol']}"
                    }), 200
                else:
                    return jsonify({'error': f'No open position found for {alert["symbol"]}'}), 404
            
            # Handle buy/short (open position) actions
            instruction = alert['instruction']
            if instruction not in ['buy', 'short', 'long', 'sell_short']:
                return jsonify({'error': f'Invalid instruction for opening position: {instruction}. Use buy/short for entries, sell/cover for exits.'}), 400
            
            # Get or create strategy
            strategy = session.query(Strategy).filter_by(name=strategy_name).first()
            if not strategy:
                strategy = Strategy(
                    name=strategy_name,
                    description=f"Strategy from TradingView alerts: {alert['strategy']}",
                    parameters=json.dumps({})
                )
                session.add(strategy)
                session.commit()
                session.refresh(strategy)
            
            strategy_id = strategy.id
            
            # Parse timestamp
            try:
                if isinstance(alert['timestamp'], str):
                    entry_time = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00'))
                else:
                    entry_time = datetime.utcnow()
            except:
                entry_time = datetime.utcnow()
            
            # Determine side
            if instruction in ['buy', 'long']:
                side = 'long'
            elif instruction in ['short', 'sell_short']:
                side = 'short'
            else:
                side = 'long'  # Default
            
            # Execute order via Alpaca
            order_result = None
            if alpaca:
                try:
                    # For Alpaca: 'buy' for long, 'sell' for short
                    alpaca_side = 'buy' if side == 'long' else 'sell'
                    order_result = alpaca.place_order(
                        symbol=alert['symbol'],
                        qty=alert['quantity'],
                        side=alpaca_side,
                        order_type='market'
                    )
                except Exception as e:
                    print(f"Error executing Alpaca order: {e}")
                    # Continue anyway - we'll still record the trade
            
            # Create trade record
            trade = Trade(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                symbol=alert['symbol'],
                side=side,
                entry_price=alert['price'],
                quantity=alert['quantity'],
                stop_loss=alert['stop_loss'],
                take_profit=alert['take_profit'],
                status='open',
                forward_test=True,
                tradingview_alert_id=alert['alert_id'],
                entry_time=entry_time
            )
            
            session.add(trade)
            session.commit()
            session.refresh(trade)
            
            return jsonify({
                'status': 'success',
                'trade_id': trade.id,
                'alpaca_order_id': order_result.get('id') if order_result else None,
                'message': f"Trade executed and recorded for {alert['symbol']}"
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

@app.route('/api/webhook/test', methods=['POST', 'GET'])
def test_webhook():
    """Test endpoint for webhook"""
    if request.method == 'GET':
        return jsonify({
            'message': 'Webhook test endpoint',
            'usage': 'POST JSON data with symbol, action, price, strategy fields'
        })
    
    try:
        data = request.get_json() or {}
        return jsonify({
            'status': 'test_received',
            'data': data,
            'message': 'This is a test endpoint. Use /api/webhook for actual trades.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('WEBHOOK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
