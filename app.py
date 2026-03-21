import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import warnings
import time
import json
import os
import requests
import FinanceDataReader as fdr
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv(override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

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

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Z-Hunter Web Scanner", page_icon="🎯", layout="wide")

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

def backtest_symbol(ticker, period="10y", initial_capital=10000000, stop_loss_type="ADX 25 돌파 시 (추세 강제청산)"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if df.empty:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['High', 'Low', 'Close']].copy()
        
        # 지표 산출
        df['MA'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
        
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0
        df.dropna(inplace=True)

        capital = initial_capital
        position = 0
        buy_price = 0
        buy_date = None
        win_trades = 0
        total_trades = 0
        trade_logs = []

        for index, row in df.iterrows():
            z = row['Z-Score']
            adx = row['ADX']
            price = row['Close']
            current_date = index.strftime('%Y-%m-%d') if pd.notnull(index) else str(index)

            if position == 0 and z <= -2 and adx < 25:
                position = capital // price
                buy_price = price
                buy_date = current_date
                capital -= position * price
            
            elif position > 0:
                sell_condition = False
                sell_type = ""
                profit_pct = ((price - buy_price) / buy_price) * 100
                
                # 매도 조건 1: Z-Score 0 도달 (평균 회귀 목표 달성)
                if z >= 0:
                    sell_condition = True
                    sell_type = "🎯 목표달성"
                else:
                    # 매도 조건 2: 선택된 손절/강제청산 기준 적용
                    if stop_loss_type == "ADX 25 돌파 시 (추세 강제청산)" and adx >= 25:
                        sell_condition = True
                        sell_type = "📉 추세청산 (ADX 25+)"
                    elif stop_loss_type == "-3% 수익률 손절" and profit_pct <= -3:
                        sell_condition = True
                        sell_type = "📉 손절 (-3%)"
                    elif stop_loss_type == "-5% 수익률 손절" and profit_pct <= -5:
                        sell_condition = True
                        sell_type = "📉 손절 (-5%)"
                    elif stop_loss_type == "-10% 수익률 손절" and profit_pct <= -10:
                        sell_condition = True
                        sell_type = "📉 손절 (-10%)"
                    elif stop_loss_type == "20일선 하향 돌파 시" and price < row['MA']:
                        sell_condition = True
                        sell_type = "📉 추세이탈 (20일선 미만)"

                if sell_condition:
                    capital += position * price
                    if price > buy_price:
                        win_trades += 1
                    total_trades += 1
                    
                    trade_logs.append({
                        "매수일자": buy_date,
                        "매도일자": current_date,
                        "매도사유": sell_type,
                        "매수가": f"{round(buy_price, 2):,}",
                        "매도가": f"{round(price, 2):,}",
                        "수익률(%)": f"{round(profit_pct, 2):.2f}",
                        "거래금액": f"{int(position * price):,}"
                    })
                    position = 0

        # 백테스트 기간 종료 시점에 보유 중인 종목이 있다면 현재가로 평가산산
        if position > 0:
            last_price = df.iloc[-1]['Close']
            last_date = df.index[-1].strftime('%Y-%m-%d')
            capital += position * last_price
            profit_pct = ((last_price - buy_price) / buy_price) * 100
            if last_price > buy_price:
                win_trades += 1
            total_trades += 1
            trade_logs.append({
                "매수일자": buy_date,
                "매도일자": last_date,
                "매도사유": "보유중 (마지막 종가 평가)",
                "매수가": f"{round(buy_price, 2):,}",
                "매도가": f"{round(last_price, 2):,}",
                "수익률(%)": f"{round(profit_pct, 2):.2f}",
                "거래금액": f"{int(position * last_price):,}"
            })
            position = 0

        total_return = ((capital - initial_capital) / initial_capital) * 100
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "티커표시": f"{ticker} ({UNIVERSE_DICT.get(ticker, '')})",
            "수익률(%)": f"{round(total_return, 2):.2f}",
            "총수익금(원)": f"{int(capital - initial_capital):,}",
            "최종잔고(원)": f"{int(capital):,}",
            "승률(%)": f"{round(win_rate, 2):.2f}",
            "거래횟수": total_trades,
            "상세내역": trade_logs,
            "chart_data": df[['Close']].reset_index(),
        }
    except Exception as e:
        return None

# --- 관심그룹 관리 로직 ---
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

watchlists = load_watchlists()

def get_live_signal(ticker, stop_loss_type="ADX 25 돌파 시 (추세 강제청산)"):
    try:
        # 최근 6개월 데이터만 가져와서 지표 계산
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['High', 'Low', 'Close']].copy()
        
        df['MA'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
        
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0
        df.dropna(inplace=True)
        
        if df.empty:
            return None
            
        last_date = df.index[-1].strftime('%Y-%m-%d') if pd.notnull(df.index[-1]) else str(df.index[-1])
        last_row = df.iloc[-1]
        
        z = last_row['Z-Score']
        adx = last_row['ADX']
        price = last_row['Close']
        ma = last_row['MA']
        
        # 전략 조건
        if z <= -2 and adx < 25:
            signal = "🚨 매수 시그널"
        elif z >= 0:
            signal = "🟢 매도 시그널 (목표달성)"
        else:
            if stop_loss_type == "ADX 25 돌파 시 (추세 강제청산)" and adx >= 25:
                signal = "⚠️ 매도 시그널 (추세강화 강제청산)"
            elif stop_loss_type == "20일선 하향 돌파 시" and price < ma:
                signal = "⚠️ 매도 시그널 (20일선 이탈 손절)"
            else:
                signal = "➖ 관망"
            
        # 예상 수익률: 현재가 매수 시 목표가(20일선)까지의 도달 수익률
        expected_profit = ((ma - price) / price) * 100 if price > 0 else 0
            
        return {
            "티커": ticker,
            "종목명": UNIVERSE_DICT.get(ticker, ticker),
            "날짜": last_date,
            "현재가": f"{round(price, 2):,}",
            "20일선(MA)": f"{round(ma, 2):,}",
            "예상수익률(%)": round(expected_profit, 2),
            "Z-Score": round(z, 2),
            "ADX": round(adx, 2),
            "현재 상태": signal
        }
    except:
        return None

# --- UI 세팅 ---
st.title("🎯 Z-Hunter Web Scanner")
st.markdown("Z-Score와 ADX를 활용한 **평균회귀 전략(Mean Reversion)** 최적화 종목 검색기입니다.")

tab_scan, tab_live, tab_watch = st.tabs(["🔍 백테스트 스캐너", "📡 실시간 매수/매도 포착", "⭐ 관심그룹 관리"])

with tab_live:
    st.header("📡 실시간 매수/매도 시그널 포착")
    st.markdown("설정된 전략(**Z-Score <= -2 & ADX < 25**)을 만족하여 **오늘 당장 매수**하거나 **매도**해야 할 종목을 찾아줍니다.")
    
    live_target = st.selectbox("탐색 대상 선택", ["기본 유니버스 (50종목)"] + list(watchlists.keys()), key="live_target_box")
    live_stop_loss = st.selectbox(
        "종목 매도/손절 기준", 
        ["ADX 25 돌파 시 (추세 강제청산)", "20일선 하향 돌파 시", "손절/강제청산 없음"],
        key="live_stop_loss_box",
        help="수익률(-5%, -10%) 손절은 개인 매수 단가가 필요하므로 실시간 스캐너에서는 기술적 지표 기준만 제공됩니다."
    )
    
    if st.button("🚀 실시간 스캔 시작", type="primary", key="live_btn"):
        st.markdown(f"### 🔍 실시간 데이터를 불러오는 중... (청산 기준: `{live_stop_loss}`)")
        progress_bar_live = st.progress(0)
        status_text_live = st.empty()
        
        if live_target == "기본 유니버스 (50종목)":
            live_tickers = list(UNIVERSE_DICT.keys())
        else:
            live_tickers = watchlists[live_target]
            
        total_live = len(live_tickers)
        if total_live == 0:
            st.warning("선택한 그룹에 등록된 종목이 없습니다.")
            st.stop()
            
        live_results = []
        for i, t in enumerate(live_tickers):
            status_text_live.text(f"분석 중: {t} ({i+1}/{total_live})")
            res = get_live_signal(t, stop_loss_type=live_stop_loss)
            if res:
                live_results.append(res)
            progress_bar_live.progress((i + 1) / total_live)
            
        status_text_live.text("✅ 실시간 스캔 완료!")
        
        if live_results:
            df_live = pd.DataFrame(live_results)
            # 매수 시그널 먼저, 그다음 매도 시그널, 그 다음 관망 순으로 정렬
            def sort_signal(x):
                if '🚨 매수 시그널' in x: return 0
                elif '🟢 매도 시그널' in x: return 1
                elif '⚠️ 매도 시그널' in x: return 2
                else: return 3
            
            df_live['sort_key'] = df_live['현재 상태'].apply(sort_signal)
            df_live = df_live.sort_values('sort_key').drop('sort_key', axis=1).reset_index(drop=True)
            df_live.index += 1
            
            # 하이라이트 함수 적용
            def highlight_row(row):
                if '🚨 매수 시그널' in row['현재 상태']:
                    return ['background-color: rgba(255, 99, 71, 0.4)'] * len(row)
                elif '🟢 매도 시그널' in row['현재 상태']:
                    return ['background-color: rgba(144, 238, 144, 0.4)'] * len(row)
                elif '⚠️ 매도 시그널' in row['현재 상태']:
                    return ['background-color: rgba(255, 165, 0, 0.4)'] * len(row)
                else:
                    return [''] * len(row)
                    
            st.session_state['live_results'] = df_live
            st.dataframe(df_live.style.apply(highlight_row, axis=1), use_container_width=True)
        else:
            st.warning("데이터를 불러올 수 없습니다.")

    if 'live_results' in st.session_state and not st.session_state['live_results'].empty:
        st.markdown("---")
        if st.button("✈️ 텔레그램으로 결과 전송하기"):
            df_curr = st.session_state['live_results']
            buy_list = df_curr[df_curr['현재 상태'] == '🚨 매수 시그널']
            sell_list_norm = df_curr[df_curr['현재 상태'] == '🟢 매도 시그널 (목표달성)']
            sell_list_force = df_curr[df_curr['현재 상태'].str.startswith('⚠️ 매도 시그널')]
            
            msg = "⚡ Z-Hunter 실시간 스캔 결과 ⚡\n\n"
            if not buy_list.empty:
                msg += "🚨 [매수 시그널] (Z-Score<=-2 & ADX<25)\n"
                for _, row in buy_list.iterrows():
                    msg += f"• {row['종목명']} ({row['티커']})\n  - 현재가: {row['현재가']}\n  - 목표매도가(20일선): {row['20일선(MA)']}\n  - 예상수익률: {row['예상수익률(%)']}%\n"
                msg += "\n"
                
            if not sell_list_norm.empty:
                msg += "🟢 [매도 시그널 - 정상 익절] (Z-Score>=0)\n"
                for _, row in sell_list_norm.iterrows():
                    msg += f"• {row['종목명']} ({row['티커']})\n  - 현재가: {row['현재가']}\n"
                msg += "\n"
                
            if not sell_list_force.empty:
                msg += "⚠️ [매도 시그널 - 강제청산/손절]\n"
                for _, row in sell_list_force.iterrows():
                    reason = row['현재 상태'].replace('⚠️ 매도 시그널 ', '')
                    msg += f"• {row['종목명']} ({row['티커']})\n  - 현재가: {row['현재가']}\n  - 사유: {reason}\n"
                msg += "\n"
                
            if buy_list.empty and sell_list_norm.empty and sell_list_force.empty:
                msg += "현재 포착된 매수/매도 시그널이 없습니다."
                
            if send_telegram_message(msg):
                st.success("✅ 텔레그램으로 결과 전송을 완료했습니다!")

with tab_watch:
    st.header("⭐ 관심그룹 관리")
    col1, col2 = st.columns(2)
    with col1:
        new_group = st.text_input("새로운 관심그룹 이름")
        if st.button("그룹 추가"):
            if new_group and new_group not in watchlists:
                watchlists[new_group] = []
                save_watchlists(watchlists)
                st.success(f"'{new_group}' 그룹 추가 완료!")
                st.rerun()

    with col2:
        if watchlists:
            del_group = st.selectbox("삭제할 그룹 선택", list(watchlists.keys()))
            if st.button("그룹 삭제"):
                if del_group in watchlists:
                    del watchlists[del_group]
                    save_watchlists(watchlists)
                    st.success(f"'{del_group}' 그룹 삭제 완료!")
                    st.rerun()
                    
    st.divider()
    
    if watchlists:
        mng_group = st.selectbox("관리할 관심그룹 선택", list(watchlists.keys()))
        col_add, col_list = st.columns([1.5, 1.5])  # 좌측 검색 영역 공간 확보를 위해 비율을 조정
        
        with col_add:
            st.markdown("**🔍 새로운 종목 검색 및 추가 (국내/해외 모두 지원)**")
            search_query = st.text_input("회사명이나 티커를 입력하세요 (예: 삼성전자, Apple, 005930, TSLA)")
            
            if search_query:
                # 1. 국내 주식 및 ETF 검색 (FinanceDataReader 활용)
                try:
                    df_krx = fdr.StockListing("KRX")
                    df_etf = fdr.StockListing("ETF/KR")
                    
                    # 주식 검색어 매칭
                    mask_krx = df_krx['Name'].str.contains(search_query, case=False, na=False) | df_krx['Code'].str.contains(search_query, case=False, na=False)
                    krx_matches = df_krx[mask_krx].head(10)
                    
                    # ETF 검색어 매칭
                    mask_etf = df_etf['Name'].str.contains(search_query, case=False, na=False) | df_etf['Symbol'].str.contains(search_query, case=False, na=False)
                    etf_matches = df_etf[mask_etf].head(10)
                    
                    def get_suffix(market):
                        if market == 'KOSPI': return '.KS'
                        elif 'KOSDAQ' in str(market): return '.KQ'
                        return '.KS'
                        
                    suggestions = {}
                    # 주식 추가
                    for _, row in krx_matches.iterrows():
                        code_yf = row['Code'] + get_suffix(row['Market'])
                        suggestions[code_yf] = f"[국내주식] {row['Name']}"
                        
                    # ETF 추가 (.KS가 기본)
                    for _, row in etf_matches.iterrows():
                        code_yf = row['Symbol'] + '.KS'
                        suggestions[code_yf] = f"[국내ETF] {row['Name']}"
                except:
                    suggestions = {}

                # 2. 해외 주식 검색 (Yahoo Finance API)
                url = f"https://query2.finance.yahoo.com/v1/finance/search?q={search_query}"
                headers = {"User-Agent": "Mozilla/5.0"}
                try:
                    req = requests.get(url, headers=headers, timeout=3)
                    data = req.json()
                    quotes = data.get("quotes", [])
                    for q in quotes:
                        if q.get("quoteType") in ["EQUITY", "ETF"]:
                            suggestions[q["symbol"]] = q.get("shortname", q.get("longname", ""))
                except:
                    pass

                if suggestions:
                    options = [f"{sym} - {name}" for sym, name in suggestions.items()]
                    selected_option = st.selectbox("검색 결과 (선택)", options)
                    
                    if st.button("관심그룹에 추가", type="primary"):
                        new_ticker = selected_option.split(" - ")[0]
                        if new_ticker not in watchlists[mng_group]:
                            watchlists[mng_group].append(new_ticker)
                            save_watchlists(watchlists)
                            
                            # 이름을 UNIVERSE_DICT에 추가 (세션 내 표시용)
                            UNIVERSE_DICT[new_ticker] = suggestions[new_ticker]
                            
                            st.success(f"'{new_ticker}' ({suggestions[new_ticker]}) 추가 완료!")
                            st.rerun()
                        else:
                            st.warning("이미 등록된 종목입니다.")
                else:
                    st.warning("검색 결과가 없습니다.")
                    manual_ticker = st.text_input("직접 추가할 티커명 입력").upper().strip()
                    if st.button("직접 등록") and manual_ticker:
                        if manual_ticker not in watchlists[mng_group]:
                            watchlists[mng_group].append(manual_ticker)
                            save_watchlists(watchlists)
                            st.success(f"'{manual_ticker}' 추가 완료!")
                            st.rerun()
                        else:
                            st.warning("이미 등록된 종목입니다.")
            else:
                st.info("검색어를 입력하면 자동 완성이 제공됩니다.")
                    
        with col_list:
            st.write(f"**[{mng_group}] 등록된 종목 ({len(watchlists[mng_group])}개)**")
            if not watchlists[mng_group]:
                st.info("등록된 종목이 없습니다.")
            else:
                for t in watchlists[mng_group]:
                    c_name, c_btn = st.columns([4, 1])
                    c_name.write(f"- {t} ({UNIVERSE_DICT.get(t, '사용자 추가 종목')})")
                    if c_btn.button("삭제", key=f"del_{mng_group}_{t}"):
                        watchlists[mng_group].remove(t)
                        save_watchlists(watchlists)
                        st.rerun()

with tab_scan:
    st.sidebar.header("⚙️ 스캐너 설정")
    scan_target = st.sidebar.selectbox("스캔 대상 선택", ["기본 유니버스 (50종목)"] + list(watchlists.keys()))
    initial_capital = st.sidebar.number_input("초기 투자금 (원)", min_value=100000, value=10000000, step=1000000, format="%d")
    period = st.sidebar.selectbox("테스트할 기간 선택", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y"], index=4) # 기본 3y
    min_trades = st.sidebar.number_input("최소 거래 횟수 기준", min_value=1, value=1)
    stop_loss_type = st.sidebar.selectbox(
        "손절 기준 (청산 전략)", 
        ["ADX 25 돌파 시 (추세 강제청산)", "-3% 수익률 손절", "-5% 수익률 손절", "-10% 수익률 손절", "20일선 하향 돌파 시", "손절/강제청산 없음"]
    )

    if st.sidebar.button("🚀 스캔 시작 (Run Scanner)", type="primary"):
        st.markdown(f"### 🔍 {period} 데이터 스캔 진행 중... (투자금: {initial_capital:,}원)")
        st.markdown(f"**적용된 청산 전략:** `{stop_loss_type}`")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        if scan_target == "기본 유니버스 (50종목)":
            tickers = list(UNIVERSE_DICT.keys())
        else:
            tickers = watchlists[scan_target]
            
        total_tickers = len(tickers)
        
        if total_tickers == 0:
            st.warning("선택한 그룹에 등록된 종목이 없습니다.")
            st.stop()
        
        for i, ticker in enumerate(tickers):
            status_text.text(f"스캔 중: {ticker} ({i+1}/{total_tickers})")
            
            res = backtest_symbol(ticker, period=period, initial_capital=initial_capital, stop_loss_type=stop_loss_type)
            if res and res["거래횟수"] >= min_trades:
                results.append(res)
                
            progress_bar.progress((i + 1) / total_tickers)
            
        status_text.text("✅ 스캔 완료!")
        
        if results:
            st.session_state["scan_results"] = results
            st.session_state["scan_meta"] = {"period": period, "capital": initial_capital, "stop_loss": stop_loss_type}
        else:
            st.session_state["scan_results"] = []
            st.warning("조건(최소 거래횟수 등)을 만족하는 종목이 없습니다. 기간이나 조건을 완화해 보세요.")

    if "scan_results" in st.session_state and st.session_state["scan_results"]:
        results = st.session_state["scan_results"]
        meta = st.session_state.get("scan_meta", {})
        
        st.markdown("---")
        st.markdown(f"### 📊 {meta.get('period', period)} 백테스트 결과 (투자금: {meta.get('capital', initial_capital):,}원)")
        st.markdown(f"**적용된 청산 전략:** `{meta.get('stop_loss', stop_loss_type)}`")
        
        # 데이터프레임 변환 및 정렬
        df_results = pd.DataFrame(results)
        df_summary = df_results.drop(columns=["상세내역", "거래횟수", "chart_data"], errors="ignore").copy()
        df_summary["거래횟수"] = df_results["거래횟수"]
        
        # 수익률과 승률을 숫자로 변환하여 정렬 (문자열 정렬 오류 방지)
        df_summary["수익률(%)"] = df_summary["수익률(%)"].astype(float)
        df_summary["승률(%)"] = df_summary["승률(%)"].astype(float)
        
        df_summary = df_summary.sort_values(by=["수익률(%)", "승률(%)"], ascending=[False, False]).reset_index(drop=True)
        # 인덱스 1부터 시작
        df_summary.index += 1
        # 인덱스를 "순위"라는 컬럼으로 명시적으로 변환하여 보이게 만들기
        df_summary.insert(0, "순위", df_summary.index)
        
        st.subheader("🏆 백테스트 요약 결과 Top Rank (클릭하여 상세 내역 확인)")
        
        # 데이터프레임 예쁘게 출력 및 선택 기능 추가
        st_styled = df_summary.style.format({
            "수익률(%)": "{:.2f}",
            "승률(%)": "{:.2f}"
        }).background_gradient(cmap='Greens', subset=['수익률(%)', '승률(%)']).hide(axis="index") # 기본 인덱스 숨기고 커스텀 순위 컬럼 사용
        
        event = st.dataframe(
            st_styled, 
            use_container_width=True, 
            on_select="rerun", 
            selection_mode=["single-cell"], # 체크박스(single-row) 대신 셀 클릭 이벤트 사용
            hide_index=True # Streamlit 데이터프레임 설정에서도 인덱스 렌더링 끄기 (체크박스 공간만 차지하는 빈 컬럼 방지)
        )

        selected_rows = event.selection.get("rows", [])
        selected_cells = event.selection.get("cells", [])
        selected_idx = None
        
        if selected_rows:
            selected_idx = selected_rows[0]
        elif selected_cells:
            # Streamlit 반환 형태(Tuple 또는 Dict)에 맞게 안전하게 행(Row) 인덱스 추출
            first_cell = selected_cells[0]
            selected_idx = first_cell[0] if isinstance(first_cell, tuple) else first_cell.get("row")

        if selected_idx is not None:
            # 선택된 행의 인덱스를 가져와 원래 데이터 정보 찾기
            selected_ticker_name = df_summary.iloc[selected_idx]["티커표시"]
            
            # results에서 해당 종목 데이터 찾기
            selected_res = next((item for item in results if item["티커표시"] == selected_ticker_name), None)
            
            if selected_res:
                st.markdown("---")
                st.subheader(f"📜 {selected_ticker_name} 상세 거래 내역")
                
                trade_logs = selected_res["상세내역"]
                chart_df = selected_res.get("chart_data")
                
                if trade_logs:
                    df_logs = pd.DataFrame(trade_logs)
                    df_logs.index += 1
                    
                    # Plotly 차트 그리기
                    if chart_df is not None and not chart_df.empty:
                        fig = go.Figure()
                        # 전체 종가 라인 차트
                        fig.add_trace(go.Scatter(
                            x=chart_df['Date'], y=chart_df['Close'], 
                            mode='lines', name='Price', line=dict(color='gray', width=1)
                        ))
                        
                        # 매수/매도 포인트 추출
                        buy_dates, buy_prices = [], []
                        sell_dates, sell_prices = [], []
                        for log in trade_logs:
                            buy_dates.append(log['매수일자'])
                            buy_prices.append(float(str(log['매수가']).replace(',', '')))
                            sell_dates.append(log['매도일자'])
                            sell_prices.append(float(str(log['매도가']).replace(',', '')))
                            
                        # 매수(Buy) 점 찍기 (파란색 세모 위로)
                        if buy_dates:
                            fig.add_trace(go.Scatter(
                                x=buy_dates, y=buy_prices, mode='markers', name='Buy',
                                marker=dict(symbol='triangle-up', size=12, color='blue', line=dict(width=1, color='DarkSlateGrey'))
                            ))
                            
                        # 매도(Sell) 점 찍기 (빨간색 세모 아래로)
                        if sell_dates:
                            fig.add_trace(go.Scatter(
                                x=sell_dates, y=sell_prices, mode='markers', name='Sell',
                                marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='DarkSlateGrey'))
                            ))
                            
                        fig.update_layout(
                            title=f"{selected_ticker_name} Backtest Trade Points",
                            xaxis_title="Date",
                            yaxis_title="Price",
                            xaxis=dict(
                                tickformat="%Y-%m-%d",
                                hoverformat="%Y-%m-%d"
                            ),
                            height=400,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(df_logs, use_container_width=True)
                else:
                    st.write("상세 거래 내역이 없습니다.")
        else:
            st.info("👆 위 표에서 종목의 행을 클릭하시면 상세 거래 내역과 차트가 이곳에 표시됩니다.")