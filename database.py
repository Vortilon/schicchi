"""
Database models and setup for SQLite storage
"""
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

def utcnow():
    return datetime.utcnow()

Base = declarative_base()

class Strategy(Base):
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    parameters = Column(Text)  # JSON string of parameters
    created_at = Column(DateTime, default=datetime.utcnow)

class BacktestResult(Base):
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, nullable=False)
    strategy_name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    parameters = Column(Text)  # JSON string
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, nullable=False)
    strategy_name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # 'long' or 'short'
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    quantity = Column(Float, nullable=False)
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    status = Column(String(20), default='open')  # 'open', 'closed', 'stopped'
    stop_loss = Column(Float)
    take_profit = Column(Float)
    backtest_id = Column(Integer)  # If from backtest
    forward_test = Column(Boolean, default=False)
    tradingview_alert_id = Column(String(100))  # ID from TradingView webhook
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class EquityCurve(Base):
    __tablename__ = 'equity_curves'
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer)
    strategy_name = Column(String(100))
    symbol = Column(String(20))
    timestamp = Column(DateTime, nullable=False)
    equity = Column(Float, nullable=False)
    cumulative_pnl = Column(Float, default=0.0)

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), 'schicchi.db')

def get_engine():
    return create_engine(f'sqlite:///{DB_PATH}', echo=False)

def init_db():
    """Initialize database and create tables"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

