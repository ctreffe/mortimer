from flask.ext.wtf import Form
from wtforms import TextField, PasswordField, BooleanField, TextAreaField, \
    SelectField, FileField
from wtforms.validators import Required

class LoginForm(Form):
    username = TextField('Name')
    password = PasswordField('Password')

class ExperimentForm(Form):
    name = TextField('Name')
    external = BooleanField('External Experiment')
    expName = TextField('expName')
    expVersion = TextField('expVersion')
    active = BooleanField('Active')
    access_type = SelectField('Access Type', choices=[(x, x) for x in [u'public', u'password']])
    password = TextField('Password')
    config = TextAreaField('Config')
    script = TextAreaField('Script')
    # TODO external / not external required fields

class ExperimentExportForm(Form):
    format = SelectField('Format', choices=[(x,x) for x in [u'csv',
        u'excel_csv', u'json', u'excel']])
    replace_none = BooleanField('Replace none values\nnot for json')
    none_value = TextField('None value replacement')

class UploadForm(Form):
    file = FileField('Your File', [Required()])

class FolderForm(Form):
    folder = TextField('Foler Name', [Required()])
