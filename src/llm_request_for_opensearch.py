import requests
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
import json
from json_repair import repair_json

# Проверка наличия индекса


url="http://92.39.53.155:8000/v1/chat/completions"
client = OpenSearch(
        hosts=[{"host": "opensearch", "port": 9200}], # для запуска через docker-compose поменять на 172.23.0.4
        http_auth=("admin", "bestteam1984A."),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False
    )


def request_llm(candidates):


    system_prompt = """
Мне нужно чтобы ты из текста множественных резюме выделил основные данные и выдал ответ в формате JSON без лишней информации
Ты парсер резюме. Из текста кандидата ты должен:
1. Самостоятельно определить какие поля есть в тексте
2. Построить подходящую JSON-схему
3. Вернуть ТОЛЬКО валидный JSON объект — без markdown, без пояснений
4. Если видишь что в тексте больше чем 3 знака переноса строки \n\n\n то нужно рассматривать это как следующее резюме
=== ЖЁСТКИЕ ПРАВИЛА для совместимости с OpenSearch ===

ТИПЫ ДАННЫХ:
- Числа (возраст, стаж, зарплата)  → integer или float, НЕ строки: "age": 26  (не "26")
- Даты                              → формат "YYYY-MM-DD": "applied_at": "2026-04-28"
- Списки навыков, достижений        → массив строк: ["pandas", "scikit-learn"]
- Булевы значения                   → true/false, НЕ строки: "remote_ready": true
- Текстовые поля                    → строка: "name": "Алексей Смирнов"
- Отсутствующие поля                → null для строк, [] для массивов, не пропускай

ЗАПРЕЩЕНО:
- Смешивать типы в одном поле: если поле числовое — всегда число, не строка
- Использовать точки в ключах: НЕ "experience.years" → используй вложенный объект
- Ключи с пробелами или спецсимволами: только snake_case
- Вкладывать массивы в массивы: [["a","b"]] — неверно, только ["a","b"]
- Пустые ключи: "" — недопустимо

ОБЯЗАТЕЛЬНЫЕ ПОЛЯ (должны быть всегда):
- "name"       → string
- "contacts"   данные кандидата для связи
- "status"     → всегда "active"
- "tags"       → массив ключевых слов из резюме


СТРУКТУРА:
- Группируй связанные поля во вложенные объекты: experience{}, skills{}, languages{}
- Называй поля по смыслу на английском в snake_case

Ответ должен содержать только JSON массив для вставки в Opensearch"
Возвращай данные как JSON-массив объектов:
[
  {"name": "...", "age": ...},
  {"name": "...", "age": ...}
]
НЕ используй формат {"index": ...} — только чистый массив.
Если не хватает информации оставляй "null"
В ключ resume_text добавь короткий текст о кандидате со всеми кейвордами. Ключ resume_text должен быть у каждого кандидата
=== ПРИМЕР ВЫВОДА ===
{"index": {"_id": "1"}}
{"name": "Дмитрий Волков", "age": 29, "experience": {"years": 4, "position": "Data Analyst", "industry": "banking"}, "skills": {"python": ["pandas", "matplotlib", "seaborn"], "databases": ["PostgreSQL", "Redshift"]}, "achievements": ["Автоматизировал отчётность — сократил время подготовки на 70%"], "english_level": "B1", "applied_at": "2026-04-28"}
"""

    data = {
    "model": "Qwen/Qwen3-14B-AWQ",
    "messages": [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": candidates}
    ],
    "max_tokens": 8192,
    "temperature": 0,
    "top_p": 1.0,
    "repetition_penalty": 1.05,
    "chat_template_kwargs": {"enable_thinking": False}
    }

    response = requests.post(url, json=data)
    data_for_open = response.json()["choices"][0]["message"]["content"]
    print(f'Данные ответа от модели Qwen: {data_for_open}')
    # чиним json на всякий случай
    data_for_open = repair_json(data_for_open)

    # Создание индекса Opensearch
    # Если индекс есть до удаляем из него все данные (нужно для повторных пусков)
    if client.indices.exists(index='candidates'):
        # если индекс есть до удаляем все данные из него (нужно для повторных запусков)
        client.indices.delete(index='candidates')
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },

        }
        client.indices.create(index='candidates', body=mapping)
        parsed = json.loads(data_for_open)
        actions = [
            {"_index": "candidates", "_id": str(i + 1), "_source": doc}
            for i, doc in enumerate(parsed)
        ]
        success, failed = bulk(client, actions)
        print("success: ", success)
        print("failed: ", failed)
        return success

    else:
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },

        }
        client.indices.create(index='candidates', body=mapping)

        parsed = json.loads(data_for_open)
        actions = [
            {"_index": "candidates", "_id": str(i + 1), "_source": doc}
            for i, doc in enumerate(parsed)
        ]
        success, failed = bulk(client, actions)
        print("success: ", success)
        print("failed: ", failed)
        return success




