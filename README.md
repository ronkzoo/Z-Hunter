# 🎯 Z-Hunter: Mean Reversion Analyzer

통계학적 **평균회귀(Mean Reversion)** 원리를 이용하여 금융 자산의 과매수/과매도 구간을 분석하는 도구입니다.

## 📈 Mathematical Background
본 프로젝트는 **Z-Score**를 핵심 지표로 사용합니다.

$$Z = \frac{X - \mu}{\sigma}$$

- $X$: 현재 가격
- $\mu$: 이동평균 (20일 기준)
- $\sigma$: 표준편차

## 🚀 Key Features
- **WTI 원유 및 HMM 주가 분석**: 실시간 금융 데이터를 바탕으로 Z-Score 산출
- **Visual Alert**: $\pm2\sigma$를 벗어나는 '이상치(Outlier)' 발생 시 시각적 시그널 제공
- **Mean Reversion Strategy**: 평균으로 회귀하려는 성질을 이용한 매수/매도 타이밍 포착