import hashlib
import json
import re

import requests
from json_repair import repair_json

from ..parsers.candidate_common import read_resume_pdf_raw
from ..parsers.candidate_parser import parse_resume
from ..embeddings.make_embed import build_resume_text
from ..embeddings.make_embed import embed_resume
from ..storage.opensearch_client import get_opensearch_client
from ..storage.opensearch_candidates import (
    candidate_exists,
    bulk_index_candidates,
    create_candidates_index_if_not_exists,
    list_candidates as storage_list_candidates,
    clear_candidates_index as storage_clear_candidates_index,
)

LLM_URL = "http://92.39.53.155:8000/v1/chat/completions"
LLM_MODEL = "Qwen/Qwen3-14B-AWQ"


def prepare_candidate_doc(parsed: dict, source_file: str) -> dict:
    doc = parsed.copy()
    doc["source_file"] = source_file
    doc["resume_text"] = build_resume_text(doc)
    doc["resume_vector"] = embed_resume(doc["resume_text"])
    return doc


def parse_data_full(data_full: dict) -> dict:
    parsed_docs = {}

    for filename, data in data_full.items():
        parsed = parse_resume(data)
        doc = prepare_candidate_doc(parsed, filename)
        parsed_docs[filename] = doc

    return parsed_docs


def ingest_candidate_pdfs(files) -> dict:
    docs = {}
    loaded = 0
    errors = 0
    duplicates = 0
    error_details = []

    client = get_opensearch_client()
    create_candidates_index_if_not_exists(client)

    for file in files:
        try:
            data = read_resume_pdf_raw(file)
            parsed = parse_resume(data)
            doc = prepare_candidate_doc(parsed, file.filename)

            if candidate_exists(client, file.filename):
                duplicates += 1
                continue

            docs[file.filename] = doc
            loaded += 1
        except Exception as e:
            errors += 1
            error_details.append({
                "file": getattr(file, "filename", "unknown"),
                "error": str(e),
            })

    if docs:
        bulk_index_candidates(client, docs)

    return {
        "loaded": loaded,
        "errors": errors,
        "duplicates": duplicates,
        "error_details": error_details,
    }


def list_candidates() -> list[dict]:
    client = get_opensearch_client()
    create_candidates_index_if_not_exists(client)
    return storage_list_candidates(client, size=100)


def clear_candidates_index() -> bool:
    client = get_opensearch_client()
    return storage_clear_candidates_index(client)


def split_resume_texts(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    parts = re.split(r"\n{3,}", normalized)
    return [part.strip() for part in parts if part.strip()]


def _to_int_or_none(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _to_str_or_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value)


def _to_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if item is None:
                continue
            item = str(item).strip()
            if item:
                result.append(item)
        return result
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [str(value).strip()] if str(value).strip() else []


def _normalize_positions(value) -> list[dict]:
    if not isinstance(value, list):
        return []

    positions = []
    for item in value:
        if not isinstance(item, dict):
            continue

        positions.append({
            "company": _to_str_or_none(item.get("company")),
            "role": _to_str_or_none(item.get("role")),
            "start_date": _to_str_or_none(item.get("start_date")),
            "end_date": _to_str_or_none(item.get("end_date")),
            "responsibilities": _to_str_list(item.get("responsibilities")),
        })

    return positions


def normalize_llm_candidate(parsed: dict, raw_text: str) -> dict:
    if not isinstance(parsed, dict):
        parsed = {}

    contacts = parsed.get("contacts") or {}
    experience = parsed.get("experience") or {}
    skills = parsed.get("skills") or {}
    education = parsed.get("education") or {}

    normalized = {
        "name": _to_str_or_none(parsed.get("name")),
        "age": _to_int_or_none(parsed.get("age")),
        "contacts": {
            "location": _to_str_or_none(contacts.get("location")),
            "citizenship": _to_str_or_none(contacts.get("citizenship")),
            "work_permission": _to_str_or_none(contacts.get("work_permission")),
            "phone": _to_str_or_none(contacts.get("phone")),
            "email": _to_str_or_none(contacts.get("email")),
        },
        "experience": {
            "years": _to_int_or_none(experience.get("years")),
            "positions": _normalize_positions(experience.get("positions")),
        },
        "skills": {
            "tools": _to_str_list(skills.get("tools")),
            "languages": _to_str_list(skills.get("languages")),
        },
        "education": {
            "institution": _to_str_or_none(education.get("institution")),
            "degree": _to_str_or_none(education.get("degree")),
            "specialization": _to_str_or_none(education.get("specialization")),
            "year": _to_int_or_none(education.get("year")),
        },
        "achievements": _to_str_list(parsed.get("achievements")),
        "english_level": _to_str_or_none(parsed.get("english_level")),
        "tags": _to_str_list(parsed.get("tags")),
        "resume_text": _to_str_or_none(parsed.get("resume_text")),
        "resume_text_orig": _to_str_or_none(parsed.get("resume_text_orig")) or raw_text,
    }

    return normalized


def _extract_json_content(text: str):
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()
    fixed = repair_json(text)
    parsed = json.loads(fixed)

    if isinstance(parsed, list):
        if not parsed:
            return {}
        parsed = parsed[0]

    if not isinstance(parsed, dict):
        raise ValueError("LLM returned non-dict JSON")

    return parsed


def parse_resume_text_via_llm(resume_text: str) -> dict:
    system_prompt = """
Ты — парсер резюме.
Извлекай данные из текста резюме и возвращай ТОЛЬКО валидный JSON.
Никакого текста до или после JSON. Никаких комментариев. Только JSON.

СТРУКТУРА:
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
  "resume_text_orig": "string — полный исходный текст резюме"
}

ПРАВИЛА:
1. Верни один JSON-объект, не массив.
2. Если данных нет, ставь null или [].
3. positions — всегда массив объектов.
4. skills — всегда объект с tools и languages.
5. education — всегда объект.
6. achievements и tags — всегда массивы.
7. Для текущей работы end_date = null.
8. В resume_text_orig положи исходный текст резюме без сокращений.
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": resume_text},
        ],
        "max_tokens": 4096,
        "temperature": 0,
        "top_p": 1.0,
        "repetition_penalty": 1.05,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    response = requests.post(LLM_URL, json=payload, timeout=120)
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    parsed = _extract_json_content(content)
    return normalize_llm_candidate(parsed, resume_text)


def build_text_resume_doc_id(raw_text: str) -> str:
    digest = hashlib.md5(raw_text.encode("utf-8")).hexdigest()[:16]
    return f"text_resume_{digest}"


def ingest_candidate_texts_via_llm(text_blob: str) -> dict:
    docs = {}
    loaded = 0
    errors = 0
    duplicates = 0
    error_details = []

    resumes = split_resume_texts(text_blob)

    client = get_opensearch_client()
    create_candidates_index_if_not_exists(client)

    for idx, resume_text in enumerate(resumes, start=1):
        doc_id = build_text_resume_doc_id(resume_text)
        source_name = f"{doc_id}.txt"

        try:
            if candidate_exists(client, doc_id):
                duplicates += 1
                continue

            parsed = parse_resume_text_via_llm(resume_text)
            doc = prepare_candidate_doc(parsed, source_name)

            docs[doc_id] = doc
            loaded += 1

        except Exception as e:
            errors += 1
            error_details.append({
                "file": f"text_resume_{idx}",
                "error": str(e),
            })

    if docs:
        bulk_index_candidates(client, docs)

    return {
        "loaded": loaded,
        "errors": errors,
        "duplicates": duplicates,
        "error_details": error_details,
    }