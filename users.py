from init import db
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import text 

def register(username, password):
    hash_value = generate_password_hash(password)
    try:
        sql = text("INSERT INTO users (username, password) VALUES (:username, :password)")
        db.session.execute(sql, {"username": username, "password": hash_value})
        db.session.commit()
    except Exception as e:
        print(f"Registration error: {e}")
        return False
    return True


def login(username, password):
    sql = text("SELECT id, password FROM users WHERE username=:username")
    result = db.session.execute(sql, {"username": username})
    user = result.fetchone()
    if not user:
        return False
    if check_password_hash(user.password, password):
        session["user_id"] = user.id
        return True
    return False

def logout():
    session.clear()
