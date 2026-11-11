import json
from pathlib import Path

from PyQt6.QtCore import QPropertyAnimation, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

import database


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_student_details():
    """Read name and roll number from config.json; use placeholders if missing."""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return (data.get("student_name", "YOUR NAME"),
                data.get("roll_number", "YOUR ROLL NO"))
    except (OSError, ValueError):      # file missing or not valid JSON
        return "YOUR NAME", "YOUR ROLL NO"


STUDENT_NAME, ROLL_NUMBER = load_student_details()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_students = []     # students currently shown in the table
        self.setWindowTitle(f"Student Record Manager - {STUDENT_NAME} ({ROLL_NUMBER})")
        self.resize(1050, 700)
        self.setMinimumSize(800, 550)
        self._build_menu()
        self._build_ui()
        self._connect_signals()
        self.refresh_table()
        self._fade_in()

    # ---------- animation ----------
    def _fade_in(self):
        """Fade the window in when the app starts."""
        self.setWindowOpacity(0.0)
        self.fade = QPropertyAnimation(self, b"windowOpacity")
        self.fade.setDuration(700)
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)
        self.fade.start()

    # ---------- menu bar ----------
    def _build_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        help_menu = menu_bar.addMenu("&Help")
        self.about_action = QAction("&About", self)
        help_menu.addAction(self.about_action)

    # ---------- widgets and layouts ----------
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)           # layout 1: whole window

        banner = QLabel("Student Record Manager  |  B.Ed IT")
        banner.setObjectName("banner")
        main_layout.addWidget(banner)

        # --- student details (QFormLayout: layout 2) ---
        details_box = QGroupBox("Student details")
        details_form = QFormLayout(details_box)
        self.roll_input = QLineEdit()
        self.roll_input.setPlaceholderText("e.g. S001")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")
        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in database.YEARS])
        self.active_check = QCheckBox("Currently enrolled")
        self.active_check.setChecked(True)
        details_form.addRow("Roll no:", self.roll_input)
        details_form.addRow("Name:", self.name_input)
        details_form.addRow("Year:", self.year_combo)
        details_form.addRow("", self.active_check)

        # --- marks (QGridLayout: layout 3); labels change with the year ---
        marks_box = QGroupBox("Marks (out of 100)")
        marks_grid = QGridLayout(marks_box)
        self.mark_inputs = {}
        self.mark_labels = {}
        for col, key in enumerate(database.MARK_FIELDS):
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin = QSpinBox()
            spin.setRange(0, 100)
            self.mark_labels[key] = label
            self.mark_inputs[key] = spin
            marks_grid.addWidget(label, 0, col)
            marks_grid.addWidget(spin, 1, col)
        self.update_subject_labels(self.year_combo.currentText())

        top_row = QHBoxLayout()
        top_row.addWidget(details_box, 1)
        top_row.addWidget(marks_box, 2)
        main_layout.addLayout(top_row)

        # --- live result preview ---
        result_row = QHBoxLayout()
        self.result_label = QLabel("Total: 0 / 500    Grade: F")
        self.percent_bar = QProgressBar()
        self.percent_bar.setRange(0, 100)
        self.percent_bar.setFormat("%p%")
        result_row.addWidget(self.result_label)
        result_row.addWidget(self.percent_bar, 1)
        main_layout.addLayout(result_row)

        # --- buttons ---
        button_row = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.update_button = QPushButton("Update")
        self.delete_button = QPushButton("Delete")
        self.clear_button = QPushButton("Clear form")
        self.delete_button.setObjectName("deleteButton")   # lets QSS colour it red
        for button in (self.add_button, self.update_button,
                       self.delete_button, self.clear_button):
            button_row.addWidget(button)
        main_layout.addLayout(button_row)

        # --- search ---
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a name or roll number...")
        search_row.addWidget(self.search_input, 1)
        main_layout.addLayout(search_row)

        # --- table (subjects differ by year, so marks share one column) ---
        headers = ["Roll No", "Name", "Year", "Marks", "Total /500", "%", "Grade", "Active"]
        self.table = QTableWidget(0, len(headers))
        self.table.setAlternatingRowColors(True)           # striped rows
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)   # Name
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # Marks
        main_layout.addWidget(self.table, 1)   # stretch factor 1: table takes spare space

    # ---------- display ----------
    def update_subject_labels(self, year_text):
        """Show the subject names that belong to the chosen year."""
        if not year_text:
            return
        subjects = database.YEAR_SUBJECTS[int(year_text)]
        for key, name in zip(database.MARK_FIELDS, subjects):
            self.mark_labels[key].setText(name)

    def refresh_table(self, students=None):
        """Fill the table. With no argument it shows every student."""
        if students is None:
            students = database.get_all_students()
        self.current_students = students
        self.table.setRowCount(len(students))
        for row, s in enumerate(students):
            subjects = database.YEAR_SUBJECTS[s["year"]]
            marks_text = ",  ".join(
                f"{name} {s[key]}" for name, key in zip(subjects, database.MARK_FIELDS))
            values = [s["roll_no"], s["name"], s["year"], marks_text,
                      s["total"], s["percentage"], s["grade"],
                      "Yes" if s["active"] else "No"]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    # hide the database id inside the first cell for edit/delete later
                    item.setData(Qt.ItemDataRole.UserRole, s["id"])
                self.table.setItem(row, col, item)

    # ---------- signals and slots ----------
    def _connect_signals(self):
        self.add_button.clicked.connect(self.on_add)
        self.update_button.clicked.connect(self.on_update)
        self.delete_button.clicked.connect(self.on_delete)
        self.clear_button.clicked.connect(self.clear_form)
        self.search_input.textChanged.connect(self.on_search)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.about_action.triggered.connect(self.show_about)
        self.year_combo.currentTextChanged.connect(self.update_subject_labels)
        for spin in self.mark_inputs.values():
            spin.valueChanged.connect(self.update_preview)

    # ---------- helpers ----------
    def form_data(self):
        """Read every input into a dict that database.py can validate."""
        data = {
            "roll_no": self.roll_input.text(),
            "name": self.name_input.text(),
            "year": self.year_combo.currentText(),
            "active": self.active_check.isChecked(),
        }
        for key, spin in self.mark_inputs.items():
            data[key] = spin.value()
        return data

    def selected_id(self):
        """Database id of the selected table row, or None."""
        items = self.table.selectedItems()
        if not items:
            return None
        return self.table.item(items[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def show_error(self, message):
        QMessageBox.warning(self, "Please check your input", message)

    def reload_table(self):
        """Refresh the table, respecting whatever is typed in the search box."""
        text = self.search_input.text().strip()
        students = database.search_students(text) if text else None
        self.refresh_table(students)

    # ---------- slots (event handlers) ----------
    def on_add(self):
        try:
            database.add_student(self.form_data())
        except ValueError as err:          # validation or duplicate roll number
            self.show_error(str(err))
            return
        self.clear_form()
        self.reload_table()
        self.statusBar().showMessage("Student added.", 3000)

    def on_update(self):
        student_id = self.selected_id()
        if student_id is None:
            self.show_error("Select a student in the table first.")
            return
        try:
            database.update_student(student_id, self.form_data())
        except ValueError as err:
            self.show_error(str(err))
            return
        self.clear_form()
        self.reload_table()
        self.statusBar().showMessage("Student updated.", 3000)

    def on_delete(self):
        student_id = self.selected_id()
        if student_id is None:
            self.show_error("Select a student in the table first.")
            return
        answer = QMessageBox.question(
            self, "Confirm delete", "Delete this student permanently?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        database.delete_student(student_id)
        self.clear_form()
        self.reload_table()
        self.statusBar().showMessage("Student deleted.", 3000)

    def on_search(self, text):
        self.reload_table()

    def on_row_selected(self):
        """Copy the selected student into the form so it can be edited."""
        items = self.table.selectedItems()
        if not items:
            return
        s = self.current_students[items[0].row()]
        self.roll_input.setText(s["roll_no"])
        self.name_input.setText(s["name"])
        self.year_combo.setCurrentText(str(s["year"]))   # also updates subject labels
        for key in database.MARK_FIELDS:
            self.mark_inputs[key].setValue(s[key])
        self.active_check.setChecked(bool(s["active"]))

    def update_preview(self, value=None):
        """Live total/grade/progress bar while marks are being typed."""
        marks = {key: spin.value() for key, spin in self.mark_inputs.items()}
        result = database.calculate_result(marks)
        self.result_label.setText(
            f"Total: {result['total']} / 500    Grade: {result['grade']}")
        self.bar_anim = QPropertyAnimation(self.percent_bar, b"value")
        self.bar_anim.setDuration(300)
        self.bar_anim.setEndValue(int(result["percentage"]))
        self.bar_anim.start()

    def clear_form(self):
        self.table.clearSelection()
        self.roll_input.clear()
        self.name_input.clear()
        self.year_combo.setCurrentIndex(0)
        self.active_check.setChecked(True)
        for spin in self.mark_inputs.values():
            spin.setValue(0)
        self.roll_input.setFocus()

    def show_about(self):
        QMessageBox.about(
            self, "About",
            f"Student Record Manager\n\nStudent: {STUDENT_NAME}\n"
            f"Roll no: {ROLL_NUMBER}\nProgramme: B.Ed IT\nBuilt with PyQt6")