# -*- coding:utf-8 -*-

from flask import current_app
from flask.ext.login import UserMixin
from flask.ext.mongokit import Document
from mongokit import IS
from bson.objectid import ObjectId

class User(Document, UserMixin):
    __collection__ = 'users'
    #__database__ = 'mortimer'
    use_dot_notation = True
    structure = {
        'username': unicode,
        'mail': unicode,
        'password_hash': unicode,
        'active': bool,
        'admin': bool
    }
    required_fields = ['username', 'mail', 'password_hash', 'active']
    default_values = {'admin': False}

    def is_active(self):
        return self.active

    def get_id(self):
        return str(self._id)

    def set_password(self, password):
        self.password_hash = unicode(current_app.bcrypt.generate_password_hash(password))

    def validate_password(self, password):
        return current_app.bcrypt.check_password_hash(self.password_hash, password)

    def __unicode__(self):
        return u"User<name: %s>" % self.username
    def __str__(self):
        return self.__unicode__().encode('utf-8')


class Experiment(Document):
    __collection__ = 'experiments'
    #__database__ = 'mortimer'
    use_dot_notation = True

    structure = {
        'name': unicode,
        'owner': ObjectId,
        'active': bool,
        'access_type': IS(u'public', u'password'),
        'password': unicode,
        'config': unicode,
        'script': unicode,
        'expName': unicode,
        'expVersion': unicode,
        'external': bool
    }
    required_fields = ['name', 'owner', 'external']
    #TODO requrements

    def __unicode__(self):
        return u'Experiment<name: %s>' % self.name
    def __str__(self):
        return self.__unicode__().encode('utf-8')
