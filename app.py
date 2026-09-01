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
    .color-btn-black button { background-color: #000000 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    .color-btn-red button { background-color: #E53935 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    .color-btn-blue button { background-color: #1E88E5 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
    .color-btn-green button { background-color: #43A047 !important; color: white !important; height: 2.8rem; border-radius: 8px; }
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
if "selected_color" not in st.session_state:
  st.session_state.selected_color = "#000000"
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
      return pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
      return pd.read_csv(file_path, encoding="cp949")
  else:
    st.error(
        "⚠️ 'keyword.csv' 파일이 같은 폴더에 존재하지 않습니다! 파일을 확인해 주세요."
    )
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
        f"설명: [장점과 보완점 같은 복잡한 내용은 제외하고, 핵심 내용 위주로 한두 문장으로 짧게 설명]"
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash", contents=[pil_image, prompt]
    )
    if response and response.text:
      text = response.text.strip()
      is_success = False
      if "판정: 성공" in text or "성공" in text.split("\n")[0]:
        is_success = True
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
        
        학습 목표: 제시된 대상에서 불필요한 디테일은 없애고, 본질적인 핵심 요소만 간결하게 그려 표현해 봅시다!
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
          filtered = df_keywords[df_keywords["카테고리"] == cat]["키워드"].tolist()
          required_count = target_q + 2

          if len(filtered) < required_count:
            st.error(
                f"'{cat}' 카테고리의 키워드가 부족합니다 (요청하신 문제 수에 맞추려면 최소 {required_count}개가 필요합니다). 입력한 문제 수를 낮추거나 키워드를 추가해 주세요."
            )
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
# 2. 화면 2: 게임 화면
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
        f"<h4 style='text-align: right; color: {timer_color};'>⏱️ {remaining_time}초</h4>",
        unsafe_allow_html=True,
    )

  st.write("")

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
    custom_color = st.color_picker(
        "기타 색상",
        st.session_state.selected_color,
        disabled=is_time_over,
        label_visibility="collapsed",
    )
    if custom_color != st.session_state.selected_color:
      st.session_state.selected_color = custom_color
  with p_col6:
    stroke_width = st.slider(
        "선 두께", 3, 25, 8, disabled=is_time_over, label_visibility="collapsed"
    )

  canvas_result = st_canvas(
      fill_color="rgba(255, 255, 255, 1)",
      stroke_width=stroke_width,
      stroke_color=st.session_state.selected_color,
      background_color="#FFFFFF",
      height=400,
      width=900,
      drawing_mode="freedraw" if not is_time_over else "transform",
      key=f"canvas_p{pool_idx}",
  )


  def process_submission(image_data):
    with st.spinner("🔍 AI가 추상화(핵심 특징 추출) 결과를 분석 중입니다..."):
      pil_img = Image.fromarray(image_data.astype("uint8")).convert("RGB")
      is_success, ai_ans = ask_gemini_vision(pil_img, keyword, category)

      has_error = "통신 오류" in ai_ans or "API 키" in ai_ans
      if has_error:
        is_success = False

      result_data = {
          "round": solved_q + 1,
          "keyword": keyword,
          "image": pil_img,
          "ai_response": ai_ans,
          "is_success": is_success,
      }

      st.session_state.history.append(result_data)
      st.session_state.last_result = result_data

      st.session_state.solved_count += 1
      st.session_state.current_pool_idx += 1
      st.session_state.page = "intermediate"
      st.rerun()


  def process_pass():
    st.session_state.pass_count += 1
    st.session_state.current_pool_idx += 1
    st.session_state.start_time = time.time()
    st.rerun()


  st.write("")
  btn_col1, btn_col2 = st.columns([1, 1])

  with btn_col1:
    if st.button("🧩 추상화 결과 제출하기", key="btn_submit"):
      if canvas_result.image_data is not None:
        process_submission(canvas_result.image_data)
      else:
        st.warning("캔버스에 핵심 특징을 그려주세요!")

  with btn_col2:
    pass_disabled = pass_used >= 2
    if st.button(
        f"⏩ 패스하기 ({pass_used}/2회 사용)",
        key="btn_pass",
        disabled=pass_disabled,
    ):
      process_pass()

  if is_time_over:
    st.error("시간이 종료되었습니다. 제출하기를 눌러주세요.")

  if not is_time_over:
    time.sleep(1)
    st.rerun()

# -----------------------------------------------------------------------------
# 3. 화면 3: 중간 평가 화면
# -----------------------------------------------------------------------------
elif st.session_state.page == "intermediate":
  render_top_bar()

  res = st.session_state.last_result
  if res is None:
    st.session_state.page = "start"
    st.rerun()

  round_num = res.get("round", 1)
  img = res.get("image")
  kw = res.get("keyword", "")
  ai_res = res.get("ai_response", "")
  is_success = res.get("is_success", False)

  st.markdown(f"### 📋 [문제 {round_num}] 추상화 분석 결과")

  col_img, col_info = st.columns([1, 1.2])

  with col_img:
    if img:
      st.image(img, caption="내가 표현한 그림", width=320)

  with col_info:
    st.write("")
    if is_success:
      st.success("✨ 핵심 특징 추출(추상화) 성공!")
    else:
      st.error("⚠️ 핵심 특징 추출 실패 (다시 도전해 보세요!)")

    st.markdown(
        f"""
        <div class="result-text-big" style="background-color: #E0F2F1; padding: 20px; border-radius: 12px; margin-top: 10px; border-left: 6px solid #00838F;">
            • 목표 제시어: <span style="color: #00838F;"><b>{kw}</b></span><br><br>
            • <b>AI 분석 결과:</b><br>
            <span style="font-size: 1.1rem; color: #333333; font-weight: normal;">{ai_res}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")

    if st.session_state.solved_count >= st.session_state.total_target_questions:
      if st.button("📊 최종 추상화 학습 결과 보기"):
        st.session_state.page = "result"
        st.rerun()
    else:
      if not is_success:
        b_col1, b_col2 = st.columns(2)
        with b_col1:
          if st.button("🔄 다시 시도하기"):
            st.session_state.history.pop()
            st.session_state.solved_count -= 1
            st.session_state.current_pool_idx -= 1
            st.session_state.start_time = time.time()
            st.session_state.page = "game"
            st.rerun()
        with b_col2:
          if st.button("➡️ 다음 문제 풀기"):
            st.session_state.start_time = time.time()
            st.session_state.page = "game"
            st.rerun()
      else:
        if st.button("➡️ 다음 문제 풀기"):
          st.session_state.start_time = time.time()
          st.session_state.page = "game"
          st.rerun()

# -----------------------------------------------------------------------------
# 4. 화면 4: 최종 결과 화면
# -----------------------------------------------------------------------------
elif st.session_state.page == "result":
  render_top_bar()

  st.markdown(
      "<div class='big-title'>📊 컴퓨팅 사고력 학습 결과 (추상화)</div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='sub-title'>학습 카테고리: <b>{st.session_state.category}</b> | 패스 사용: <b>{st.session_state.pass_count}회</b></div>",
      unsafe_allow_html=True,
  )

  completed_cnt = len(st.session_state.history)
  st.metric("완료된 문항 수", f"{completed_cnt} 문항")
  st.divider()

  for item in st.session_state.history:
    item_success = item.get("is_success", False)
    bg_color = "#E0F2F1" if item_success else "#FFEBEE"
    border_color = "#00838F" if item_success else "#C62828"
    status_label = "성공" if item_success else "실패"

    with st.container():
      st.markdown(
          f"""
            <div style='background-color: {bg_color}; padding: 12px 20px; border-radius: 12px; border-left: 8px solid {border_color}; margin-bottom: 10px;'>
                <h4>🧩 문제 {item.get('round', 1)} - 제시어: [{item.get('keyword', '')}] ({status_label})</h4>
            </div>
            """,
          unsafe_allow_html=True,
      )

      r_col1, r_col2 = st.columns([1, 2])

      with r_col1:
        if "image" in item:
          st.image(item["image"], width=280)

      with r_col2:
        st.markdown(
            f"""
                <div class="result-text-big" style="font-size: 1.1rem !important; font-weight: normal;">
                    <b>🔍 AI 분석 피드백:</b><br>
                    {item.get('ai_response', '')}
                </div>
                """,
            unsafe_allow_html=True,
        )
      st.divider()

  if st.button("🔄 다시 학습하기", key="btn_restart"):
    st.session_state.page = "start"
    st.session_state.category = None
    st.session_state.history = []
    st.rerun()
