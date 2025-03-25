from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    approved = db.Column(db.Boolean, default=False)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if user.approved:
                session['user_id'] = user.id
                return redirect(url_for('dashboard'))
            else:
                flash('החשבון ממתין לאישור מנהל.', 'warning')
        else:
            flash('שם משתמש או סיסמה שגויים.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('הרשמה הושלמה! יש להמתין לאישור מנהל.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user = User.query.get(user_id)
        if user:
            user.approved = True
            db.session.commit()
            flash(f'משתמש {user.email} אושר!', 'success')
    users = User.query.filter_by(approved=False).all()
    return render_template('admin.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)
