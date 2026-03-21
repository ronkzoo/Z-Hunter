import numpy as np
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from typing import Tuple, Dict

class DualRegimeRiskManager:
    """
    Z-Hunter 핵심 엔진:
    Hurst Exponent를 이용한 Regime Switching 및 국면별 차등 Stop-Loss 메커니즘 구현
    """
    
    def __init__(self, ticker: str, start_date: str, end_date: str, initial_capital: float = 10000000):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        
        # 거래 비용 (진입/청산 왕복 0.25% -> 편도 0.125%)
        self.tx_cost = 0.00125  
        self.data = pd.DataFrame()
        self.trade_logs = []

    def _calc_hurst(self, ts: pd.Series, max_lag: int = 20) -> float:
        """Rescaled Range 변형을 이용한 Hurst Exponent 산출"""
        if len(ts) < max_lag:
            return np.nan
        lags = range(2, max_lag)
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    def prepare_market_data(self) -> pd.DataFrame:
        """시장 데이터 다운로드 및 국면/리스크 기술적 지표 생성"""
        df = yf.download(self.ticker, start=self.start_date, end=self.end_date, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['Open', 'High', 'Low', 'Close']].copy()

        # 1. 기술적 지표 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA20']) / df['STD20']
        
        # breakout 기준선: 전일 기준 최근 20일 고가 (Lookahead Bias 방지)
        df['High_20'] = df['High'].rolling(window=20).max().shift(1)
        
        # 리스크 지표 (ADX, ATR)
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0
        df['ATR'] = df.ta.atr(length=14)
        
        # 2. Regime 판별 지표 (Hurst Exponent - 100일 윈도우)
        df['Hurst'] = df['Close'].rolling(100).apply(self._calc_hurst, raw=True)
        
        # 결측치 제거
        self.data = df.dropna().copy()
        return self.data

    def run_backtest(self) -> Tuple[pd.DataFrame, Dict]:
        """듀얼 전략 및 국면별 맞춤 손절 엔진 구동"""
        if self.data.empty:
            self.prepare_market_data()
            
        df = self.data
        capital = self.initial_capital
        position = 0
        entry_price = 0.0
        mode = None               # 'MR' (Mean Reversion) or 'TF' (Trend Following)
        trailing_stop_price = 0.0
        
        equity_curve = []
        
        for date, row in df.iterrows():
            close = row['Close']
            z_score = row['Z-Score']
            adx = row['ADX']
            atr = row['ATR']
            ma20 = row['MA20']
            hurst = row['Hurst']
            high_20 = row['High_20']

            # ----------------------------------------------------
            # [포지션이 있는 경우] 청산 및 손절(Stop-Loss) 로직
            # ----------------------------------------------------
            if position > 0:
                exit_signal = False
                reason = ""

                if mode == 'MR':
                    # 1) MR: 통계적 붕괴 손절 (Z <= -3.5)
                    if z_score <= -3.5:
                        exit_signal, reason = True, "[MR 손절] 통계적 붕괴 (Z<=-3.5)"
                    # 2) MR: 추세 전환 손절 (ADX > 30)
                    elif adx > 30:
                        exit_signal, reason = True, "[MR 손절] 박스권 이탈형 추세발생 (ADX>30)"
                    # 3) MR: 정상 익절 (평균 회귀 완료, Z >= 0)
                    elif z_score >= 0:
                        exit_signal, reason = True, "[MR 익절] 평균 회귀 달성 (Z>=0)"

                elif mode == 'TF':
                    # 변동성 트레일링 스톱 계산 (2 * ATR)
                    current_ts = close - (2 * atr)
                    trailing_stop_price = max(trailing_stop_price, current_ts)
                    
                    # 1) TF: 기준선 이탈 손절 (종가 < 20일선)
                    if close < ma20:
                        exit_signal, reason = True, "[TF 청산] 기준선(MA20) 하향 돌파"
                    # 2) TF: 트레일링 스톱 이탈 손절
                    elif close < trailing_stop_price:
                        exit_signal, reason = True, "[TF 청산] 트레일링 스톱 이탈"

                if exit_signal:
                    gross_return = (close / entry_price) - 1
                    net_return = gross_return - (self.tx_cost * 2) # 왕복 수수료 차감
                    
                    pnl = position * close * (1 - self.tx_cost) - (position * entry_price)
                    capital += (position * close) * (1 - self.tx_cost) # 매도
                    
                    self.trade_logs.append({
                        "Date": date.strftime('%Y-%m-%d'),
                        "Regime": mode,
                        "Type": reason,
                        "Entry Price": round(entry_price, 2),
                        "Exit Price": round(close, 2),
                        "Net PnL": round(pnl, 2),
                        "Return(%)": round(net_return * 100, 2)
                    })
                    
                    position = 0
                    mode = None

            # ----------------------------------------------------
            # [포지션이 없는 경우] Regime Switching 기반 진입 로직
            # ----------------------------------------------------
            if position == 0:
                # 1. 평균회귀(MR) 국면 (Hurst < 0.45)
                if hurst < 0.45 and z_score <= -2.0:
                    mode = 'MR'
                # 2. 추세추종(TF) 국면 (Hurst > 0.55)
                elif hurst > 0.55 and close > high_20:
                    mode = 'TF'
                    trailing_stop_price = close - (2 * atr)
                
                if mode is not None:
                    # 매수 실행 (편도 수수료 차감)
                    buy_size = capital * (1 - self.tx_cost)
                    position = buy_size / close
                    entry_price = close
                    capital -= (buy_size + capital * self.tx_cost)

            # Mark to Market (일일 자본금 평가)
            current_equity = capital + (position * close) if position > 0 else capital
            equity_curve.append(current_equity / self.initial_capital)

        df['Equity'] = equity_curve
        return df, self.evaluate_performance(df, equity_curve)

    def evaluate_performance(self, df: pd.DataFrame, equity_curve: list) -> Dict:
        """CAGR, MDD, Sharpe Ratio 등 성과 지표 계산 모듈"""
        returns = pd.Series(equity_curve).pct_change().dropna()
        
        # CAGR
        days = (df.index[-1] - df.index[0]).days
        cagr = (equity_curve[-1] ** (365.0 / days)) - 1 if days > 0 else 0
        
        # MDD (자산 고점 대비 최대 낙폭)
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        mdd = abs(np.min(drawdown))
        
        # Sharpe Ratio (무위험 수익률 0% 가정)
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        
        # Win Rate
        if len(self.trade_logs) > 0:
            win_trades = sum(1 for log in self.trade_logs if log['Return(%)'] > 0)
            win_rate = win_trades / len(self.trade_logs)
        else:
            win_rate = 0.0

        return {
            "Total Return(%)": round((equity_curve[-1]-1) * 100, 2),
            "CAGR(%)": round(cagr * 100, 2),
            "MDD(%)": round(mdd * 100, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Win Rate(%)": round(win_rate * 100, 2),
            "Total Trades": len(self.trade_logs)
        }

# =====================================================================
# 실행 및 검증 (Execution & Validation)
# =====================================================================
if __name__ == "__main__":
    print("🚀 Initializing Dual-Regime Risk Management Engine...")
    
    # QQQ (나스닥 100 ETF) 기준 백테스트 (변동성이 좋아 하이브리드 검증에 우수)
    engine = DualRegimeRiskManager(ticker="QQQ", start_date="2018-01-01", end_date="2024-01-01")
    
    df, metrics = engine.run_backtest()
    
    # 전략 성과 테이블 파싱
    print("\n" + "="*50)
    print(f"📊 [ {engine.ticker} ] Performance Analytics Dashboard")
    print("="*50)
    for key, val in metrics.items():
        print(f" - {key:18}: {val}")
    print("="*50)

    # 주요 손절/방어 로그 출력 (최근 부분만 출력하여 확인)
    print("\n🔍 Recent Trade Logs (Focusing on Risk Management Events):")
    print("-" * 80)
    for log in engine.trade_logs[-10:]:
        # Terminal 컬러 포맷팅 (손실: 빨강, 이익: 초록 파랑)
        color = "\033[91m" if log['Return(%)'] < 0 else "\033[92m"
        reset = "\033[0m"
        print(f"[{log['Date']}] {log['Regime']} | {log['Type']:<32} | Return: {color}{log['Return(%)']:>5}%{reset}")
    print("-" * 80)
