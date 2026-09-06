# FabOMatic Backend — Discovery Survey & Security Audit

Date: 2026-09-06
Scope: full repository at commit `93b848d` (v1.0.5)

## 1. Discovery survey — drift from previous CLAUDE.md

| CLAUDE.md said | Actual |
|---|---|
| Current version 1.0.3, last updated Jan 2025 | `pyproject.toml` version is **1.0.5**, tag `v1.0.5` (2026-07-26). Two releases (1.0.4, 1.0.5) happened since. |
| Dependency versions given as loose ranges (Flask 3.0+, SQLAlchemy 2.0+, Paho-MQTT 2.1) | `requirements.txt` now pins exact versions: `flask==3.1.3`, `SQLAlchemy==2.0.51`, `alembic==1.18.5`, `psutil==7.2.2`, `pyopenssl==26.3.0`, `Flask-Babel==4.0.0`, `flask-mail==0.10.0`, `waitress==3.0.2`. |
| No mention of Dependabot | Recent git log (`#37`, `#38`) shows automated dependency-bump PRs, but no `dependabot.yml` exists anywhere in the repo — the automation config itself appears to be missing/unmanaged. |
| Key Components list omits weekly summary | `src/FabOMatic/logic/WeeklySummary.py` (336 lines) implements a weekly usage-summary email feature (added v1.0.1, `4f1da62`), with its own `[weekly_summary]` config block and `[email]` SMTP config block in `settings.example.toml`. Neither was documented. |
| Route list omits language routes | `src/FabOMatic/web/routes_languages.py` (i18n switch) exists and wasn't listed. |
| Structure tree omits `database/constants.py` | File exists, minor omission, now not worth separately calling out. |
| CI/lint/test commands | Verified unchanged and accurate — `.github/workflows/build.yml`/`deploy.yml` still run Python 3.10, same flake8 flags, same pytest invocation, same Babel compile step. No coverage upload, no dependency/security scanning step in CI. |
| Translations IT/EN | Confirmed still just `it` and `en`. |

CLAUDE.md has been updated in place to reflect the version, the new module/config surface, and (see below) the security findings.

## 2. Security & correctness findings

Ordered by severity. File:line references are against the current `main` branch.

### CRITICAL

**C1. Live credential committed to git**
`src/FabOMatic/conf/settings.toml:22-23` — this file is tracked in git (not templated/ignored) and contains what appears to be a real Gmail app password:
```
username = "fabomatic@fablabbergamo.it"
password = "[REDACTED-ROTATED-CREDENTIAL]"
```
Introduced in commit `4f1da62` (2025-10-26) and still present at HEAD. If the GitHub repo is public, this credential is exposed to the internet.
**Action:** rotate the Gmail app password immediately; remove the file from git tracking and add it to `.gitignore`; scrub it from history (BFG/`git filter-repo`) since rotation doesn't erase the historical exposure record.
**Status (branch `security-hardening/critical-fixes`):** file untracked (`git rm --cached`) and added to `.gitignore`. **Still outstanding and not doable from this branch: rotate the Gmail app password, and scrub `4f1da62` from history** — those are account-owner/repo-owner actions.

**C2. Flask debug mode enabled in production**
`src/FabOMatic/__main__.py:67`:
```python
app.run(host="0.0.0.0", port=23336, debug=True, use_reloader=False, ssl_context="adhoc")
```
`debug=True` on a server bound to `0.0.0.0` exposes the Werkzeug interactive debugger. If any unhandled exception is triggered by a request, an attacker on the network can reach a debug console with (PIN-gated, but historically bypassable) arbitrary code execution, plus verbose stack traces leaking source/paths.
**Action:** set `debug=False` for production runs; gate debug mode behind an explicit env var/config flag used only in development.
**Status (branch `security-hardening/critical-fixes`):** Fixed — `debug=False`.

**C3. Broken access control — role checks not enforced on sensitive routes**
Every route across `routes_users.py`, `routes_roles.py`, `routes_machines.py`, `routes_machinetypes.py`, `routes_interventions.py`, `routes_maintenance.py`, `routes_authorizations.py`, `routes_uses.py`, and `routes_system.py` is guarded only by `@login_required` — none check `current_user.role.backend_admin`. The login gate (`authentication.py:38`) admits any user whose role has `backend_admin` **or** `authorize_all`, but `authorize_all` is a separate, narrower permission (intended for RFID authorization management, see `models.py` `Role` class, `database/models.py:37-40`). A user with only `authorize_all=True` can therefore fully administer users/roles/machines, download/replace the database, and trigger system operations (see C4).
**Action:** add an explicit `backend_admin`-check decorator and apply it to every admin route; reserve `authorize_all`-only accounts for a deliberately scoped subset of routes, if any.
**Status (branch `security-hardening/critical-fixes`):** Fixed — added `backend_admin_required` in `authentication.py`, applied alongside `@login_required` to every route in `routes_authorizations.py`, `routes_interventions.py`, `routes_machines.py`, `routes_machinetypes.py`, `routes_maintenance.py`, `routes_roles.py`, `routes_system.py`, `routes_users.py`, `routes_uses.py`. `authorize_all`-only accounts (e.g. "Fab Staff"/"Fab Users" seed roles) can still log in per `authentication.py:43` but now get `403` on every admin route — the login gate itself was left as-is since redesigning who can authenticate at all is a separate, bigger decision. Also found and fixed **three routes with no auth check at all** (not just missing the role check): `routes_interventions.py` `interventions_export`, `routes_maintenance.py` `delete_maintenance`, `routes_roles.py` `delete_role` — these were fully unauthenticated, worse than the general C3 finding.

**C4. State-changing actions exposed as CSRF-able `GET` routes, no CSRF protection anywhere**
No CSRF framework (Flask-WTF or equivalent) is used anywhere in the app — none of the templates under `flask_app/templates/` include a CSRF token, and no `@app.after_request`/Talisman/session cookie hardening is configured (`webapplication.py` has no `SESSION_COOKIE_SECURE`/`SAMESITE` settings).
Worse, several destructive actions are implemented as `GET` routes in `routes_system.py`:
- `GET /reboot` (line 122) → `subprocess.run(["sudo", "reboot"], ...)`
- `GET /update_app` (line 94) → `pip install FabOMatic --upgrade` + service restart
- `GET /restart_app` (line 134) → service restart

A `GET` route with side effects can be triggered by a single `<img src="https://host:23336/reboot">` embedded in any web page an authenticated admin happens to view — no JavaScript, no form, no click required. This also implies the service account has (at minimum) passwordless `sudo reboot` rights, so this CSRF gap is effectively root-level.
**Action:** convert all state-changing operations to `POST` with a CSRF token; add Flask-WTF (or manual double-submit token) globally; set `SESSION_COOKIE_SAMESITE="Lax"` and `SESSION_COOKIE_SECURE=True`; scope the sudoers entry to exactly `reboot`, nothing broader.

**C5. Unrestricted database replacement**
`POST /upload_db` (`routes_system.py`, `upload_db()`) lets any logged-in user (see C3) overwrite the live SQLite database with an uploaded file, validated only by filename extension (`.sqldb`) — no content/schema validation. Combined with C3 (any authenticated account, not just admins) and the general lack of CSRF protection, this is a full data-integrity compromise path.
**Action:** restrict to `backend_admin`, validate the uploaded file is a well-formed SQLite DB matching the expected schema before swapping it in, and require CSRF + re-authentication for this specific action.

### HIGH

**H1. MQTT broker effectively unauthenticated**
`src/FabOMatic/mqtt/MQTTInterface.py:209`: `self._client.username_pw_set("backend", None)` — connects with a fixed username and **no password**. `settings.example.toml`'s `[MQTT] user = ""` comment ("Auth not used") suggests this is the intended production pattern, not just a test convenience — confirmed by `.ci/mosquitto.conf`/`mosquitto/conf.d/aclfile` allowing broad anonymous/pattern-based access. Any device or process that can reach the broker can publish forged machine-status or authorization-request messages.
**Action:** require broker username/password (and ideally TLS) in production configs; keep anonymous access confined to the CI test broker only.

**H2. No security headers / cookie hardening**
No CSP, `X-Frame-Options`, `X-Content-Type-Options`, or `Referrer-Policy` are set anywhere (`grep` for Talisman/CSP/`after_request` returned nothing). Combined with C4, this increases clickjacking and session-fixation exposure on the admin portal.
**Action:** add `flask-talisman` or equivalent middleware with sane defaults for an HTTPS-only admin app.

**H3. Outbound network call on every `/system` page load, no timeout**
`routes_system.py:35`: `requests.get(f"https://pypi.org/pypi/{package}/json")` has no `timeout=` argument. If PyPI is unreachable or slow, the request thread (and the admin's page load) hangs indefinitely — a simple availability bug that also leaks the server's presence/version-check pattern to PyPI on every admin visit.
**Action:** add a short timeout (e.g. `timeout=3`) and wrap in try/except so a PyPI outage doesn't break the system page.

### MEDIUM

**M1. Dependabot PRs without visible Dependabot config**
Recent "Bump X from Y to Z (#nn)" commits (`d9ccb00`, `ee21fc8`) look Dependabot-authored, but no `.github/dependabot.yml` exists in the repo. Either the config was removed, or updates are coming from elsewhere (manual PRs mimicking the style, or a org-level config not visible here). Worth confirming — if Dependabot truly isn't configured, dependency-CVE turnaround is ad hoc.

**M2. Dependency versions should be checked against a live CVE feed**
Exact pins in `requirements.txt` (`pyopenssl==26.3.0`, `paho-mqtt==2.1.0`, `Flask-Babel==4.0.0`, etc.) were reviewed for obviously stale/legacy patterns but not cross-checked against a live CVE database in this pass. Recommend running `pip-audit` or `safety check` against `requirements.txt` as a follow-up, and adding it as a CI step.

**M3. `download_logs` / `download_db` accessible to any authenticated user (ties back to C3)**
Both expose full application logs and the entire database (including hashed passwords, RFID card UUIDs, emails) to anyone who can log in, not just admins. Once C3 is fixed this resolves as a side effect, but flagging separately since log/DB exfiltration is a distinct risk from the "manage records" issue.

### LOW

**L1. Password reset token salt is a static, hardcoded value**
`authentication.py:24`: `SALT = b"fablab-bg"`. Combined with `SECRET_KEY` this is acceptable (itsdangerous still requires the secret key to forge a token), but a static salt shared across all deployments of this open-source project slightly weakens the design compared to a per-install random salt. Low priority given `SECRET_KEY` is the real secret.

**L2. No rate limiting on `/login` or `/forgot_password`**
No Flask-Limiter or equivalent; both endpoints log failed attempts (`authentication.py:47`, `:120`) but don't throttle them, allowing online credential-stuffing/brute force.

**L3. User enumeration on `/forgot_password`**
`authentication.py:112-122` returns a distinct flash message for "No user found with this email" vs. "Email sent," letting anyone enumerate which emails have accounts. Combine with L2 for a low-cost account-discovery script.

**L4. `requests==2.34.2` pin looks invalid**
`requirements.txt:14` pins `requests==2.34.2`; the published `requests` line tops out around 2.32.x as of this review. Likely a typo — verify with `pip index versions requests` and correct the pin (a nonexistent version just fails `pip install`, but worth fixing before it blocks a clean environment setup).

**L5. `.gitignore` does not cover the real `settings.toml`**
`.gitignore` only excludes `src/FabOMatic/conf/settings.toml.bak`, not `settings.toml` itself — confirming why C1 was committed in the first place and why it will happen again after rotation unless the file is untracked and ignored.

## 3. What was verified clean

- Password storage uses `werkzeug.security.generate_password_hash`/`check_password_hash` (salted, modern hashing) — no weak MD5/SHA1 hashing found (`database/models.py:87-91`).
- No raw/string-formatted SQL found anywhere — all DB access goes through SQLAlchemy ORM (`repositories.py`, `models.py`).
- No `eval`/`exec`/`pickle`/unsafe `yaml.load` usage anywhere in `src/`.
- Password-reset tokens are time-limited (30 min, `models.py:108`) via `itsdangerous`, with an exception-safe verify path.
- No bare `except:` clauses found; all exception handling in `MsgMapper.py`/`authentication.py` catches specific/broad `Exception` and logs it — no silent failures found in the scan.
- Subprocess calls in `routes_system.py` use argument lists (not `shell=True`), so they aren't shell-injectable from user input — the concern there is authorization (C3/C4), not injection.

## 4. Scope not covered in this pass

- Full template-by-template XSS review of all ~40 Jinja templates (spot-checked a sample; none showed `|safe` on user-controlled data, but not exhaustive).
- `MachineLogic.py` maintenance/access-hours arithmetic was not deeply reviewed for off-by-one/race-condition bugs under concurrent MQTT message handling.
- Live CVE lookup against pinned dependency versions (recommend `pip-audit`).
- Runtime testing of any of the above (this was a static review only).
