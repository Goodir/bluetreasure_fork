import re
from ..taxonomy import TERM_MAP, FALLBACK_TECH_TAGS

SECTION_PATTERNS = {
    "must_have": r"(важное требование|обязательное требование)",
    "requirements": r"(требования|мы ожидаем|что ожидаем|что нужно)",
    "responsibilities": r"(обязанности|задачи|что делать|чем предстоит заниматься)",
    "conditions": r"(условия|мы предлагаем|что предлагаем)",
    "tags": r"(стек и теги|теги|стек|технологии|ключевые навыки)",
}

SECTION_HEADERS = {
    "важное требование",
    "обязательное требование",
    "требования",
    "обязанности",
    "задачи",
    "условия",
    "стек и теги",
    "стек",
    'теги',
    "технологии",
    "ключевые навыки",
}

LEVEL_TO_YEARS = {
    "intern": 0.0,
    "стажер": 0.0,
    "junior": 1.0,
    "джуниор": 1.0,
    "middle": 3.0,
    "middle+": 4.0,
    "senior": 5.0,
    "сеньор": 5.0,
    "lead": 7.0,
    "тимлид": 7.0,
}

BULLET_ONLY_RE = re.compile(r"^[•●▪◦·\-–—*]+$")
SPACE_RE = re.compile(r"\s+")
MULTI_NL_RE = re.compile(r"\n{3,}")