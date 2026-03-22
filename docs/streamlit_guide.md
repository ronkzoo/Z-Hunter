# Streamlit 핵심 가이드 (기술 문서)

## 1. Streamlit 개요
Streamlit은 데이터 과학자와 머신러닝 엔지니어들이 Python 스크립트만으로 빠르고 쉽게 대화형 웹 애플리케이션을 구축할 수 있게 해주는 오픈소스 프레임워크입니다. HTML, CSS, JavaScript 같은 프론트엔드 지식 없이도 Python 코드만으로 풍부한 UI를 구성할 수 있다는 것이 가장 큰 특징입니다.

## 2. Streamlit의 핵심 특징 및 작동 방식

### 2.1 Top-down 실행 구조 (가장 중요한 특징)
- **전체 재실행 (Rerun):** 사용자가 버튼을 클릭하거나, 입력값을 변경하는 등 **UI 모션이 발생할 때마다 파이썬 스크립트 전체가 위에서부터 아래로 다시 실행(Rerun)됩니다.**
- **상태 초기화:** 스크립트가 위에서부터 다시 실행되므로, 일반적인 변수들은 버튼 클릭 시마다 초기값으로 리셋됩니다.
- 이 특성 때문에 값을 유지하기 위해서는 반드시 **Session State (세션 상태)** 메커니즘을 사용해야 합니다.

### 2.2 직관적인 위젯 (Widgets)
웹 앱의 요소를 선언하는 동시에 반환값을 얻어낼 수 있습니다.
```python
import streamlit as st

# UI 렌더링과 동시에 변수 할당
user_input = st.text_input("이름을 입력하세요", "홍길동")
if st.button("인사하기"):
    st.write(f"안녕하세요, {user_input}님!")
```

### 2.3 레이아웃 컨트롤
`st.columns`, `st.expander`, `st.tabs`, `st.container` 등을 이용해 화면 배치를 간단하게 제어할 수 있습니다.
```python
col1, col2 = st.columns(2)
with col1:
    st.header("왼쪽 영역")
with col2:
    st.header("오른쪽 영역")
```

## 3. 핵심 기술 및 사용법

### 3.1 상태 관리 (Session State)
Streamlit 앱에서 "Rerun(재실행)" 간에 데이터를 유지하려면 `st.session_state`라는 딕셔너리(사전)를 활용해야 합니다.
*(Z-Hunter에서 선택된 종목, 현재 활성화된 탭 등을 기억하기 위해 핵심적으로 사용 중입니다.)*

```python
# 1. 초기값 설정
if "counter" not in st.session_state:
    st.session_state.counter = 0

# 2. 버튼 클릭 시 값 업데이트
if st.button("카운터 증가"):
    st.session_state.counter += 1

# 3. 화면에 표시 (버튼을 눌러 스크립트가 재실행되어도 값이 유지됨)
st.write(f"현재 카운트: {st.session_state.counter}")
```

### 3.2 데이터 캐싱 (@st.cache_data)
API 요청, 데이터베이스 쿼리, 무거운 연산(예: 백테스트) 등은 매번 Rerun 될 때마다 실행되면 속도가 매우 느려집니다.
이를 방지하기 위해 로딩 결과를 메모리에 저장해두는 데코레이터가 `@st.cache_data` 입니다.
* Z-Hunter에서는 야후 파이낸스 데이터 다운로드와 연산 시 매번 트래픽을 아끼기 위해 사용됩니다.

```python
import time

@st.cache_data(ttl=3600)  # 결과를 1시간(3600초) 동안 보관
def heavy_computation(x):
    time.sleep(5)  # 5초 소요되는 무거운 작업
    return x * 2

# 첫 번째 실행은 5초가 걸리지만, 두 번째부터는 0초만에 반환됩니다.
result = heavy_computation(10)
```
> **주의:** 반환되는 객체가 Pandas DataFrame이나 JSON 형태처럼 복사 가능한 객체일 때 `cache_data`를 사용하며, DB 연결 객체나 텐서플로우 세션 같은 글로벌 리소스는 `@st.cache_resource`를 사용합니다.

### 3.3 대화형 데이터 표 표시 (Dataframe on_select)
Streamlit의 `st.dataframe`은 버전이 업데이트됨에 따라 사용자의 클릭 이벤트를 감지할 수 있게 되었습니다.

```python
# Z-Hunter 상세 거래내역 클릭에서 사용되는 방식
event = st.dataframe(
    df,
    on_select="rerun",           # 선택 시 앱을 재실행
    selection_mode="single-row"  # 단일 행 선택
)

# 선택된 행의 인덱스 가져오기
if len(event.selection['rows']) > 0:
    selected_idx = event.selection['rows'][0]
    st.write(f"선택한 데이터: {df.iloc[selected_idx]}")
```
- 사용자가 데이터프레임의 행을 클릭하면 `on_select="rerun"` 옵션에 의해 스크립트가 재실행되며, `event.selection` 객체에 클릭된 정보가 담겨서 내려옵니다.

## 4. Z-Hunter 아키텍처 관점에서의 적용
1. **app.py (UI 계층):**
   - 사용자의 위젯 입력값(기간, 자본금 등)을 받아옵니다.
   - `st.session_state`를 이용해 화면을 이동할 객체들을 저장하고 로드합니다.
   - `st.plotly_chart`를 통해 인터랙티브한 차트를 그립니다.
2. **data/loader.py (Data & Logic 계층):**
   - `@st.cache_data`로 감싸진 함수들이 백테스트나 지표 연산을 담당하며 캐싱의 혜택을 봅니다.
   - UI에서 받은 손절 타겟 등의 파라미터를 넘겨주어 순수 Python 로직(RegimeRiskManager)을 실행시킵니다.

## 5. 결론 및 주의사항
Streamlit은 "매 동작마다 파이썬 파일 전체가 위에서 아래로 처음부터 다시 실행된다"는 컨셉만 완벽히 이해하면 쉽습니다. 이 개념을 우회하기 위해 존재하는 것이 **Session State(상태 유지)**와 **캐싱(연산 건너뛰기)** 입니다.
UI가 꼬이거나 데이터가 사라진다면 가장 먼저 이 Top-Down Rerun 메커니즘을 떠올려야 합니다.
