import yfinance as yf
import pandas as pd
import numpy as np

def calculate_hurst(series, window=100):
    """허스트 지수 계산 (최근 window 기간 기준)"""
    def get_hurst(s):
        lags = range(2, 20)
        tau = [np.sqrt(np.std(np.subtract(s[lag:], s[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0
    
    return series.rolling(window).apply(get_hurst)

def run_hybrid_backtest(ticker, initial_capital=10000000, fee=0.0025):
    print(f"🚀 [{ticker}] 하이브리드 전략 백테스트 시작...")
    
    # 1. 데이터 수집 및 지표 계산
    df = yf.download(ticker, period="10y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df['MA20'] = df['Close'].rolling(20).mean()
    df['STD20'] = df['Close'].rolling(20).std()
    df['Z'] = (df['Close'] - df['MA20']) / df['STD20']
    
    # 허스트 지수 계산 (상태 판별기)
    df['Hurst'] = calculate_hurst(df['Close'], window=100)
    df.dropna(inplace=True)

    # 2. 백테스트 변수
    capital = initial_capital
    position = 0
    buy_price = 0
    
    print(f"💰 시작 자산: {capital:,.0f}원")

    # 3. 시뮬레이션
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        price = row['Close']
        h = row['Hurst']
        z = row['Z']

        # [매수 로직]
        if position == 0:
            # 국면 1: 평균회귀 (H < 0.45) -> 과매도 시 매수
            if h < 0.45 and z <= -2.0:
                mode = "Mean Reversion"
            # 국면 2: 추세추종 (H > 0.55) -> 이평선 돌파 시 매수
            elif h > 0.55 and price > row['MA20'] and prev_row['Close'] <= prev_row['MA20']:
                mode = "Trend Following"
            else:
                continue
            
            position = int(capital // (price * (1 + fee)))
            capital -= position * price * (1 + fee)
            buy_price = price
            print(f"🛒 [{mode}] 매수: {df.index[i].date()} | {price:,.0f}원")

        # [매도 로직]
        elif position > 0:
            # 평균회귀로 샀다면 평균 복귀 시 매도, 추세로 샀다면 이평선 이탈 시 매도
            if (h < 0.45 and z >= 0) or (h > 0.55 and price < row['MA20']):
                capital += position * price * (1 - fee)
                profit = ((price * (1 - fee) - buy_price * (1 + fee)) / (buy_price * (1 + fee))) * 100
                print(f"💰 매도: {df.index[i].date()} | {price:,.0f}원 | 수익률: {profit:.2f}%")
                position = 0

    # 최종 평가
    if position > 0: capital += position * df.iloc[-1]['Close'] * (1 - fee)
    
    print("-" * 40)
    print(f"🎯 최종 자산: {capital:,.0f}원")
    print(f"📈 총 수익률: {((capital-initial_capital)/initial_capital)*100:.2f}%")

# HMM으로 테스트
run_hybrid_backtest("404120.KS")