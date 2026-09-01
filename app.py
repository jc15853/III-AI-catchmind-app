import os
import time
import random
import io
import pandas as pd
import streamlit as st
from PIL import Image
from google import genai
from streamlit_drawable_canvas import st_canvas

# -----------------------------------------------------------------------------
# 0. 페이지 기본 설정 및 태블릿 맞춤형 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="🎨 AI 캐치마인드",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 태블릿 환경을 고려한 터치 친화적 패딩 및 글씨 크기 설정
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.25rem !important;
        font-weight: bold;
        border-radius: 12px;
    }
    .big-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        font-size: 1.2rem;
        color: #555555;
        margin-bottom: 2rem;
    }
    .card-box {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. 세션 상태(Session State) 초기화
# -----------------------------------------------------------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'start'  # 'start', 'game', 'result'
if 'category' not in st.session_state:
    st.session_state.category = None
if 'quiz_list' not in st.session_state:
    st.session_state.quiz_list = []
if 'current_round' not in st.session_state:
    st.session_state.current_round = 0  # 0~4 (총 5문제)
if 'history' not in st.session_state:
    st.session_state.history = []  # [{round, keyword, image, ai_response}]
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

# -----------------------------------------------------------------------------
# 2. 헬퍼 함수 정의
# -----------------------------------------------------------------------------
@st.cache_data
def load_keywords():
    """keyword.csv 파일을 로드하는 함수"""
    file_path = 'keyword.csv'
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='cp949')
    else:
        st.error("⚠️ 'keyword.csv' 파일이 필요합니다!")
        return None

def get_gemini_client():
    """Streamlit Secrets에서 GEMINI_API_KEY를 받아 Gemini 클라이언트 생성"""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        # 시스템 환경변수에서 예비로 로드 시도
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 설정되어 있지 않습니다.")
        return None
    return genai.Client(api_key=api_key)

def ask_gemini(pil_image, category):
    """Gemini-2.5-flash 모델을 호출하여 그림을 추론하는 함수"""
    client = get_gemini_client()
    if not client:
        return "API키 없음"

    prompt = (
        f"당신은 캐치마인드 게임의 정답을 맞히는 AI입니다. "
        f"제시된 카테고리는 '{category}'입니다.\n"
        f"사용자가 그린 그림의 전체적인 '형태'와 '윤곽'에 집중해서 무엇을 그린 것인지 정답을 추론해 주세요.\n"
        f"★주의사항: 다른 부연 설명이나 문장 없이, 오직 해당 카테고리와 관련된 '한 단어'(예: 사과, 호랑이, 연필 등)로만 답변해 주세요."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[pil_image, prompt]
        )
        return response.text.strip()
    except Exception as e:
        return f"분석 오류 ({str(e)})"

# -----------------------------------------------------------------------------
# 3. 화면 1: 시작 화면 (카테고리 선택)
# -----------------------------------------------------------------------------
if st.session_state.page == 'start':
    st.markdown("<div class='big-title'>🎨 AI 캐치마인드 연구소</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>그림을 그려서 AI에게 마음을 전달해보세요!</div>", unsafe_allow_html=True)

    df_keywords = load_keywords()
    
    if df_keywords is not None:
        categories = ["동물", "과일", "채소", "사물", "교통수단"]
        
        st.write("### 📌 주제 카테고리를 선택해 주세요")
        cols = st.columns(5)
        
        for idx, cat in enumerate(categories):
            with cols[idx]:
                if st.button(f"{cat}", key=f"cat_btn_{idx}"):
                    # 해당 카테고리의 단어 중 5개 무작위 추출
                    filtered = df_keywords[df_keywords['카테고리'] == cat]['키워드'].tolist()
                    if len(filtered) < 5:
                        st.error("해당 카테고리의 키워드가 5개 미만입니다.")
                    else:
                        st.session_state.category = cat
                        st.session_state.quiz_list = random.sample(filtered, 5)
                        st.session_state.current_round = 0
                        st.session_state.history = []
                        st.session_state.start_time = time.time()
                        st.session_state.page = 'game'
                        st.rerun()

# -----------------------------------------------------------------------------
# 4. 화면 2: 게임 화면 (그림판 & AI 추론)
# -----------------------------------------------------------------------------
elif st.session_state.page == 'game':
    current_round = st.session_state.current_round
    keyword = st.session_state.quiz_list[current_round]
    category = st.session_state.category

    # 타이머 계산 (60초 제한)
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, int(60 - elapsed_time))
    is_time_over = (remaining_time == 0)

    # 상단 대시보드
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.markdown(f"#### 🎯 문제 {current_round + 1} / 5")
    with col2:
        st.markdown(f"<h3 style='text-align: center; color: #D32F2F;'>제시어: <b>[{keyword}]</b></h3>", unsafe_allow_html=True)
    with col3:
        if is_time_over:
            st.markdown("<h4 style='text-align: right; color: red;'>⏱️ 시간 종료!</h4>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h4 style='text-align: right;'>⏱️ 남은 시간: {remaining_time}초</h4>", unsafe_allow_html=True)

    st.divider()

    # 캔버스 제어 도구 (그리기 툴 & 펜 굵기/색상)
    c_col1, c_col2, c_col3 = st.columns([2, 2, 1])
    with c_col1:
        stroke_color = st.color_picker("펜 색상 선택", "#000000", disabled=is_time_over)
    with c_col2:
        stroke_width = st.slider("펜 두께", 3, 25, 8, disabled=is_time_over)
    with c_col3:
        drawing_mode = st.selectbox("도구", ["freedraw", "transform"], disabled=is_time_over)

    # 그림판 (캔버스) 생성 - 제한시간 종료 시 Drawing 불가능하도록 처리
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color="#FFFFFF",
        height=380,
        width=700,
        drawing_mode="freedraw" if not is_time_over else "transform",
        key=f"canvas_r{current_round}",
    )

    # 제출 처리 함수
    def process_submission(image_data):
        with st.spinner("🤖 AI가 열심히 그림을 생각 중입니다..."):
            # numpy array (RGBA) -> PIL Image (RGB) 로 변환
            pil_img = Image.fromarray(image_data.astype('uint8'), 'RGBA').convert('RGB')
            
            # Gemini AI 응답 수신
            ai_ans = ask_gemini(pil_img, category)

            # 라운드 데이터 기록
            st.session_state.history.append({
                'round': current_round + 1,
                'keyword': keyword,
                'image': pil_img,
                'ai_response': ai_ans
            })

            # 다음 라운드 이동 또는 결과 화면 전환
            if current_round + 1 < 5:
                st.session_state.current_round += 1
                st.session_state.start_time = time.time()
            else:
                st.session_state.page = 'result'
            st.rerun()

    # 버튼 영역
    st.write("")
    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
        if st.button("🚀 제출하기"):
            if canvas_result.image_data is not None:
                process_submission(canvas_result.image_data)
            else:
                st.warning("그림을 먼저 그려주세요!")

    with btn_col2:
        # 시간 초과 시 자동 처리 안내
        if is_time_over:
            st.error("시간이 초과되었습니다! '제출하기'를 눌러 작성한 그림을 제출해주세요.")

    # 자동 화면 갱신 (1초 마다 타이머 업데이트)
    if not is_time_over:
        time.sleep(1)
        st.rerun()

# -----------------------------------------------------------------------------
# 5. 화면 3: 결과 화면
# -----------------------------------------------------------------------------
elif st.session_state.page == 'result':
    st.markdown("<div class='big-title'>🎉 게임 종료! 결과 보고서</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>선택한 카테고리: <b>{st.session_state.category}</b></div>", unsafe_allow_html=True)

    # 5개의 문제 결과를 카드 형태로 출력
    for idx, item in enumerate(st.session_state.history):
        is_correct = (item['keyword'].strip() == item['ai_response'].strip())
        
        with st.container():
            st.markdown(f"### 📍 라운드 {item['round']}")
            r_col1, r_col2 = st.columns([1, 2])
            
            with r_col1:
                st.image(item['image'], caption=f"라운드 {item['round']} 사용자가 그린 그림", width=250)
            
            with r_col2:
                st.markdown(f"- **정답 (제시어):** `{item['keyword']}`")
                st.markdown(f"- **AI 추론 응답:** `{item['ai_response']}`")
                
                if is_correct:
                    st.success("✅ **성공!** AI가 정답을 맞혔습니다!")
                else:
                    st.error("❌ **아쉬워요!** AI가 정답을 맞히지 못했습니다.")
            st.divider()

    if st.button("🔄 다시 게임하기"):
        st.session_state.page = 'start'
        st.session_state.category = None
        st.session_state.history = []
        st.rerun()
