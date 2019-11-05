#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask_mongoengine import MongoEngine
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_dropzone import Dropzone
import pymongo

# the EnvironSetter sets enviroment variables for the current session
# It is not included in the GitHub repository, because it contains sensitive
# information. We use it for easy testing. You can either write your own
# EnvironSetter, or do one of the following:
# 1) Set your environment variables directly
# 2) Set your environment variables in another file, e.g. wsgi.py (we do this on our production sever)
# 3) Set your login data directly in the config.py
try:
    from mortimer.set_environ_vars import EnvironSetter

    # set environment variables
    setter = EnvironSetter()
    setter.set_environment_variables()

except ImportError:
    print("Environment variables are not set automatically.\
     This is no problem, if you specified them manually or set the relevant data directly in your config.py.")


from mortimer.config import Config


# register extensions
bcrypt = Bcrypt()                               # for hashing passwords
login_manager = LoginManager()                  # managing login and loggout
login_manager.login_view = "users.login"        # function name of login route
login_manager.login_message_category = "info"   # bootstrap class of "login necessary" message
mail = Mail()                                   # for sending password reset mails
dropzone = Dropzone()                           # for multiple file upload

# databases
db = MongoEngine()   # mortimer database

# database for querying alfred collections
client = pymongo.MongoClient(host=Config.MONGODB_ALFRED_SETTINGS["host"],
                             port=Config.MONGODB_ALFRED_SETTINGS["port"],
                             username=Config.MONGODB_ALFRED_SETTINGS["username"],
                             password=Config.MONGODB_ALFRED_SETTINGS["password"],
                             authSource=Config.MONGODB_ALFRED_SETTINGS["authentication_source"],
                             ssl=Config.mongodb_ssl,
                             ssl_ca_certs=Config.ssl_ca_path
                             )

alfred_db = client.alfred           # checkin database
alfred_web_db = alfred_db.web       # web collection
alfred_local_db = alfred_db.local   # local collection


# application factory
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    # import blueprints
    from mortimer.users.routes import users
    from mortimer.web_experiments.routes import web_experiments
    from mortimer.web_experiments.alfredo import alfredo
    from mortimer.main.routes import main
    from mortimer.local_experiments.routes import local_experiments
    from mortimer.errors.handlers import errors

    # register blueprints
    app.register_blueprint(users)
    app.register_blueprint(web_experiments)
    app.register_blueprint(main)
    app.register_blueprint(alfredo)
    app.register_blueprint(local_experiments)
    app.register_blueprint(errors)

    # bind extensions to app instance
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    dropzone.init_app(app)

    return app
