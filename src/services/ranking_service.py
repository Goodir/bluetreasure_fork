import numpy as np
import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from ..taxonomy import *


def extract_vacancy_tags(vacancy: dict) -> list[str]:
    return vacancy.get("tags", []) or []



def extract_candidate_tags(candidate: dict) -> list[str]:
    skills_tags = candidate.get("skills", {}).get("tools", []) or []
    if skills_tags:
        return skills_tags

    resume_text = candidate.get("resume_text", "") or ""
    return extract_tags_from_text(resume_text)


def score_jaccard_fast(vacancy_tags: List[str], resume_tags: List[str]) -> Dict[str, Any]:
    vac_set = normalize_tags(vacancy_tags)
    res_set = normalize_tags(resume_tags)

    if not vac_set:
        return {
            "score": 0.0,
            "matched": [],
            "missed": [],
            "matched_count": 0,
            "missed_count": 0,
        }

    matched = vac_set.intersection(res_set)
    missed = vac_set.difference(res_set)
    score = round(len(matched) / len(vac_set), 4)

    return {
        "score": score,
        "matched": sorted(list(matched)),
        "missed": sorted(list(missed)),
        "matched_count": len(matched),
        "missed_count": len(missed),
    }


def score_tfidf_batch(vacancy_tags: List[str], resumes_tags: List[List[str]]) -> List[Dict[str, Any]]:
    vac_str = " ".join(normalize_tags(vacancy_tags))
    res_strings = [" ".join(normalize_tags(tags)) for tags in resumes_tags]

    corpus = [vac_str] + res_strings

    try:
        vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return [
            {
                "score": 0.0,
                "matched": [],
                "missed": [],
                "matched_count": 0,
                "missed_count": 0,
            }
            for _ in resumes_tags
        ]

    feature_names = np.array(vectorizer.get_feature_names_out())

    dense_matrix = tfidf_matrix.toarray()
    vac_vec = dense_matrix[0]
    res_vecs = dense_matrix[1:]

    vac_total_weight = np.sum(vac_vec)
    if vac_total_weight == 0:
        return [
            {
                "score": 0.0,
                "matched": [],
                "missed": [],
                "matched_count": 0,
                "missed_count": 0,
            }
            for _ in resumes_tags
        ]

    results = []
    for res_vec in res_vecs:
        intersection_weights = np.minimum(vac_vec, res_vec)
        score = round(float(np.sum(intersection_weights) / vac_total_weight), 4)

        matched_indices = np.where((vac_vec > 0) & (res_vec > 0))[0]
        missed_indices = np.where((vac_vec > 0) & (res_vec == 0))[0]

        results.append({
            "score": score,
            "matched": feature_names[matched_indices].tolist(),
            "missed": feature_names[missed_indices].tolist(),
            "matched_count": int(len(matched_indices)),
            "missed_count": int(len(missed_indices)),
        })

    return results


def calculate_final_ranking(
    cosine_score: float,
    jaccard_score: float,
    tfidf_score: float,
    use_tag_metrics: bool = True,
) -> dict:
    if not use_tag_metrics:
        final_score = round(cosine_score, 4)
    else:
        final_score = round((cosine_score + jaccard_score + tfidf_score) / 3, 4)

    return {
        "final_score": final_score,
        "metrics_breakdown": {
            "cosine_similarity": round(cosine_score, 4),
            "jaccard_simple": round(jaccard_score, 4),
            "jaccard_tfidf": round(tfidf_score, 4),
        },
    }


def cosine_from_vectors(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2:
        return 0.0
    return round(float(np.dot(v1, v2)), 4)


def rerank_candidates_rule_based(vacancy: dict, candidates: list[dict]) -> list[dict]:
    vacancy_tags = extract_vacancy_tags(vacancy)
    vacancy_vector = vacancy.get("vacancy_vector") or []
    resumes_tags_batch = [extract_candidate_tags(candidate) for candidate in candidates]
    tfidf_results = score_tfidf_batch(vacancy_tags, resumes_tags_batch)

    ranked = []
    use_tag_metrics = bool(normalize_tags(vacancy_tags))

    for i, candidate in enumerate(candidates):
        candidate_tags = extract_candidate_tags(candidate)
        candidate_vector = candidate.get("resume_vector") or []

        cosine_score = cosine_from_vectors(vacancy_vector, candidate_vector)
        jaccard_result = score_jaccard_fast(vacancy_tags, candidate_tags)
        tfidf_score = tfidf_results[i]["score"]

        ranking = calculate_final_ranking(
            cosine_score=cosine_score,
            jaccard_score=jaccard_result["score"],
            tfidf_score=tfidf_score,
            use_tag_metrics=use_tag_metrics,
        )

        candidate_copy = candidate.copy()
        candidate_copy["final_score"] = ranking["final_score"]
        candidate_copy["ranking"] = ranking
        candidate_copy["matched_tags"] = jaccard_result["matched"]
        candidate_copy["missed_tags"] = jaccard_result["missed"]

        ranked.append(candidate_copy)

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked