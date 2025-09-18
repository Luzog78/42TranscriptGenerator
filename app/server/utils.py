import os
import sys
import urllib.parse
from flask import session, render_template as flask_render_template

from .data import Data


def strbool(s: str | int | bool | None, strict: bool = False) -> bool | None:
	"""
	Convert a string to a boolean value.

	Args:
		s (str): The string to convert. Accepts 'true', 'false', '1', '0', 'yes', 'no', 'y', 'n', 'on', 'off'.
		strict (bool): If True, returns None for unrecognized strings. If False, treats unrecognized strings as False.

	Returns:
		bool: True or False based on the input string or None if strict is True and the string is unrecognized.
	"""
	if s is None:
		return None if strict else False
	if isinstance(s, bool):
		return s
	if not isinstance(s, int | float):
		return s != 0
	if s.lower() in ('true', '1', 'yes', 'y', 'on'):
		return True
	elif not strict or s.lower() in ('false', '0', 'no', 'n', 'off'):
		return False
	return None


def set_default(var: str, value, env: dict | os._Environ | None = None) -> None:
	"""
	Set the environment variable `var` to `value` if it is not already set in `env`.

	Args:
		var (str): The name of the environment variable.
		value: The value to set if the variable is not already set.
		env (dict | os._Environ | None): The environment dictionary (e.g., os.environ).
	"""
	if env is None:
		env = os.environ
	if var not in env:
		env[var] = str(value)


def os_assert(variable: str) -> None:
	"""
	Assert that the environment variable `variable` is set.
	If not, print an error message and exit the program.
	"""
	if os.environ.get(variable) is None:
		print(f"[FATAL] Environment variable {variable} must be set.")
		sys.exit(1)


def get_url(url, *args, **kwargs):
	"""
	Construct a URL with optional query parameters and an optional base API URL.

	If `url`:
		- starts with 'http://' or 'https://', it is treated as a full URL.
		- starts with '/', it is treated as an absolute path appended to the base API URL.
		- starts with '~/', the '~' is removed and it is treated as an local absolute path.
		- otherwise, it is treated as a local relative path.

	Args:
		url (str): The base URL or endpoint.
		*args: Positional arguments to be added as query parameters.
		**kwargs: Keyword arguments to be added as query parameters.

	Returns:
		str: The constructed URL with query parameters.
	"""
	SAFE = '$@?![]:+-_,'
	quote = urllib.parse.quote
	if args or kwargs:
		url += '?'
	for arg in args:
		url += quote(f'{arg}', safe=SAFE) + '&'
	for k, v in kwargs.items():
		url += quote(f'{k}', safe=SAFE) + '=' + quote(f'{v}', safe=SAFE) + '&'
	if args or kwargs:
		url = url[:-1]
	if url.startswith('/'):
		url = os.environ.get(Data.X_API_URL) + url
	elif url.startswith('~/'):
		url = url[1:]
	return url


def session_error(
		error: dict | str | None,
		message: str | None = None,
		code: int | None = None,
		**kwargs,
		) -> dict:
	try:
		e = error.get('error', error.get('message'))
		m = error.get('error_description', error.get('description', error.get('text', error.get('message'))))
		c = error.get('status_code', error.get('status', error.get('code')))

		if m is None and message is not None:
			m = message
		if c is None and code is not None:
			c = code

		is_dict = True
	except Exception:
		e = error
		m = message
		c = code
		is_dict = False

	if e is None and m is None and c is None:
		raise Exception("No valid error information found.")

	try:
		c = int(c)
	except Exception:
		pass

	if e is None:
		if m is None:
			e = f"[{c}] Unknown error"
			m = f"Error code {c} with no message."
		elif c is None:
			e = f"Error: {m}"
		else:
			e = f"[{c}] {m}"
	elif m is None:
		m = e

	obj = {
		'error': str(e),
		'message': str(m),
		'code': c,
	}

	if not Data.S_ERRORS in session:
		session[Data.S_ERRORS] = []
	session[Data.S_ERRORS].append(kwargs | obj)

	return kwargs | (error if is_dict else obj)


def session_success(message: str, **kwargs) -> None:
	if not Data.S_SUCCESSES in session:
		session[Data.S_SUCCESSES] = []
	session[Data.S_SUCCESSES].append(kwargs | {
		'message': str(message),
	})


def pop_session_errors() -> list[dict]:
	if Data.S_ERRORS in session:
		errs = session[Data.S_ERRORS]
		session.pop(Data.S_ERRORS, None)
		return errs
	return []


def pop_session_successes() -> list[dict]:
	if Data.S_SUCCESSES in session:
		succs = session[Data.S_SUCCESSES]
		session.pop(Data.S_SUCCESSES, None)
		return succs
	return []


def render_template(template_name: str, /, pop_feedbacks: bool = True, **context) -> str:
	"""
	Render a template with the given context, optionally popping session feedback messages.

	Args:
		template_name (str): The name of the template to render.
		pop_feedbacks (bool): If True, pop session errors and successes into the context.
		**context: Additional context variables to pass to the template.

	Returns:
		str: The rendered template as a string.
	"""
	if 'env' not in context:
		context['env'] = os.environ
	if pop_feedbacks and 'errors' not in context and 'successes' not in context:
		context['errors'] = pop_session_errors()
		context['successes'] = pop_session_successes()
	return flask_render_template(template_name, **context)
