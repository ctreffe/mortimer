import sys
import logging
from pathlib import Path
from alfred3 import alfredlog
from mortimer import create_app
from dotenv import load_dotenv
load_dotenv()

path = Path(sys.argv[0]).resolve()


# configure logging
formatter = alfredlog.prepare_alfred_formatter("n/a")
alfredlogger = logging.getLogger("alfred3")

logdir = path.parent / "log"
logdir.mkdir(exist_ok=True)
print(logdir)
logfile = logdir / "alfred.log"
alfredlog_file_handler = alfredlog.prepare_file_handler(logfile)
alfredlog_file_handler.setFormatter(formatter)
alfredlog_file_handler.setLevel(logging.INFO)
alfredlogger.addHandler(alfredlog_file_handler)
alfredlogger.setLevel(logging.INFO)

logpath = logdir / "alfredo.log"
app = create_app(instance_path=path.parent, logfile=str(logpath.resolve()))

if __name__ == "__main__":
    app.run(debug=True)
