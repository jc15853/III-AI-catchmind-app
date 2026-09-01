import os
import time
import random
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

st.markdown("""
<style>
    /* 버튼 스타일 정의 */
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
        color: #1E88E5;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        text-align: center;
        font-size: 1.1rem;
        color: #666666;
        margin-bottom: 1.5rem;
    }
    
    /* 팔레트 색상 전용 버튼 */
    .color-btn-black button { background-color: #000000 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    .color-btn-red button { background-color: #E53935 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    .color-btn-blue button { background-color: #1E88E5 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    .color-btn-green button { background-color: #43A047 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    
    /* 결과 및 중간 화면 대형 텍스트 */
    .result-text-big {
        font-size: 1.4rem !important;
        font-weight: bold;
        line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. 세션 상태(Session State) 초기화
# -----------------------------------------------------------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'start'  # 'start', 'game', 'intermediate', 'result'
if 'category' not in st.session_state:
    st.session_state.category = None
if 'total_target_questions' not in st.session_state:
    st.session_state.total_target_questions = 5
if 'quiz_pool' not in st.session_state:
    st.session_state.quiz_pool = []
if 'current_pool_idx' not in st.session_state:
    st.session_state.current_pool_idx = 0
if 'solved_count' not in st.session_state:
    st.session_state.solved_count = 0
if 'pass_count' not in st.session_state:
    st.session_state.pass_count = 0
if 'history' not in st.session_state:
    st.session_state.history = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'selected_color' not in st.session_state:
    st.session_state.selected_color = "#000000"
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

# -----------------------------------------------------------------------------
# 2. 헬퍼 함수 정의
# -----------------------------------------------------------------------------
@st.cache_data
def load_keywords():
    """keyword.csv 파일 로드"""
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
    """Gemini Client 생성"""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 설정되어 있지 않습니다.")
        return None
    return genai.Client(api_key=api_key)

def ask_gemini(pil_image, category):
    """Gemini-2.5-flash 모델 호출"""
    client = get_gemini_client()
    if not client:
        return "통신에 실패했습니다"

    prompt = (
        f"당신은 캐치마인드 게임의 정답을 맞히는 AI입니다. 제시된 카테고리는 '{category}'입니다.\n"
        f"사용자가 그린 그림의 전체적인 '형태'와 '윤곽'에 집중해서 무엇을 그린 것인지 정답을 추론해 주세요.\n"
        f"★주의사항: 부연 설명 없이 오직 카테고리와 관련된 '한 단어'(예: 사과, 호랑이, 연필 등)로만 답변해 주세요."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[pil_image, prompt]
        )
        return response.text.strip()
    except Exception:
        return "통신에 실패했습니다"

# -----------------------------------------------------------------------------
# 3. 화면 1: 시작 화면 (안내 및 카테고리 선택)
# -----------------------------------------------------------------------------
if st.session_state.page == 'start':
    st.markdown("<div class='big-title'>🎨 AI 캐치마인드</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>내가 그린 그림을 AI가 맞힐 수 있을까요?</div>", unsafe_allow_html=True)

    # 📌 게임 안내 (시작 화면에만 깔끔하게 배치)
    with st.expander("📖 **게임 방법 및 규칙 안내**", expanded=True):
        st.markdown("""
        1. **목표:** 제한 시간(60초) 동안 화면에 나오는 제시어를 그림으로 표현하세요.
        2. **제출:** 그림을 다 그린 후 `제출하기`를 누르면 AI가 그림을 분석해 정답을 맞힙니다.
        3. **패스 기능:** 그림을 그리기 어렵다면 한 게임당 최대 **2회**까지 패스할 수 있습니다.
        4. **주의:** 불필요한 배경보다는 그림의 **‘핵심 형태’**를 강조해 주세요!
        """)

    st.write("")
    df_keywords = load_keywords()
    
    if df_keywords is not None:
        st.write("### ⚙️ 1. 도전할 문항 수")
        target_q = st.select_slider("문항 수 선택:", options=[3, 5, 7, 10], value=5, label_visibility="collapsed")
        
        st.write("### 📌 2. 카테고리 선택하여 시작")
        categories = ["동물", "과일", "채소", "사물", "교통수단"]
        cols = st.columns(5)
        
        for idx, cat in enumerate(categories):
            with cols[idx]:
                if st.button(f"{cat}", key=f"cat_btn_{idx}"):
                    filtered = df_keywords[df_keywords['카테고리'] == cat]['키워드'].tolist()
                    required_count = target_q + 2  # 패스 2회 대비
                    
                    if len(filtered) < required_count:
                        st.error(f"'{cat}' 카테고리의 키워드가 부족합니다 (최소 {required_count}개 필요).")
                    else:
                        st.session_state.category = cat
                        st.session_state.total_target_questions = target_q
                        # ⚠️ 중복 방지: 키워드 풀 전체를 무작위로 한 번만 추출
                        st.session_state.quiz_pool = random.sample(filtered, required_count)
                        st.session_state.current_pool_idx = 0
                        st.session_state.solved_count = 0
                        st.session_state.pass_count = 0
                        st.session_state.history = []
                        st.session_state.start_time = time.time()
                        st.session_state.page = 'game'
                        st.rerun()

# -----------------------------------------------------------------------------
# 4. 화면 2: 게임 화면 (넓어진 캔버스 & 인터페이스)
# -----------------------------------------------------------------------------
elif st.session_state.page == 'game':
    pool_idx = st.session_state.current_pool_idx
    keyword = st.session_state.quiz_pool[pool_idx]
    category = st.session_state.category
    target_q = st.session_state.total_target_questions
    solved_q = st.session_state.solved_count
    pass_used = st.session_state.pass_count

    # 타이머 (60초)
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, int(60 - elapsed_time))
    is_time_over = (remaining_time == 0)

    # 상단 요약 바 (가독성 중심으로 간결하게)
    col1, col2, col3 = st.columns([1.2, 2, 1.2])
    with col1:
        st.markdown(f"#### 🎯 문제 **{solved_q + 1} / {target_q}**")
        st.caption(f"🎟️ 패스 남은 횟수: {2 - pass_used}회")
    with col2:
        st.markdown(f"<h3 style='text-align: center; color: #D32F2F;'>제시어: <b>[{keyword}]</b></h3>", unsafe_allow_html=True)
    with col3:
        timer_color = "red" if remaining_time <= 10 else "#333333"
        st.markdown(f"<h4 style='text-align: right; color: {timer_color};'>⏱️ {remaining_time}초</h4>", unsafe_allow_html=True)

    st.write("")

    # 🎨 팔레트 설정 (4가지 선호 색상 + 커스텀 피커)
    p_col1, p_col2, p_col3, p_col4, p_col5, p_col6 = st.columns([1, 1, 1, 1, 1.5, 2])
    
    with p_col1:
        st.markdown("<div class='color-btn-black'>", unsafe_allow_html=True)
        if st.button("검정", key="btn_black", disabled=is_time_over):
            st.session_state.selected_color = "#000000"
        st.markdown("</div>", unsafe_allow_html=True)
    with p_col2:
        st.markdown("<div class='color-btn-red'>", unsafe_allow_html=True)
        if st.button("빨강", key="btn_red", disabled=is_time_over):
            st.session_state.selected_color = "#E53935"
        st.markdown("</div>", unsafe_allow_html=True)
    with p_col3:
        st.markdown("<div class='color-btn-blue'>", unsafe_allow_html=True)
        if st.button("파랑", key="btn_blue", disabled=is_time_over):
            st.session_state.selected_color = "#1E88E5"
        st.markdown("</div>", unsafe_allow_html=True)
    with p_col4:
        st.markdown("<div class='color-btn-green'>", unsafe_allow_html=True)
        if st.button("초록", key="btn_green", disabled=is_time_over):
            st.session_state.selected_color = "#43A047"
        st.markdown("</div>", unsafe_allow_html=True)
    with p_col5:
        custom_color = st.color_picker("기타 색상", st.session_state.selected_color, disabled=is_time_over, label_visibility="collapsed")
        if custom_color != st.session_state.selected_color:
            st.session_state.selected_color = custom_color
    with p_col6:
        stroke_width = st.slider("두께", 3, 25, 8, disabled=is_time_over, label_visibility="collapsed")

    # 🖌️ 캔버스 (가로 900px로 확장)
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=stroke_width,
        stroke_color=st.session_state.selected_color,
        background_color="#FFFFFF",
        height=400,
        width=900,  # 태블릿 화면 맞춤 확장
        drawing_mode="freedraw" if not is_time_over else "transform",
        key=f"canvas_p{pool_idx}",
    )

    # 제출 처리 함수
    def process_submission(image_data):
        with st.spinner("🤖 AI가 그림을 분석 중입니다..."):
            pil_img = Image.fromarray(image_data.astype('uint8'), 'RGBA').convert('RGB')
            ai_ans = ask_gemini(pil_img, category)
            is_correct = (keyword.strip() == ai_ans.strip())

            result_data = {
                'round': solved_q + 1,
                'keyword': keyword,
                'image': pil_img,
                'ai_response': ai_ans,
                'is_correct': is_correct
            }

            st.session_state.history.append(result_data)
            st.session_state.last_result = result_data
            
            st.session_state.solved_count += 1
            st.session_state.current_pool_idx += 1
            st.session_state.page = 'intermediate'  # 중간 채점 화면으로 이동
            st.rerun()

    # 패스 처리 함수
    def process_pass():
        st.session_state.pass_count += 1
        st.session_state.current_pool_idx += 1  # 키워드 풀의 다음 순번으로 이동 (중복 방지)
        st.session_state.start_time = time.time()
        st.rerun()

    # 하단 버튼 그룹
    st.write("")
    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
        if st.button("🚀 제출하기", key="btn_submit"):
            if canvas_result.image_data is not None:
                process_submission(canvas_result.image_data)
            else:
                st.warning("그림을 먼저 그려주세요!")

    with btn_col2:
        pass_disabled = (pass_used >= 2)
        if st.button(f"⏩ 패스하기 ({pass_used}/2회 사용)", key="btn_pass", disabled=pass_disabled):
            process_pass()

    if is_time_over:
        st.error("⏰ 시간이 종료되었습니다! 제출하기를 눌러주세요.")

    if not is_time_over:
        time.sleep(1)
        st.rerun()

# -----------------------------------------------------------------------------
# 5. 화면 3: 중간 채점 화면 (각 라운드 결과 즉시 확인)
# -----------------------------------------------------------------------------
elif st.session_state.page == 'intermediate':
    res = st.session_state.last_result
    st.markdown(f"### 📍 문제 {res['round']} 결과 확인")
    
    col_img, col_info = st.columns([1, 1.2])
    
    with col_img:
        # 태블릿 화면에서 한눈에 들도록 적당한 너비(320px)로 조절
        st.image(res['image'], caption="내가 그린 그림", width=320)

    with col_info:
        st.write("")
        if res['is_correct']:
            st.success("🎉 **정답입니다!** AI가 그림을 완벽히 이해했습니다!")
        else:
            st.error("❌ **아쉽네요!** AI가 다른 단어로 생각했습니다.")

        st.markdown(f"""
        <div class="result-text-big" style="background-color: #F8F9FA; padding: 20px; border-radius: 12px; margin-top: 10px;">
            • 🎯 <b>정답 (제시어):</b> <span style="color: #1565C0;">{res['keyword']}</span><br>
            • 🤖 <b>AI의 응답:</b> <span style="color: #D32F2F;">{res['ai_response']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.write("")
        
        # 다음 단계 버튼
        if st.session_state.solved_count >= st.session_state.total_target_questions:
            if st.button("🏆 최종 결과 보기"):
                st.session_state.page = 'result'
                st.rerun()
        else:
            if st.button("➡️ 다음 문제로 넘어가지"):
                st.session_state.start_time = time.time()
                st.session_state.page = 'game'
                st.rerun()

# -----------------------------------------------------------------------------
# 6. 화면 4: 최종 결과 화면
# -----------------------------------------------------------------------------
elif st.session_state.page == 'result':
    st.markdown("<div class='big-title'>🎉 게임 종료! 최종 결과 보고서</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>카테고리: <b>{st.session_state.category}</b> | 패스 사용: <b>{st.session_state.pass_count}회</b></div>", unsafe_allow_html=True)

    correct_cnt = sum(1 for item in st.session_state.history if item.get('is_correct', False))
    st.metric("총 맞힌 문제 수", f"{correct_cnt} / {st.session_state.total_target_questions} 문제")
    st.divider()

    for item in st.session_state.history:
        is_correct = item['is_correct']
        bg_color = "#E8F5E9" if is_correct else "#FFEBEE"
        border_color = "#4CAF50" if is_correct else "#EF5350"
        status_badge = "🟢 **[정답]**" if is_correct else "🔴 **[오답]**"

        with st.container():
            st.markdown(f"""
            <div style='background-color: {bg_color}; padding: 12px 20px; border-radius: 12px; border-left: 8px solid {border_color}; margin-bottom: 10px;'>
                <h4>📍 문제 {item['round']} {status_badge}</h4>
            </div>
            """, unsafe_allow_html=True)

            r_col1, r_col2 = st.columns([1, 2])
            
            with r_col1:
                # 태블릿 한눈에 들어오는 알맞은 스냅샷 크기 지정
                st.image(item['image'], width=280)
            
            with r_col2:
                st.markdown(f"""
                <div class="result-text-big">
                    • 🎯 <b>정답:</b> <span style="color: #1565C0;">{item['keyword']}</span><br>
                    • 🤖 <b>AI 응답:</b> <span style="color: #D32F2F;">{item['ai_response']}</span>
                </div>
                """, unsafe_allow_html=True)
            st.divider()

    if st.button("🔄 다시 게임하기", key="btn_restart"):
        st.session_state.page = 'start'
        st.session_state.category = None
        st.session_state.history = []
        st.rerun()
