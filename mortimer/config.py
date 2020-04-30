# -*- coding: utf-8 -*-
"""Provide cofiguration settings for mortimer.
Apply configuration to app.

Configuration is imported from the following locations:
1. The apps own default config.py
2. "/etc/mortimer.conf"
3. A "mortimer.conf" in the current users home directory
4. A "mortimer.conf" in a path provided via an environement variable MORTIMER_CONFIG

The config files are read in that order. Settings from later files override previous settings,
"""

import os
from configparser import ConfigParser
from pathlib import Path

parser = ConfigParser()

# read in default config first
parent = Path(__file__).resolve().parent
with open(os.path.join(parent, "mortimer.conf")) as f:
    parser.read_file(f)

# now look in other locations and read them
locations = ["/etc", os.path.expanduser("~"), os.getenv("MORTIMER_CONFIG")]
for l in locations:
    try:
        f = os.path.join(l, "mortimer.conf")
        parser.read(f)
    except (FileNotFoundError, TypeError):
        pass

# add to Config object for flask
class Config:
    
    # Must be URL-safe base64-encoded 32-byte key for fernet encryption
    SECRET_KEY = parser.get("mortimer", "secret_key")

    # Passphrase for account creation
    PAROLE = parser.get("mortimer", "parole")

    # MongoDB Settings
    MONGODB_SETTINGS = {}
    MONGODB_SETTINGS["host"] = parser.get("mongodb", "host")
    MONGODB_SETTINGS["port"] = parser.getint("mongodb", "port")
    MONGODB_SETTINGS["db"] = parser.get("mongodb", "mortimer_db")
    MONGODB_SETTINGS["username"] = parser.get("mongodb", "username")
    MONGODB_SETTINGS["password"] = parser.get("mongodb", "password")
    MONGODB_SETTINGS["authentication_source"] = parser.get("mongodb", "auth_source")
    MONGODB_SETTINGS["ssl"] = parser.getboolean("mongodb", "ssl")
    MONGODB_SETTINGS["ssl_ca_certs"] = parser.get("mongodb", "ssl_ca_certs", fallback=None)
    
    # Name of alfred database
    ALFRED_DB = parser.get("mongodb", "alfred_db")

    # Mail settings
    MAIL_USE = parser.get("mail", "mail_use")
    MAIL_SERVER = parser.get("mail", "server")
    MAIL_PORT = parser.get("mail", "port")
    MAIL_USE_TLS = parser.get("mail", "use_tls")
    MAIL_USERNAME = parser.get("mail", "username")
    MAIL_PASSWORD = parser.get("mail", "password")

    # Flask-Dropzone settings:
    DROPZONE_ALLOWED_FILE_CUSTOM = parser.getboolean("dropzone", "allowed_file_custom")
    DROPZONE_ALLOWED_FILE_TYPE = parser.get("dropzone", "allowed_file_type")
    DROPZONE_MAX_FILE_SIZE = parser.getint("dropzone", "max_file_size")
    DROPZONE_MAX_FILES = parser.getint("dropzone", "max_files")
    DROPZONE_UPLOAD_ON_CLICK = parser.getboolean("dropzone", "upload_on_click")
    DROPZONE_UPLOAD_BTN_ID = parser.get("dropzone", "upload_btn_id")
    DROPZONE_UPLOAD_MULTIPLE = parser.getboolean("dropzone", "upload_multiple")
    DROPZONE_PARRALEL_UPLOAD = parser.getint("dropzone", "parallel_upload")
    DROPZONE_TIMEOUT = parser.getint("dropzone", "timeout")
