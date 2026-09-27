# Grok OAuth: RFC 9207 iss on authorize redirect

## Status
shipped-via-pr

## Change type
bugfix

## Summary
Grok Bot OAuth login returns 302 from `POST /oauth/authorize` but Cursor never calls `POST /oauth/token`. Include RFC 9207 `iss` on the authorize redirect and advertise `authorization_response_iss_parameter_supported` in AS metadata.

## Acceptance criteria
- AS metadata includes `authorization_response_iss_parameter_supported: true`
- Successful authorize redirect includes `iss` matching metadata `issuer`
- Token exchange accepts RFC 8707 `resource` when present
- Grok retry shows `POST /oauth/token` → 200 in prod logs (manual)
