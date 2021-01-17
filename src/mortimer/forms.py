# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import (
    StringField,
    SubmitField,
    BooleanField,
    PasswordField,
    TextAreaField,
    SelectField,
    SelectMultipleField,
    RadioField,
)
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from mortimer.models import User, WebExperiment
from flask import current_app
import re

# pylint: disable=no-member


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    parole = PasswordField("Parole", validators=[DataRequired()])

    # functions for validation of user input
    # return errors if user tries to register username or email
    # that is already in use.
    def validate_username(self, username):
        user = User.objects(username__exact=username.data).first()
        if user is not None:
            raise ValidationError("That username is taken. Please choose a different one.")

    def validate_email(self, email):
        user = User.objects(email__exact=email.data).first()
        if user is not None:
            raise ValidationError("That email is taken. Please choose a different one.")

    def validate_parole(self, parole):
        if parole.data != current_app.config["PAROLE"]:
            raise ValidationError(
                "Incorrect parole. You can write to alfred@psych.uni-goettingen.de to get the correct parole."
            )

    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")

    submit = SubmitField("Login")


class UpdateAccountForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])

    # functions for validation of user input
    # return errors if user tries to register username or email
    # that is already in use.
    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.objects(username__exact=username.data).first()
            if user is not None:
                raise ValidationError("That username is taken. Please choose a different one.")

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.objects(email__exact=email.data).first()
            if user is not None:
                raise ValidationError("That email is taken. Please choose a different one.")

    submit = SubmitField("Update")


class WebExperimentForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    version = StringField("Version", validators=[DataRequired()])
    description = TextAreaField("Description")
    password = StringField("Password")
    script = FileField("script.py", validators=[FileAllowed(["py"])])

    def validate_title(self, title):
        experiment = WebExperiment.objects(
            title__exact=title.data, author__exact=current_user.username
        ).first()
        if experiment is not None:
            raise ValidationError(
                "You already have a web experiment with this title. Please choose a unique title."
            )

    def validate_script(self, script):
        if script.data is not None and not re.match("script.py", script.data.filename):
            raise ValidationError("Your script file needs to be called 'script.py'.")

    def validate_version(self, version):
        try:
            int(version.data.replace(".", ""))
        except Exception:
            raise ValidationError(
                "Please use only points and digits for the version number. Example: '1.3.2'"
            )

    submit = SubmitField("Create")


class ExperimentScriptForm(FlaskForm):
    script = TextAreaField("Script")
    version = StringField("Updated version", validators=[DataRequired()])

    def validate_version(self, version):
        try:
            int(version.data.replace(".", ""))
        except Exception:
            raise ValidationError(
                "Please use only points and digits for the version number. Example: '1.3.2'"
            )

    submit = SubmitField("Save")


class FuturizeScriptForm(FlaskForm):
    script = TextAreaField("Script", validators=[DataRequired()])
    submit = SubmitField("Futurize")


class NewScriptForm(FlaskForm):
    script = FileField("Update script.py", validators=[FileAllowed(["py"])])
    version = StringField("Updated version", validators=[DataRequired()])

    def validate_script(self, script):
        if script.data is not None and not re.match("script.py", script.data.filename):
            raise ValidationError("Your script file needs to be called 'script.py'.")

    def validate_version(self, version):
        try:
            int(version.data.replace(".", ""))
        except Exception:
            raise ValidationError(
                "Please use only points and digits for the version number. Example: '1.3.2'"
            )

    submit = SubmitField("Update Script")


class NewExperimentVersionForm(FlaskForm):
    updated_version = StringField("Updated Version Number", validators=[DataRequired()])
    changes = TextAreaField("Change Note", validators=[DataRequired()])
    script = FileField("script.py", validators=[FileAllowed(["py"])])

    def validate_updated_version(self, updated_version):
        try:
            int(updated_version.data.replace(".", ""))
        except Exception:
            raise ValidationError(
                "Please use only points and digits for the version number. Example: '1.3.2'"
            )

    def validate_script(self, script):
        if script.data is not None and not re.match("script.py", script.data.filename):
            raise ValidationError("Your script file needs to be called 'script.py'.")

    submit = SubmitField("Add New Version")


class RequestResetForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        user = User.objects(email__exact=email.data).first()
        if user is None:
            raise ValidationError("There is no account with that email.")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("password")]
    )

    submit = SubmitField("Reset Password")


class ExportCodebookForm(FlaskForm):
    choices = [
        ("csv1", "csv ( , )"),
        ("csv2", "csv ( ; )"),
        ("json", "json"),
    ]
    file_type = RadioField(default="csv2", choices=choices, validators=[DataRequired()])
    version = SelectField("Version", validators=[DataRequired()], default="latest")


class ExportExpDataForm(FlaskForm):
    choices = [
        ("csv1", "csv ( , )"),
        ("csv2", "csv ( ; )"),
        ("json", "json"),
    ]
    file_type = RadioField(default="csv2", choices=choices, validators=[DataRequired()])
    data_type = RadioField(
        default="exp_data",
        choices=[("exp_data", "Experiment Data"), ("unlinked", "Unlinked Data")],
        validators=[DataRequired()],
    )
    version = SelectMultipleField("Version", validators=[DataRequired()])
    submit = SubmitField("Export Experiment Data")


class ExperimentExportForm(FlaskForm):

    file_type = SelectField(
        "File Type", choices=[(x, x) for x in ["csv", "excel_csv", "json", "excel"]]
    )
    version = SelectMultipleField("Version", validators=[DataRequired()])
    # replace_none = BooleanField('Replace none values\nnot for json')
    replace_none_with_empty_string = BooleanField(
        'Replace "None" values with empty string (recommended for R users).'
    )
    none_value = StringField('Replace "None" values with custom string:')

    submit = SubmitField("Download")


class FilterLogForm(FlaskForm):
    debug = BooleanField(label="debug")
    info = BooleanField(label="info")
    warning = BooleanField(label="warning")
    error = BooleanField(label="error")
    critical = BooleanField(label="critical")

    display_range = SelectField(label="Display Range")

    submit = SubmitField(label="Apply Filter")


class ExperimentConfigForm(FlaskForm):
    # general
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description")
    password = StringField("Password")

    exp_config = TextAreaField("config.conf")
    exp_secrets = TextAreaField("secrets.conf")

    submit = SubmitField("Save")


class ExperimentConfigurationForm(FlaskForm):
    # general
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description")
    password = StringField("Password")
    debug = BooleanField("Debug mode")

    # navigation
    forward = StringField("Forward", validators=[DataRequired()])
    backward = StringField("Backward", validators=[DataRequired()])
    finish = StringField("Finish", validators=[DataRequired()])

    # no input hints
    no_inputTextEntryElement = StringField("TextEntryElement")
    no_inputTextAreaElement = StringField("TextAreaElement")
    no_inputRegEntryElement = StringField("RegEntryElement")
    no_inputNumberEntryElement = StringField("NumberEntryElement")
    no_inputPasswordElement = StringField("PasswordElement")
    no_inputLikertMatrix = StringField("LikertMatrix")
    no_inputLikertElement = StringField("LikertElement")
    no_inputSingleChoiceElement = StringField("SingleChoiceElement")
    no_inputMultipleChoiceElement = StringField("MultipleChoiceElement")
    no_inputWebLikertImageElement = StringField("WebLikertImageElement")
    no_inputLikertListElement = StringField("LikertListElement")

    # wrong input hints
    corrective_RegEntry = StringField("RegEntryElement")
    corrective_NumberEntry = StringField("NumberEntryElement")
    corrective_Password = StringField("PasswordElement")

    # messages
    minimum_display_time = StringField("Minimum display time")

    submit = SubmitField("Save")
