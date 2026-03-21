import os

# ===================================
# הגדרות בדיקת זמינות יו ספלאש
# ===================================

# תאריכים
CHECK_IN  = "2026-03-27"   # תאריך הגעה (YYYY-MM-DD)
CHECK_OUT = "2026-03-28"   # תאריך עזיבה (YYYY-MM-DD)

# הרכב האורחים
ADULTS   = 2
CHILDREN = 2
INFANTS  = 1
ROOMS    = 1

# Sensitive values loaded from environment variables (GitHub Secrets)
TO_EMAIL            = os.environ["TO_EMAIL"]
EMAILJS_SERVICE_ID  = os.environ["EMAILJS_SERVICE_ID"]
EMAILJS_TEMPLATE_ID = os.environ["EMAILJS_TEMPLATE_ID"]
EMAILJS_PUBLIC_KEY  = os.environ["EMAILJS_PUBLIC_KEY"]
EMAILJS_PRIVATE_KEY = os.environ["EMAILJS_PRIVATE_KEY"]
