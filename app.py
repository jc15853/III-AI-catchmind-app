import os
import random
import time
import pandas as pd
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas

# -----------------------------------------------------------------------------
# 0. 페이지 설정 및 정보 교과 테마 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="정보 교과: 추상화 게임",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stButton>button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.2rem !important;
        font-weight: bold;
        border-radius: 12px;
    }
    .big-title {
        text-align: center;
        font-size: 2.3rem;
        font-weight: 800;
        color: #00838F;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        text-align: center;
        font-size: 1.1rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .result-text-big {
        font-size: 1.3rem !important;
        font-weight: bold;
        line-height: 1.8;
    }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 세션 상태(Session State) 초기화
# -----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "start"
if "category" not in st.session_state:
    st.session_state.category = None
if "total_target_questions" not in st.session_state:
    st.session_state.total_target_questions = 5
if "quiz_pool" not in st.session_state:
    st.session_state.quiz_pool = []
if "current_pool_idx" not in st.session_state:
    st.session_state.current_pool_idx = 0
if "solved_count" not in st.session_state:
    st.session_state.solved_count = 0
if "pass_count" not in st.session_state:
    st.session_state.pass_count = 0
if "history" not in st.session_state:
    st.session_state.history = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None


def render_top_bar():
    c1, c2 = st.columns([6, 1])
    with c1:
        st.markdown("#### 🧩 AI 추상화 핵심 특징 추출 챌린지")
    with c2:
        if st.button("🏠 처음으로", key="top_home_btn"):
            st.session_state.page = "start"
            st.session_state.category = None
            st.session_state.history = []
            st.session_state.last_result = None
            st.rerun()
    st.divider()


# -----------------------------------------------------------------------------
# 키워드 CSV 로드 및 AI 심사 헬퍼 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_keywords():
    file_path = "keyword.csv"
    if os.path.exists(file_path):
        try:
            for enc in ["utf-8-sig", "cp949", "euc-kr"]:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            
            df.columns = [str(col).strip().lower() for col in df.columns]
            rename_map = {}
            for col in df.columns:
                if "카테고리" in col or "cat" in col:
                    rename_map[col] = "category"
                elif "키워드" in col or "word" in col or "제시어" in col:
                    rename_map[col] = "keyword"
            df = df.rename(columns=rename_map)
            return df
        except Exception as e:
            st.error(f"⚠️ keyword.csv 오류: {e}")
            return None
    else:
        st.error("⚠️ 'keyword.csv' 파일이 없습니다!")
        return None


def ask_gemini_vision(pil_image, keyword, category):
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False, "API 키 설정 필요 (Secrets 확인)"

    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())

        prompt = (
            f"당신은 정보 교과(컴퓨팅 사고력)의 '추상화' 개념을 평가하는 엄격한 AI 심사위원입니다.\n"
            f"교과서 정의: '추상화란 불필요한 것을 없애고, 문제 해결에 반드시 필요한 요소만을 뽑아 문제 해결 방법을 찾는 것이다.'\n\n"
            f"카테고리: '{category}' / 목표 개념(제시어): '{keyword}'\n\n"
            f"사용자가 그린 그림이 위 정의에 따라 불필요한 것을 없애고 제시어('{keyword}')의 핵심 요소를 제대로 뽑아냈는지 엄격하게 평가해주세요.\n"
            f"반드시 아래 형식으로만 답변해주세요.\n"
            f"판정: [성공 또는 실패 중 하나만 작성]\n"
            f"설명: [핵심 내용 위주로 한두 문장으로 짧게 설명]"
        )

        response = client.models.generate_content(
            model="gemini-3.8-flash", contents=[pil_image, prompt]
        )
        if response and response.text:
            text = response.text.strip()
            is_success = "판정: 성공" in text or "성공" in text.split("\n")[0]
            return is_success, text
    except Exception as e:
        return False, f"통신 오류 발생: {str(e)}"

    return False, "판정 불가"


# -----------------------------------------------------------------------------
# 1. 화면 1: 시작 화면
# -----------------------------------------------------------------------------
if st.session_state.page == "start":
    st.title("🧩 AI 추상화 핵심 특징 추출 챌린지")
    st.caption("중1 정보 [2. 문제해결과 프로그래밍] - 복잡한 대상에서 핵심 특징만 추출하는 컴퓨팅 사고력 학습기")

    with st.expander("📖 교육과정 학습 목표 및 정의 안내", expanded=True):
        st.markdown("""
            🤖 **정보 교과 [문제해결과 프로그래밍 - 추상화]**  
            💡 **추상화:** 불필요한 것을 없애고, 문제 해결에 반드시 필요한 요소만을 뽑아 문제 해결 방법을 찾는 것
            """)

    st.write("")
    df_keywords = load_keywords()

    if df_keywords is not None:
        st.write("### 1. 문제 수 입력")
        target_q = st.number_input(
            "풀고 싶은 문제 수를 입력하세요 (1~20):",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
        )

        st.write("### 2. 카테고리 선택")
        categories = ["동물", "과일", "채소", "사물", "교통수단"]
        cols = st.columns(5)

        for idx, cat in enumerate(categories):
            with cols[idx]:
                if st.button(f"{cat}", key=f"cat_btn_{idx}"):
                    filtered = df_keywords[df_keywords["category"] == cat]["keyword"].tolist()
                    required_count = target_q

                    if len(filtered) < required_count:
                        st.error(f"'{cat}' 카테고리 키워드가 부족합니다 (요청: {required_count}개, 보유: {len(filtered)}개).")
                    else:
                        st.session_state.category = cat
                        st.session_state.total_target_questions = target_q
                        st.session_state.quiz_pool = random.sample(filtered, required_count)
                        st.session_state.current_pool_idx = 0
                        st.session_state.solved_count = 0
                        st.session_state.pass_count = 0
                        st.session_state.history = []
                        st.session_state.start_time = time.time()
                        st.session_state.page = "game"
                        st.rerun()

# -----------------------------------------------------------------------------
# 2. 화면 2: 게임 화면 (안전한 Drawing Canvas 연동)
# -----------------------------------------------------------------------------
elif st.session_state.page == "game":
    render_top_bar()

    pool_idx = st.session_state.current_pool_idx
    keyword = st.session_state.quiz_pool[pool_idx]
    category = st.session_state.category
    target_q = st.session_state.total_target_questions
    solved_q = st.session_state.solved_count
    pass_used = st.session_state.pass_count

    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, int(60 - elapsed_time))
    is_time_over = remaining_time == 0

    col1, col2, col3 = st.columns([1.2, 2, 1.2])
    with col1:
        st.markdown(f"#### 추상화 문제 **{solved_q + 1} / {target_q}**")
        st.caption(f"패스 찬스: {2 - pass_used}회 남음")
    with col2:
        st.markdown(
            f"<h3 style='text-align: center; color: #00838F;'>추상화 대상(제시어): <b>[{keyword}]</b></h3>",
            unsafe_allow_html=True,
        )
    with col3:
        timer_color = "red" if remaining_time <= 10 else "#333333"
        st.markdown(
            f"<h4 style='text-align: right; color: {timer_color};'>⏱️ 남은 시간: {remaining_time}초</h4>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.info("💡 아래 그림판에 마우스나 터치로 직접 그림을 그린 후 **[제출하기]**를 눌러주세요!")

    # 펜 컨트롤 툴바
    t_col1, t_col2 = st.columns([1, 1])
    with t_col1:
        stroke_color = st.color_picker("펜 색상", "#000000", key=f"color_{pool_idx}")
    with t_col2:
        stroke_width = st.slider("선 두께", 1, 25, 6, key=f"width_{pool_idx}")

    # 인-앱 드로잉 캔버스 컴포넌트
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color="#FFFFFF",
        height=380,
        width=850,
        drawing_mode="freedraw",
        key=f"canvas_{pool_idx}",
    )

    def process_pass():
        st.session_state.pass_count += 1
        st.session_state.current_pool_idx += 1
        st.session_state.start_time = time.time()
        st.rerun()

    st.write("")
    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
        if st.button("🧩 추상화 결과 제출하기", key=f"btn_submit_{pool_idx}", use_container_width=True):
            pil_img = None

            # RuntimeError를 원천 예방하는 안전한 접근방식
            try:
                # 캔버스 객체의 __dict__를 조회하여 RuntimeError 유발 속성을 건너뜀
                raw_data = getattr(canvas_result, "image_data", None)
                if raw_data is not None:
                    pil_img = Image.fromarray(raw
