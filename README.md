# Welcome to Mortimer

Mortimer is a free, open source web application written in the [Flask Framework](http://flask.pocoo.org/). It's purpose is to host and manage [Alfred](https://github.com/ctreffe/alfred) experiments and surveys.

**IMPORTANT NOTE**: Mortimer is currently not easy to set up and use safely. Please contanct us, if you want to use it. Most importantly, you should allow only trusted users to register.

# Installation

## Prerequisites

- Python 3.7 or newer installed
- A [MongoDB](https://www.mongodb.com/de) instance with [authentication](https://docs.mongodb.com/manual/tutorial/enable-authentication/) enabled.
    - For MongoDB installation on Debian servers, you can refer to the [official installation guide](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-debian/).
    - Create a databse "mortimer" and a database "alfred" in your MongoDB instance. The "mortimer" db will be used for user management and deployment of Alfred experiments. The "alfred" database will be used by Alfred to store experimental data.
- Refer to the [MongoDB security checklist](https://docs.mongodb.com/manual/administration/security-checklist/) to ensure adequate security of your database.

## Installation

**IMPORTANT NOTE**: Mortimer is currently not easy to set up and use safely. Please contanct us, if you want to use it. Most importantly, you should only ever allow trusted users to register.

``` BASH
pip install mortimer
```

### Configure Mortimer
Now you need to configure mortimer. You have the following options on where to place it:

1. If you are operating on a unix-based operating system, you can create a file `mortimer.conf` in `/etc`.
2. You can create a file `mortimer.conf` in your user home directory.
3. You can create a file `mortimer.conf` in a directory of your choosing and set the **directory path** (not the full path to the file) as an environment variable with the key `MORTIMER_CONFIG`.
4. You can create a file `mortimer.conf` in your instance path.

You only need to use one of these options. If you don't know which one to use, we recommend to place the configuration fiel in your instance directory. The files are read in that order, later files override earlier ones.

For a minimal setup, you need to specify the following settings. 

Notes:

* The mongoDB user needs to have the following roles:
    + `userAdmin` role on the "alfred" database.
    + `readWrite` role on the "mortimer" dabatase.
    + `read` role on the "alfred" database.

``` Python
# General flask settings
SECRET_KEY =            # Must be URL-safe base64-encoded 32-byte key for fernet encryption in STR (NOT in bytes)
PAROLE =                # a passphrase that new users need to enter upon registration
DEBUG =                 # True or False

# flask-mongoengine settings
MONGODB_SETTINGS = {
    "host": "localhost",
    "port": 27017,
    "username": "<username>",
    "password": "<password>"
}
```

## Start

Before starting, you need to create a run.py and specify your instance path. The run.py will look like this:

``` Python
from mortimer import create_app

path = "" # fill in your instance path here!

app = create_app(instance_path=path)

if __name__ == "__main__":
    app.run(debug=True)

```


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

**IMPORTANT NOTE**: Mortimer is currently not easy to set up and use safely. Please contanct us, if you want to use it. Most importantly, you should allow only trusted users to register.

