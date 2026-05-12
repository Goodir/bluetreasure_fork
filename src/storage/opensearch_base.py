from opensearchpy import helpers


def create_index_if_not_exists(client, index_name: str, mapping: dict) -> None:
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=mapping)


def document_exists(client, index_name: str, doc_id: str) -> bool:
    return client.exists(index=index_name, id=doc_id)

def delete_index_if_exists(client, index_name: str) -> bool:
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        return True
    return False


def index_document(client, index_name: str, doc_id: str, doc: dict) -> None:
    client.index(index=index_name, id=doc_id, body=doc, refresh="wait_for")


def get_document_by_id(client, index_name: str, doc_id: str) -> dict | None:
    if not client.exists(index=index_name, id=doc_id):
        return None

    response = client.get(index=index_name, id=doc_id)
    return response["_source"]


def list_documents(client, index_name: str, size: int = 100) -> list[dict]:
    response = client.search(
        index=index_name,
        body={
            "size": size,
            "query": {
                "match_all": {}
            }
        }
    )

    result = []
    for hit in response["hits"]["hits"]:
        doc = hit["_source"]
        doc["_id"] = hit["_id"]
        result.append(doc)

    return result


def search_documents(client, index_name: str, query_body: dict) -> list[dict]:
    response = client.search(index=index_name, body=query_body)

    result = []
    for hit in response["hits"]["hits"]:
        doc = hit["_source"]
        doc["_id"] = hit["_id"]
        doc["_score"] = hit["_score"]
        result.append(doc)

    return result


def bulk_index_documents(client, docs: dict[str, dict], index_name: str) -> int:
    actions = []

    for doc_id, doc in docs.items():
        actions.append({
            "_op_type": "index",
            "_index": index_name,
            "_id": doc_id,
            "_source": doc,
        })

    if not actions:
        return 0

    helpers.bulk(client, actions, refresh="wait_for")
    return len(actions)


def bulk_update_documents(client, updates: dict[str, dict], index_name: str) -> int:
    actions = []

    for doc_id, fields in updates.items():
        actions.append({
            "_op_type": "update",
            "_index": index_name,
            "_id": doc_id,
            "doc": fields,
        })

    if not actions:
        return 0

    helpers.bulk(client, actions)
    return len(actions)