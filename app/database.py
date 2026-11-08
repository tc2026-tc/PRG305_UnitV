"""Data layer for the Student Record Manager. No GUI code in this file."""
import sqlite3
from contextlib import closing
from pathlib import Path

# Relative to this file, so it works on any computer (no hard-coded path)
DB_PATH = Path(__file__).resolve().parent.parent / "students.db"

# Five subjects per year. Marks are stored in mark1 ... mark5 in this order.
YEAR_SUBJECTS = {
    1: ["DZO", "PSY", "MATH", "IT", "EAE"],
    2: ["MATH", "EAE", "PSY", "EDU", "DDD"],
    3: ["MATH", "BPY", "DDD", "EDU", "RES"],
    4: ["EDU", "RES", "PRG 305", "PRG 404", "CAP"],
}
YEARS = sorted(YEAR_SUBJECTS)
MARK_FIELDS = ["mark1", "mark2", "mark3", "mark4", "mark5"]
COLUMNS = ["roll_no", "name", "year"] + MARK_FIELDS + ["active"]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    return conn


def init_db():
    """Create the students table if needed; keep data from an older layout."""
    with closing(_connect()) as conn, conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(students)")]
        if columns and "mark1" not in columns:
            # Old table (fixed subjects): keep it under another name
            conn.execute("DROP TABLE IF EXISTS students_old")
            conn.execute("ALTER TABLE students RENAME TO students_old")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                year INTEGER NOT NULL,
                mark1 INTEGER NOT NULL,
                mark2 INTEGER NOT NULL,
                mark3 INTEGER NOT NULL,
                mark4 INTEGER NOT NULL,
                mark5 INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )""")


def validate_student(data):
    """Return a cleaned copy of data, or raise ValueError with a friendly message."""
    roll_no = str(data.get("roll_no", "")).strip()
    name = str(data.get("name", "")).strip()
    if not roll_no:
        raise ValueError("Roll number is required.")
    if not name:
        raise ValueError("Name is required.")
    try:
        year = int(data.get("year"))
    except (TypeError, ValueError):
        raise ValueError("Year must be a number.")
    if year not in YEAR_SUBJECTS:
        raise ValueError("Year must be between 1 and 4.")

    clean = {"roll_no": roll_no, "name": name, "year": year,
             "active": 1 if data.get("active", True) else 0}
    for field, label in zip(MARK_FIELDS, YEAR_SUBJECTS[year]):
        try:
            mark = int(data.get(field))
        except (TypeError, ValueError):
            raise ValueError(f"{label} marks must be a whole number.")
        if not 0 <= mark <= 100:
            raise ValueError(f"{label} marks must be between 0 and 100.")
        clean[field] = mark
    return clean


def grade_for(percentage):
    """Convert a percentage to a letter grade (change the scale to your college's)."""
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 50:
        return "D"
    return "F"


def calculate_result(student):
    """Return total (out of 500), percentage and grade for one student."""
    total = sum(student[field] for field in MARK_FIELDS)
    percentage = round(total / len(MARK_FIELDS), 1)  # each subject is out of 100
    return {"total": total, "percentage": percentage, "grade": grade_for(percentage)}


def _with_result(row):
    student = dict(row)
    student.update(calculate_result(student))
    return student


def add_student(data):
    student = validate_student(data)
    placeholders = ", ".join(["?"] * len(COLUMNS))
    try:
        with closing(_connect()) as conn, conn:
            conn.execute(
                f"INSERT INTO students ({', '.join(COLUMNS)}) VALUES ({placeholders})",
                [student[c] for c in COLUMNS])
    except sqlite3.IntegrityError:
        raise ValueError(f"Roll number {student['roll_no']} already exists.")


def update_student(student_id, data):
    student = validate_student(data)
    assignments = ", ".join(f"{c} = ?" for c in COLUMNS)
    try:
        with closing(_connect()) as conn, conn:
            cursor = conn.execute(
                f"UPDATE students SET {assignments} WHERE id = ?",
                [student[c] for c in COLUMNS] + [student_id])
    except sqlite3.IntegrityError:
        raise ValueError(f"Roll number {student['roll_no']} already exists.")
    if cursor.rowcount == 0:
        raise ValueError("That student no longer exists.")


def delete_student(student_id):
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def get_all_students():
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    return [_with_result(row) for row in rows]


def search_students(text):
    """Find students whose name or roll number contains the text."""
    pattern = f"%{text.strip()}%"
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM students WHERE name LIKE ? OR roll_no LIKE ? ORDER BY roll_no",
            (pattern, pattern)).fetchall()
    return [_with_result(row) for row in rows]


if __name__ == "__main__":
    # Quick self-test: run with  python app/database.py
    init_db()
    sample = {"roll_no": "S001", "name": "Sample Student", "year": 1,
              "mark1": 75, "mark2": 68, "mark3": 82, "mark4": 71, "mark5": 90,
              "active": True}
    try:
        add_student(sample)
        print("Added sample student.")
    except ValueError as err:
        print("Could not add:", err)
    for s in get_all_students():
        print(s["roll_no"], s["name"], s["total"], s["percentage"], s["grade"])
    try:
        add_student({**sample, "roll_no": "S002", "mark1": 150})
    except ValueError as err:
        print("Validation works:", err)