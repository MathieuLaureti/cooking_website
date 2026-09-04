# Authentication

## What it does

Every user must sign in before accessing the app. There is no guest access — match checker and recipes are only available with a valid JWT.

Two roles:

| Role | Access |
|------|--------|
| `admin` | Read everything + create/edit/delete recipes + AI URL import + view registration code |
| `user` | Read-only: ingredient pairings and recipes |

New accounts register with a **7-digit code** that rotates every 60 seconds. Only admins can see the current code (admin panel in the UI). The admin shares the code manually to invite new users.

## User flow

1. Visit app → login screen (no content visible).
2. **Register**: username, password (min 6 chars), 7-digit code from admin → account created with `user` role → redirect to login.
3. **Login**: username + password → JWT stored in `localStorage` → full app loads.
4. **Admin panel** (admin only): expandable section showing live registration code + countdown.
5. **Sign out**: clears token, returns to login.

## Bootstrap

On first server start, if the `user` table is empty and `ADMIN_USERNAME` / `ADMIN_PASSWORD` are set in `.env`, one admin account is created automatically.

## UI

- `console/src/context/AuthContext.tsx` — login, register, logout, JWT decode, `isAdmin`
- `console/src/api/client.ts` — axios interceptor attaches Bearer token; 401 clears token
- `console/src/components/Login.tsx` — sign-in form
- `console/src/components/Register.tsx` — registration form with code field
- `console/src/components/AdminPanel.tsx` — registration code display (admin only)
- `console/src/App.tsx` — auth gate; mounts content only when logged in

## Backend

- Router: `server/app/router/auth.py`
- Auth logic: `server/app/auth.py` — bcrypt passwords, JWT create/decode, HMAC registration codes
- Model: `User` in `server/app/db_models/models.py`
- Bootstrap: `server/app/seed_admin.py` (called on app startup)

### Registration code

Deterministic HMAC from `JWT_SECRET` (or `REGISTRATION_SECRET`) + current minute bucket. No DB or Redis. Accepts current or previous minute (clock-skew tolerance).

## Data

See [data model](../data-model.md) — `user` table.

## Edge cases

- Invalid/expired JWT → `401` on API; client clears token and shows login.
- Wrong registration code → `400`.
- Duplicate username on register → `400`.
- Non-admin hitting admin routes → `403`.
- Registration code refreshes every 60s; previous minute's code still valid briefly.
