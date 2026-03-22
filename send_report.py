import os
import requests
import pandas as pd
from dotenv import load_dotenv

# 대상 스크립트 및 딕셔너리 임포트
from app import UNIVERSE_DICT, backtest_hybrid_symbol

# 환경 변수 로드
load_dotenv(override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ 텔레그램 토큰 또는 CHAT_ID가 설정되지 않았습니다 (.env 확인 필요)")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ 텔레그램 알림 전송 성공!")
            return True
        else:
            print(f"❌ 전송 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 전송 중 에러 발생: {e}")
        return False

def generate_report():
    print("🚀 하이브리드 전략 5년치 배치 백테스트 시작 (듀얼-리즘 리스크 매니지먼트)...\n")
    
    results = []
    tickers = list(UNIVERSE_DICT.keys())
    
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] {ticker} 분석 중...")
        res = backtest_hybrid_symbol(ticker, period="5y", initial_capital=10000000)
        if res is not None:
            results.append({
                "Ticker": ticker,
                "Name": UNIVERSE_DICT[ticker],
                "CAGR": float(res["CAGR(%)"]),
                "MDD": float(res["MDD(%)"]),
                "WinRate": float(res["승률(%)"]),
                "Return": float(res["수익률(%)"]),
                "Trades": int(res["거래횟수"])
            })
            
    if not results:
        print("결과가 없습니다.")
        return
        
    df = pd.DataFrame(results)
    
    # 평균 수치 계산
    avg_cagr = df["CAGR"].mean()
    avg_mdd = df["MDD"].mean()
    avg_return = df["Return"].mean()
    
    # CAGR 기준 상/하위 정렬
    df_sorted = df.sort_values(by="CAGR", ascending=False)
    
    top_5 = df_sorted.head(5)
    bottom_5 = df_sorted.tail(5)
    
    msg = f"🏆 *Z-Hunter 하이브리드 전략 5년 백테스트 최종 리포트*\n"
    msg += f"▪️ 테스트 종목: 총 {len(df)}개 유니버스\n"
    msg += f"▪️ 기간: 최근 5년\n"
    msg += f"▪️ 적용 전략: Dual Regime + 동적 손절 엔진\n\n"
    
    msg += f"📊 *[유니버스 평균 지표]*\n"
    msg += f"• 평균 누적 수익률: `{avg_return:.2f}%`\n"
    msg += f"• 평균 연복리 (CAGR): `{avg_cagr:.2f}%`\n"
    msg += f"• 평균 최대 낙폭 (MDD): `{avg_mdd:.2f}%`\n\n"
    
    msg += f"🚀 *[Top 5 우수 종목 (CAGR 기준)]*\n"
    for _, row in top_5.iterrows():
        msg += f"🥇 {row['Ticker']} ({row['Name']})\n"
        msg += f"   └ CAGR: {row['CAGR']:.2f}% | MDD: {row['MDD']:.2f}% | 승률: {row['WinRate']:.2f}%\n"
        
    msg += f"\n⚠️ *[Bottom 5 부진 종목 (CAGR 기준)]*\n"
    for _, row in bottom_5.iterrows():
        msg += f"🔻 {row['Ticker']} ({row['Name']})\n"
        msg += f"   └ CAGR: {row['CAGR']:.2f}% | MDD: {row['MDD']:.2f}% | 승률: {row['WinRate']:.2f}%\n"

    print("\n[Report Generated]\n" + msg)
    send_telegram_message(msg)

if __name__ == "__main__":
    generate_report()
