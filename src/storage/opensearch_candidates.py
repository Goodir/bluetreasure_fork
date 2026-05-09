def create_index_if_not_exists(client, index_name: str, mapping: dict):
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=mapping)
        print(f"Index '{index_name}' created")
    else:
        print(f"Index '{index_name}' already exists")


from opensearchpy import helpers


def bulk_index_candidates(client, docs: dict[str, dict], index_name: str = "candidates",) -> int:
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

    helpers.bulk(client, actions)
    return len(actions)


def bulk_update_candidates(client, updates: dict[str, dict], index_name: str = "candidates",) -> int:
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