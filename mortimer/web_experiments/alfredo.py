import sys
import importlib.util
from flask import Blueprint, abort, request, session, url_for, redirect, make_response, flash, send_file
from threading import Lock
from time import time
from uuid import uuid4
from mortimer.models import WebExperiment
from bson.objectid import ObjectId
import re
import os
import inspect


class Script:

    def __init__(self, experiment=None):
        self.experiment = experiment

    def generate_experiment(self):
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
    experiment = WebExperiment.objects.get_or_404(id=experiment_id)

    # Fast path: see if the module has already been imported.
    try:
        return sys.modules[experiment.script_name]
    except KeyError:
        pass

    path = experiment.script_fullpath

    spec = importlib.util.spec_from_file_location(experiment.script_name, path)
    module = importlib.util.module_from_spec(spec)
    module.filepath = experiment.path  # Creates new variable filepath in globals() of imported module before loading
    spec.loader.exec_module(module)

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
alfredo = Blueprint('alfredo', __name__, template_folder='templates')


@alfredo.route('/')
def index():
    return "Welcome to Alfredo :-)"


@alfredo.route('/start/<expid>', methods=['GET', 'POST'])
def start(expid):
    experiment = WebExperiment.objects.get_or_404(id=ObjectId(expid))

    if not experiment.script_name:
        flash("You need to add a script.py file, before you can start an experiment.", "warning")
        return redirect(url_for('web_experiments.experiment', experiment_title=experiment.title, username=experiment.author))

    if not experiment.active:
        abort(403)

    if not experiment.public and experiment.password != request.form.get('password', None):
        exp_url = url_for('alfredo.start', expid=str(experiment.id))
        return '<div align="center"><h1>Please enter the password</h1><form method="post" action="%s">\
            <input type="password" name="password" /><button type="submit">Submit</button></form></div>' % exp_url

    sid = str(uuid4())
    session['sid'] = sid
    session['page_tokens'] = []

    # get values passed by get or post request
    values = request.values.to_dict()

    # os.chdir(experiment.path)

    try:
        module = import_script(experiment.id)
    except Exception as e:
        flash("Error during script import:\n'{e}'".format(e=e), 'danger')
        return redirect(url_for('web_experiments.experiment', username=experiment.author, exp_title=experiment.title))

    try:
        script = Script()
        script.set_generator(module.generate_experiment)
        
        custom_settings = {
        "author": experiment.author,
        "title": experiment.title,
        "version": experiment.version,
        "exp_id": str(experiment.id),
        "path": experiment.path,
        "session_id": sid,
        "type": "web"
        }

        try:
            if number_of_func_params(module.generate_experiment) > 1:
                script.experiment = script.generate_experiment(custom_settings=custom_settings,**values)
            else:
                script.experiment = script.generate_experiment(custom_settings=custom_settings)
        except SyntaxError:
            flash("The definition of experiment title, type, or version in script.py is deprecated. Please define these parameters in config.conf, when you are working locally. Mortimer will set these parameters for you automatically. In your script.py, just use 'exp = Experiment()'.", "danger")
            return redirect(url_for('web_experiments.experiment', username=experiment.author, exp_title=experiment.title))

    except Exception as e:
        flash("Error during experiment generation:\n'{e}'".format(e=e), 'danger')
        return redirect(url_for('web_experiments.experiment', username=experiment.author, exp_title=experiment.title))

    try:
        # start experiment
        script.experiment.start()
    except Exception as e:
        flash("Error during experiment startup:\n'{e}'".format(e=e), 'danger')
        return redirect(url_for('web_experiments.experiment', username=experiment.author, exp_title=experiment.title))

    # set session variables
    experiment_manager.save(sid, script)

    return redirect(url_for('alfredo.experiment'))


@alfredo.route('/experiment', methods=['GET', 'POST'])
def experiment():
    try:
        sid = session['sid']
    except KeyError:
        abort(412)
        return

    script = experiment_manager.get(sid)

    if request.method == "POST":

        move = request.values.get('move', None)
        directjump = request.values.get('directjump', None)
        par = request.values.get('par', None)
        page_token = request.values.get('page_token', None)

        try:
            token_list = session['page_tokens']
            token_list.remove(page_token)
            session['page_tokens'] = token_list
        except ValueError:
            return redirect(url_for('alfredo.experiment'))

        kwargs = request.values.to_dict()
        kwargs.pop('move', None)
        kwargs.pop('directjump', None)
        kwargs.pop('par', None)

        script.experiment.user_interface_controller.update_with_user_input(kwargs)
        if move is None and directjump is None and par is None and kwargs == {}:
            pass
        elif directjump and par:
            posList = list(map(int, par.split('.')))
            script.experiment.user_interface_controller.move_to_position(posList)
        elif move == 'started':
            pass
        elif move == 'forward':
            script.experiment.user_interface_controller.move_forward()
        elif move == 'backward':
            script.experiment.user_interface_controller.move_backward()
        elif move == 'jump' and par and re.match(r'^\d+(\.\d+)*$', par):
            posList = list(map(int, par.split('.')))
            script.experiment.user_interface_controller.move_to_position(posList)
        else:
            abort(400)
        return redirect(url_for('alfredo.experiment'))

    elif request.method == "GET":
        page_token = str(uuid4())

        token_list = session['page_tokens']
        token_list.append(page_token)
        session['page_tokens'] = token_list

        resp = make_response(script.experiment.user_interface_controller.render(page_token))
        resp.cache_control.no_cache = True
        return resp


@alfredo.route('/staticfile/<identifier>')
def staticfile(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        path, content_type = script.experiment.user_interface_controller.get_static_file(identifier)

    except KeyError:
        abort(404)
    resp = make_response(send_file(path, mimetype=content_type))

    # resp.cache_control.no_cache = True
    return resp


@alfredo.route('/dynamicfile/<identifier>')
def dynamicfile(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        strIO, content_type = script.experiment.user_interface_controller.get_dynamic_file(identifier)
    except KeyError:
        abort(404)
    resp = make_response(send_file(strIO, mimetype=content_type))
    resp.cache_control.no_cache = True
    return resp


@alfredo.route('/callable/<identifier>', methods=['GET', 'POST'])
def callable(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        f = script.experiment.user_interface_controller.get_callable(identifier)
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
        resp = make_response(redirect(url_for('alfredo.experiment')))
    resp.cache_control.no_cache = True
    return resp
