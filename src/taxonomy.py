import re

TERM_MAP = {
    "golang": "go",

    "питон": "python",
    "джава": "java",
    "яваскрипт": "javascript",
    "js": "javascript",
    "тайпскрипт": "typescript",
    "ts": "typescript",

    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "scikit-learn": "scikit-learn",

    "микросервис": "microservices",
    "микросервисный": "microservices",
    "microservice": "microservices",

    "лидерство": "lead",
    "лидер": "lead",
    "тимлид": "lead",
    "тимлида": "lead",
    "тимлидер": "lead",
    "руководитель": "lead",

    "менторинг": "mentoring",
    "наставничество": "mentoring",

    "постгрес": "postgresql",
    "postgres": "postgresql",
    "pg": "postgresql",

    "монго": "mongodb",
    "mongo": "mongodb",

    "эластик": "elasticsearch",
    "elastic": "elasticsearch",

    "кубернетес": "kubernetes",
    "кубернетёс": "kubernetes",
    "кубер": "kubernetes",
    "k8s": "kubernetes",

    "докер": "docker",

    "оптимизация": "optimization",
    "проектирование": "design",
    "архитектура": "architecture",
    "архитектурный": "architecture",
    "тестирование": "testing",
    "мониторинг": "monitoring",
    "развёртывание": "deploy",
    "деплой": "deploy",
    "deployment": "deploy",

    "разработка": "development",
    "бэкенд": "backend",
    "бекенд": "backend",
    "фронтенд": "frontend",
    "фулстек": "fullstack",
    "full-stack": "fullstack",

    "скрам": "scrum",
    "аджайл": "agile",
    "канбан": "kanban",

    "распределённый": "distributed",
    "высоконагруженный": "highload",
    "масштабируемость": "scalability",
    "производительность": "performance",
    "отказоустойчивость": "fault_tolerance",

    "а/б-тестирование":'a/b testing',
    "a/b-тестирование":'a/b testing',
    "а/b-тестирование":'a/b testing',
    "а/в-тестирование":'a/b testing',
    "a/в-тестирование":'a/b testing',
    

    "llm":'llm'
}

CANONICAL_TECH_TAGS = [
    "python",
    "sql",
    "postgresql",
    "mongodb",
    "redis",
    "clickhouse",
    "airflow",
    "spark",
    "hadoop",
    "etl",
    "dwh",
    "docker",
    "kubernetes",
    "helm",
    "grafana",
    "prometheus",
    "victoriametrics",
    "vault",
    "rabbitmq",
    "kafka",
    "nats",
    "linux",
    "bash",
    "java",
    "go",
    "javascript",
    "typescript",
    ".net",
    "c++",
    "ci/cd",
    "gitlab ci/cd",
    "backend",
    "frontend",
    "fullstack",

    # ML / DS / LLM
    "pandas",
    "numpy",
    "scipy",
    "matplotlib",
    "seaborn",
    "plotly",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "catboost",
    "optuna",
    "mlflow",
    "pytorch",
    "tensorflow",
    "keras",
    "transformers",
    "opencv",
    "nltk",
    "spacy",
    "fastapi",
    "flask",
    "llm"
]

FALLBACK_TECH_TAGS = sorted(
    set(TERM_MAP.values()) | set(CANONICAL_TECH_TAGS),
    key=len,
    reverse=True,
)

_SPLIT_RE = re.compile(r"[,;/|]+")
_WORD_RE = re.compile(r"[a-zа-я0-9\.\+#\-]+", flags=re.IGNORECASE)


def normalize_term(value: str) -> str:
    value = value.lower().strip()
    return TERM_MAP.get(value, value)


def extract_tags_from_text(text: str) -> list[str]:
    if not text:
        return []

    low = text.lower()
    found = []

    for tag in FALLBACK_TECH_TAGS:
        pattern = rf"(?<!\w){re.escape(tag.lower())}(?!\w)"
        if re.search(pattern, low, flags=re.IGNORECASE):
            normalized = TERM_MAP.get(tag.lower(), tag.lower())
            if normalized not in found:
                found.append(normalized)

    return found


def normalize_tags(tags: list[str]) -> set[str]:
    result = set()

    for tag in tags:
        if not isinstance(tag, str):
            continue

        tag = tag.lower().strip()
        if not tag:
            continue

        parts = re.split(r"[,;/|]+", tag)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if " " not in part:
                token = TERM_MAP.get(part, part)
                if len(token) > 1:
                    result.add(token)
                continue

            for token in extract_tags_from_text(part):
                if len(token) > 1:
                    result.add(token)

    return result