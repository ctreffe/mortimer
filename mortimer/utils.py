
# -*- coding: utf-8 -*-

import os
import subprocess
import json
import re
from datetime import datetime
from flask import current_app
from mortimer import mail
from flask_mail import Message
from flask import url_for, current_app, render_template
from uuid import uuid4
from jinja2 import Template
from cryptography.fernet import Fernet

def create_fernet():
    app_fernet_key = current_app.config["FERNET_KEY"].encode()
    return Fernet(app_fernet_key)


def set_experiment_settings(title, version, author, exp_id, path):
    from alfred import settings
    exp_specific_settings = settings.ExperimentSpecificSettings()

    settings = {
        'general': dict(settings.general),

        'experiment': {
            'title': title, 
            'author': author, 
            'version': version, 
            'type': settings.experiment.type, 
            'exp_id': exp_id,
            'qt_fullscreen': settings.experiment.qt_full_screen,
            'web_layout': settings.experiment.web_layout            
            },

        'mortimer_specific': {'session_id': None, 'path': path},
        'log': dict(settings.log),
        'navigation': dict(exp_specific_settings.navigation),
        'debug': dict(exp_specific_settings.debug),
        'hints': dict(exp_specific_settings.hints),
        'messages': dict(exp_specific_settings.messages)
        }

    return settings


def send_reset_email(user: str):
    token = user.get_reset_token()
    msg = Message("Password Reset Request",
                  sender="mortimer.test1@gmail.com",
                  recipients=[user.email])
    msg.body = Template(''' Dear Mortimer user,

a request to reset your password was made for your email address.

To reset your password, visit the following link:
{{ URL }}

If you did not make this request, you can simply ignore this email and no changes will be made.

Kind regards,
The Mortimer Team
                        ''', lstrip_blocks=True).render(URL=url_for('users.reset_password', token=token, _external=True))

    mail.send(msg)


def display_directory(directories: list, parent_directory: str,
                      experiment) ->str:
    """
    This is a recursive function. The endpoint is reached if it is called on
    a list that contains a single directory without subdirectories.

    :param list directories: List of directories that shall be displayed.

    :param str parent_directory: **Full** path to the directory holding the
    directories in the list `directories`.

    :param int call_id: Each time, the function is called on a new directory
    level, the call ID gets increased. This information gets passed to the
    helper function display_directory_controls(). This way we can handle the
    case if two subdirectories in different top foldern have the same name.
    """

    call_id = str(uuid4())

    experiment_title = experiment.title
    experiment_author = experiment.author

    # Get to path relative to user/experiments/experiment_title
    if parent_directory == experiment.path:
        relative_path = ""
    else:
        prefix = os.path.commonprefix([parent_directory, experiment.path])
        relative_path = parent_directory.replace(prefix, "")
        full_path = os.path.join(experiment.path, relative_path)

    # --- HELPER FUNCTIONS --- #

    def display_files(file_list: list, path: str,
                      experiment_title: str, experiment_author: str) ->str:
        """
        This function generates html code to display the files in a directory.
        :param list file_list: List of files in a directory.
        """
        out = []
        for f in file_list:
            if f == ".DS_Store":
                continue
            filepath = os.path.join(path, f)
            url = url_for('web_experiments.delete_file',
                          experiment_title=experiment_title,
                          username=experiment_author,
                          relative_path=filepath)
            fileid = "{}_{}".format(f.replace(".", ""), str(uuid4()))
            single_file = render_template("additional/display_one_file.html", f=f, fileid=fileid, url=url)
            out.append(single_file)
        return "".join(out)

    def display_directory_controls(directory: str,
                                   path: str,
                                   experiment_title: str,
                                   experiment_author: str,
                                   file_display: str,
                                   subdirectory_display: str) ->str:

        call_id = str(uuid4())

        upload_url = url_for('web_experiments.upload_resources',
                             experiment_title=experiment_title,
                             username=experiment_author,
                             relative_path=path)
        new_subdirectory_url = url_for(
            'web_experiments.new_directory',
            experiment_title=experiment_title,
            username=experiment_author,
            relative_path=path)
        delete_directory_url = url_for('web_experiments.delete_directory',
                                       experiment_title=experiment_title,
                                       username=experiment_author,
                                       relative_path=path)

        return render_template("additional/display_dir_controls.html", path=path,
                          directory=directory,
                          upload_url=upload_url,
                          call_id=call_id,
                          new_subdirectory_url=new_subdirectory_url,
                          file_display=file_display,
                          subdirectory_display=subdirectory_display,
                          delete_directory_url=delete_directory_url
                          )

    if not directories:
        return ''

    # --- LEN == 1 FUNCTION CALL --- #
    # If the Input to the function is a single directory,
    # the code below will be executed
    if len(directories) == 1:

        # Get directory path
        path = os.path.join(relative_path, directories[0])
        full_path = os.path.join(experiment.path, path)

        # find out, which elements of directory are files and
        # which are subdirectories
        subdirectory_list = []
        file_list = []

        for filename in sorted(os.listdir(full_path)):
            if os.path.isdir(os.path.join(full_path, filename)):
                subdirectory_list.append(filename)
            else:
                file_list.append(filename)

        # Create html code for file display
        if file_list:
            single_files = display_files(
                file_list=file_list,
                path=path,
                experiment_title=experiment_title,
                experiment_author=experiment_author)
        else:
            single_files = ""

        # Create html code for display of subdirectories.
        # The function is called again.
        if subdirectory_list != []:
            subdirectory_display = display_directory(
                directories=subdirectory_list,
                experiment=experiment,
                parent_directory=path)
        else:
            subdirectory_display = ""

        # return the full html code for a single directory
        if parent_directory == experiment.path:
            div_open = "<div class=\"content-section\">"
            div_close = "</div>"
        else:
            div_open = ""
            div_close = ""

        return div_open + display_directory_controls(
            directory=directories[0],
            path=path,
            experiment_title=experiment_title,
            experiment_author=experiment_author,
            file_display=single_files,
            subdirectory_display=subdirectory_display) + div_close

    # --- USUAL FUNCTION CALL --- #
    # The code below will be executed, if the function was called
    # on a list of multiple directories. First, the list is split
    # into one list containing the first directory
    # and another list containing the remaining directories.
    # The function is then called on both lists, resulting in a
    # len(directories) == 1 function-call for the first directory
    # and another usual all for the remaining ones.

    # Make sure that input is of correct type (list)
    input1 = [directories[0]]
    if isinstance(directories[1:], list):
        input2 = directories[1:]
    else:
        input2 = [directories[1:]]

    # Function calls
    display_first_directory = display_directory(
        directories=input1,
        experiment=experiment,
        parent_directory=parent_directory)
    display_other_directories = display_directory(
        directories=input2,
        experiment=experiment,
        parent_directory=parent_directory)

    # Return the full html code for display
    return "<br>".join([display_first_directory, display_other_directories])


def perform_futurization(file):
    futurize = subprocess.run(['futurize', '-w', file], check=True, universal_newlines=True)

    return futurize


def replace_all_patterns(file):

    def load_json(file):
        with open(file, "r", encoding="utf-8") as json_file:
            text = json_file.read().replace("\n", "")
            json_data = json.loads(text)

        return json_data

    def replace_patterns(file, change_dict, write=False, max_iter=10):
        with open(file, "r", encoding="utf-8") as f:
            code = []
            iter = 0
            for line in f.readlines():  # go through code line by line
                # for each line, go through all changes
                for old_name, new_name in change_dict.items():
                    pattern = re.compile(
                        r"\W?(?P<name>{pattern})\W?".format(pattern=old_name))
                    m = pattern.search(line)

                    # while-loop for multiple occurences of old_name per line
                    # with max number of iterations for safety
                    while m and iter <= max_iter:
                        line = line[:m.start("name")] + \
                            new_name + line[m.end("name"):]
                        m = pattern.search(line)
                        iter += 1
                        # print each old and new name
                        # print("Old: %s, New: %s" % (old_name, new_name))
                    if iter == max_iter:
                        raise AssertionError(
                            "One line had at least %i replacements. Something seems to be wrong" % max_iter)
                    iter = 0

                gen_pattern = re.compile(r"(?P<gen>def generate_experiment\(self\):)")
                exp_pattern = re.compile(r"(?P<exp>exp = Experiment\('web', exp_name, exp_version\))")
                
                line = gen_pattern.sub('def generate_experiment(self, config=None):', line)
                line = exp_pattern.sub('exp = Experiment(config=config)', line)

                code.append(line)

        code = "".join(code)

        if write:  # if parameter is true, we save the changes to the file
            with open(file, "w", encoding="utf-8") as f:
                f.write(code)

        return code

    json_data = []
    path = os.path.join(current_app.root_path, "static",
                        "futurizing_alfred_scripts")
    for pattern_file in sorted(os.listdir(path)):
        json_data.append(load_json(os.path.join(path, pattern_file)))

    for dct in json_data:
        replace_patterns(file, dct, write=True)


class ScriptString:

    def __init__(self, exp, script=None):
        self.exp = exp
        self.name = self.exp.script_name if self.exp.script else str(uuid4()) + ".py"
        self.script = script

    def parse(self):
        # removes the run(generate_experiment) command from the end of a script.py allow mortimer to run it
        p = re.compile(r"(?P<call>(alfred\.)?run\(generate_experiment\))(?P<comments>([\s]*(#.*)*)*)\Z")
        self.script = p.sub("# Here, the call to 'run(generate_experiment)' and following comments were removed.", self.script)

    def save(self):
        # saves the script to the experiment and to the file system, if changes were made
        if (self.exp.script != self.script) or not os.path.exists(self.exp.script_fullpath):
            
            try:
                os.remove(self.exp.script_fullpath)
            except (FileNotFoundError, TypeError):
                pass

            self.exp.script = self.script
            self.exp.script_name = self.name
            self.exp.script_fullpath = os.path.join(self.exp.path, self.exp.script_name)
            self.exp.last_update = datetime.utcnow

            with open(self.exp.script_fullpath, "w", encoding="utf-8") as f:
                f.write(self.exp.script)

            self.exp.save()


class ScriptFile(ScriptString):

    def __init__(self, exp, file):
        super().__init__(exp)
        self.file = file
        self.script = ''

    def load(self):
        path = os.path.join(current_app.root_path, 'tmp', self.name)
        self.file.save(path)

        with open(path, 'r', encoding='utf-8') as f:
            self.script = f.read()

        os.remove(path)


class _DictObj(dict):
    """
    This class allows dot notation to access dict elements

    Example:
    d = _DictObj()
    d.hello = "Hello World"
    print d.hello # Hello World
    """

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
