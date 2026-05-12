import hashlib
from datetime import datetime, timezone

from ..parsers.vacancy_parser import parse_vacancy_text, parse_vacancy_pdf
from ..embeddings.make_embed import embed_vacancy
from ..storage.opensearch_client import get_opensearch_client
from ..storage.opensearch_vacancies import (
    create_vacancy_index_if_not_exists,
    vacancy_exists,
    index_vacancy,
    list_vacancies as storage_list_vacancies,
    get_vacancy_by_id as storage_get_vacancy_by_id,
    clear_vacancies_index as storage_clear_vacancies_index,
)


def normalize_for_hash(text: str) -> str:
    return " ".join(text.lower().split())


def make_vacancy_hash(vacancy_text: str) -> str:
    normalized = normalize_for_hash(vacancy_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def prepare_vacancy_doc(
    parsed: dict,
    source_type: str,
    source_file: str | None = None,
) -> tuple[str, dict]:
    vacancy_text = parsed["vacancy_text"]
    vacancy_id = make_vacancy_hash(vacancy_text)

    doc = {
        "title": parsed.get("title"),
        "company": parsed.get("company"),
        "format": parsed.get("format"),
        "experience_level": parsed.get("experience_level"),
        "required_years": parsed.get("required_years"),
        "salary_hint": parsed.get("salary_hint"),
        "must_have": parsed.get("must_have", []),
        "requirements": parsed.get("requirements", []),
        "responsibilities": parsed.get("responsibilities", []),
        "conditions": parsed.get("conditions", []),
        "tags": parsed.get("tags", []),
        "raw_text": parsed.get("raw_text"),
        "vacancy_text": vacancy_text,
        "vacancy_hash": vacancy_id,
        "source_type": source_type,
        "source_file": source_file,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "vacancy_vector": embed_vacancy(vacancy_text),
    }
    return vacancy_id, doc


def save_vacancy_from_text(text: str) -> dict:
    client = get_opensearch_client()
    create_vacancy_index_if_not_exists(client)

    parsed = parse_vacancy_text(text)
    vacancy_id, doc = prepare_vacancy_doc(parsed, source_type="text")

    if vacancy_exists(client, vacancy_id):
        return {
            "status": "duplicate",
            "message": "Такая вакансия уже есть",
            "vacancy_id": vacancy_id,
        }

    index_vacancy(client, vacancy_id, doc)

    return {
        "status": "created",
        "message": "Вакансия сохранена",
        "vacancy_id": vacancy_id,
    }


def save_vacancy_from_pdf(file) -> dict:
    client = get_opensearch_client()
    create_vacancy_index_if_not_exists(client)

    parsed = parse_vacancy_pdf(file)
    vacancy_id, doc = prepare_vacancy_doc(
        parsed,
        source_type="pdf",
        source_file=file.filename,
    )

    if vacancy_exists(client, vacancy_id):
        return {
            "status": "duplicate",
            "message": "Такая вакансия уже есть",
            "vacancy_id": vacancy_id,
        }

    index_vacancy(client, vacancy_id, doc)

    return {
        "status": "created",
        "message": "Вакансия сохранена",
        "vacancy_id": vacancy_id,
    }


def list_vacancies() -> list[dict]:
    client = get_opensearch_client()
    create_vacancy_index_if_not_exists(client)
    return storage_list_vacancies(client, size=100)


def get_vacancy_by_id(vacancy_id: str) -> dict | None:
    client = get_opensearch_client()
    return storage_get_vacancy_by_id(client, vacancy_id)


def clear_vacancies_index() -> bool:
    client = get_opensearch_client()
    return storage_clear_vacancies_index(client)