# CLAUDE.md - FabOMatic Backend Project Guide

## Project Overview

FabOMatic Backend is a Python-based web application that manages FabLab machine access through RFID-enabled boards. It provides a comprehensive admin portal for managing users, machines, permissions, and maintenance schedules.

**Key Features:**
- Web admin portal with HTTPS authentication
- RFID member card database management
- Machine maintenance tracking based on actual usage hours
- Real-time machine status dashboard
- User permissions system per machine
- Machine usage and maintenance history

## Project Structure

```
FabOMatic-backend/
├── src/FabOMatic/           # Main application package
│   ├── __main__.py          # Entry point for module execution
│   ├── conf/                # Configuration files
│   │   ├── settings.example.toml  # Template configuration
│   │   └── settings.toml    # Active configuration (created from example)
│   ├── database/            # Database layer
│   │   ├── DatabaseBackend.py
│   │   ├── models.py        # SQLAlchemy models
│   │   └── repositories.py  # Data access layer
│   ├── flask_app/           # Web application assets
│   │   ├── static/          # CSS, JS, fonts
│   │   └── templates/       # Jinja2 HTML templates
│   ├── logic/               # Business logic
│   │   ├── MachineLogic.py
│   │   ├── MsgMapper.py     # MQTT message handling
│   │   └── WeeklySummary.py # Weekly usage summary emails (since v1.0.1)
│   ├── mqtt/                # MQTT communication
│   │   ├── MQTTInterface.py
│   │   └── mqtt_types.py
│   ├── web/                 # Flask routes and authentication
│   │   ├── authentication.py
│   │   ├── routes_*.py      # Route definitions by feature (incl. routes_system.py: subprocess-based update/reboot)
│   │   └── webapplication.py
│   ├── alembic/             # Database migrations
│   └── translations/        # i18n support (IT, EN)
├── tests/                   # Test suite
├── doc/                     # Documentation
├── mosquitto/               # MQTT broker configuration
├── .github/workflows/       # CI/CD pipelines
├── .ci/                     # CI configuration files
├── run.py                   # Development entry point
├── pyproject.toml           # Package configuration
└── requirements.txt         # Dependencies
```

## Technology Stack

**Core Technologies:**
- **Python 3.10+** - Main runtime
- **Flask 3.0+** - Web framework with HTTPS support
- **SQLAlchemy 2.0+** - ORM and database abstraction
- **SQLite** - Default database (configurable)
- **Paho-MQTT 2.1** - MQTT client for IoT communication
- **Alembic** - Database migrations
- **Flask-Babel** - Internationalization (IT/EN)

**Key Dependencies:**
- Flask-Login - User session management
- Flask-Mail - Email functionality
- PyOpenSSL - SSL/TLS support
- Flask-Excel - Data export functionality
- Waitress - WSGI server
- PSUtil - System monitoring

## Development Setup

### Prerequisites
```bash
# Linux systems
sudo apt install python3-apt rustc mosquitto dbus-user-session

# For Raspberry Pi Zero (additional)
wget -qO - https://raw.githubusercontent.com/tvdsluijs/sh-python-installer/main/python.sh | sudo bash -s 3.10.9
```

### Virtual Environment Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Verify activation (should show venv path)
which python
```

### Installation
```bash
# IMPORTANT: Always activate venv first!
source venv/bin/activate

# Install in development mode
pip install -e .

# Or install from PyPI
pip install FabOMatic
```

## Development Tools Setup

### Recommended VSCode Extensions
Based on the project's README, these extensions are recommended:
- **Python** - Python language support
- **SQLTools** - Database management  
- **SQLTools SQLite** - SQLite integration
- **Black Formatter** - Code formatting

### Code Formatting with Black
```bash
# Activate venv first
source venv/bin/activate

# Install Black
pip install black

# Format code (line length: 119 chars)
black . --line-length 119

# Check formatting without applying changes
black . --line-length 119 --check
```

### Linting with Flake8
```bash
# Activate venv first  
source venv/bin/activate

# Install Flake8
pip install flake8

# Run basic linting
flake8 .

# Run with project-specific settings (as used in CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

### Configuration
1. Copy `src/FabOMatic/conf/settings.example.toml` to `settings.toml`
2. Edit configuration for:
   - Database connection (SQLite default)
   - MQTT broker settings
   - Web server secret key
   - `[email]` SMTP settings (server/port/TLS/username/password/sender) — used for password reset and weekly summary emails
   - `[weekly_summary]` — `enabled` flag and `language` (en/it) for the weekly usage summary email feature

**⚠️ `src/FabOMatic/conf/settings.toml` is tracked in git and is NOT a template — it holds real per-deployment secrets (SMTP password, Flask `secret_key`).** Never commit real credentials into it; treat any value currently in that file as compromised (see Known Security Issues below).

### Running the Application

**Development Mode:**
```bash
# Activate venv first
source venv/bin/activate
python ./run.py
```

**Module Mode:**
```bash
# Activate venv first
source venv/bin/activate
python -m FabOMatic --loglevel 5
```

**Production Mode:**
- Use systemd service (see `doc/systemd/`)
- Default URL: `https://HOSTNAME:23336/`
- Default login: admin email from settings + "admin" password

## Testing

```bash
# Activate venv first
source venv/bin/activate

# Run all tests
pytest -v

# Run tests with coverage
pytest -v --cov

# Test configuration in tests/test_settings.toml
```

## CI/CD Pipeline

The project uses GitHub Actions for automated testing and deployment:

### Build & Test Workflow (.github/workflows/build.yml)
- **Triggers:** Pull requests, pushes to main branch, manual dispatch
- **Python Version:** 3.10
- **Steps:**
  1. Checkout code and setup Python
  2. Cache pip dependencies for faster builds
  3. Install dependencies and flake8/pytest
  4. Run flake8 linting with strict error checking
  5. Start Mosquitto test broker
  6. Install package in development mode
  7. Compile Babel translations
  8. Run pytest test suite
  9. Build wheel and source distribution

### Deploy Workflow (.github/workflows/deploy.yml)
- **Triggers:** Git tags (version releases)
- **Features:**
  - PyPI trusted publishing (no manual tokens needed)
  - Same build process as above
  - Automatic PyPI upload with skip-existing option

### Running CI Locally
```bash
# Activate venv first
source venv/bin/activate

# Install CI dependencies
pip install flake8 pytest build

# Run linting (same as CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Start local Mosquitto (if needed for testing)
mosquitto -c .ci/mosquitto.conf

# Run tests
pytest -v

# Build package
python -m build
```

## Database Management

**Migration Commands:**
```bash
# Activate venv first
source venv/bin/activate

# Check schema
alembic check

# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

**GDPR Compliance:**
```bash
# Activate venv first
source venv/bin/activate

# Purge old data (run daily via cron)
python -m FabOMatic --purge
journalctl --vacuum-time=1y
```

## Internationalization

**Babel Commands (run from src/FabOMatic/):**
```bash
# Activate venv first
source venv/bin/activate

# Navigate to source directory
cd src/FabOMatic/

# Extract translatable strings
pybabel extract -F babel.cfg -o messages.pot ./

# Update translations
pybabel update -i messages.pot -d translations

# Add new locale
pybabel init -i messages.pot -d translations -l <locale>

# Compile translations
pybabel compile -d translations
```

## MQTT Communication

**Topics:**
- `machine/<ID>` - Machine status and commands
- `machine/<ID>/reply` - Backend responses
- `stats/` - System statistics

**Message Flow:**
1. Fab-O-Matic boards publish status to machine topics
2. Backend processes messages via MsgMapper
3. Backend publishes replies and stats
4. Real-time updates shown in web dashboard

### MQTT Testing Setup

The project includes a Mosquitto configuration for testing (`.ci/mosquitto.conf`):

**Key Configuration Settings:**
- **Port:** 1883 (standard MQTT)
- **Anonymous Access:** Enabled for testing
- **Zero-length Client IDs:** Allowed
- **Persistence:** Disabled for testing

**Starting Test Broker:**
```bash
# Using project's test configuration
mosquitto -c .ci/mosquitto.conf

# Or start with default settings
mosquitto -p 1883

# Test MQTT connection
mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT"
mosquitto_sub -h localhost -t "test/topic"
```

**MQTT Client Testing:**
```bash
# Activate venv first
source venv/bin/activate

# Test FabOMatic MQTT topics
mosquitto_pub -h localhost -t "machine/1" -m '{"status": "active"}'
mosquitto_sub -h localhost -t "machine/+/reply"
mosquitto_sub -h localhost -t "stats/#"
```

## Key Components

### Backend Class (`src/FabOMatic/__main__.py:15`)
Main orchestrator that:
- Manages database and MQTT connections
- Handles message mapping between MQTT and database
- Starts Flask web server in separate thread
- Maintains connection health and statistics

### MsgMapper (`src/FabOMatic/logic/MsgMapper.py`)
Bridges MQTT messages and database operations:
- Processes machine status updates
- Handles user authentication requests
- Manages maintenance notifications

### DatabaseBackend (`src/FabOMatic/database/DatabaseBackend.py`)
Provides data access layer:
- SQLAlchemy session management
- Database schema creation/updates
- Data purging for GDPR compliance

### Web Routes (`src/FabOMatic/web/routes_*.py`)
Feature-specific Flask routes:
- User management
- Machine configuration
- Authorization handling
- Maintenance tracking
- System administration

## Deployment Notes

## Known Security Issues (found in audit, 2026-09-06)

See `doc/SECURITY_AUDIT_2026-09-06.md` for full detail. Do not reintroduce these patterns in new code, and flag them again if seen elsewhere:

Fixed on branch `security-hardening/critical-fixes`:
- ~~Flask runs with `debug=True` in production~~ — now `debug=False` (`src/FabOMatic/__main__.py:67`).
- ~~Broken access control~~ — added a `backend_admin_required` decorator (`web/authentication.py`) and applied it alongside `@login_required` to every route across `routes_authorizations.py`, `routes_interventions.py`, `routes_machines.py`, `routes_machinetypes.py`, `routes_maintenance.py`, `routes_roles.py`, `routes_system.py`, `routes_users.py`, `routes_uses.py` — including three routes (`interventions_export`, `delete_maintenance`, `delete_role`) that had **no auth check at all**. Accounts with only `authorize_all` can still log in but now get `403` on admin routes.
- `src/FabOMatic/conf/settings.toml` untracked from git and added to `.gitignore` — **but the historical secret is still in git history and the live credential is still unrotated** (repo-owner action, not fixable from a branch).

Still open (see `doc/SECURITY_AUDIT_2026-09-06.md` for full detail — do not reintroduce these patterns in new code):
- **Rotate the leaked Gmail app password** and scrub commit `4f1da62` from history (BFG/`git filter-repo`).
- **No CSRF protection anywhere** (no Flask-WTF, no CSRF tokens in any template). Several state-changing routes are plain `GET` (`/reboot`, `/update_app`, `/restart_app` in `routes_system.py`), which is trivially forgeable via a single `<img src=...>` tag from any page an admin visits while logged in.
- **MQTT has no real auth**: `MQTTInterface.py` calls `username_pw_set("backend", None)` — no password — and `settings.example.toml`'s `[MQTT] user = ""` implies anonymous broker access is the norm, not just a test fixture.
- No security headers (no CSP/X-Frame-Options/Talisman), no `SESSION_COOKIE_SECURE`/`SAMESITE` hardening, no rate limiting on `/login`/`/forgot_password`, user enumeration on `/forgot_password`.

## Git Workflow

### Committing Changes
```bash
# Activate venv first
source venv/bin/activate

# Check status and see changes
git status
git diff

# Add files to staging
git add .

# Or add specific files
git add src/FabOMatic/specific_file.py

# Commit with descriptive message
git commit -m "Add new feature: description of changes

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote repository
git push origin main
```

### Creating Releases
```bash
# Tag a new version (triggers PyPI deployment)
git tag v0.7.3
git push origin v0.7.3

# Or create annotated tag with message
git tag -a v0.7.3 -m "Release version 0.7.3: Bug fixes and improvements"
git push origin v0.7.3
```

## Package Distribution

### Building Packages
```bash
# Activate venv first
source venv/bin/activate

# Install build tools
pip install --upgrade build twine

# Build wheel and source distribution
python -m build

# Upload to PyPI manually (if needed)
python -m twine upload dist/*
```

### Automated PyPI Deployment
The project uses GitHub Actions for automatic PyPI deployment:
- **Trigger:** Push git tags (e.g., `git push origin v0.7.3`)
- **Authentication:** PyPI trusted publishing (no manual tokens)
- **Features:** Skip existing packages, automated testing before upload

### Upgrade Process
```bash
# For end users
pip install FabOMatic --upgrade

# For developers
source venv/bin/activate
pip install -e . --upgrade

# Review settings.toml after upgrade
# Database migrations applied automatically on startup
```

**Security Requirements:**
- Secure admin passwords
- HTTPS certificate setup
- Database backup strategy
- Regular log rotation
- GDPR compliance cron jobs

## Entry Points

**Note: Always activate virtual environment first with `source venv/bin/activate`**

- **Main Application:** `python -m FabOMatic`
- **Development:** `python ./run.py`
- **Purge Data:** `python -m FabOMatic --purge`
- **Web Interface:** `https://localhost:23336/`

## Troubleshooting

### Common Development Issues

**Virtual Environment Not Activated**
```bash
# Symptom: ModuleNotFoundError or wrong Python version
which python  # Should show venv path
source venv/bin/activate
```

**MQTT Connection Issues**
```bash
# Check if Mosquitto is running
ps aux | grep mosquitto

# Start Mosquitto with test config
mosquitto -c .ci/mosquitto.conf

# Test MQTT connectivity
mosquitto_pub -h localhost -t "test" -m "hello"
```

**Database Migration Errors**
```bash
# Check migration status
source venv/bin/activate
alembic current
alembic history

# Apply pending migrations
alembic upgrade head
```

**Babel Translation Issues**
```bash
# Recompile translations
cd src/FabOMatic/
pybabel compile -d translations
```

**Build/Package Issues**
```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info/

# Rebuild
python -m build
```

**Test Failures**
```bash
# Run specific test
pytest tests/test_specific.py -v

# Run tests with more output
pytest -v -s

# Check test database
ls tests/databases/
```

### Performance Tips

- Use `--loglevel 40` for production (ERROR level only)
- Monitor MQTT message frequency to avoid overwhelming
- Regular database maintenance with `--purge` command
- Use systemd for production deployment instead of development server

## Current Version: 1.0.7

Last updated: September 2026 (discovery survey + security audit)

---

*This CLAUDE.md file provides comprehensive guidance for FabOMatic Backend development. Keep it updated as the project evolves.*
- remember to activate the venv for this python project before to run python commands in the shell
- run flake8 and tests before to create a PR