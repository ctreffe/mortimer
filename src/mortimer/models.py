# -*- coding: utf-8 -*-
import random
import string
import logging
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient
from cryptography.fernet import Fernet
from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from alfred3 import settings as alfred_settings
from alfred3.config import ExperimentConfig, ExperimentSecrets
from alfred3 import alfredlog

from mortimer import db, login_manager
from mortimer.utils import create_fernet

# pylint: disable=no-member


@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()


class User(db.Document, UserMixin):
    username = db.StringField(required=True, unique=True, max_length=20)
    email = db.EmailField(required=True, unique=True)
    role = db.StringField(required=True, default="user")

    encryption_key = db.BinaryField()
    password = db.StringField(required=True)
    experiments = db.ListField(db.ObjectIdField())

    alfred_user = db.StringField()
    alfred_pw = db.BinaryField()
    alfred_col = db.StringField()

    local_db_user = db.StringField()
    local_db_pw = db.BinaryField()
    local_col = db.StringField()

    settings = db.DictField(
        default={
            "logfilter": {
                "debug": False,
                "info": True,
                "warning": True,
                "error": True,
                "critical": True,
            }
        }
    )

    def get_reset_token(self, expires_sec=1800):
        # methode for creating a token for password reset
        s = Serializer(current_app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": str(self.id)}).decode("utf-8")

    @staticmethod
    def generate_encryption_key() -> bytes:
        """Generate a new fernet encryption key and encrypt it with the apps secret fernet key.
        """
        key = Fernet.generate_key()
        f = create_fernet()
        encrypted_key = f.encrypt(key)
        return encrypted_key

    @staticmethod
    def generate_password() -> bytes:
        """Generate a random password and encrypt it with the apps secret fernet key."""

        f = create_fernet()
        letters = string.ascii_lowercase
        pw_raw = "".join(random.choice(letters) for i in range(20))
        pw_enc = f.encrypt(pw_raw.encode())
        return pw_enc

    def prepare_local_db_user(self):
        user_lower = self.username.lower().replace(" ", "_")
        self.local_db_user = "localUser_{}".format(user_lower)
        self.local_col = "local_{}".format(user_lower)
        self.local_db_pw = self.generate_password()
        self.create_local_db_user()

    def create_local_db_user(self):

        f = create_fernet()
        pw_dec = f.decrypt(self.local_db_pw).decode()

        alfred_db = current_app.config["ALFRED_DB"]
        client = db.connection

        # local exp role
        rolename = "localAccess{}".format(self.local_db_user)
        res = {"db": alfred_db, "collection": self.local_col}
        act = ["find", "insert", "update"]
        priv = [{"resource": res, "actions": act}]

        client.alfred.command("createRole", rolename, privileges=priv, roles=[])

        client.alfred.command("createUser", self.local_db_user, pwd=pw_dec, roles=[rolename])

    def create_db_user(self):
        """Create a new user in the alfred database."""

        f = create_fernet()
        pw_dec = f.decrypt(self.alfred_pw).decode()

        alfred_db = current_app.config["ALFRED_DB"]
        user_lower = self.username.lower().replace(" ", "_")
        rolename = "alfredAccess_{}".format(user_lower)
        res = {"db": alfred_db, "collection": self.alfred_col}
        act = ["find", "insert", "update"]
        priv = [{"resource": res, "actions": act}]

        client = db.connection

        client.alfred.command("createRole", rolename, privileges=priv, roles=[])

        client.alfred.command("createUser", self.alfred_user, pwd=pw_dec, roles=[rolename])

    @property
    def mongo_saving_agent(self) -> dict:
        """Returns a mongo saving agent configuration dictionary, using 
        the user's own database credentials. For parsing with
        :class:`alfred3.config.ExperimentSecrets`.
        """
        f = create_fernet()
        appdb_config = current_app.config["MONGODB_SETTINGS"]
        mongo_config = {
            "use": "true",
            "host": appdb_config["host"],
            "port": str(appdb_config["port"]),
            "collection": self.alfred_col,
            "user": self.alfred_user,
            "password": f.decrypt(self.alfred_pw).decode(),
            "use_ssl": str(appdb_config.get("ssl")).lower(),
            "ca_file_path": str(appdb_config.get("ssl_ca_certs")),
            "activation_level": "1",
        }
        return {"mongo_saving_agent": mongo_config}

    @property
    def encryption_config(self) -> dict:
        """Returns a configuration dictionary with the user's encryption
        key for parsing with :class:`alfred3.config.ExperimentSecrets`.

        The key is first decrypted and then converted from bytes to 
        string.
        """
        f = create_fernet()
        encryption_config = {"key": f.decrypt(self.encryption_key).decode()}

        return {"encryption": encryption_config}

    @staticmethod
    def verify_reset_token(token):
        # verify that a token for password reset is valid
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token)["user_id"]
        except Exception:
            return None

        return User.objects.get(id=user_id)

    def __repr__(self):
        return "User(%s, %s)" % (self.username, self.email)


class WebExperiment(db.Document):
    author = db.StringField(required=True)
    author_id = db.ObjectIdField()
    title = db.StringField(required=True, unique_with="author")
    version = db.StringField(required=True)
    available_versions = db.ListField(db.StringField())
    date_created = db.DateTimeField(default=datetime.now, required=True)
    last_update = db.DateTimeField(default=datetime.now, required=True)
    description = db.StringField()

    title_from_script = db.StringField()  # Deprecated
    author_mail_from_script = db.StringField()  # Deprecated

    script = db.StringField()
    script_name = db.StringField()
    script_fullpath = db.StringField()
    path = db.StringField()  # full path to exp directory
    directory_name = db.StringField()  # name of exp directory
    user_directories = db.ListField(db.StringField())  # user-created directories

    exp_config = db.StringField()  # possibility to include config.conf
    exp_secrets = db.BinaryField()
    settings = db.DictField()

    public = db.BooleanField(default=True)
    password = db.StringField()
    web = db.BooleanField()
    active = db.BooleanField(default=False)

    def prepare_logger(self):
        """Sets the formatter and file handler for the experiment 
        logger.
        """
        formatter = alfredlog.prepare_alfred_formatter(str(self.id))
        explogger = logging.getLogger(f"exp.{str(self.id)}")

        explog = Path(self.path) / "exp.log"
        if not explogger.handlers:  # in order to prevent double or triple adding handlers
            exp_file_handler = alfredlog.prepare_file_handler(explog)
            exp_file_handler.setFormatter(formatter)

            explogger.addHandler(exp_file_handler)

    def parse_exp_config(self, session_id: str) -> ExperimentConfig:
        exp_config = ExperimentConfig(expdir=self.path)

        # parse config from mortimer
        metadata = self.metadata_config(session_id)
        exp_config.read_dict(metadata)

        return exp_config

    def parse_exp_secrets(self) -> ExperimentSecrets:
        # get secrets from user config
        f = create_fernet()
        try:
            secrets_string = f.decrypt(self.exp_secrets).decode()
        except TypeError:
            logger = logging.getLogger(__name__)
            logger.exception(
                (
                    "Exception during secrets decryption. "
                    "To proceed, the value of secrets.conf was set to an empty string."
                    f" Exp id={str(self.id)}"
                )
            )
            secrets_string = ""

        exp_secrets = ExperimentSecrets(expdir=self.path)
        exp_secrets.read_string(secrets_string)

        exp_author = User.objects.get_or_404(id=self.author_id)
        exp_secrets.read_dict(exp_author.mongo_saving_agent)
        exp_secrets.read_dict(exp_author.encryption_config)

        return exp_secrets

    def metadata_config(self, session_id: str) -> dict:
        """Returns a configuration dictionary of experiment metadata for
        parsing with :class:`alfred3.config.ExperimentConfig`.

        It also includes the boolean 'True' value for the option
        *runs_on_mortimer* in section *general*.

        The included metadata are:

        * Experiment Title
        * Experiment Author
        * Experiment ID
        * Session ID (taken from method argument)

        Args:
            session_id (str): Session ID
        """
        config = {}
        config["title"] = self.title
        config["author"] = self.author
        config["exp_id"] = str(self.id)
        config["session_id"] = session_id

        return {"metadata": config, "general": {"runs_on_mortimer": "true"}}

    def set_settings(self):
        """Set experiment settings based on self and alfred.settings.
        """
        if not self.id:
            raise AttributeError("The experiment needs to have an ID before settings can be set.")

        exp_specific_settings = alfred_settings.ExperimentSpecificSettings()

        settings = {
            "general": dict(alfred_settings.general),
            "experiment": {
                "title": self.title,
                "author": self.author,
                "version": self.version,
                "type": alfred_settings.experiment.type,
                "exp_id": str(self.id),
                "qt_fullscreen": alfred_settings.experiment.qt_full_screen,
                "web_layout": alfred_settings.experiment.web_layout,
            },
            "mortimer_specific": {"session_id": None, "path": self.path},
            "log": dict(alfred_settings.log),
            "navigation": dict(exp_specific_settings.navigation),
            "debug": dict(exp_specific_settings.debug),  # pylint: disable=no-member
            "hints": dict(exp_specific_settings.hints),
            "messages": dict(exp_specific_settings.messages),
        }

        self.settings = settings

    def __repr__(self):
        return "Experiment(Title: %s, Version: %s, Created: %s, Author: %s)" % (
            self.title,
            self.version,
            self.date_created,
            self.author,
        )


class LocalExperiment(db.Document):
    author = db.StringField(required=True)
    title = db.StringField(required=True, unique_with="author")
    version = db.StringField()
    exp_id = db.StringField(required=True, unique_with="author")
    available_versions = db.ListField(db.StringField())
    date_created = db.DateTimeField(default=datetime.utcnow, required=True)
    last_update = db.DateTimeField(default=datetime.utcnow, required=True)
    description = db.StringField()

    def __repr__(self):
        return "Local WebExperiment(Title: %s, Version: %s, Created: %s, Author: %s)" % (
            self.title,
            self.version,
            self.date_created,
            self.author,
        )
