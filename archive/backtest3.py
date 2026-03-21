import yfinance as yf
import pandas as pd

def run_universe_z_score_backtest(tickers, start_date="2016-01-01", end_date="2026-03-21"):
    print(f"🚀 {len(tickers)}개 종목 Z-Score 유니버스 백테스트 시작...")
    
    # 1. 50개 종목 데이터 한 번에 다운로드
    data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
    
    results = []
    
    for ticker in tickers:
        try:
            df = pd.DataFrame(data[ticker]).dropna()
            if df.empty: continue
            
            # Z-Score 계산
            df['MA'] = df[ticker].rolling(20).mean()
            df['STD'] = df[ticker].rolling(20).std()
            df['Z'] = (df[ticker] - df['MA']) / df['STD']
            
            # 매수/매도 시그널 (수익률 계산을 위한 Shift)
            df['Signal'] = 0
            df.loc[df['Z'] <= -2, 'Signal'] = 1  # 매수
            df.loc[df['Z'] >= 0, 'Signal'] = -1  # 매도
            
            # 포지션 유지 로직 (간단한 버전)
            df['Position'] = df['Signal'].replace(to_replace=0, method='ffill')
            df['Position'] = df['Position'].apply(lambda x: 1 if x == 1 else 0)
            
            # 다음 날 수익률
            df['Next_Return'] = df[ticker].pct_change().shift(-1)
            df['Strategy_Return'] = df['Position'] * df['Next_Return']
            
            # 누적 수익률 계산
            total_return = (1 + df['Strategy_Return']).prod() - 1
            win_rate = len(df[df['Strategy_Return'] > 0]) / len(df[df['Strategy_Return'] != 0]) if len(df[df['Strategy_Return'] != 0]) > 0 else 0
            
            results.append({
                'Ticker': ticker,
                'Total_Return(%)': round(total_return * 100, 2),
                'Win_Rate(%)': round(win_rate * 100, 2)
            })
        except Exception:
            continue
            
    # 결과 요약
    result_df = pd.DataFrame(results)
    print("\n📊 --- 백테스트 결과 요약 ---")
    print(f"평균 누적 수익률: {result_df['Total_Return(%)'].mean():.2f}%")
    print(f"평균 승률: {result_df['Win_Rate(%)'].mean():.2f}%")
    print(f"수익률 Top 3 종목:\n{result_df.nlargest(3, 'Total_Return(%)')}")
    
    return result_df

# KOSPI 대형주, ETF 등 원하는 50개 티커 리스트를 넣으세요!
universe_tickers = ['005930.KS', '000660.KS', '011200.KS', '035420.KS', '051910.KS'] # 예시 5개
run_universe_z_score_backtest(universe_tickers)