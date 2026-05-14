from flask import Blueprint, request, render_template, flash, redirect, url_for, session
import uuid
import redis
import json
import markdown

from .services.candidate_service import (
    ingest_candidate_pdfs,
    ingest_candidate_texts_via_llm,
    list_candidates as list_candidates_service,
    clear_candidates_index as clear_candidates_index_service,
)
from .services.vacancy_service import (
    list_vacancies,
    save_vacancy_from_text,
    save_vacancy_from_pdf,
    get_vacancy_by_id,
    clear_vacancies_index as clear_vacancies_index_service,
)
from .services.search_service import search_candidates_by_vacancy, search_candidates_for_llm
from .llm_request import request_llm_final

webstart = Blueprint("webstart", __name__)
r = redis.Redis(host="redis", port=6379, decode_responses=True)


def render_llm_results(llm_results: list[dict]) -> list[dict]:
    return [
        {
            "candidate_title": item["candidate_title"],
            "response_html": markdown.markdown(
                item["response"],
                extensions=["nl2br", "tables"]
            )
        }
        for item in llm_results
    ]


def ensure_session_id() -> str:
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def redis_set_json(key: str, value, ttl: int = 1800) -> None:
    r.setex(key, ttl, json.dumps(value, ensure_ascii=False))


def redis_get_json(key: str):
    raw = r.get(key)
    if not raw:
        return None
    return json.loads(raw)


@webstart.route("/", methods=["GET"])
def start_page():
    return render_template("start.html")


@webstart.route("/vacancies", methods=["GET", "POST"])
def vacancies_page():
    ensure_session_id()

    if request.method == "POST":
        vacancy_text = request.form.get("vacancy_text", "").strip()
        vacancy_pdf = request.files.get("vacancy_pdf")

        if vacancy_pdf and vacancy_pdf.filename:
            result = save_vacancy_from_pdf(vacancy_pdf)
            flash(result["message"], "success")
            return redirect(url_for("webstart.vacancies_page"))

        if vacancy_text:
            result = save_vacancy_from_text(vacancy_text)
            flash(result["message"], "success")
            return redirect(url_for("webstart.vacancies_page"))

        flash("Нужно вставить текст вакансии или загрузить PDF", "error")
        return redirect(url_for("webstart.vacancies_page"))

    vacancies = list_vacancies()
    return render_template("vacancies.html", vacancies=vacancies)


@webstart.route("/vacancies/clear", methods=["POST"])
def clear_vacancies():
    deleted = clear_vacancies_index_service()
    flash(
        "Индекс вакансий очищен" if deleted else "Индекс вакансий уже пуст",
        "success",
    )
    return redirect(url_for("webstart.vacancies_page"))


@webstart.route("/candidates/upload", methods=["GET", "POST"])
def candidates_upload_page():
    ensure_session_id()

    if request.method == "POST":
        files = request.files.getlist("candidate_pdfs")
        files = [f for f in files if f and f.filename]
        candidate_texts = request.form.get("candidate_texts", "").strip()

        if files:
            result = ingest_candidate_pdfs(files)
        elif candidate_texts:
            result = ingest_candidate_texts_via_llm(candidate_texts)
        else:
            flash("Нужно выбрать хотя бы один PDF или вставить текст резюме", "error")
            return redirect(url_for("webstart.candidates_upload_page"))

        redis_set_json(f"candidate_upload:{session['session_id']}", result, ttl=1800)

        flash(
            f"Загружено: {result['loaded']}, дублей: {result['duplicates']}, ошибок: {result['errors']}",
            "success",
        )
        return redirect(url_for("webstart.candidates_upload_page"))

    report = redis_get_json(f"candidate_upload:{ensure_session_id()}")
    candidates = list_candidates_service()

    return render_template(
        "candidate_upload.html",
        report=report,
        candidates=candidates,
    )


@webstart.route("/candidates/clear", methods=["POST"])
def clear_candidates():
    deleted = clear_candidates_index_service()
    flash(
        "Индекс резюме очищен" if deleted else "Индекс резюме уже пуст",
        "success",
    )
    return redirect(url_for("webstart.candidates_upload_page"))


@webstart.route("/search", methods=["GET", "POST"])
def search_page():
    ensure_session_id()

    vacancies = list_vacancies()
    search_key = f"candidate_search:{session['session_id']}"

    selected_vacancy_id = None
    search_results = None
    selected_vacancy = None

    if request.method == "POST":
        vacancy_id = request.form.get("vacancy_id", "").strip()
        top_k_raw = request.form.get("top_k", "20").strip()

        if not vacancy_id:
            flash("Нужно выбрать вакансию", "error")
            return redirect(url_for("webstart.search_page"))

        try:
            top_k = int(top_k_raw)
        except ValueError:
            top_k = 20

        selected_vacancy = get_vacancy_by_id(vacancy_id)
        if not selected_vacancy:
            flash("Вакансия не найдена", "error")
            return redirect(url_for("webstart.search_page"))

        search_results = search_candidates_by_vacancy(vacancy_id, top_k=top_k)

        payload = {
            "vacancy_id": vacancy_id,
            "top_k": top_k,
            "results": search_results,
        }
        redis_set_json(search_key, payload, ttl=1800)
        selected_vacancy_id = vacancy_id

        return render_template(
            "search.html",
            vacancies=vacancies,
            selected_vacancy_id=selected_vacancy_id,
            selected_vacancy=selected_vacancy,
            search_results=search_results,
        )

    cached = redis_get_json(search_key)
    if cached:
        selected_vacancy_id = cached.get("vacancy_id")
        search_results = cached.get("results")
        if selected_vacancy_id:
            selected_vacancy = get_vacancy_by_id(selected_vacancy_id)

    return render_template(
        "search.html",
        vacancies=vacancies,
        selected_vacancy_id=selected_vacancy_id,
        selected_vacancy=selected_vacancy,
        search_results=search_results,
    )


@webstart.route("/llmquery", methods=["GET", "POST"])
def best_candidates():
    ensure_session_id()

    vacancies = list_vacancies()
    search_key = f"candidate_search:{session['session_id']}"
    selected_vacancy_id = None
    search_results = None
    selected_vacancy = None

    if request.method == "POST":
        vacancy_id = request.form.get("vacancy_id", "").strip()
        top_k_raw = request.form.get("top_k", "3").strip()

        if not vacancy_id:
            flash("Нужно выбрать вакансию", "error")
            return redirect(url_for("webstart.best_candidates"))

        try:
            top_k = int(top_k_raw)
        except ValueError:
            top_k = 3

        selected_vacancy = get_vacancy_by_id(vacancy_id)
        if not selected_vacancy:
            flash("Вакансия не найдена", "error")
            return redirect(url_for("webstart.best_candidates"))

        search_results = search_candidates_for_llm(vacancy_id, top_k=top_k)
        payload = {
            "vacancy_id": vacancy_id,
            "top_k": top_k,
            "results": search_results,
        }
        redis_set_json(search_key, payload, ttl=1800)
        selected_vacancy_id = vacancy_id

        llm_response = request_llm_final(selected_vacancy["vacancy_text"], search_results)
        fin_result = render_llm_results(llm_response)

        return render_template(
            "info.html",
            vacancies=vacancies,
            llm_response=fin_result,
            selected_vacancy=selected_vacancy,
            selected_vacancy_id=selected_vacancy_id,
            top_k=top_k,
        )

    cached = redis_get_json(search_key)
    if cached:
        selected_vacancy_id = cached.get("vacancy_id")
        search_results = cached.get("results")
        if selected_vacancy_id:
            selected_vacancy = get_vacancy_by_id(selected_vacancy_id)

    return render_template(
        "search_llm.html",
        vacancies=vacancies,
        selected_vacancy_id=selected_vacancy_id,
        selected_vacancy=selected_vacancy,
    )