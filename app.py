def ask_gemini(pil_image, category):
    """Gemini Flash 모델을 호출하여 그림을 추론하는 함수"""
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
