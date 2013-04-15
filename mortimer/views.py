# -*- coding:utf-8 -*-
import os
import imp

from flask import abort, redirect, url_for, request, render_template, flash,\
    escape, g, current_app, _app_ctx_stack, send_file
from flask.views import View, MethodView
from flask.ext.login import current_user, login_required, login_user, logout_user

from .forms import *
from .models import *
from . import export

class LoginView(View):
    methods = ['GET', 'POST']
    def dispatch_request(self):
        form = LoginForm()
        if form.validate_on_submit():
            user = current_app.db.User.find_one({'username': form.username.data})
            if user is not None and user.validate_password(form.password.data) and login_user(user):
                return redirect(request.args.get("next") or url_for("index"))
        return render_template('login.html', form=form)

class LogoutView(View):
    def dispatch_request(self):
        logout_user()
        flash("Logged out")
        return redirect(url_for('index'))

class IndexView(View):
    def dispatch_request(self):
        return render_template('index.html')

# Neues Experiment erstellen/Experiment Verändern
# Experiment übersicht
# Experimentdaten exportieren
# Übersicht über aktive öffentliche Experimente

# Experiment
#   - starten (mit passwort eingabe)
#   - dynamic und static files
#   - callables

class ExperimentView(View):
    decorators = [login_required]
    def dispatch_request(self, id):
        experiment = current_app.db.Experiment.get_or_404(id)
        res = current_app.alfred_col.aggregate([
            {'$match': {'expName': 'test_test', 'expVersion': '1'}},
            {'$project': {'expFinished': 1}},
            {'$group': {'_id': '$expFinished', 'count' : {'$sum' : 1}}}
        ])['result']
        total_count = 0
        finished_count = 0
        for v in res:
            total_count += v['count']
            if v['_id'] == True:
                finished_count = v['count']



        return render_template('experiment.html', experiment=experiment,
                total_count=total_count, finished_count=finished_count)

class ExperimentDeleteView(View):
    decorators = [login_required]
    def dispatch_request(self, id):
        experiment = current_app.db.Experiment.get_or_404(id)
        if experiment.owner != current_user.get_id():
            abort(403)
        experiment.collection.remove({'_id': experiment._id})
        flash('Experiment %s was deleted.' % experiment.name)
        return redirect('experiments')

    
class ExperimentEditView(MethodView):
    decorators = [login_required]
    def post(self, id):
        form = ExperimentForm()
        if id is not None:
            experiment = current_app.db.Experiment.get_or_404(id)
            if experiment.owner != current_user.get_id():
                abort(403)
        else:
            experiment = current_app.db.Experiment()
        if form.validate_on_submit():
            experiment.owner = current_user.get_id()
            experiment.name = form.name.data
            experiment.active = form.active.data
            experiment.access_type = form.access_type.data
            experiment.password = form.password.data
            experiment.config = form.config.data
            experiment.script = form.script.data

            experiment.save()

            # save experiment module
            with current_app.open_instance_resource(os.path.join(
                    current_app.config['SCRIPT_FOLDER'],
                    str(experiment._id) + '.py'), 'w') as f:
                f.write('# -*- coding:utf-8 -*-\n')
                f.write(experiment.script.encode('utf-8'))

            f, pathname, desc = imp.find_module(str(experiment._id), 
                [os.path.join(current_app.instance_path,
                current_app.config['SCRIPT_FOLDER'])]
            )
            try:
                module = imp.load_module(str(experiment._id), f, pathname, desc)
            finally:
                f.close()
            script = module.Script()
            script.experiment = script.generate_experiment()
            experiment.expName = unicode(script.experiment.name)
            experiment.expVersion = unicode(script.experiment.version)

            experiment.save()

            return redirect(url_for('experiment', id=experiment._id))
        else:
            return render_template('experiment_form.html', form=form)
    def get(self, id):
        form = ExperimentForm()
        if id is not None:
            experiment = current_app.db.Experiment.get_or_404(id)
            if experiment.owner != current_user.get_id():
                abort(403)
            form.name.data = experiment.name
            form.active.data = experiment.active
            form.access_type.data = experiment.access_type
            form.password.data = experiment.password
            form.config.data = experiment.config
            form.script.data = experiment.script
            #TODO load exp form id
        return render_template('experiment_form.html', form=form)

class ExperimentListView(View):
    decorators = [login_required]
    def dispatch_request(self):
        experiments = current_app.db.Experiment.find({'owner': current_user.get_id()})
        return render_template('experiment_list.html', experiments=experiments)

class ExperimentExportView(View):
    decorators = [login_required]
    methods = ['GET', 'POST']
    def dispatch_request(self, id):
        experiment = current_app.db.Experiment.get_or_404(id)
        form = ExperimentExportForm()

        if form.validate_on_submit():
            cur = current_app.alfred_col.find({'expName': experiment.expName,
                'expVersion': experiment.expVersion})
            
            none_value = None
            if form.replace_none.data:
                none_value = form.none_value.data

            if form.format.data == 'json':
                f = export.to_json(cur)
                return send_file(f, mimetype='application/json',
                    as_attachment=True, attachment_filename='export.json', cache_timeout=0)
            elif form.format.data == 'csv':
                f = export.to_csv(cur, none_value=none_value)
                return send_file(f, mimetype='text/csv',
                    as_attachment=True, attachment_filename='export.csv', cache_timeout=0)
            elif form.format.data == 'excel_csv':
                f = export.to_excel_csv(cur, none_value=none_value)
                return send_file(f, mimetype='text/csv',
                    as_attachment=True, attachment_filename='export.csv', cache_timeout=0)


        return render_template('experiment_export.html', experiment=experiment,
                form=form)

class FooView(View):
    def dispatch_request(self):
        return 'Foobar'
