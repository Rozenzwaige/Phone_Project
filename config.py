import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    SECRET_FILE = os.getenv("SECRET_FILE")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = None
    AUTHORIZED_EMAILS = ["nroznim@gmail.com", "naamakunik@gmail.com"]

    # קריאת GOOGLE_CLIENT_SECRET מתוך הקובץ ב-Render או ממשתנה סביבה
    if SECRET_FILE and os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r") as file:
            GOOGLE_CLIENT_SECRET = file.read().strip()
    else:
        GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
