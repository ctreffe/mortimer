# -*- coding: utf-8 -*-
import collections
import os
import re
import shutil
import sys
import logging
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from alfred3 import alfredlog

from mortimer import export
from mortimer.forms import (
    ExperimentConfigurationForm,  # Deprecated
    ExperimentConfigForm,
    ExperimentExportForm,
    ExperimentScriptForm,
    FilterLogForm,
    NewScriptForm,
    WebExperimentForm,
)
from mortimer.models import User, WebExperiment
from mortimer.utils import (
    ScriptFile,
    ScriptString,
    _DictObj,
    display_directory,
    get_user_collection,
    create_fernet,
)

web_experiments = Blueprint("web_experiments", __name__)


@web_experiments.route("/experiment/new", methods=["GET", "POST"])
@login_required
def new_experiment():

    form = WebExperimentForm()

    if form.validate_on_submit():

        exp = WebExperiment(
            title=form.title.data,
            author=current_user.username,
            author_id=current_user.id,
            version=form.version.data,
            description=form.description.data,
        )

        exp.available_versions.append(form.version.data)
        exp.directory_name = str(uuid4())
        exp.path = os.path.join(current_app.instance_path, "exp", exp.directory_name)

        # create experiment directory
        try:
            os.makedirs(exp.path)
        except OSError:
            flash(
                "Action aborted: The experiment directory already exists on the file system.",
                "danger",
            )
            return redirect(url_for("web_experiments.new_experiment"))

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

        exp.save()  # IMPORTANT! Needed to create an exp ID
        exp.set_settings()
        # save the exp to the data base
        exp.save()

        # append an entry for the current experiment to the current user
        current_user.experiments.append(exp.id)  # pylint: disable=no-member
        current_user.save()

        flash("Your Experiment has been created.", "success")

        return redirect(
            url_for("web_experiments.user_experiments", username=current_user.username)
        )

    return render_template(
        "create_experiment.html", title="New Experiment", form=form, legend="New Experiment",
    )


@web_experiments.route("/<username>/<path:exp_title>", methods=["POST", "GET"])
@login_required
def experiment(username, exp_title):

    exp = WebExperiment.objects.get_or_404(  # pylint: disable=no-member
        title=exp_title, author=username
    )
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

    # Query Database
    db = get_user_collection()

    f_id = {"exp_id": str(exp.id)}
    f_fin = {"exp_finished": True}
    f_ver = {"exp_version": exp.version}

    # Used versions
    alfred_versions = db.distinct("alfred_version", {**f_id, **f_fin})
    alfred_versions.sort()

    # Number of datasets
    n = {}
    n["total"] = db.count_documents(f_id)
    n["fin"] = db.count_documents({**f_id, **f_fin})
    n["unfin"] = n["total"] - n["fin"]
    n["current_ver"] = db.count_documents({**f_id, **f_ver})
    n["fin_current_ver"] = db.count_documents({**f_fin, **f_id, **f_ver})
    n["unfin_current_ver"] = n["current_ver"] - n["fin_current_ver"]
    n["individual_versions"] = {}

    # Number of datasets per version
    for v in exp.available_versions:
        f_ver = {"exp_version": v, **f_id}
        entry = {"total": db.count_documents(f_ver), "fin": db.count_documents({**f_fin, **f_ver})}
        n["individual_versions"][v] = entry

    # start time
    group = {"_id": 1, "first": {"$min": "$start_time"}, "last": {"$max": "$start_time"}}
    pipe = [{"$match": f_id}, {"$group": group}]
    times = list(db.aggregate(pipe))

    activity = {}
    if times:
        activity["first"] = datetime.fromtimestamp(times[0]["first"])
        activity["last"] = datetime.fromtimestamp(times[0]["last"])
    else:
        activity["first"] = "none"
        activity["last"] = "none"

    # Form for script.py upload
    form = NewScriptForm()

    if not exp.settings:
        exp.set_settings()
        exp.save()

    if form.validate_on_submit() and form.script.data:

        # process script.py
        if form.script.data:
            script = ScriptFile(exp, form.script.data)
            script.load()
            script.parse()
            script.save()

        # update version
        if exp.version != form.version.data:
            exp.version = form.version.data
            exp.settings["experiment"]["version"] = form.version.data
            exp.available_versions.append(exp.version)

        # save experiment
        exp.save()

        # redirect to experiment page
        flash("New script.py was uploaded successfully", "success")
        return redirect(
            url_for("web_experiments.experiment", username=exp.author, exp_title=exp.title)
        )

    elif form.validate_on_submit():
        flash("No script.py was provided, so nothing happened.", "info")
        return redirect(
            url_for("web_experiments.experiment", username=exp.author, exp_title=exp.title)
        )

    # pre-populate form
    form.version.data = exp.version

    return render_template(
        "experiment.html",
        experiment=exp,
        alfred_versions=alfred_versions,
        expid=str(exp.id),
        form=form,
        status=status,
        toggle_button=toggle_button,
        n=n,
        activity=activity,
        password_protection=password_protection,
    )


@web_experiments.route("/<username>/<path:exp_title>/script", methods=["GET", "POST"])
@login_required
def experiment_script(username, exp_title):

    exp = WebExperiment.objects.get_or_404(  # pylint: disable=no-member
        title=exp_title, author=username
    )

    if exp.author != current_user.username:
        abort(403)

    form = ExperimentScriptForm()

    if form.validate_on_submit():

        # update script
        script = ScriptString(exp, form.script.data)
        script.parse()
        script.save()

        # update version
        if exp.version != form.version.data:
            exp.version = form.version.data
            exp.settings["experiment"]["version"] = form.version.data
            exp.available_versions.append(exp.version)

        # save simple updates
        exp.last_update = datetime.now

        # save experiment
        exp.save()

        # return to experiment page
        flash("Your experiment has been updated", "success")
        return redirect(
            url_for("web_experiments.experiment", exp_title=exp.title, username=exp.author)
        )

    # pre-populate form
    form.script.data = exp.script
    form.version.data = exp.version

    return render_template(
        "experiment_script.html",
        title="Experiment Script",
        experiment=exp,
        form=form,
        legend="Experiment Script",
    )


@web_experiments.route(
    "/<username>/<path:experiment_title>/delete", methods=["POST", "GET"]
)  # only allow POST request
@login_required
def delete_experiment(username, experiment_title):

    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)
    try:
        shutil.rmtree(experiment.path)
    except FileNotFoundError:
        flash("Experiment directory didn't exist on file system.", "warning")

    experiment.delete()
    flash("Experiment deleted.", "info")

    return redirect(url_for("web_experiments.user_experiments", username=current_user.username))


@web_experiments.route(
    "/<username>/<path:experiment_title>/upload_resources/<path:relative_path>",
    methods=["POST", "GET"],
)
@login_required
def upload_resources(username, experiment_title, relative_path):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    path = os.path.join(experiment.path, relative_path)

    path_list = []

    tail, head = os.path.split(relative_path)

    while head != "":
        path_list.insert(0, head)
        tail, head = os.path.split(tail)

    if request.method == "POST":

        for key, f in request.files.items():

            old_filenames = []
            new_filenames = []

            if key.startswith("file"):
                # exemption from sanitization for __init__.py to allow submodules
                if f.filename == "__init__.py":
                    file_fn = f.filename
                else:
                    file_fn = secure_filename(f.filename)
                f.save(os.path.join(path, file_fn))

                old_filenames.append(f.filename)
                new_filenames.append(file_fn)

        # TODO: Display old and new filenames
        if old_filenames != new_filenames:
            for i in range(len(old_filenames)):
                flash(
                    "Filename changed from <code>%s</code> to <code>%s</code>."
                    % (old_filenames[i], new_filenames[i]),
                    "danger",
                )

    return render_template(
        "upload_resources.html",
        experiment=experiment,
        legend="Upload Resources",
        relative_path=relative_path,
        path_list=path_list,
    )


@web_experiments.route(
    "/<username>/<path:experiment_title>/manage_resources", methods=["POST", "GET"]
)
@login_required
def manage_resources(username, experiment_title):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    # if the experiment path does not exist on the file system, we get a warning
    # this is valuable feedback during development
    if not os.path.exists(experiment.path):
        flash(
            "Experiment path doesn't exist. You probably created the experiment while running mortimer on a \
        different server.",
            "warning",
        )
        return redirect(
            url_for(
                "web_experiments.experiment",
                exp_title=experiment.title,
                username=experiment.author,
            )
        )

    display = display_directory(
        sorted(experiment.user_directories),
        parent_directory=experiment.path,
        experiment=experiment,
    )

    return render_template(
        "manage_resources.html", legend="Manage Resources", experiment=experiment, display=display,
    )


@web_experiments.route("/experiments")
def experiments():

    if current_user.is_authenticated:
        return redirect(
            url_for("web_experiments.user_experiments", username=current_user.username)
        )
    else:
        flash("Please log in to access this page.", "info")
        return redirect(url_for("users.login"))


@web_experiments.route("/<string:username>/experiments")
@login_required
def user_experiments(username):

    user = User.objects.get_or_404(username=username)  # pylint: disable=no-member

    if user.username != current_user.username:
        abort(403)

    # pylint: disable=no-member
    experiments = WebExperiment.objects(author_id=user.id).order_by("-last_update")

    return render_template(
        "user_experiments.html",
        experiments=experiments,
        user=user,
        secure_filename=secure_filename,
    )


@web_experiments.route(
    "/<username>/<path:experiment_title>/delete_all_files", methods=["POST"]
)  # only allow POST requests
@login_required
def delete_all_files(username, experiment_title):

    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)
    if experiment.author != current_user.username:
        abort(403)

    for dir in experiment.user_directories:
        path = os.path.join(experiment.path, dir)
        shutil.rmtree(path)  # remove directory

    experiment.user_directories = []  # empty the file list in the experiment document in mongoDB
    experiment.save()

    flash("All files and directories deleted.", "info")

    return redirect(
        url_for(
            "web_experiments.manage_resources",
            experiment_title=experiment.title,
            username=experiment.author,
        )
    )


@web_experiments.route(
    "/<username>/<path:experiment_title>/new_directory",
    methods=["POST"],
    defaults={"relative_path": None},
)
@web_experiments.route(
    "/<username>/<path:experiment_title>/new_directory/<path:relative_path>", methods=["POST"],
)
@login_required
def new_directory(username: str, experiment_title: str, relative_path: str = None):
    """Create a new directory inside the experiment directory.

    :param str experiment_title: Title of the experiment
    :param str path: Name of the path in which the new path shall be created
    """
    name = request.form["new_directory"]

    # pylint: disable=no-member
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
            return redirect(
                url_for(
                    "web_experiments.manage_resources",
                    experiment_title=experiment.title,
                    username=experiment.author,
                )
            )
    else:
        try:
            os.mkdir(os.path.join(experiment.path, relative_path, name))
        except FileExistsError:
            flash("A directory with this name already exsists.", "warning")
            return redirect(
                url_for(
                    "web_experiments.manage_resources",
                    experiment_title=experiment.title,
                    username=experiment.author,
                )
            )

    flash("New directory created.", "success")

    return redirect(
        url_for(
            "web_experiments.manage_resources",
            experiment_title=experiment.title,
            username=experiment.author,
        )
    )


@web_experiments.route(
    "/<username>/<path:experiment_title>/<path:relative_path>/delete_directory", methods=["POST"],
)
@login_required
def delete_directory(username, experiment_title, relative_path):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    path = os.path.join(experiment.path, relative_path)
    shutil.rmtree(path)

    if os.path.abspath(os.path.join(path, os.pardir)) == experiment.path:
        experiment.user_directories.remove(os.path.basename(path))
        experiment.save()

    flash("Directory deleted", "info")
    return redirect(
        url_for(
            "web_experiments.manage_resources",
            experiment_title=experiment.title,
            username=experiment.author,
        )
    )


@web_experiments.route(
    "/<username>/<path:experiment_title>/<path:relative_path>/delete_file", methods=["POST"],
)
@login_required
def delete_file(username, experiment_title, relative_path):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    os.remove(os.path.join(experiment.path, relative_path))

    flash("File deleted.", "info")
    return redirect(
        url_for(
            "web_experiments.manage_resources",
            experiment_title=experiment.title,
            username=experiment.author,
        )
    )


@web_experiments.route("/<username>/<path:experiment_title>/web_export", methods=["POST", "GET"])
@login_required
def web_export(username, experiment_title):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if not experiment.script:
        flash(
            "You have not uploaded a script.py yet. Please upload a script.py and try again.",
            "warning",
        )
        return redirect(
            url_for(
                "web_experiments.experiment",
                username=current_user.username,
                exp_title=experiment.title,
            )
        )

    form = ExperimentExportForm()
    form.version.choices = [
        (version, version) for version in ["all versions"] + experiment.available_versions
    ]
    form.file_type.choices = [("csv", "csv"), ("excel_csv", "excel_csv"), ("json", "json")]

    if form.validate_on_submit():
        db = get_user_collection()
        if "all versions" in form.version.data:
            results = db.count_documents({"exp_id": str(experiment.id)})
            if results == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(
                    url_for(
                        "web_experiments.web_export",
                        username=experiment.author,
                        experiment_title=experiment.title,
                    )
                )

            cur = db.find({"exp_id": str(experiment.id)})
        else:
            for version in form.version.data:
                results = []
                results.append(
                    db.count_documents({"exp_id": str(experiment.id), "exp_version": version})
                )
            if max(results) == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(
                    url_for(
                        "web_experiments.web_export",
                        username=experiment.author,
                        experiment_title=experiment.title,
                    )
                )

            cur = db.find(
                {"exp_id": str(experiment.id), "exp_version": {"$in": form.version.data},}
            )

        none_value = None

        # if form.replace_none.data:
        if form.none_value.data:
            none_value = form.none_value.data
        if form.replace_none_with_empty_string.data:
            none_value = ""

        if form.file_type.data == "json":
            f = export.to_json(cur)
            bytes_f = export.make_str_bytes(f)
            return send_file(
                bytes_f,
                mimetype="application/json",
                as_attachment=True,
                attachment_filename="export.json",
                cache_timeout=1,
            )
        elif form.file_type.data == "csv":
            f = export.to_csv(cur, none_value=none_value)
            bytes_f = export.make_str_bytes(f)

            return send_file(
                bytes_f,
                mimetype="text/csv",
                as_attachment=True,
                attachment_filename="export_%s_web.csv" % experiment.title,
                cache_timeout=1,
            )
        elif form.file_type.data == "excel_csv":
            f = export.to_excel_csv(cur, none_value=none_value)
            bytes_f = export.make_str_bytes(f)
            return send_file(
                bytes_f,
                mimetype="text/csv",
                as_attachment=True,
                attachment_filename="export.csv",
                cache_timeout=1,
            )
        # elif form.file_type.data == "excel":
        #     f = export.to_excel(cur, none_value=none_value)
        #     bytes_f = export.make_str_bytes(f)
        #     return send_file(
        #         bytes_f,
        #         mimetype="application/excel",
        #         cache_timeout=1,
        #         as_attachment=True,
        #         attachment_filename="export.xlsx",
        #     )

    return render_template(
        "web_export.html", form=form, experiment=experiment, legend="Export data", type="web",
    )


@web_experiments.route("/<username>/<path:experiment_title>/data", methods=["GET"])
@login_required
def data(username, experiment_title):
    experiment = WebExperiment.objects.get_or_404(  # pylint: disable=no-member
        title=experiment_title, author=username
    )
    if experiment.author != current_user.username:
        abort(403)

    db = get_user_collection()

    results = db.count_documents({"exp_id": str(experiment.id)})
    if results == 0:
        flash("No data found for this experiment.", "warning")
        return redirect(
            url_for(
                "web_experiments.data",
                username=experiment.author,
                experiment_title=experiment.title,
            )
        )

    cur = db.find({"exp_id": str(experiment.id)})
    data_list = export.cursor_to_rows(cursor=cur)

    # hotfix for performance-issues: show only the first fifty entries.
    # TODO: Implement AJAX for DataTables display
    cols = 30
    rows = 50
    shorter_data_list = [x[:cols] for x in data_list[:rows]]
    flash(
        (
            f"For performance reasons, we currently only show the first {rows} "
            f"observations of the first {cols} variables."
        ),
        "info",
    )

    return render_template(
        "data.html", experiment=experiment, author=username, data_list=shorter_data_list
    )


@web_experiments.route("/de_activate/<username>/<path:experiment_title>", methods=["POST"])
@login_required
def de_activate_experiment(username, experiment_title):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    if not experiment.active:
        if not experiment.script:
            flash(
                "You need to upload a script.py before you can activate your experiment.",
                "warning",
            )
            return redirect(
                url_for(
                    "web_experiments.experiment",
                    username=current_user.username,
                    exp_title=experiment.title,
                )
            )

        experiment.active = True
        experiment.save()
        flash("Experiment activated.", "success")
    elif experiment.active:
        experiment.active = False
        experiment.save()
        flash("Experiment deactivated.", "info")

    return redirect(request.referrer)


@web_experiments.route("/<username>/<path:experiment_title>/config", methods=["POST", "GET"])
@login_required
def experiment_config(username, experiment_title):
    # pylint: disable=no-member
    exp = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if exp.author != current_user.username:
        abort(403)

    form = ExperimentConfigForm()
    f = create_fernet()

    if form.validate_on_submit():
        exp.title = form.title.data
        exp.description = form.description.data
        if form.password.data:
            exp.public = False
        else:
            exp.public = True
        exp.password = form.password.data

        exp.exp_config = form.exp_config.data
        exp.exp_secrets = f.encrypt(form.exp_secrets.data.encode())

        exp.last_update = datetime.utcnow
        exp.save()

        flash("Experiment configuration updated", "success")

        return redirect(
            url_for(
                "web_experiments.experiment_config", username=username, experiment_title=exp.title
            )
        )

    form.title.data = exp.title
    form.description.data = exp.description
    form.password.data = exp.password
    form.exp_config.data = exp.exp_config
    try:
        form.exp_secrets.data = f.decrypt(exp.exp_secrets).decode()
    except TypeError:
        form.exp_secrets.data = ""
        import traceback

    return render_template("experiment_config.html", form=form, experiment=exp)


@web_experiments.route(
    "/<username>/<path:experiment_title>/log/",
    methods=["GET", "POST"],
    defaults={"end": 199, "start": "default"},
)
@web_experiments.route(
    "/<username>/<path:experiment_title>/log/<start>/<end>", methods=["GET", "POST"]
)
@login_required
def experiment_log(username, experiment_title, end, start):
    # pylint: disable=no-member
    exp = WebExperiment.objects.get_or_404(title=experiment_title, author=username)

    if exp.author != current_user.username:
        abort(403)

    form = FilterLogForm()

    logfile = Path(exp.path) / "exp.log"
    # parse with start and end values (crude pagination)
    date_pattern = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2} )")
    with open(logfile, "r", encoding="utf-8") as f:
        log = []
        traceback_lines = 0
        i = 0
        for i, line in enumerate(reversed(f.readlines()), start=1):

            # for newest first sorting
            if start == "default":
                start_check = 1
            else:
                start_check = start

            if end == "-99":
                log.append(line)
                continue
            elif not int(start_check) <= (i + traceback_lines) <= int(end):
                continue

            if not date_pattern.match(line):
                traceback_lines += 1
                log.append(line)
            else:
                log.append(line)
        n_entries = i - traceback_lines

    # parse options for choice selection fields
    # we need this format: [(<choice1_id>, "choice1_description"), ...]
    n_entries_to_display = 300
    choices = []
    choice_numbers = [[1, n_entries_to_display - 1]]
    items = n_entries // n_entries_to_display

    for i in range(items):
        _, this_end = choice_numbers[i]
        next_start = this_end + 1
        next_end = next_start + n_entries_to_display - 1

        choice_numbers.append([next_start, next_end])  # entry: (0, 199)

    for i, c in enumerate(choice_numbers):
        choice_string = f"{c[0]} - {c[1]}"  # "0 - 199"
        choices.append((str(i), choice_string))

    choices += [("newest", f"newest {n_entries_to_display}"), ("all", "all")]

    form.display_range.choices = choices

    if form.validate_on_submit():
        logfilter = {
            "debug": form.debug.data,
            "info": form.info.data,
            "warning": form.warning.data,
            "error": form.error.data,
            "critical": form.critical.data,
        }
        current_user.settings["logfilter"] = logfilter

        if form.display_range.data == "all":
            choice_start = "0"
            choice_end = "-99"
        elif form.display_range.data == "newest":
            choice_start = "default"
            choice_end = 199
        else:
            choice_start = choice_numbers[int(form.display_range.data)][0]
            choice_end = choice_numbers[int(form.display_range.data)][1]

        current_user.save()

        # flash(f"{form.display_range.choices}", "danger")

        return redirect(
            url_for(
                "web_experiments.experiment_log",
                experiment_title=exp.title,
                username=exp.author,
                start=choice_start,
                end=choice_end,
            )
        )

        # return redirect
    p = re.compile(
        r"(?P<date>20.+?) - (?P<module>.+?) - (?P<log_level>.+?) - ((experiment id=)(?P<exp_id>.+?) - )?(session id=(?P<session_id>.+?) - )?(?P<message>(.|\s)*?(?=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\Z)))"
    )

    log_entries = collections.deque()
    flash_type = {
        "DEBUG": "secondary",
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "danger",
        "CRITICAL": "danger",
    }

    pattern_ip = re.compile(r"(host=\[(?P<ip>.+?)\])")
    pattern_path = re.compile(r"(File \"(?P<path>.+))(?=/.+.py)")

    for match in p.finditer(" ".join(reversed(log))):
        # print(match.group("message"))
        date = match.group("date")
        module = match.group("module")
        log_level = match.group("log_level")
        if not current_user.settings.get("logfilter", {}).get(log_level.lower(), True):
            continue
        exp_id = match.group("exp_id")
        session_id = match.group("session_id")
        message = match.group("message").replace("<", "&lt;").replace(">", "&gt;").rstrip()

        message = pattern_ip.sub("host=[--removed--]", message)
        message = pattern_path.sub('File "...', message)

        entry_info = (
            f'<span class="badge badge-light">{date}</span>'
            f' - <span class="badge badge-{flash_type[log_level]}">{log_level}</span>'
            f" - <b>exp id</b> = {exp_id} - <b>session id</b> = {session_id}"
            f' - <span class="badge badge-secondary">{module}</span>'
        )

        flash_entry = (
            f'<div class="alert alert-{flash_type[log_level]}">'
            f"{entry_info}<hr><pre>{message}</pre></div>"
        )
        log_entries.appendleft(flash_entry)

    # fill rest of form
    form.debug.data = current_user.settings.get("logfilter", {}).get("debug", True)
    form.info.data = current_user.settings.get("logfilter", {}).get("info", True)
    form.warning.data = current_user.settings.get("logfilter", {}).get("warning", True)
    form.error.data = current_user.settings.get("logfilter", {}).get("error", True)
    form.critical.data = current_user.settings.get("logfilter", {}).get("critical", True)

    return render_template(
        "experiment_log.html",
        experiment=exp,
        username=exp.author,
        log=log_entries,
        form=form,
        range=(start, end, n_entries_to_display),
    )

