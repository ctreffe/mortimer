# -*- coding: utf-8 -*-

import importlib.util
import inspect
import os
import re
import sys
import traceback
import logging
from pathlib import Path
from threading import Lock
from time import time
from uuid import uuid4

from bson.objectid import ObjectId
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
    jsonify,
)
from flask_login import current_user

from mortimer.models import WebExperiment, User
from mortimer.utils import (
    create_fernet,
    is_social_media_preview,
    render_social_media_preview,
)
from alfred3 import alfredlog
import alfred3.config


class Script:
    def __init__(self):

        self.experiment = None
        self.exp_session = None
        self.expdir = None
        self.config = None

    def generate_experiment(self, config=None):  # pylint: disable=method-hidden
        """Hook for the ``generate_experiment`` function extracted from
        the user's script.py. It is meant to be replaced in ``run.py``.
        """

        return ""


class Script2:
    def __init__(self, experiment=None):
        self.experiment = experiment

    def generate_experiment(self):  # pylint: disable=method-hidden
        pass

    def set_generator(self, generator):
        self.generate_experiment = generator.__get__(self, Script)


def number_of_func_params(func):
    # use in python 3 inspect.signature
    argspec = inspect.getfullargspec(func)
    num_params = len(argspec[0])
    if argspec[1] is not None:
        num_params += 1
    if argspec[2] is not None:
        num_params += 1
    return num_params


def import_script(experiment_id):
    experiment = WebExperiment.objects.get_or_404(
        id=experiment_id
    )  # pylint: disable=no-member

    # Fast path: see if the module has already been imported.
    try:
        return sys.modules[experiment.script_name]
    except KeyError:
        pass

    path = experiment.script_fullpath

    sys.path.append(experiment.path)

    spec = importlib.util.spec_from_file_location(experiment.script_name, path)
    module = importlib.util.module_from_spec(spec)
    module.filepath = (
        experiment.path
    )  # Creates new variable filepath in globals() of imported module before loading
    spec.loader.exec_module(module)

    sys.path.remove(experiment.path)

    return module


class ExperimentManager(object):
    def __init__(self, timeout=60 * 60 * 24 * 2):
        self.timeout = timeout
        self.experiments = {}
        self.lock = Lock()

    def save(self, key, experiment):
        self.remove_outdated()
        self.lock.acquire()
        self.experiments[key] = (int(time()), experiment)
        self.lock.release()

    def remove(self, key):
        self.remove_outdated()
        self.lock.acquire()
        try:
            del self.experiments[key]
        except KeyError:
            pass
        self.lock.release()

    def get(self, key):
        self.remove_outdated()
        self.lock.acquire()
        rv = self.experiments.get(key, (None, None))[1]

        self.lock.release()
        if rv is None:
            molog = logging.getLogger("mortimer")
            molog.warning(
                f"Tried to access experiment with session id '{key}'. Available Keys:"
                f" {list(self.experiments.keys())}"
            )
            abort(412)
        self.save(key, rv)
        return rv

    def remove_outdated(self):
        self.lock.acquire()
        current_time = int(time())
        molog = logging.getLogger("mortimer")
        for k in list(self.experiments.keys()):
            v = self.experiments[k]
            if current_time - v[0] > self.timeout:
                molog.warning(f"Delete exp with session id '{k}' and last access time {v[0]}")
                del self.experiments[k]
        self.lock.release()


experiment_manager = ExperimentManager()
alfredo = Blueprint("alfredo", __name__, template_folder="templates")


@alfredo.route("/")
def index():
    return "Welcome to Alfredo :-)"


@alfredo.route("/start/<expid>", methods=["GET", "POST"])
def start(expid):
    # pylint: disable=no-member
    experiment = WebExperiment.objects.get_or_404(id=ObjectId(expid))

    # create session id
    sid = "sid-" + str(uuid4())

    config = experiment.parse_exp_config(sid)
    secrets = experiment.parse_exp_secrets()

    if is_social_media_preview(request.headers.get("User-Agent")):
        return render_social_media_preview(config)

    if not experiment.public and experiment.password != request.form.get(
        "password", None
    ):
        exp_url = url_for("alfredo.start", expid=str(experiment.id))
        return (
            '<div align="center"><h1>Please enter the password</h1><form method="post"'
            ' action="%s">            <input type="password" name="password" /><button'
            ' type="submit">Submit</button></form></div>' % exp_url
        )

    args = request.args.to_dict()
    test_mode = args.get("test") in ["true", "True", "TRUE"]
    debug_mode = args.get("debug") in ["true", "True", "TRUE"] or config.getboolean(
        "general", "debug"
    )
    if not experiment.active and not test_mode and not debug_mode:
        return render_template("exp_inactive.html")

    session["sid"] = sid
    session["page_tokens"] = {}

    # initialize log
    log = alfredlog.QueuedLoggingInterface("alfred3", f"exp.{str(experiment.id)}")
    log.session_id = sid
    log.setLevel(config.get("log", "level").upper())
    experiment.prepare_logger()

    log.debug("Access from: " + request.headers.get("User-Agent"))

    # IMPORT SCRIPT CREATE SESSION
    try:
        user_script = import_script(experiment.id)
        exp_session = user_script.exp.create_session(
            session_id=sid, config=config, secrets=secrets, **request.args
        )

    except Exception:
        msg = "Error during creation of experiment session."
        log.exception(msg)
        if current_user.is_authenticated:
            flash(f"{msg} For further details, take a look at the log.", "danger")
            return redirect(
                url_for(
                    "web_experiments.experiment",
                    username=current_user.username,
                    exp_title=experiment.title,
                )
            )
        else:
            abort(500)

    try:
        exp_session._start()
        experiment_manager.save(sid, exp_session)
    except Exception:
        msg = "An exception occured during experiment startup."
        log.exception(msg)
        if current_user.is_authenticated:
            flash(f"{msg} For further details, take a look at the log.", "danger")
            return redirect(
                url_for(
                    "web_experiments.experiment",
                    username=current_user.username,
                    exp_title=experiment.title,
                )
            )
        else:
            abort(500)

    page = request.args.get("page", None)
    if page:
        return redirect(url_for("alfredo.experiment", page=page))
    return redirect(url_for("alfredo.experiment"))


@alfredo.route("/experiment", methods=["GET", "POST"])
def experiment():
    molog = logging.getLogger("mortimer")
    try:
        sid = session["sid"]
    except KeyError:
        molog.warning(
            "Experiment route called, but there was no session id in the session"
            " cookie."
        )
        abort(412)

    experiment = experiment_manager.get(sid)
    tkey = experiment.current_page.name + sid

    try:
        if request.method == "GET":
            url_pagename = request.args.get(
                "page", None
            )  # https://basepath.de/experiment?page=name
            if url_pagename:
                experiment.movement_manager.move(direction=f"jump>{url_pagename}")

            token = session["page_tokens"].get(tkey, uuid4().hex)
            session["page_tokens"][tkey] = token
            session.modified = True  # because the dict is mutable

            current_page_html = make_response(experiment.ui.render_html(token))
            current_page_html.cache_control.no_cache = True
            return current_page_html

        elif request.method == "POST":
            move = request.values.get("move", None)
            submitted_token = request.values.get("page_token", None)

            token = session["page_tokens"].pop(tkey, None)
            session.modified = True  # because the dict is mutable
            if not token or not token == submitted_token:
                return redirect(url_for("alfredo.experiment"))

            data = request.values.to_dict()
            data.pop("move", None)
            data.pop("directjump", None)
            data.pop("par", None)

            experiment.movement_manager.current_page._set_data(data)
            if move is None and not data:
                pass
            elif move:
                experiment.movement_manager.move(direction=move)
            else:
                abort(400)
            return redirect(url_for("alfredo.experiment"))

    except Exception:
        log = alfredlog.QueuedLoggingInterface(
            "alfred3", f"exp.{str(experiment.exp_id)}"
        )
        log.session_id = sid
        msg = "Exception during experiment execution."
        log.exception(msg)
        if current_user.is_authenticated:
            flash(f"{msg} For further details, take a look at the log.", "danger")
            return redirect(
                url_for(
                    "web_experiments.experiment",
                    username=current_user.username,
                    exp_title=experiment.title,
                )
            )
        else:
            abort(500)


@alfredo.route("/staticfile/<identifier>")
def staticfile(identifier):
    try:
        sid = session["sid"]
        experiment = experiment_manager.get(sid)
        path, content_type = experiment.user_interface_controller.get_static_file(
            identifier
        )
        dirname, filename = os.path.split(path)
        resp = make_response(
            send_from_directory(dirname, filename, mimetype=content_type)
        )
        # resp.cache_control.no_cache = True
        return resp

    except KeyError:
        abort(404)


@alfredo.route("/dynamicfile/<identifier>")
def dynamicfile(identifier):
    try:
        sid = session["sid"]
        experiment = experiment_manager.get(sid)
        strIO, content_type = experiment.user_interface_controller.get_dynamic_file(
            identifier
        )
    except KeyError:
        abort(404)
    resp = make_response(send_file(strIO, mimetype=content_type))
    resp.cache_control.no_cache = True
    return resp


@alfredo.route("/callable/<identifier>", methods=["GET", "POST"])
def callable(identifier):
    try:
        sid = session["sid"]
        experiment = experiment_manager.get(sid)
        f = experiment.user_interface_controller.get_callable(identifier)
    except KeyError:
        abort(404)

    if request.content_type == "application/json":
        values = request.get_json()
    else:
        values = request.values.to_dict()

    values.pop("_", None)  # remove argument with name "_"

    rv = f(**values)
    if rv is not None:
        resp = jsonify(rv)
        resp.cache_control.no_cache = True
        return resp
    else:
        return (" ", 204)
