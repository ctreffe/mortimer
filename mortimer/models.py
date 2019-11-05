#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import current_app
from mortimer import db, login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()


class User(db.Document, UserMixin):
    username = db.StringField(required=True, unique=True, max_length=20)
    email = db.EmailField(required=True, unique=True)
    role = db.StringField(required=True, default="user")
    password = db.StringField(required=True)
    experiments = db.ListField(db.ObjectIdField())

    def get_reset_token(self, expires_sec=1800):
        # methode for creating a token for password reset
        s = Serializer(current_app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": str(self.id)}).decode("utf-8")

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
    title = db.StringField(required=True, unique_with="author")
    version = db.StringField(required=True)
    available_versions = db.ListField(db.StringField())
    date_created = db.DateTimeField(default=datetime.utcnow, required=True)
    last_update = db.DateTimeField(default=datetime.utcnow, required=True)
    description = db.StringField()

    title_from_script = db.StringField()
    author_mail_from_script = db.StringField()

    script = db.StringField()
    script_name = db.StringField()
    script_fullpath = db.StringField()
    path = db.StringField()     # full path to exp directory
    directory_name = db.StringField()   # name of exp directory
    user_directories = db.ListField(db.StringField())   # user-created directories
    config = db.StringField()   # possibility to include config.conf

    public = db.BooleanField(default=True)
    password = db.StringField()
    web = db.BooleanField()
    active = db.BooleanField(default=False)

    def __repr__(self):
        return "Experiment(Title: %s, Version: %s, Created: %s, Author: %s)" % (self.title, self.version, self.date_created, self.author)


class LocalExperiment(db.Document):
    author = db.StringField(required=True)
    title = db.StringField(required=True, unique_with="author")
    version = db.StringField(unique_with="title")
    available_versions = db.ListField(db.StringField())
    date_created = db.DateTimeField(default=datetime.utcnow, required=True)
    last_update = db.DateTimeField(default=datetime.utcnow, required=True)
    description = db.StringField()

    def __repr__(self):
        return "Local WebExperiment(Title: %s, Version: %s, Created: %s, Author: %s)" % (self.title, self.version, self.date_created, self.author)
