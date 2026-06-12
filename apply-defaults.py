#!/usr/bin/env python3
"""Apply default Jellyfin home/library order to all users.

No secrets are printed. Uses a local Jellyfin API key from the Jellyfin DB.
"""
import json
import sqlite3
import urllib.request
import urllib.error

import os

BASE = os.environ.get('JELLYFIN_URL', 'http://127.0.0.1:8096').rstrip('/')
DB = os.environ.get('JELLYFIN_DB', '/jellyfin-data/jellyfin.db')
HOME_SECTIONS = ['livetv', 'resume', 'nextup', 'latestmedia', 'smalllibrarytiles', 'none', 'none', 'none', 'none', 'none']
VIEW_ORDER_NAMES = ['Shows', 'Movies', 'Recorded Shows', 'Recorded Movies', 'Recordings', 'Live TV']


def get_token():
    con = sqlite3.connect(DB)
    row = con.execute('SELECT AccessToken FROM ApiKeys ORDER BY Id LIMIT 1').fetchone()
    if not row:
        raise SystemExit('No Jellyfin API key found')
    return row[0]


def api(token, path, method='GET', obj=None):
    headers = {'X-Emby-Token': token}
    data = None
    if obj is not None:
        data = json.dumps(obj).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode('utf-8')
        return resp.status, json.loads(body) if body else None


def apply_user(token, user):
    uid = user['Id']
    _, views = api(token, f'/Users/{uid}/Views?includeHidden=true')
    items = views.get('Items', [])
    by_name = {i.get('Name'): i.get('Id') for i in items if i.get('Name') and i.get('Id')}

    ordered = []
    for name in VIEW_ORDER_NAMES:
        vid = by_name.get(name)
        if vid and vid not in ordered:
            ordered.append(vid)
    for item in items:
        vid = item.get('Id')
        if vid and vid not in ordered:
            ordered.append(vid)

    _, full_user = api(token, f'/Users/{uid}')
    conf = full_user['Configuration']
    changed = False
    if conf.get('OrderedViews') != ordered:
        conf['OrderedViews'] = ordered
        api(token, f'/Users/{uid}/Configuration', method='POST', obj=conf)
        changed = True

    # Use user's existing emby display preference row when available, otherwise root/home default id.
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT ItemId FROM DisplayPreferences WHERE UserId=? AND Client='emby' LIMIT 1", (uid.upper(),)).fetchone()
    if not row:
        row = con.execute("SELECT ItemId FROM DisplayPreferences WHERE Client='emby' LIMIT 1").fetchone()
    dpid = row['ItemId'] if row else '00000000-0000-0000-0000-000000000000'

    _, prefs = api(token, f'/DisplayPreferences/{dpid}?userId={uid}&client=emby')
    cp = prefs.setdefault('CustomPrefs', {})
    before = [cp.get(f'homesection{i}') for i in range(10)]
    for i, val in enumerate(HOME_SECTIONS):
        cp[f'homesection{i}'] = val
    if before != HOME_SECTIONS:
        api(token, f'/DisplayPreferences/{dpid}?userId={uid}&client=emby', method='POST', obj=prefs)
        changed = True
    return changed


def main():
    token = get_token()
    _, users = api(token, '/Users')
    changed = 0
    for user in users:
        if apply_user(token, user):
            changed += 1
    print(f'checked={len(users)} changed={changed}')


if __name__ == '__main__':
    main()
