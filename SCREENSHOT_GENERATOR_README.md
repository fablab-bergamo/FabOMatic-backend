# Screenshot Generator for FabOMatic Documentation

This script automates the process of taking screenshots of all FabOMatic web pages for documentation purposes.

## Prerequisites

1. **Virtual environment must be activated:**
   ```bash
   source venv/bin/activate
   ```

2. **Install Playwright:**
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. **FabOMatic application must be running:**
   ```bash
   # In another terminal window (with venv activated)
   python run.py
   # Or
   python -m FabOMatic
   ```

## Usage

### Basic Usage

```bash
# Make sure venv is activated
source venv/bin/activate

# Run the screenshot generator
python screenshot_generator.py
```

The script will:
1. Connect to the running FabOMatic application at `https://localhost:23336`
2. Log in using the admin credentials from `settings.toml`
3. Navigate to each main page
4. Take full-page screenshots
5. Save all images to `doc/media/` directory

## Configuration

You can modify the script's configuration at the top of `screenshot_generator.py`:

```python
BASE_URL = "https://localhost:23336"  # Change if using different port
OUTPUT_DIR = "doc/media"              # Output directory for screenshots
ADMIN_EMAIL = "initial@test.com"      # Admin email from settings.toml
ADMIN_PASSWORD = "admin"              # Default admin password
```

## Screenshots Generated

The script captures screenshots of:

### Main Pages:
- `dashboard.png` - Main dashboard (/)
- `about.png` - About page with machine status
- `login.png` - Login page
- `users_list.png` - Users management
- `machines_list.png` - Machines list
- `machine_types_list.png` - Machine types
- `roles_list.png` - User roles
- `authorizations_list.png` - User authorizations
- `interventions_list.png` - Interventions tracking
- `maintenances_list.png` - Maintenance schedules
- `uses_list.png` - Machine usage history
- `system_info.png` - System information
- `settings.png` - Application settings

### Add/Edit Pages:
- `users_add.png` - Add user form
- `machines_add.png` - Add machine form
- `authorizations_add.png` - Add authorization form
- `interventions_add.png` - Add intervention form
- `maintenances_add.png` - Add maintenance form
- `uses_add.png` - Add usage entry form

## Troubleshooting

### Application Not Running
```
Error: Could not connect to https://localhost:23336
```
**Solution:** Start the FabOMatic application in another terminal window.

### Login Failed
```
Error: Login failed. Please check credentials.
```
**Solution:** Verify that `ADMIN_EMAIL` and `ADMIN_PASSWORD` match your `settings.toml` configuration.

### Playwright Not Installed
```
Error: Playwright is not installed.
```
**Solution:** Install Playwright:
```bash
pip install playwright
playwright install chromium
```

### SSL Certificate Errors
The script is configured to ignore HTTPS errors for self-signed certificates. If you encounter issues, check that the application is running with HTTPS enabled.

## Output

All screenshots are saved as PNG files in the `doc/media/` directory. They are full-page screenshots that capture the entire page content, not just the visible viewport.

## Customization

### Adding More Pages

To capture additional pages, edit the `PAGES` or `DETAIL_PAGES` lists in the script:

```python
PAGES = [
    ("/your-route", "your_filename"),
    # Add more routes here
]
```

### Changing Screenshot Size

Modify the viewport size in the script:

```python
context = browser.new_context(
    viewport={"width": 1920, "height": 1080},  # Change dimensions here
    ignore_https_errors=True
)
```

### Changing Language

The script captures screenshots in the default language (Italian). To capture in English, you can modify the script to click the language switcher before taking screenshots.

## Notes

- Screenshots are taken in headless mode (no browser window is shown)
- Full-page screenshots capture all content, including content below the fold
- The script waits 1 second after each page load to ensure all content is rendered
- Existing screenshots in `doc/media/` will be overwritten
