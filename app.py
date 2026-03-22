import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import json
import os
import requests
import FinanceDataReader as fdr
import plotly.graph_objects as go

from utils.helpers import send_telegram_message, get_ticker_name, load_watchlists, save_watchlists, load_ticker_names, UNIVERSE_DICT

watchlists = load_watchlists()
ticker_names_cache = load_ticker_names()
from data.loader import backtest_symbol, backtest_hybrid_symbol, get_hybrid_signal, get_live_signal
from dotenv import load_dotenv

load_dotenv(override=True)


warnings.filterwarnings("ignore")

st.set_page_config(page_title="Z-Hunter Web Scanner", page_icon="🎯", layout="wide")

# --- 모바일 최적화 CSS ---
st.markdown("""
<style>
/* --- 1. 기본 Streamlit 여백 및 불필요한 UI 숨김 --- */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 100vw !important;
}

/* --- 2. 모바일 전용 반응형 (max-width: 768px) --- */
@media (max-width: 768px) {
    /* 기본 패딩 최소화 */
    .block-container {
        padding: 1rem 0.5rem !important;
    }
    
    /* 폰트 스케일링 */
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.1rem !important; }

    /* --- 3. 탭(Tab) UI 모바일 최적화 (iOS Segmented Control / 알약 스타일) --- */
    div[data-baseweb="tab-list"] {
        gap: 0.3rem !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        -webkit-overflow-scrolling: touch;
        background-color: rgba(240, 242, 246, 0.8) !important; /* 모바일형 연한 회색 배경 */
        padding: 0.3rem !important;
        border-radius: 12px !important;
        border-bottom: none !important;
        margin-bottom: 15px !important;
    }
    
    /* 기본 탭(Tab) 요소 리셋 및 둥글게 */
    button[data-baseweb="tab"] {
        padding: 0.6rem 1rem !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        background-color: transparent !important;
        border: none !important;
        color: #555555 !important;
    }
    
    /* 활성화된(선택된) 탭 스타일 */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #ffffff !important;
        color: #1f77b4 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.08) !important;
    }

    /* 스트림릿 기본 하단 하이라이트(파란 밑줄) 숨김 */
    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }
    
    /* --- 4. 데이터프레임 모바일 스크롤 확보 --- */
    div[data-testid="stDataFrame"] {
        font-size: 0.75rem !important;
        width: 100% !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    
    /* --- 5. 터치 타겟(Touch Target) 확대 (버튼, 인풋 최소 44px 이상) --- */
    .stButton>button, 
    div[data-baseweb="select"] > div, 
    input[type="number"],
    input[type="text"] {
        min-height: 48px !important;
        font-size: 16px !important; /* iOS 자동 줌(Zoom) 방지 */
        width: 100% !important;
        border-radius: 8px !important;
    }
    
    label[data-baseweb="checkbox"] {
        font-size: 0.9rem !important;
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }
    
    /* --- 6. Metric(지표) 카드형 디자인 구축 --- */
    div[data-testid="metric-container"] {
        background-color: #f7f9fc;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 0.5rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.75rem !important;
    }
    div[data-testid="metric-container"] div {
        font-size: 1.1rem !important;
    }

    /* Plotly 차트 너비 넘침 방지 */
    .js-plotly-plot, .plotly, .js-plotly-plot .plot-container {
        max-width: 100% !important;
    }
}

/* 7. 다크모드 대응 Metric 카드 & Tab UI */
@media (prefers-color-scheme: dark) and (max-width: 768px) {
    div[data-testid="metric-container"] {
        background-color: #2b2b30;
        border: 1px solid #3d3d42;
    }
    div[data-baseweb="tab-list"] {
        background-color: #2b2b30 !important;
    }
    button[data-baseweb="tab"] {
        color: #aaaaaa !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #3d3d42 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3) !important;
    }
}
</style>
""", unsafe_allow_html=True)




# --- 관심그룹 관리 로직 ---


# --- UI 세팅 ---
st.title("🎯 Z-Hunter Web Scanner")
st.markdown("Z-Score와 ADX를 활용한 **평균회귀 전략(Mean Reversion)** 최적화 종목 검색기입니다.")

tab_scan, tab_live, tab_hybrid, tab_watch = st.tabs(["🔍 백테스트 스캐너", "📡 실시간 매수/매도 포착", "🧬 국면별 전략 추천", "⭐ 관심그룹 관리"])

with tab_live:
    st.header("📡 실시간 매수/매도 시그널 포착")
    st.markdown("설정된 전략(**Z-Score <= -2 & ADX < 25**)을 만족하여 **오늘 당장 매수**하거나 **매도**해야 할 종목을 찾아줍니다.")
    
    live_target = st.selectbox("탐색 대상 선택", ["기본 유니버스 (50종목)"] + list(watchlists.keys()), key="live_target_box")
    live_stop_loss = st.selectbox(
        "종목 매도/손절 기준", 
        [
            "ADX 25 돌파 시 (추세 강제청산)", 
            "-3% 수익률 손절", 
            "-5% 수익률 손절", 
            "-10% 수익률 손절", 
            "20일선 하향 돌파 시", 
            "손절/강제청산 없음"
        ],
        key="live_stop_loss_box",
        help="수익률(-3%, -5%, -10%) 손절은 개인 매수 단가가 필요하므로 실시간 스캐너에서는 개별 확인이 필요하다는 메시지가 출력됩니다."
    )
    
    if st.button("🚀 실시간 스캔 시작", type="primary", key="live_btn"):
        st.markdown(f"### 🔍 실시간 데이터를 불러오는 중... (청산 기준: `{live_stop_loss}`)")
        progress_bar_live = st.progress(0)
        status_text_live = st.empty()
        
        if live_target == "기본 유니버스 (50종목)":
            live_tickers = list(UNIVERSE_DICT.keys())
        else:
            live_tickers = watchlists[live_target]
            
        total_live = len(live_tickers)
        if total_live == 0:
            st.warning("선택한 그룹에 등록된 종목이 없습니다.")
            st.stop()
            
        live_results = []
        for i, t in enumerate(live_tickers):
            status_text_live.text(f"분석 중: {t} ({i+1}/{total_live})")
            res = get_live_signal(t, stop_loss_type=live_stop_loss)
            if res:
                live_results.append(res)
            progress_bar_live.progress((i + 1) / total_live)
            
        status_text_live.text("✅ 실시간 스캔 완료!")
        
        if live_results:
            df_live = pd.DataFrame(live_results)
            # 매수 시그널 먼저, 그다음 매도 시그널, 그 다음 관망 순으로 정렬
            def sort_signal(x):
                if '🚨 매수 시그널' in x: return 0
                elif '🟢 매도 시그널' in x: return 1
                elif '⚠️ 매도 시그널' in x: return 2
                else: return 3
            
            df_live['sort_key'] = df_live['현재 상태'].apply(sort_signal)
            df_live = df_live.sort_values('sort_key').drop('sort_key', axis=1).reset_index(drop=True)
            df_live.index += 1
            
            # 하이라이트 함수 적용
            def highlight_row(row):
                if '🚨 매수 시그널' in row['현재 상태']:
                    return ['background-color: rgba(255, 99, 71, 0.4)'] * len(row)
                elif '🟢 매도 시그널' in row['현재 상태']:
                    return ['background-color: rgba(144, 238, 144, 0.4)'] * len(row)
                elif '⚠️ 매도 시그널' in row['현재 상태']:
                    return ['background-color: rgba(255, 165, 0, 0.4)'] * len(row)
                else:
                    return [''] * len(row)
                    
            st.session_state['live_results'] = df_live
            st.dataframe(df_live.style.apply(highlight_row, axis=1), use_container_width=True)
        else:
            st.warning("데이터를 불러올 수 없습니다.")

    if 'live_results' in st.session_state and not st.session_state['live_results'].empty:
        st.markdown("---")
        if st.button("✈️ 텔레그램으로 결과 전송하기"):
            df_curr = st.session_state['live_results']
            buy_list = df_curr[df_curr['현재 상태'] == '🚨 매수 시그널']
            sell_list_norm = df_curr[df_curr['현재 상태'] == '🟢 매도 시그널 (목표달성)']
            sell_list_force = df_curr[df_curr['현재 상태'].str.startswith('⚠️ 매도 시그널')]
            
            msg = "⚡ Z-Hunter 실시간 스캔 결과 ⚡\n\n"
            if not buy_list.empty:
                msg += "🚨 [매수 시그널] (Z-Score<=-2 & ADX<25)\n"
                for _, row in buy_list.iterrows():
                    msg += f"• {row['종목명']} ({row['티커']})\n  - 현재가: {row['현재가']}\n  - 목표매도가(20일선): {row['20일선(MA)']}\n  - 예상수익률: {row['예상수익률(%)']}%\n"
                msg += "\n"
                
            if not sell_list_norm.empty:
                msg += "🟢 [매도 시그널 - 정상 익절] (Z-Score>=0)\n"
                for _, row in sell_list_norm.iterrows():
                    msg += f"• {row['종목명']} ({row['티커']})\n  - 현재가: {row['현재가']}\n"
                msg += "\n"
                
            if not sell_list_force.empty:
                msg += "⚠️ [매도 시그널 - 강제청산/손절]\n"
                for _, row in sell_list_force.iterrows():
                    reason = row['현재 상태'].replace('⚠️ 매도 시그널 ', '')
                    msg += f"• {row['종목명']} ({row['티커']})\n  - 현재가: {row['현재가']}\n  - 사유: {reason}\n"
                msg += "\n"
                
            if buy_list.empty and sell_list_norm.empty and sell_list_force.empty:
                msg += "현재 포착된 매수/매도 시그널이 없습니다."
                
            if send_telegram_message(msg):
                st.success("✅ 텔레그램으로 결과 전송을 완료했습니다!")


with tab_hybrid:
    st.header("🧬 시장 국면별 맞춤 전략 (Regime Switching)")
    st.markdown("허스트 지수(Hurst Exponent)를 통해 현재 **시장의 성질(추세장 vs 박스권)**을 파악하고 최적의 종목을 추천합니다.")
    
    hybrid_target = st.selectbox("분석 대상 선택", ["기본 유니버스 (50종목)"] + list(watchlists.keys()), key="hybrid_target_box")
    
    if st.button("🚀 하이브리드 스캔 시작", type="primary", key="hybrid_run_btn"):
        progress_bar_hy = st.progress(0)
        status_text_hy = st.empty()
        

        if hybrid_target == "기본 유니버스 (50종목)":
            hy_tickers = list(UNIVERSE_DICT.keys())
        else:
            hy_tickers = watchlists[hybrid_target]
            
        total_hy = len(hy_tickers)
        if total_hy == 0:
            st.warning("선택한 그룹에 등록된 종목이 없습니다.")
        else:
            hy_results = []
            for i, t in enumerate(hy_tickers):
                status_text_hy.text(f"국면 분석 중: {t} ({i+1}/{total_hy})")
                res = get_hybrid_signal(t)
                if res is not None:
                    hy_results.append(res)
                progress_bar_hy.progress((i + 1) / total_hy)
                
            status_text_hy.text("✅ 하이브리드 분석 완료!")
            st.session_state["hy_results"] = hy_results
            st.session_state["hy_meta"] = {"target": hybrid_target}
            
    if "hy_results" in st.session_state and st.session_state["hy_results"]:
        hy_results = st.session_state["hy_results"]
        df_hy = pd.DataFrame(hy_results)
        
        st.markdown("---")
        st.markdown(f"### 📊 분석 결과 (대상: `{st.session_state.get('hy_meta', {}).get('target', '선택 그룹')}`)")
        
        # 분리해서 보여주기
        df_buy = df_hy[df_hy["현황 분류"] == "🎯 평균회귀 사냥(매수)"].reset_index(drop=True)
        df_sell = df_hy[df_hy["현황 분류"] == "💰 평균회귀 수확(매도)"].reset_index(drop=True)
        df_trend = df_hy[df_hy["현황 분류"] == "🌊 강력 추세 탑승(매수)"].reset_index(drop=True)
        df_wait = df_hy[df_hy["현황 분류"] == "⏳ 관망"].reset_index(drop=True)
        
        col1, col2 = st.columns(2)
        events = {}
        
        with col1:
            st.subheader("🎯 [박스권-매수] 낙폭 과대 (단기반등 기대)")
            if not df_buy.empty:
                events['buy'] = st.dataframe(df_buy.drop(columns=["현황 분류"]), hide_index=True, use_container_width=True, on_select="rerun", selection_mode=["single-row"], key="hy_df_buy")
            else:
                st.info("조건에 맞는 종목이 없습니다.")
                
            st.subheader("🌊 [추세장-매수] 강력 상승 (불장 탑승)")
            if not df_trend.empty:
                events['trend'] = st.dataframe(df_trend.drop(columns=["현황 분류"]), hide_index=True, use_container_width=True, on_select="rerun", selection_mode=["single-row"], key="hy_df_trend")
            else:
                st.info("조건에 맞는 종목이 없습니다.")
                
        with col2:
            st.subheader("💰 [박스권-매도] 반등 고점 도달 (수확)")
            if not df_sell.empty:
                events['sell'] = st.dataframe(df_sell.drop(columns=["현황 분류"]), hide_index=True, use_container_width=True, on_select="rerun", selection_mode=["single-row"], key="hy_df_sell")
            else:
                st.info("조건에 맞는 종목이 없습니다.")
                
            with st.expander("⏳ 관망 종목 전체 보기 (랜덤 워크)"):
                if not df_wait.empty:
                    events['wait'] = st.dataframe(df_wait.drop(columns=["현황 분류"]), hide_index=True, use_container_width=True, on_select="rerun", selection_mode=["single-row"], key="hy_df_wait")
                else:
                    st.info("조건에 맞는 종목이 없습니다.")
        
        # 선택된 종목 계산
        selected_ticker = None
        for k, e in events.items():
            if e and isinstance(e, dict) and e.get("selection", {}).get("rows"):
                idx = e.get("selection", {}).get("rows")[0]
                if k == 'buy': selected_ticker = df_buy.iloc[idx]["티커"]
                elif k == 'trend': selected_ticker = df_trend.iloc[idx]["티커"]
                elif k == 'sell': selected_ticker = df_sell.iloc[idx]["티커"]
                elif k == 'wait': selected_ticker = df_wait.iloc[idx]["티커"]
                break
                
        if selected_ticker:
            st.markdown("---")
            st.subheader(f"📈 {selected_ticker} ({get_ticker_name(selected_ticker)}) - 최근 1년 차트")
            with st.spinner("차트 데이터 불러오는 중..."):
                chart_df = yf.download(selected_ticker, period="1y", interval="1d", progress=False)
                if not chart_df.empty:
                    if isinstance(chart_df.columns, pd.MultiIndex):
                        chart_df.columns = chart_df.columns.get_level_values(0)
                    # plotly 차트 렌더링
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=chart_df.index,
                        open=chart_df['Open'],
                        high=chart_df['High'],
                        low=chart_df['Low'],
                        close=chart_df['Close'],
                        name='Price',
                        increasing_line_color='red', decreasing_line_color='blue'))
                        
                    # MA20 추가
                    chart_df['MA20'] = chart_df['Close'].rolling(20).mean()
                    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA20'], mode='lines', name='MA20', line=dict(color='orange', width=1)))
                    
                    fig.update_layout(
                        title=f"{selected_ticker} Daily Chart",
                        xaxis_rangeslider_visible=False,
                        template="plotly_dark",
                        height=500,
                        margin=dict(l=0, r=0, t=40, b=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("차트 데이터를 가져올 수 없습니다.")


with tab_watch:
    st.header("⭐ 관심그룹 관리")
    col1, col2 = st.columns(2)
    with col1:
        new_group = st.text_input("새로운 관심그룹 이름")
        if st.button("그룹 추가"):
            if new_group and new_group not in watchlists:
                watchlists[new_group] = []
                save_watchlists(watchlists)
                st.success(f"'{new_group}' 그룹 추가 완료!")
                st.rerun()

    with col2:
        if watchlists:
            del_group = st.selectbox("삭제할 그룹 선택", list(watchlists.keys()))
            if st.button("그룹 삭제"):
                if del_group in watchlists:
                    del watchlists[del_group]
                    save_watchlists(watchlists)
                    st.success(f"'{del_group}' 그룹 삭제 완료!")
                    st.rerun()
                    
    st.divider()
    
    if watchlists:
        mng_group = st.selectbox("관리할 관심그룹 선택", list(watchlists.keys()))
        col_add, col_list = st.columns([1.5, 1.5])  # 좌측 검색 영역 공간 확보를 위해 비율을 조정
        
        with col_add:
            st.markdown("**🔍 새로운 종목 검색 및 추가 (국내/해외 모두 지원)**")
            search_query = st.text_input("회사명이나 티커를 입력하세요 (예: 삼성전자, Apple, 005930, TSLA)")
            
            if search_query:
                # 1. 국내 주식 및 ETF 검색 (FinanceDataReader 활용)
                try:
                    df_krx = fdr.StockListing("KRX")
                    df_etf = fdr.StockListing("ETF/KR")
                    
                    # 주식 검색어 매칭
                    mask_krx = df_krx['Name'].str.contains(search_query, case=False, na=False) | df_krx['Code'].str.contains(search_query, case=False, na=False)
                    krx_matches = df_krx[mask_krx].head(10)
                    
                    # ETF 검색어 매칭
                    mask_etf = df_etf['Name'].str.contains(search_query, case=False, na=False) | df_etf['Symbol'].str.contains(search_query, case=False, na=False)
                    etf_matches = df_etf[mask_etf].head(10)
                    
                    def get_suffix(market):
                        if market == 'KOSPI': return '.KS'
                        elif 'KOSDAQ' in str(market): return '.KQ'
                        return '.KS'
                        
                    suggestions = {}
                    # 주식 추가
                    for _, row in krx_matches.iterrows():
                        code_yf = row['Code'] + get_suffix(row['Market'])
                        suggestions[code_yf] = f"[국내주식] {row['Name']}"
                        
                    # ETF 추가 (.KS가 기본)
                    for _, row in etf_matches.iterrows():
                        code_yf = row['Symbol'] + '.KS'
                        suggestions[code_yf] = f"[국내ETF] {row['Name']}"
                except:
                    suggestions = {}

                # 2. 해외 주식 검색 (Yahoo Finance API)
                url = f"https://query2.finance.yahoo.com/v1/finance/search?q={search_query}"
                headers = {"User-Agent": "Mozilla/5.0"}
                try:
                    req = requests.get(url, headers=headers, timeout=3)
                    data = req.json()
                    quotes = data.get("quotes", [])
                    for q in quotes:
                        if q.get("quoteType") in ["EQUITY", "ETF"]:
                            suggestions[q["symbol"]] = q.get("shortname", q.get("longname", ""))
                except:
                    pass

                if suggestions:
                    options = [f"{sym} - {name}" for sym, name in suggestions.items()]
                    selected_option = st.selectbox("검색 결과 (선택)", options)
                    
                    if st.button("관심그룹에 추가", type="primary"):
                        new_ticker = selected_option.split(" - ")[0]
                        if new_ticker not in watchlists[mng_group]:
                            watchlists[mng_group].append(new_ticker)
                            save_watchlists(watchlists)
                            
                            # 이름을 캐시에 추가하여 전역으로 유지
                            ticker_names_cache[new_ticker] = suggestions[new_ticker]
                            save_ticker_names(ticker_names_cache)
                            
                            st.success(f"'{new_ticker}' ({suggestions[new_ticker]}) 추가 완료!")
                            st.rerun()
                        else:
                            st.warning("이미 등록된 종목입니다.")
                else:
                    st.warning("검색 결과가 없습니다.")
                    manual_ticker = st.text_input("직접 추가할 티커명 입력").upper().strip()
                    if st.button("직접 등록") and manual_ticker:
                        if manual_ticker not in watchlists[mng_group]:
                            watchlists[mng_group].append(manual_ticker)
                            save_watchlists(watchlists)
                            st.success(f"'{manual_ticker}' 추가 완료!")
                            st.rerun()
                        else:
                            st.warning("이미 등록된 종목입니다.")
            else:
                st.info("검색어를 입력하면 자동 완성이 제공됩니다.")
                    
        with col_list:
            st.write(f"**[{mng_group}] 등록된 종목 ({len(watchlists[mng_group])}개)**")
            if not watchlists[mng_group]:
                st.info("등록된 종목이 없습니다.")
            else:
                for t in watchlists[mng_group]:
                    c_name, c_btn = st.columns([4, 1])
                    c_name.write(f"- {t} ({get_ticker_name(t)})")
                    if c_btn.button("삭제", key=f"del_{mng_group}_{t}"):
                        watchlists[mng_group].remove(t)
                        save_watchlists(watchlists)
                        st.rerun()

with tab_scan:
    st.header("🔍 백테스트 스캐너")
    st.markdown("과거 데이터를 바탕으로 선택한 종목과 전략의 퍼포먼스를 검증합니다.")
    
    with st.expander("⚙️ 스캐너 설정", expanded=True):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            scan_strategy = st.selectbox("백테스트 전략", ["기본 평균회귀 (Z-Score)", "하이브리드 (Regime Switching)"], key="scan_strat")
            scan_target = st.selectbox("스캔 대상 선택", ["기본 유니버스 (50종목)"] + list(watchlists.keys()), key="scan_target")
            initial_capital = st.number_input("초기 투자금 (원)", min_value=100000, value=10000000, step=1000000, format="%d", key="scan_cap")
        with col_s2:
            period = st.selectbox("테스트할 기간 선택", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y"], index=4, key="scan_period") # 기본 3y
            min_trades = st.number_input("최소 거래 횟수 기준", min_value=1, value=1, key="scan_trades")
            
            if scan_strategy == "하이브리드 (Regime Switching)":
                stop_ops = ["듀얼 국면 리스크 모델", "ADX 25 돌파 시 (추세 강제청산)", "-3% 수익률 손절", "-5% 수익률 손절", "-10% 수익률 손절", "20일선 하향 돌파 시", "손절/강제청산 없음"]
            else:
                stop_ops = ["ADX 25 돌파 시 (추세 강제청산)", "-3% 수익률 손절", "-5% 수익률 손절", "-10% 수익률 손절", "20일선 하향 돌파 시", "손절/강제청산 없음"]
                
            stop_loss_type = st.selectbox(
                "손절 기준 (청산 전략)", 
                stop_ops,
                key="scan_stop"
            )
        
        run_scan_btn = st.button("🚀 백테스트 스캔 시작", type="primary", use_container_width=True)

    if run_scan_btn:
        st.markdown(f"### 🔍 {period} 데이터 스캔 진행 중... (투자금: {initial_capital:,}원)")
        st.markdown(f"**적용된 청산 전략:** `{stop_loss_type}`")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        if scan_target == "기본 유니버스 (50종목)":
            tickers = list(UNIVERSE_DICT.keys())
        else:
            tickers = watchlists[scan_target]
            
        total_tickers = len(tickers)
        
        if total_tickers == 0:
            st.warning("선택한 그룹에 등록된 종목이 없습니다.")
            st.stop()
        
        for i, ticker in enumerate(tickers):
            status_text.text(f"스캔 중: {ticker} ({i+1}/{total_tickers})")
            
            if scan_strategy == "하이브리드 (Regime Switching)":
                res = backtest_hybrid_symbol(ticker, period=period, initial_capital=initial_capital, stop_loss_type=stop_loss_type)
            else:
                res = backtest_symbol(ticker, period=period, initial_capital=initial_capital, stop_loss_type=stop_loss_type)
                
            if res and res["거래횟수"] >= min_trades:
                results.append(res)
                
            progress_bar.progress((i + 1) / total_tickers)
            
        status_text.text("✅ 스캔 완료!")
        
        if results:
            st.session_state["scan_results"] = results
            st.session_state["scan_meta"] = {"period": period, "capital": initial_capital, "stop_loss": stop_loss_type, "strategy": scan_strategy}
        else:
            st.session_state["scan_results"] = []
            st.warning("조건(최소 거래횟수 등)을 만족하는 종목이 없습니다. 기간이나 조건을 완화해 보세요.")

    if "scan_results" in st.session_state and st.session_state["scan_results"]:
        results = st.session_state["scan_results"]
        meta = st.session_state.get("scan_meta", {})
        
        st.markdown("---")
        st.markdown(f"### 📊 {meta.get('period', period)} 백테스트 결과 (투자금: {meta.get('capital', initial_capital):,}원)")
        st.markdown(f"**적용 전략:** `{meta.get('strategy', '기본 평균회귀 (Z-Score)')}` | **청산 전략:** `{meta.get('stop_loss', stop_loss_type)}`")
        
        # 데이터프레임 변환 및 정렬
        df_results = pd.DataFrame(results)
        df_summary = df_results.drop(columns=["상세내역", "거래횟수", "chart_data"], errors="ignore").copy()
        df_summary["거래횟수"] = df_results["거래횟수"]
        
        # 수익률과 승률을 숫자로 변환하여 정렬 (문자열 정렬 오류 방지)
        df_summary["수익률(%)"] = df_summary["수익률(%)"].astype(float)
        df_summary["승률(%)"] = df_summary["승률(%)"].astype(float)
        
        df_summary = df_summary.sort_values(by=["수익률(%)", "승률(%)"], ascending=[False, False]).reset_index(drop=True)
        # 인덱스 1부터 시작
        df_summary.index += 1
        # 인덱스를 "순위"라는 컬럼으로 명시적으로 변환하여 보이게 만들기
        df_summary.insert(0, "순위", df_summary.index)
        
        st.subheader("🏆 백테스트 요약 결과 Top Rank (클릭하여 상세 내역 확인)")
        
        # 요약 평균 지표를 화면에 표시 (모바일 환경에 맞춰 2열로 배치)
        avg_return = df_summary["수익률(%)"].mean()
        avg_win_rate = df_summary["승률(%)"].mean()
        avg_trades = df_summary["거래횟수"].mean()
        
        profitable_count = (df_summary["수익률(%)"] >= 0).sum()
        loss_count = (df_summary["수익률(%)"] < 0).sum()
        
        if "총수익금(원)" in df_summary.columns and "최종잔고(원)" in df_summary.columns:
            avg_profit = df_summary["총수익금(원)"].astype(str).str.replace(",", "").astype(float).mean()
            avg_balance = df_summary["최종잔고(원)"].astype(str).str.replace(",", "").astype(float).mean()
        else:
            avg_profit, avg_balance = 0, 0
            
        c1, c2 = st.columns(2)
        c1.metric("📌 평균 수익률", f"{avg_return:.2f}%")
        c2.metric("🎯 평균 승률", f"{avg_win_rate:.2f}%")
        
        c3, c4 = st.columns(2)
        c3.metric("💰 평균 수익금", f"{int(avg_profit):,}원")
        c4.metric("🏦 평균 최종잔고", f"{int(avg_balance):,}원")
        
        c5, c6 = st.columns(2)
        if "MDD(%)" in df_summary.columns:
            df_summary["MDD(%)"] = df_summary["MDD(%)"].astype(float)
            avg_mdd = df_summary["MDD(%)"].mean()
            c5.metric("📉 평균 MDD", f"{avg_mdd:.2f}%")
            c6.metric("🔄 평균 거래횟수", f"{avg_trades:.1f}회")
        else:
            c5.metric("🔄 평균 거래횟수", f"{avg_trades:.1f}회")
            
        c7, c8 = st.columns(2)
        c7.metric("📈 수익 종목 수", f"{profitable_count}개")
        c8.metric("📉 손실 종목 수", f"{loss_count}개")
        
        st.markdown("")

        # 데이터프레임 예쁘게 출력 및 선택 기능 추가
        st_styled = df_summary.style.format({
            "수익률(%)": "{:.2f}",
            "승률(%)": "{:.2f}"
        }).background_gradient(cmap='Greens', subset=['수익률(%)', '승률(%)']).hide(axis="index") # 기본 인덱스 숨기고 커스텀 순위 컬럼 사용
        
        event = st.dataframe(
            st_styled, 
            use_container_width=True, 
            on_select="rerun", 
            selection_mode=["single-cell"], # 체크박스(single-row) 대신 셀 클릭 이벤트 사용
            hide_index=True # Streamlit 데이터프레임 설정에서도 인덱스 렌더링 끄기 (체크박스 공간만 차지하는 빈 컬럼 방지)
        )

        selected_rows = event.get("selection", {}).get("rows", []) if isinstance(event, dict) else (event.selection.get("rows", []) if hasattr(event, "selection") else [])
        selected_cells = event.get("selection", {}).get("cells", []) if isinstance(event, dict) else (event.selection.get("cells", []) if hasattr(event, "selection") else [])
        selected_idx = None
        
        if selected_rows:
            selected_idx = selected_rows[0]
        elif selected_cells:
            # Streamlit 반환 형태(Tuple 또는 Dict)에 맞게 안전하게 행(Row) 인덱스 추출
            first_cell = selected_cells[0]
            selected_idx = first_cell[0] if isinstance(first_cell, tuple) else first_cell.get("row")

        if selected_idx is not None:
            # 선택된 행의 인덱스를 가져와 원래 데이터 정보 찾기
            selected_ticker_name = df_summary.iloc[selected_idx]["티커표시"]
            
            # results에서 해당 종목 데이터 찾기
            selected_res = next((item for item in results if item["티커표시"] == selected_ticker_name), None)
            
            if selected_res:
                st.markdown("---")
                
                # 헤더 및 관심종목 추가 UI 영역을 콤팩트하게 구성
                c_title, c_group, c_btn = st.columns([5, 2, 1.5])
                with c_title:
                    st.subheader(f"📜 {selected_ticker_name} 상세 거래 내역")
                
                # 티커 심볼 유추 (예: "AAPL (Apple)" -> AAPL, "005930 (삼성전자)" -> 005930)
                raw_ticker = selected_ticker_name.split(" ")[0].strip()
                
                with c_group:
                    if watchlists:
                        target_group = st.selectbox("관심그룹 지정", list(watchlists.keys()), key=f"wc_group_{raw_ticker}", label_visibility="collapsed")
                with c_btn:
                    if watchlists:
                        if st.button("⭐ 그룹에 추가", type="secondary", key=f"wc_add_{raw_ticker}"):
                            if raw_ticker not in watchlists[target_group]:
                                watchlists[target_group].append(raw_ticker)
                                save_watchlists(watchlists)
                                st.toast(f"✅ [{target_group}] 그룹에 {raw_ticker} 추가 완료!")
                            else:
                                st.toast(f"⚠️ 이미 [{target_group}] 그룹에 존재합니다.")

                trade_logs = selected_res["상세내역"]
                chart_df = selected_res.get("chart_data")
                
                if trade_logs:
                    df_logs = pd.DataFrame(trade_logs)
                    df_logs.index += 1
                    
                    # 1. 고유 키로 dataframe 선택 상태 확인 (렌더링 전 사전 확인)
                    log_table_key = f"logs_{raw_ticker}"
                    selected_log_idx = None
                    if log_table_key in st.session_state:
                        rows = st.session_state[log_table_key].get("selection", {}).get("rows", [])
                        if rows:
                            selected_log_idx = rows[0]
                    
                    # Plotly 차트 그리기
                    if chart_df is not None and not chart_df.empty:
                        fig = go.Figure()
                        # 전체 종가 라인 차트
                        fig.add_trace(go.Scatter(
                            x=chart_df['Date'], y=chart_df['Close'], 
                            mode='lines', name='Price', line=dict(color='gray', width=1)
                        ))
                        
                        # 2. 매수/매도 포인트 추출 (결측치 '-' 고려)
                        buy_dates, buy_prices = [], []
                        sell_dates, sell_prices = [], []
                        for log in trade_logs:
                            if log.get('매수일자') and log['매수일자'] != '-':
                                buy_dates.append(log['매수일자'])
                                buy_prices.append(float(str(log['매수가']).replace(',', '')))
                            if log.get('매도일자') and log['매도일자'] != '-':
                                sell_dates.append(log['매도일자'])
                                sell_prices.append(float(str(log['매도가']).replace(',', '')))
                            
                        # 일반 매수(Buy) 점 찍기
                        if buy_dates:
                            fig.add_trace(go.Scatter(
                                x=buy_dates, y=buy_prices, mode='markers', name='Buy',
                                marker=dict(symbol='triangle-up', size=10, color='blue', line=dict(width=1, color='DarkSlateGrey'))
                            ))
                            
                        # 일반 매도(Sell) 점 찍기
                        if sell_dates:
                            fig.add_trace(go.Scatter(
                                x=sell_dates, y=sell_prices, mode='markers', name='Sell',
                                marker=dict(symbol='triangle-down', size=10, color='red', line=dict(width=1, color='DarkSlateGrey'))
                            ))
                            
                        # 🔥 선택된 내역 강조 표시
                        if selected_log_idx is not None:
                            sel_log = df_logs.iloc[selected_log_idx]
                            b_date = sel_log.get('매수일자', '-')
                            s_date = sel_log.get('매도일자', '-')
                            
                            b_valid = str(b_date) != '-' and pd.notnull(b_date)
                            s_valid = str(s_date) != '-' and pd.notnull(s_date)
                            
                            if b_valid:
                                b_price = float(str(sel_log.get('매수가', 0)).replace(',', ''))
                                fig.add_trace(go.Scatter(
                                    x=[b_date], y=[b_price], mode='markers', name='Selected Buy',
                                    marker=dict(size=20, color='gold', symbol='star', line=dict(width=2, color='black'))
                                ))
                                
                            if s_valid:
                                s_price = float(str(sel_log.get('매도가', 0)).replace(',', ''))
                                fig.add_trace(go.Scatter(
                                    x=[s_date], y=[s_price], mode='markers', name='Selected Sell',
                                    marker=dict(size=20, color='darkorange', symbol='star', line=dict(width=2, color='black'))
                                ))
                                
                            if b_valid and s_valid:
                                fig.add_vrect(
                                    x0=b_date, x1=s_date,
                                    fillcolor="yellow", opacity=0.3,
                                    layer="below", line_width=0,
                                )

                        fig.update_layout(
                            title=f"{selected_ticker_name} Backtest Trade Points",
                            xaxis_title="Date",
                            yaxis_title="Price",
                            xaxis=dict(tickformat="%Y-%m-%d", hoverformat="%Y-%m-%d"),
                            height=400,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(
                        df_logs, 
                        use_container_width=True,
                        selection_mode="single-row",
                        on_select="rerun",
                        key=log_table_key
                    )
                else:
                    st.write("상세 거래 내역이 없습니다.")
        else:
            st.info("👆 위 표에서 종목의 행을 클릭하시면 상세 거래 내역과 차트가 이곳에 표시됩니다.")