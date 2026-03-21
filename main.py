import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def analyze_z_score(ticker, name, window=20):
    # 1. 데이터 가져오기 (최근 6개월)
    data = yf.download(ticker, period="6mo", interval="1d")
    df = data[['Close']].copy()

    # 2. 이동평균(μ) 및 표준편차(σ) 계산
    df['MA'] = df['Close'].rolling(window=window).mean()
    df['STD'] = df['Close'].rolling(window=window).std()

    # 3. Z-Score 수식 적용: Z = (X - μ) / σ
    df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']

    print(f"\n--- {name} ({ticker}) 분석 결과 ---")
    print(df.tail(1)[['Close', 'Z-Score']])
    
    # 4. 시각화
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['Z-Score'], label='Z-Score', color='purple')
    plt.axhline(y=2, color='r', linestyle='--', label='Overbought (+2σ)')
    plt.axhline(y=-2, color='g', linestyle='--', label='Oversold (-2σ)')
    plt.axhline(y=0, color='black', linestyle='-')
    plt.title(f'{name} Z-Score Mean Reversion')
    plt.legend()
    plt.show()

# 실행: 유가(WTI)와 HMM 분석
analyze_z_score("CL=F", "WTI Crude Oil")
analyze_z_score("011200.KS", "HMM")