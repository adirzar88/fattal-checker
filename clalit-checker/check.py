"""
Clalit Dermatologist Appointment Checker & Booker
Searches for dermatology appointments in Holon (excluding hospitals),
books the first available slot, and sends an email notification.
"""

from playwright.sync_api import sync_playwright
from config import *
import requests
import os
import sys
from datetime import datetime

SCREENSHOTS_DIR = "screenshots"
LOGIN_URL = "https://e-services.clalit.co.il/OnlineWeb/General/Login.aspx"
TAMUZ_URL = "https://e-services.clalit.co.il/OnlineWeb/Services/Tamuz/TamuzTransfer.aspx"

HEADLESS = os.environ.get("CI") == "true" or os.environ.get("HEADLESS") == "true"

HOSPITAL_KEYWORDS = ["בי\"ח", "בית חולים", "וולפסון", "אסף הרופא", "שיבא", "איכילוב", "בילינסון"]

TEST_MODE = os.environ.get("TEST_MODE") == "true"


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {msg}")
    except UnicodeEncodeError:
        print(f"[{timestamp}] {msg.encode('ascii', 'replace').decode()}")


def ss(page, name):
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"{name}.png"), full_page=True)


def login(page):
    log("Logging in...")
    page.goto(LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    page.fill("#ctl00_cphBody__loginView_tbUserId", ID_NUMBER)
    page.fill("#ctl00_cphBody__loginView_tbUserName", USER_CODE)
    page.fill("#ctl00_cphBody__loginView_tbPassword", PASSWORD)

    captcha = page.locator("#ctl00_cphBody__loginView_tbCaptchaLogin")
    if captcha.is_visible():
        log("CAPTCHA detected - cannot solve automatically")
        ss(page, "captcha")
        return False

    page.locator("#ctl00_cphBody__loginView_btnSend").click()
    page.wait_for_timeout(5000)

    if "login" in page.url.lower():
        log("Login FAILED - check credentials")
        ss(page, "login_failed")
        return False

    log("Login OK")
    return True


def open_tamuz(page):
    log("Opening Tamuz appointment system...")
    try:
        page.goto(TAMUZ_URL, timeout=60000, wait_until="domcontentloaded")
    except Exception:
        pass
    page.wait_for_timeout(10000)

    tamuz = page.frame("ifrmMainTamuz")
    if not tamuz:
        log("ERROR: Tamuz iframe not found")
        ss(page, "no_iframe")
        return None

    tamuz.wait_for_load_state("domcontentloaded")
    tamuz.wait_for_timeout(5000)
    return tamuz


def search_dermatology(tamuz, page):
    log("Opening specialist search...")
    tamuz.locator("#ProfessionVisitButton").click()
    tamuz.wait_for_timeout(5000)

    log("Selecting dermatology...")
    tamuz.locator("#SelectedGroupCode").select_option(value="31")
    tamuz.wait_for_timeout(2000)
    tamuz.locator("#SelectedSpecializationCode").select_option(value="31")
    tamuz.wait_for_timeout(2000)

    if CITY:
        log(f"Setting city: {CITY}")
        city_input = tamuz.locator("#SelectedCityName")
        city_input.fill("")
        city_input.type(CITY, delay=100)
        tamuz.wait_for_timeout(2000)
        try:
            suggestion = tamuz.locator(
                f'li:has-text("{CITY}"), '
                f'[class*="suggestion"]:has-text("{CITY}"), '
                f'[class*="auto"]:has-text("{CITY}")'
            ).first
            if suggestion.is_visible(timeout=3000):
                suggestion.click()
                tamuz.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            cb = tamuz.locator("#IsSearchDiariesByDistricts")
            if cb.is_checked():
                cb.uncheck()
                tamuz.wait_for_timeout(500)
        except Exception:
            pass

    ss(page, "01_search_form")

    log("Searching...")
    tamuz.locator('input[value="חיפוש"]').click()
    tamuz.wait_for_timeout(15000)

    # Close popup if present
    try:
        close = tamuz.locator("text=X").first
        if close.is_visible(timeout=3000):
            close.click()
            tamuz.wait_for_timeout(2000)
    except Exception:
        pass

    ss(page, "02_results")


def find_bookable_clinics(tamuz):
    """Parse search results and return list of bookable clinics with dates.
    Only returns clinics in CITY that are not hospitals."""
    all_links = tamuz.locator('a:has-text("לכל התורים")').all()
    log(f"Found {len(all_links)} results with available slots")

    clinics = []
    for i, link in enumerate(all_links):
        try:
            context = link.evaluate("""el => {
                let container = el.parentElement;
                for (let j = 0; j < 10; j++) {
                    if (!container) break;
                    let text = container.innerText || '';
                    if (text.length > 80) return text.substring(0, 500);
                    container = container.parentElement;
                }
                return '';
            }""")

            has_date = "בתאריך" in context
            in_city = CITY in context if CITY else True
            is_hospital = any(kw in context for kw in HOSPITAL_KEYWORDS)

            doctor = ""
            for line in context.split("\n"):
                line = line.strip()
                if "ד\"ר" in line and len(line) < 60:
                    doctor = line
                    break
                if "רופא" in line and len(line) < 60:
                    doctor = line
                    break

            date = ""
            for line in context.split("\n"):
                if "בתאריך" in line:
                    date = line.strip()
                    break

            clinic = ""
            for line in context.split("\n"):
                if "מרפאה:" in line:
                    clinic = line.strip()
                    break

            status = []
            if not has_date:
                status.append("no date")
            if not in_city:
                status.append(f"not in {CITY}")
            if is_hospital:
                status.append("hospital")

            if status:
                log(f"  [{i}] SKIP ({', '.join(status)}): {doctor} | {clinic}")
            else:
                log(f"  [{i}] MATCH: {doctor} | {date} | {clinic}")
                clinics.append({
                    "index": i,
                    "link": link,
                    "doctor": doctor,
                    "date": date,
                    "clinic": clinic,
                    "context": context,
                })

        except Exception as e:
            log(f"  [{i}] Error reading result: {e}")

    return clinics


def book_appointment(tamuz, page, clinic):
    """Click into a clinic's calendar and book the first available slot."""
    doctor = clinic["doctor"]
    log(f"Booking: {doctor} | {clinic['date']}")

    clinic["link"].click()
    tamuz.wait_for_timeout(10000)
    ss(page, "03_calendar")

    book_buttons = tamuz.locator("a.createVisitButton").all()
    log(f"  {len(book_buttons)} time slots available")

    if not book_buttons:
        log("  No booking buttons found")
        return None

    book_buttons[0].click()
    tamuz.wait_for_timeout(8000)
    ss(page, "04_booked")

    body = tamuz.locator("body").inner_text()

    if "הוזמן בהצלחה" not in body:
        log("  Booking may have failed - 'success' text not found")
        ss(page, "04_booking_unclear")
        return None

    details = {"doctor": doctor, "clinic": clinic["clinic"]}
    for line in body.split("\n"):
        line = line.strip()
        if "נקבע ליום" in line:
            details["datetime"] = line
        if "במרפאת" in line:
            details["address"] = line

    log(f"  BOOKED: {details.get('datetime', '?')}")
    log(f"  Location: {details.get('address', '?')}")
    return details


def send_email(subject, message):
    if not TO_EMAIL or not EMAILJS_SERVICE_ID:
        log("Email not configured - skipping")
        return

    try:
        response = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json={
                "service_id": EMAILJS_SERVICE_ID,
                "template_id": EMAILJS_TEMPLATE_ID,
                "user_id": EMAILJS_PUBLIC_KEY,
                "accessToken": EMAILJS_PRIVATE_KEY,
                "template_params": {
                    "to_email": TO_EMAIL,
                    "name": subject,
                    "email": TO_EMAIL,
                    "message": message,
                },
            },
        )
        if response.status_code == 200:
            log(f"Email sent to {TO_EMAIL}")
        else:
            log(f"Email error: {response.text}")
    except Exception as e:
        log(f"Email error: {e}")


def disable_workflow():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return
    try:
        requests.put(
            f"https://api.github.com/repos/{repo}/actions/workflows/check.yml/disable",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        log("GitHub workflow disabled (appointment found)")
    except Exception:
        pass


def main():
    log("=== Clalit Dermatologist Checker ===")
    log(f"City: {CITY} | Exclude hospitals: {EXCLUDE_HOSPITALS}")
    if TEST_MODE:
        log("*** TEST MODE — scan only, no booking ***")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="he-IL",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            if not login(page):
                return False

            tamuz = open_tamuz(page)
            if not tamuz:
                return False

            search_dermatology(tamuz, page)

            clinics = find_bookable_clinics(tamuz)

            if TEST_MODE:
                # --- TEST: just report what's available and email ---
                lines = []
                if clinics:
                    lines.append(f"Found {len(clinics)} available clinic(s):\n")
                    for c in clinics:
                        lines.append(f"- {c['doctor']}")
                        lines.append(f"  {c['date']}")
                        lines.append(f"  {c['clinic']}\n")
                else:
                    lines.append("No available appointments in Holon clinics.")

                # Also list skipped results
                all_links = tamuz.locator('a:has-text("לכל התורים")').all()
                if all_links:
                    lines.append(f"\nTotal results with dates: {len(all_links)}")
                    lines.append("(some filtered out: hospitals / wrong city)")

                report = "\n".join(lines)
                log("\n" + report)
                send_email("Clalit Test Scan", report)
                return len(clinics) > 0

            # --- PRODUCTION: book first available ---
            if not clinics:
                log("No available appointments matching criteria")
                return False

            log(f"\n{len(clinics)} bookable clinic(s) found!")

            details = book_appointment(tamuz, page, clinics[0])
            if not details:
                log("Booking failed")
                return False

            log("\nAPPOINTMENT BOOKED SUCCESSFULLY!")
            message = (
                f"Clalit appointment booked!\n\n"
                f"Doctor: {details.get('doctor', '?')}\n"
                f"When: {details.get('datetime', '?')}\n"
                f"Where: {details.get('address', '?')}\n"
                f"Clinic: {details.get('clinic', '?')}\n\n"
                f"Manage: {TAMUZ_URL}"
            )
            send_email("Clalit Appointment BOOKED!", message)
            disable_workflow()
            return True

        except Exception as e:
            log(f"ERROR: {e}")
            ss(page, "error")
            return False
        finally:
            browser.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
