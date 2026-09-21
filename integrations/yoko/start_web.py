"""Start the browser-only web app; no LINE, SDK, Node or API key is required."""
import os
import sys
from pathlib import Path


if __name__ == "__main__":
    if sys.version_info < (3, 12):
        sys.exit("Python 3.12 以降を用意して、もう一度実行してください。")
    # Double-click launchers can start in an unrelated directory. Always reuse
    # this application's persisted database unless the operator passes --db.
    os.chdir(Path(__file__).resolve().parent)
    from app.__main__ import main
    main(["--open-browser", *sys.argv[1:]])
