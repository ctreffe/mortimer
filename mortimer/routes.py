from flask import render_template, url_for, flash, redirect, request, abort, current_app
from mortimer import bcrypt
from mortimer.forms import RegistrationForm, LoginForm, UpdateAccountForm, WebExperimentForm, RequestResetForm, ResetPasswordForm, NewExperimentVersionForm, UpdateExperimentForm
from mortimer.models import User, Experiment, ExperimentVersion
from mortimer.utils import save_file, create_filepath, send_reset_email, display_directory, filter_directories
from flask_login import login_user, current_user, logout_user, login_required
import os
from werkzeug.utils import secure_filename
import shutil


@app.errorhandler(403)
def page_not_found(e):
    return "Error 403: Forbidden"
