from init import app 
from flask import render_template, request, redirect
import users 

@app.route("/")
def index():
    return "Index test"

@app.route("/test")
def test():
    return "Another test"

@app.route("/register", methods=["GET", "POST"])
def register():
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
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if users.login(username, password):
            return redirect("/")
        else:
            return render_template("error.html", message="Invalid username or password")

@app.route("/logout")
def logout():
    users.logout()
    return redirect("/")
