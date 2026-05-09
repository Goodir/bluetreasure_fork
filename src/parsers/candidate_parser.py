from candidate_top import *
from candidate_experience import *
from candidate_tail import *


def parse_resume(data: dict) -> dict:
    blocks = data["blocks"]
    raw_text = data["raw_text"]

    top = parse_top_block(blocks)
    exp = parse_experience_from_blocks(blocks)
    tail = parse_tail_from_blocks(blocks, exp["positions"])

    return {
        "name": top["name"],
        "age": top["age"],
        "contacts": top["contacts"],
        "experience": exp,
        "skills": tail["skills"],
        "education": tail["education"],
        "achievements": tail["achievements"],
        "english_level": tail["english_level"],
        "driving_categories": tail["driving_categories"],
        "resume_text_orig": raw_text,
    }