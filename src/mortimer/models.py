# -*- coding: utf-8 -*-
import random
import string
import secrets
import logging
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient
from cryptography.fernet import Fernet
from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
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

    db_rolename = db.StringField()
    alfred_user = db.StringField()
    alfred_pw = db.BinaryField()
    alfred_col = db.StringField()
    alfred_col_unlinked = db.StringField()
    alfred_col_misc = db.StringField()
    alfred_col_detached = db.StringField()  # for bw compatibility

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

    @property
    def user_lower(self):
        return self.username.lower().replace(" ", "_")

    def get_reset_token(self, expires_sec=1800):
        # methode for creating a token for password reset
        s = Serializer(current_app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": str(self.id)}).decode("utf-8")

    @staticmethod
    def generate_encryption_key() -> bytes:
        """Generate a new fernet encryption key and encrypt it with the apps secret fernet key."""
        key = Fernet.generate_key()
        f = create_fernet()
        encrypted_key = f.encrypt(key)
        return encrypted_key

    @staticmethod
    def generate_password() -> bytes:
        """Generate a random password and encrypt it with the apps secret fernet key."""

        f = create_fernet()
        alphabet = string.ascii_letters + string.digits
        pw_raw = "".join(secrets.choice(alphabet) for i in range(20))
        pw_enc = f.encrypt(pw_raw.encode())
        return pw_enc

    def _prepare_db_role_privileges(self):
        alfred_db = current_app.config["ALFRED_DB"]
        res = {"db": alfred_db}

        c_exp = {**res, **{"collection": self.alfred_col}}
        c_unlinked = {**res, **{"collection": self.alfred_col_unlinked}}
        c_misc = {**res, **{"collection": self.alfred_col_misc}}

        act = ["find", "insert", "update"]
        priv = [{"resource": res_dict, "actions": act} for res_dict in [c_exp, c_unlinked, c_misc]]
        return priv

    def create_db_role(self):
        """Create a role in the alfred database and save its name as an
        attribute to the user model.
        """

        self.db_rolename = "alfredAccess_{}".format(self.user_lower)

        priv = self._prepare_db_role_privileges()

        alfred_db = current_app.config["ALFRED_DB"]
        client = db.connection
        client[alfred_db].command("createRole", self.db_rolename, privileges=priv, roles=[])

    def update_db_role(self):

        if not self.alfred_col:
            self.alfred_col = "col_{}".format(self.user_lower)
        if not self.alfred_col_unlinked:
            self.alfred_col_unlinked = "col_{}_unlinked".format(self.user_lower)
        if not self.alfred_col_misc:
            self.alfred_col_misc = "col_{}_misc".format(self.user_lower)
        if not self.db_rolename:
            self.db_rolename = "alfredAccess_{}".format(self.user_lower)

        alfred_db = current_app.config["ALFRED_DB"]
        client = db.connection
        priv = self._prepare_db_role_privileges()

        client[alfred_db].command("updateRole", self.db_rolename, privileges=priv, roles=[])

    def create_db_user(self):
        """Create a new user with appropriate role in the alfred database."""

        self.alfred_pw = self.generate_password()  # password is encrypted
        f = create_fernet()
        pw_dec = f.decrypt(self.alfred_pw).decode()

        alfred_db = current_app.config["ALFRED_DB"]
        client = db.connection
        client[alfred_db].command(
            "createUser", self.alfred_user, pwd=pw_dec, roles=[self.db_rolename]
        )

    def set_db_config(self):
        self.alfred_user = f"alfredUser_{self.user_lower}"
        self.alfred_col = "col_{}".format(self.user_lower)
        self.alfred_col_unlinked = "col_{}_unlinked".format(self.user_lower)
        self.alfred_col_misc = "col_{}_misc".format(self.user_lower)

        self.create_db_role()
        self.create_db_user()

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
            "misc_collection": self.alfred_col_misc,
            "user": self.alfred_user,
            "password": f.decrypt(self.alfred_pw).decode(),
            "use_ssl": str(appdb_config.get("ssl")).lower(),
            "ca_file_path": str(appdb_config.get("ssl_ca_certs")),
            "activation_level": "1",
        }
        return {"mongo_saving_agent": mongo_config}

    @property
    def mongo_saving_agent_unlinked(self) -> dict:
        mongo_agent = self.mongo_saving_agent["mongo_saving_agent"]
        mongo_agent["collection"] = self.alfred_col_unlinked
        mongo_agent["encrypt"] = "true"
        return {"mongo_saving_agent_unlinked": mongo_agent}

    @property
    def mongo_saving_agent_codebook(self) -> dict:
        mongo_agent = self.mongo_saving_agent["mongo_saving_agent"]
        mongo_agent["collection"] = self.alfred_col_misc
        return {"mongo_saving_agent_codebook": mongo_agent}

    @property
    def encryption_config(self) -> dict:
        """Returns a configuration dictionary with the user's encryption
        key for parsing with :class:`alfred3.config.ExperimentSecrets`.

        The key is first decrypted and then converted from bytes to
        string.
        """
        f = create_fernet()
        encryption_config = {"key": f.decrypt(self.encryption_key).decode(), "public_key": "false"}

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
    settings = db.DictField() # DEPRECATED

    public = db.BooleanField(default=True)
    password = db.StringField()
    web = db.BooleanField()
    active = db.BooleanField(default=False)
    urlparam = db.StringField()

    def prepare_logger(self):
        """Sets the formatter and file handler for the experiment
        logger.
        """
        formatter = alfredlog.prepare_alfred_formatter(str(self.id))
        explogger = logging.getLogger(f"exp.{str(self.id)}")
        lsa_logger = explogger.getChild("saving_agent.AutoLocalSavingAgent")
        lsa_cb_logger = explogger.getChild("saving_agent.CodebookLocalSavingAgent")

        lsa_logger.setLevel(logging.WARNING)
        lsa_cb_logger.setLevel(logging.WARNING)

        explog = Path(self.path) / "exp.log"
        if not explogger.handlers:  # in order to prevent double or triple adding handlers
            exp_file_handler = alfredlog.prepare_file_handler(explog)
            exp_file_handler.setFormatter(formatter)

            explogger.addHandler(exp_file_handler)

    def parse_exp_config(self, session_id: str) -> ExperimentConfig:
        exp_config = ExperimentConfig(expdir=self.path)

        # parse config from mortimer
        exp_config.read_dict(self.metadata_config(session_id))
        exp_config.read_string(self.exp_config)

        return exp_config

    def parse_exp_secrets(self) -> ExperimentSecrets:
        # get secrets from user config
        f = create_fernet()
        try:
            secrets_string = f.decrypt(self.exp_secrets).decode()
        except TypeError:
            logger = logging.getLogger(__name__)
            logger.info(
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
        exp_secrets.read_dict(exp_author.encryption_config)
        exp_secrets.read_dict(exp_author.mongo_saving_agent)
        exp_secrets.read_dict(exp_author.mongo_saving_agent_unlinked)
        exp_secrets.read_dict(exp_author.mongo_saving_agent_codebook)

        return exp_secrets

    def parse_encryption_key(self):

        f = create_fernet()
        exp_author = User.objects.get_or_404(id=self.author_id)
        key = f.decrypt(exp_author.encryption_key).decode()

        encryption_config = {"encryption": {"key": key, "public_key": "false"}}

        return encryption_config

    def metadata_config(self, session_id: str) -> dict:
        """Returns a configuration dictionary of experiment metadata for
        parsing with :class:`alfred3.config.ExperimentConfig`.

        It also includes the boolean 'True' value for the option
        *runs_on_mortimer* in section *mortimer_specific*.

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
        config["version"] = self.version

        return {"metadata": config, "mortimer_specific": {"runs_on_mortimer": "true"}}


    def __repr__(self):
        return "Experiment(Title: %s, Version: %s, Created: %s, Author: %s)" % (
            self.title,
            self.version,
            self.date_created,
            self.author,
        )

class Participant(db.Document):
    alias = db.StringField(required=True, unique=True)
    experiments = db.DictField()
