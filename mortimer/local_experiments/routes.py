from mortimer import export
from flask import Blueprint, render_template, url_for, flash, redirect, abort, send_file, request
from mortimer.forms import ExperimentExportForm, LocalExperimentForm
from mortimer.models import User, LocalExperiment
from mortimer import alfred_local_db
from mortimer.config import Config
from flask_login import current_user, login_required
from datetime import datetime


local_experiments = Blueprint("local_experiments", __name__)


@local_experiments.route("/new_local_experiment", methods=["POST", "GET"])
@login_required
def new_local_experiment():
    form = LocalExperimentForm()

    if form.validate_on_submit():

        experiment = LocalExperiment(title=form.title.data, author=current_user.username,
                                     description=form.description.data)

        experiment.save()
        flash("New local experiment added. You can now download the corresponding data.", "success")
        return redirect(url_for('local_experiments.local_experiment', username=current_user.username, experiment_title=experiment.title))

    return render_template("create_local_experiment.html", form=form, legend="New Local Experiment")


@local_experiments.route("/<username>/local/<experiment_title>", methods=["POST", "GET"])
@login_required
def local_experiment(username, experiment_title):

    experiment = LocalExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    datasets = {}

    datasets["all_datasets"] = alfred_local_db.count_documents({"expAuthorMail": current_user.email, "expName": experiment_title})
    datasets["all_finished_datasets"] = alfred_local_db.count_documents({"expAuthorMail": current_user.email, "expName": experiment_title, "expFinished": True})
    datasets["all_unfinished_datasets"] = datasets["all_datasets"] - datasets["all_finished_datasets"]

    versions = {}
    created = []
    cur = alfred_local_db.find({"expAuthorMail": current_user.email, "expName": experiment_title})
    for exp in cur:
        if exp["expVersion"] not in versions.keys():
            versions[exp["expVersion"]] = {"total": 1, "finished": 0, "unfinished": 0}
        else:
            versions[exp["expVersion"]]["total"] += 1
        if exp["expFinished"]:
            versions[exp["expVersion"]]["finished"] += 1
        else:
            versions[exp["expVersion"]]["unfinished"] += 1
        created.append(exp["start_time"])

    if created:
        first_activity = datetime.fromtimestamp(min(created)).strftime('%Y-%m-%d, %H:%M')
        last_activity = datetime.fromtimestamp(max(created)).strftime('%Y-%m-%d, %H:%M')
    else:
        first_activity = "none"
        last_activity = "none"

    return render_template("local_experiment.html",
                           experiment=experiment, expid=str(experiment.id), datasets=datasets,
                           first_activity=first_activity, last_activity=last_activity,
                           versions=versions)


@local_experiments.route("/experiments")
def experiments():

    if current_user.is_authenticated:
        return redirect(url_for('local_experiments.user_experiments', username=current_user.username))
    else:
        flash("Please log in to access this page.", "info")
        return redirect(url_for("users.login"))


@local_experiments.route("/<string:username>/experiments")
@login_required
def user_experiments(username):

    page = request.args.get("page", 1, type=int)
    user = User.objects.get_or_404(username=username)

    if user.username != current_user.username:
        abort(403)

    experiments = LocalExperiment.objects(author=user.username)\
        .order_by("-date_created")\
        .paginate(page=page, per_page=Config.EXP_PER_PAGE)

    return render_template("user_local_experiments.html", experiments=experiments, user=user)


@local_experiments.route("/<username>/<experiment_title>/local_export", methods=["POST", "GET"])
@login_required
def local_export(username, experiment_title):
    experiment = LocalExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    form = ExperimentExportForm()
    cur = alfred_local_db.find({"expAuthorMail": current_user.email, "expName": experiment.title})

    available_versions = ["all versions"]
    for exp in cur:
        available_versions.append(exp["expVersion"])
    form.version.choices = [(version, version) for version in available_versions]
    form.file_type.choices = [("csv", "csv")]
    # form.version.choices = [(version, version) for version in experiment.available_versions]

    if form.validate_on_submit():
        if "all versions" in form.version.data:
            results = alfred_local_db.count_documents({"expAuthorMail": current_user.email, "expName": experiment_title})
            if results == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author, experiment_title=experiment.title))

            cur = alfred_local_db.find({"expAuthorMail": current_user.email, "expName": experiment_title})
        else:
            for version in form.version.data:
                results = []
            results.append(alfred_local_db.count_documents({"expAuthorMail": current_user.email, "expName": experiment_title, "expVersion": form.version.data}))
            if max(results) == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author, experiment_title=experiment.title))

            cur = alfred_local_db.find({"expAuthorMail": current_user.email, "expName": experiment_title, "expVersion": {"$in": form.version.data}})

        none_value = None
        # if form.replace_none.data:
        if form.none_value.data:
            none_value = form.none_value.data

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

    return render_template("web_export.html", form=form, experiment=experiment, legend="Download data")


@local_experiments.route("/<username>/<experiment_title>/delete", methods=["POST", "GET"])  # only allow POST requests
@login_required
def delete_experiment(username, experiment_title):

    experiment = LocalExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    experiment.delete()
    flash("Experiment deleted.", "info")

    return redirect(url_for('main.home'))
