from init import app
from flask import render_template, request, redirect, session
from init import db
import users
from sqlalchemy.sql import text

@app.route("/")
def index():
    user_id = session.get("user_id")
    user_role = session.get("user_role")

    if not user_id:
        categories = db.session.execute(
            text("SELECT * FROM categories WHERE id NOT IN (SELECT category_id FROM secret_categories)")
        ).fetchall()
    elif user_role == "admin":
        categories = db.session.execute(
            text("SELECT * FROM categories")
        ).fetchall()
    else:
        categories = db.session.execute(
            text("""
                SELECT c.*
                FROM categories c
                LEFT JOIN secret_categories sc ON c.id = sc.category_id
                WHERE sc.user_id = :user_id OR sc.category_id IS NULL
            """),
            {"user_id": user_id}
        ).fetchall()
    
    return render_template("index.html", categories=categories)


@app.route("/new_thread", methods=["GET", "POST"])
def new_thread():
    if request.method == "GET":
        categories = db.session.execute(text("SELECT id, name FROM categories")).fetchall()
        return render_template("new_thread.html", categories=categories)
    
    if request.method == "POST":
        title = request.form["title"]
        category_id = request.form["category"]
        first_message = request.form["message"]
        user_id = session.get("user_id")
        
        if user_id:
            thread_id = db.session.execute(
                text("INSERT INTO threads (title, user_id, category_id) VALUES (:title, :user_id, :category_id) RETURNING id"),
                {"title": title, "user_id": user_id, "category_id": category_id}
            ).fetchone()[0]
            db.session.commit()

            db.session.execute(
                text("INSERT INTO messages (content, user_id, thread_id) VALUES (:content, :user_id, :thread_id)"),
                {"content": first_message, "user_id": user_id, "thread_id": thread_id}
            )
            db.session.commit()

            db.session.execute(
                text("UPDATE categories SET thread_count = thread_count + 1, message_count = message_count + 1, last_message_date = CURRENT_TIMESTAMP WHERE id = :category_id"),
                {"category_id": category_id}
            )
            db.session.commit()

            return redirect(f"/thread/{thread_id}") 
        else:
            return redirect("/login")


@app.route("/message/<int:thread_id>", methods=["POST"])
def post_message(thread_id):
    content = request.form["message"]
    user_id = session.get("user_id")
    
    if user_id:
        db.session.execute(
            text("INSERT INTO messages (content, user_id, thread_id) VALUES (:content, :user_id, :thread_id)"),
            {"content": content, "user_id": user_id, "thread_id": thread_id}
        )
        db.session.commit()

        thread_category_id = db.session.execute(
            text("SELECT category_id FROM threads WHERE id = :thread_id"),
            {"thread_id": thread_id}
        ).fetchone()[0]

        db.session.execute(
            text("UPDATE categories SET message_count = message_count + 1 WHERE id = :category_id"),
            {"category_id": thread_category_id}
        )
        db.session.commit()

        db.session.execute(
            text("UPDATE categories SET last_message_date = CURRENT_TIMESTAMP WHERE id = :category_id"),
            {"category_id": thread_category_id}
        )
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
        username = request.form["username"]
        password = request.form["password"]

        if users.login(username, password):
            user = db.session.execute(
                text("SELECT id, role FROM users WHERE username=:username"),
                {"username": username}
            ).fetchone()
            if user:
                session["user_role"] = user.role
            return redirect("/")
        else:
            return render_template("error.html", message="Invalid username or password")

@app.route("/logout", methods=["POST"])
def logout():
    users.logout()
    return redirect("/")

@app.route("/edit_message/<int:message_id>", methods=["GET", "POST"])
def edit_message(message_id):
    user_id = session.get("user_id")
    
    message = db.session.execute(
        text("SELECT id, content, user_id, thread_id FROM messages WHERE id = :id"),
        {"id": message_id}
    ).fetchone()

    if not message:
        return render_template("error.html", message="Message not found")
    
    if message.user_id != user_id:
        return render_template("error.html", message="You are not authorized to edit this message")
    
    if request.method == "GET":
        return render_template("edit_message.html", message=message)
    
    if request.method == "POST":
        new_content = request.form["content"]
        db.session.execute(
            text("UPDATE messages SET content = :content, sent_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"content": new_content, "id": message_id}
        )
        db.session.commit()
        return redirect(f"/thread/{message.thread_id}")



@app.route("/delete_message/<int:message_id>", methods=["POST"])
def delete_message(message_id):
    user_id = session.get("user_id")
    
    message = db.session.execute(
        text("SELECT id, user_id, thread_id FROM messages WHERE id = :id"),
        {"id": message_id}
    ).fetchone()

    if not message:
        return render_template("error.html", message="Message not found")
    
    if message.user_id != user_id:
        return render_template("error.html", message="You are not authorized to delete this message")
    
    db.session.execute(
        text("DELETE FROM messages WHERE id = :id"),
        {"id": message_id}
    )
    db.session.commit()
    
    return redirect(f"/thread/{message.thread_id}")


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query")
    
    if not query:
        return render_template("error.html", message="Please provide a search term.")
    
    results = db.session.execute(
        text("SELECT m.content, m.sent_at, m.thread_id, u.username FROM messages m "
             "JOIN users u ON m.user_id = u.id "
             "WHERE m.content ILIKE :query"),
        {"query": f"%{query}%"}
    ).fetchall()
    
    return render_template("search_results.html", results=results, query=query)


@app.route("/create_category", methods=["GET", "POST"])
def create_category():
    user_id = session.get("user_id")
    user_role = session.get("user_role") 
    if not user_id or user_role != "admin":
        return render_template("error.html", message="You are not authorized to create categories")

    if request.method == "GET":
        return render_template("create_category.html")

    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description", "")
        try:
            db.session.execute(
                text("INSERT INTO categories (name, description) VALUES (:name, :description)"),
                {"name": name, "description": description}
            )
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return render_template("error.html", message=f"An error occurred: {e}")

@app.route("/category/<int:category_id>")
def category(category_id):
    category = db.session.execute(
        text("SELECT id, name, description FROM categories WHERE id = :id"),
        {"id": category_id}
    ).fetchone()

    if not category:
        return render_template("error.html", message="Category not found")
    
    threads = db.session.execute(
        text("SELECT id, title, created_at FROM threads WHERE category_id = :id ORDER BY created_at DESC"),
        {"id": category_id}
    ).fetchall()
    
    return render_template("category.html", category=category, threads=threads)

@app.route("/thread/<int:thread_id>")
def thread(thread_id):
    thread = db.session.execute(
        text("SELECT t.id, t.title, t.user_id, t.created_at, u.username "
            "FROM threads t "
            "JOIN users u ON t.user_id = u.id "
            "WHERE t.id = :id"),
        {"id": thread_id}
    ).fetchone()

    if not thread:
        return render_template("error.html", message="Thread not found")

    messages = db.session.execute(
        text("""
            SELECT m.id, m.content, m.user_id, m.sent_at, u.username,
                (SELECT COUNT(*) FROM likes WHERE message_id = m.id) AS like_count,
                EXISTS (
                    SELECT 1
                    FROM likes
                    WHERE message_id = m.id AND user_id = :user_id
                ) AS user_has_liked
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.thread_id = :thread_id
            ORDER BY m.sent_at ASC
        """),
        {"thread_id": thread_id, "user_id": session.get("user_id")}
    ).fetchall()

    return render_template("thread.html", thread=thread, messages=messages)

@app.route("/thread/<int:thread_id>/search", methods=["GET"])
def search_in_thread(thread_id):
    query = request.args.get("query")
    
    if not query:
        return render_template("error.html", message="Please provide a search term.")
    
    thread = db.session.execute(
        text("SELECT id, title, user_id, created_at FROM threads WHERE id = :id"),
        {"id": thread_id}
    ).fetchone()

    if not thread:
        return render_template("error.html", message="Thread not found")
    
    results = db.session.execute(
        text("SELECT m.content, m.sent_at, u.username FROM messages m "
             "JOIN users u ON m.user_id = u.id "
             "WHERE m.thread_id = :thread_id AND m.content ILIKE :query"),
        {"thread_id": thread_id, "query": f"%{query}%"}
    ).fetchall()
    
    return render_template("thread_search_results.html", thread=thread, results=results, query=query)

@app.route("/edit_thread/<int:thread_id>", methods=["GET", "POST"])
def edit_thread(thread_id):
    user_id = session.get("user_id")
    
    thread = db.session.execute(
        text("SELECT id, title, user_id FROM threads WHERE id = :id"),
        {"id": thread_id}
    ).fetchone()

    if not thread:
        return render_template("error.html", message="Thread not found")
    
    if thread.user_id != user_id:
        return render_template("error.html", message="You are not authorized to edit this thread")
    
    if request.method == "GET":
        return render_template("edit_thread.html", thread=thread)
    
    if request.method == "POST":
        new_title = request.form["title"]
        db.session.execute(
            text("UPDATE threads SET title = :title WHERE id = :id"),
            {"title": new_title, "id": thread_id}
        )
        db.session.commit()
        return redirect(f"/thread/{thread_id}")

@app.route("/delete_thread/<int:thread_id>", methods=["POST"])
def delete_thread(thread_id):
    user_id = session.get("user_id")
    
    thread = db.session.execute(
        text("SELECT id, user_id FROM threads WHERE id = :id"),
        {"id": thread_id}
    ).fetchone()

    if not thread:
        return render_template("error.html", message="Thread not found")
    
    if thread.user_id != user_id:
        return render_template("error.html", message="You are not authorized to delete this thread")
    
    db.session.execute(
        text("DELETE FROM threads WHERE id = :id"),
        {"id": thread_id}
    )
    db.session.commit()
    
    return redirect("/")

@app.route("/make_secret/<int:category_id>", methods=["GET", "POST"])
def make_secret(category_id):
    user_id = session.get("user_id")
    user_role = session.get("user_role")
    
    if not user_id or user_role != "admin":
        return render_template("error.html", message="You are not authorized to manage secret categories.")
    
    category = db.session.execute(
        text("SELECT id, name FROM categories WHERE id = :id"),
        {"id": category_id}
    ).fetchone()

    if not category:
        return render_template("error.html", message="Category not found.")

    if request.method == "GET":
        users = db.session.execute(
            text("SELECT id, username FROM users WHERE id != :admin_id"),
            {"admin_id": user_id}
        ).fetchall()
        return render_template("make_secret.html", category=category, users=users)
    
    if request.method == "POST":
        selected_users = request.form.getlist("user_ids")
        
        for selected_user_id in selected_users:
            db.session.execute(
                text("INSERT INTO secret_categories (category_id, user_id) VALUES (:category_id, :user_id)"),
                {"category_id": category_id, "user_id": selected_user_id}
            )
        db.session.commit()
        
        return redirect("/")

@app.route("/like_message/<int:message_id>", methods=["POST"])
def like_message(message_id):
    user_id = session.get("user_id")
    
    if not user_id:
        return redirect("/login")
    
    like = db.session.execute(
        text("SELECT id FROM likes WHERE message_id = :message_id AND user_id = :user_id"),
        {"message_id": message_id, "user_id": user_id}
    ).fetchone()
    
    if like:
        db.session.execute(
            text("DELETE FROM likes WHERE id = :id"),
            {"id": like.id}
        )
    else:
        db.session.execute(
            text("INSERT INTO likes (message_id, user_id) VALUES (:message_id, :user_id)"),
            {"message_id": message_id, "user_id": user_id}
        )
    db.session.commit()
    
    thread_id = db.session.execute(
        text("SELECT thread_id FROM messages WHERE id = :message_id"),
        {"message_id": message_id}
    ).fetchone()[0]
    return redirect(f"/thread/{thread_id}")
