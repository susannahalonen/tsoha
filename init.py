from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import getenv

app = Flask(__name__)
app.secret_key = getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DATABASE_URL")
print(f"DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
db = SQLAlchemy()
db.init_app(app)