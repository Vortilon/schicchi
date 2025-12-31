"""
Schicchi - Intraday Trading Strategy Backtesting and Forward Testing Platform
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import sys
import os
import requests

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_session, Trade, BacktestResult, Strategy, EquityCurve
from strategies import get_strategy, RSIPullbackStrategy, BollingerBandSqueezeBreakoutStrategy
from backtest import BacktestEngine, optimize_strategy
from data_fetcher import fetch_intraday_data, get_latest_price, validate_symbol
from alpaca_client import AlpacaClient
from utils import inject_tailwind_daisyui, format_currency, format_percent, get_color_for_value, validate_login, export_trades_to_csv

# Page configuration
st.set_page_config(
    page_title="Schicchi Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Tailwind CSS and daisyUI
inject_tailwind_daisyui()

# Initialize database
@st.cache_resource
def init_database():
    return init_db()

init_database()

# Authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; min-height: 100vh;">
        <div class="daisy-card" style="max-width: 400px; width: 100%;">
            <h1 style="text-align: center; margin-bottom: 2rem;">Schicchi Trading Platform</h1>
            <h2 style="text-align: center; margin-bottom: 2rem;">Login</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if validate_login(username, password):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    st.stop()

# Main App
st.sidebar.title("📈 Schicchi")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["Dashboard", "Backtesting", "Strategy Optimization", "Forward Testing", "TradingView Alerts"]
)

# Default symbols
default_symbols = ["NVDA", "PLTR", "AAPL"]

# Get or initialize user symbols
if 'user_symbols' not in st.session_state:
    st.session_state.user_symbols = default_symbols.copy()

# Symbols management in sidebar
st.sidebar.markdown("### Symbols")
new_symbol = st.sidebar.text_input("Add Symbol", placeholder="e.g., TSLA")
if st.sidebar.button("Add", use_container_width=True) and new_symbol:
    symbol_upper = new_symbol.upper().strip()
    if validate_symbol(symbol_upper):
        if symbol_upper not in st.session_state.user_symbols:
            st.session_state.user_symbols.append(symbol_upper)
            st.sidebar.success(f"Added {symbol_upper}")
            st.rerun()
    else:
        st.sidebar.error(f"Invalid symbol: {symbol_upper}")

# Display current symbols
if st.session_state.user_symbols:
    for symbol in st.session_state.user_symbols:
        col1, col2 = st.sidebar.columns([3, 1])
        col1.write(symbol)
        if col2.button("×", key=f"remove_{symbol}"):
            st.session_state.user_symbols.remove(symbol)
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

# Dashboard Page
if page == "Dashboard":
    st.title("📊 Dashboard")
    
    # Get forward test trades
    session = get_session()
    try:
        forward_trades = session.query(Trade).filter_by(forward_test=True).order_by(Trade.entry_time.desc()).all()
        
        if forward_trades:
            # Summary stats
            open_trades = [t for t in forward_trades if t.status == 'open']
            closed_trades = [t for t in forward_trades if t.status == 'closed']
            
            total_open = len(open_trades)
            total_closed = len(closed_trades)
            
            if closed_trades:
                winning = len([t for t in closed_trades if t.pnl > 0])
                win_rate = (winning / total_closed) * 100
                total_pnl = sum(t.pnl for t in closed_trades)
            else:
                winning = 0
                win_rate = 0.0
                total_pnl = 0.0
            
            # Update open trades with latest prices
            for trade in open_trades:
                latest_price = get_latest_price(trade.symbol)
                if latest_price:
                    if trade.side == 'long':
                        trade.pnl = (latest_price - trade.entry_price) * trade.quantity
                        trade.pnl_percent = ((latest_price - trade.entry_price) / trade.entry_price) * 100
                    else:
                        trade.pnl = (trade.entry_price - latest_price) * trade.quantity
                        trade.pnl_percent = ((trade.entry_price - latest_price) / trade.entry_price) * 100
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Open Trades", total_open)
            with col2:
                st.metric("Closed Trades", total_closed)
            with col3:
                st.metric("Win Rate", f"{win_rate:.2f}%")
            with col4:
                st.metric("Total P&L", format_currency(total_pnl))
            
            # Open Positions Section
            if open_trades:
                st.subheader("🔵 Open Positions")
                
                # Store selected trade in session state
                if 'selected_trade_id' not in st.session_state:
                    st.session_state.selected_trade_id = None
                
                # Display open positions as cards
                for trade in open_trades:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{trade.symbol}**")
                            st.caption(f"Strategy: {trade.strategy_name}")
                        
                        with col2:
                            st.markdown(f"**{trade.side.upper()}**")
                            st.caption(f"Qty: {trade.quantity:.2f}")
                        
                        with col3:
                            st.markdown(f"Entry: ${trade.entry_price:.2f}")
                            current_price = get_latest_price(trade.symbol) or trade.entry_price
                            st.caption(f"Current: ${current_price:.2f}")
                        
                        with col4:
                            pnl_color = "🟢" if trade.pnl > 0 else "🔴" if trade.pnl < 0 else "⚪"
                            st.markdown(f"{pnl_color} P&L: {format_currency(trade.pnl)}")
                            st.caption(f"({format_percent(trade.pnl_percent)})")
                        
                        with col5:
                            if st.button("View", key=f"view_{trade.id}"):
                                st.session_state.selected_trade_id = trade.id
                                st.rerun()
                        
                        st.divider()
            
            # Strategy breakdown
            st.subheader("Performance by Strategy")
            strategy_stats = {}
            for trade in forward_trades:
                if trade.strategy_name not in strategy_stats:
                    strategy_stats[trade.strategy_name] = {
                        'open': 0, 'closed': 0, 'winning': 0, 'pnl': 0.0
                    }
                if trade.status == 'open':
                    strategy_stats[trade.strategy_name]['open'] += 1
                else:
                    strategy_stats[trade.strategy_name]['closed'] += 1
                    if trade.pnl > 0:
                        strategy_stats[trade.strategy_name]['winning'] += 1
                    strategy_stats[trade.strategy_name]['pnl'] += trade.pnl
            
            strategy_df = pd.DataFrame([
                {
                    'Strategy': name,
                    'Open': stats['open'],
                    'Closed': stats['closed'],
                    'Win Rate': (stats['winning'] / stats['closed'] * 100) if stats['closed'] > 0 else 0,
                    'P&L': format_currency(stats['pnl'])
                }
                for name, stats in strategy_stats.items()
            ])
            st.dataframe(strategy_df, use_container_width=True)
            
            # Position Detail View
            if st.session_state.selected_trade_id:
                selected_trade = next((t for t in forward_trades if t.id == st.session_state.selected_trade_id), None)
                if selected_trade:
                    st.subheader(f"📊 Position Details: {selected_trade.symbol} - {selected_trade.strategy_name}")
                    
                    if st.button("← Back to Dashboard"):
                        st.session_state.selected_trade_id = None
                        st.rerun()
                    
                    # Position info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Entry Price", format_currency(selected_trade.entry_price))
                        st.metric("Quantity", f"{selected_trade.quantity:.2f}")
                    with col2:
                        current_price = get_latest_price(selected_trade.symbol) or selected_trade.entry_price
                        st.metric("Current Price", format_currency(current_price))
                        if selected_trade.stop_loss:
                            st.metric("Stop Loss", format_currency(selected_trade.stop_loss))
                    with col3:
                        st.metric("P&L", format_currency(selected_trade.pnl), 
                                 delta=format_percent(selected_trade.pnl_percent))
                        if selected_trade.take_profit:
                            st.metric("Take Profit", format_currency(selected_trade.take_profit))
                    with col4:
                        st.metric("Side", selected_trade.side.upper())
                        st.metric("Status", selected_trade.status.upper())
                    
                    # Price chart with entry/exit markers
                    try:
                        # Fetch historical data for the symbol
                        data = fetch_intraday_data(selected_trade.symbol, period_months=1, interval='15m')
                        
                        # Create chart
                        fig = go.Figure()
                        
                        # Price line
                        fig.add_trace(go.Scatter(
                            x=data.index,
                            y=data['close'],
                            mode='lines',
                            name='Price',
                            line=dict(color='blue', width=1)
                        ))
                        
                        # Entry marker
                        entry_idx = data.index.get_indexer([selected_trade.entry_time], method='nearest')[0]
                        fig.add_trace(go.Scatter(
                            x=[data.index[entry_idx]],
                            y=[selected_trade.entry_price],
                            mode='markers',
                            name='Entry',
                            marker=dict(size=15, color='green', symbol='triangle-up')
                        ))
                        
                        # Exit marker (if closed)
                        if selected_trade.exit_time and selected_trade.exit_price:
                            exit_idx = data.index.get_indexer([selected_trade.exit_time], method='nearest')[0]
                            color = 'red' if selected_trade.pnl < 0 else 'orange'
                            fig.add_trace(go.Scatter(
                                x=[data.index[exit_idx]],
                                y=[selected_trade.exit_price],
                                mode='markers',
                                name='Exit',
                                marker=dict(size=15, color=color, symbol='triangle-down')
                            ))
                        
                        # Stop loss line
                        if selected_trade.stop_loss:
                            fig.add_hline(y=selected_trade.stop_loss, line_dash="dash", 
                                        line_color="red", annotation_text="Stop Loss")
                        
                        # Take profit line
                        if selected_trade.take_profit:
                            fig.add_hline(y=selected_trade.take_profit, line_dash="dash", 
                                        line_color="green", annotation_text="Take Profit")
                        
                        fig.update_layout(
                            title=f"{selected_trade.symbol} Price Chart",
                            xaxis_title="Time",
                            yaxis_title="Price ($)",
                            height=500,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error loading chart: {str(e)}")
                    
                    # All trades for this symbol/strategy
                    st.subheader(f"All Trades: {selected_trade.symbol} - {selected_trade.strategy_name}")
                    symbol_trades = [t for t in forward_trades 
                                   if t.symbol == selected_trade.symbol 
                                   and t.strategy_name == selected_trade.strategy_name]
                    
                    trades_detail = []
                    for t in symbol_trades:
                        trades_detail.append({
                            'ID': t.id,
                            'Entry Time': t.entry_time.strftime('%Y-%m-%d %H:%M') if t.entry_time else '-',
                            'Exit Time': t.exit_time.strftime('%Y-%m-%d %H:%M') if t.exit_time else '-',
                            'Side': t.side,
                            'Entry Price': format_currency(t.entry_price),
                            'Exit Price': format_currency(t.exit_price) if t.exit_price else '-',
                            'Quantity': f"{t.quantity:.2f}",
                            'P&L': format_currency(t.pnl) if t.pnl else '-',
                            'P&L %': format_percent(t.pnl_percent) if t.pnl_percent else '-',
                            'Status': t.status
                        })
                    
                    st.dataframe(pd.DataFrame(trades_detail), use_container_width=True)
            
            # Recent trades table (if no position selected)
            if not st.session_state.selected_trade_id:
                st.subheader("Recent Trades")
                trades_data = []
                for trade in forward_trades[:50]:  # Latest 50
                    trades_data.append({
                        'ID': trade.id,
                        'Symbol': trade.symbol,
                        'Strategy': trade.strategy_name,
                        'Side': trade.side,
                        'Entry Price': trade.entry_price,
                        'Exit Price': trade.exit_price if trade.exit_price else '-',
                        'Quantity': trade.quantity,
                        'P&L': format_currency(trade.pnl) if trade.pnl else '-',
                        'P&L %': format_percent(trade.pnl_percent) if trade.pnl_percent else '-',
                        'Status': trade.status,
                        'Entry Time': trade.entry_time.strftime('%Y-%m-%d %H:%M') if trade.entry_time else '-',
                    })
                
                trades_df = pd.DataFrame(trades_data)
                st.dataframe(trades_df, use_container_width=True, height=400)
            
            # Export button
            if st.button("Export Trades to CSV"):
                csv = export_trades_to_csv(trades_data)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No forward test trades yet. Start backtesting or receive TradingView alerts to see data here.")
    
    finally:
        session.close()

# Backtesting Page
elif page == "Backtesting":
    st.title("🔬 Backtesting")
    
    # Strategy selection
    strategy_name = st.selectbox(
        "Select Strategy",
        ["RSI Pullback", "Bollinger Band Squeeze Breakout"],
        index=0
    )
    
    # Symbol selection
    symbol = st.selectbox("Symbol", st.session_state.user_symbols)
    
    # Period selection
    period_months = st.slider("Data Period (months)", 1, 12, 6)
    
    # Strategy parameters
    st.subheader("Strategy Parameters")
    
    if strategy_name == "RSI Pullback":
        col1, col2 = st.columns(2)
        with col1:
            rsi_period = st.number_input("RSI Period", 5, 30, 10)
            oversold = st.number_input("Oversold Level", 20, 50, 40)
            atr_period = st.number_input("ATR Period", 10, 30, 14)
        with col2:
            overbought = st.number_input("Overbought Level", 60, 90, 75)
            atr_multiplier_stop = st.number_input("ATR Multiplier (Stop)", 1.0, 5.0, 2.0, 0.1)
            atr_multiplier_target = st.number_input("ATR Multiplier (Target)", 1.0, 10.0, 3.0, 0.1)
        
        volume_filter = st.slider("Volume Filter (x average)", 1.0, 3.0, 1.5, 0.1)
        
        parameters = {
            'rsi_period': rsi_period,
            'oversold': oversold,
            'overbought': overbought,
            'atr_period': atr_period,
            'atr_multiplier_stop': atr_multiplier_stop,
            'atr_multiplier_target': atr_multiplier_target,
            'volume_filter': volume_filter
        }
    else:  # Bollinger Band Squeeze Breakout
        col1, col2 = st.columns(2)
        with col1:
            bb_period = st.number_input("BB Period", 10, 50, 20)
            bb_std = st.number_input("BB Standard Deviation", 1.0, 3.0, 2.0, 0.1)
            kc_period = st.number_input("KC Period", 10, 50, 20)
        with col2:
            kc_mult = st.number_input("KC Multiplier", 1.0, 3.0, 1.5, 0.1)
            atr_multiplier_stop = st.number_input("ATR Multiplier (Stop)", 1.0, 5.0, 2.0, 0.1)
            atr_multiplier_target = st.number_input("ATR Multiplier (Target)", 1.0, 10.0, 3.0, 0.1)
        
        volume_filter = st.slider("Volume Filter (x average)", 1.0, 3.0, 1.5, 0.1)
        
        parameters = {
            'bb_period': bb_period,
            'bb_std': bb_std,
            'kc_period': kc_period,
            'kc_mult': kc_mult,
            'atr_multiplier_stop': atr_multiplier_stop,
            'atr_multiplier_target': atr_multiplier_target,
            'volume_filter': volume_filter,
            'atr_period': 14
        }
    
    # Initial capital
    initial_capital = st.number_input("Initial Capital", 10000, 1000000, 100000, 10000)
    position_size = st.slider("Position Size (% of capital)", 0.05, 1.0, 0.1, 0.05)
    
    # Run backtest button
    if st.button("Run Backtest", type="primary", use_container_width=True):
        with st.spinner(f"Fetching data for {symbol}..."):
            try:
                data = fetch_intraday_data(symbol, period_months, interval='5m')
                st.success(f"Loaded {len(data)} data points")
                
                with st.spinner("Running backtest..."):
                    strategy = get_strategy(strategy_name, parameters)
                    engine = BacktestEngine(data, initial_capital)
                    results = engine.run_backtest(strategy, position_size)
                    
                    # Display results
                    st.subheader("Backtest Results")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Trades", results['total_trades'])
                        st.metric("Win Rate", f"{results['win_rate']:.2f}%")
                    with col2:
                        st.metric("Winning Trades", results['winning_trades'])
                        st.metric("Losing Trades", results['losing_trades'])
                    with col3:
                        st.metric("Total P&L", format_currency(results['total_pnl']))
                        st.metric("Returns", format_percent(results['returns']))
                    with col4:
                        st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
                        st.metric("Max Drawdown", format_percent(results['max_drawdown']))
                    
                    # Equity curve chart
                    if results['equity_curve']:
                        equity_df = pd.DataFrame(results['equity_curve'])
                        fig = px.line(
                            equity_df,
                            x='timestamp',
                            y='equity',
                            title='Equity Curve',
                            labels={'equity': 'Equity ($)', 'timestamp': 'Date'}
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Trades table
                    if results['trades']:
                        st.subheader("Trade Log")
                        trades_df = pd.DataFrame(results['trades'])
                        st.dataframe(trades_df, use_container_width=True, height=400)
                        
                        # Save backtest result
                        session = get_session()
                        try:
                            strategy_obj = session.query(Strategy).filter_by(name=strategy_name).first()
                            if not strategy_obj:
                                strategy_obj = Strategy(
                                    name=strategy_name,
                                    description=f"{strategy_name} strategy",
                                    parameters=json.dumps(parameters)
                                )
                                session.add(strategy_obj)
                                session.commit()
                                session.refresh(strategy_obj)
                            
                            backtest_result = BacktestResult(
                                strategy_id=strategy_obj.id,
                                strategy_name=strategy_name,
                                symbol=symbol,
                                start_date=data.index[0],
                                end_date=data.index[-1],
                                parameters=json.dumps(parameters),
                                total_trades=results['total_trades'],
                                winning_trades=results['winning_trades'],
                                losing_trades=results['losing_trades'],
                                win_rate=results['win_rate'],
                                total_pnl=results['total_pnl'],
                                sharpe_ratio=results['sharpe_ratio'],
                                max_drawdown=results['max_drawdown']
                            )
                            session.add(backtest_result)
                            session.commit()
                            st.success("Backtest results saved!")
                        finally:
                            session.close()
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Strategy Optimization Page
elif page == "Strategy Optimization":
    st.title("⚙️ Strategy Optimization")
    
    strategy_name = st.selectbox(
        "Select Strategy",
        ["RSI Pullback", "Bollinger Band Squeeze Breakout"]
    )
    
    symbol = st.selectbox("Symbol", st.session_state.user_symbols)
    period_months = st.slider("Data Period (months)", 1, 12, 6)
    min_win_rate = st.slider("Minimum Win Rate (%)", 0, 100, 55)
    
    st.subheader("Parameter Grid")
    
    if strategy_name == "RSI Pullback":
        rsi_periods = st.multiselect("RSI Periods", [5, 7, 10, 14, 20, 30], default=[7, 10, 14])
        oversold_levels = st.multiselect("Oversold Levels", [30, 35, 40, 45, 50], default=[35, 40, 45])
        overbought_levels = st.multiselect("Overbought Levels", [70, 75, 80, 85], default=[70, 75, 80])
        
        if st.button("Run Optimization", type="primary", use_container_width=True):
            if not (rsi_periods and oversold_levels and overbought_levels):
                st.error("Please select at least one value for each parameter")
            else:
                with st.spinner(f"Fetching data for {symbol}..."):
                    try:
                        data = fetch_intraday_data(symbol, period_months, interval='5m')
                        
                        param_grid = {
                            'rsi_period': rsi_periods,
                            'oversold': oversold_levels,
                            'overbought': overbought_levels,
                            'atr_period': [14],
                            'atr_multiplier_stop': [2.0],
                            'atr_multiplier_target': [3.0],
                            'volume_filter': [1.5]
                        }
                        
                        with st.spinner("Running optimization (this may take a while)..."):
                            from backtest import optimize_strategy
                            best = optimize_strategy(data, strategy_name, param_grid, min_win_rate)
                            
                            if best:
                                st.subheader("Best Parameters")
                                st.json(best['best_parameters'])
                                
                                st.subheader("Best Results")
                                best_results = best['best_results']
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Win Rate", f"{best_results['win_rate']:.2f}%")
                                with col2:
                                    st.metric("Total P&L", format_currency(best_results['total_pnl']))
                                with col3:
                                    st.metric("Sharpe Ratio", f"{best_results['sharpe_ratio']:.2f}")
                                with col4:
                                    st.metric("Max Drawdown", format_percent(best_results['max_drawdown']))
                                
                                # Show all results
                                if len(best['all_results']) > 1:
                                    st.subheader("All Results (Top 10)")
                                    results_data = []
                                    sorted_results = sorted(best['all_results'], 
                                                          key=lambda x: (x['sharpe_ratio'], x['win_rate']), 
                                                          reverse=True)[:10]
                                    for r in sorted_results:
                                        results_data.append({
                                            'Parameters': json.dumps(r['parameters']),
                                            'Win Rate': f"{r['win_rate']:.2f}%",
                                            'Total P&L': format_currency(r['total_pnl']),
                                            'Sharpe': f"{r['sharpe_ratio']:.2f}",
                                            'Max DD': format_percent(r['max_drawdown'])
                                        })
                                    st.dataframe(pd.DataFrame(results_data), use_container_width=True)
                            else:
                                st.error("No results found")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    else:
        st.info("Optimization for Bollinger Band Squeeze Breakout coming soon")
        # Similar structure can be added here

# Forward Testing Page
elif page == "Forward Testing":
    st.title("🚀 Forward Testing")
    
    st.info("Forward testing trades are recorded via TradingView webhook alerts. View trades on the Dashboard.")
    
    # Alpaca integration status
    st.subheader("Alpaca Integration")
    
    try:
        # Try to get from Streamlit secrets, fallback to environment variables
        try:
            api_key = st.secrets["alpaca_api_key"]
            secret_key = st.secrets["alpaca_secret_key"]
        except (KeyError, AttributeError):
            api_key = os.getenv('ALPACA_API_KEY')
            secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if api_key and secret_key:
            try:
                alpaca = AlpacaClient(api_key, secret_key)
                account = alpaca.get_account()
                
                st.success("✅ Connected to Alpaca Paper Trading")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Equity", format_currency(account['equity']))
                with col2:
                    st.metric("Cash", format_currency(account['cash']))
                with col3:
                    st.metric("Buying Power", format_currency(account['buying_power']))
                
                # Current positions
                positions = alpaca.get_positions()
                if positions:
                    st.subheader("Current Positions")
                    pos_df = pd.DataFrame(positions)
                    st.dataframe(pos_df, use_container_width=True)
                else:
                    st.info("No open positions")
                
                # Recent orders
                orders = alpaca.get_orders(status='all', limit=20)
                if orders:
                    st.subheader("Recent Orders")
                    orders_df = pd.DataFrame(orders)
                    st.dataframe(orders_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error connecting to Alpaca: {str(e)}")
        else:
            st.warning("Alpaca API keys not configured. Check secrets.toml or environment variables.")
    
    except Exception as e:
        st.warning(f"Could not load Alpaca credentials: {str(e)}")

# TradingView Alerts Page
elif page == "TradingView Alerts":
    st.title("🔔 TradingView Alerts")
    
    st.subheader("Webhook Endpoint")
    
    # Get server URL
    server_url = st.text_input(
        "Server URL",
        value="https://schicchi.noteify.us",
        help="Your server URL where the webhook endpoint is hosted"
    )
    
    webhook_url = f"{server_url}/api/webhook"
    
    st.code(webhook_url, language="text")
    
    st.markdown(f"""
    **Webhook Endpoint:** `{server_url}/api/webhook`
    
    Configure your TradingView alerts to POST to this endpoint with the following JSON format:
    
    ```json
    {{
        "symbol": "NVDA",
        "action": "buy",
        "price": 150.50,
        "strategy": "rsi_pullback",
        "timestamp": "2024-01-01T10:00:00Z",
        "stop_loss": 145.00,
        "take_profit": 160.00,
        "quantity": 10,
        "alert_id": "unique_alert_id"
    }}
    ```
    
    **Strategy values:** `rsi_pullback` or `bb_squeeze`  
    **Action values:** 
    - `buy` or `long` - Open long position (executes Alpaca buy order)
    - `sell` or `short` - Open short position (executes Alpaca sell order)  
    - `close` - Close existing open position for this symbol/strategy (executes opposite Alpaca order)
    
    **Note:** Orders are automatically executed via Alpaca API when received. Ensure Alpaca credentials are configured.
    """)
    
    # Test webhook
    st.subheader("Test Webhook")
    
    with st.form("test_webhook_form"):
        test_symbol = st.selectbox("Symbol", st.session_state.user_symbols)
        test_action = st.selectbox("Action", ["buy", "sell"])
        test_price = st.number_input("Price", 0.0, 10000.0, 100.0, 0.01)
        test_strategy = st.selectbox("Strategy", ["rsi_pullback", "bb_squeeze"])
        test_stop = st.number_input("Stop Loss", 0.0, 10000.0, 95.0, 0.01)
        test_target = st.number_input("Take Profit", 0.0, 10000.0, 110.0, 0.01)
        test_qty = st.number_input("Quantity", 1.0, 1000.0, 10.0, 1.0)
        
        if st.form_submit_button("Send Test Alert"):
            test_data = {
                "symbol": test_symbol,
                "action": test_action,
                "price": test_price,
                "strategy": test_strategy,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "stop_loss": test_stop,
                "take_profit": test_target,
                "quantity": test_qty,
                "alert_id": f"test_{datetime.now().timestamp()}"
            }
            
            try:
                response = requests.post(webhook_url, json=test_data, timeout=5)
                if response.status_code == 200:
                    st.success("Test alert sent successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Error sending test alert: {str(e)}")
                st.info("Note: The webhook server must be running. Start it with: `python webhook_server.py`")

