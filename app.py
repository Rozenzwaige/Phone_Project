from flask import Flask, redirect, url_for, session, render_template
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")  # עדיף משתנה סביבה

# קריאת GOOGLE_CLIENT_SECRET מתוך הקובץ ב-Render או ממשתנה סביבה
secret_file_path = os.getenv("SECRET_FILE")
if secret_file_path and os.path.exists(secret_file_path):
    with open(secret_file_path, "r") as file:
        GOOGLE_CLIENT_SECRET = file.read().strip()
else:
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")  # גיבוי ממשתנה סביבה

# הגדרת Google OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize', _external=True)  # לוודא שזה נכון ב-Google Cloud
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    if not token:
        return redirect(url_for('login'))  # במקרה של כשלון
    user_info = google.get('userinfo').json()
    session['user'] = user_info
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html', email=session['user']['email'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
