from flask import Blueprint, request, render_template, flash, redirect, url_for, session
import uuid
from .llm_request import request_llm_final
from .save_vacanсy import create_index
from .llm_request_for_opensearch import request_llm
from .list_objects import show_objects
import time
import redis
import json
webstart = Blueprint('webstart', __name__)

r = redis.Redis(host='redis', port=6379, decode_responses=True)
@webstart.route('/', methods=['GET'])
def start_page():
    return render_template('start.html')

@webstart.route('/', methods=['POST'])
def start_page_post():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        vacancy_text = form_data['vacancy_info']
        cand_info = form_data['cand_info']
        if len(vacancy_text) < 30 or len(cand_info) < 30:
            flash('Введите данные вакансии и/или данные кандидата', 'error')
            return redirect(url_for('webstart.start_page'))
        session.permanent = True
        sess_id = str(uuid.uuid4())
        session['session_id'] = sess_id
        # Запись значений в Redis
        r.setex(
            name=f"result:{sess_id}",
            time=900,
            value=cand_info,

        )
        session['vacancy_text'] = vacancy_text
        # session['cand_info'] = cand_info

        return redirect(url_for('webstart.request_info'))
    return redirect(url_for('webstart.start_page'))


@webstart.route('/info', methods=['GET'])
def request_info():
    if request.method == 'GET':
        vacancy_text = session['vacancy_text']
        # cand_info = session['cand_info']
        cand_info = r.get(f"result:{session['session_id']}")
        print(f"Инфо о кандидате: {cand_info}")
        if not session.get('session_id'):
            return redirect(url_for('webstart.start_page'))
        if not cand_info:
            flash("Данные отсутствуют", 'error')
            return redirect(url_for('webstart.start_page'))
        create_index(vacancy_text)
        result = request_llm(cand_info)
        print(result)
        time.sleep(2)
        if result == 0:
            flash('Ошибка подключения к серверу', 'error')
            return redirect(url_for('webstart.start_page'))
        vac_text, cand_text = show_objects()
        return render_template('object_list.html', vac_text=vac_text, cand_text=cand_text)
    return redirect(url_for('webstart.start_page'))






