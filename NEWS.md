# Mortimer v0.4-beta

## Breaking changes
- **Separation of web and local experiments**. Web experiments hosted via mortimer and local experiments now save their data into different collections in the Alfred database (`web` and `local`). This means that you can be completely sure that your web and local experiments don't interfere.
- **`exp_id`** for local experiments. You need to specify a unique `exp_id` in the section `[metadata]` of your `config.conf` to be sure that you can retrieve your data from local experiments. Thankfully, Mortimer will always give you a new unique ID on its home page and on the page for local experiment creation.

## New user interface
- **Fully reworked user interface**. The new interface should be quite self-explanatory. Feel free to explore!

## New features
- **File Management**
    - You can create directories and subdirectories belonging to your experiment
    - You can upload now multiple files at once
    - No one but you can access you files
- **Configuration**. You can now configure your experiment from within Mortimer.
- **Experiment Log**. You can now view your experiment's log file from within Mortimer.
- **Futurize Scripts**. You can futurize an old script to help you port it to Alfred v1.0.
