
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template
from flask_wtf.csrf import CSRFError

errors = Blueprint("erros", __name__)


@errors.app_errorhandler(400)
def error_400(error):
    return render_template("errors/400.html"), 400


@errors.app_errorhandler(403)
def error_403(error):
    return render_template('errors/403.html'), 403


@errors.app_errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404


@errors.app_errorhandler(500)
def error_500(error):
    return render_template('errors/500_alfred.html'), 500


# handle CSRF error
@errors.app_errorhandler(CSRFError)
def csrf_error(e):
    return e.description, 400