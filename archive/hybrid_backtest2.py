import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

class ZHunterHybridBacktester:
    def __init__(self, ticker="SPY", start_date="2015-01-01", end_date="2024-01-01", initial_capital=100000):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        
        # 종목별 특정 파라미터 튜닝 (Stock Specific Tuning)
        self.z_threshold = -2.5 if self.ticker == "TSLA" else -2.0
        
    def _calculate_hurst(self, ts, max_lag=20):
        """허스트 지수(Hurst Exponent) 계산 (Rescaled Range 변형)"""
        if len(ts) < max_lag:
            return np.nan
        lags = range(2, max_lag)
        # 시차(lag)에 따른 표준편차 배열 생성
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        # Log-Log 기울기를 통해 H값 도출
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    def prepare_data(self):
        """데이터 수집 및 핵심 지표 계산"""
        print(f"[{self.ticker}] 데이터 수집 및 지표 계산 중...")
        df = yf.download(self.ticker, start=self.start_date, end=self.end_date, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. 기술적 지표 (pandas_ta 활용)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Z_Score'] = (df['Close'] - df['MA20']) / df['STD20']
        
        # ADX (14일) & ATR (14일)
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14']
        df['ATR'] = df.ta.atr(length=14)
        
        # 20일 이전 신고가 추적 (추세추종 Breakout 용)
        df['High20_Prev'] = df['High'].rolling(window=20).max().shift(1)
        
        # 2. 시장 국면 (Regime) 판별: 100일 롤링 허스트 지수
        df['Hurst'] = df['Close'].rolling(window=100).apply(self._calculate_hurst, raw=True)
        
        return df.dropna()

    def run_backtest(self):
        df = self.prepare_data()
        
        cash = self.initial_capital
        shares = 0
        position_mode = None  # "MR" (평균회귀) or "TF" (추세추종)
        entry_price = 0
        stop_loss = 0
        
        trades = []
        equity_curve = []
        
        for date, row in df.iterrows():
            close = row['Close']
            ma20, ma60 = row['MA20'], row['MA60']
            z_score, adx = row['Z_Score'], row['ADX']
            atr, hurst = row['ATR'], row['Hurst']
            prev_high_20 = row['High20_Prev']
            
            # --- [1] EXIT (청산 로직) ---
            if position_mode is not None:
                # 1-1. 공통 리스크 관리 (Stop Loss)
                if close <= stop_loss:
                    cash = shares * close
                    profit_pct = (close - entry_price) / entry_price
                    trades.append({'Date': date, 'Type': 'StopLoss', 'Mode': position_mode, 'Profit': profit_pct})
                    position_mode, shares, entry_price = None, 0, 0
                    
                # 1-2. 평균회귀(MR) 청산 로직
                elif position_mode == "MR":
                    # 돌발 추세 발생에 의한 강제 청산 (ADX 25 돌파)
                    if adx > 25:
                        cash = shares * close
                        profit_pct = (close - entry_price) / entry_price
                        trades.append({'Date': date, 'Type': 'ForceExit_MR_Breakout', 'Mode': 'MR', 'Profit': profit_pct})
                        position_mode, shares, entry_price = None, 0, 0
                        
                    # 평균으로의 회귀 성공 (Z-Score가 양수로 전환되거나 20일선 터치)
                    elif z_score >= 0 or close >= ma20:
                        cash = shares * close
                        profit_pct = (close - entry_price) / entry_price
                        trades.append({'Date': date, 'Type': 'TakeProfit_MR', 'Mode': 'MR', 'Profit': profit_pct})
                        position_mode, shares, entry_price = None, 0, 0
                        
                # 1-3. 추세추종(TF) 청산 로직
                elif position_mode == "TF":
                    # 추세 이탈 (20일선 하향 이탈시 익절/손절)
                    if close < ma20:
                        cash = shares * close
                        profit_pct = (close - entry_price) / entry_price
                        trades.append({'Date': date, 'Type': 'Exit_TF_DropMA20', 'Mode': 'TF', 'Profit': profit_pct})
                        position_mode, shares, entry_price = None, 0, 0

            # --- [2] ENTRY (진입 로직) ---
            if position_mode is None:
                # 2-1. 평균회귀 모드 (Hurst < 0.45)
                if hurst < 0.45:
                    if z_score <= self.z_threshold and adx < 25:
                        position_mode = "MR"
                        entry_price = close
                        shares = cash / entry_price
                        cash = 0
                        
                        # Stop Loss: -3% 고정 손목과 2*ATR 변동 손목 중 더 '타이트한(높은 가격)' 라인을 산출 적용
                        stop_loss = max(entry_price * 0.97, entry_price - (2 * atr))

                # 2-2. 추세추종 모드 (Hurst > 0.55)
                elif hurst > 0.55:
                    # 20일 이전 신고가 돌파 & 강한 추세(ADX > 25) & 정배열(MA20 > MA60)
                    if close > prev_high_20 and adx > 25 and ma20 > ma60:
                        position_mode = "TF"
                        entry_price = close
                        shares = cash / entry_price
                        cash = 0
                        
                        stop_loss = max(entry_price * 0.97, entry_price - (2 * atr))
            
            # --- [3] 수익금 시계열 로깅 ---
            current_equity = cash + (shares * close if position_mode is not None else 0)
            equity_curve.append({'Date': date, 'Equity': current_equity})
            
        return pd.DataFrame(trades), pd.DataFrame(equity_curve)

    def print_performance(self, trades_df, equity_df):
        """백테스트 핵심 퍼포먼스 지표(Metrics) 계산 및 출력"""
        if equity_df.empty:
            print("데이터가 부족하여 백테스트를 수행할 수 없습니다.")
            return

        equity = equity_df['Equity'].values
        initial = float(self.initial_capital)
        final = float(equity[-1])
        
        # 1. CAGR (연평균 수익률)
        days = (equity_df['Date'].iloc[-1] - equity_df['Date'].iloc[0]).days
        years = days / 365.25
        cagr = ((final / initial) ** (1 / years) - 1) * 100
        
        # 2. MDD (최대 낙폭)
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max
        mdd = drawdowns.min() * 100
        
        # 3. Win Rate (승률)
        if not trades_df.empty:
            wins = len(trades_df[trades_df['Profit'] > 0])
            total_trades = len(trades_df)
            win_rate = (wins / total_trades) * 100
        else:
            win_rate = 0.0
            total_trades = 0
        
        # 4. Sharpe Ratio (샤프 지수)
        daily_returns = equity_df['Equity'].pct_change().dropna()
        if daily_returns.std() != 0:
            sharpe_ratio = np.sqrt(252) * (daily_returns.mean() / daily_returns.std())
        else:
            sharpe_ratio = 0.0

        print("="*45)
        print(f"🎯 Z-Hunter Backtest Result: {self.ticker}")
        print(f"기간: {self.start_date} ~ {self.end_date}")
        print("="*45)
        print(f"포트폴리오 최종 자산: ${final:,.2f} / (초기 ${initial:,.2f})")
        print(f"누적 수익률          : {((final / initial) - 1) * 100:.2f}%")
        print(f"CAGR (연평균수익률): {cagr:.2f}%")
        print(f"MDD (최대 낙폭)      : {mdd:.2f}%")
        print(f"전체 거래 횟수       : {total_trades}회")
        print(f"매매 승률 (Win Rate) : {win_rate:.2f}%")
        print(f"Sharpe Ratio         : {sharpe_ratio:.2f}")
        print("="*45)

# --- 실제 백테스트 실행 ---
if __name__ == "__main__":
    # 나스닥 QQQ 테스트 (표준 설정)
    tester_qqq = ZHunterHybridBacktester(ticker="QQQ", start_date="2018-01-01", end_date="2024-01-01")
    trades_qqq, equity_qqq = tester_qqq.run_backtest()
    tester_qqq.print_performance(trades_qqq, equity_qqq)
    
    # 튜닝된 TSLA 테스트 (Z-Score -2.5 진입)
    tester_tsla = ZHunterHybridBacktester(ticker="TSLA", start_date="2018-01-01", end_date="2024-01-01")
    trades_tsla, equity_tsla = tester_tsla.run_backtest()
    tester_tsla.print_performance(trades_tsla, equity_tsla)