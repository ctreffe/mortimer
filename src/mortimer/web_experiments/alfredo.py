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
)
from flask_login import current_user

from mortimer.models import WebExperiment, User
from mortimer.utils import create_fernet
from alfred3 import alfredlog
import alfred3.config


class Script:
    def __init__(self):

        self.experiment = None
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
    experiment = WebExperiment.objects.get_or_404(id=experiment_id)  # pylint: disable=no-member

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
    def __init__(self, timeout=3600):
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
            try:
                print("Tried to access experiment with key %s" % key)
                print("Available Keys: %s" % list(self.experiments.keys()))
            except Exception:
                pass
            abort(412)
        self.save(key, rv)
        return rv

    def remove_outdated(self):
        self.lock.acquire()
        current_time = int(time())
        for k in list(self.experiments.keys()):
            v = self.experiments[k]
            if current_time - v[0] > self.timeout:
                print("delete exp with key %s and last access time %s" % (k, v[0]))
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

    if not experiment.public and experiment.password != request.form.get("password", None):
        exp_url = url_for("alfredo.start", expid=str(experiment.id))
        return (
            '<div align="center"><h1>Please enter the password</h1><form method="post" action="%s">\
            <input type="password" name="password" /><button type="submit">Submit</button></form></div>'
            % exp_url
        )

    # create session id
    sid = str(uuid4())
    session["sid"] = sid
    session["page_tokens"] = []

    # initialize configuration
    config = {
        "exp_config": experiment.parse_exp_config(sid),
        "exp_secrets": experiment.parse_exp_secrets(),
    }

    # initialize log
    log = alfredlog.QueuedLoggingInterface("alfred3", f"exp.{str(experiment.id)}")
    log.session_id = sid
    log.setLevel(config["exp_config"].get("log", "level").upper())
    experiment.prepare_logger()

    try:
        user_script = import_script(experiment.id)
        Script.generate_experiment = user_script.generate_experiment
        script = Script()
        alfred_exp = script.generate_experiment(config=config)
        alfred_exp.start()
        experiment_manager.save(sid, alfred_exp)
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

    return redirect(url_for("alfredo.experiment"))


@alfredo.route("/experiment", methods=["GET", "POST"])
def experiment():
    try:
        sid = session["sid"]
    except KeyError:
        abort(412)
        return

    experiment = experiment_manager.get(sid)

    try:
        if request.method == "POST":

            move = request.values.get("move", None)
            directjump = request.values.get("directjump", None)
            par = request.values.get("par", None)
            page_token = request.values.get("page_token", None)

            try:
                token_list = session["page_tokens"]
                token_list.remove(page_token)
                session["page_tokens"] = token_list
            except ValueError:
                return redirect(url_for("alfredo.experiment"))

            kwargs = request.values.to_dict()
            kwargs.pop("move", None)
            kwargs.pop("directjump", None)
            kwargs.pop("par", None)

            experiment.user_interface_controller.update_with_user_input(kwargs)
            if move is None and directjump is None and par is None and kwargs == {}:
                pass
            elif directjump and par:
                posList = list(map(int, par.split(".")))
                experiment.user_interface_controller.move_to_position(posList)
            elif move == "started":
                pass
            elif move == "forward":
                experiment.user_interface_controller.move_forward()
            elif move == "backward":
                experiment.user_interface_controller.move_backward()
            elif move == "jump" and par and re.match(r"^\d+(\.\d+)*$", par):
                posList = list(map(int, par.split(".")))
                experiment.user_interface_controller.move_to_position(posList)
            else:
                abort(400)
            return redirect(url_for("alfredo.experiment"))

        elif request.method == "GET":
            page_token = str(uuid4())

            token_list = session["page_tokens"]
            token_list.append(page_token)
            session["page_tokens"] = token_list

            resp = make_response(experiment.user_interface_controller.render(page_token))
            resp.cache_control.no_cache = True
            return resp
    except Exception:
        log = alfredlog.QueuedLoggingInterface("alfred3", f"exp.{str(experiment.id)}")
        log.session_id = sid
        log.exception("Exception during experiment execution.")
        # raise e
        # logger.critical(
        #     msg=traceback.format_exc(), exp_id=str(experiment.exp_id), session_id=sid
        # )
        return render_template("errors/500_alfred.html")


@alfredo.route("/staticfile/<identifier>")
def staticfile(identifier):
    try:
        sid = session["sid"]
        experiment = experiment_manager.get(sid)
        path, content_type = experiment.user_interface_controller.get_static_file(identifier)
        dirname, filename = os.path.split(path)
        resp = make_response(send_from_directory(dirname, filename, mimetype=content_type))
        # resp.cache_control.no_cache = True
        return resp

    except KeyError:
        abort(404)


@alfredo.route("/dynamicfile/<identifier>")
def dynamicfile(identifier):
    try:
        sid = session["sid"]
        experiment = experiment_manager.get(sid)
        strIO, content_type = experiment.user_interface_controller.get_dynamic_file(identifier)
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
    rv = f(**values)
    if rv is not None:
        resp = make_response(rv)
    else:
        resp = make_response(redirect(url_for("alfredo.experiment")))
    resp.cache_control.no_cache = True
    return resp

