from init import app 
from flask import render_template

@app.route("/")
def index():
    return "Index test"

@app.route("/test")
def test():
    return "Another test"

