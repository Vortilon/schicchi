"""
Backtesting engine with grid search optimization
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from strategies import get_strategy
from database import Trade, EquityCurve, get_session
import json

class BacktestEngine:
    """Backtesting engine for trading strategies"""
    
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.results = None
    
    def run_backtest(self, strategy, position_size: float = 0.1) -> Dict:
        """
        Run backtest on strategy
        
        Args:
            strategy: Strategy instance
            position_size: Fraction of capital per trade (0.1 = 10%)
        
        Returns:
            Dictionary with backtest results
        """
        df = strategy.generate_signals(self.data.copy())
        
        # Initialize tracking variables
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = [{'timestamp': df.index[0], 'equity': capital, 'cumulative_pnl': 0.0}]
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Close position if signal is exit or stop/target hit
            if position is not None:
                exit_reason = None
                exit_price = None
                
                # Check stop loss
                if current['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'stop_loss'
                # Check take profit
                elif current['high'] >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'take_profit'
                # Check exit signal
                elif current['signal'] == -1:
                    exit_price = current['close']
                    exit_reason = 'signal'
                
                if exit_price is not None:
                    # Calculate P&L
                    if position['side'] == 'long':
                        pnl = (exit_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - exit_price) * position['quantity']
                    
                    pnl_percent = (pnl / (position['entry_price'] * position['quantity'])) * 100
                    capital += pnl
                    
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': current.name,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'side': position['side'],
                        'exit_reason': exit_reason
                    })
                    
                    position = None
            
            # Open new position on signal
            if position is None and current['signal'] == 1:
                trade_capital = capital * position_size
                quantity = trade_capital / current['close']
                
                position = {
                    'side': 'long',
                    'entry_price': current['close'],
                    'entry_time': current.name,
                    'quantity': quantity,
                    'stop_loss': current['stop_loss'],
                    'take_profit': current['take_profit']
                }
            
            # Update equity curve
            current_equity = capital
            if position is not None:
                current_price = current['close']
                if position['side'] == 'long':
                    unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
                else:
                    unrealized_pnl = (position['entry_price'] - current_price) * position['quantity']
                current_equity += unrealized_pnl
            
            cumulative_pnl = current_equity - self.initial_capital
            equity_curve.append({
                'timestamp': current.name,
                'equity': current_equity,
                'cumulative_pnl': cumulative_pnl
            })
        
        # Close any open position at end
        if position is not None:
            last_price = df.iloc[-1]['close']
            if position['side'] == 'long':
                pnl = (last_price - position['entry_price']) * position['quantity']
            else:
                pnl = (position['entry_price'] - last_price) * position['quantity']
            
            pnl_percent = (pnl / (position['entry_price'] * position['quantity'])) * 100
            capital += pnl
            
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': df.index[-1],
                'entry_price': position['entry_price'],
                'exit_price': last_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'side': position['side'],
                'exit_reason': 'end_of_data'
            })
        
        # Calculate metrics
        if len(trades) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'final_capital': capital,
                'returns': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'trades': trades,
                'equity_curve': equity_curve
            }
        
        trades_df = pd.DataFrame(trades)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] <= 0])
        win_rate = (winning_trades / len(trades)) * 100
        total_pnl = trades_df['pnl'].sum()
        returns = ((capital - self.initial_capital) / self.initial_capital) * 100
        
        # Calculate Sharpe ratio (annualized)
        equity_df = pd.DataFrame(equity_curve)
        equity_df['returns'] = equity_df['equity'].pct_change()
        if equity_df['returns'].std() > 0:
            sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252 * 78)  # 78 5-min periods per day
        else:
            sharpe_ratio = 0.0
        
        # Calculate max drawdown
        equity_df['peak'] = equity_df['equity'].expanding().max()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        return {
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'final_capital': capital,
            'returns': returns,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def grid_search(self, strategy_class, param_grid: Dict, position_size: float = 0.1) -> List[Dict]:
        """
        Grid search optimization
        
        Args:
            strategy_class: Strategy class
            param_grid: Dictionary of parameter ranges
            position_size: Fraction of capital per trade
        
        Returns:
            List of results for each parameter combination
        """
        from itertools import product
        
        # Generate all parameter combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = list(product(*values))
        
        results = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            strategy = strategy_class(params)
            
            try:
                result = self.run_backtest(strategy, position_size)
                result['parameters'] = params
                results.append(result)
            except Exception as e:
                print(f"Error with parameters {params}: {e}")
                continue
        
        return results

def optimize_strategy(data: pd.DataFrame, strategy_name: str, param_grid: Dict, 
                     min_win_rate: float = 55.0) -> Dict:
    """
    Optimize strategy parameters using grid search
    
    Args:
        data: Price data DataFrame
        strategy_name: Name of strategy
        param_grid: Parameter grid for optimization
        min_win_rate: Minimum acceptable win rate
    
    Returns:
        Best parameters and results
    """
    from strategies import get_strategy
    
    engine = BacktestEngine(data)
    strategy_class = {
        "RSI Pullback": get_strategy("RSI Pullback", {}).__class__,
        "Bollinger Band Squeeze Breakout": get_strategy("Bollinger Band Squeeze Breakout", {}).__class__,
    }[strategy_name]
    
    results = engine.grid_search(strategy_class, param_grid)
    
    if not results:
        return None
    
    # Filter by minimum win rate
    valid_results = [r for r in results if r['win_rate'] >= min_win_rate]
    
    if not valid_results:
        # If no results meet win rate, return best by Sharpe ratio
        valid_results = results
    
    # Sort by Sharpe ratio (or win rate if similar Sharpe)
    best = max(valid_results, key=lambda x: (x['sharpe_ratio'], x['win_rate']))
    
    return {
        'best_parameters': best['parameters'],
        'best_results': best,
        'all_results': results
    }

