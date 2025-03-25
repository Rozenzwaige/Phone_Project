from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# יצירת מופע Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ייבוא המודלים כדי לוודא שהם נטענים
from models import User

# יצירת מסד הנתונים באופן אוטומטי בעת עליית האפליקציה
with app.app_context():
    db.create_all()
    print("Database initialized successfully!")

if __name__ == '__main__':
    app.run(debug=True)
