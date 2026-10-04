# Jellyfin Signup Helper

I made this so I could let trusted people create their own Jellyfin account without giving them admin access or doing every account by hand.

It is a small self-hosted signup page. It creates a normal Jellyfin user, applies safe default policy settings, and can optionally run `apply-defaults.py` to set up the home screen and library order the way I like it.

## Security notes

Treat this like an admin helper, not a public signup service.

- Put it behind trusted-network access, invite-only routing, or proper auth/rate limiting.
- Do not expose it to the open internet unless you really want anyone to create accounts.
- The default token discovery reads an existing Jellyfin API key from the Jellyfin SQLite DB. That is handy for a private homelab, but a dedicated API key or service account is cleaner for anything broader.
- Never publish your Jellyfin database or `.env` file.

## Quick start

```bash
git clone https://github.com/<your-user>/jellyfin-signup-helper.git
cd jellyfin-signup-helper
cp .env.example .env
# edit .env and set JELLYFIN_URL, PUBLIC_JELLYFIN_URL, and JELLYFIN_DB_PATH
docker compose up -d --build
```

Open <http://localhost:8060>.

## Configuration

| Variable | Purpose |
| --- | --- |
| `SIGNUP_PORT` | Host port for the signup page. |
| `JELLYFIN_URL` | Internal URL reachable from the signup container. |
| `PUBLIC_JELLYFIN_URL` | URL shown after signup. |
| `JELLYFIN_DB_PATH` | Host path to Jellyfin's SQLite DB, mounted read-only. |
| `JELLYFIN_DB` | Container path to the mounted DB. |
| `APPLY_DEFAULTS` | Optional script path run after user creation. |

## Development

```bash
python3 -m py_compile app.py apply-defaults.py
python3 app.py
```

## License

MIT
