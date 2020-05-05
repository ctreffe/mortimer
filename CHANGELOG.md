# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

* Mortimer is now available from PyPi. It can be installed with pip:

``` BASH
pip install mortimer
```

* Mortimer now uses a different configuration setup. See README.md for details.

* From now on, we will generally be using the changelog format recommended by [Keep a Changelog](https://keepachangelog.com/en/)
    + In the course of this change, we changed the name of the former `NEWS.md` to `CHANGELOG.md`.

### Fixed

* Fixed a registration bug.

## Mortimer v0.4.5

### Security improvements

* We further increased data protection and data security through an improved handling of access to the alfred database from inside experiments.

### Bugfixes

* Fixed a bug that caused JavaScript to crash on some pages.
* Fixed a bug that caused an error during data encryption using the key introduced in v0.4.4
* Fixed a bug that prevented the deletion of experiments with specific filenames 
* Fixed the referrer after changing an experiments title

### Small changes

* Included line wrapping for the experiment log

## Mortimer v0.4.4

### Encryption Keys

* Every user now has a unique fernet encryption key, generated via `cryptography.fernet.Fernet.generate_key()`. The key is passed as an entry in the `config` dictionary (key: `encryption_key`) to the `generate_experiment()` function in `alfredo.py`. 
* The key itself is saved to the mortimer database in encrypted form.
* Usage: See [here](https://github.com/ctreffe/alfred/releases/tag/v1.0.6)

### Bugfixes

* Fixed a bug that prevented the deletion of single files in the resources pane to work properly.

## Mortimer v0.4.3

### Bugfixes

* Fixed a bug that caused the `web_experiments.experiment()` page to crash as a consequence of a specific experiment startup error.

### Smaller changes

* Improved error handling: Subjects will now always receive a neutral error page, if an experiment crashes. Previously, they were redirected to the login page in some cases.
* Small UI improvements

## Mortimer v0.4.2

### Bugfixes

* Fixed a bug introduced in v0.4.1, which led to a problem with new experiments. Their experiment ID did not get saved at the right time, which caused trouble with data export.

### Smaller changes

* Mortimer now displays its own version number and the alfred version currently running on the server.

## Mortimer v0.4.1

### Bugfixes

* Fixed a bug in `alfredo.py` that caused trouble for videos implemented via `alfred.element.WebVideoElement` in Safari (wouldn't play at all) and Chrome (forward/backward wouldn't work)

## Mortimer v0.4-beta

### Breaking changes

* **Separation of web and local experiments**. Web experiments hosted via mortimer and local experiments now save their data into different collections in the Alfred database ( `web` and `local` ). This means that you can be completely sure that your web and local experiments don't interfere.
* **`exp_id`** for local experiments. You need to specify a unique `exp_id` in the section `[metadata]` of your `config.conf` to be sure that you can retrieve your data from local experiments. Thankfully, Mortimer will always give you a new unique ID on its home page and on the page for local experiment creation.

### New user interface

* **Fully reworked user interface**. The new interface should be quite self-explanatory. Feel free to explore!

### New features

* **File Management**
    - You can create directories and subdirectories belonging to your experiment
    - You can upload now multiple files at once
    - No one but you can access you files
* **Configuration**. You can now configure your experiment from within Mortimer.
* **Experiment Log**. You can now view your experiment's log file from within Mortimer.
* **Futurize Scripts**. You can futurize an old script to help you port it to Alfred v1.0.

