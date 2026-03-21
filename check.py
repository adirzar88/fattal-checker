from playwright.sync_api import sync_playwright
from config import *
import requests

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
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait for search result cards to appear
        try:
            page.wait_for_selector('[id^="search-page-search-result-main_"]', timeout=30000)
        except Exception:
            print("❌ No search results loaded — U Splash not available")
            browser.close()
            return False

        cards = page.query_selector_all('[id^="search-page-search-result-main_"]')
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

if __name__ == "__main__":
    check_availability()
