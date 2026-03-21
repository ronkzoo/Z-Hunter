with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

start_str = '@st.cache_data(ttl=3600, show_spinner=False)\ndef backtest_hybrid_symbol('
end_str = '# --- 관심그룹 관리 로직 ---'

start_idx = text.find(start_str)
end_idx = text.find(end_str, start_idx)

new_func = """@st.cache_data(ttl=3600, show_spinner=False)
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
                "매수일자": "-", # 포지션 진입 시 Date는 스크립트 특성상 현재 미기록, 매도일자로 대체
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

"""

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text[:start_idx] + new_func + text[end_idx:])
