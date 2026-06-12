# Deployment

The signup helper serves a small HTML form and calls the Jellyfin API to create users.

## Required configuration

- internal Jellyfin URL reachable from the container
- user-facing Jellyfin URL for the success link
- a Jellyfin API token strategy
- optional default-preferences script

## Recommended placement

Use this on trusted networks, invite-only routes, or behind auth/rate limits. Open public signup should be a deliberate decision.
