"""
database.py
------------
All SQLite database logic lives here. SQLite needs no separate server -
it is just one file (data/attendance.db) sitting on your laptop, which is
perfect for a local, 10-20 student project.

Tables:
    students     -> pre-fed student data (photo, name, roll no, USN, division)
    professors   -> pre-fed professor data + login credentials
    attendance   -> one row per student per session (Present/Absent + timestamp)
"""

import sqlite3
import hashlib
from datetime import datetime

import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row       # lets us access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't already exist. Safe to call every run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            roll_no     TEXT NOT NULL UNIQUE,
            usn         TEXT NOT NULL UNIQUE,
            division    TEXT,
            photo_path  TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS professors (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            designation   TEXT,
            subject       TEXT,
            photo_path    TEXT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'teacher'
        )
    """)

    # migrate older databases created before the HOD/teacher role split existed
    existing_cols = {row["name"] for row in cur.execute("PRAGMA table_info(professors)").fetchall()}
    if "role" not in existing_cols:
        cur.execute("ALTER TABLE professors ADD COLUMN role TEXT NOT NULL DEFAULT 'teacher'")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            date          TEXT NOT NULL,
            time          TEXT NOT NULL,
            status        TEXT NOT NULL,
            subject       TEXT,
            professor_id  INTEGER,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (professor_id) REFERENCES professors (id) ON DELETE SET NULL,
            UNIQUE(student_id, date, subject)
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# PASSWORD HELPERS (simple sha256 hashing - fine for a local college project)
# ---------------------------------------------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# STUDENT CRUD
# ---------------------------------------------------------------------
def add_student(name, roll_no, usn, division, photo_path):
    conn = get_connection()
    conn.execute(
        "INSERT INTO students (name, roll_no, usn, division, photo_path, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, roll_no, usn, division, photo_path, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_by_id(student_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_student(student_id):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()


def roll_or_usn_exists(roll_no, usn):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM students WHERE roll_no = ? OR usn = ?", (roll_no, usn)
    ).fetchone()
    conn.close()
    return row is not None


def get_student_by_roll_and_usn(roll_no, usn):
    """Simple identity check used for student login (no password - read-only access)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE roll_no = ? AND usn = ?", (roll_no, usn)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------
# PROFESSOR CRUD + LOGIN
# ---------------------------------------------------------------------
def add_professor(name, designation, subject, photo_path, username, password, role="teacher"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO professors (name, designation, subject, photo_path, username, password_hash, role) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, designation, subject, photo_path, username, hash_password(password), role),
    )
    conn.commit()
    conn.close()


def any_professor_exists():
    conn = get_connection()
    row = conn.execute("SELECT id FROM professors LIMIT 1").fetchone()
    conn.close()
    return row is not None


def any_hod_exists():
    conn = get_connection()
    row = conn.execute("SELECT id FROM professors WHERE role = 'hod' LIMIT 1").fetchone()
    conn.close()
    return row is not None


def verify_professor(username, password, role=None):
    conn = get_connection()
    if role:
        row = conn.execute(
            "SELECT * FROM professors WHERE username = ? AND role = ?", (username, role)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM professors WHERE username = ?", (username,)
        ).fetchone()
    conn.close()
    if row and row["password_hash"] == hash_password(password):
        return dict(row)
    return None


def get_all_professors():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM professors").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_teachers():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM professors WHERE role = 'teacher' ORDER BY subject"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_professor_by_subject(subject_code):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM professors WHERE subject = ? AND role = 'teacher'", (subject_code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_professor(professor_id):
    conn = get_connection()
    conn.execute("DELETE FROM professors WHERE id = ?", (professor_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# ATTENDANCE
# ---------------------------------------------------------------------
def mark_attendance(student_id, date, time, status, subject, professor_id):
    """Insert a record; if one already exists for this student/date/subject, update it instead."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO attendance (student_id, date, time, status, subject, professor_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, date, subject)
        DO UPDATE SET status=excluded.status, time=excluded.time, professor_id=excluded.professor_id
        """,
        (student_id, date, time, status, subject, professor_id),
    )
    conn.commit()
    conn.close()


def get_attendance_by_date(date, subject=None):
    conn = get_connection()
    if subject:
        rows = conn.execute(
            """
            SELECT a.*, s.name, s.roll_no, s.usn, s.division
            FROM attendance a JOIN students s ON a.student_id = s.id
            WHERE a.date = ? AND a.subject = ?
            ORDER BY s.roll_no
            """,
            (date, subject),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT a.*, s.name, s.roll_no, s.usn, s.division
            FROM attendance a JOIN students s ON a.student_id = s.id
            WHERE a.date = ?
            ORDER BY s.roll_no
            """,
            (date,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_attendance_dates():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT date FROM attendance ORDER BY date DESC"
    ).fetchall()
    conn.close()
    return [r["date"] for r in rows]


def get_student_attendance_history(student_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? ORDER BY date DESC", (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
