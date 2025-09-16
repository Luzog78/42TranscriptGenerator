import os
import time
import json
import requests
from flask import session

from .data import Data
from .utils import session_error, session_success
from .utils import get_url, strbool


class Session:
	@staticmethod
	def get_current() -> dict | None:
		return session.get(Data.S_SESSION, None)
		# sess = session.get(Data.S_SESSION)
		# if sess is not None and isinstance(sess, Session):
		# 	if sess.is_valid():
		# 		return sess
		# 	session.pop(Data.S_SESSION, None)
		# return None

	def __new__(self, code: str = None, fetch_token: bool = True):
		sess = {
			'code': code,
			'token': None,
			'refresh': None,
			'created': None,
			'expires': None,
		}

		if fetch_token and code is not None:
			self.fetch_token(sess)

		return sess

	@staticmethod
	def is_valid(sess: dict, split_time_validity: bool = False) -> bool | tuple[bool, bool]:
		if split_time_validity:
			return sess.get('code') is not None and sess.get('expires') is not None, sess.get('expires', 0) > time.time()
		return sess.get('code') is not None and sess.get('expires') is not None and sess.get('expires') > time.time()

	@staticmethod
	def fetch_token(sess: dict, code: str | None = None, session_feedback: bool = True) -> tuple[bool, dict]:
		if code is not None:
			sess['code'] = code
		res = requests.post(
			os.environ.get(Data.X_API_OAUTH_URL),
			data={
				'grant_type': 'authorization_code',
				'client_id': os.environ.get(Data.X_FT_UID),
				'client_secret': os.environ.get(Data.X_FT_SECRET),
				'code': sess.get('code'),
				'redirect_uri': os.environ.get(Data.X_REDIRECT_URI),
			},
		)
		res = res.json() | {'status_code': res.status_code}
		if 'access_token' in res:
			sess['token'] = res['access_token']
			sess['refresh'] = res.get('refresh_token')
			sess['created'] = time.time()
			sess['expires'] = sess['created'] + res.get('expires_in', 3600)
			if session_feedback:
				session_success("Successfully authenticated.")
			success = True
		else:
			success = False
			if session_feedback:
				session_error(res)
		if Data.DEBUG:
			print(f"[DEBUG] ({sess.get('code')}) authorization_code: {json.dumps(res, indent=4)}")
		return success, res
	
	@staticmethod
	def refresh_token(sess: dict, refresh: str | None = None, session_feedback: bool = True) -> tuple[bool, dict]:
		if refresh is not None:
			sess['refresh'] = refresh
		res = requests.post(
			os.environ.get(Data.X_API_OAUTH_URL),
			data={
				'grant_type': 'refresh_token',
				'client_id': os.environ.get(Data.X_FT_UID),
				'client_secret': os.environ.get(Data.X_FT_SECRET),
				'refresh_token': sess.get('refresh'),
			},
		)
		res = res.json() | {'status_code': res.status_code}
		if 'access_token' in res:
			sess['token'] = res['access_token']
			sess['refresh'] = res.get('refresh_token', sess.get('refresh'))
			sess['created'] = time.time()
			sess['expires'] = sess['created'] + res.get('expires_in', 3600)
			if session_feedback:
				session_success("Session token successfully refreshed.")
			success = True
		else:
			success = False
			if session_feedback:
				session_error(res)
		if Data.DEBUG:
			print(f"[DEBUG] <{sess.get('token')}> refresh_token: {json.dumps(res, indent=4)}")
		return success, res

	@staticmethod
	def _send(sess: dict, endpoint: str, res_callback, feedback_error: bool = True, *query, **kwquery) -> dict:
		v_syntax, v_time = Session.is_valid(sess, split_time_validity=True)
		if not v_syntax:
			raise Exception("Session is not valid.")
		
		def __refresh(v_time):
			nonlocal sess
			if not v_time:
				if Session.refresh_token(sess, session_feedback=feedback_error)[0]:
					return None
				res = {
					'status_code': 401,
					'error': 'Unauthorized',
					'text': 'Failed to refresh token.',
				}
				if feedback_error:
					session_error(res)
				return res
			return None

		# In case the token is expired, try to refresh it
		if (r := __refresh(v_time)) is not None:
			return r

		url = get_url(endpoint, *query, **kwquery)
		method, res = res_callback(url)

		if res.status_code >= 401:
			# Maybe it has expired in a span of .1 sec... Refreshing again might solve the issue...
			if (r := __refresh(Session.is_valid(sess, split_time_validity=True)[1])) is not None:
				return r

		try:
			res = res.json() | {'status_code': res.status_code}
		except Exception as e:
			res = {
				'status_code': res.status_code,
				'error': str(e),
				'text': res.text,
			}
			if feedback_error:
				session_error(res)

		if Data.DEBUG:
			print(f"[DEBUG] <{sess.get('token')}> {method} '{url}': {json.dumps(res, indent=4)}")
		return res

	@staticmethod
	def post(sess: dict, endpoint: str, data: dict = None, feedback_error: bool = True, *query, **kwquery) -> dict:
		return Session._send(
			sess,
			endpoint,
			lambda url: (
				'POST',
				requests.post(
					url=url,
					json=data,
					headers={
						'Authorization': f'Bearer {sess.get('token')}',
					},
				),
			),
			feedback_error,
			*query,
			**kwquery,
		)

	@staticmethod
	def get(sess: dict, endpoint: str, feedback_error: bool = True, *query, **kwquery) -> dict:
		return Session._send(
			sess,
			endpoint,
			lambda url: (
				'GET',
				requests.get(
					url=url,
					headers={
						'Authorization': f'Bearer {sess.get('token')}',
					},
				),
			),
			feedback_error,
			*query,
			**kwquery,
		)
