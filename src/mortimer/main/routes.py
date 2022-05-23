import os
import time
from flask import Blueprint, render_template, current_app, send_file, after_this_request, redirect, request, url_for
from flask_login import login_required, current_user
from uuid import uuid4
from mortimer.forms import NewScriptForm, FuturizeScriptForm
from mortimer.utils import perform_futurization, replace_all_patterns

main = Blueprint("main", __name__)

# this route has two addresses


@main.route("/")
@main.route("/home")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for("users.login"))

    id = str(uuid4())
    return render_template("home.html", id=id)


@main.route("/about")
@login_required
def about():
    return render_template("about.html")


@main.route("/impressum")
def impressum():
    return render_template("impressum.html")


@main.route("/futurize_script", methods=["POST", "GET"])
@login_required
def futurize_script(script_name=None):

    # clean up operation: delete files from the temp directory, if they are older than 15 minutes
    temp_path = os.path.join(current_app.instance_path, "tmp", "futurize_scripts")
    if not os.path.isdir(temp_path):
        os.makedirs(temp_path)
    s_since_epoch = time.time()

    for file in os.listdir(temp_path):
        file_path = os.path.join(temp_path, file)
        creation_of_file = os.path.getmtime(file_path)

        if (s_since_epoch - creation_of_file) > 900:
            os.remove(file_path)

    form = FuturizeScriptForm()

    if form.validate_on_submit():
        filename = str(uuid4()) + ".py"
        filepath = os.path.join(temp_path, filename)
        filepath_bak = os.path.join(temp_path, filename + '.bak')

        with open(filepath, "w", encoding='utf-8') as f:
            f.write(form.script.data)

        perform_futurization(filepath)
        replace_all_patterns(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            new_script = f.read()

        os.remove(filepath)
        try:
            os.remove(filepath_bak)
        except FileNotFoundError:
            pass

        return render_template('futurize_script.html', form=form, new_script=new_script)

    return render_template("futurize_script.html", form=form, script_name=script_name)
