from playwright.sync_api import sync_playwright
from config import *
import requests
import os

def check_availability():
    url = (
        f"https://www.fattal.co.il/search"
        f"?In={CHECK_IN}&Out={CHECK_OUT}"
        f"&city=eilat-hotels&country=israel&flight=no_flights"
        f"&Rooms={ROOMS}&Ad1={ADULTS}&Ch1={CHILDREN}&Inf1={INFANTS}"
    )

    print(f"🔍 בודק זמינות ביו ספלאש...")
    print(f"   צ'ק אין: {CHECK_IN} | צ'ק אאוט: {CHECK_OUT}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="he-IL",
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=90000)
        except Exception as e:
            print(f"⚠️ Page load timed out, checking what loaded so far...")

        # Wait for search result cards to appear
        try:
            page.wait_for_selector('[id^="search-page-search-result-main_"]', timeout=45000)
        except Exception:
            print("❌ No search results loaded — U Splash not available")
            browser.close()
            return False

        cards = page.query_selector_all('[id^="search-page-search-result-main_"]')
        print(f"   נמצאו {len(cards)} תוצאות חיפוש")

        found = False
        for card in cards:
            text = card.inner_text()
            html = card.inner_html()
            if "יו ספלאש" in text or "u-splash-resort-eilat-hotel" in html:
                found = True
                break

        browser.close()

    if found:
        print("✅ יו ספלאש זמין! שולח מייל...")
        send_email()
        disable_workflow()
    else:
        print("❌ יו ספלאש לא זמין בתאריכים אלו")

    return found

def send_email():
    response = requests.post(
        "https://api.emailjs.com/api/v1.0/email/send",
        json={
            "service_id":  EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id":     EMAILJS_PUBLIC_KEY,
            "accessToken": EMAILJS_PRIVATE_KEY,
            "template_params": {
                "to_email": TO_EMAIL,
                "name":     "Fattal Alert",
                "email":    TO_EMAIL,
                "message":  f"Room available at U Splash Resort Eilat!\nCheck-in: {CHECK_IN} | Check-out: {CHECK_OUT}\nBook now: https://www.fattal.co.il/hotel/u-splash-resort-eilat-hotel"
            }
        }
    )
    if response.status_code == 200:
        print(f"📧 מייל נשלח בהצלחה ל-{TO_EMAIL}")
    else:
        print(f"⚠️ שגיאה בשליחת מייל: {response.text}")

def disable_workflow():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("⚠️ Cannot disable workflow — not running in GitHub Actions")
        return

    workflow_id = "check.yml"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/disable"
    response = requests.put(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    if response.status_code == 204:
        print("🛑 Workflow disabled — no more automatic checks")
    else:
        print(f"⚠️ Could not disable workflow: {response.status_code} {response.text}")

if __name__ == "__main__":
    check_availability()
