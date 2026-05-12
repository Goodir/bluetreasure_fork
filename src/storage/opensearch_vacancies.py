from .opensearch_base import * 
VACANCY_INDEX = "vacancy"

VACANCY_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "knn": True,
        }
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "company": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "format": {
                "type": "keyword"
            },
            "experience_level": {
                "type": "keyword"
            },
            "required_years": {
                "type": "float"
            },
            "salary_hint": {
                "type": "text"
            },
            "must_have": {
                "type": "text"
            },
            "requirements": {
                "type": "text"
            },
            "responsibilities": {
                "type": "text"
            },
            "conditions": {
                "type": "text"
            },
            "tags": {
                "type": "keyword"
            },
            "raw_text": {
                "type": "text",
                "index": False
            },
            "vacancy_text": {
                "type": "text"
            },
            "vacancy_hash": {
                "type": "keyword"
            },
            "source_type": {
                "type": "keyword"
            },
            "source_file": {
                "type": "keyword"
            },
            "created_at": {
                "type": "date"
            },
            "vacancy_vector": {
                "type": "knn_vector",
                "dimension": 768
            }
        }
    }
}


def create_vacancy_index_if_not_exists(client) -> None:
    create_index_if_not_exists(client, VACANCY_INDEX, VACANCY_MAPPING)


def vacancy_exists(client, vacancy_id: str) -> bool:
    return document_exists(client, VACANCY_INDEX, vacancy_id)


def index_vacancy(client, vacancy_id: str, doc: dict) -> None:
    index_document(client, VACANCY_INDEX, vacancy_id, doc)


def get_vacancy_by_id(client, vacancy_id: str) -> dict | None:
    return get_document_by_id(client, VACANCY_INDEX, vacancy_id)


def list_vacancies(client, size: int = 100) -> list[dict]:
    return list_documents(client, VACANCY_INDEX, size=size)


def search_vacancies(client, query_body: dict) -> list[dict]:
    return search_documents(client, VACANCY_INDEX, query_body)


def clear_vacancies_index(client) -> bool:
    return delete_index_if_exists(client, VACANCY_INDEX)