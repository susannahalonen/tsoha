from init import app
from flask import render_template, request, redirect, session
from init import db
import users
from sqlalchemy.sql import text

@app.route("/")
def index():
    categories = db.session.execute(text("SELECT * FROM categories ORDER BY last_message_date DESC"))
    categories = categories.fetchall()
    return render_template("index.html", categories=categories)

@app.route("/new_thread", methods=["GET", "POST"])
def new_thread():
    if request.method == "GET":
        categories = db.session.execute(text("SELECT id, name FROM categories")).fetchall()
        return render_template("new_thread.html", categories=categories)
    
    if request.method == "POST":
        title = request.form["title"]
        category_id = request.form["category"]
        user_id = session.get("user_id")
        
        if user_id:
            db.session.execute(text("INSERT INTO threads (title, user_id, category_id) VALUES (:title, :user_id, :category_id)"), 
                               {"title": title, "user_id": user_id, "category_id": category_id})
            db.session.commit()
            
            db.session.execute(text("UPDATE categories SET thread_count = thread_count + 1 WHERE id = :category_id"), 
                               {"category_id": category_id})
            db.session.commit()

            return redirect("/") 
        else:
            return redirect("/login")  

@app.route("/thread/<int:thread_id>")
def thread(thread_id):
    thread = db.session.execute(text("SELECT id, title, user_id, last_message_date FROM threads WHERE id = :id"), {"id": thread_id}).fetchone()
    
    if thread:
        messages = db.session.execute(text("SELECT content, user_id, sent_at FROM messages WHERE thread_id = :id ORDER BY sent_at ASC"), {"id": thread_id}).fetchall()
        return render_template("thread.html", thread=thread, messages=messages)
    else:
        return render_template("error.html", message="Thread not found")

@app.route("/message/<int:thread_id>", methods=["POST"])
def post_message(thread_id):
    content = request.form["message"]
    user_id = session.get("user_id")
    
    if user_id:
        db.session.execute(text("INSERT INTO messages (content, user_id, thread_id) VALUES (:content, :user_id, :thread_id)"), 
                           {"content": content, "user_id": user_id, "thread_id": thread_id})
        db.session.commit()

        thread_category_id = db.session.execute(text("SELECT category_id FROM threads WHERE id = :thread_id"), {"thread_id": thread_id}).fetchone()[0]
        db.session.execute(text("UPDATE categories SET message_count = message_count + 1 WHERE id = :category_id"), 
                           {"category_id": thread_category_id})
        db.session.commit()

        db.session.execute(text("UPDATE categories SET last_message_date = CURRENT_TIMESTAMP WHERE id = :category_id"), 
                           {"category_id": thread_category_id})
        db.session.commit()

        return redirect(f"/thread/{thread_id}")
    else:
        return redirect("/login") 

@app.route("/test")
def test():
    return "Another test"

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get('user_id'):
        return redirect("/")

    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        username = request.form["username"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]
        if password1 != password2:
            return render_template("error.html", message="Passwords do not match")
        if users.register(username, password1):
            return redirect("/login")
        else:
            return render_template("error.html", message="Registration failed")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get('user_id'):
        return redirect("/")

    if request.method == "GET":
        return render_template("login.html")
    
    if request.method == "POST":
        print("asdewr")
        username = request.form["username"]
        password = request.form["password"]

        if users.login(username, password):
            return redirect("/")
        else:
            return render_template("error.html", message="Invalid username or password")

@app.route("/logout", methods=["POST"])
def logout():
    users.logout()
    return redirect("/")
