# Security notes

- Do not publish `.env` or Jellyfin database files.
- Rate-limit if exposed beyond a trusted group.
- Prefer a purpose-made API key or service-account pattern when adapting this for a larger deployment.
- Keep success/error messages helpful but avoid exposing backend exception details to users.
