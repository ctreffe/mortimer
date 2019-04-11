from flask import Flask
from flask_mongoengine import MongoEngine
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_dropzone import Dropzone
from mortimer.config import Config
import pymongo

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
client = pymongo.MongoClient(host=Config.MONGODB_ALFRED_HOST,
                             port=Config.MONGODB_ALFRED_PORT,
                             username=Config.MONGODB_ALFRED_USER,
                             password=Config.MONGODB_ALFRED_PW,
                             authSource=Config.MONGODB_ALFRED_AUTHSOURCE,
                             ssl=Config.MONGODB_ALFRED_USE_SSL,
                             ssl_ca_certs=Config.MONGODB_ALFRED_CA_CERTS)
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
