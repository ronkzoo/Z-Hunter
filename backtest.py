import yfinance as yf
import pandas as pd
import pandas_ta as ta

def run_backtest(ticker, name, period="3y", initial_capital=10000000, window=20):
    data = yf.download(ticker, period=period, interval="1d", progress=False)
    if data.empty:
        print(f"❌ {ticker} 데이터를 불러오지 못했습니다.")
        return
        
    df = data[['High', 'Low', 'Close']].copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df['MA'] = df['Close'].rolling(window=window).mean()
    df['STD'] = df['Close'].rolling(window=window).std()
    df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
    
    adx_df = df.ta.adx(length=14)
    if adx_df is not None:
        df['ADX'] = adx_df['ADX_14']
    else:
        df['ADX'] = 0
        
    df.dropna(inplace=True)
    
    capital = initial_capital
    position = None
    entry_price = 0
    trades = 0
    win_trades = 0
    
    for index, row in df.iterrows():
        close = row['Close']
        z_val = row['Z-Score']
        adx_val = row['ADX']
        
        # 포지션이 없을 때 진입 로직
        if position is None:
            # 2. ADX 조건 수정: 완전 횡보장의 휩쏘와 극도로 강한 추세를 모두 배제 (15 < ADX < 35)
            if 15 < adx_val < 35:
                if z_val <= -2:
                    # Long 진입 (과매도)
                    position = 'Long'
                    entry_price = close
                elif z_val >= 2:
                    # Short 진입 (과매수)
                    position = 'Short'
                    entry_price = close
                
        # 포지션이 있을 때 동적 청산 로직 (1. 타이트한 익절/손절 비율 개선)
        elif position == 'Long':
            # 손절: Z-Score -2.5 이하로 타이트하게 설정
            if z_val <= -2.5:
                profit_pct = (close - entry_price) / entry_price
                capital *= (1 + profit_pct)
                trades += 1
                position = None
            # 익절: 중심선(0)을 넘어 Z-Score 0.5 까지 대기 (수익 극대화)
            elif z_val >= 0.5:
                profit_pct = (close - entry_price) / entry_price
                capital *= (1 + profit_pct)
                trades += 1
                if profit_pct > 0: win_trades += 1
                position = None
                
        elif position == 'Short':
            # 손절: Z-Score 2.5 이상으로 타이트하게 설정
            if z_val >= 2.5:
                profit_pct = (entry_price - close) / entry_price
                capital *= (1 + profit_pct)
                trades += 1
                position = None
            # 익절: 중심선(0)을 넘어 Z-Score -0.5 까지 대기 (수익 극대화)
            elif z_val <= -0.5:
                profit_pct = (entry_price - close) / entry_price
                capital *= (1 + profit_pct)
                trades += 1
                if profit_pct > 0: win_trades += 1
                position = None

    # 결과 표기
    win_rate = (win_trades / trades * 100) if trades > 0 else 0
    profit = capital - initial_capital
    profit_pct = (profit / initial_capital) * 100
    
    print(f"📊 [{name}] 백테스트 결과 (기간: {period} 데이터)")
    print(f"  - 총 거래 횟수: {trades} 회")
    print(f"  - 승률: {win_rate:.2f}% ({win_trades}/{trades})")
    print(f"  - 초기 자본금: {initial_capital:,.0f} 원")
    print(f"  - 최종 자본금: {capital:,.0f} 원")
    print(f"  - 총 수익: {profit:,.0f} 원 ({profit_pct:.2f}%)\n")

if __name__ == "__main__":
    targets = [
        ("CL=F", "WTI Crude Oil"),
        ("011200.KS", "HMM")
    ]
    print("🚀 1,000만원 투자 기준 Z-Hunter 전략 백테스트 시작\n" + "="*50)
    for ticker, name in targets:
        run_backtest(ticker, name, period="10y")
