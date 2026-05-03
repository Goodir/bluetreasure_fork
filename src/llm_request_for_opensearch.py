import requests
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
import json
from json_repair import repair_json
import re

# Проверка наличия индекса


url="http://92.39.53.155:8000/v1/chat/completions"
client = OpenSearch(
        hosts=[{"host": "opensearch", "port": 9200}],
        http_auth=("admin", "bestteam1984A."),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False
    )

def check_opensearch_index():
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
        return 1
    else:
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },

        }
        client.indices.create(index='candidates', body=mapping)
        return 1


def split_vacancies(vacancy):
    vacancy = vacancy.replace('\r\n', '\n').replace('\r', '\n')
    pattern = r'\n{3,}'
    parts = re.split(pattern, vacancy)
    parts = [p.strip() for p in parts if p.strip()]
    return [[p] for p in parts]


def request_llm(candidates): # сюда приходит вложенный список кандидатов


    system_prompt = """
    Ты — парсер резюме. Извлекай данные из текста резюме и возвращай ТОЛЬКО валидный JSON.
Никакого текста до или после JSON. Никаких комментариев. Только JSON.

ОБЯЗАТЕЛЬНАЯ СТРУКТУРА (строго соблюдай типы данных):

{
  "name": "string или null",
  "age": integer или null,
  "contacts": {
    "location": "string или null",
    "citizenship": "string или null",
    "work_permission": "string или null",
    "phone": "string или null",
    "email": "string или null"
  },
  "experience": {
    "years": integer или null,
    "positions": [
      {
        "company": "string или null",
        "role": "string или null",
        "start_date": "YYYY-MM или null",
        "end_date": "YYYY-MM или null",
        "responsibilities": ["string", "string"]
      }
    ]
  },
  "skills": {
    "tools": ["string", "string"],
    "languages": ["string", "string"]
  },
  "education": {
    "institution": "string или null",
    "degree": "string или null",
    "specialization": "string или null",
    "year": integer или null
  },
  "achievements": ["string", "string"],
  "english_level": "string или null",
  "tags": ["string", "string"],
  "resume_text": "string — краткое резюме со всеми кейвордами",
  "resume_text_orig": "string — полный исходный текст резюме",
  
}

ПРАВИЛА (никогда не нарушай):
1. end_date текущей должности = null (никогда не пиши "present", "н.в.", "сейчас")
2. education — ВСЕГДА объект с полями institution, degree, specialization, year. Никогда не строка.
3. skills — ВСЕГДА объект с полями tools и languages. Оба поля — массивы строк.
4. positions — ВСЕГДА массив объектов, даже если одна позиция
5. achievements — ВСЕГДА массив строк, даже если пустой: []
6. tags — ВСЕГДА массив строк
7. Если данные отсутствуют — используй null для строк/чисел, [] для массивов
8. start_date и end_date — ТОЛЬКО формат "YYYY-MM". Если данные отсутсвуют ставь 2026-04
9. В ключ resume_text добавь короткий текст о кандидате со всеми кейвордами. Ключ resume_text должен быть у каждого кандидата
10. В ключ resume_text_orig клади оригинальный текст резюме который тебе был передан
11. Не клади JSON в список. JSON НЕ ДОЛЖЕН БЫТЬ В КВАДРАТНЫХ СКОБКАХ. Нужен чистый JSON
 
"""
    start_index = 0
    # итерируемся по списку
    for cand in candidates:
        cand = ", ".join(cand)
        data = {
            "model": "Qwen/Qwen3-14B-AWQ",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cand}
            ],
            "max_tokens": 8192,
            "temperature": 0,
            "top_p": 1.0,
            "repetition_penalty": 1.05,
            "chat_template_kwargs": {"enable_thinking": False}
        }
        response = requests.post(url, json=data)
        data_for_open = response.json()["choices"][0]["message"]["content"]
        # print(f'Данные ответа от модели Qwen: {data_for_open}')
        # чиним json на всякий случай
        data_for_open = repair_json(data_for_open)
        start_index += 1
        opensearch_write(data_for_open, start_index)
    return True

def opensearch_write(candidate, start_index):
    parsed = json.loads(candidate)
    id = start_index
    response = client.index(
            index="candidates",
            id=id,
            body=parsed
        )
    # print(f"{id} result: {response}")
    return True




# Старый промпт на всякий случай

# Мне нужно чтобы ты из текста множественных резюме выделил основные данные и выдал ответ в формате JSON без лишней информации
# Ты парсер резюме. Из текста кандидата ты должен:
# 1. Самостоятельно определить какие поля есть в тексте
# 2. Построить подходящую JSON-схему
# 3. Вернуть ТОЛЬКО валидный JSON объект — без markdown, без пояснений
# 4. Если видишь что в тексте больше чем 3 знака переноса строки \n\n\n то нужно рассматривать это как следующее резюме
# === ЖЁСТКИЕ ПРАВИЛА для совместимости с OpenSearch ===
#
# ТИПЫ ДАННЫХ:
# - Числа (возраст, стаж, зарплата)  → integer или float, НЕ строки: "age": 26  (не "26")
# - Даты                              → формат "YYYY-MM-DD": "applied_at": "2026-04-28"
# - Списки навыков, достижений        → массив строк: ["pandas", "scikit-learn"]
# - Булевы значения                   → true/false, НЕ строки: "remote_ready": true
# - Текстовые поля                    → строка: "name": "Алексей Смирнов"
# - Отсутствующие поля                → null для строк, [] для массивов, не пропускай
#
# ЗАПРЕЩЕНО:
# - Смешивать типы в одном поле: если поле числовое — всегда число, не строка
# - Использовать точки в ключах: НЕ "experience.years" → используй вложенный объект
# - Ключи с пробелами или спецсимволами: только snake_case
# - Вкладывать массивы в массивы: [["a","b"]] — неверно, только ["a","b"]
# - Пустые ключи: "" — недопустимо
#
# ОБЯЗАТЕЛЬНЫЕ ПОЛЯ (должны быть всегда):
# - "name"       → string
# - "contacts"   данные кандидата для связи
# - "status"     → всегда "active"
# - "tags"       → массив ключевых слов из резюме
#
#
# СТРУКТУРА:
# - Группируй связанные поля во вложенные объекты: experience{}, skills{}, languages{}
# - Называй поля по смыслу на английском в snake_case
#
# Ответ должен содержать только JSON массив для вставки в Opensearch"
# Возвращай данные как JSON-массив объектов:
# [
#   {"name": "...", "age": ...},
#   {"name": "...", "age": ...}
# ]
# НЕ используй формат {"index": ...} — только чистый массив.
# Если не хватает информации оставляй "null"
# В ключ resume_text добавь короткий текст о кандидате со всеми кейвордами. Ключ resume_text должен быть у каждого кандидата
# Если в end_date не стоит правильной даты до ставь null
# Не клади JSON в список. JSON НЕ ДОЛЖЕН БЫТЬ В КВАДРАТНЫХ СКОБКАХ. Нужен чистый JSON как в примере ниже
# === ПРИМЕР ВЫВОДА ===
# {"name": "Дмитрий Волков", "age": 29, "experience": {"years": 4, "position": "Data Analyst", "industry": "banking"}, "skills": {"python": ["pandas", "matplotlib", "seaborn"], "databases": ["PostgreSQL", "Redshift"]}, "achievements": ["Автоматизировал отчётность — сократил время подготовки на 70%"], "english_level": "B1", "applied_at": "2026-04-28"}






