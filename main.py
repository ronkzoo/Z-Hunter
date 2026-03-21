import os
import requests
import yfinance as yf
import pandas as pd
import pandas_ta as ta  # ADX 계산용
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# ==========================================
# 1. 환경 변수 및 보안 설정 (.env 파일 로드)
# ==========================================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 토큰 누락 방지 체크
if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 에러: .env 파일에 TELEGRAM_TOKEN 또는 CHAT_ID가 설정되지 않았습니다.")
    exit()

# ==========================================
# 2. 텔레그램 이미지 전송 함수
# ==========================================
def send_telegram_photo(photo_path, caption):
    """생성된 차트 이미지와 메시지를 텔레그램으로 전송합니다."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {'chat_id': CHAT_ID, 'caption': caption}
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            print(f"✅ 텔레그램 메시지 전송 성공!")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

# ==========================================
# 3. Z-Score 차트 생성 함수
# ==========================================
def create_z_score_chart(df, name, ticker):
    """Z-Score 추세선과 과매수/과매도 기준선을 시각화하여 이미지로 저장합니다."""
    plt.figure(figsize=(10, 5))
    
    # Z-Score 라인
    plt.plot(df.index, df['Z-Score'], label='Z-Score', color='purple', linewidth=2)
    
    # 통계적 기준선 (표준편차 ±2σ)
    plt.axhline(y=2, color='red', linestyle='--', label='Overbought (+2σ)')
    plt.axhline(y=-2, color='green', linestyle='--', label='Oversold (-2σ)')
    plt.axhline(y=0, color='black', linestyle='-', linewidth=1)
    
    # 최신 데이터 포인트 강조
    latest_date = df.index[-1]
    latest_z = df['Z-Score'].iloc[-1]
    plt.scatter(latest_date, latest_z, color='blue', s=100, zorder=5)
    plt.annotate(f'Latest: {latest_z:.2f}', 
                 xy=(latest_date, latest_z), 
                 xytext=(-40, 20), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

    plt.title(f'[{name}] Z-Score Mean Reversion Analyzer')
    plt.xlabel('Date')
    plt.ylabel('Z-Score')
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # 여백 제거 후 저장
    filename = f"{ticker}_z_score.png"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    
    return filename

# ==========================================
# 4. 핵심 분석 및 알람 로직 (Z-Score + ADX 필터)
# ==========================================
def analyze_z_hunter_pro(ticker, name, window=20):
    print(f"\n🔍 [{name}] 데이터 분석을 시작합니다...")
    
    # 1. 데이터 수집 (최근 1년치)
    data = yf.download(ticker, period="1y", interval="1d", progress=False)
    if data.empty:
        print(f"❌ {ticker} 데이터를 불러오지 못했습니다.")
        return
    
    df = data[['High', 'Low', 'Close']].copy()
    # 멀티인덱스 컬럼일 경우(yfinance 최신 버전) 단일 인덱스로 평탄화
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. Z-Score 계산: Z = (X - μ) / σ
    df['MA'] = df['Close'].rolling(window=window).mean()
    df['STD'] = df['Close'].rolling(window=window).std()
    df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']

    # 3. ADX 필터 계산 (추세 강도 측정, 14일 기준)
    # pandas_ta를 사용하여 ADX 계산 (결과로 3개 컬럼의 DataFrame이 반환됨)
    adx_df = df.ta.adx(length=14)
    if adx_df is not None:
        df['ADX'] = adx_df['ADX_14']
    else:
        df['ADX'] = 0 # 계산 실패 시 기본값

    # 결측치 제거
    df.dropna(inplace=True)

    # 4. 최신 데이터 추출
    latest = df.iloc[-1]
    z_val = round(latest['Z-Score'], 2)
    adx_val = round(latest['ADX'], 2)
    price = round(latest['Close'], 2)
    
    # 평균(μ)과 표준편차(σ) 추출 (익절/손절 계산용)
    mean_val = latest['MA']
    std_val = latest['STD']

    print(f"📊 현재가: {price} | Z-Score: {z_val} | ADX: {adx_val}")

    # 5. 사냥꾼의 필터링 로직 (텔레그램 전송 판단)
    chart_file = ""
    caption = ""
    send_alert = False

    if z_val <= -2:
        if adx_val < 25:
            # 매수 시점(과매도): 익절은 평균 회귀 지점인 중심선(MA, Z=0)
            tp_price = round(mean_val, 2)
            
            caption = (f"🚨 [Z-Hunter 사냥 시그널 - 롱(매수) 포지션]\n\n"
                       f"🎯 종목: {name}\n"
                       f"💵 현재가: {price:,}\n"
                       f"📉 Z-Score: {z_val} (통계적 바닥권)\n"
                       f"🌊 ADX: {adx_val} (추세 약함, 박스권)\n"
                       f"✅ 익절 목표가: {tp_price:,} (Z-Score 0 / 이동평균선 회귀시)\n"
                       f"⚠️ (주의: 강한 하락장일 경우 분할매수 또는 자체 손절 라인 필요)\n\n"
                       f"✅ 승률 높은 평균회귀 반등 타점입니다! 사냥을 준비하세요! 웅! 😃")
            send_alert = True
        else:
            print(f"⚠️ [보류] 과매도 구간이나 하락 추세가 너무 강합니다. (ADX: {adx_val} >= 25)")

    elif z_val >= 2:
        if adx_val < 25:
            # 숏/매도 시점(과매수): 익절은 평균 회귀 지점인 중심선(MA, Z=0)
            tp_price = round(mean_val, 2)
            
            caption = (f"📢 [Z-Hunter 수확 시그널 - 숏(매도) 포지션]\n\n"
                       f"🎯 종목: {name}\n"
                       f"💵 현재가: {price:,}\n"
                       f"📈 Z-Score: {z_val} (통계적 고점)\n"
                       f"🌊 ADX: {adx_val} (추세 약함, 박스권)\n"
                       f"✅ 목표가(재매수/숏익절): {tp_price:,} (Z-Score 0 / 이동평균선 회귀시)\n\n"
                       f"✅ 익절을 기분 좋게 마무리할 타이밍입니다. 수확하세요! 웅! 😊")
            send_alert = True
        else:
            print(f"⚠️ [보류] 과매수 구간이나 상승 추세가 강력합니다. (ADX: {adx_val} >= 25) 조금 더 즐기셔도 좋습니다!")

    # 6. 알람 전송 및 임시 파일 삭제
    if send_alert:
        print("📲 텔레그램으로 차트와 알람을 전송합니다...")
        chart_file = create_z_score_chart(df, name, ticker)
        send_telegram_photo(chart_file, caption)
        
        # 전송 후 이미지 파일 정리
        if os.path.exists(chart_file):
            os.remove(chart_file)
            print(f"🧹 임시 차트 파일({chart_file}) 삭제 완료.")

# ==========================================
# 5. 메인 실행부
# ==========================================
if __name__ == "__main__":
    print("🤖 Z-Hunter Pro 가동을 시작합니다...")
    
    # 타겟 종목 리스트 (티커, 이름)
    targets = [
        ("CL=F", "WTI Crude Oil"),
        ("011200.KS", "HMM")
    ]
    
    for ticker, name in targets:
        analyze_z_hunter_pro(ticker, name)
        
    print("\n✅ 모든 종목의 감시가 완료되었습니다.")