import re

with open("app.py", "r") as f:
    content = f.read()

# Add json and os imports
if "import json" not in content:
    content = content.replace("import time\n", "import time\nimport json\nimport os\n")

# Replacements
UI_SETTING_MARKER = "# --- UI 세팅 ---"
ui_code = """
# --- 관심그룹 관리 로직 ---
WATCHLIST_FILE = "watchlists.json"

def load_watchlists():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"내 관심그룹": ["AAPL", "TSLA", "QQQ"]}

def save_watchlists(data):
    with open(WATCHLIST_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

watchlists = load_watchlists()

# --- UI 세팅 ---
st.title("🎯 Z-Hunter Web Scanner")
st.markdown("Z-Score와 ADX를 활용한 **평균회귀 전략(Mean Reversion)** 최적화 종목 검색기입니다.")

tab_scan, tab_watch = st.tabs(["🔍 스캐너", "⭐ 관심그룹 관리"])

with tab_watch:
    st.header("⭐ 관심그룹 관리")
    
    col1, col2 = st.columns(2)
    with col1:
        new_group = st.text_input("새로운 관심그룹 이름")
        if st.button("그룹 추가"):
            if new_group and new_group not in watchlists:
                watchlists[new_group] = []
                save_watchlists(watchlists)
                st.success(f"'{new_group}' 그룹 추가 완료! (새로고침 해주세요)")
                st.rerun()

    with col2:
        if watchlists:
            del_group = st.selectbox("삭제할 그룹 선택", list(watchlists.keys()))
            if st.button("그룹 삭제"):
                if del_group in watchlists:
                    del watchlists[del_group]
                    save_watchlists(watchlists)
                    st.success(f"'{del_group}' 그룹 삭제 완료! (새로고침 해주세요)")
                    st.rerun()
                    
    st.divider()
    
    if watchlists:
        mng_group = st.selectbox("관리할 관심그룹 선택", list(watchlists.keys()))
        
        col_add, col_list = st.columns([1, 2])
        with col_add:
            new_t = st.text_input("추가할 종목 티커 (예: SOXL)").upper().strip()
            if st.button("종목 추가"):
                if new_t and new_t not in watchlists[mng_group]:
                    watchlists[mng_group].append(new_t)
                    save_watchlists(watchlists)
                    st.success(f"{new_t} 추가 완료!")
                    st.rerun()
                    
        with col_list:
            st.write(f"**[{mng_group}] 등록된 종목 ({len(watchlists[mng_group])}개)**")
            if not watchlists[mng_group]:
                st.info("등록된 종목이 없습니다.")
            else:
                for t in watchlists[mng_group]:
                    c1, c2 = st.columns([4, 1])
                    name = UNIVERSE_DICT.get(t, "사용자 추가 종목")
                    c1.write(f"- {t} ({name})")
                    if c2.button("삭제", key=f"del_{mng_group}_{t}"):
                        watchlists[mng_group].remove(t)
                        save_watchlists(watchlists)
                        st.rerun()

with tab_scan:
"""

# Replace UI setting area
content = content.replace(
    "# --- UI 세팅 ---\n"
    "st.title(\"🎯 Z-Hunter Web Scanner\")\n"
    "st.markdown(\"Z-Score와 ADX를 활용한 **평균회귀 전략(Mean Reversion)** 최적화 종목 검색기입니다. 50개의 주요 미국 자산 유니버스를 스캔합니다.\")\n",
    ui_code
)

sidebar_old = """st.sidebar.header("⚙️ 스캐너 설정")
initial_capital = st.sidebar.number_input("초기 투자금 (원)", min_value=100000, value=10000000, step=1000000, format="%d")
period = st.sidebar.selectbox("테스트할 기간 선택", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y"], index=4) # 기본 3y"""

sidebar_new = """st.sidebar.header("⚙️ 스캐너 설정")
scan_target = st.sidebar.selectbox("스캔 대상 선택", ["기본 유니버스 (50종목)"] + list(watchlists.keys()))
initial_capital = st.sidebar.number_input("초기 투자금 (원)", min_value=100000, value=10000000, step=1000000, format="%d")
period = st.sidebar.selectbox("테스트할 기간 선택", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y"], index=4) # 기본 3y"""

content = content.replace(sidebar_old, sidebar_new)

scan_logic_old = """    results = []
    tickers = list(UNIVERSE_DICT.keys())
    total_tickers = len(tickers)"""

scan_logic_new = """    results = []
    if scan_target == "기본 유니버스 (50종목)":
        tickers = list(UNIVERSE_DICT.keys())
    else:
        tickers = watchlists[scan_target]

    total_tickers = len(tickers)
    
    if total_tickers == 0:
        st.warning("선택한 그룹에 종목이 없습니다.")
        st.stop()"""

content = content.replace(scan_logic_old, scan_logic_new)

# Fix indentation if necessary, but string replacement handles it because python whitespace matters!
# Let's ensure the indentation of tab_scan content is correct.
# Actually, since with tab_scan: is introduced, the content under it needs to be indented.
# A simpler way: we don't strictly need to indent EVERYTHING under with tab_scan as long as we structure it properly,
# Wait, Python requires indentation for the block under 'with tab_scan:'. 
# So `st.sidebar...` and `if st.button...` don't need to be strictly under `with tab_scan:` if we just put the results inside `tab_scan`.
# Let's rewrite the replacement carefully.
