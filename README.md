# 🎯 Z-Hunter: Mean Reversion Analyzer

통계학적 **평균회귀(Mean Reversion)** 원리를 이용하여 금융 자산의 과매수/과매도 구간을 분석하고 텔레그램으로 알람을 전송하는 퀀트 분석 봇입니다.

## 🚀 Key Features
- **최적의 타겟 종목 감시**: 평균회귀 전략에 최적화된 자산(QQQ, SPY, GLD, KO, WTI) 실시간 모니터링
- **Visual Alert**: Z-Score $\pm2\sigma$ 이탈 시 시각적 차트 시그널 제공
- **Telegram Bot Integration**: 백테스트로 검증된 전략을 바탕으로 실시간 텔레그램 푸시 알림 전송
- **Dynamic Exit Price**: 고정된 틱이 아닌 중심선(이동평균선) 회귀를 이용한 동적 익절 목표가 산출

## 🧠 Theoretical Background (이론적 배경)

**Z-Hunter**는 단순한 감이 아닌, 통계학적 '평균회귀(Mean Reversion)' 원리와 기술적 지표를 결합한 퀀트(Quant) 분석 봇입니다. 핵심 엔진은 **Z-Score**와 **ADX** 두 가지 지표로 구성됩니다.

### 📊 1. Z-Score (표준점수): 사냥의 타점 포착
Z-Score는 현재 가격이 과거의 평균으로부터 통계적으로 얼마나 벗어나 있는지를 측정하는 지표입니다. 데이터가 정규분포를 따른다고 가정할 때, 가격은 결국 평균($\mu$)으로 회귀하려는 강력한 성질(Mean Reversion)을 가집니다.

$$Z = \frac{X - \mu}{\sigma}$$

* **$X$**: 현재 주가 
* **$\mu$**: 20일 기준 이동평균 (Moving Average)
* **$\sigma$**: 20일 기준 표준편차 (Standard Deviation)

**[Trading Logic]**
* **$Z \ge +2$ (Overbought)**: 평균 대비 +2 표준편차 진입 (상위 2.2% 극단값). **숏(매도) 및 익절** 시그널.
* **$Z \le -2$ (Oversold)**: 평균 대비 -2 표준편차 진입 (하위 2.2% 극단값). **롱(매수) 사냥** 시그널.

### 🌊 2. ADX (Average Directional Index): 추세 필터링
Z-Score 평균회귀 전략의 유일한 약점인 '떨어지는 칼날(강력한 한 방향 추세)'을 방어하기 위해 ADX(14일 기준)를 필터로 사용합니다. ADX는 추세의 방향이 아닌 **'추세의 강도(Strength)'**만을 측정합니다.

* **$15 < ADX < 25$**: 극단적 횡보장의 노이즈는 거르고, 지나치게 강력한 추세는 피하는 **평균회귀 전략의 최적 구간**입니다. 봇은 이 구간에서만 알람을 보냅니다.

## 🏆 Backtest Results
10년간의 백테스트를 통해 Z-Score 기반 평균회귀 전략이 가치/배당주(Coca-cola)나 광범위 지수(QQQ, SPY), 그리고 원자재(WTI)에서 박스권 매매에 가장 효과적임을 증명했습니다. (과거 10년, 초기 자본 1,000만원 기준 - Long position only)

- 🥇 **Coca-Cola (KO)**: 누적 수익률 **+68.63%**  (전형적 밴드 장세 방어주)
- 🥈 **NASDAQ 100 (QQQ)**: 누적 수익률 **+36.65%** 
- 🥉 **S&P 500 (SPY)**: 누적 수익률 **+32.86%**
- 🏅 **Gold (GLD)**: 누적 수익률 **+27.24%**

## 🌐 Web Dashboard (Streamlit)
터미널 기반의 봇 뿐만 아니라, 종목을 직접 검색하고 실시간으로 스캔할 수 있는 **강력한 Web UI 대시보드**를 지원합니다.

### 🌟 Dashboard Features
- **🔍 백테스트 스캐너**: 원하는 투자금, 기간을 설정하여 전 종목 복리 시뮬레이션 및 인터랙티브 타점(Plotly) 차트 제공
- **📡 실시간 스캐너**: 당일 기준 매수/매도 시그널 및 추세 강제청산 판별, 원클릭 **텔레그램 알람 전송 기능** 내장
- **⭐ 관심그룹 관리**: 미국 주식, ETF 뿐만 아니라 **국내 주식/ETF (FinanceDataReader)** 검색 및 자동완성 지원

## ⚙️ Installation & Usage

1. **패키지 설치**
```bash
pip install -r requirements.txt
```
*(웹 대시보드 실행을 위해서는 `streamlit`, `plotly`, `FinanceDataReader` 등이 요구됩니다.)*

2. **환경 변수 (.env) 설정**  
프로젝트 루트에 `.env` 파일을 생성하고 텔레그램 봇 토큰과 채팅 ID를 입력합니다.
```text
TELEGRAM_TOKEN=your_token_here
CHAT_ID=your_chat_id_here
```

3. **웹 대시보드 실행 (강력 추천)**
```bash
streamlit run app.py
```

4. **단일 스크립트 모니터링 봇 실행**
```bash
python main.py
```


