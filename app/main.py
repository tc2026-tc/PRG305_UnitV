import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

import database
from ui import MainWindow


def main():
    database.init_db()          # making sure the table exists
    app = QApplication(sys.argv)

    # Load the stylesheet (path is relative to this file, not hard-coded)
    qss_path = Path(__file__).resolve().parent / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())        # start the event loop


if __name__ == "__main__":
    main()