import re
from candidate_constants import *
from candidate_common import *


def parse_languages_from_text(text: str) -> list[tuple[str, str]]:
    text = normalize_text(text).replace("Знание языков", "").strip()

    result = []
    for m in LANG_RE.finditer(text):
        lang = m.group(1).strip()
        level_main = m.group(2).strip()
        level_extra = m.group(3).strip() if m.group(3) else None
        level = level_main if not level_extra else f"{level_main} — {level_extra}"
        result.append((lang, level))

    return result


def parse_tools_text(tools_text: str) -> list[str]:
    rest = normalize_text(tools_text)
    multiword_found = []

    for skill in KNOWN_MULTIWORD_SKILLS:
        if skill in rest:
            multiword_found.append(skill)
            rest = rest.replace(skill, " ")

    tokens = [x.strip() for x in re.split(r"[,\s]+", rest) if x.strip()]
    banned = {"Навыки", "Знание", "языков", "Права", "категории"}
    tokens = [x for x in tokens if x not in banned]

    return unique_preserve_order(multiword_found + tokens)


def add_language_pairs(
    pairs: list[tuple[str, str]],
    languages: list[str],
    english_level: str | None,
) -> str | None:
    for lang, level in pairs:
        languages.append(lang)
        if lang.lower() == "английский":
            english_level = level
    return english_level


def parse_skills_and_languages(blocks: list[dict]) -> tuple[dict, str | None]:
    texts = extract_section_texts(
        blocks,
        start_marker="Ключевые навыки",
        end_markers=("Опыт вождения",) + TAIL_END_MARKERS,
    )

    languages = []
    english_level = None
    tool_parts = []

    for text in texts:
        text = normalize_text(text)

        if "Знание языков" in text:
            english_level = add_language_pairs(
                parse_languages_from_text(text),
                languages,
                english_level,
            )
            continue

        if "—" in text and any(lang in text for lang in LANG_HINTS):
            english_level = add_language_pairs(
                parse_languages_from_text(text),
                languages,
                english_level,
            )
            continue

        if text.startswith("Навыки"):
            tool_parts.append(text.replace("Навыки", "", 1).strip())
        elif tool_parts:
            tool_parts.append(text)

    return {
        "tools": parse_tools_text(" ".join(tool_parts)) if tool_parts else [],
        "languages": unique_preserve_order(languages),
    }, english_level


def parse_education(blocks: list[dict]) -> dict:
    texts = extract_section_texts(
        blocks,
        start_marker="Образование",
        end_markers=("Ключевые навыки", "Опыт вождения") + TAIL_END_MARKERS,
    )

    if not texts:
        return {
            "institution": None,
            "degree": None,
            "specialization": None,
            "year": None,
        }

    degree = normalize_text(texts[0])
    year = None
    institution = None
    specialization = None

    for i, text in enumerate(texts[1:], start=1):
        text = normalize_text(text)
        m = re.match(r"^(\d{4})\s+(.+)$", text)
        if not m:
            continue

        year = int(m.group(1))
        institution = m.group(2).strip()

        if i + 1 < len(texts):
            next_text = normalize_text(texts[i + 1])
            if not re.match(r"^\d{4}\s+.+$", next_text):
                specialization = next_text

        break

    return {
        "institution": institution,
        "degree": degree,
        "specialization": specialization,
        "year": year,
    }


def parse_driving_categories(blocks: list[dict]) -> list[str]:
    texts = extract_section_texts(
        blocks,
        start_marker="Опыт вождения",
        end_markers=TAIL_END_MARKERS,
    )

    if not texts:
        return []

    joined = " ".join(texts)
    m = re.search(r"Права категории\s+([A-ZА-Я,\s]+)", joined)
    if not m:
        return []

    return [x.strip() for x in m.group(1).split(",") if x.strip()]


def parse_achievements_from_positions(positions: list[dict]) -> list[str]:
    result = []

    for pos in positions:
        for line in pos.get("responsibilities", []):
            line = normalize_text(line)
            low = line.lower()

            if (
                re.search(r"\d|%|\$|млн|раз", low)
                or "с нуля" in low
                or "увелич" in low
                or "ускор" in low
                or "сниз" in low
                or "оптимиз" in low
                or "помог" in low
                or "автомат" in low
                or "реализ" in low
                or "разработал" in low
                or "спроектировал" in low
            ):
                if line not in result:
                    result.append(line)

    return result


def parse_tail_from_blocks(blocks: list[dict], positions: list[dict]) -> dict:
    skills, english_level = parse_skills_and_languages(blocks)

    return {
        "skills": skills,
        "education": parse_education(blocks),
        "achievements": parse_achievements_from_positions(positions),
        "english_level": english_level,
        "driving_categories": parse_driving_categories(blocks),
    }