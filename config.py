"""
config.py
----------
Central place for all folder paths, filenames and tunable settings.
Change values here instead of hunting through the rest of the code.
"""

import os

# ---------------------------------------------------------------------
# BASE FOLDERS
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

STUDENT_PHOTOS_DIR = os.path.join(DATA_DIR, "student_photos")       # pre-fed student photos
CLASSROOM_UPLOADS_DIR = os.path.join(DATA_DIR, "classroom_uploads") # row-wise classroom photos
ATTENDANCE_EXCEL_DIR = os.path.join(DATA_DIR, "attendance_excel")   # daily + master excel reports
ENCODINGS_DIR = os.path.join(DATA_DIR, "encodings")                 # cached face encodings (.pkl)

DB_PATH = os.path.join(DATA_DIR, "attendance.db")
ENCODINGS_FILE = os.path.join(ENCODINGS_DIR, "face_encodings.pkl")
MASTER_EXCEL_FILE = os.path.join(ATTENDANCE_EXCEL_DIR, "Attendance_Master_Log.xlsx")

# make sure every folder exists the moment config.py is imported
for folder in (STUDENT_PHOTOS_DIR, CLASSROOM_UPLOADS_DIR,
               ATTENDANCE_EXCEL_DIR, ENCODINGS_DIR):
    os.makedirs(folder, exist_ok=True)

# ---------------------------------------------------------------------
# FACE RECOGNITION TUNING
# ---------------------------------------------------------------------
# Lower = stricter matching (fewer false positives, may miss some real matches)
# Higher = looser matching (catches more faces, but risk of wrong matches)
# 0.5-0.55 is a good starting point for classroom photos.
FACE_MATCH_TOLERANCE = 0.52

# Which face_recognition model to use for detection: "hog" (fast, CPU, default)
# or "cnn" (much more accurate, but slow without a GPU). For 10-20 students on
# a laptop, "hog" is recommended.
FACE_DETECTION_MODEL = "hog"

# ---------------------------------------------------------------------
# APP SETTINGS
# ---------------------------------------------------------------------
APP_TITLE = "AI Attendance System"
COLLEGE_NAME = "BLDE College of Engineering"
DEPARTMENT_NAME = "Department of Electronics & Communication Engineering"  # <-- edit as needed
DIVISIONS = ["A", "B", "C", "D"]             # <-- edit to match your class divisions

# ---------------------------------------------------------------------
# 7th SEMESTER SUBJECTS & TIMETABLE-ASSIGNED TEACHERS
# ---------------------------------------------------------------------
# Each subject has exactly one fixed teacher (per the timetable), and
# attendance is tracked separately per subject code.
SUBJECTS = [
    {"code": "CBEC701", "short": "MEA",  "name": "Microwave Engineering and Antenna Theory", "teacher": "Mr. A. S. Yaragal"},
    {"code": "CBEC702", "short": "CN&P", "name": "Computer Networks & Protocols",             "teacher": "Mr. M. N. Deshmukh"},
    {"code": "BEC703",  "short": "WCS",  "name": "Wireless Communication System",             "teacher": "Dr. S. K. Padaganur"},
    {"code": "BEC714A", "short": "ASIC", "name": "Application Specific Integrated Circuit",   "teacher": "Mr. V. C. Sajjanan"},
]
SUBJECT_BY_CODE = {s["code"]: s for s in SUBJECTS}


def subject_label(code):
    """Human-readable label for a subject code, e.g. 'CBEC701 - Microwave Engineering and Antenna Theory'."""
    s = SUBJECT_BY_CODE.get(code)
    return f"{s['code']} - {s['name']}" if s else (code or "")
