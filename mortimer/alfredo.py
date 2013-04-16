import os
import imp
from time import time
from threading import Lock
from uuid import uuid4

from flask import Blueprint, current_app, escape, session, send_file, \
        redirect, url_for, abort, request

alfredo = Blueprint('alfredo', __name__, template_folder='templates')

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
        except:
            pass
        self.lock.release()


    def get(self, key):
        self.remove_outdated()
        self.lock.acquire()
        rv = self.experiments.get(key, (None, None))[1]
        self.lock.release()
        if rv is None:
            abort(412)
        return rv

    def remove_outdated(self):
        self.lock.acquire()
        current_time = int(time())
        for k in self.experiments.keys():
            v = self.experiments[k]
            if current_time - v[0] > self.timeout:
                del self.experiments[k]
        self.lock.release()

experiment_manager = ExperimentManager()


@alfredo.route('/')
def index():
    experiments = current_app.db.Experiment.find({'access_type': 'public', 'active': True}, {'name': True})
    return "Public available experiments: %s" % escape(list(experiments))

@alfredo.route('/start/<ObjectId:id>/', methods=['GET', 'POST'])
def start(id):
    experiment = current_app.db.Experiment.get_or_404(id)

    if not experiment.active:
        abort(403)

    if experiment.access_type == 'password' \
            and experiment.password != request.form.get('password', None):
        return '<h1>Please enter the password</h1><form method="post" action="."><input type="password" name="password" /><button type="submit">Submit</button></form>'

    sid = str(uuid4())
    session['sid'] = sid

    # create experiment
    f, pathname, desc = imp.find_module(str(experiment._id), 
        [os.path.join(current_app.instance_path,
        current_app.config['SCRIPT_FOLDER'])]
    )
    try:
        module = imp.load_module(str(experiment._id), f, pathname, desc)
    finally:
        f.close()
    script = module.Script()
    script.experiment = script.generate_experiment()

    # start experiment
    script.experiment.start()

    # set session variables
    experiment_manager.save(sid, script)

    return redirect(url_for('alfredo.experiment'))

@alfredo.route('/experiment/', methods=['GET', 'POST'])
def experiment():
    sid = session['sid']
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

    return script.experiment.userInterfaceController.render()

@alfredo.route('/staticfile/<identifier>')
def staticfile(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        path, content_type = script.experiment.userInterfaceController.getStaticFile(identifier)
    except KeyError:
       abort(404)
    return send_file(path, mimetype=content_type)

@alfredo.route('/dynamicfile/<identifier>')
def dynamicfile(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        strIO, content_type = script.experiment.userInterfaceController.getDynamicFile(identifier)
    except KeyError:
        abort(404)
    return send_file(strIO, mimetype=content_type)

@alfredo.route('/callable/<identifier>', methods=['GET', 'POST'])
def callable(identifier):
    try:
        sid = session['sid']
        script = experiment_manager.get(sid)
        f = script.experiment.userInterfaceController.getCallable(identifier)
    except KeyError:
        abort(404)
    rv = f(**request.values.to_dict())
    if rv is not None:
        return rv
    else:
        return redirect(url_for('alfredo.experiment'))

