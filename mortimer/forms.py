from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, \
    SelectField, FileField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Name')
    password = PasswordField('Password')

class ExperimentForm(FlaskForm):
    name = StringField('Name')
    external = BooleanField('External Experiment')
    expName = StringField('expName')
    expVersion = StringField('expVersion')
    active = BooleanField('Active')
    access_type = SelectField('Access Type', choices=[(x, x) for x in [u'public', u'password']])
    password = StringField('Password')
    config = TextAreaField('Config')
    script = TextAreaField('Script')
    # TODO external / not external required fields

class ExperimentExportForm(FlaskForm):
    format = SelectField('Format', choices=[(x,x) for x in [u'csv',
        u'excel_csv', u'json', u'excel']])
    replace_none = BooleanField('Replace none values\nnot for json')
    none_value = StringField('None value replacement')

class UploadForm(FlaskForm):
    file = FileField('Your File', [DataRequired()])

class FolderForm(FlaskForm):
    folder = StringField('Foler Name', [DataRequired()])
