# Repo quality standards (post-WIP landing)

## Status
draft

## Summary

After landing the large feature batch on `master`, bring **cooking_website** to a maintainable standard: **automated tests**, **CI that exercises server + console**, **docs that match code** (`plan-docs`), and clear **ops/runbook** gaps closed. Work proceeds only via **`agent-managed`** issues and `docs/work/active-slice.yaml` after gate 1.

## Motivation

- Feature surface grew fast (admin, CNF nutrition, URL import, MCP/OAuth, PWA, extension) with **no server test suite** and CI that only **lint/builds the console**.
- Evergreen docs exist but were written alongside code; a **verification pass** is needed so `docs/api.md`, `data-model.md`, and feature pages stay trustworthy.
- Agent stack is scaffolded; this initiative is the first **manifest-driven** slice sequence.

## Detailed intent

1. **Testing foundation**
   - Add `pytest` (and fixtures) under `server/` for auth, alias review, nutrition lookups, recipe import state machine, and MCP auth boundaries (mock external Gemini/OAuth where needed).
   - Document `make test` / `pytest` in `docs/operations.md` and root `README.md`.

2. **CI hardening**
   - Extend `.github/workflows/ci.yml` with a **server** job: install deps, run migrations against ephemeral Postgres (service container), run pytest, optional ruff/mypy if lightweight.
   - Keep console `lint` + `build`; fail PRs on either job.

3. **Documentation audit**
   - Cross-check routes in `server/app/router/` vs `docs/api.md`.
   - Cross-check models/migrations vs `docs/data-model.md`.
   - Ensure each feature in `docs/README.md` has a matching feature doc; link delivery reports as slices complete.

4. **Quality gates for new work**
   - Enforce `plan-docs` rule: API/schema/UI changes update docs in the same PR.
   - Tester handoff checklist: what ran locally + CI link.

5. **Optional follow-ups** (later slices, not blocking v1 of this initiative)
   - Playwright smoke for login + admin toggle (homelab or CI with secrets stubbed).
   - Extension manual test section in `docs/features/recipe-import.md`.
   - MCP inspector scripted smoke in CI (may stay manual if OAuth-heavy).

## Constraints

- Do not rewrite working product behavior unless a test exposes a real bug.
- No secrets in repo; tests use env stubs / fixtures.
- Prod deploy path (`deploy-prod.yml`) unchanged unless a slice explicitly targets ops.
- One **active slice** at a time unless Planner splits parallel work with separate manifest files.

## Open questions

- Should nutrition seed CSVs stay in git (~560k rows) or move to download-on-first-seed in CI only?
- Minimum MCP test coverage: API key path only first, or full OAuth DCR flow in integration tests?
- Playwright in CI now vs homelab-only for cost/complexity?

## Risks and criticism

- **Large seed data** slows CI checkout and clone; may need subset DB for tests.
- **Gemini-dependent** import paths need mocks; risk of tests that don't catch real API drift.
- **Scope creep**: "standards" can balloon; keep slices small and shippable.
- Brownfield WIP just landed—first standardization PRs should be additive (tests/docs/CI), not refactors.

## Out of scope

- New user-facing features (unless required to test existing flows).
- Replacing Gemini with another model.
- Multi-repo split or manifest per service.

## Technical plan (draft)

1. Slice A: pytest harness + Postgres test DB + 3–5 high-value API tests (auth, alias accept 400/404, nutrition food by id).
2. Slice B: CI server job wired to those tests.
3. Slice C: doc audit PR (api + data-model deltas only).
4. Slice D: import worker + MCP API-key tests with mocks.
5. Slice E (optional): console smoke / extension checklist.

## Proposed issues (draft)

| # | Title (draft) | Acceptance (sketch) |
|---|----------------|---------------------|
| 1 | Server pytest harness and Postgres test fixtures | `pytest` runs locally; documented in operations |
| 2 | API tests: auth and admin routes | 401/403/200 cases for representative endpoints |
| 3 | API tests: alias review accept/reject | Matches `docs/features/admin.md` edge cases |
| 4 | API tests: nutrition read paths | Food lookup returns expected shape from seeded subset |
| 5 | CI: server job with pytest | PR fails if server tests fail |
| 6 | Docs: API and data-model reconciliation | `docs/api.md` and `data-model.md` match routers/migrations |
| 7 | Docs: operations test and CI section | README + operations describe full CI matrix |
| 8 | Tests: recipe import worker (mocked Gemini) | State transitions extracting → ready/failed |
| 9 | Tests: MCP API key auth | 401 without key; tool list with key (no live OAuth) |
| 10 | Optional: Playwright login smoke | Documented env; runs in CI or manual gate |

## Raw notes

- Baseline commits on `master`: `c71c528` (agent scaffold), `1dc4547` (feature landing).
- GitHub label `agent-managed` already exists on `MathieuLaureti/cooking_website`.
