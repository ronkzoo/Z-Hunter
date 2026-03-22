import re

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def get_block(start, end):
    return "".join(lines[start-1:end])

# utils.py setup
utils_content = """import requests
import json
import os
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

load_dotenv(override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

""" + get_block(176, 188) + "\n" + get_block(190, 219) + "\n" + get_block(397, 412) + "\n" + get_block(17, 36)

with open("utils.py", "w", encoding="utf-8") as f:
    f.write(utils_content)

# data_loader.py setup
data_loader_content = """import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta

""" + get_block(414, 424) + "\n" + get_block(221, 342) + "\n" + get_block(344, 395) + "\n" + get_block(426, 493) + "\n" + get_block(495, 554)

with open("data_loader.py", "w", encoding="utf-8") as f:
    f.write(data_loader_content)

# new app.py setup
new_app_lines = []
skip_ranges = [
    (14, 15), # TELEGRAM configs
    (17, 36), # send_telegram_message
    (176, 188), # UNIVERSE_DICT
    (190, 219), # TICKER_NAMES_FILE, load_ticker_names, etc
    (221, 395), # backtest_symbol, backtest_hybrid_symbol
    (397, 412), # watchlists
    (414, 554), # calculate_hurst, get_hybrid_signal, get_live_signal
]

def should_skip(idx):
    for start, end in skip_ranges:
        if start <= idx + 1 <= end:
            return True
    return False

for i, line in enumerate(lines):
    if should_skip(i):
        continue
    new_app_lines.append(line)

# Insert imports at the top
imports = """
from utils import send_telegram_message, get_ticker_name, load_watchlists, save_watchlists, ticker_names_cache, watchlists, UNIVERSE_DICT
from data_loader import backtest_symbol, backtest_hybrid_symbol, calculate_hurst, get_hybrid_signal, get_live_signal
"""
# insert after import plotly.graph_objects as go
for i, line in enumerate(new_app_lines):
    if line.startswith("import plotly.graph_objects as go"):
        new_app_lines.insert(i+1, imports)
        break

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(new_app_lines)
