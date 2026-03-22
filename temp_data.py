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
            "티커표시": f"{ticker} ({get_ticker_name(ticker)})",
            "수익률(%)": f"{round(total_return, 2):.2f}",
            "총수익금(원)": f"{int(capital - initial_capital):,}",
            "최종잔고(원)": f"{int(capital):,}",
            "승률(%)": f"{round(win_rate, 2):.2f}",
            "거래횟수": total_trades,
            "상세내역": trade_logs,
            "chart_data": df[['Close']].reset_index(),
        }
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def backtest_hybrid_symbol(ticker, period="3y", initial_capital=10000000, stop_loss_type="듀얼 국면 리스크 모델"):
    try:
        from regime_risk_manager import DualRegimeRiskManager
        import yfinance as yf
        import pandas_ta as ta
        import types
        
        # DualRegimeRiskManager 초기화 (날짜 대신 앱의 period 활용)
        engine = DualRegimeRiskManager(ticker=ticker, period=period, initial_capital=initial_capital)
        engine.tx_cost = 0.00125 # 0.125% per trade
        
        df, metrics = engine.run_backtest()
        
        if df.empty:
            return None
            
        # 기존 Web UI의 trade_logs 양식에 맞춰 매핑
        trade_logs = []
        for log in engine.trade_logs:
            # log format: Date, Regime, Type, Entry Price, Exit Price, Net PnL, Return(%)
            strategy_name = "평균회귀(매수)" if log['Regime'] == 'MR' else "강력추세(매수)"
            trade_logs.append({
                "매수일자": log.get('Entry Date', '-'),
                "매도일자": log['Date'],
                "진입전략": strategy_name,
                "매도사유": log['Type'],
                "매수가": f"{log['Entry Price']:,}",
                "매도가": f"{log['Exit Price']:,}",
                "수익률(%)": f"{log['Return(%)']:.2f}",
                "거래금액": f"{int(log['Exit Price'] * 10):,}" # 임의 기록
            })
            
        # UI Return Format
        return {
            "티커표시": f"{ticker} ({get_ticker_name(ticker)})",
            "수익률(%)": f"{metrics['Total Return(%)']:.2f}",
            "CAGR(%)": f"{metrics['CAGR(%)']:.2f}",
            "MDD(%)": f"{metrics['MDD(%)']:.2f}",
            "Sharpe": f"{metrics['Sharpe Ratio']:.2f}",
            "총수익금(원)": f"{int(initial_capital * (metrics['Total Return(%)']/100)):,}",
            "최종잔고(원)": f"{int(initial_capital * (1 + metrics['Total Return(%)']/100)):,}",
            "승률(%)": f"{metrics['Win Rate(%)']:.2f}",
            "거래횟수": metrics['Total Trades'],
            "상세내역": trade_logs,
            "chart_data": df[['Close']].reset_index(),
        }
    except Exception as e:
        print(f"[{ticker}] Backtest Error: {e}")
        import traceback
        traceback.print_exc()
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

def calculate_hurst(series):
    """시계열의 허스트 지수를 계산합니다. (RS Analysis)"""
    lags = range(2, 20)
    if len(series) < 20 or np.std(series) == 0:
        return 0.5
    try:
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0
    except:
        return 0.5

@st.cache_data(ttl=600, show_spinner=False)
def get_hybrid_signal(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 100:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['High', 'Low', 'Close']].copy()
        
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA20']) / df['STD20']
        df.dropna(inplace=True)
        
        if df.empty:
            return None
            
        hurst_val = calculate_hurst(df['Close'].values[-100:])
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        z_val = round(latest['Z-Score'], 2)
        price = round(latest['Close'], 2)
        ma5 = round(latest['MA5'], 2)
        ma = round(latest['MA20'], 2)
        ma60 = round(latest['MA60'], 2)
        
        prev_ma5 = round(prev['MA5'], 2)
        prev_ma = round(prev['MA20'], 2)
        prev_ma60 = round(prev['MA60'], 2)
        
        h_val = round(hurst_val, 2)
        
        last_date = df.index[-1].strftime('%Y-%m-%d') if pd.notnull(df.index[-1]) else str(df.index[-1])
        
        signal_type = "⏳ 관망"
        msg = "현재 '랜덤 워크' 국면"
        
        if h_val < 0.45:
            if z_val <= -2:
                signal_type = "🎯 평균회귀 사냥(매수)"
                msg = "평균회귀 반등 기대"
            elif z_val >= 2:
                signal_type = "💰 평균회귀 수확(매도)"
                msg = "평균회귀 고점 도달"
        elif h_val > 0.55:
            if ma5 > ma and ma > ma60 and not (prev_ma5 > prev_ma and prev_ma > prev_ma60):
                signal_type = "🌊 강력 추세 탑승(매수)"
                msg = "이동평균선 정배열 진입 감지!"
        
        return {
            "티커": ticker,
            "종목명": get_ticker_name(ticker),
            "날짜": last_date,
            "현황 분류": signal_type,
            "현재가": f"{price:,}",
            "허스트지수(H)": h_val,
            "Z-Score": z_val,
            "상세 메시지": msg
        }
    except:
        return None

@st.cache_data(ttl=600, show_spinner=False)
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
            "종목명": get_ticker_name(ticker),
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

tab_scan, tab_live, tab_hybrid, tab_watch = st.tabs(["🔍 백테스트 스캐너", "📡 실시간 매수/매도 포착", "🧬 국면별 전략 추천", "⭐ 관심그룹 관리"])

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
