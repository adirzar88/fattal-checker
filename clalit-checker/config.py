import os

# ===================================
# Clalit Dermatologist Appointment Checker
# ===================================

# Login credentials (from env vars / GitHub Secrets)
ID_NUMBER = os.environ.get("CLALIT_ID", "")
USER_CODE = os.environ.get("CLALIT_USER_CODE", "")
PASSWORD  = os.environ.get("CLALIT_PASSWORD", "")

# Search filters
CITY = "חולון"
EXCLUDE_HOSPITALS = True

# Email notifications (EmailJS)
TO_EMAIL            = os.environ.get("TO_EMAIL", "")
EMAILJS_SERVICE_ID  = os.environ.get("EMAILJS_SERVICE_ID", "")
EMAILJS_TEMPLATE_ID = os.environ.get("EMAILJS_TEMPLATE_ID", "")
EMAILJS_PUBLIC_KEY  = os.environ.get("EMAILJS_PUBLIC_KEY", "")
EMAILJS_PRIVATE_KEY = os.environ.get("EMAILJS_PRIVATE_KEY", "")
