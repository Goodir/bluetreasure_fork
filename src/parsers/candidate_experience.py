import re
from candidate_constants import *
from candidate_common import *


def parse_total_years(text: str) -> int | None:
    m = re.search(r"опыт работы\s*[—-]\s*(\d+)\s*(год|года|лет)", normalize_text(text).lower())
    return int(m.group(1)) if m else None


def parse_month_year(text: str) -> str | None:
    m = re.match(rf"^({MONTH_ALT})\s+(\d{{4}})$", normalize_text(text).lower())
    if not m:
        return None
    return f"{m.group(2)}-{RU_MONTHS[m.group(1)]}"


def parse_date_block(text: str) -> dict | None:
    m = DATE_BLOCK_RE.match(normalize_text(text).lower())
    if not m:
        return None

    start_date = parse_month_year(f"{m.group(1)} {m.group(2)}")
    end_date = None if m.group(3) == "настоящее время" else parse_month_year(m.group(3))

    return {
        "start_date": start_date,
        "end_date": end_date,
        "duration": m.group(5),
    }


def split_company_and_info(text: str) -> tuple[str, str | None]:
    text = normalize_text(text)
    low = text.lower()

    markers = [
        " www.",
        " http",
        " информационные технологии",
        " финансовый сектор",
        " розничная торговля",
        " гостиницы, рестораны",
        " товары народного потребления",
        " образовательные учреждения",
        " услуги для бизнеса",
        " добывающая отрасль",
        " • ",
    ]

    positions = [low.find(marker) for marker in markers if low.find(marker) != -1]
    if not positions:
        return text, None

    idx = min(positions)
    company = text[:idx].strip(" ,")
    company_info = text[idx:].strip()

    return company, company_info if company_info else None


def extract_experience_texts(blocks: list[dict]) -> tuple[int | None, list[str]]:
    total_years = None

    for block in blocks:
        text = normalize_text(block["text"])
        if text.startswith("Опыт работы"):
            total_years = parse_total_years(text)
            break

    texts = extract_section_texts(
        blocks,
        start_marker="Опыт работы",
        end_markers=EXPERIENCE_END_MARKERS,
    )

    return total_years, texts


def parse_experience_from_blocks(blocks: list[dict]) -> dict:
    years, texts = extract_experience_texts(blocks)
    positions = []

    i = 0
    while i < len(texts):
        date_info = parse_date_block(texts[i])
        if not date_info:
            i += 1
            continue

        if i + 2 >= len(texts):
            break

        company, company_info = split_company_and_info(texts[i + 1])
        role = texts[i + 2]

        i += 3
        responsibilities = []

        while i < len(texts) and not parse_date_block(texts[i]):
            responsibilities.append(texts[i].lstrip("•").strip())
            i += 1

        positions.append({
            "company": company,
            "company_info": company_info,
            "role": role,
            "start_date": date_info["start_date"],
            "end_date": date_info["end_date"],
            "responsibilities": responsibilities,
        })

    return {
        "years": years,
        "positions": positions,
    }
