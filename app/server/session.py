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
		sess = session.get(Data.S_SESSION, None)
		if sess is not None:
			Session.is_valid(sess)
		return sess
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
			'valid': False,
		}

		if fetch_token and code is not None:
			self.fetch_token(sess)

		return sess

	@staticmethod
	def is_valid(sess: dict, split_time_validity: bool = False) -> bool | tuple[bool, bool]:
		if split_time_validity:
			r = sess.get('code') is not None and sess.get('expires') is not None, sess.get('expires', 0) > time.time()
			sess['valid'] = r[0] and r[1]
		else:
			r = sess.get('code') is not None and sess.get('expires') is not None and sess.get('expires') > time.time()
			sess['valid'] = r
		return r

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
			sess['valid'] = True
			if session_feedback:
				session_success("Successfully authenticated.")
			success = True
		else:
			success = False
			if session_feedback:
				session_error(res)
		if Data.DEBUG:
			print(f"[DEBUG] ({sess.get('code')}) authorization_code: {json.dumps(res, indent=4, ensure_ascii=False)}")
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
			sess['valid'] = True
			if session_feedback:
				session_success("Session token successfully refreshed.")
			success = True
		else:
			success = False
			if session_feedback:
				session_error(res)
		if Data.DEBUG:
			print(f"[DEBUG] <{sess.get('token')}> refresh_token: {json.dumps(res, indent=4, ensure_ascii=False)}")
		return success, res

	@staticmethod
	def _send(
			sess: dict,
			endpoint: str,
			res_callback,
			page: int = 1,
			page_size: int = 100,
			fetch_all: bool = False,
			feedback_error: bool = True,
			*query,
			**kwquery
			) -> dict:
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

		if 'page[number]' not in kwquery and 'page' not in kwquery and page != 1:
			kwquery['page[number]'] = page
		if 'page[size]' not in kwquery and 'per_page' not in kwquery:
			kwquery['page[size]'] = page_size

		url = get_url(endpoint, *query, **kwquery)
		method, res = res_callback(url)
		if Data.DEBUG and fetch_all:
			print(f"[DEBUG] <{sess.get('token')}> {method} '{url}'")

		if res.status_code >= 401:
			# Maybe it has expired in a span of .1 sec... Refreshing again might solve the issue...
			if (r := __refresh(Session.is_valid(sess, split_time_validity=True)[1])) is not None:
				return r

		try:
			res, status = res.json(), res.status_code
			if not isinstance(res, dict):
				res = { 'data': res }
				if isinstance(res['data'], list):
					res['total'] = len(res['data'])
			res['status_code'] = status

			if fetch_all:
				if not isinstance(res.get('data'), list):
					raise Exception("Cannot fetch all pages of a non-list response.")
				all_data = res
				page = kwquery.get('page[number]', kwquery.get('page', 1))
				page_size = kwquery.get('page[size]', kwquery.get('per_page', 30))
				kwquery.pop('page', None)
				while len(res['data']) == page_size:
					page += 1
					kwquery['page[number]'] = page
					_, res = res_callback(get_url(endpoint, *query, **kwquery))
					if Data.DEBUG:
						print(f"[DEBUG] <{sess.get('token')}> {method} '{get_url(endpoint, *query, **kwquery)}'")
					if res.status_code != all_data.get('status_code'):
						all_data |= res.json()
						all_data['status_code'] = res.status_code
						break
					res = { 'data': res.json() }
					res['total'] = len(res['data'])
					all_data['data'] += res['data']
					all_data['total'] += res['total']
				res = all_data

		except Exception as e:
			res = {
				'status_code': res.status_code,
				'error': str(e),
				'text': res.text,
			}
			if feedback_error:
				session_error(res)

		if Data.DEBUG:
			print(f"[DEBUG] <{sess.get('token')}> {method} '{url}': {json.dumps(res, indent=4, ensure_ascii=False)}")
		return res

	@staticmethod
	def post(
			sess: dict,
			endpoint: str,
			data: dict = None,
			page: int = 1,
			page_size: int = 100,
			fetch_all: bool = False,
			feedback_error: bool = True,
			*query,
			**kwquery
			) -> dict:
		return Session._send(
			sess=sess,
			endpoint=endpoint,
			res_callback=lambda url: (
				'POST',
				requests.post(
					url=url,
					json=data,
					headers={
						'Authorization': f'Bearer {sess.get('token')}',
					},
				),
			),
			page=page,
			page_size=page_size,
			fetch_all=fetch_all,
			feedback_error=feedback_error,
			*query,
			**kwquery,
		)

	@staticmethod
	def get(
			sess: dict,
			endpoint: str,
			page: int = 1,
			page_size: int = 100,
			fetch_all: bool = False,
			feedback_error: bool = True,
			*query,
			**kwquery
			) -> dict:
		return Session._send(
			sess=sess,
			endpoint=endpoint,
			res_callback=lambda url: (
				'GET',
				requests.get(
					url=url,
					headers={
						'Authorization': f'Bearer {sess.get('token')}',
					},
				),
			),
			page=page,
			page_size=page_size,
			fetch_all=fetch_all,
			feedback_error=feedback_error,
			*query,
			**kwquery,
		)
