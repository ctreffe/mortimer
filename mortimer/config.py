import os


class Config:
    # secret key of flask app (e.g. for encrypted session data)
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Mortimer database login settings
    # MONGODB_HOST = os.environ.get("MONGODB_HOST")     # Could also just use URI string
    MONGODB_SETTINGS = {
        "host": "134.76.19.150",
        "port": 49130,
        "db": "mortimer",
        "username": "jobrachem",
        "password": "brachpass",
        "authentication_source": "admin",
        "ssl": True,
        "ssl_ca_certs": "/Users/jobrachem/Documents/_Diverses/tech_tests/pymongo_test/CA_server_public.pem"
    }

    # Alfred database login settings
    MONGODB_ALFRED_HOST = "134.76.19.150"
    MONGODB_ALFRED_PORT = 49130
    MONGODB_ALFRED_USER = "jobrachem"
    MONGODB_ALFRED_PW = "brachpass"
    MONGODB_ALFRED_AUTHSOURCE = "admin"
    MONGODB_ALFRED_USE_SSL = True
    MONGODB_ALFRED_CA_CERTS = "/Users/jobrachem/Documents/_Diverses/tech_tests/pymongo_test/CA_server_public.pem"

    # Mail settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = 587
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
    PAROLE = os.environ.get("PAROLE")       # Parole for registration
    EXP_PER_PAGE = 10                       # number of experiments displayed per page
