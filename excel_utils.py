"""
excel_utils.py
--------------
Generates the daily Excel attendance report (as required in the synopsis)
using openpyxl + pandas. Two things are produced every time attendance is
taken:

1. A per-day workbook: data/attendance_excel/Attendance_YYYY-MM-DD.xlsx
   - Sheet "Attendance": Roll No | USN | Name | Division | Status | Time
   - Sheet "Summary":    Total Present, Total Absent, Present Roll Nos,
                          Absent Roll Nos

2. A running master log: data/attendance_excel/Attendance_Master_Log.xlsx
   which appends every session ever taken, so the professor has one file
   with full history across all dates/subjects.
"""

import os
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

import config
import database


HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _style_header(ws):
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col)].width = 18


def generate_daily_excel(date, subject=None):
    """
    Build/overwrite the day's Excel report from whatever is currently in the
    database for that date, and append the session to the master log.
    Returns the path to the daily Excel file.
    """
    records = database.get_attendance_by_date(date, subject=subject)

    if not records:
        raise ValueError(f"No attendance records found for {date}.")

    df = pd.DataFrame(
        [
            {
                "Roll No": r["roll_no"],
                "USN": r["usn"],
                "Name": r["name"],
                "Division": r["division"],
                "Status": r["status"],
                "Time": r["time"],
                "Subject": r["subject"],
            }
            for r in records
        ]
    ).sort_values("Roll No")

    present_df = df[df["Status"] == "Present"]
    absent_df = df[df["Status"] == "Absent"]

    subject_tag = f"_{subject}" if subject else ""
    filename = f"Attendance_{date}{subject_tag}.xlsx"
    filepath = os.path.join(config.ATTENDANCE_EXCEL_DIR, filename)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Attendance", index=False)

        summary_data = {
            "Metric": [
                "Date",
                "Subject",
                "Total Students",
                "Total Present",
                "Total Absent",
                "Present Roll Numbers",
                "Absent Roll Numbers",
            ],
            "Value": [
                date,
                subject or "All Subjects",
                len(df),
                len(present_df),
                len(absent_df),
                ", ".join(present_df["Roll No"].astype(str)) or "None",
                ", ".join(absent_df["Roll No"].astype(str)) or "None",
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)

    # apply header styling
    wb = load_workbook(filepath)
    for sheet_name in wb.sheetnames:
        _style_header(wb[sheet_name])
    wb.save(filepath)

    _append_to_master_log(df)

    return filepath


def _append_to_master_log(session_df):
    """
    Append this session's rows to the running master Excel log, keeping a
    separate sheet per subject so each subject's attendance history stays
    independent.
    """
    session_df = session_df.copy()
    session_df.insert(0, "Logged At", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if os.path.exists(config.MASTER_EXCEL_FILE):
        book_sheets = pd.read_excel(config.MASTER_EXCEL_FILE, sheet_name=None)
    else:
        book_sheets = {}

    for subject_code, subject_rows in session_df.groupby("Subject", dropna=True):
        sheet_name = str(subject_code)[:31]
        if sheet_name in book_sheets:
            book_sheets[sheet_name] = pd.concat([book_sheets[sheet_name], subject_rows], ignore_index=True)
        else:
            book_sheets[sheet_name] = subject_rows

    with pd.ExcelWriter(config.MASTER_EXCEL_FILE, engine="openpyxl") as writer:
        for sheet_name, sheet_df in book_sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    wb = load_workbook(config.MASTER_EXCEL_FILE)
    for sheet_name in wb.sheetnames:
        _style_header(wb[sheet_name])
    wb.save(config.MASTER_EXCEL_FILE)


def generate_subject_register(subject_code):
    """
    Build a roll-no-wise attendance register for a single subject: one row
    per student, one column per session date that subject was taken, and a
    final "Attendance %" column. Saved as Register_<SUBJECT_CODE>.xlsx.
    Returns the path to the generated file.
    """
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT a.student_id, a.date, a.status
        FROM attendance a
        WHERE a.subject = ?
        """,
        (subject_code,),
    ).fetchall()
    conn.close()
    records = [dict(r) for r in rows]

    if not records:
        raise ValueError(f"No attendance records found for subject {subject_code}.")

    students = database.get_all_students()
    session_dates = sorted({r["date"] for r in records})
    status_lookup = {(r["student_id"], r["date"]): r["status"] for r in records}

    table_rows = []
    for s in students:
        row = {"Roll No": s["roll_no"], "USN": s["usn"], "Name": s["name"], "Division": s["division"]}
        present_count = 0
        for d in session_dates:
            status = status_lookup.get((s["id"], d))
            row[d] = "P" if status == "Present" else ("A" if status == "Absent" else "-")
            if status == "Present":
                present_count += 1
        row["Attendance %"] = round((present_count / len(session_dates)) * 100, 1) if session_dates else 0.0
        table_rows.append(row)

    df = pd.DataFrame(table_rows).sort_values("Roll No")

    subj = config.SUBJECT_BY_CODE.get(subject_code, {})
    filename = f"Register_{subject_code}.xlsx"
    filepath = os.path.join(config.ATTENDANCE_EXCEL_DIR, filename)
    sheet_name = (subj.get("short") or subject_code)[:31]

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    wb = load_workbook(filepath)
    _style_header(wb[sheet_name])
    wb.save(filepath)

    return filepath


def generate_student_report(student_id):
    """
    Build a personal attendance excel for one student: a per-subject summary
    (sessions held, present, attendance %) plus a full session-by-session
    detail sheet. Used by the read-only Student Login portal.
    Saved as Student_<ROLL_NO>.xlsx. Returns the path to the generated file.
    """
    student = database.get_student_by_id(student_id)
    if not student:
        raise ValueError("Student not found.")

    history = database.get_student_attendance_history(student_id)
    if not history:
        raise ValueError("No attendance records found yet.")

    subject_codes = sorted({r["subject"] for r in history if r["subject"]})

    summary_rows = []
    for code in subject_codes:
        sessions = [r for r in history if r["subject"] == code]
        present = len([r for r in sessions if r["status"] == "Present"])
        total = len(sessions)
        summary_rows.append(
            {
                "Subject": config.subject_label(code),
                "Sessions Held": total,
                "Present": present,
                "Attendance %": round((present / total) * 100, 1) if total else 0.0,
            }
        )
    summary_df = pd.DataFrame(summary_rows)

    detail_df = pd.DataFrame(
        [
            {
                "Date": r["date"],
                "Time": r["time"],
                "Subject": config.subject_label(r["subject"]),
                "Status": r["status"],
            }
            for r in history
        ]
    ).sort_values(["Subject", "Date"])

    filename = f"Student_{student['roll_no']}.xlsx"
    filepath = os.path.join(config.ATTENDANCE_EXCEL_DIR, filename)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        detail_df.to_excel(writer, sheet_name="Session Details", index=False)

    wb = load_workbook(filepath)
    for sheet_name in wb.sheetnames:
        _style_header(wb[sheet_name])
    wb.save(filepath)

    return filepath
