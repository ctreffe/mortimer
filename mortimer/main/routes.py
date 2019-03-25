from flask import Blueprint, render_template

main = Blueprint("main", __name__)

# this route has two adresses


@main.route("/")
@main.route("/home")
def home():
    return render_template("home.html")


@main.route("/about")
def about():
    return render_template("about.html")
