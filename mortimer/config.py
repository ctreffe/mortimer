import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    MONGODB_HOST = os.environ.get("MONGODB_HOST")
    MONGODB_ALFRED = os.environ.get("MONGODB_ALFRED")
    # abt5.psych.bio.uni-goettinggen.de:49130
    # MONGODB_DB = 'mortimer'
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

    PAROLE = os.environ.get("PAROLE")
    EXP_PER_PAGE = 10
