import os
import random
import time

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# -----------------------------------------------------------------------------
# 0. 페이지 설정 및 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="정보: 추상화 게임",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stButton > button {
            width: 100%;
            min-height: 3rem;
            font-size: 1.05rem !important;
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
            font-size: 1.15rem !important;
            line-height: 1.8;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 1. 세션 상태 초기화
# -----------------------------------------------------------------------------
DEFAULTS = {
    "page": "start",
    "category": None,
    "total_target_questions": 5,
    "quiz_pool": [],
    "current_pool_idx": 0,
    "solved_count": 0,
    "pass_count": 0,
    "history": [],
    "start_time": None,
    "last_result": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def render_top_bar():
    c1, c2 = st.columns([4, 20])
    with c1:
        st.markdown("#### 🧩 추상화 게임")
    with c2:
        if st.button("🏠 처음으로", key="top_home_btn"):
            for key, value in DEFAULTS.items():
                st.session_state[key] = value
            st.rerun()
    st.divider()


# -----------------------------------------------------------------------------
# 2. 키워드 CSV 로드
# -----------------------------------------------------------------------------
@st.cache_data
def load_keywords():
    file_path = "keyword.csv"
    if not os.path.exists(file_path):
        return None, "'keyword.csv' 파일이 없습니다. app.py와 같은 저장소 경로에 추가해 주세요."

    last_error = None
    df = None

    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
        except Exception as exc:
            return None, f"keyword.csv 읽기 오류: {exc}"

    if df is None:
        return None, f"keyword.csv 인코딩을 확인해 주세요: {last_error}"

    df.columns = [str(col).strip().lower() for col in df.columns]
    rename_map = {}

    for col in df.columns:
        if "카테고리" in col or "category" in col or col == "cat":
            rename_map[col] = "category"
        elif "키워드" in col or "keyword" in col or "제시어" in col or "word" in col:
            rename_map[col] = "keyword"

    df = df.rename(columns=rename_map)

    if "category" not in df.columns or "keyword" not in df.columns:
        return None, (
            "keyword.csv에 카테고리와 키워드 열이 필요합니다. "
            "예: category,keyword 또는 카테고리,키워드"
        )

    df["category"] = df["category"].astype(str).str.strip()
    df["keyword"] = df["keyword"].astype(str).str.strip()
    df = df[
        df["category"].ne("")
        & df["keyword"].ne("")
        & df["category"].ne("nan")
        & df["keyword"].ne("nan")
    ].copy()

    return df, None


# -----------------------------------------------------------------------------
# 3. Gemini 이미지 평가
# -----------------------------------------------------------------------------
def ask_gemini_vision(pil_image, keyword, category):
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return False, "API 키 설정 필요: Streamlit Secrets에 GEMINI_API_KEY를 설정해 주세요."

    try:
        from google import genai
        from google.genai import types
        import io

        client = genai.Client(api_key=api_key.strip())
        prompt = (
            "당신은 정보 교과의 추상화 개념을 평가하는 AI 심사위원입니다.\\n"
            "추상화란 불필요한 것을 없애고 문제 해결에 필요한 핵심 요소만 표현하는 것입니다.\\n"
            f"카테고리: {category}\\n"
            f"목표 제시어: {keyword}\\n"
            "첨부된 이미지를 실제로 확인하고 평가하세요. 이미지가 완전히 비어 있을 때만 빈 그림이라고 판단하세요.\\n"
            "제시어를 알아볼 수 있는 핵심 특징이 표현되었는지 평가하세요.\\n"
            "반드시 아래 형식으로 답하세요.\\n"
            "판정: 성공 또는 실패\\n"
            "설명: 핵심 내용 위주로 한두 문장"
        )

        image_buffer = io.BytesIO()
        pil_image.convert("RGB").save(image_buffer, format="PNG")
        image_bytes = image_buffer.getvalue()

        # 일시적인 서버 혼잡이나 요청 제한에 대비해 최대 3회 시도
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[
                        prompt,
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ],
                )
                response_text = getattr(response, "text", None)
                if not response_text:
                    return False, "Gemini에서 텍스트 응답을 받지 못했습니다."
                answer = response_text.strip()
                first_line = answer.splitlines()[0].strip()
                is_success = (
                    first_line.startswith("판정:")
                    and "성공" in first_line
                    and "실패" not in first_line
                )
                return is_success, answer

            except Exception as exc:
                error_text = str(exc)
                temporary_error = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )
                if temporary_error and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                if temporary_error:
                    return False, (
                        "Gemini 서버가 혼잡하거나 요청 한도에 도달해 분석하지 못했습니다. "
                        "잠시 후 같은 그림으로 다시 제출해 주세요.\\n"
                        f"상세 오류: {error_text}"
                    )
                return False, f"Gemini API 오류: {error_text}"

    except Exception as exc:
        return False, f"Gemini API 오류: {exc}"


def image_has_drawing(image_data):
    """흰 배경과 비교해 캔버스에 실제로 그린 흔적이 있는지 확인."""
    if image_data is None:
        return False

    rgb = np.asarray(image_data)[..., :3]
    # 캔버스 배경색이 흰색이므로 흰색에서 유의미하게 벗어난 픽셀이 있는지 검사
    return bool(np.any(rgb < 245))


# -----------------------------------------------------------------------------
# 4. 시작 화면
# -----------------------------------------------------------------------------
if st.session_state.page == "start":
    st.title("🧩 추상화 게임")
    st.caption(
        "💡 추상화: 불필요한 것을 없애고, 문제 해결에 반드시 필요한 요소만을 뽑아 문제 해결 방법을 찾는 것"
    )

    df_keywords, csv_error = load_keywords()
    if csv_error:
        st.error(csv_error)
        st.stop()

    st.write("### 카테고리 선택")
    categories = ["동물", "과일", "채소", "사물", "교통수단"]
    cols = st.columns(5)

    for idx, cat in enumerate(categories):
        with cols[idx]:
            if st.button(cat, key=f"cat_btn_{idx}"):
                filtered = (
                    df_keywords.loc[df_keywords["category"] == cat, "keyword"]
                    .drop_duplicates()
                    .tolist()
                )
                required_count = 5

                if len(filtered) < required_count:
                    st.error(
                        f"'{cat}' 카테고리 키워드가 부족합니다 "
                        f"(요청: {required_count}개, 보유: {len(filtered)}개)."
                    )
                else:
                    st.session_state.category = cat
                    st.session_state.total_target_questions = required_count
                    st.session_state.quiz_pool = random.sample(filtered, required_count)
                    st.session_state.current_pool_idx = 0
                    st.session_state.solved_count = 0
                    st.session_state.pass_count = 0
                    st.session_state.history = []
                    st.session_state.last_result = None
                    st.session_state.start_time = time.time()
                    st.session_state.page = "game"
                    st.rerun()


# -----------------------------------------------------------------------------
# 5. 게임 화면
# -----------------------------------------------------------------------------
elif st.session_state.page == "game":
    render_top_bar()

    pool_idx = st.session_state.current_pool_idx
    if pool_idx >= len(st.session_state.quiz_pool):
        st.session_state.page = "result"
        st.rerun()

    keyword = st.session_state.quiz_pool[pool_idx]
    category = st.session_state.category
    target_q = st.session_state.total_target_questions
    solved_q = st.session_state.solved_count
    pass_used = st.session_state.pass_count

    #if st.session_state.start_time is None:
    #    st.session_state.start_time = time.time()

    #elapsed_time = time.time() - st.session_state.start_time
    #remaining_time = max(0, int(60 - elapsed_time))
    #is_time_over = remaining_time == 0

    col1, col2 = st.columns([1, 10])
    #col1, col2, col3 = st.columns([1.2, 2, 1.2])
    with col1:
        st.markdown(f"#### 문제 **{solved_q + 1} / {5}**")
    with col2:
        bg_color = "#E0F2F1"
        border_color = "#00838F"
        st.markdown(
                f"""
                <div style="background-color:{bg_color};padding:12px 20px;border-radius:12px;border-left:8px solid {border_color};margin-bottom:10px;">
                    <h4>제시어: <b>{keyword}</b></h4>
                </div>
                """,
                unsafe_allow_html=True,
        )

    st.info("아래 그림판에 마우스나 터치로 그림을 그린 후 [제출하기] 버튼을 눌러주세요!")

    draw_col1, draw_col2 = st.columns([1, 15])
    with draw_col1:
        stroke_color = st.color_picker(
            "펜 색상", "#000000", key=f"stroke_color_{pool_idx}"
        )
        
    with draw_col2:
        stroke_width = st.slider(
            "선 두께", 2, 25, 6, key=f"stroke_width_{pool_idx}"
        )

    clear_state_key = f"clear_canvas_{pool_idx}"
    if clear_state_key not in st.session_state:
        st.session_state[clear_state_key] = 0

    canvas_col, button_col = st.columns([5,4])
    with canvas_col:
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_color="#FFFFFF",
                height=380,
                width=850,
                drawing_mode="freedraw",
                update_streamlit=True,
                key=f"canvas_{pool_idx}_{st.session_state[clear_state_key]}",
            )
    
    with button_col:
        st.write("")
        st.write("")
    
        if st.button(
            "🧩 결과 제출",
            key=f"btn_submit_{pool_idx}",
            use_container_width=True,
        ):
            if not image_has_drawing(canvas_result.image_data):
                st.warning("그림을 먼저 그려 주세요.")
                st.stop()
    
            pil_img = Image.fromarray(
                np.asarray(canvas_result.image_data).astype("uint8")
            ).convert("RGB")
    
            with st.spinner("🔍 AI가 그림을 분석 중입니다..."):
                is_success, ai_answer = ask_gemini_vision(
                    pil_img, keyword, category
                )
    
            if ai_answer.startswith(
                ("Gemini 서버가", "Gemini API 오류:", "API 키 설정")
            ):
                st.error(ai_answer)
                st.info("그림은 유지됩니다. 다시 제출해 주세요.")
                st.stop()
    
            result_data = {
                "round": solved_q + 1,
                "keyword": keyword,
                "image": pil_img.copy(),
                "ai_response": ai_answer,
                "is_success": is_success,
            }
    
            st.session_state.history.append(result_data)
            st.session_state.last_result = result_data
            st.session_state.solved_count += 1
            st.session_state.current_pool_idx += 1
            st.session_state.page = "intermediate"
            st.rerun()
    
        if st.button(
            f"⏩ 패스 ({pass_used}/5)",
            key=f"btn_pass_{pool_idx}",
            use_container_width=True,
        ):
            solved_q += 1
            st.session_state.pass_count += 1
            st.session_state.current_pool_idx += 1
            #st.session_state.start_time = time.time()
    
            if (
                st.session_state.current_pool_idx
                >= len(st.session_state.quiz_pool)
            ):
                st.session_state.page = "result"
    
            st.rerun()

    #if is_time_over:
    #    st.error("⏰ 제한 시간이 초과되었습니다! 그림을 제출하거나 패스해 주세요.")


# -----------------------------------------------------------------------------
# 6. 중간 평가 화면
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

    st.markdown(f"### 📋 [문제 {round_num}] 분석 결과")

    col_img, col_info = st.columns([1, 2])
    with col_img:
        if img is not None:
            st.image(img, caption="내가 표현한 그림", width=500)

    with col_info:
        if is_success:
            st.success("✨ 추상화 성공!")
        else:
            st.error("⚠️ 추상화 실패! 다시 도전해 보세요.")

        st.markdown(
            f"""
            <div class="result-text-big" style="background-color:#E0F2F1;padding:20px;border-radius:12px;margin-top:10px;border-left:6px solid #00838F;">
                • 목표 제시어: <span style="color:#00838F;"><b>{kw}</b></span><br><br>
                • <b>AI 분석 결과:</b><br>
                <span style="font-size:1.05rem;color:#333333;">{ai_res}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.solved_count >= st.session_state.total_target_questions:
        if st.button("📊 최종 결과 보기"):
            st.session_state.page = "result"
            st.rerun()
    else:
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if not is_success:
                if st.button("🔄 다시 시도하기"):
                    if st.session_state.history:
                        st.session_state.history.pop()
                    st.session_state.solved_count = max(0, st.session_state.solved_count - 1)
                    st.session_state.current_pool_idx = max(
                        0, st.session_state.current_pool_idx - 1
                    )
                    st.session_state.start_time = time.time()
                    st.session_state.last_result = None
                    st.session_state.page = "game"
                    st.rerun()

        with b_col2:
            if st.button("➡️ 다음 문제 풀기"):
                st.session_state.start_time = time.time()
                st.session_state.last_result = None
                if st.session_state.current_pool_idx >= len(st.session_state.quiz_pool):
                    st.session_state.page = "result"
                else:
                    st.session_state.page = "game"
                st.rerun()


# -----------------------------------------------------------------------------
# 7. 최종 결과 화면
# -----------------------------------------------------------------------------
elif st.session_state.page == "result":
    render_top_bar()

    st.markdown(
        "<div class='big-title'>📊 최종 결과</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-title'>학습 카테고리: <b>{st.session_state.category}</b> | "
        f"패스 사용: <b>{st.session_state.pass_count}회</b></div>",
        unsafe_allow_html=True,
    )

    completed_count = len(st.session_state.history)
    st.metric("완료된 문항 수", f"{completed_count} 문항")
    st.divider()

    for item in st.session_state.history:
        item_success = item.get("is_success", False)
        bg_color = "#E0F2F1" if item_success else "#FFEBEE"
        border_color = "#00838F" if item_success else "#C62828"
        status_label = "성공" if item_success else "실패"

        with st.container():
            st.markdown(
                f"""
                <div style="background-color:{bg_color};padding:12px 20px;border-radius:12px;border-left:8px solid {border_color};margin-bottom:10px;">
                    <h4>🧩 문제 {item.get('round', 1)} - 제시어: [{item.get('keyword', '')}] ({status_label})</h4>
                </div>
                """,
                unsafe_allow_html=True,
            )

            r_col1, r_col2 = st.columns([1, 2])
            with r_col1:
                if item.get("image") is not None:
                    st.image(item["image"], width=280)
            with r_col2:
                st.markdown("**🔍 AI 분석 피드백:**")
                st.write(item.get("ai_response", ""))
            st.divider()

    if st.button("🔄 다시 학습하기", key="btn_restart"):
        for key, value in DEFAULTS.items():
            st.session_state[key] = value
        st.rerun()
