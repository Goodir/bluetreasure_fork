import re
from candidate_common import *
from candidate_constants import *



def build_header_text(blocks: list[dict]) -> str:
    parts = []

    for block in blocks:
        text = normalize_text(block["text"])
        if not text:
            continue

        if "Желаемая должность и зарплата" in text:
            break

        parts.append(text)

    return "\n".join(parts)


def extract_name(lines: list[str]) -> str | None:
    banned_words = (
        "мужчина", "женщина", "родился", "родилась",
        "проживает", "гражданство", "разрешение на работу",
        "переезду", "командировкам", "@", "+7", "8 ("
    )

    for line in lines[:5]:
        low = line.lower()
        if any(word in low for word in banned_words):
            continue

        words = line.split()
        if 2 <= len(words) <= 4:
            return line

    return None


def extract_age(text: str) -> int | None:
    m = re.search(r"(\d+)\s*(лет|года|год)\b", text.lower())
    return int(m.group(1)) if m else None


def extract_phone(text: str) -> str | None:
    m = re.search(r"(\+7|8)\s*\(?\d{3}\)?[\s-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}", text)
    return m.group(0) if m else None


def extract_email(text: str) -> str | None:
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return m.group(0) if m else None


def extract_location(text: str) -> str | None:
    return extract_field_after_label(text, "Проживает", CONTACT_STOP_MARKERS)


def extract_citizenship(text: str) -> str | None:
    return extract_field_after_label(text, "Гражданство", CONTACT_STOP_MARKERS)


def extract_work_permission(text: str) -> str | None:
    return extract_field_after_label(text, "разрешение на работу", CONTACT_STOP_MARKERS)


def parse_top_block(blocks: list[dict]) -> dict:
    header_text = build_header_text(blocks)
    lines = [line.strip() for line in header_text.split("\n") if line.strip()]

    return {
        "name": extract_name(lines),
        "age": extract_age(header_text),
        "contacts": {
            "location": extract_location(header_text),
            "citizenship": extract_citizenship(header_text),
            "work_permission": extract_work_permission(header_text),
            "phone": extract_phone(header_text),
            "email": extract_email(header_text),
        },
    }