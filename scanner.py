import yfinance as yf
import pandas as pd
import warnings
from tqdm import tqdm

warnings.filterwarnings("ignore")

# 광범위한 자산 유니버스 (ETF, 방어주, 필수소비재, 빅테크, 금융, 에너지 등 50개 대표 종목)
UNIVERSE = [
    # 시황/지수 ETF 및 원자재
    "SPY", "QQQ", "DIA", "IWM", "GLD", "SLV", "TLT", "USO", "UNG", "UUP",
    # 방어주 및 배당/필수소비재
    "KO", "PEP", "PG", "JNJ", "MCD", "WMT", "COST", "TGT", "PM", "CL",
    # 대형 우량주 / 빅테크
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ADBE", "CRM",
    # 금융 
    "JPM", "BAC", "WFC", "V", "MA", "AXP", "GS", "MS", "BLK", "C",
    # 헬스케어, 에너지 및 기타
    "XOM", "CVX", "SHW", "HD", "UNH", "LLY", "MRK", "ABBV", "PFE", "TMO"
]

def backtest_symbol(ticker, period="10y", initial_capital=10000000):
    try:
        # 데이터 다운로드
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if df.empty:
            return None
        
        # yfinance 최신버전 MultiIndex 처리
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
        win_trades = 0
        total_trades = 0

        # 시뮬레이션
        for index, row in df.iterrows():
            z = row['Z-Score']
            adx = row['ADX']
            price = row['Close']

            # 매수: 과매도 (Z <= -2) AND 추세가 없을 때 (ADX < 25)
            if position == 0 and z <= -2 and adx < 25:
                position = capital // price
                buy_price = price
                capital -= position * price
            
            # 매도: 중심선(평균) 회귀 시 (Z >= 0)
            elif position > 0 and z >= 0:
                capital += position * price
                if price > buy_price:
                    win_trades += 1
                total_trades += 1
                position = 0

        # 백테스트 마지막 날 강제 청산
        if position > 0:
            last_price = df.iloc[-1]['Close']
            capital += position * last_price
            if last_price > buy_price:
                win_trades += 1
            total_trades += 1

        # 수익률 및 승률 계산
        total_return = ((capital - initial_capital) / initial_capital) * 100
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "Ticker": ticker,
            "Return(%)": round(total_return, 2),
            "Win Rate(%)": round(win_rate, 2),
            "Trades": total_trades
        }
    except Exception:
        return None

def main():
    print(f"🔍 총 {len(UNIVERSE)}개 주요 벤치마크 종목 대상 최근 3개월 치 Z-Hunter 로직 스캔 시작...\n")
    results = []
    
    for ticker in tqdm(UNIVERSE, desc="백테스트 진행 중", unit="종목"):
        res = backtest_symbol(ticker, period="3mo")
        if res:
            # 3개월처럼 짧은 기간에는 거래 횟수가 적으므로, 최소 거래 횟수 조건을 대폭 하향(1회 이상)
            if res["Trades"] >= 1:
                results.append(res)
                
    # 결과 정렬 (1순위: 누적 수익률, 2순위: 승률)
    sorted_results = sorted(results, key=lambda x: (x["Return(%)"], x["Win Rate(%)"]), reverse=True)
    
    print("\n\n🏆 Z-Hunter (평균회귀) 전략에 최적화된 TOP 10 종목 🏆")
    print("=" * 65)
    print(f"{'Rank':<5} | {'Ticker':<8} | {'Return(%)':<12} | {'Win Rate(%)':<13} | {'Trades':<8}")
    print("-" * 65)
    
    for i, res in enumerate(sorted_results[:10], start=1):
        print(f"{i:<5} | {res['Ticker']:<8} | {res['Return(%)']:>8.2f} % | {res['Win Rate(%)']:>9.2f} % | {res['Trades']:>6}")

if __name__ == '__main__':
    main()