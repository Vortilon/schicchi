"""
Utility functions
"""
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

def format_currency(value: float, decimals: int = 2) -> str:
    """Format number as currency"""
    return f"${value:,.{decimals}f}"

def format_percent(value: float, decimals: int = 2) -> str:
    """Format number as percentage"""
    return f"{value:.{decimals}f}%"

def get_color_for_value(value: float, threshold: float = 0) -> str:
    """Get color (green/red) based on value"""
    if value > threshold:
        return 'text-success'  # daisyUI success color
    elif value < threshold:
        return 'text-error'  # daisyUI error color
    return 'text-base-content'  # neutral

def validate_login(username: str, password: str) -> bool:
    """Simple login validation"""
    return username == "otto" and password == "otto"

def inject_tailwind_daisyui():
    """Inject Tailwind CSS and daisyUI via CDN"""
    st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.4.19/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            daisyui: {
                themes: ["light", "dark", "cupcake"],
            },
        }
    </script>
    <style>
        .stApp {
            background-color: hsl(var(--b2, 0 0% 100%));
        }
        .daisy-card {
            background-color: hsl(var(--b1, 0 0% 100%));
            border-radius: 1rem;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
            padding: 1.5rem;
        }
        .daisy-btn {
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        .daisy-btn-primary {
            background-color: hsl(var(--p, 259 94% 51%));
            color: hsl(var(--pc, 0 0% 100%));
        }
        .daisy-btn-primary:hover {
            background-color: hsl(var(--pf, 259 94% 51%));
        }
        .daisy-stats {
            background-color: hsl(var(--b1, 0 0% 100%));
            border-radius: 0.5rem;
            padding: 1rem;
        }
        .text-success {
            color: hsl(var(--su, 142 76% 36%));
        }
        .text-error {
            color: hsl(var(--er, 0 84% 60%));
        }
        .text-warning {
            color: hsl(var(--wa, 38 92% 50%));
        }
        .text-info {
            color: hsl(var(--in, 199 89% 48%));
        }
        .table-container {
            border-radius: 0.5rem;
            overflow-x: auto;
        }
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(title: str, value: str, delta: Optional[str] = None, 
                      delta_color: Optional[str] = None) -> str:
    """Create a daisyUI-style metric card HTML"""
    delta_html = f'<div class="text-sm {delta_color or "text-base-content"}">{delta}</div>' if delta else ''
    return f"""
    <div class="daisy-stats shadow">
        <div class="stat">
            <div class="stat-title text-base-content/70">{title}</div>
            <div class="stat-value text-primary">{value}</div>
            {delta_html}
        </div>
    </div>
    """

def export_trades_to_csv(trades: List[Dict], filename: str = None) -> str:
    """Export trades to CSV format"""
    if not filename:
        filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    df = pd.DataFrame(trades)
    csv = df.to_csv(index=False)
    return csv

