from ..storage.opensearch_client import get_opensearch_client
from ..storage.opensearch_vacancies import get_vacancy_by_id
from ..storage.opensearch_candidates import search_candidates, list_candidates


def build_knn_query(vacancy_vector: list[float], top_k: int = 20) -> dict:
    return {
        "size": top_k,
        "query": {
            "knn": {
                "resume_vector": {
                    "vector": vacancy_vector,
                    "k": top_k
                }
            }
        }
    }

from .ranking_service import rerank_candidates_rule_based


def normalize_candidate(item: dict) -> dict:
    return {
        "id": item.get("_id"),
        "score": item.get("_score"),
        "name": item.get("name"),
        "resume_text": item.get("resume_text"),
        "contacts": item.get("contacts"),
        "experience": item.get("experience"),
        "skills": item.get("skills"),
        "source_file": item.get("source_file"),
        "resume_vector": item.get("resume_vector"),
    }


def search_candidates_by_vacancy(vacancy_id: str, top_k: int = 20) -> list[dict]:
    client = get_opensearch_client()
    vacancy = get_vacancy_by_id(client, vacancy_id)

    if not vacancy:
        return []

    candidates = list_candidates(client, size=10000)
    normalized = [normalize_candidate(item) for item in candidates]

    ranked = rerank_candidates_rule_based(vacancy, normalized)
    return ranked[:top_k]


def search_candidates_for_llm(vacancy_id: str, top_k: int = 3) -> list[dict]:
    return search_candidates_by_vacancy(vacancy_id, top_k=top_k)