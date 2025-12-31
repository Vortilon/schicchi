"""
Trading strategy implementations
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    return upper, middle, lower

class BaseStrategy:
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, parameters: Dict):
        self.name = name
        self.parameters = parameters
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def validate_parameters(self) -> bool:
        """Validate strategy parameters"""
        return True

class RSIPullbackStrategy(BaseStrategy):
    """
    RSI Pullback Strategy
    Default parameters:
    - rsi_period: 10
    - oversold: 40
    - overbought: 70-80
    - atr_multiplier: 2.0 (for stops/targets)
    - volume_filter: 1.5x average volume
    """
    
    def __init__(self, parameters: Dict):
        super().__init__("RSI Pullback", parameters)
        self.rsi_period = parameters.get('rsi_period', 10)
        self.oversold = parameters.get('oversold', 40)
        self.overbought = parameters.get('overbought', 75)
        self.atr_multiplier_stop = parameters.get('atr_multiplier_stop', 2.0)
        self.atr_multiplier_target = parameters.get('atr_multiplier_target', 3.0)
        self.volume_filter = parameters.get('volume_filter', 1.5)
        self.atr_period = parameters.get('atr_period', 14)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate RSI Pullback signals"""
        df = data.copy()
        
        # Calculate RSI
        df['rsi'] = calculate_rsi(df['close'], period=self.rsi_period)
        
        # Calculate ATR for stops/targets
        df['atr'] = calculate_atr(df['high'], df['low'], df['close'], period=self.atr_period)
        
        # Calculate average volume
        df['avg_volume'] = df['volume'].rolling(window=20).mean()
        
        # Generate signals
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        
        # Long entry: RSI oversold + volume filter
        long_condition = (
            (df['rsi'] < self.oversold) &
            (df['volume'] > df['avg_volume'] * self.volume_filter) &
            (df['close'] > df['close'].shift(1))  # Price pulling back up
        )
        df.loc[long_condition, 'signal'] = 1
        
        # Calculate stops and targets for long entries
        df.loc[df['signal'] == 1, 'stop_loss'] = df.loc[df['signal'] == 1, 'close'] - (
            df.loc[df['signal'] == 1, 'atr'] * self.atr_multiplier_stop
        )
        df.loc[df['signal'] == 1, 'take_profit'] = df.loc[df['signal'] == 1, 'close'] + (
            df.loc[df['signal'] == 1, 'atr'] * self.atr_multiplier_target
        )
        
        # Long exit: RSI overbought
        exit_condition = df['rsi'] > self.overbought
        df.loc[exit_condition & (df['signal'] != 1), 'signal'] = -1
        
        return df

class BollingerBandSqueezeBreakoutStrategy(BaseStrategy):
    """
    Bollinger Band Squeeze Breakout Strategy
    Detects volatility squeeze and trades breakouts
    """
    
    def __init__(self, parameters: Dict):
        super().__init__("Bollinger Band Squeeze Breakout", parameters)
        self.bb_period = parameters.get('bb_period', 20)
        self.bb_std = parameters.get('bb_std', 2.0)
        self.kc_period = parameters.get('kc_period', 20)
        self.kc_mult = parameters.get('kc_mult', 1.5)
        self.squeeze_threshold = parameters.get('squeeze_threshold', 0.0)  # BB inside KC
        self.atr_multiplier_stop = parameters.get('atr_multiplier_stop', 2.0)
        self.atr_multiplier_target = parameters.get('atr_multiplier_target', 3.0)
        self.atr_period = parameters.get('atr_period', 14)
        self.volume_filter = parameters.get('volume_filter', 1.5)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate Bollinger Band Squeeze Breakout signals"""
        df = data.copy()
        
        # Calculate Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            df['close'], period=self.bb_period, num_std=self.bb_std
        )
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        df['bb_width'] = (bb_upper - bb_lower) / bb_middle
        
        # Calculate Keltner Channels (using ATR)
        df['kc_middle'] = df['close'].rolling(window=self.kc_period).mean()
        df['atr'] = calculate_atr(df['high'], df['low'], df['close'], period=self.atr_period)
        df['kc_upper'] = df['kc_middle'] + (df['atr'] * self.kc_mult)
        df['kc_lower'] = df['kc_middle'] - (df['atr'] * self.kc_mult)
        
        # Detect squeeze (BB inside KC)
        df['squeeze'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
        
        # Average volume
        df['avg_volume'] = df['volume'].rolling(window=20).mean()
        
        # Generate signals
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        
        # Long entry: Breakout above BB upper after squeeze + volume
        long_breakout = (
            df['squeeze'].shift(1) &  # Was in squeeze
            (df['close'] > df['bb_upper']) &  # Breaking above BB upper
            (df['volume'] > df['avg_volume'] * self.volume_filter)
        )
        df.loc[long_breakout, 'signal'] = 1
        
        # Calculate stops and targets for long entries
        df.loc[df['signal'] == 1, 'stop_loss'] = df.loc[df['signal'] == 1, 'close'] - (
            df.loc[df['signal'] == 1, 'atr'] * self.atr_multiplier_stop
        )
        df.loc[df['signal'] == 1, 'take_profit'] = df.loc[df['signal'] == 1, 'close'] + (
            df.loc[df['signal'] == 1, 'atr'] * self.atr_multiplier_target
        )
        
        # Exit: Break below BB middle or stop/target hit (handled in backtest)
        exit_condition = df['close'] < df['bb_middle']
        df.loc[exit_condition & (df['signal'] != 1), 'signal'] = -1
        
        return df

def get_strategy(name: str, parameters: Dict) -> BaseStrategy:
    """Factory function to get strategy instance"""
    strategies = {
        "RSI Pullback": RSIPullbackStrategy,
        "Bollinger Band Squeeze Breakout": BollingerBandSqueezeBreakoutStrategy,
    }
    
    if name not in strategies:
        raise ValueError(f"Unknown strategy: {name}")
    
    return strategies[name](parameters)
