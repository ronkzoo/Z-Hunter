import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt

def run_z_hunter_backtest(ticker, name, initial_capital=10000000):
    print(f"\n🔄 [{name}] 과거 10년 데이터 백테스트 시작 (초기 자본: {initial_capital:,}원)")
    
    # 1. 데이터 준비 (최근 10년)
    df = yf.download(ticker, period="10y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df[['High', 'Low', 'Close']].copy()
    # 2. 지표 계산
    df['MA'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
    
    adx_df = df.ta.adx(length=14)
    df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0
    df.dropna(inplace=True)

    # 3. 백테스트 로직 변수
    capital = initial_capital
    position = 0      # 보유 주식 수
    buy_price = 0
    trade_history = []

    # 4. 시뮬레이션 실행 (한 줄씩 과거로 돌아가서 거래)
    for index, row in df.iterrows():
        z = row['Z-Score']
        adx = row['ADX']
        price = row['Close']

        # [매수 조건]: 포지션이 없고, Z <= -2 이고, ADX < 25 일 때
        if position == 0 and z <= -2 and adx < 25:
            position = capital // price  # 살 수 있는 만큼 전량 매수
            buy_price = price
            capital -= position * price  # 남은 현금
            trade_history.append((index, 'BUY', price))
            print(f"🛒 매수: {index.date()} | 가격: {price:,.0f}원 | 수량: {position}주")

        # [매도 조건]: 포지션을 보유 중이고, 가격이 평균(Z >= 0)으로 회귀했을 때
        elif position > 0 and z >= 0:
            capital += position * price  # 전량 매도 후 현금 확보
            profit_rate = ((price - buy_price) / buy_price) * 100
            trade_history.append((index, 'SELL', price))
            print(f"💰 매도: {index.date()} | 가격: {price:,.0f}원 | 수익률: {profit_rate:.2f}% | 총자산: {capital:,.0f}원")
            position = 0 # 포지션 초기화

    # 마지막 날 혹시 주식을 들고 있다면 현재가로 청산(평가액 계산)
    if position > 0:
        capital += position * df.iloc[-1]['Close']
        print(f"🏁 마지막 날 강제 청산 진행")

    # 5. 최종 결과 출력
    total_return = ((capital - initial_capital) / initial_capital) * 100
    print("-" * 50)
    print(f"🎯 최종 자산: {capital:,.0f}원")
    print(f"📈 누적 수익률: {total_return:.2f}%")
    print(f"💸 순수익금: {(capital - initial_capital):,.0f}원")
    print("-" * 50)

# 실행: 설정된 종목들, 1천만 원으로 백테스트
if __name__ == "__main__":
    targets = [
        ("SPY", "S&P 500 ETF"),
        ("QQQ", "NASDAQ 100 ETF"),
        ("GLD", "Gold ETF (금)"),
        ("KO", "Coca-Cola (코카콜라)"),
        ("TLT", "미국 장기채 ETF")
    ]
    for ticker, name in targets:
        run_z_hunter_backtest(ticker, name, initial_capital=10000000)