import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    
    # קריאת GOOGLE_CLIENT_SECRET מתוך קובץ ב-Render או ממשתנה סביבה
    SECRET_FILE_PATH = os.getenv("SECRET_FILE")
    if SECRET_FILE_PATH and os.path.exists(SECRET_FILE_PATH):
        with open(SECRET_FILE_PATH, "r") as file:
            GOOGLE_CLIENT_SECRET = file.read().strip()
    else:
        GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    
    AUTHORIZED_EMAILS = {"nroznim@gmail.com", "naamakunik@gmail.com"}

    # הדפסת הערכים לבדיקת טעינה נכונה (למחוק ב-production)
    print(f"SECRET_KEY: {SECRET_KEY}")
    print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
    print(f"GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET}")  # אל תדפיס ב-production
