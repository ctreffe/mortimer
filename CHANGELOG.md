# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## Newer versions

See https://github.com/ctreffe/mortimer/releases

## Mortimer v0.8.13 (Released 2022-05-21)

### Changed

- (New) users are now allowed to remove documents in their own alfred3 
  mongoDB collections.

### Fixed

- Fixed support for url-jumping support
- Fixed #82

### Added

- Added logging capability (#78)
- Added log calls for 412 server responses (#79)

## Mortimer v0.8.12 (Released 2021-10-28)

### Added

- Added support for alfred3's new test mode
- Added "sid" prefix for session ids
- Added quickstart options for alfred3's test mode and debug mode
- Added a warning that will appear upon codebook download if element 
  labels in *the two newest* datasets are unequal.

## Mortimer v0.8.11 (Released 2021-10-14)

### Changed

- Compatibility patch for alfred3 v2.2.0

## Mortimer v0.8.10 (Released 2021-06-09)

### Added

- Added beta support for social media previews

## Mortimer v0.8.8 (Released 2021-06-03)

### Added v0.8.8

- .zip archives can be used for uploading experiment resources

## Mortimer v0.8.7 (Released 2021-05-14)

### Fixed v0.8.7

- Fixed subdirectory display (#54)
- Inactive experiments are now in fact unavailable (#53)

## Mortimer v0.8.6 (Released 2021-05-14)

### Changed v0.8.6

- Increased timeout before experiment sessions are removed by mortimer.

## Mortimer v0.8.5 (Released 2021-04-20)

### Changed v0.8.5

- Changed some internal functions in alfredo.py for compatibility with
  alfred3 v2.0.0

## Mortimer v0.8.4 (Released 2021-04-15)

### Added v0.8.4

- Added button for starting an experiment directly with url parameters

### Changed v0.8.4
- Participant registration route now works with experiment version. The version is required for registration and optional for checking.
- Changed internal handling of page tokens
- /callable route in alfredo.py does not automatically redirect to /experiment anymore. This prevents unnecessary redirects. Previously, those redirects happened every time the called function return `None`.
- /callable route in alfredo.py now automatically jsonifies return values.

## Mortimer v0.8.2

### Added

Starting from v0.8.2, Mortimer allows experimenters to check, whether partcipants have
participated in a specific experiment through the route `/participation`.

A guide on how to use it is available in the [wiki](https://github.com/ctreffe/mortimer/wiki/Check-participation)

## Mortimer v0.8.0

### Changed

Mortimer was updated to be compatible with alfred3 v2.0. This included
first and foremost an update to the data export handling and some small
updates to configuration handling. Due to these changes, Mortimer v0.8.0
is not compatible with older versions of alfred3.

## Mortimer v0.7.0

### Added

* Added support for two additional collections in the alfred database.
* Redesigned and enhanced data export. When used with alfred v1.4+, Mortimer now offers export of unlinked data and codebooks.

### Fixed

* Fixed a bug in the password reset email.

## Mortimer v0.6.1 (Released 2020-07-23)

### Fixed

* Fixed a bug that prevented correct logging of exceptions occuring during experiment execution.

* Fixed a bug that messed up the layout of the experiment page for inactive experiments.

## Mortimer v0.6.0 (Released 2020-07-13)

### Changed

* Mortimer was updated to be compatible with alfred's new logging and configuration handling introduced in alfred3 v1.2.0.

* The "Log" tab received an update. To increase performance, we now only show the newest 300 entries by default. You can still choose to display all entries. If you have a very large log, you should be prepared for a few seconds processing time in this case.

* Changed the "Configuration" tab. You can now paste your secrets.conf and config.conf from your local experiment directory into text fields. Note that some settings will be overwritten by mortimer, most notably the **metdata** and **loca_saving_agent** sections in *config.conf* and the **mongo_saving_agent** section in *secrets.conf*.

* The experiment homepage and the "Resources" tab both received a small facelift. Most notably, we now show datasets by experimental version.

* Changed default sorting in "Experiments" overview (new default: Last Update) and "Data" Tab (new default: save_time).

### Fixed

* Included a hotfix for a performance issues with our use of the DataTables Javascript plugin. Until we include server-side processing for the table, the data tab will only show a preview of 50 observations.

## Mortimer v0.5.1

### Changed

* We now use the JavaScript plugin DataTable for the data tab and the experiment overview.
* You can now upload your own modules to subfolders of the experiment directory and import them in your `script.py` . Remember to add an `__init__.py` to the subdirectory.
* Small UI change to the account page.

## Mortimer v0.5.0

### Added

* Added automatic DB credential generation. Mortimer now automatically generates database credentials for locally run alfred experiments for all users. They can be viewed on the "Account" page. You can use these credentials in your config.conf to write your experiment data to a collection in the Alfred database specifically reserved for your local experiments. **Make sure to specify ` ` auth_source = alfred ` ` in your config.conf**, otherwise you will receive an authentication error upon trying to save to the database.

* Added encryption key display. Mortimer now displays the user's encryption key on the "Account" page. This is the key used for encryption via `alfred3.Experiment.encrypt` and `alfred3.Experiment.decrypt` .

* Added a "Data" tab to the experiment view, allowing users to preview collected data.

* Added two data export formats: `excel_csv` (export to excel-friendly .csv format with `;` -delimiter) and `json` .

* Added log filtering. On the "log" tab of the experiment view, you can now select the log levels that you want to display. Your settings are saved and applied on an account level.

## Mortimer v0.4.5

### Changed

* Mortimer is now available from PyPi. It can be installed with pip:

``` BASH
pip install mortimer
```

* Mortimer now uses a different configuration setup. See README.md for details.

* In the future, we will be using the changelog format recommended by [Keep a Changelog](https://keepachangelog.com/en/)
    - In the course of this change, we changed the name of the former `NEWS.md` to `CHANGELOG.md` .

### Fixed

* Fixed a registration bug.

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

* Every user now has a unique fernet encryption key, generated via `cryptography.fernet.Fernet.generate_key()` . The key is passed as an entry in the `config` dictionary (key: `encryption_key` ) to the `generate_experiment()` function in `alfredo.py` . 
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
