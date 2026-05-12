from .opensearch_base import (
    create_index_if_not_exists,
    document_exists,
    index_document,
    get_document_by_id,
    list_documents,
    search_documents,
    bulk_index_documents,
    bulk_update_documents,
    delete_index_if_exists
)

CANDIDATES_INDEX = "candidates"

CANDIDATES_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "knn": True,
        }
    },
    "mappings": {
        "properties": {
            "name": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "age": {
                "type": "integer"
            },
            "contacts": {
                "properties": {
                    "location": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "citizenship": {
                        "type": "keyword"
                    },
                    "work_permission": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "phone": {
                        "type": "keyword"
                    },
                    "email": {
                        "type": "keyword"
                    }
                }
            },
            "experience": {
                "properties": {
                    "years": {
                        "type": "integer"
                    },
                    "positions": {
                        "type": "nested",
                        "properties": {
                            "company": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "company_info": {
                                "type": "text"
                            },
                            "role": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "start_date": {
                                "type": "date",
                                "format": "yyyy-MM"
                            },
                            "end_date": {
                                "type": "date",
                                "format": "yyyy-MM"
                            },
                            "responsibilities": {
                                "type": "text"
                            }
                        }
                    }
                }
            },
            "skills": {
                "properties": {
                    "tools": {
                        "type": "keyword"
                    },
                    "languages": {
                        "type": "keyword"
                    }
                }
            },
            "education": {
                "properties": {
                    "institution": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "degree": {
                        "type": "keyword"
                    },
                    "specialization": {
                        "type": "text"
                    },
                    "year": {
                        "type": "integer"
                    }
                }
            },
            "achievements": {
                "type": "text"
            },
            "english_level": {
                "type": "keyword"
            },
            "driving_categories": {
                "type": "keyword"
            },
            "resume_text_orig": {
                "type": "text",
                "index": False
            },
            "resume_text": {
                "type": "text"
            },
            "resume_vector": {
                "type": "knn_vector",
                "dimension": 768
            },
            "source_file": {
                "type": "keyword"
            }
        }
    }
}


def create_candidates_index_if_not_exists(client) -> None:
    create_index_if_not_exists(client, CANDIDATES_INDEX, CANDIDATES_MAPPING)


def candidate_exists(client, candidate_id: str) -> bool:
    return document_exists(client, CANDIDATES_INDEX, candidate_id)


def index_candidate(client, candidate_id: str, doc: dict) -> None:
    index_document(client, CANDIDATES_INDEX, candidate_id, doc)


def get_candidate_by_id(client, candidate_id: str) -> dict | None:
    return get_document_by_id(client, CANDIDATES_INDEX, candidate_id)


def list_candidates(client, size: int = 100) -> list[dict]:
    return list_documents(client, CANDIDATES_INDEX, size=size)


def search_candidates(client, query_body: dict) -> list[dict]:
    return search_documents(client, CANDIDATES_INDEX, query_body)


def bulk_index_candidates(client, docs: dict[str, dict]) -> int:
    return bulk_index_documents(client, docs, CANDIDATES_INDEX)


def bulk_update_candidates(client, updates: dict[str, dict]) -> int:
    return bulk_update_documents(client, updates, CANDIDATES_INDEX)

def clear_candidates_index(client) -> bool:
    return delete_index_if_exists(client, CANDIDATES_INDEX)