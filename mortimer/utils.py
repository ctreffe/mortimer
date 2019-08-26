import os
import subprocess
import json
import re
from datetime import datetime
from flask import current_app
from mortimer import mail
from flask_mail import Message
from flask import url_for
from uuid import uuid4
from jinja2 import Template


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
            display_one = Template('''<div class=\"row m-1\">
            <div class="col-md-10 float-left">
             <span class=\"ml-2\">- {{f}}</span>
            </div>
            <div class="col-md-2 btn btn-outline-danger btn-sm"
             <button type="button" data-toggle="modal" data-target="#deleteModal_{{filepath}}">Delete</button>
            </div>
            </div>

                <div class="modal fade" id="deleteModal_{{filepath}}" tabindex="-1" role="dialog" aria-labelledby="deleteModal_{{filepath}}Label" aria-hidden="true">
                  <div class="modal-dialog" role="document">
                    <div class="modal-content">
                      <div class="modal-header">
                        <h5 class="modal-title" id="deleteModal_{{filepath}}Label">Delete All Files</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                      </div>
                      <div class="modal-body">
                        Are you sure that you want to delete the file <code>{{f}}</code>? The data stored in Mortimer will be lost!
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <form method="POST" action="{{url}}">
                          <input class="btn btn-danger" type="submit" value="Delete">
                        </form>
                      </div>
                    </div>
                  </div>
                </div>
            ''')

            out.append(display_one.render(f=f, filepath=filepath, url=url))
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

        out = Template('''<div>
                    <p>
                        <span><code style="color:black">{{path}}</code></span>
                        <span class="float-md-right">
                        <button class=\"btn btn-outline-primary btn-sm ml-2\" type=\"button\" data-toggle=\"collapse\" data-target=\"#collapse_{{directory}}_{{call_id}}\" aria-expanded=\"false\" aria-controls=\"collapseExample\">
                        Show Files
                        </button>
                        <button class=\"btn btn-outline-primary btn-sm\" type=\"button\" data-toggle=\"collapse\" data-target=\"#NewDirectory_{{directory}}_{{call_id}}\" aria-expanded=\"false\" aria-controls=\"collapseExample\">
                        New Subdirectory
                        </button>
                        <a class=\"btn btn-outline-success btn-sm\" href=\"{{upload_url}}\">Upload Files</a>
                        <button type="button" class="btn btn-outline-danger btn-sm mt-1 mb-1" data-toggle="modal" data-target="#deleteModal_{{directory}}_{{call_id}}">Delete Directory</button>
                        </span>
                    </p>

                    <div class="collapse" id="NewDirectory_{{directory}}_{{call_id}}">
                        <form action="{{new_subdirectory_url}}", method="POST">
                            <div><input class="form-control form-control-lg mr-3 mb-3 mt-3" id="new_directory" name="new_directory" required type="text" value="" placeholder="Name">
                            <input class="btn btn-outline-primary btn-sm" type="submit" value="Create"></div>


                        </form>
                    </div>

                    <div class=\"collapse pt-3\" id=\"collapse_{{directory}}_{{call_id}}\">
                    {{file_display}} <br>
                    </div>


                    {{subdirectory_display}}

                </div>

                <div class="modal fade" id="deleteModal_{{directory}}_{{call_id}}" tabindex="-1" role="dialog" aria-labelledby="deleteModal_{{directory}}Label_{{call_id}}" aria-hidden="true">
                  <div class="modal-dialog" role="document">
                    <div class="modal-content">
                      <div class="modal-header">
                        <h5 class="modal-title" id="deleteModal_{{directory}}Label_{{call_id}}">Delete All Files</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                      </div>
                      <div class="modal-body">
                        Are you sure that you want to delete the directory <code>{{path}}</code>? The data stored in Mortimer will be lost!
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <form method="POST" action="{{delete_directory_url}}">
                          <input class="btn btn-danger" type="submit" value="Delete">
                        </form>
                      </div>
                    </div>
                  </div>
                </div>
                ''')

        return out.render(path=path,
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


def extract_version(filename):
    p = re.compile(
        r"(exp_version|expVersion|EXP_VERSION) *= *[\"\'](?P<version>.*)[\"\']")

    version = []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f.readlines():
            m = p.search(line)
            if m is not None:
                version.append(m.group("version"))

    return version[0]


def extract_title(filename):
    p = re.compile(r"(exp_name|expName|EXP_NAME) *= *[\"\'](?P<name>.*)[\"\']")

    name = []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f.readlines():
            m = p.search(line)
            if m is not None:
                name.append(m.group("name"))

    return name[0]


def extract_author_mail(filename):
    p = re.compile(
        r"(exp_author_mail|expAuthorMail|EXP_AUTHOR_MAIL) *= *[\"\'](?P<author_mail>.*)[\"\']")

    name = []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f.readlines():
            m = p.search(line)
            if m is not None:
                name.append(m.group("author_mail"))

    return name[0]


def futurize_script(file):
    futurize = subprocess.run(['futurize', '-w', file], check=True, text=True)

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

                code.append(line)
        code = "".join(code)

        if write:  # if parameter is true, we save the changes to the file
            with open(file, "w", encoding="utf-8") as f:
                f.write(code)

        return code

    json_data = []
    path = os.path.join(current_app.root_path, "static",
                        "futurizing_alfred_scripts")
    for pattern_file in os.listdir(path):
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
        p = re.compile(r"(?P<call>run\(generate_experiment\)[\s]*)\Z")
        self.script = p.sub("# run(generate_experiment)", self.script)

    def save(self):
        # saves the script to the experiment and to the file system, if changes were made
        if self.exp.script != self.script:
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
