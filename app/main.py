import os
import sys
import codecs
import json
import dotenv
import traceback
from flask import Flask, redirect
from flask_session import Session as FlaskSession

from server.data import Data
from server.utils import strbool, set_default, os_assert, session_error


def parse_args():
	for arg in sys.argv[1:]:
		if arg == '--debug':
			os.environ[Data.X_DEBUG] = '1'
			break

		if arg.startswith('--port='):
			port = arg.split('=')[1]
			try:
				port = int(port)
				if port < 1 or port > 65535:
					raise ValueError
				os.environ[Data.X_PORT] = str(port)
			except ValueError:
				print("Invalid port number. Please provide a valid port between 1 and 65535.")
				sys.exit(1)

		if os.path.exists(arg):
			dotenv.load_dotenv(arg, override=True)
			print(f"[INFO] Loaded environment file {arg}.")
		else:
			print(f"[WARN] Environment file {arg} does not exist.")


def setup_env():
	set_default(Data.X_TITLE, '42 Transcript Generator')
	set_default(Data.X_PORT, 5000)
	set_default(Data.X_DEBUG, False)
	set_default(Data.X_VERSION, '0.0.0')
	set_default(Data.X_SECRET_KEY, 'change_me')

	os_assert(Data.X_API_URL)
	os_assert(Data.X_API_OAUTH_URL)
	os_assert(Data.X_REDIRECT_URI)
	os_assert(Data.X_FT_UID)
	os_assert(Data.X_FT_SECRET)

	Data.DEBUG = strbool(os.environ[Data.X_DEBUG])


def setup_session(app: Flask):
	"""
	Session config: https://flask-session.readthedocs.io/en/latest/config.html#relevant-flask-configuration-values
	"""
	app.config['SESSION_TYPE'] = 'filesystem'
	app.config['SESSION_FILE_THRESHOLD'] = 64
	app.config['SESSION_PERMANENT'] = True
	app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
	app.config['SESSION_COOKIE_NAME'] = 'ft_tg'
	app.config['SESSION_COOKIE_HTTPONLY'] = True
	app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
	app.config['SESSION_COOKIE_SECURE'] = not Data.DEBUG
	FlaskSession(app)


def setup_routes(app: Flask):
	@app.errorhandler(404)
	def handle_not_found(e=None):
		session_error('[404] Not Found', 'The requested resource was not found.', 404)
		return redirect('/')


	@app.errorhandler(Exception)
	def handle_generic_exception(e=None):
		session_error(
			'An unexpected error occurred.', f'[{e.__class__.__name__}] {e}', 500,
			**({ 'trace': traceback.format_exc().split('\n') } if Data.DEBUG else {}),
		)
		return redirect('/')

	from server.routes import main_bp
	app.register_blueprint(main_bp)


if __name__ == '__main__':
	parse_args()
	setup_env()

	app = Flask(__name__, static_folder='client', template_folder='client/html')
	app.secret_key = codecs.decode(os.environ.get(Data.X_SECRET_KEY), 'unicode_escape').encode('latin1')

	setup_session(app)
	setup_routes(app)

	print(f"[INFO] ENV: {json.dumps(dict(os.environ), indent=4, ensure_ascii=False)}")
	print(f"[INFO] Starting server {os.environ[Data.X_TITLE]} v{os.environ.get(Data.X_VERSION, '?.?')} on port {os.environ[Data.X_PORT]} (debug={Data.DEBUG}; key={app.secret_key})")

	app.run(
		debug=Data.DEBUG,
		host='0.0.0.0',
		port=int(os.environ[Data.X_PORT]),
	)
