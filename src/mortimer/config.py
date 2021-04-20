# -*- coding: utf-8 -*-
"""Provide basic configuration for mortimer.

The `BaseConfig` class can be used as a parent in order to create different sets of default configuration.
"""

import os


def configure_app(app):
    """Apply configuration to app.

    Configuration is imported from the following locations:
    1. The apps own default config.py
    2. "/etc/mortimer.conf"
    3. A "mortimer.conf" in the current users home directory
    4. A "mortimer.conf" in a path provided via an environement variable 
        MORTIMER_CONFIG
    5. A "mortimer.conf" in the instance path

    The config files are read in that order. Settings from later files 
    override previous settings.

    The implementation is extensible: It is possible to include multiple 
    configuration objects in `config.py` and utilise a switch to tell 
    mortimer, which one to use. The switch key is provided in an 
    environment variable `MORTIMER_CONFIG`. It needs to be paired with 
    the object's name in this functions dict `switch`. Currently 
    available:

    * "default" (the default)

    Args:
        app: The app, an instance of `flask.Flask`.
    """

    switch = {"default": "mortimer.config.BaseConfig"}

    config_name = os.getenv("FLASK_CONFIGURATION", "default")

    # First: Get config from source control
    app.config.from_object(switch[config_name])

    # Then: Read user-defined config files
    locations = ["/etc", os.path.expanduser("~"), os.getenv("MORTIMER_CONFIG")]
    for l in locations:
        try:
            f = os.path.join(l, "mortimer.conf")
            app.config.from_pyfile(f)
        except (FileNotFoundError, TypeError):
            pass

    # Last: Read config form instance folder config
    instance_config = os.path.join(app.instance_path, "mortimer.conf")
    try:
        app.config.from_pyfile(instance_config)
    except FileNotFoundError:
        pass


class BaseConfig:

    # Must be URL-safe base64-encoded 32-byte key for fernet encryption
    SECRET_KEY = None

    # Passphrase for account creation
    PAROLE = None

    # MONGODB_HOST = "localhost"
    # MONGODB_PORT = 27017
    # MONGODB_DB = "mortimer"
    # MONGODB_USERNAME = None
    # MONGODB_PASSWORD = None
    # MONGODB_AUTHENTICATION_SOURCE = "admin"
    # MONGODB_SSL = False
    # MONGODB_SSL_CA_CERTS = None

    # MongoDB Settings
    MONGODB_SETTINGS = {}
    MONGODB_SETTINGS["host"] = "localhost"
    MONGODB_SETTINGS["port"] = 27017
    MONGODB_SETTINGS["db"] = "mortimer"
    MONGODB_SETTINGS["username"] = None
    MONGODB_SETTINGS["password"] = None
    MONGODB_SETTINGS["authentication_source"] = "admin"
    MONGODB_SETTINGS["ssl"] = False
    MONGODB_SETTINGS["ssl_ca_certs"] = None

    # Alfred settings
    ALFRED_DB = "alfred"

    # Mail settings
    MAIL_USE = False
    MAIL_SERVER = None
    MAIL_PORT = None
    MAIL_USE_TLS = None
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_SENDER_ADDRESS = None

    # Flask-Dropzone settings:
    DROPZONE_ALLOWED_FILE_CUSTOM = True
    DROPZONE_ALLOWED_FILE_TYPE = ".pdf, image/*, .txt, .xml, .pem, .mp3, .mp4, .ogg, .csv, .py"
    DROPZONE_MAX_FILE_SIZE = 20
    DROPZONE_MAX_FILES = 5
    DROPZONE_UPLOAD_ON_CLICK = True
    DROPZONE_UPLOAD_BTN_ID = "upload"
    DROPZONE_UPLOAD_MULTIPLE = True
    DROPZONE_PARRALEL_UPLOAD = True
    DROPZONE_TIMEOUT = 300000  # 5 minutes
