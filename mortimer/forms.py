from flask.ext.wtf import Form
from wtforms import TextField, PasswordField, BooleanField, TextAreaField, SelectField

class LoginForm(Form):
    username = TextField('Name')
    password = PasswordField('Password')

class ExperimentForm(Form):
    name = TextField('Name')
    active = BooleanField('Active')
    access_type = SelectField('Access Type', choices=[(x, x) for x in [u'public', u'password']])
    password = TextField('Password')
    config = TextAreaField('Config')
    script = TextAreaField('Script')

class ExperimentExportForm(Form):
    format = SelectField('Format', choices=[(x,x) for x in [u'csv', u'excel_csv', u'json']])
    replace_none = BooleanField('Replace none values\nnot for json')
    none_value = TextField('None value replacement')
