# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from mortimer.export import make_str_bytes, to_json
from mortimer.forms import LocalExperimentForm
from mortimer.forms import ExportExpDataForm
from mortimer.forms import ExportCodebookForm
from mortimer.models import LocalExperiment, User
from mortimer.utils import get_alfred_db

from alfred3.data_manager import DataManager
from alfred3.data_manager import ExpDataExporter
from alfred3.data_manager import CodeBookExporter

from bson import json_util

local_experiments = Blueprint("local_experiments", __name__)

# pylint: disable=no-member


@local_experiments.route("/new_local_experiment", methods=["POST", "GET"])
@login_required
def new_local_experiment():
    form = LocalExperimentForm()

    id = str(uuid4())

    if form.validate_on_submit():

        experiment = LocalExperiment(
            title=form.title.data,
            author=current_user.username,
            description=form.description.data,
            exp_id=form.exp_id.data,
        )

        experiment.save()
        flash("New local experiment added.", "success")
        return redirect(
            url_for(
                "local_experiments.local_experiment",
                username=current_user.username,
                experiment_title=experiment.title,
            )
        )

    return render_template(
        "create_local_experiment.html", form=form, legend="New Local Experiment", id=id
    )


@local_experiments.route("/local/<username>/<path:experiment_title>", methods=["POST", "GET"])
@login_required
def local_experiment(username, experiment_title):

    experiment = LocalExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    db = get_alfred_db()
    alfred_local_db = db[current_user.local_col]

    datasets = {}

    datasets["all_datasets"] = alfred_local_db.count_documents(
        {"exp_id": experiment.exp_id, "type": DataManager.EXP_DATA}
    )
    datasets["all_finished_datasets"] = alfred_local_db.count_documents(
        {"exp_id": experiment.exp_id, "exp_finished": True}
    )
    datasets["all_unfinished_datasets"] = (
        datasets["all_datasets"] - datasets["all_finished_datasets"]
    )

    versions = {}
    all_activity = []
    created = []
    cur = alfred_local_db.find({"exp_id": experiment.exp_id, "type": DataManager.EXP_DATA})
    for exp in cur:
        all_activity.append(exp["start_time"])
        if exp["exp_version"] not in versions.keys():
            versions[exp["exp_version"]] = {"total": 1, "finished": 0, "unfinished": 0}
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

    return render_template(
        "local_experiment.html",
        experiment=experiment,
        expid=str(experiment.id),
        datasets=datasets,
        first_activity=first_activity,
        last_activity=last_activity,
        versions=versions,
    )


@local_experiments.route("/local/experiments")
def experiments():

    if current_user.is_authenticated:
        return redirect(
            url_for("local_experiments.user_experiments", username=current_user.username)
        )
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

    experiments = LocalExperiment.objects(author=user.username).order_by("-date_created")  # \
    # .paginate(page=page, per_page=Config.EXP_PER_PAGE)

    return render_template("user_local_experiments.html", experiments=experiments, user=user)


@local_experiments.route(
    "/local/<username>/<path:experiment_title>/local_export", methods=["POST", "GET"]
)
@login_required
def local_export(username, experiment_title):
    experiment = LocalExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    versions1 = [
        (version, version) for version in ["all versions"] + experiment.available_versions
    ]
    versions2 = [(version, version) for version in ["latest"] + experiment.available_versions]

    form_exp_data = ExportExpDataForm()
    form_exp_data.version.choices = versions1

    form_codebook = ExportCodebookForm()
    form_codebook.version.choices = versions2

    if form_exp_data.validate_on_submit():
        db = get_alfred_db()
        if form_exp_data.data_type.data == "exp_data":
            col = current_user.local_col
            f = {"exp_id": str(experiment.exp_id), "type": DataManager.EXP_DATA}
        elif form_exp_data.data_type.data == "unlinked":
            col = current_user.local_col_unlinked
            f = {"exp_id": str(experiment.exp_id), "type": DataManager.UNLINKED_DATA}

        exporter = ExpDataExporter()
        if not "all versions" in form_exp_data.version.data:
            f.update({"exp_version": {"$in": form_exp_data.version.data}})

        if not db[col].find_one():
            flash("No data found.", "info")
            return redirect(
                url_for(
                    "local_experiments.local_export",
                    username=experiment.author,
                    experiment_title=experiment.title,
                )
            )

        cursor = db[col].find(f)

        if "csv" in form_exp_data.file_type.data:
            for dataset in cursor:
                print(dataset)
                exporter.process_one(dataset)

            delimiter = ";" if form_exp_data.file_type.data == "csv2" else ","
            data = exporter.write_to_object(delimiter=delimiter)
            fn = f"{form_exp_data.data_type.data}_{experiment.title}.csv"
            return send_file(
                make_str_bytes(data),
                mimetype="text/csv",
                as_attachment=True,
                attachment_filename=fn,
                cache_timeout=1,
            )

        elif form_exp_data.file_type.data == "json":
            data = to_json(cursor)
            fn = f"{form_exp_data.data_type.data}_{experiment.title}.json"
            return send_file(
                make_str_bytes(data),
                mimetype="application/json",
                as_attachment=True,
                attachment_filename=fn,
                cache_timeout=1,
            )

    if form_codebook.validate_on_submit():
        db = get_alfred_db()
        col = current_user.local_col_misc
        f = {"exp_id": str(experiment.exp_id), "type": DataManager.CODEBOOK_DATA}

        codebook = db[col].find_one(f)
        if not codebook:
            flash("No codebook data found.", "info")
            return redirect(
                url_for(
                    "local_experiments.local_export",
                    experiment_title=experiment.title,
                    username=current_user.username,
                )
            )

        exporter = CodeBookExporter()
        exporter.process(codebook)

        if "csv" in form_exp_data.file_type.data:

            delimiter = ";" if form_codebook.file_type.data == "csv2" else ","
            data = exporter.write_to_object(delimiter=delimiter)
            fn = f"codebook_{experiment.title}.csv"
            return send_file(
                make_str_bytes(data),
                mimetype="text/csv",
                as_attachment=True,
                attachment_filename=fn,
                cache_timeout=1,
            )

        elif form_exp_data.file_type.data == "json":
            data = json_util.dumps(exporter.full_codebook, indent=4)
            fn = f"codebook_{experiment.title}.json"
            return send_file(
                make_str_bytes(data),
                mimetype="application/json",
                as_attachment=True,
                attachment_filename=fn,
                cache_timeout=1,
            )

    return render_template(
        "local_export.html",
        experiment=experiment,
        form_exp_data=form_exp_data,
        form_codebook=form_codebook,
    )


# only allow POST requests
@local_experiments.route("/local/<username>/<path:experiment_title>/delete", methods=["POST"])
@login_required
def delete_experiment(username, experiment_title):

    experiment = LocalExperiment.objects.get_or_404(title=experiment_title, author=username)

    if experiment.author != current_user.username:
        abort(403)

    experiment.delete()
    flash("Experiment deleted.", "info")

    return redirect(url_for("main.home"))
