import os
from flask import current_app
from werkzeug.utils import secure_filename
from mortimer import mail
from flask_mail import Message
from flask import url_for
import re


def save_file(file, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file.save(path)


def create_filepath(file, experiment_title: str, subdirectory: str=""):
    experiment_directory = experiment_title.replace(" ", "_")
    file_fn = secure_filename(file.filename)
    file_path = os.path.join(current_app.root_path, "experiments", experiment_directory, subdirectory, file_fn)

    return {"filename": file_fn, "full_path": file_path}


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Password Reset Request",
                  sender="mortimer.test1@gmail.com",
                  recipients=[user.email])
    msg.body = f'''Dear Mortimer user,

a request to reset your password was made for your email adress.

To reset your password, visit the following link:
{url_for('users.reset_password', token=token, _external=True)}

If you did not make this request, then you can simply ignore this email and no changes will be made.

Kind regards,
The Mortimer Team
'''
    mail.send(msg)


def display_directory(directories: list, parent_directory: str, experiment, call_id: int=0) ->str:
    """
    This is a recursive function. The endpoint is reached if it is called on a list
    that contains a single directory without subdirectories.

    :param list directories: List of directories that shall be displayed.

    :param str parent_directory: **Full** path to the directory holding the
    directories in the list `directories`.

    :param int call_id: Each time, the function is called on a new directory
    level, the call ID gets increased. This information gets passed to the
    helper function display_directory_controls(). This way we can handle the
    case if two subdirectories in different top foldern have the same name.
    """

    print("\n----------------------------")
    print(f"FUNCTION CALLED ON {directories}\nPARENT DIRECTORY: {parent_directory}")

    call_id += 1

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

    def display_files(file_list: list, path: str, experiment_title: str, experiment_author: str) ->str:
        """
        This function generates html code to display the files in a directory.
        :param list file_list: List of files in a directory.
        """
        out = []
        for f in file_list:
            if f == ".DS_Store":
                continue
            filepath = os.path.join(path, f)
            url = url_for('web_experiments.delete_file', experiment_title=experiment_title, username=experiment_author, relative_path=filepath)
            display_one = f"""<div class=\"m-1\">
            <button type="button" class="btn btn-outline-danger btn-sm mt-1 mb-1" data-toggle="modal" data-target="#deleteModal_{filepath}">Delete</button> <span class=\"ml-2\">{f}</span>
            </div>

                <div class="modal fade" id="deleteModal_{filepath}" tabindex="-1" role="dialog" aria-labelledby="deleteModal_{filepath}Label" aria-hidden="true">
                  <div class="modal-dialog" role="document">
                    <div class="modal-content">
                      <div class="modal-header">
                        <h5 class="modal-title" id="deleteModal_{filepath}Label">Delete All Files</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                      </div>
                      <div class="modal-body">
                        Are you sure that you want to delete the file <code>{f}</code>? The data stored in Mortimer will be lost!
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <form method="POST" action="{url}">
                          <input class="btn btn-danger" type="submit" value="Delete">
                        </form>
                      </div>
                    </div>
                  </div>
                </div>

            """
            out.append(display_one)
        return "".join(out)

    def display_directory_controls(directory: str, path: str, experiment_title: str, experiment_author: str, file_display: str, subdirectory_display: str, call_id: int=0) ->str:
        upload_url = url_for('web_experiments.upload_resources', experiment_title=experiment_title, username=experiment_author, relative_path=path)
        new_subdirectory_url = url_for('web_experiments.new_directory', experiment_title=experiment_title, username=experiment_author, relative_path=path)
        delete_directory_url = url_for('web_experiments.delete_directory', experiment_title=experiment_title, username=experiment_author, relative_path=path)

        out = f"""<div>
                    <p>
                        <code style="color:black">{path}</code>
                        <button class=\"btn btn-outline-primary btn-sm ml-2\" type=\"button\" data-toggle=\"collapse\" data-target=\"#collapse_{directory}_{call_id}\" aria-expanded=\"false\" aria-controls=\"collapseExample\">
                        Show Files
                        </button>
                        <button class=\"btn btn-outline-primary btn-sm\" type=\"button\" data-toggle=\"collapse\" data-target=\"#NewDirectory_{directory}_{call_id}\" aria-expanded=\"false\" aria-controls=\"collapseExample\">
                        New Subdirectory
                        </button>
                        <a class=\"btn btn-outline-success btn-sm\" href=\"{upload_url}\">Upload Files</a>
                        <button type="button" class="btn btn-outline-danger btn-sm mt-1 mb-1" data-toggle="modal" data-target="#deleteModal_{directory}">Delete Directory</button>
                    </p>

                    <div class="collapse" id="NewDirectory_{directory}_{call_id}">
                        <form action="{new_subdirectory_url}", method="POST">
                            <div><input class="form-control form-control-lg mr-3 mb-3 mt-3" id="new_directory" name="new_directory" required type="text" value="" placeholder="Name">
                            <input class="btn btn-outline-primary btn-sm" type="submit" value="Create"></div>


                        </form>
                    </div>

                    <div class=\"collapse\" id=\"collapse_{directory}_{call_id}\">
                    {file_display} <br>
                    </div>


                    {subdirectory_display}

                </div>

                <div class="modal fade" id="deleteModal_{directory}" tabindex="-1" role="dialog" aria-labelledby="deleteModal_{directory}Label" aria-hidden="true">
                  <div class="modal-dialog" role="document">
                    <div class="modal-content">
                      <div class="modal-header">
                        <h5 class="modal-title" id="deleteModal_{directory}Label">Delete All Files</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                      </div>
                      <div class="modal-body">
                        Are you sure that you want to delete the directory <code>{path}</code>? The data stored in Mortimer will be lost!
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <form method="POST" action="{delete_directory_url}">
                          <input class="btn btn-danger" type="submit" value="Delete">
                        </form>
                      </div>
                    </div>
                  </div>
                </div>
                """

        return out

    if not directories:
        return ""

    # --- LEN == 1 FUNCTION CALL --- #
    # If the Input to the function is a single directory, the code below will be executed
    if len(directories) == 1:

        path = os.path.join(relative_path, directories[0])  # Get directory path
        full_path = os.path.join(experiment.path, path)

        # find out, which elements of directory are files and which are subdirectories
        subdirectory_list = []
        file_list = []

        for filename in sorted(os.listdir(full_path)):
            if os.path.isdir(os.path.join(full_path, filename)):
                subdirectory_list.append(filename)
            else:
                file_list.append(filename)

        # Create html code for file display
        if file_list:
            single_files = display_files(file_list=file_list, path=path, experiment_title=experiment_title, experiment_author=experiment_author)
        else:
            single_files = ""

        # Create html code for display of subdirectories. The function is called again.
        if subdirectory_list != []:
            subdirectory_display = display_directory(directories=subdirectory_list,
                                                     experiment=experiment,
                                                     parent_directory=path,
                                                     call_id=call_id)
        else:
            subdirectory_display = ""

        # return the full html code for a single directory
        if parent_directory == experiment.path:
            div_open = "<div class=\"content-section\">"
            div_close = "</div>"
        else:
            div_open = ""
            div_close = ""

        return div_open + display_directory_controls(directory=directories[0],
                                                     path=path,
                                                     experiment_title=experiment_title,
                                                     experiment_author=experiment_author,
                                                     file_display=single_files,
                                                     subdirectory_display=subdirectory_display,
                                                     call_id=call_id) + div_close

    # --- USUAL FUNCTION CALL --- #
    # The code below will be executed, if the function was called on a list of multiple
    # directories. First, the list is split into one list containing the first directory
    # and another list containing the remaining directories.
    # The function is then called on both lists, resulting in a len(directories) == 1
    # function-call for the first directory and another usual all for the remaining ones.

    # Make sure that input is of correct type (list)
    input1 = [directories[0]]
    if isinstance(directories[1:], list):
        input2 = directories[1:]
    else:
        input2 = [directories[1:]]

    # Function calls
    display_first_directory = display_directory(directories=input1,
                                                experiment=experiment,
                                                parent_directory=parent_directory,
                                                call_id=call_id)
    display_other_directories = display_directory(directories=input2,
                                                  experiment=experiment,
                                                  parent_directory=parent_directory,
                                                  call_id=call_id)

    # Return the full html code for display
    return "<br>".join([display_first_directory, display_other_directories])


def filter_directories(experiment):
    dir_list = os.listdir(experiment.path)
    subdirectory_list = []

    for filename in sorted(dir_list):
        if (os.path.isdir(os.path.join(experiment.path, filename)) and filename in experiment.user_directories):
            subdirectory_list.append(filename)

    return subdirectory_list


def extract_version(filename):
    p = re.compile(r"(exp_version|expVersion) *= *[\"\'](?P<version>.*)[\"\']")

    version = []

    with open(filename, "r") as f:
        for line in f.readlines():
            m = p.search(line)
            if m is not None:
                version.append(m.group("version"))

    return version[0]


def extract_title(filename):
    p = re.compile(r"(exp_name|expName) *= *[\"\'](?P<name>.*)[\"\']")

    name = []

    with open(filename, "r") as f:
        for line in f.readlines():
            m = p.search(line)
            if m is not None:
                name.append(m.group("name"))

    return name[0]
