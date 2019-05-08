import os
from flask import current_app


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")  # secret key of flask app (e.g. for encrypted session data)
    PAROLE = os.environ.get("PAROLE")       # Parole/Passphrase for registration
    EXP_PER_PAGE = 10                       # number of experiments displayed per page

    # Mortimer database login settings
    MONGODB_SETTINGS = {
        "host": os.environ.get("MONGODB_HOST"),
        "port": os.environ.get("MONGODB_PORT"),

        "db": os.environ.get("MONGODB_MORTIMER_DB"),
        "username": os.environ.get("MONGODB_MORTIMER_USER"),
        "password": os.environ.get("MONGODB_MORTIMER_PW"),
        "authentication_source": os.environ.get("MONGODB_MORTIMER_AUTHDB"),

        "ssl": False,
        "ssl_ca_certs": os.path.join(current_app.root_path, "mongodb_ca_file.pem")
    }

    # Alfred database login settings
    MONGODB_ALFRED_SETTINGS = {
        "host": os.environ.get("MONGODB_HOST"),
        "port": os.environ.get("MONGODB_PORT"),

        "db": os.environ.get("MONGODB_ALFRED_DB"),
        "username": os.environ.get("MONGODB_ALFRED_USER"),
        "password": os.environ.get("MONGODB_ALFRED_PW"),
        "authentication_source": os.environ.get("MONGODB_ALFRED_AUTHDB"),

        "ssl": False,
        "ssl_ca_certs": os.path.join(current_app.root_path, "mongodb_ca_file.pem")
    }

    # Mail settings
    MAIL_USE = True     # enable or disable password reset emails
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = os.environ.get("MAIL_PORT")
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # Flask-Dropzone config:
    # DROPZONE_ALLOWED_FILE_TYPE = 'image',
    DROPZONE_MAX_FILE_SIZE = 300
    DROPZONE_MAX_FILES = 100
    DROPZONE_UPLOAD_ON_CLICK = True
    DROPZONE_UPLOAD_BTN_ID = 'upload'

    # Mortimer settings
