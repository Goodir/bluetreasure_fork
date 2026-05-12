import re


RU_MONTHS = {
    "январь": "01",
    "февраль": "02",
    "март": "03",
    "апрель": "04",
    "май": "05",
    "июнь": "06",
    "июль": "07",
    "август": "08",
    "сентябрь": "09",
    "октябрь": "10",
    "ноябрь": "11",
    "декабрь": "12",
}

MONTH_ALT = "|".join(RU_MONTHS)

DATE_BLOCK_RE = re.compile(
    rf"^({MONTH_ALT})\s+(\d{{4}})\s+[—-]\s+(({MONTH_ALT})\s+\d{{4}}|настоящее время)\s+(.+)$",
    re.IGNORECASE
)

LANG_RE = re.compile(
    r"([А-ЯЁA-Z][А-ЯЁа-яёA-Za-z]+)\s*—\s*"
    r"(A1|A2|B1|B2|C1|C2|Родной|Начальный|Элементарный|Средний|Средне-продвинутый|Продвинутый)"
    r"(?:\s*—\s*([А-ЯЁа-яёA-Za-z\-]+))?",
    re.IGNORECASE
)

KNOWN_MULTIWORD_SKILLS = [
    "REST API",
    "Unit Testing",
    "Clean Architecture",
    "Английский язык",
    "Django Rest Framework",
    "Django Framework",
    "Machine Learning",
    "Deep Learning",
    "Computer Vision",
    "Natural Language Processing",
    "Prompt Engineering",
    "Feature Engineering",
    "A/B Testing",
]

TAIL_END_MARKERS = (
    "Дополнительная информация",
    "История общения с кандидатом",
    "Комментарии к резюме",
)

EXPERIENCE_END_MARKERS = (
    "Образование",
    "Ключевые навыки",
    "Дополнительная информация",
    "История общения с кандидатом",
    "Комментарии к резюме",
)

CONTACT_STOP_MARKERS = (
    "Гражданство:",
    "есть разрешение на работу:",
    "Хочу переехать",
    "Готов к переезду",
    "Не готов к переезду",
    "готов к командировкам",
    "не готов к командировкам",
)

LANG_HINTS = ("Русский", "Английский", "Китайский", "Испанский")