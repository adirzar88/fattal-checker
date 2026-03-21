import requests
from config import *

def check_availability():
    url = (
        f"https://www.fattal.co.il/search"
        f"?In={CHECK_IN}&Out={CHECK_OUT}"
        f"&city=eilat-hotels&country=israel&flight=no_flights"
        f"&Rooms={ROOMS}&Ad1={ADULTS}&Ch1={CHILDREN}&Inf1={INFANTS}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "he-IL,he;q=0.9",
    }

    print(f"🔍 בודק זמינות ביו ספלאש...")
    print(f"   צ'ק אין: {CHECK_IN} | צ'ק אאוט: {CHECK_OUT}")

    response = requests.get(url, headers=headers, timeout=30)
    html = response.text

    # בדיקה אם יו ספלאש מופיע בתוצאות
    found = "u-splash-resort-eilat-hotel" in html or "יו ספלאש" in html

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
