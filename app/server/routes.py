import io
import json
import pdfkit
from flask import Blueprint, redirect, request, session, send_file, Response

from .data import Data
from .utils import render_template, session_error, session_success
from .session import Session
from .transcript import get_transcript_data


main_bp = Blueprint('main', __name__)

"""
Jinja variables:

- sess: None | {
	'first_name': str,
	'last_name': str,
	'login': str,
	'pic': str,
	'grade_title': str,
	'level': float[XX.XX],
	'token': None,
	'expires': None,
	'valid': False,
}
- env: {
	'TITLE': str,
	'VERSION': str,
	'DEBUG': bool,
}
- successes: list[{
	'message': str,
	... (other optional fields)
}]
- errors: list[{
	'error': str,
	'message': str,
	'code': int | None,
	... (other optional fields)
}]
"""


@main_bp.route('/')
def index():
	sess = Session.get_current()
	return render_template('index.html', sess=sess)


@main_bp.route('/auth')
def auth():
	if 'code' not in request.args:
		return redirect('/')

	code = request.args.get('code')
	sess = Session(code)
	if not sess['valid']:
		return redirect('/')

	try:
		me = Session.get(sess, '/v2/me')
		if 'error' in me:
			raise Exception()

		try:
			cu = sorted(me['cursus_users'], key=lambda x: x['begin_at'], reverse=True)[0]
			sess |= {
				'first_name': me['first_name'].upper(),
				'last_name': me['last_name'].title(),
				'login': me['login'].lower(),
				'pic': me['image']['link'],
				'grade_title': cu['grade'].title(),
				'level': cu['level'],
			}
		except Exception as e:
			session_error(f'[{e.__class__.__name__}] {e}', 'Failed to fetch user data from 42 API.', 500)
			raise Exception()
	except Exception:
			sess |= {
				'first_name': 'UNKNOWN',
				'last_name': 'Unknown',
				'login': 'unknown',
				'pic': '/client/img/42_logo.png',
				'grade_title': '',
				'level': '--.--',
			}
	session[Data.S_SESSION] = sess
	return redirect('/')


@main_bp.route('/logout')
def logout():
	session.pop(Data.S_SESSION, None)
	return redirect('/')


@main_bp.route('/transcript')
def transcript():
	sess = Session.get_current()
	if sess is None or not sess['valid']:
		return redirect('/')

	data = get_transcript_data(sess)
	if 'error' in data:
		return Response(json.dumps(data, ensure_ascii=False), mimetype='application/json')
	html = render_template('transcript.html', **data)
	result = pdfkit.from_string(html, False, options={
		'page-size': 'A4',
		'margin-top': '0.15in',
		'margin-right': '0.15in',
		'margin-bottom': '0.15in',
		'margin-left': '0.15in',
		'encoding': 'UTF-8',
		'no-outline': None,
	})
	return send_file(
		io.BytesIO(result),
		download_name=f'{data['name']}.pdf',
		mimetype='application/pdf'
	)
