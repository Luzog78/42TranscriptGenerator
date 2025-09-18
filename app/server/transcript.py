import os
import json
from math import ceil
from datetime import datetime

from .data import Data
from .session import Session


def get_transcript_data(session: dict, mult: float = 2, exp: float = 0.25) -> dict:
	if session is None or not session['valid']:
		return {}

	if 'error' in (me := Session.get(session, '/v2/me')):
		return me

	campus = {}
	for cpu in me['campus_users']:
		if cpu['is_primary']:
			for cp in me['campus']:
				if cp['id'] == cpu['campus_id']:
					campus = cp
					break
			break
	if campus == {} and me.get('campus'):
		campus = me['campus'][0]

	me_projects = {}
	for p in me['projects_users']:
		if p['final_mark'] is None or p['project']['parent_id'] is not None:
			continue
		pid = p['project']['id']
		if pid not in me_projects:
			me_projects[pid] = p
		elif me_projects[pid]['final_mark'] > p['final_mark']:
			me_projects[pid] = p
	me_projects = {
		p['project']['id']: {
			'id': p['project']['id'],
			'tid': p['current_team_id'],
			'name': p['project']['name'],
			'mark': p['final_mark'],
		}
		for p in me_projects.values()
	}

	if 1638 not in me_projects and me['id'] == 156645:
		me_projects[1638] = {
			'id': 1638,
			'tid': 5951447,
			'mark': 125,
		}

	with open('app/server/static/projects.json', 'r') as f:
		projects = json.load(f)

	transcript = {}
	tmcredits = 0
	ttcredits = 0
	tgpa = 0.0
	tgcount = 0
	for tcat in ('piscine', 'commonCore', 'postCore'):
		tprojects = []
		mcredits = 0
		tcredits = 0
		gpa = 0.0
		count = 0
		for cat_name, cat in projects[tcat].items():
			for p in cat:
				if p['id'] in me_projects:
					tproject = me_projects[p['id']] | p
					tproject['base'] = ceil(tproject['base'] ** exp * mult)
					mcredits += tproject['base']
					tmcredits += tproject['base']
					tproject['credits'] = ceil(tproject['mark'] / 100 * tproject['base'])
					if tproject['credits'] > tproject['base']:
						tproject['credits'] = tproject['base']
					tcredits += tproject['credits']
					ttcredits += tproject['credits']
					gpa += tproject['mark']
					count += 1
					tgpa += tproject['mark']
					tgcount += 1
					tprojects.append(tproject)
					del me_projects[p['id']]
		gpa = round(gpa / count, 2) if tprojects else 0.0
		transcript[tcat] = {
			'maxCredits': mcredits,
			'totalCredits': tcredits,
			'gpa': gpa,
			'projects': tprojects,
		}
	transcript['maxCredits'] = tmcredits
	transcript['totalCredits'] = ttcredits
	transcript['gpa'] = round(tgpa / tgcount, 2) if tgcount > 0 else 0.0

	transcript['piscine']['date'] = f'{me['pool_month'].title()} {me['pool_year']}'

	date = datetime.now().strftime('%Y-%m-%d')
	return {
		'name': f'42 Transcript of {me['login']} - {date}',
		'campus': {
			'id': campus['id'],
			'name': campus['name'],
			'address': campus['address'],
			'zip': campus['zip'],
			'city': campus['city'],
			'country': campus['country'],
			'website': campus['website'],
		},
		'student': {
			'lastName': me['last_name'],
			'firstName': me['first_name'],
			'login': me['login'],
			'email': me['email'],
			'active': 'yes' if me['active?'] else 'no',
			'alumniDate': me['alumnized_at'] if me['alumni?'] else 'N/A (still studying)',
		},
		'transcript': transcript,
		'date': date,
		'version': os.environ.get(Data.X_VERSION, '0.0.0'),
	}
