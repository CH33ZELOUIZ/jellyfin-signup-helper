#!/usr/bin/env python3
import html
import json
import os
import re
import sqlite3
import subprocess
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

JELLYFIN = os.environ.get('JELLYFIN_URL', 'http://jellyfin:8096').rstrip('/')
DB = os.environ.get('JELLYFIN_DB', '/jellyfin-data/jellyfin.db')
PUBLIC_JELLYFIN = os.environ.get('PUBLIC_JELLYFIN_URL', JELLYFIN)
APPLY_DEFAULTS = os.environ.get('APPLY_DEFAULTS', '/app/apply-defaults.py')

USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,32}$')

PAGE = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Create Jellyfin Account</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at top,#253657,#090b10 62%);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#f4f7ff;display:flex;align-items:center;justify-content:center;padding:24px}.card{width:100%;max-width:520px;background:rgba(10,14,23,.9);border:1px solid rgba(255,255,255,.14);border-radius:22px;box-shadow:0 24px 70px rgba(0,0,0,.55);padding:30px}h1{margin:0 0 8px;font-size:30px;line-height:1.1}.sub{opacity:.8;margin:0 0 24px;line-height:1.4}label{display:block;margin:16px 0 7px;font-weight:800}input{width:100%;border-radius:12px;border:1px solid rgba(255,255,255,.22);background:#111827;color:#fff;padding:13px 14px;font-size:16px}input:focus{outline:2px solid #00a4dc;border-color:#00a4dc}button,.btn{display:inline-block;margin-top:22px;width:100%;border:0;border-radius:13px;background:#00a4dc;color:#00131b;font-weight:950;padding:14px 16px;font-size:16px;text-decoration:none;text-align:center;cursor:pointer}.msg{margin:16px 0 0;padding:12px 14px;border-radius:12px;background:rgba(255,255,255,.08);line-height:1.4}.err{background:rgba(255,60,60,.14);border:1px solid rgba(255,60,60,.35)}.ok{background:rgba(40,220,120,.14);border:1px solid rgba(40,220,120,.35)}small{opacity:.72;display:block;margin-top:8px;line-height:1.35}.foot{margin-top:20px;text-align:center}.foot a{color:#80dfff}</style></head>
<body><main class="card"><h1>Create Jellyfin Account</h1><p class="sub">Choose a username and password. Then sign in to Jellyfin and start watching.</p>__BODY__<div class="foot"><a href="__PUBLIC_JELLYFIN__">Back to Jellyfin</a></div></main></body></html>'''

FORM = '''<form method="post" action="/create">
<label>Username</label><input name="username" autocomplete="username" required minlength="3" maxlength="32" pattern="[A-Za-z0-9._-]+" value="__USERNAME__"><small>Letters, numbers, dot, dash, underscore. 3–32 characters.</small>
<label>Password</label><input name="password" type="password" autocomplete="new-password" required minlength="4"><small>4 characters minimum.</small>
<label>Confirm password</label><input name="confirm" type="password" autocomplete="new-password" required minlength="4">
<button type="submit">Create account</button>
</form>'''

def form(username=''):
    return FORM.replace('__USERNAME__', html.escape(username, quote=True))

def get_token():
    con = sqlite3.connect(DB)
    try:
        row = con.execute('SELECT AccessToken FROM ApiKeys ORDER BY Id LIMIT 1').fetchone()
    finally:
        con.close()
    if not row or not row[0]:
        raise RuntimeError('No Jellyfin API key found')
    return row[0]

def jf(path, method='GET', obj=None):
    token = get_token()
    headers = {'X-Emby-Token': token}
    data = None
    if obj is not None:
        data = json.dumps(obj).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(JELLYFIN + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode('utf-8')
        return resp.status, json.loads(body) if body else None

def user_exists(name):
    _, users = jf('/Users')
    return any((u.get('Name') or '').lower() == name.lower() for u in users)

def create_user(name, password):
    _, user = jf('/Users/New', method='POST', obj={'Name': name, 'Password': password})
    uid = user.get('Id')
    if not uid:
        raise RuntimeError('Jellyfin did not return a user id')
    _, full = jf(f'/Users/{uid}')
    pol = full.get('Policy', {})
    pol.update({
        'IsAdministrator': False,
        'IsDisabled': False,
        'EnableContentDeletion': False,
        'EnableContentDeletionFromFolders': [],
        'EnableRemoteControlOfOtherUsers': False,
        'EnableSharedDeviceControl': False,
        'EnableRemoteAccess': True,
        'EnableAllFolders': True,
        'EnableAllChannels': True,
    })
    jf(f'/Users/{uid}/Policy', method='POST', obj=pol)
    try:
        subprocess.run(['python3', APPLY_DEFAULTS], timeout=60, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return uid

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('%s - %s' % (self.address_string(), fmt % args), flush=True)

    def render(self, body, code=200):
        out = PAGE.replace('__PUBLIC_JELLYFIN__', html.escape(PUBLIC_JELLYFIN, quote=True)).replace('__BODY__', body).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/signup'):
            self.render(form())
        elif path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'ok\n')
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != '/create':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        data = parse_qs(self.rfile.read(length).decode('utf-8', errors='ignore'))
        username = (data.get('username', [''])[0] or '').strip()
        password = data.get('password', [''])[0]
        confirm = data.get('confirm', [''])[0]

        def fail(msg, code=400):
            self.render(form(username) + f'<div class="msg err">{html.escape(msg)}</div>', code)

        if not USERNAME_RE.match(username):
            return fail('Username must be 3–32 characters and only use letters, numbers, dot, dash, or underscore.')
        if len(password) < 4:
            return fail('Password must be at least 4 characters.')
        if password != confirm:
            return fail('Passwords do not match.')
        try:
            if user_exists(username):
                return fail('That username already exists. Pick another one.')
            create_user(username, password)
        except urllib.error.HTTPError:
            return fail('Jellyfin rejected the account creation request. Try another username/password.')
        except Exception as exc:
            print(f'create failed: {exc}', flush=True)
            return fail('Server error creating account. Ask the server administrator to check the signup service.', 500)
        self.render(f'<div class="msg ok">Account created for <b>{html.escape(username)}</b>.</div><a class="btn" href="{html.escape(PUBLIC_JELLYFIN, quote=True)}">Continue to Jellyfin</a>')

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8060), Handler).serve_forever()
