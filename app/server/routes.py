import os
from flask import Blueprint, redirect, request, session

from .data import Data
from .utils import render_template
from .session import Session


main_bp = Blueprint('main', __name__)


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
	if not Session.is_valid(sess):
		return redirect('/')

	session[Data.S_SESSION] = sess
	return redirect('/dashboard')


@main_bp.route('/logout')
def logout():
	session.pop(Data.S_SESSION, None)
	return redirect('/')


@main_bp.route('/dashboard')
def dashboard():
	sess = Session.get_current()
	if sess is None or not Session.is_valid(sess):
		return redirect('/')

	return render_template('dashboard.html', sess=sess)
