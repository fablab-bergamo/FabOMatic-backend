#!/usr/bin/env python3
"""
Automated screenshot generator for FabOMatic web pages.
This script logs into the application and takes screenshots of all major pages.
"""

import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright, expect

# Configuration
BASE_URL = "https://localhost:23336"
OUTPUT_DIR = "doc/media"
ADMIN_EMAIL = "initial@test.com"  # From settings.toml: web.default_admin_email
ADMIN_PASSWORD = "admin"
TRIM_SCREENSHOTS = True  # Use ImageMagick mogrify -trim to remove whitespace

# Pages to screenshot (route, filename)
PAGES = [
    ("/", "dashboard"),
    ("/about", "about"),
    ("/users", "users_list"),
    ("/machines", "machines_list"),
    ("/machinetypes", "machine_types_list"),
    ("/roles", "roles_list"),
    ("/authorizations", "authorizations_list"),
    ("/interventions", "interventions_list"),
    ("/maintenances", "maintenances_list"),
    ("/view_uses", "uses_list"),
    ("/system", "system_info"),
    ("/settings", "settings"),
]

# Example detail pages (will only screenshot if they exist)
DETAIL_PAGES = [
    ("/users/add", "users_add"),
    ("/machines/add", "machines_add"),
    ("/authorizations/add", "authorizations_add"),
    ("/interventions/add", "interventions_add"),
    ("/maintenances/add", "maintenances_add"),
    ("/add_use", "uses_add"),
]


def create_output_dir():
    """Create output directory if it doesn't exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")


def trim_screenshot(screenshot_path):
    """Trim whitespace from screenshot using ImageMagick mogrify."""
    if not TRIM_SCREENSHOTS:
        return

    try:
        # mogrify -trim removes any edges that are the same color as the corner pixels
        subprocess.run(
            ["mogrify", "-trim", screenshot_path],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"  Warning: Failed to trim {screenshot_path}: {e.stderr}")
    except FileNotFoundError:
        print(f"  Warning: ImageMagick 'mogrify' not found. Install with: sudo apt install imagemagick")
        print(f"  Continuing without trimming...")
        # Disable trimming for subsequent screenshots to avoid repeated warnings
        globals()['TRIM_SCREENSHOTS'] = False


def take_screenshots():
    """Main function to take screenshots of all pages."""
    create_output_dir()

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True  # For self-signed certificates
        )
        page = context.new_page()

        print(f"Connecting to {BASE_URL}...")

        # Navigate to login page
        try:
            page.goto(f"{BASE_URL}/login", timeout=10000)
            print("Login page loaded")
        except Exception as e:
            print(f"Error: Could not connect to {BASE_URL}")
            print(f"Make sure the FabOMatic application is running.")
            print(f"Error details: {e}")
            browser.close()
            return False

        # Take screenshot of login page
        login_screenshot = os.path.join(OUTPUT_DIR, "login.png")
        page.screenshot(path=login_screenshot, full_page=True)
        trim_screenshot(login_screenshot)
        print(f"✓ Saved: {login_screenshot}")

        # Login
        print(f"\nLogging in as {ADMIN_EMAIL}...")
        page.fill('input#email', ADMIN_EMAIL)
        page.fill('input#password', ADMIN_PASSWORD)
        page.click('button[type="submit"]')

        # Wait for navigation after login (redirects to /about)
        try:
            page.wait_for_url(f"{BASE_URL}/about", timeout=5000)
            print("✓ Login successful")
        except Exception as e:
            print(f"✗ Login failed. Please check credentials in the script.")
            print(f"Error details: {e}")
            # Take screenshot of current page for debugging
            error_screenshot = os.path.join(OUTPUT_DIR, "login_error.png")
            page.screenshot(path=error_screenshot, full_page=True)
            trim_screenshot(error_screenshot)
            print(f"  Saved error screenshot to {error_screenshot}")
            browser.close()
            return False

        # Switch to English language
        print("\nSwitching to English language...")
        page.goto(f"{BASE_URL}/language/en", timeout=5000)
        time.sleep(1)  # Wait for language switch
        print("✓ Language set to English")

        # Take screenshots of main pages
        print("\nCapturing main pages...")
        for route, filename in PAGES:
            try:
                url = f"{BASE_URL}{route}"
                page.goto(url, timeout=10000)
                time.sleep(1)  # Wait for page to fully render

                screenshot_path = os.path.join(OUTPUT_DIR, f"{filename}.png")
                page.screenshot(path=screenshot_path, full_page=True)
                trim_screenshot(screenshot_path)
                print(f"✓ Saved: {screenshot_path}")
            except Exception as e:
                print(f"✗ Failed to capture {route}: {e}")

        # Take screenshots of detail/add pages
        print("\nCapturing detail pages...")
        for route, filename in DETAIL_PAGES:
            try:
                url = f"{BASE_URL}{route}"
                page.goto(url, timeout=10000)
                time.sleep(1)  # Wait for page to fully render

                screenshot_path = os.path.join(OUTPUT_DIR, f"{filename}.png")
                page.screenshot(path=screenshot_path, full_page=True)
                trim_screenshot(screenshot_path)
                print(f"✓ Saved: {screenshot_path}")
            except Exception as e:
                print(f"✗ Failed to capture {route}: {e}")

        # Close browser
        browser.close()
        print(f"\n✓ Screenshot generation complete!")
        print(f"All screenshots saved to: {OUTPUT_DIR}/")
        return True


if __name__ == "__main__":
    print("FabOMatic Screenshot Generator")
    print("=" * 50)
    print(f"Target URL: {BASE_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Admin email: {ADMIN_EMAIL}")
    print("=" * 50)

    # Check if Playwright is installed
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\nError: Playwright is not installed.")
        print("Please install it with:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    success = take_screenshots()
    sys.exit(0 if success else 1)
