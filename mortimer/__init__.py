# -*- coding:utf-8 -*-

import os

from flask import Flask, g, session, url_for, abort, request, Response,\
    send_file, render_template, redirect
from flask.ext.login import LoginManager, login_required
from flask.ext.mongokit import MongoKit
from flask.ext.bcrypt import Bcrypt

from pymongo import MongoClient

from bson.objectid import ObjectId

from .models import *
from .views import *
from .alfredo import alfredo

# Configuration
DEBUG = True
SECRET_KEY = 'development key'
SCRIPT_FOLDER = 'scripts'
UPLOAD_FOLDER = 'uploads'

ALFRED_HOST = 'localhost'
ALFRED_DB = 'alfred'
ALFRED_COLLECTION = 'test_col'
ALFRED_USERNAME = None
ALFRED_PASSWORD = None

# Initalize Flask
app = Flask(__name__)
app.config.from_object(__name__)

# Create instance folders
if not os.path.exists(app.instance_path):
    os.makedirs(app.instance_path)
if not os.path.exists(os.path.join(app.instance_path, app.config['SCRIPT_FOLDER'])):
    os.makedirs(os.path.join(app.instance_path, app.config['SCRIPT_FOLDER']))
if not os.path.exists(os.path.join(app.instance_path, app.config['UPLOAD_FOLDER'])):
    os.makedirs(os.path.join(app.instance_path, app.config['UPLOAD_FOLDER']))

# Bcrypt
app.bcrypt = Bcrypt(app)

# login manager
login_manager = LoginManager()
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(id):
    return db.User.get_from_id(ObjectId(id))

login_manager.setup_app(app)

# Mongo
db = MongoKit(app)
app.db = db
db.register([User, Experiment])

alfred_db = MongoClient(app.config['ALFRED_HOST'])[app.config['ALFRED_DB']]
if app.config['ALFRED_USERNAME']:
    alfred_db.authenticate(app.config['ALFRED_USERNAME'],
            app.config['ALFRED_PASSWORD'])
app.alfred_col = alfred_db[app.config['ALFRED_COLLECTION']]


# register blueprints
app.register_blueprint(alfredo, url_prefix='/alfredo')
app.register_blueprint(alfredo, url_prefix='/alfred')

# Configure Routes
app.add_url_rule('/', view_func=IndexView.as_view('index'))

app.add_url_rule('/experiments/', view_func=ExperimentListView.as_view('experiments'))
app.add_url_rule('/experiment/new/', defaults={'id': None}, view_func=ExperimentEditView.as_view('experiment_new'))
app.add_url_rule('/experiment/<ObjectId:id>/', view_func=ExperimentView.as_view('experiment'))
app.add_url_rule('/experiment/<ObjectId:id>/edit/', view_func=ExperimentEditView.as_view('experiment_edit'))
app.add_url_rule('/experiment/<ObjectId:id>/delete/', view_func=ExperimentDeleteView.as_view('experiment_delete'))
app.add_url_rule('/experiment/<ObjectId:id>/export/', view_func=ExperimentExportView.as_view('experiment_export'))

app.add_url_rule('/uploads/', defaults={'path': '', 'delete': False}, view_func=UploadView.as_view('uploads'))
app.add_url_rule('/uploads/<path:path>/', defaults={'delete': False}, view_func=UploadView.as_view('upload-path'))
app.add_url_rule('/uploads/<path:path>/delete/', defaults={'delete': True}, view_func=UploadView.as_view('upload_delete'))

app.add_url_rule('/data/', view_func=FooView.as_view('data_management'))
app.add_url_rule('/settings/', view_func=FooView.as_view('settings'))
app.add_url_rule('/login/', view_func=LoginView.as_view('login'))
app.add_url_rule('/logout/', view_func=LogoutView.as_view('logout'))

@app.route('/add_user/<username>/<password>')
def add_user(username, password):
    u = db.User()
    u.username = unicode(username)
    u.mail = u'dummy@example.com'
    u.active = True
    u.set_password(password)
    u.save()
    flash("user %s created." % username)
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run()
