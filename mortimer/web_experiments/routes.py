import os
import shutil
import re
from mortimer import export
from flask import Blueprint, render_template, url_for, flash, redirect, request, abort, current_app, send_file
from mortimer.forms import WebExperimentForm, UpdateExperimentForm, NewScriptForm, ExperimentExportForm
from mortimer.models import User, WebExperiment
from mortimer.utils import display_directory, ScriptFile, ScriptString
from mortimer import alfred_web_db
from mortimer.config import Config
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime
from uuid import uuid4

web_experiments = Blueprint("web_experiments", __name__)


@web_experiments.route("/experiment/new", methods=["GET", "POST"])
@login_required
def new_experiment():

    form = WebExperimentForm()

    if form.validate_on_submit():

        exp = WebExperiment(title=form.title.data, author=current_user.username,
                            version=form.version.data, description=form.description.data)

        exp.available_versions.append(form.version.data)
        exp.directory_name = str(uuid4())
        exp.path = os.path.join(current_app.root_path, "exp", exp.directory_name)

        # create experiment directory
        try:
            os.makedirs(exp.path)
        except OSError:
            flash("Action aborted: The experiment directory already exists on the file system.", "danger")
            return redirect(url_for('web_experiments.new_experiment'))

        # process script.py
        if form.script.data:
            script = ScriptFile(exp, form.script.data)
            script.load()
            script.parse()
            script.save()

        # set password protection if password is given
        if form.password.data:
            exp.public = False
            exp.password = form.password.data
        else:
            exp.public = True

        # save the exp to the data base
        exp.save()

        # append an entry for the current experiment to the current user
        current_user.experiments.append(exp.id)
        current_user.save()

        flash("Your Experiment has been created.", "success")

        return redirect(url_for('web_experiments.user_experiments', username=current_user.username))

    return render_template("create_experiment.html", title="New Experiment", form=form,
                           legend="New Experiment")


@web_experiments.route("/<username>/<path:exp_title>", methods=["POST", "GET"])
@login_required
def experiment(username, exp_title):

    exp = WebExperiment.objects.get_or_404(title=exp_title, author=username)

    if exp.author != current_user.username:
        abort(403)

    # Set some status indicators

    if exp.active:
        status = "active"
        toggle_button = "Deactivate"
    else:
        status = "inactive"
        toggle_button = "Activate"

    if exp.public:
        password_protection = "disabled"
    else:
        password_protection = "enabled"

    # Query Database: Number of datasets

    datasets = {}

    datasets["all_datasets"] = alfred_web_db\
        .count_documents({"exp_uuid": exp.id})

    datasets["all_finished_datasets"] = alfred_web_db\
        .count_documents({"exp_uuid": exp.id,
                          "exp_finished": True})

    datasets["all_unfinished_datasets"] = datasets["all_datasets"] - datasets["all_finished_datasets"]

    datasets["datasets_current_version"] = alfred_web_db\
        .count_documents({"exp_uuid": exp.id,
                          "exp_version": exp.version})

    datasets["finished_datasets_current_version"] = alfred_web_db\
        .count_documents({"exp_uuid": exp.id,
                          "exp_version": exp.version,
                          "exp_finished": True})

    datasets["unfinished_datasets_current_version"] = datasets["datasets_current_version"] - datasets["finished_datasets_current_version"]

    # Number of finished datasets per version
    versions = {}
    finished = []
    cur = alfred_web_db.find({"exp_author_mail": current_user.email, "exp_name": exp_title})
    for single_exp in cur:
        if single_exp["exp_version"] not in versions.keys():
            versions[single_exp["exp_version"]] = {"total": 1, "finished": 0, "unfinished": 0}
        else:
            versions[single_exp["exp_version"]]["total"] += 1
        if single_exp["exp_finished"]:
            versions[single_exp["exp_version"]]["finished"] += 1
        else:
            versions[single_exp["exp_version"]]["unfinished"] += 1
        finished.append(single_exp["start_time"])

    # Time of first and last activity
    if finished:
        first_activity = datetime.fromtimestamp(min(finished))\
            .strftime('%Y-%m-%d, %H:%M')
        last_activity = datetime.fromtimestamp(max(finished))\
            .strftime('%Y-%m-%d, %H:%M')
    else:
        first_activity = "none"
        last_activity = "none"

    # Form for script.py upload
    form = NewScriptForm()

    if form.validate_on_submit() and form.script.data:
        # remove old script.py
        try:
            os.remove(exp.script_fullpath)
        except (FileNotFoundError, TypeError):
            pass

        # process script.py
        if form.script.data:
            script = ScriptFile(exp, form.script.data)
            script.load()
            script.parse()
            script.save()

        # update version
        if exp.version != form.version.data:
            exp.version = form.version.data
            exp.available_versions.append(exp.version)

        # save experiment
        exp.save()

        # redirect to experiment page
        flash("New script.py was uploaded successfully", "success")
        return redirect(url_for('web_experiments.experiment', username=exp.author, exp_title=exp.title))

    elif form.validate_on_submit():
        flash("No script.py was provided, so nothing happened.", "info")
        return redirect(url_for('web_experiments.experiment', username=exp.author, exp_title=exp.title))

    # pre-populate form
    form.version.data = exp.version

    return render_template("experiment.html",
                           experiment=exp, expid=str(exp.id), form=form, status=status,
                           toggle_button=toggle_button, datasets=datasets, first_activity=first_activity,
                           last_activity=last_activity, versions=versions, password_protection=password_protection)


@web_experiments.route("/<username>/<path:exp_title>/update", methods=["GET", "POST"])
@login_required
def update_experiment(username, exp_title):

    exp = WebExperiment.objects.get_or_404(title=exp_title, author=username)

    if exp.author != current_user.username:
        abort(403)

    form = UpdateExperimentForm()

    if form.validate_on_submit():

        # check for uniqueness of experiment title
        title = form.title.data
        if title and title != exp.title:
            if WebExperiment.objects(title=title, author=username):
                flash("You already have a web experiment with this title. Please choose a unique title. The \
                changes were not saved.", "danger")
                return redirect(url_for('web_experiments.experiment', exp_title=exp.title, username=exp.author))
            else:
                exp.title = title

        # update password settings
        if form.password.data:
            exp.public = False
            exp.password = form.password.data
        else:
            exp.public = True

        # update script
        script = ScriptString(exp, form.script.data)
        script.parse()
        script.save()

        # update version
        if exp.version != form.version.data:
            exp.version = form.version.data
            exp.available_versions.append(exp.version)

        # save simple updates
        exp.description = form.description.data
        exp.last_update = datetime.utcnow

        # save experiment
        exp.save()

        # return to experiment page
        flash("Your experiment has been updated", "success")
        return redirect(url_for('web_experiments.experiment', exp_title=exp.title, username=exp.author))

    # pre-populate form
    form.title.data = exp.title
    form.description.data = exp.description
    form.password.data = exp.password
    form.script.data = exp.script
    form.version.data = exp.version

    return render_template("update_experiment.html", title="Update Experiment",
                           experiment=exp, form=form, legend="Update Experiment")


@web_experiments.route("/<username>/<path:experiment_title>/delete", methods=["POST", "GET"])  # only allow POST request
@login_required
def delete_experiment(username, experiment_title):

    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)
    try:
        shutil.rmtree(experiment.path)
    except FileNotFoundError:
        flash("Experiment directory didn't exist on file system.", "warning")

    experiment.delete()
    flash("Experiment deleted.", "info")

    return redirect(url_for('web_experiments.user_experiments', username=current_user.username))


@web_experiments.route("/<username>/<path:experiment_title>/upload_resources/<path:relative_path>",
                       methods=["POST", "GET"])
@login_required
def upload_resources(username, experiment_title, relative_path):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    path = os.path.join(experiment.path, relative_path)

    if request.method == 'POST':

        for key, f in request.files.items():

            old_filenames = []
            new_filenames = []

            if key.startswith('file'):
                file_fn = secure_filename(f.filename)
                f.save(os.path.join(path, file_fn))

                old_filenames.append(f.filename)
                new_filenames.append(file_fn)

        # TODO: Display old and new filenames
        if old_filenames != new_filenames:
            for i in range(len(old_filenames)):
                flash("Filename changed from <code>%s</code> to <code>%s</code>." % (old_filenames[i],
                                                                                     new_filenames[i]), "danger")

    return render_template("upload_resources.html", experiment=experiment, legend="Upload Resources",
                           relative_path=relative_path)


@web_experiments.route("/<username>/<path:experiment_title>/manage_resources", methods=["POST", "GET"])
@login_required
def manage_resources(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    # if the experiment path does not exist on the file system, we get a warning
    # this is valuable feedback during development
    if not os.path.exists(experiment.path):
        flash("Experiment path doesn't exist. You probably created the experiment while running mortimer on a \
        different server.", "warning")
        return redirect(url_for("web_experiments.experiment", exp_title=experiment.title,
                                username=experiment.author))

    display = display_directory(sorted(experiment.user_directories), parent_directory=experiment.path,
                                experiment=experiment)

    return render_template("manage_resources.html",
                           legend="Manage Resources", experiment=experiment,
                           display=display)


@web_experiments.route("/experiments")
def experiments():

    if current_user.is_authenticated:
        return redirect(url_for('web_experiments.user_experiments', username=current_user.username))
    else:
        flash("Please log in to access this page.", "info")
        return redirect(url_for("users.login"))


@web_experiments.route("/<string:username>/experiments")
@login_required
def user_experiments(username):

    page = request.args.get("page", 1, type=int)
    user = User.objects.get_or_404(username=username)

    if user.username != current_user.username:
        abort(403)

    experiments = WebExperiment.objects(author=user.username)\
        .order_by("-last_update")\
        .paginate(page=page, per_page=Config.EXP_PER_PAGE)

    return render_template("user_experiments.html", experiments=experiments, user=user)


@web_experiments.route("/<username>/<path:experiment_title>/delete_all_files",
                       methods=["POST"])  # only allow POST requests
@login_required
def delete_all_files(username, experiment_title):

    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    for dir in experiment.user_directories:
        path = os.path.join(experiment.path, dir)
        shutil.rmtree(path)  # remove directory

    experiment.user_directories = []  # empty the file list in the experiment document in mongoDB
    experiment.save()

    flash("All files and directories deleted.", "info")

    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title,
                            username=experiment.author))


@web_experiments.route("/<username>/<path:experiment_title>/new_directory", methods=["POST"], defaults={"relative_path": None})
@web_experiments.route("/<username>/<path:experiment_title>/new_directory/<path:relative_path>", methods=["POST"])
@login_required
def new_directory(username: str, experiment_title: str, relative_path: str=None):
    """
    :param str experiment_title: Title of the experiment
    :param str path: Name of the path in which the new path shall be created
    """

    name = request.form["new_directory"]

    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if not relative_path:
        try:
            os.mkdir(os.path.join(experiment.path, name))
            # if the new directory is a direct subdirectory of the experiment directory,
            # we save the new directory's name in the experiments' db entry
            experiment.user_directories.append(name)
            experiment.save()
        except FileExistsError:
            flash("A directory with this name already exsists.", "warning")
            return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title,
                                    username=experiment.author))
    else:
        try:
            os.mkdir(os.path.join(experiment.path, relative_path, name))
        except FileExistsError:
            flash("A directory with this name already exsists.", "warning")
            return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title,
                                    username=experiment.author))

    flash("New directory created.", "success")

    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title,
                            username=experiment.author))


@web_experiments.route("/<username>/<path:experiment_title>/<path:relative_path>/delete_directory", methods=["POST"])
@login_required
def delete_directory(username, experiment_title, relative_path):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    path = os.path.join(experiment.path, relative_path)
    shutil.rmtree(path)

    if os.path.abspath(os.path.join(path, os.pardir)) == experiment.path:
        experiment.user_directories.remove(os.path.basename(path))
        experiment.save()

    flash("Directory deleted", "info")
    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title,
                            username=experiment.author))


@web_experiments.route("/<username>/<path:experiment_title>/<path:relative_path>/delete_file", methods=["POST"])
@login_required
def delete_file(username, experiment_title, relative_path):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    os.remove(os.path.join(experiment.path, relative_path))

    flash("File deleted.", "info")
    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title,
                            username=experiment.author))


@web_experiments.route("/<username>/<path:experiment_title>/web_export", methods=["POST", "GET"])
@login_required
def web_export(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if not experiment.script:
        flash("You have not uploaded a script.py yet. Please upload a script.py and try again.", "warning")
        return redirect(url_for('web_experiments.experiment', username=current_user.username,
                                exp_title=experiment.title))

    form = ExperimentExportForm()
    form.version.choices = [(version, version) for version in ["all versions"] + experiment.available_versions]
    form.file_type.choices = [("csv", "csv")]

    if form.validate_on_submit():
        if "all versions" in form.version.data:
            results = alfred_web_db.count_documents({"exp_uuid": experiment.id})
            if results == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author,
                                        experiment_title=experiment.title))

            cur = alfred_web_db.find({"exp_uuid": experiment.id})
        else:
            for version in form.version.data:
                results = []
                results.append(alfred_web_db.count_documents({"exp_uuid": experiment.id,
                                                              "exp_version": version}))
            if max(results) == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author,
                                        experiment_title=experiment.title))

            cur = alfred_web_db.find({"exp_uuid": experiment.id,
                                      "exp_version": {"$in": form.version.data}})



        # if "all versions" in form.version.data:
        #     results = alfred_web_db.count_documents({"exp_author_mail": current_user.email,
        #                                              "exp_name": experiment_title})
        #     if results == 0:
        #         flash("No data found for this experiment.", "warning")
        #         return redirect(url_for('web_experiments.web_export', username=experiment.author,
        #                                 experiment_title=experiment.title))

        #     cur = alfred_web_db.find({"exp_author_mail": current_user.email, "exp_name": experiment_title})
        # else:
        #     for version in form.version.data:
        #         results = []
        #         results.append(alfred_web_db.count_documents({"exp_author_mail": current_user.email,
        #                                                       "exp_name": experiment_title,
        #                                                       "exp_version": version}))
        #     if max(results) == 0:
        #         flash("No data found for this experiment.", "warning")
        #         return redirect(url_for('web_experiments.web_export', username=experiment.author,
        #                                 experiment_title=experiment.title))

        #     cur = alfred_web_db.find({"exp_author_mail": current_user.email,
        #                               "exp_name": experiment_title,
        #                               "exp_version": {"$in": form.version.data}})

        none_value = None

        # if form.replace_none.data:
        if form.none_value.data:
            none_value = form.none_value.data
        if form.replace_none_with_empty_string.data:
            none_value = ""

        if form.file_type.data == 'json':
            f = export.to_json(cur)
            bytes_f = export.make_str_bytes(f)
            return send_file(bytes_f, mimetype='application/json',
                             as_attachment=True, attachment_filename='export.json', cache_timeout=1)
        elif form.file_type.data == 'csv':
            f = export.to_csv(cur, none_value=none_value)
            bytes_f = export.make_str_bytes(f)

            return send_file(bytes_f, mimetype='text/csv',
                             as_attachment=True, attachment_filename='export_%s_web.csv' % experiment.title,
                             cache_timeout=1)
        elif form.file_type.data == 'excel_csv':
            f = export.to_excel_csv(cur, none_value=none_value)
            bytes_f = export.make_str_bytes(f)
            return send_file(bytes_f, mimetype='text/csv',
                             as_attachment=True, attachment_filename='export.csv', cache_timeout=1)
        elif form.file_type.data == 'excel':
            f = export.to_excel(cur, none_value=none_value)
            bytes_f = export.make_str_bytes(f)
            return send_file(bytes_f, mimetype='application/excel',
                             cache_timeout=1, as_attachment=True,
                             attachment_filename='export.xlsx')

    return render_template("web_export.html", form=form, experiment=experiment, legend="Export data", type="web")


@web_experiments.route("/de_activate/<username>/<path:experiment_title>", methods=["POST"])
@login_required
def de_activate_experiment(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if not experiment.active:
        if not experiment.script:
            flash("You need to upload a script.py before you can activate your experiment.", "warning")
            return redirect(url_for('web_experiments.experiment', username=current_user.username,
                                    experiment_title=experiment.title))
        experiment.active = True
        experiment.save()
        flash("Experiment activated.", "success")
    elif experiment.active:
        experiment.active = False
        experiment.save()
        flash("Experiment deactivated.", "info")

    return redirect(url_for('web_experiments.experiment', username=current_user.username,
                            exp_title=experiment.title))
