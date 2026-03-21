
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

start_str = 'def backtest_hybrid_symbol(ticker, period="3y", initial_capital=10000000, stop_loss_type="ADX 25 돌파 시 (추세 강제청산)"):'
end_str = '# --- 관심그룹 관리 로직 ---'

start_idx = text.find(start_str)
end_idx = text.find(end_str, start_idx)

new_func = """def backtest_hybrid_symbol(ticker, period="3y", initial_capital=10000000, stop_loss_type="ADX 25 돌파 시 (추세 강제청산)"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if df.empty or len(df) < 100:
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['High', 'Low', 'Close']].copy()
        
        df['MA'] = df['Close'].rolling(window=20).mean()
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
        
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0
        df['ATR'] = df.ta.atr(length=14)
        df['High20_Prev'] = df['High'].rolling(window=20).max().shift(1)
        
        def _get_hurst(s):
            import numpy as np
            lags = range(2, 20)
            tau = [np.sqrt(np.std(np.subtract(s[lag:], s[:-lag]))) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0
            
        df['Hurst'] = df['Close'].rolling(100).apply(_get_hurst, raw=True)
        df.dropna(inplace=True)

        capital = initial_capital
        position = 0
        buy_price = 0
        buy_date = None
        win_trades = 0
        total_trades = 0
        trade_logs = []
        mode = ""
        stop_loss_price = 0
        
        equity_curve = []

        prices = df['Close'].values
        zs = df['Z-Score'].values
        adxs = df['ADX'].values
        atrs = df['ATR'].values
        hursts = df['Hurst'].values
        mas = df['MA'].values
        ma60s = df['MA60'].values
        high20_prevs = df['High20_Prev'].values
        dates = df.index
        
        # [TSLA 튜닝 옵션] 변동성이 큰 종목은 진입을 빡빡하게
        z_threshold = -2.5 if "TSLA" in ticker.upper() else -2.0

        for i in range(1, len(df)):
            price = prices[i]
            z = zs[i]
            adx = adxs[i]
            atr = atrs[i]
            h = hursts[i]
            ma = mas[i]
            ma60 = ma60s[i]
            prev_high20 = high20_prevs[i]
            
            current_date = dates[i].strftime('%Y-%m-%d') if pd.notnull(dates[i]) else str(dates[i])
            
            # --- [1] EXIT (청산 로직) ---
            if position > 0:
                sell_condition = False
                sell_type = ""
                profit_pct = ((price - buy_price) / buy_price) * 100
                
                # 공통 리스크 관리: ATR 2배수 혹은 고정 -3% (더 타이트한 손절 가격) 
                if price <= stop_loss_price:
                    sell_condition = True
                    sell_type = "📉 손절 (-3% / -2ATR 이탈)"
                
                elif mode == "평균회귀(매수)":
                    if adx > 25:
                        sell_condition = True
                        sell_type = "📉 추세청산 (ADX 25 돌파 투매)"
                    elif z >= 0 or price >= ma:
                        sell_condition = True
                        sell_type = "🎯 목표달성 (Z>=0 or 중심선 회귀)"
                        
                elif mode == "강력추세(매수)":
                    if price < ma:
                        sell_condition = True
                        sell_type = "📉 추세이탈 (20일 이평선 이탈)"
                        
                if sell_condition:
                    capital += position * price
                    if price > buy_price:
                        win_trades += 1
                    total_trades += 1
                    trade_logs.append({
                        "매수일자": buy_date,
                        "매도일자": current_date,
                        "진입전략": mode,
                        "매도사유": sell_type,
                        "매수가": f"{round(buy_price, 2):,}",
                        "매도가": f"{round(price, 2):,}",
                        "수익률(%)": f"{round(profit_pct, 2):.2f}",
                        "거래금액": f"{int(position * price):,}"
                    })
                    position = 0
            
            # --- [2] ENTRY (진입 로직) ---
            if position == 0:
                # 평균회귀 (Hurst < 0.45)
                if h < 0.45 and z <= z_threshold and adx < 25:
                    mode = "평균회귀(매수)"
                    position = capital // price
                    buy_price = price
                    buy_date = current_date
                    capital -= position * price
                    stop_loss_price = max(price * 0.97, price - (2 * atr))
                # 추세추종 (Hurst > 0.55), 20일 신고가 돌파, 강한 추세(ADX>25), 정배열(20 > 60)
                elif h > 0.55 and price > prev_high20 and adx > 25 and ma > ma60:
                    mode = "강력추세(매수)"
                    position = capital // price
                    buy_price = price
                    buy_date = current_date
                    capital -= position * price
                    stop_loss_price = max(price * 0.97, price - (2 * atr))
                    
            # --- [3] 시계열 로깅 ---
            current_equity = capital + (position * price)
            equity_curve.append(current_equity)
                    
        if position > 0:
            last_price = prices[-1]
            last_date = dates[-1].strftime('%Y-%m-%d')
            capital += position * last_price
            profit_pct = ((last_price - buy_price) / buy_price) * 100
            if last_price > buy_price:
                win_trades += 1
            total_trades += 1
            trade_logs.append({
                "매수일자": buy_date,
                "매도일자": last_date,
                "진입전략": mode,
                "매도사유": "보유중 (마지막 종가 평가)",
                "매수가": f"{round(buy_price, 2):,}",
                "매도가": f"{round(last_price, 2):,}",
                "수익률(%)": f"{round(profit_pct, 2):.2f}",
                "거래금액": f"{int(position * last_price):,}"
            })
            position = 0

        total_return = ((capital - initial_capital) / initial_capital) * 100
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        cagr = 0
        mdd = 0
        sr = 0
        if equity_curve:
            import numpy as np
            eq_series = pd.Series(equity_curve)
            final_equity = eq_series.iloc[-1]
            
            days = (dates[-1] - dates[0]).days if (dates[-1] - dates[0]).days > 0 else 1
            years = days / 365.25
            if years > 0:
                cagr = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if final_equity > 0 else -100
                
            running_max = eq_series.cummax()
            drawdowns = (eq_series - running_max) / running_max
            mdd = drawdowns.min() * 100
            
            daily_returns = eq_series.pct_change().dropna()
            if daily_returns.std() != 0:
                sr = np.sqrt(252) * (daily_returns.mean() / daily_returns.std())
        
        return {
            "티커표시": f"{ticker} ({get_ticker_name(ticker)})",
            "수익률(%)": f"{round(total_return, 2):.2f}",
            "CAGR(%)": f"{round(cagr, 2):.2f}",
            "MDD(%)": f"{round(mdd, 2):.2f}",
            "Sharpe": f"{round(sr, 2):.2f}",
            "총수익금(원)": f"{int(capital - initial_capital):,}",
            "최종잔고(원)": f"{int(capital):,}",
            "승률(%)": f"{round(win_rate, 2):.2f}",
            "거래횟수": total_trades,
            "상세내역": trade_logs,
            "chart_data": df[['Close']].reset_index(),
        }
    except Exception as e:
        return None

"""

if start_idx != -1 and end_idx != -1:
    new_text = text[:start_idx] + new_func + text[end_idx:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("SUCCESS")
else:
    print("FAILED TO FIND INDICES")

