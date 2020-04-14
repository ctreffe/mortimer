# -*- coding: utf-8 -*-

import os

# For security reasons (this code is public), we use a lot of environmentt variables here.
# You don't have to do the same for your installation of mortimer.
# On your secured server, you can simply input the needed information right here.


class Config:
    # If the ssl settings and the ca-file are not set manually, but via environment variables
    # this if-else-clause ensures, that the correct settings are being used.
    if os.environ.get("MONGODB_SSL") == "True":
        mongodb_ssl = True
        ssl_ca_certs = os.environ.get("MONGODB_SSL_CAFILE")
        ssl_ca_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), ssl_ca_certs
        )
    else:
        mongodb_ssl = False
        ssl_ca_certs = None
        ssl_ca_path = None

    # secret key of app (e.g. for encrypted session data)
    SECRET_KEY = os.environ.get("SECRET_KEY")
    
    # URL-safe base64-encoded 32-byte key for fernet encryption 
    FERNET_KEY = os.environ.get("FERNET_KEY")

    PAROLE = os.environ.get("PAROLE")  # Parole/Passphrase for registration
    EXP_PER_PAGE = 10  # number of experiments displayed per page

    # Mortimer database login settings
    MONGODB_SETTINGS = {
        "host": os.environ.get("MONGODB_HOST"),
        "port": int(os.environ.get("MONGODB_PORT")),
        "db": os.environ.get("MONGODB_MORTIMER_DB"),
        "username": os.environ.get("MONGODB_MORTIMER_USER"),
        "password": os.environ.get("MONGODB_MORTIMER_PW"),
        "authentication_source": os.environ.get("MONGODB_MORTIMER_AUTHDB"),
        "ssl": mongodb_ssl,  # True / False
        "ssl_ca_certs": ssl_ca_certs
        # "ssl": False,
        # "ssl_ca_certs": "mongodb_ca_file.pem"  # filepath must be relative to the directory that contains config.py and __init__.py
    }

    # Alfred database login settings
    MONGODB_ALFRED_SETTINGS = {
        "host": os.environ.get("MONGODB_HOST"),
        "port": int(os.environ.get("MONGODB_PORT")),
        "db": os.environ.get("MONGODB_ALFRED_DB"),
        "username": os.environ.get("MONGODB_ALFRED_USER"),
        "password": os.environ.get("MONGODB_ALFRED_PW"),
        "authentication_source": os.environ.get("MONGODB_ALFRED_AUTHDB"),
        "ssl": mongodb_ssl,
        "ssl_ca_certs": ssl_ca_certs
        # "ssl": False,
        # "ssl_ca_certs": "mongodb_ca_file.pem"  # filepath must be relative to the directory that contains config.py and __init__.py
    }

    # Mail settings
    MAIL_USE = True  # enable or disable password reset emails
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = os.environ.get("MAIL_PORT")
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # Flask-Dropzone settings:
    DROPZONE_ALLOWED_FILE_CUSTOM = True
    DROPZONE_ALLOWED_FILE_TYPE = (
        ".pdf, image/*, .txt, .xml, .pem, .mp3, .mp4, .ogg, .csv"
    )
    DROPZONE_MAX_FILE_SIZE = 10
    DROPZONE_MAX_FILES = 100
    DROPZONE_UPLOAD_ON_CLICK = True
    DROPZONE_UPLOAD_BTN_ID = "upload"
