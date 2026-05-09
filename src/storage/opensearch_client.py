from opensearchpy import OpenSearch


def get_opensearch_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": "opensearch", "port": 9200}],
        http_auth=("admin", "bestteam1984A."),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )