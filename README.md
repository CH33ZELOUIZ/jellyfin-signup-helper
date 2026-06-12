# Jellyfin Signup Helper

A tiny self-hosted signup page for creating Jellyfin users, plus an optional helper that applies default home/library display preferences.

## What it does

- Serves a simple HTML signup form.
- Validates username/password input.
- Uses the Jellyfin API to create a non-admin user.
- Applies conservative default user policy settings.
- Optionally runs `apply-defaults.py` after account creation to normalize home sections and library order.
- Provides `/health` for uptime checks.

## Important security notes

This is an admin-adjacent helper. Deploy carefully.

- Put it behind trusted-network access, invite-only routing, or a real auth/rate-limit layer.
- Do not expose unrestricted public signup unless you actually want strangers creating accounts.
- The included default token discovery reads an existing Jellyfin API key from the Jellyfin SQLite DB. That is convenient for private homelabs, but a purpose-made API key or service account flow is cleaner for broader deployments.
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
| `PUBLIC_JELLYFIN_URL` | URL shown to users after signup. |
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
