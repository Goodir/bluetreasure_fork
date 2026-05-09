import fitz
import re

import candidate_common


def normalize_text(text: str) -> str:
    return " ".join(
        text.replace("\xa0", " ")
        .replace("\n", " ")
        .replace("\u200b", " ")
        .split()
    )


def unique_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def extract_field_after_label(text: str, label: str, stop_markers: tuple[str, ...]) -> str | None:
    stop_pattern = "|".join(re.escape(x) for x in stop_markers)
    pattern = rf"{re.escape(label)}:\s*(.+?)(?=\s+(?:{stop_pattern})|$)"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1).strip(" ,") if m else None


def extract_section_texts(
    blocks: list[dict],
    start_marker: str,
    end_markers: tuple[str, ...],
) -> list[str]:
    started = False
    result = []

    for block in blocks:
        text = normalize_text(block["text"])

        if not text or "Резюме обновлено" in text:
            continue

        if not started:
            if text.startswith(start_marker):
                started = True
            continue

        if text.startswith(end_markers):
            break

        result.append(text)

    return result


# =========================
# EXTRACTION
# =========================

def read_resume_pdf_raw(pdf_path: str) -> dict:
    pages_text = []
    blocks_all = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = normalize_text(page.get_text())
            if page_text:
                pages_text.append(page_text)

            for block in page.get_text("blocks"):
                text_block = normalize_text(block[4])
                if text_block:
                    blocks_all.append({
                        "page": page_num,
                        "text": text_block,
                        "bbox": block[:4],
                    })

    return {
        "raw_text": "\n".join(pages_text),
        "blocks": blocks_all,
    }