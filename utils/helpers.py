import requests
import json
import os
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

load_dotenv(override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

UNIVERSE_DICT = {
    "SPY": "S&P 500 ETF", "QQQ": "NASDAQ 100 ETF", "DIA": "Dow Jones ETF", "IWM": "Russell 2000 ETF", 
    "GLD": "Gold ETF", "SLV": "Silver ETF", "TLT": "US Treasuries", "USO": "US Oil Fund", 
    "UNG": "US Natural Gas", "UUP": "US Dollar Index",
    "KO": "Coca-Cola", "PEP": "PepsiCo", "PG": "Procter & Gamble", "JNJ": "Johnson & Johnson", 
    "MCD": "McDonald's", "WMT": "Walmart", "COST": "Costco", "TGT": "Target", "PM": "Philip Morris", "CL": "Colgate",
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta", 
    "NVDA": "Nvidia", "TSLA": "Tesla", "AVGO": "Broadcom", "ADBE": "Adobe", "CRM": "Salesforce",
    "JPM": "JPMorgan", "BAC": "Bank of America", "WFC": "Wells Fargo", "V": "Visa", "MA": "Mastercard", 
    "AXP": "American Express", "GS": "Goldman Sachs", "MS": "Morgan Stanley", "BLK": "BlackRock", "C": "Citigroup",
    "XOM": "Exxon Mobil", "CVX": "Chevron", "SHW": "Sherwin-Williams", "HD": "Home Depot", "UNH": "UnitedHealth", 
    "LLY": "Eli Lilly", "MRK": "Merck", "ABBV": "AbbVie", "PFE": "Pfizer", "TMO": "Thermo Fisher"
}

TICKER_NAMES_FILE = "ticker_names.json"

def load_ticker_names():
    if os.path.exists(TICKER_NAMES_FILE):
        try:
            with open(TICKER_NAMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_ticker_names(data):
    with open(TICKER_NAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

ticker_names_cache = load_ticker_names()

def get_ticker_name(ticker):
    if ticker in UNIVERSE_DICT:
        return UNIVERSE_DICT[ticker]
    if ticker in ticker_names_cache:
        return ticker_names_cache[ticker]
    try:
        t_info = yf.Ticker(ticker).info
        name = t_info.get("shortName") or t_info.get("longName") or "알 수 없음"
        ticker_names_cache[ticker] = name
        save_ticker_names(ticker_names_cache)
        return name
    except:
        return "알 수 없음"

WATCHLIST_FILE = "watchlists.json"

def load_watchlists():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"내 관심그룹": ["AAPL", "TSLA", "QQQ"]}

def save_watchlists(data):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        st.error("텔레그램 토큰 또는 CHAT_ID가 설정되지 않았습니다 (.env 확인 필요)")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        return True
    except Exception as e:
        error_msg = f"텔레그램 전송 실패: {e}"
        if 'res' in locals() and res is not None:
            error_msg += f"\n상세: {res.text}"
        st.error(error_msg)
        return False
