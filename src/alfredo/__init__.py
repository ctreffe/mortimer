import logging

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_dropzone import Dropzone
from flask_login import LoginManager
from flask_mail import Mail
from flask_mongoengine import MongoEngine

from alfredo.config import configure_app

from ._version import __version__

# register extensions
bcrypt = Bcrypt()  # for hashing passwords
login_manager = LoginManager()  # managing login and loggout
login_manager.login_view = "users.login"  # function name of login route
login_manager.login_message_category = (
    "info"  # bootstrap class of "login necessary" message
)
mail = Mail()  # for sending password reset mails
dropzone = Dropzone()  # for multiple file upload

# databases
db = MongoEngine()  # alfredo database


# application factory
def create_app(instance_path=None, logfile: str = None):
    logger = logging.getLogger("alfredo")
    fh = logging.FileHandler(logfile)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.setLevel(logging.INFO)

    app = Flask(__name__, instance_path=instance_path)

    # apply configuration
    configure_app(app)

    # import blueprints
    from alfredo.errors.handlers import errors
    from alfredo.main.routes import main
    from alfredo.users.routes import users
    from alfredo.web_experiments.alfredo import alfredo
    from alfredo.web_experiments.routes import web_experiments

    # register blueprints
    app.register_blueprint(users)
    app.register_blueprint(web_experiments)
    app.register_blueprint(main)
    app.register_blueprint(alfredo)
    app.register_blueprint(errors)

    # global variables for use in templates
    @app.context_processor
    def version_processor():  # pylint: disable=unused-variable
        mv = __version__
        from alfred3 import __version__ as av

        return {"alfredo": mv, "alfred": av}

    # bind extensions to app instance
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    dropzone.init_app(app)

    return app
