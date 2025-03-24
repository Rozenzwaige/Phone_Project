from flask import Flask, redirect, url_for, session, render_template, flash, request
from authlib.integrations.flask_client import OAuth
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)

# הדפסת הערכים של ה-client_id ו-client_secret
print(f"GOOGLE_CLIENT_ID: {app.config['GOOGLE_CLIENT_ID']}")
print(f"GOOGLE_CLIENT_SECRET: {app.config['GOOGLE_CLIENT_SECRET']}")  # אל תדפיס ב-production

logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# הדפסת משתנים כדי לוודא שהם נטענים נכון
print("GOOGLE_CLIENT_ID:", app.config["GOOGLE_CLIENT_ID"])
print("GOOGLE_CLIENT_SECRET:", app.config["GOOGLE_CLIENT_SECRET"])

# הגדרת Google OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v1/userinfo',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'consent'  # מבטיח ש-Google יבקש שוב אישור אם יש בעיות
    },
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"
)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize', _external=True)
    app.logger.info(f"Redirecting to Google OAuth: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    try:
        app.logger.info(f"Request args: {dict(request.args)}")  # הצגת הפרמטרים שהתקבלו
        token = google.authorize_access_token()
        app.logger.info(f"Token received: {token}")

        if not token:
            app.logger.error("No token received!")
            session.clear()  # מחיקת הסשן במקרה של כשל
            return "No token received", 401

        # שמירת ה-token ב-session כדי שנוכל להשתמש בו אחר כך
        session['token'] = token
        app.logger.info(f"Token stored in session: {session['token']}")

        user_info = google.get('userinfo').json()
        app.logger.info(f"User Info: {user_info}")

        user_email = user_info.get('email')
        if not user_email:
            app.logger.error("Failed to fetch user email")
            return "Failed to fetch user email", 401

        if user_email not in app.config['AUTHORIZED_EMAILS']:
            app.logger.warning(f"Unauthorized login attempt: {user_email}")
            flash('הכניסה לא מורשית עבור חשבון זה', 'danger')
            return redirect(url_for('login'))

        session['user'] = user_info
        return redirect(url_for('welcome'))
    
    except Exception as e:
        app.logger.error(f"Authorization Error: {str(e)}")
        session.clear()  # ניקוי סשן למניעת שגיאות חוזרות
        return f"Authorization failed: {str(e)}", 500

@app.route('/welcome')
def welcome():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html', email=session['user']['email'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('token', None)  # מחיקת ה-token מה-session בעת יציאה
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
