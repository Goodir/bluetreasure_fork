import requests

url="http://92.39.53.155:8000/v1/chat/completions"

def request_llm_final(vacancy, candidates):

    system_prompt = (
        f"Ты профессиональный HR. Из предоставленных кандидатов выбери того, "
        f"кто максимально подходит под вакансию:\n\n{vacancy}\n\n"
        f"Проставь каждому балл от 0 до 10. "
        f"Напиши текст отказа тем, кто не подошёл, и объясни, почему выбрал именно этого кандидата."
        f"Ответ должен быть с правильными отступами и переходом на новую строку для красивого вставки в сайт."
    )

    data = {
    "model": "Qwen/Qwen3-8B-AWQ",
    "messages": [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": candidates}
    ],
    "max_tokens": 16384,
    "temperature": 0.7,
    "chat_template_kwargs": {"enable_thinking": False}
    }

    response = requests.post(url, json=data)
    return response.json()["choices"][0]["message"]["content"]









