# Welcome to Mortimer

Mortimer is a free, open source web application written in the [Flask Framework](http://flask.pocoo.org/). It's purpose is to host and manage [Alfred](https://github.com/ctreffe/alfred) experiments and surveys.

# Installation

## Prerequisites

- Python 3.5 or newer installed
- Git installed
- A [MongoDB](https://www.mongodb.com/de) instance with [authentication](https://docs.mongodb.com/manual/tutorial/enable-authentication/) enabled.
    - For MongoDB installation on Debian servers, you can refer to the [official installation guide](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-debian/).
    - Create a databse "mortimer" and a database "alfred" in your MongoDB instance. The "mortimer" db will be used for user management and deployment of Alfred experiments. The "alfred" database will be used by Alfred to store experimental data.

## Install

### Set up and activate a virtual python environment

In a shell, execute the following commands:
```
python3 -m venv /path/to/new/virtual/environment/mortimer3
source /path/to/new/virtual/environment/mortimer3/bin/activate
```

### Download and install Alfred
Mortimer requires [Alfred](https://github.com/ctreffe/alfred). Please visit the Alfred repository for instructions on how to install Alfred.


### Clone the latest stable version from GitHub
After cloning, switch to the mortimer directory.

```
git clone https://github.com/ctreffe/mortimer.git
cd mortimer
```

### Install dependencies
In a shell, execute the following command to install required Python packages (make sure that you are inside the mortimer directory):

```
pip install -r requirements.txt
```

### Configure Mortimer
Now it is time to configure Mortimer. You can do so by editing the `config.py`, or by setting the correct environment variables (Link: How to use environment variables for Mortimer configuration). The latter has the advantage of being easier to update, if a new version of Mortimer is released. The first one is more straight-forward to do.

For a first installation, you need the following settings:
- Set the login data for your MongoDB databases
- Set a secret key (used e.g. for encrypting session data)
- Set a registration parole to protect access to the platform. New users need to enter this parole during registration.
- Set the login data to a mail account. Mortimer will use this account to send password reset emails. You can alsp deactivate the use of email, but in this case Mortimer will not allow users to reset their password if they forget it. We do not recommend this.


## Start

You are now ready to start Mortimer. In a shell, execute the following command (make sure that you are inside the mortimer directory):

```bash
export FLASK_APP=run.py
flask run
```

This will allow you to access Mortimer locally via `127.0.0.1/5000` from your webbrowser. You can make the app available externally with these commands:

```bash
export FLASK_APP=run.py
flask run --host=0.0.0.0 --port=5000
```


**Important Note: Do not use this in a production setting. It is not intended to meet security and performance requirements for a production server. Instead, see Flasks [Deployment Options](http://flask.pocoo.org/docs/1.0/deploying/#deployment) for WSGI server recommendations.**

