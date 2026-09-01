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
        model="gemini-3.6-flash", contents=[pil_img, prompt]
    )
    if response and response.text:
      text = response.text.strip()
      # AI가 명시한 '판정:' 텍스트를 기반으로 성공/실패를 정확히 분기
      is_success = False
      if "판정: 성공" in text or "성공" in text.split("\n")[0]:
        is_success = True

      return is_success, text
  except Exception as e:
    return False, f"통신 오류 발생: {str(e)}"

  return False, "판정 불가"
