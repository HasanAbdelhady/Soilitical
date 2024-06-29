from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # cross origin requests, to prevent an error
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "fd7254bde95d007e9cf5eec08e864ac399f202fb920ce5e9"
app.config['WTF_CSRF_SECRET_KEY'] = 'a_different_random_string_for_csrf_protection'

db = SQLAlchemy(app)  # this is an ORM ( Object relationsal mapping, python => SQL )

csrf = CSRFProtect(app)
CORS(app)  # enabling CORS
