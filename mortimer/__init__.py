from flask import Flask
from flask_mongoengine import MongoEngine
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_dropzone import Dropzone
from mortimer.config import Config
import pymongo


db = MongoEngine()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "users.login"  # function name of login route
login_manager.login_message_category = "info"  # bootstrap class of "login necessary" message

client = pymongo.MongoClient(Config.MONGODB_ALFRED)
alfred_db = client.alfred
alfred_web_db = alfred_db.web
alfred_local_db = alfred_db.local

mail = Mail()

dropzone = Dropzone()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    from mortimer.users.routes import users
    from mortimer.web_experiments.routes import web_experiments
    from mortimer.web_experiments.alfredo import alfredo
    from mortimer.main.routes import main
    from mortimer.local_experiments.routes import local_experiments

    app.register_blueprint(users)
    app.register_blueprint(web_experiments)
    app.register_blueprint(main)
    app.register_blueprint(alfredo)
    app.register_blueprint(local_experiments)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    dropzone.init_app(app)

    return app
