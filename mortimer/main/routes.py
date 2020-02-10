import os
import time
from flask import Blueprint, render_template, current_app, send_file, after_this_request
from flask_login import login_required
from uuid import uuid4
from mortimer.forms import NewScriptForm
from mortimer.utils import futurize_script, replace_all_patterns

main = Blueprint("main", __name__)

# this route has two addresses


@main.route("/")
@main.route("/home")
@login_required
def home():
    return render_template("home.html")


@main.route("/about")
@login_required
def about():
    return render_template("about.html")


@main.route("/impressum")
def impressum():
    return render_template("impressum.html")


@main.route("/futurize_script_online", methods=["POST", "GET"])
@login_required
def futurize_script_online(script_name=None):

    # clean up operation: delete file from the temp directory, if they are older than 15 minutes
    temp_path = os.path.join(current_app.root_path, "temp")
    if not os.path.isdir(temp_path):
        os.makedirs(temp_path)
    s_since_epoch = time.time()

    for file in os.listdir(temp_path):
        file_path = os.path.join(temp_path, file)
        creation_of_file = os.path.getmtime(file_path)

        if (s_since_epoch - creation_of_file) > 900:
            os.remove(file_path)

    # create form instance
    form = NewScriptForm()

    # futurize script
    if form.validate_on_submit():
        script = form.script.data
        script_name = str(uuid4())
        script_path = os.path.join(current_app.root_path, "temp", script_name + ".py")

        script.save(script_path)
        futurize_script(script_path)
        replace_all_patterns(script_path)

        return render_template("futurize_script.html", form=form, script_name=script_name)

    return render_template("futurize_script.html", form=form, script_name=script_name)


@main.route("/donwload_futurized_script/<name>", methods=["GET"])
@login_required
def download_futurized_script(name):

    path = os.path.join(current_app.root_path, "temp", name + ".py")

    # clean up: delete file after it was downloaded
    @after_this_request
    def remove_script(response):
        os.remove(path)
        os.remove(path + ".bak")

        return response

    return send_file(path, as_attachment=True, attachment_filename="futurized_script.py")
