import os
import sys
import imp
from time import time
from threading import Lock
from uuid import uuid4
import re

from flask import Blueprint, current_app, session, send_file, redirect, url_for, abort, request, make_response


def import_script(name):
    # Fast path: see if the module has already been imported.
    try:
        return sys.modules[name]
    except KeyError:
        pass

    # If any of the following calls raises an exception,
    # there's a problem we can't handle -- let the caller handle it.
    fp, path, desc = imp.find_module(name,
                                     [os.path.join(current_app.instance_path, current_app.config['SCRIPT_FOLDER'])])

    try:
        return imp.load_module(name, fp, path, desc)
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()


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
                print "Tried to access experiment with key %s" % key
                print "Available Keys: %s" % self.experiments.keys()
            except:
                pass
            abort(412)
        self.save(key, rv)
        return rv

    def remove_outdated(self):
        self.lock.acquire()
        current_time = int(time())
        for k in self.experiments.keys():
            v = self.experiments[k]
            if current_time - v[0] > self.timeout:
                print "delete exp with key %s and last access time %s" % (k, v[0])
                del self.experiments[k]
        self.lock.release()


experiment_manager = ExperimentManager()
alfredo = Blueprint('alfredo', __name__, template_folder='templates')


@alfredo.route('/')
def index():
    return "Welcome to Alfredo :-)"


@alfredo.route('/start/<ObjectId:expid>/', methods=['GET', 'POST'])
def start(expid):
    experiment = current_app.db.Experiment.get_or_404(expid)

    if not experiment.active:
        abort(403)

    if experiment.access_type == 'password' \
            and experiment.password != request.form.get('password', None):
        return '<h1>Please enter the password</h1><form method="post" action=".">'\
            '<input type="password" name="password" /><button type="submit">Submit</button></form>'

    sid = str(uuid4())
    session['sid'] = sid

    # create experiment
    module = import_script(str(experiment._id))
    script = module.Script()
    script.experiment = script.generate_experiment()

    # start experiment
    script.experiment.start()

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

    move = request.values.get('move', None)
    directjump = request.values.get('directjump', None)
    par = request.values.get('par', None)

    kwargs = request.values.to_dict()
    kwargs.pop('move', None)
    kwargs.pop('directjump', None)
    kwargs.pop('par', None)

    script.experiment.userInterfaceController.updateWithUserInput(kwargs)
    if move is None and directjump is None and par is None and kwargs == {}:
        pass
    elif directjump and par:
        posList = map(int, par.split('.'))
        script.experiment.userInterfaceController.moveToPosition(posList)
    elif move == 'started':
        pass
    elif move == 'forward':
        script.experiment.userInterfaceController.moveForward()
    elif move == 'backward':
        script.experiment.userInterfaceController.moveBackward()
    elif move == 'jump' and par and re.match('^\d+(\.\d+)*$', par):
        posList = map(int, par.split('.'))
        script.experiment.userInterfaceController.moveToPosition(posList)
    else:
        abort(400)

    resp = make_response(script.experiment.userInterfaceController.render())
    resp.cache_control.no_cache = True
    return resp


@alfredo.route('/staticfile/<identifier>')
def staticfile(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        path, content_type = script.experiment.userInterfaceController.getStaticFile(identifier)
    except KeyError:
        abort(404)
    resp = make_response(send_file(path, mimetype=content_type))
    #resp.cache_control.no_cache = True
    return resp


@alfredo.route('/dynamicfile/<identifier>')
def dynamicfile(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        strIO, content_type = script.experiment.userInterfaceController.getDynamicFile(identifier)
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
        f = script.experiment.userInterfaceController.getCallable(identifier)
    except KeyError:
        abort(404)
    if request.content_type == "application/json":
        values = request.to_json()
    else
        values = request.values.to_dict()
    rv = f(**values)
    if rv is not None:
        resp = make_response(rv)
    else:
        resp = make_response(redirect(url_for('alfredo.experiment')))
    resp.cache_control.no_cache = True
    return resp
