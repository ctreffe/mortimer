# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import uuid4

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   send_file, url_for)
from flask_login import current_user, login_required

from mortimer import export
from mortimer.forms import ExperimentExportForm, LocalExperimentForm
from mortimer.models import LocalExperiment, User
from mortimer.utils import get_alfred_db

local_experiments = Blueprint("local_experiments", __name__)

# pylint: disable=no-member

@local_experiments.route("/new_local_experiment", methods=["POST", "GET"])
@login_required
def new_local_experiment():
    form = LocalExperimentForm()

    id = str(uuid4())

    if form.validate_on_submit():

        experiment = LocalExperiment(title=form.title.data, author=current_user.username,
                                     description=form.description.data, exp_id=form.exp_id.data)

        experiment.save()
        flash("New local experiment added.", "success")
        return redirect(url_for('local_experiments.local_experiment', username=current_user.username, experiment_title=experiment.title))

    return render_template("create_local_experiment.html", form=form, legend="New Local Experiment", id=id)


@local_experiments.route("/local/<username>/<path:experiment_title>", methods=["POST", "GET"])
@login_required
def local_experiment(username, experiment_title):

    experiment = LocalExperiment.objects.get_or_404(
        title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    
    db = get_alfred_db()
    alfred_local_db = db[current_user.local_col]
    
    datasets = {}

    datasets["all_datasets"] = alfred_local_db.count_documents({"exp_id": experiment.exp_id})
    datasets["all_finished_datasets"] = alfred_local_db.count_documents(
        {"exp_id": experiment.exp_id, "exp_finished": True})
    datasets["all_unfinished_datasets"] = datasets["all_datasets"] - \
        datasets["all_finished_datasets"]

    versions = {}
    all_activity = []
    created = []
    cur = alfred_local_db.find(
        {"exp_id": experiment.exp_id})
    for exp in cur:
        all_activity.append(exp["start_time"])
        if exp["exp_version"] not in versions.keys():
            versions[exp["exp_version"]] = {
                "total": 1, "finished": 0, "unfinished": 0}
        else:
            versions[exp["exp_version"]]["total"] += 1
        if exp["exp_finished"]:
            versions[exp["exp_version"]]["finished"] += 1
        else:
            versions[exp["exp_version"]]["unfinished"] += 1
        created.append(exp["start_time"])

    if all_activity:
        first_activity = datetime.fromtimestamp(min(all_activity))
        last_activity = datetime.fromtimestamp(max(all_activity))
    else:
        first_activity = "none"
        last_activity = "none"

    # if not versions:
    #     flash('Experiment not found in database.', 'danger')

    return render_template("local_experiment.html",
                           experiment=experiment, expid=str(experiment.id), datasets=datasets,
                           first_activity=first_activity, last_activity=last_activity,
                           versions=versions)


@local_experiments.route("/local/experiments")
def experiments():

    if current_user.is_authenticated:
        return redirect(url_for('local_experiments.user_experiments', username=current_user.username))
    else:
        flash("Please log in to access this page.", "info")
        return redirect(url_for("users.login"))


@local_experiments.route("/local/<string:username>/experiments")
@login_required
def user_experiments(username):

    # page = request.args.get("page", 1, type=int)
    user = User.objects.get_or_404(username=username)

    if user.username != current_user.username:
        abort(403)

    experiments = LocalExperiment.objects(author=user.username)\
        .order_by("-date_created")#\
        # .paginate(page=page, per_page=Config.EXP_PER_PAGE)

    return render_template("user_local_experiments.html", experiments=experiments, user=user)


@local_experiments.route("/local/<username>/<path:experiment_title>/export", methods=["POST", "GET"])
@login_required
def local_export(username, experiment_title):
    experiment = LocalExperiment.objects.get_or_404(
        title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    form = ExperimentExportForm()
    
    db = get_alfred_db()
    alfred_local_db = db[current_user.local_col]
    cur = alfred_local_db.find(
        {"exp_id": str(experiment.exp_id)})
    
    available_versions = ["all versions"]
    for exp in cur:
        if exp["exp_version"] not in available_versions:
            available_versions.append(exp["exp_version"])
    form.version.choices = [(version, version)
                            for version in available_versions]
    form.file_type.choices = [("csv", "csv")]
    # form.version.choices = [(version, version) for version in experiment.available_versions]

    if form.validate_on_submit():
        if "all versions" in form.version.data:
            results = alfred_local_db.count_documents(
                {"exp_id": experiment.exp_id})
            if results == 0:
                flash("No data found for this experiment.", "warning")
                return redirect(url_for('web_experiments.web_export', username=experiment.author, experiment_title=experiment.title))

            cur = alfred_local_db.find(
                {"exp_id": experiment.exp_id})
        else:
            for version in form.version.data:
                results = []
                results.append(
                    alfred_local_db.count_documents(
                        {"exp_id": experiment.exp_id, "exp_version": version}
                    )
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

            cur = alfred_local_db.find(
                {
                    "exp_id": experiment.exp_id,
                    "exp_version": {"$in": form.version.data},
                }
            )


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
                             as_attachment=True, attachment_filename='export_%s_local.csv' % experiment.title, cache_timeout=1)
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

    return render_template("local_export.html", form=form, experiment=experiment, legend="Export data")


# only allow POST requests
@local_experiments.route("/local/<username>/<path:experiment_title>/delete", methods=["POST"])
@login_required
def delete_experiment(username, experiment_title):

    experiment = LocalExperiment.objects.get_or_404(
        title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    experiment.delete()
    flash("Experiment deleted.", "info")

    return redirect(url_for('main.home'))
