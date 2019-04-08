import os
import shutil
from mortimer import export
from flask import Blueprint, render_template, url_for, flash, redirect, request, abort, current_app, send_file
from mortimer.forms import WebExperimentForm, UpdateExperimentForm, NewScriptForm, ExperimentExportForm
from mortimer.models import User, WebExperiment
from mortimer.utils import display_directory, filter_directories, extract_version, extract_title, extract_author_mail
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

        experiment = WebExperiment(title=form.title.data, author=current_user.username,
                                   description=form.description.data)

        experiment.directory_name = str(uuid4())
        experiment.path = os.path.join(current_app.root_path,
                                       "experiments", experiment.directory_name)

        # double-check for unique experiments with users
        user_experiments_titles = []
        for id in current_user.experiments:
            if WebExperiment.objects(id=id):
                user_experiments_titles.append(WebExperiment.objects.get(id=id).title)

        if experiment.title in user_experiments_titles:
            flash("Action aborted: An experiment with this title is already associated with your account. The data was not saved.", "danger")
            redirect(url_for('web_experiments.new_experiment'))

        # create experiment directory
        try:
            os.makedirs(experiment.path)
        except OSError:
            flash("Action aborted: The experiment directory already exists on the file system.", "danger")
            return redirect(url_for('web_experiments.new_experiment'))

        if form.script.data:
            script_file = form.script.data
            script_name = str(uuid4()) + ".py"
            path = os.path.join(experiment.path, script_name)
            script_file.save(path)
            experiment.script_name = script_name
            experiment.script_fullpath = path
            experiment.title_from_script = extract_title(experiment.script_fullpath)
            experiment.author_mail_from_script = extract_author_mail(experiment.script_fullpath)

            with open(experiment.script_fullpath, "r") as f:
                experiment.script = f.read()

            try:
                experiment.version = extract_version(experiment.script_fullpath)
                experiment.available_versions.append(experiment.version)
                title = extract_title(experiment.script_fullpath)
                if title != experiment.title:
                    flash(f"The experiment name in the script ({title}) and in mortimer ({experiment.title}) should be the same. Otherwise you will not be able to download your data. You can change the experiment title in mortimer and the script when you click on Edit.", "warning")
                author_mail = extract_author_mail(experiment.script_fullpath)
                if not author_mail:
                    flash("You need to add a field 'exp_author_mail' to your script.py next to exp_name and exp_version. Make sure to also reference this variable in the generate_experiment() method of your Script class.", "warning")
                if author_mail != current_user.email:
                    flash("The exp_author_mail in your script.py needs to be the same email adress that you used to register in mortimer. Otherwise you will not be able to export your data", "danger")
                experiment.save()
                return redirect(url_for('web_experiments.experiment', experiment_title=experiment.title, username=current_user.username))
            except Exception as e:
                flash(f"Error: {e}", "danger")
                return redirect(url_for('web_experiments.new_experiment'))

        if form.password.data:
            experiment.public = False
            experiment.password = form.password.data
        else:
            experiment.public = True

        # saves the experiment to the data base
        experiment.save()

        # appends an entry for the current experiment to the current user
        current_user.experiments.append(experiment.id)
        current_user.save()

        flash("Your Experiment has been created.", "success")

        return redirect(url_for('web_experiments.user_experiments', username=current_user.username))

    return render_template("create_experiment.html", title="New Experiment", form=form,
                           legend="New Experiment")


@web_experiments.route("/<username>/<path:experiment_title>", methods=["POST", "GET"])
@login_required
def experiment(username, experiment_title):

    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if experiment.active:
        status = "active"
        toggle_button = "Deactivate"
    else:
        status = "inactive"
        toggle_button = "Activate"

    if experiment.script_fullpath:
        script_title = experiment.title_from_script
        if experiment.title != script_title:
            title_unequal = True
        else:
            title_unequal = False
    else:
        script_title = ""
        title_unequal = False

    if experiment.public:
        password_protection = "disabled"
    else:
        password_protection = "enabled"

    if experiment.script_name:
        author_mail = experiment.author_mail_from_script
    else:
        author_mail = "(no script.py)"

    datasets = {}

    datasets["all_datasets"] = alfred_web_db\
        .count_documents({"exp_author_mail": current_user.email,
                          "exp_name": experiment_title})

    datasets["all_finished_datasets"] = alfred_web_db\
        .count_documents({"exp_author_mail": current_user.email,
                          "exp_name": experiment_title,
                          "expFinished": True})

    datasets["all_unfinished_datasets"] = datasets["all_datasets"] - datasets["all_finished_datasets"]

    datasets["datasets_current_version"] = alfred_web_db\
        .count_documents({"exp_author_mail": current_user.email,
                          "exp_name": experiment_title,
                          "exp_version": experiment.version})

    datasets["finished_datasets_current_version"] = alfred_web_db\
        .count_documents({"exp_author_mail": current_user.email,
                          "exp_name": experiment_title,
                          "expVersion": experiment.version,
                          "expFinished": True})

    datasets["unfinished_datasets_current_version"] = datasets["datasets_current_version"] - datasets["finished_datasets_current_version"]

    versions = {}
    finished = []
    cur = alfred_web_db.find({"expAuthorMail": current_user.email, "expName": experiment_title})
    for exp in cur:
        if exp["expVersion"] not in versions.keys():
            versions[exp["expVersion"]] = {"total": 1, "finished": 0, "unfinished": 0}
        else:
            versions[exp["expVersion"]]["total"] += 1
        if exp["expFinished"]:
            versions[exp["expVersion"]]["finished"] += 1
        else:
            versions[exp["expVersion"]]["unfinished"] += 1
        finished.append(exp["start_time"])

    if finished:
        first_activity = datetime.fromtimestamp(min(finished))\
            .strftime('%Y-%m-%d, %H:%M')
        last_activity = datetime.fromtimestamp(max(finished))\
            .strftime('%Y-%m-%d, %H:%M')
    else:
        first_activity = "none"
        last_activity = "none"

    form = NewScriptForm()

    if form.validate_on_submit() and form.script.data:
        if experiment.script_name:
            os.rename(experiment.script_fullpath, os.path.join(experiment.path, "old_script"))
        else:
            experiment.script_name = str(uuid4()) + ".py"
            experiment.script_fullpath = os.path.join(experiment.path, experiment.script_name)
        script_file = form.script.data

        script_file.save(experiment.script_fullpath)
        experiment.last_update = datetime.utcnow

        with open(experiment.script_fullpath, "r") as f:
            experiment.script = f.read()

        try:
            os.remove(os.path.join(experiment.path, "old_script"))
        except FileNotFoundError:
            pass

        try:
            old_version = experiment.version
            experiment.version = extract_version(experiment.script_fullpath)

            if experiment.version not in experiment.available_versions:
                experiment.available_versions.append(experiment.version)

            experiment.title_from_script = extract_title(experiment.script_fullpath)
            experiment.author_mail_from_script = extract_author_mail(experiment.script_fullpath)

            experiment.save()

            flash("New script.py was uploaded successfully", "success")

            if old_version != experiment.version:
                flash(f"Version number changed from {old_version} to {experiment.version}.", "info")
            else:
                flash("Version number did not change. If that was intended, no need to worry. If you made changes that affect the data structure (e.g. adding a new page), you might want to change the version number.", "danger")

            if experiment.title_from_script != experiment_title:
                flash(f"The experiment name in the script ({experiment.title_from_script}) and in mortimer ({experiment.title}) should be the same. Otherwise you will not be able to download your data. You can change the experiment title in mortimer at any time.", "warning")

            if not experiment.author_mail_from_script:
                flash("You need to add a field 'exp_author_mail' to your script.py next to expName and expVersion. Make sure to also reference this variable in the generate_experiment() method of your Script class.", "warning")
            if experiment.author_mail_from_script != current_user.email:
                flash("The exp_author_mail in your script.py needs to be the same email adress that you used to register in mortimer. Otherwise you will not be able to export your data", "danger")

            return redirect(url_for('web_experiments.experiment', username=experiment.author, experiment_title=experiment.title))
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for('web_experiments.experiment', username=experiment.author, experiment_title=experiment.title))

    return render_template("experiment.html",
                           experiment=experiment, expid=str(experiment.id), form=form, status=status, toggle_button=toggle_button,
                           datasets=datasets, title_unequal=title_unequal, script_title=script_title,
                           first_activity=first_activity, last_activity=last_activity, versions=versions,
                           password_protection=password_protection, author_mail=author_mail)


@web_experiments.route("/<username>/<path:experiment_title>/update", methods=["GET", "POST"])
@login_required
def update_experiment(username, experiment_title):

    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    form = UpdateExperimentForm()

    if form.validate_on_submit():

        if form.title.data:

            if form.title.data != experiment.title:
                if WebExperiment.objects(title=form.title.data, author=username):
                    flash("You already have a web experiment with this title. Please choose a unique title. The changes were not saved.", "danger")
                    return redirect(url_for('web_experiments.experiment', experiment_title=experiment.title, username=experiment.author))
                else:
                    experiment.title = form.title.data
        experiment.description = form.description.data
        if form.password.data:
            experiment.public = False
            experiment.password = form.password.data
        else:
            experiment.public = True

        if experiment.script_name and (form.script.data != experiment.script):
            experiment.script = form.script.data
            with open(experiment.script_fullpath, "w") as f:
                f.write(form.script.data)
            experiment.title_from_script = extract_title(experiment.script_fullpath)
            experiment.author_mail_from_script = extract_author_mail(experiment.script_fullpath)
            if experiment.version == extract_version(experiment.script_fullpath):
                flash("You changed the script.py, but did not change the version number. If that was intended, no need to worry. If you made changes that affect the data structure (e.g. adding a new page), you might want to change the version number.", "danger")

        # experiment.versions.append(ExperimentVersion(version=form.version.data))
        # experiment.script = form.script.data
        experiment.save()
        flash("Your experiment has been updated", "success")

        return redirect(url_for('web_experiments.experiment', experiment_title=experiment.title, username=experiment.author))

    form.title.data = experiment.title
    form.description.data = experiment.description
    form.password.data = experiment.password
    form.script.data = experiment.script

    return render_template("update_experiment.html", title="Update Experiment",
                           experiment=experiment, form=form, legend="Update Experiment")


@web_experiments.route("/<username>/<path:experiment_title>/delete", methods=["POST", "GET"])  # only allow POST requests
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


@web_experiments.route("/<username>/<path:experiment_title>/upload_resources/<path:relative_path>", methods=["POST", "GET"])
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
                flash(f"Filename changed from <code>{old_filenames[i]}</code> to <code>{new_filenames[i]}</code>.", "danger")

    return render_template("upload_resources.html", experiment=experiment, legend="Upload Resources", relative_path=relative_path)


@web_experiments.route("/<username>/<path:experiment_title>/manage_resources", methods=["POST", "GET"])
@login_required
def manage_resources(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    # if the experiment path does not exist on the file system, we get a warning
    # this is valuable feedback during development
    if not os.path.exists(experiment.path):
        flash("Experiment path doesn't exist. You probably created the experiment while running mortimer on a different server.", "warning")
        return redirect(url_for("web_experiments.experiment", experiment_title=experiment.title, username=experiment.author))

    files = filter_directories(experiment=experiment)
    display = display_directory(files, parent_directory=experiment.path, experiment=experiment)

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


@web_experiments.route("/<username>/<path:experiment_title>/delete_all_files", methods=["POST"])  # only allow POST requests
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

    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title, username=experiment.author))


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
            return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title, username=experiment.author))
    else:
        try:
            os.mkdir(os.path.join(experiment.path, relative_path, name))
        except FileExistsError:
            flash("A directory with this name already exsists.", "warning")
            return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title, username=experiment.author))

    flash("New directory created.", "success")

    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title, username=experiment.author))


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
    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title, username=experiment.author))


@web_experiments.route("/<username>/<path:experiment_title>/<path:relative_path>/delete_file", methods=["POST"])
@login_required
def delete_file(username, experiment_title, relative_path):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    os.remove(os.path.join(experiment.path, relative_path))

    flash("File deleted.", "info")
    return redirect(url_for('web_experiments.manage_resources', experiment_title=experiment.title, username=experiment.author))


@web_experiments.route("/<username>/<path:experiment_title>/web_export", methods=["POST", "GET"])
@login_required
def web_export(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    title = extract_title(experiment.script_fullpath)
    if experiment.title != title:
        flash(f"Your experiment has different names in mortimer ({experiment.title}) and in your script.py ({title}). These need to be equal to access the data. You can change the experiment title in mortimer at any time.", "danger")
        return redirect(url_for('web_experiments.experiment', username=current_user.username, experiment_title=experiment.title))

    form = ExperimentExportForm()
    form.version.choices = [(version, version) for version in ["all versions"] + experiment.available_versions]
    form.file_type.choices = [("csv", "csv")]

    if form.validate_on_submit():
        if "all versions" in form.version.data:
            results = alfred_web_db.count_documents({"expAuthorMail": current_user.email, "expName": experiment_title})
            if results == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author, experiment_title=experiment.title))

            cur = alfred_web_db.find({"expAuthorMail": current_user.email, "expName": experiment_title})
        else:
            for version in form.version.data:
                results = []
                results.append(alfred_web_db.count_documents({"expAuthorMail": current_user.email, "expName": experiment_title, "expVersion": version}))
            if max(results) == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author, experiment_title=experiment.title))

            cur = alfred_web_db.find({"expAuthorMail": current_user.email, "expName": experiment_title, "expVersion": {"$in": form.version.data}})

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
                             as_attachment=True, attachment_filename='export.csv', cache_timeout=1)
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

    return render_template("web_export.html", form=form, experiment=experiment, legend="Download data", type="web")


@web_experiments.route("/de_activate/<username>/<path:experiment_title>", methods=["POST"])
@login_required
def de_activate_experiment(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if not experiment.active:
        if not experiment.script_fullpath:
            flash("You need to upload a script.py before you can activate your experiment.", "warning")
            return redirect(url_for('web_experiments.experiment', username=current_user.username, experiment_title=experiment.title))
        if experiment.title != experiment.title_from_script or current_user.email != experiment.author_mail_from_script:
            flash("Your experiment title and the author mail need to be the same in Mortimer and in your script.py", "danger")
            return redirect(url_for('web_experiments.experiment', username=current_user.username, experiment_title=experiment.title))
        experiment.active = True
        experiment.save()
        flash("Experiment activated.", "success")
    elif experiment.active:
        experiment.active = False
        experiment.save()
        flash("Experiment deactivated.", "info")

    return redirect(url_for('web_experiments.experiment', username=current_user.username, experiment_title=experiment.title))
