import requests

url="http://92.39.53.155:8000/v1/chat/completions"


def get_candidate_title(candidate: dict) -> str:
    name = candidate.get("name")
    source_file = candidate.get("source_file") or candidate.get("id") or "unknown_file"

    if name:
        return f"{name} — {source_file}"

    return source_file

def request_llm_final(vacancy, candidates):
    llm_response_list = []

    for candidate in candidates:
        candidate_title = get_candidate_title(candidate)

        cand_text = candidate.get("resume_text", "")
        prompt = f"Кандидат: {candidate_title}\n\n{cand_text}"

        system_prompt = """Ты опытный HR-специалист с 10-летним стажем подбора технических специалистов.
        Твоя задача — объективно оценить соответствие кандидата вакансии.

        Отвечай строго по структуре ниже. Используй Markdown-форматирование: заголовки ##, жирный текст **, списки -.
        """

        user_prompt = f"""## Вакансия
        {vacancy}

        ## Резюме кандидата
        {prompt}

        ---

        Проведи анализ по следующей структуре:

        ## 1. Рейтинг соответствия
        Оцени кандидата по шкале от 1 до 10, где:
        - 1–3: не подходит
        - 4–6: частично подходит
        - 7–9: хорошо подходит
        - 10: идеальный кандидат

        **Рейтинг: X/10**
        Одно предложение — почему именно такой балл.

        ## 2. Соответствие требованиям
        Пройдись по каждому ключевому требованию вакансии и укажи есть ли оно у кандидата.
        Формат: - **Требование:** ✅ есть / ❌ нет / ⚠️ частично — краткий комментарий

        ## 3. Сильные стороны кандидата
        Перечисли 3–5 сильных сторон, которые релевантны для данной вакансии.

        ## 4. Риски при найме
        Перечисли конкретные риски для компании если мы возьмём этого кандидата.

        ## 5. Вывод
        Краткий вывод: стоит ли рассматривать кандидата и при каких условиях.

        ## 6. Текст отказа
        Напиши тактичный, уважительный текст отказа для кандидата (3–5 предложений).
        Не упоминай конкретные причины отказа — только благодарность и пожелание удачи.
        """


        data = {
            "model": "Qwen/Qwen3-14B-AWQ",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 8192,
            "temperature": 0,
            "top_p": 1.0,
            "repetition_penalty": 1.05,
            "chat_template_kwargs": {"enable_thinking": False}
        }

        response = requests.post(url, json=data)
        final_response = response.json()["choices"][0]["message"]["content"]

        llm_response_list.append({
            "candidate_title": candidate_title,
            "response": final_response,
        })
    return llm_response_list









