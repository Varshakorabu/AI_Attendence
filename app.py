"""
app.py
------
The entire user interface, built with Streamlit (pure Python - no separate
HTML/CSS/JS files). Base colors/fonts come from the theme in
.streamlit/config.toml; a custom stylesheet (CUSTOM_CSS below) layers on
gradient hero banners, colored stat cards and login cards for a bolder,
more colorful look. CSS selectors target Streamlit's real, stable
data-testid hooks (verified against the installed frontend build) plus the
official `st.container(key=...)` -> `.st-key-<key>` mechanism.

Run with:
    streamlit run app.py

Pages:
    - Login (HOD / Subject Teacher / Student, role-based)
    - Dashboard (today's summary, quick stats)
    - Manage Students (add / view / delete pre-fed student data)
    - Manage Teachers (HOD only - create subject teacher accounts)
    - Take Attendance (upload classroom photo(s), run recognition)
    - Attendance Reports (browse past dates, download Excel)
    - My Attendance (read-only student portal)
"""

import html
import os
from datetime import date

import pandas as pd
import streamlit as st

import config
import database
import face_utils
import attendance_engine
import excel_utils

# ---------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# CUSTOM STYLESHEET (colorful layer on top of the base theme)
# ---------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@keyframes fadeInUp { from {opacity:0; transform:translateY(10px);} to {opacity:1; transform:translateY(0);} }

#MainMenu, footer {visibility: hidden;}

/* Streamlit paints an opaque background straight onto stAppViewContainer /
   stMain (on top of .stApp), so the gradient has to be forced onto all of
   them with !important or it gets hidden behind a flat white pane. */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background:
        radial-gradient(1200px 650px at 4% -12%, rgba(124,58,237,.30) 0%, transparent 55%),
        radial-gradient(1000px 600px at 104% 0%, rgba(236,72,153,.28) 0%, transparent 52%),
        radial-gradient(1000px 600px at 30% 115%, rgba(6,182,212,.26) 0%, transparent 52%),
        radial-gradient(800px 500px at 80% 110%, rgba(245,158,11,.20) 0%, transparent 50%),
        linear-gradient(165deg, #F3F0FF 0%, #FDF2F8 50%, #ECFEFF 100%) !important;
}
[data-testid="stHeader"] { background: transparent !important; }

.block-container { animation: fadeInUp .35s ease; }

/* ---- Hero banners ---- */
.hero-banner {
    position: relative; overflow: hidden;
    padding: 1.5rem 2rem; border-radius: 22px; margin-bottom: 1.3rem;
    color: #fff; box-shadow: 0 12px 30px -10px rgba(30,20,70,.35);
}
.hero-banner::after {
    content:""; position:absolute; inset:0;
    background: radial-gradient(480px 220px at 92% -25%, rgba(255,255,255,.28), transparent 60%);
}
.hero-banner .hero-icon {
    display:inline-flex; align-items:center; justify-content:center;
    width:50px; height:50px; border-radius:15px; font-size:1.55rem;
    background: rgba(255,255,255,.22); margin-bottom:.55rem;
    position:relative; z-index:1;
}
.hero-banner h1 { margin:0; font-size:1.85rem; font-weight:800; letter-spacing:-.02em; position:relative; z-index:1; color:#fff;}
.hero-banner p { margin:.25rem 0 0; opacity:.94; font-size:.98rem; position:relative; z-index:1;}
.hero-indigo { background: linear-gradient(120deg,#4338CA 0%, #7C3AED 55%, #C026D3 100%); }
.hero-teal   { background: linear-gradient(120deg,#0E7490 0%, #0891B2 55%, #06B6D4 100%); }
.hero-amber  { background: linear-gradient(120deg,#B45309 0%, #D97706 55%, #F59E0B 100%); }
.hero-rose   { background: linear-gradient(120deg,#9D174D 0%, #DB2777 55%, #EC4899 100%); }
.hero-violet { background: linear-gradient(120deg,#5B21B6 0%, #7C3AED 55%, #A855F7 100%); }
.hero-blue   { background: linear-gradient(120deg,#1E3A8A 0%, #2563EB 55%, #38BDF8 100%); }

/* ---- Stat cards ---- */
.stat-row { display:flex; gap:14px; flex-wrap:wrap; margin: .3rem 0 1.3rem; }
.stat-card {
    flex:1 1 170px; border-radius:16px; padding:1rem 1.15rem;
    background:#fff; border:1px solid #ECECF5;
    box-shadow: 0 3px 12px rgba(20,20,60,.06);
    transition: transform .15s ease, box-shadow .15s ease;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 12px 24px rgba(20,20,60,.12); }
.stat-card .stat-icon { font-size:1.25rem; }
.stat-card .stat-value { font-size:1.75rem; font-weight:800; margin-top:.15rem; line-height:1.1; }
.stat-card .stat-label { font-size:.8rem; color:#6B7280; font-weight:700; text-transform:uppercase; letter-spacing:.03em; margin-top:.15rem;}
.stat-indigo{ border-left:5px solid #4F46E5;} .stat-indigo .stat-value{color:#4338CA;}
.stat-green { border-left:5px solid #16A34A;} .stat-green .stat-value{color:#15803D;}
.stat-red   { border-left:5px solid #DC2626;} .stat-red .stat-value{color:#B91C1C;}
.stat-violet{ border-left:5px solid #7C3AED;} .stat-violet .stat-value{color:#6D28D9;}
.stat-amber { border-left:5px solid #D97706;} .stat-amber .stat-value{color:#B45309;}
.stat-blue  { border-left:5px solid #2563EB;} .stat-blue .stat-value{color:#1D4ED8;}

/* ---- Buttons ---- */
button[data-testid="stBaseButton-primary"], .stButton>button[kind="primary"] {
    background: linear-gradient(135deg,#4F46E5 0%, #9333EA 100%) !important;
    border:none !important; color:#fff !important; font-weight:700 !important;
    box-shadow: 0 6px 16px rgba(79,70,229,.35) !important;
    transition: all .15s ease !important;
}
button[data-testid="stBaseButton-primary"]:hover, .stButton>button[kind="primary"]:hover {
    transform: translateY(-2px); filter: brightness(1.06);
    box-shadow: 0 10px 24px rgba(79,70,229,.45) !important;
}
button[data-testid="stBaseButton-secondary"], .stButton>button[kind="secondary"] {
    border:1.5px solid #C7C7E8 !important; font-weight:600 !important;
    transition: all .15s ease !important;
}
button[data-testid="stBaseButton-secondary"]:hover, .stButton>button[kind="secondary"]:hover {
    border-color:#7C3AED !important; color:#7C3AED !important; transform: translateY(-1px);
}
button[data-testid="stBaseButton-tertiary"] { font-weight:600 !important; }
div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button,
div[data-testid="stDownloadButton"] button { border-radius: 12px !important; }

/* ---- Sidebar ---- */
[data-testid="stSidebarContent"] {
    background: linear-gradient(190deg, #1E1147 0%, #2A1E63 45%, #17123B 100%) !important;
}
[data-testid="stSidebarContent"] [data-testid="stRadioOption"] {
    border-radius: 12px; padding: 3px 8px; margin-bottom:3px;
    transition: background .15s ease;
}
[data-testid="stSidebarContent"] [data-testid="stRadioOption"]:hover {
    background: rgba(255,255,255,.08);
}
[data-testid="stSidebarContent"] [data-testid="stRadioOption"]:has(input:checked) {
    background: linear-gradient(90deg, rgba(167,139,250,.4), rgba(167,139,250,.08));
    box-shadow: inset 3px 0 0 #C4B5FD;
}

/* ---- Login role cards (via st.container(key=...)) ---- */
.st-key-card_teacher, .st-key-card_hod, .st-key-card_student {
    border-radius:20px !important; padding: 1.5rem !important; border: none !important;
    transition: transform .18s ease, box-shadow .18s ease;
    box-shadow: 0 10px 24px -10px rgba(20,20,60,.4);
}
.st-key-card_teacher { background: linear-gradient(150deg,#0EA5E9,#4F46E5) !important; }
.st-key-card_hod     { background: linear-gradient(150deg,#A855F7,#DB2777) !important; }
.st-key-card_student  { background: linear-gradient(150deg,#F59E0B,#EF4444) !important; }
.st-key-card_teacher:hover, .st-key-card_hod:hover, .st-key-card_student:hover {
    transform: translateY(-5px); box-shadow: 0 20px 34px -12px rgba(20,20,60,.5);
}
.st-key-card_teacher *, .st-key-card_hod *, .st-key-card_student * { color:#fff !important; }
.st-key-card_teacher button, .st-key-card_hod button, .st-key-card_student button {
    background: rgba(255,255,255,.2) !important; border:1.5px solid rgba(255,255,255,.55) !important;
}
.st-key-card_teacher button:hover, .st-key-card_hod button:hover, .st-key-card_student button:hover {
    background: rgba(255,255,255,.32) !important;
}

/* ---- Manage students/teachers row cards ---- */
[class*="st-key-row_"] { border-radius:14px !important; transition: box-shadow .15s ease, transform .15s ease; }
[class*="st-key-row_"]:hover { box-shadow: 0 8px 18px rgba(20,20,60,.08); transform: translateY(-1px); }

/* ---- Forms ---- */
[data-testid="stForm"] {
    border-radius:18px !important; box-shadow: 0 4px 18px rgba(20,20,60,.07);
    border-top: 4px solid #7C3AED !important;
}

/* ---- Dataframe ---- */
[data-testid="stDataFrame"] { border-radius:14px; overflow:hidden; box-shadow:0 3px 12px rgba(20,20,60,.06); }
</style>
"""
st.html(CUSTOM_CSS)

NAV_ICONS = {
    "Dashboard": "🏠",
    "Manage students": "🧑‍🎓",
    "Manage teachers": "👩‍🏫",
    "Take attendance": "📸",
    "Attendance reports": "🗂️",
}

STAT_COLORS = {"indigo", "green", "red", "violet", "amber", "blue"}


def page_header(icon, title, subtitle="", variant="indigo"):
    st.html(
        f"""
        <div class="hero-banner hero-{variant}">
            <div class="hero-icon">{icon}</div>
            <h1>{html.escape(str(title))}</h1>
            <p>{html.escape(str(subtitle))}</p>
        </div>
        """
    )


def stat_row(items):
    """items: list of (icon, label, value, color) - color in STAT_COLORS."""
    cards = "".join(
        f"""
        <div class="stat-card stat-{color if color in STAT_COLORS else 'indigo'}">
            <div class="stat-icon">{icon}</div>
            <div class="stat-value">{html.escape(str(value))}</div>
            <div class="stat-label">{html.escape(str(label))}</div>
        </div>
        """
        for icon, label, value, color in items
    )
    st.html(f'<div class="stat-row">{cards}</div>')


def status_table(rows, **column_config):
    """Render a list-of-dicts table with Present/Absent cells color-coded."""
    df = pd.DataFrame(rows)
    if df.empty:
        st.caption("Nothing to show yet.")
        return

    def _status_style(val):
        if val == "Present":
            return "background-color:#DCFCE7;color:#14532D;font-weight:600;"
        if val == "Absent":
            return "background-color:#FEE2E2;color:#7F1D1D;font-weight:600;"
        return ""

    data = df.style.map(_status_style, subset=["Status"]) if "Status" in df.columns else df
    st.dataframe(data, hide_index=True, column_config=column_config or None)


# ---------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------
database.init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "professor" not in st.session_state:
    st.session_state.professor = None
if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
if "student" not in st.session_state:
    st.session_state.student = None
if "login_role" not in st.session_state:
    st.session_state.login_role = None


# ---------------------------------------------------------------------
# LOGIN / FIRST-TIME SETUP
# ---------------------------------------------------------------------
def render_login():
    st.title(f":primary[:material/school:]  {config.APP_TITLE}", text_alignment="center")
    st.caption(f"{config.COLLEGE_NAME} · {config.DEPARTMENT_NAME}", text_alignment="center")
    st.space("large")

    if not database.any_hod_exists():
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.info("No HOD account exists yet. Create it first to get started.", icon=":material/info:")
            with st.form("create_hod_form"):
                st.subheader("Create HOD account")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Full name")
                    username = st.text_input("Choose a username")
                with col2:
                    designation = st.text_input("Designation", value="Head of Department")
                    password = st.text_input("Choose a password", type="password")

                submitted = st.form_submit_button(
                    "Create HOD account", type="primary", icon=":material/person_add:"
                )
                if submitted:
                    if not (name and username and password):
                        st.error("Name, username and password are required.")
                    else:
                        database.add_professor(name, designation, None, "", username, password, role="hod")
                        st.success("HOD account created. Please log in below.")
                        st.rerun()
        return

    if st.session_state.login_role is None:
        _, mid, _ = st.columns([1, 3, 1])
        with mid:
            cols = st.columns(2)
            with cols[0]:
                with st.container(border=True, key="card_teacher"):
                    st.markdown("### 👨‍🏫")
                    st.markdown("**Subject teacher**")
                    st.caption("Take attendance and view reports for your own subject.")
                    if st.button(
                        "Continue", key="pick_teacher", type="primary",
                        icon=":material/login:", width="stretch",
                    ):
                        st.session_state.login_role = "teacher"
                        st.rerun()
            with cols[1]:
                with st.container(border=True, key="card_hod"):
                    st.markdown("### 🧑‍💼")
                    st.markdown("**HOD**")
                    st.caption("Manage teachers, students, and all department reports.")
                    if st.button(
                        "Continue", key="pick_hod", type="primary",
                        icon=":material/login:", width="stretch",
                    ):
                        st.session_state.login_role = "hod"
                        st.rerun()

            with st.container(border=True, key="card_student"):
                st.markdown("### 🎓")
                st.markdown("**Student**")
                st.caption("View your own attendance record only - read-only access.")
                if st.button(
                    "Continue", key="pick_student", type="primary",
                    icon=":material/login:", width="stretch",
                ):
                    st.session_state.login_role = "student"
                    st.rerun()
        return

    role = st.session_state.login_role
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if role == "student":
            st.subheader("Student login")
            with st.form("student_login_form"):
                roll_no = st.text_input("Roll number")
                usn = st.text_input("USN")
                submitted = st.form_submit_button("Log in", type="primary", icon=":material/login:")
                if submitted:
                    student = database.get_student_by_roll_and_usn(roll_no, usn)
                    if student:
                        st.session_state.student_logged_in = True
                        st.session_state.student = student
                        st.rerun()
                    else:
                        st.error("No student found with that roll number and USN.")
        else:
            st.subheader("HOD login" if role == "hod" else "Subject teacher login")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", type="primary", icon=":material/login:")
                if submitted:
                    professor = database.verify_professor(username, password, role=role)
                    if professor:
                        st.session_state.logged_in = True
                        st.session_state.professor = professor
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        if st.button("Back", icon=":material/arrow_back:", type="tertiary"):
            st.session_state.login_role = None
            st.rerun()


# ---------------------------------------------------------------------
# STUDENT PORTAL (read-only, own attendance only)
# ---------------------------------------------------------------------
def render_student_portal():
    student = st.session_state.student

    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(width="stretch"):
            page_header(
                "🎓", "My attendance",
                f"{student['name']} · Roll no. {student['roll_no']} · USN {student['usn']}",
                variant="rose",
            )
        if st.button("Log out", icon=":material/logout:"):
            st.session_state.student_logged_in = False
            st.session_state.student = None
            st.session_state.login_role = None
            st.rerun()

    history = database.get_student_attendance_history(student["id"])
    if not history:
        st.info("No attendance has been recorded for you yet.", icon=":material/info:")
        return

    subject_codes = sorted({r["subject"] for r in history if r["subject"]})
    summary_rows = []
    for code in subject_codes:
        sessions = [r for r in history if r["subject"] == code]
        present = len([r for r in sessions if r["status"] == "Present"])
        total = len(sessions)
        summary_rows.append(
            {
                "Subject": config.subject_label(code),
                "Sessions held": total,
                "Present": present,
                "Attendance %": round((present / total) * 100, 1) if total else 0.0,
            }
        )

    overall_present = len([r for r in history if r["status"] == "Present"])
    overall_pct = round((overall_present / len(history)) * 100, 1) if history else 0.0

    stat_row(
        [
            ("📈", "Overall attendance", f"{overall_pct}%", "blue"),
            ("🗓️", "Sessions recorded", len(history), "violet"),
            ("📚", "Subjects", len(subject_codes), "amber"),
        ]
    )

    st.subheader("Attendance summary")
    st.dataframe(
        pd.DataFrame(summary_rows),
        hide_index=True,
        column_config={
            "Attendance %": st.column_config.ProgressColumn(
                "Attendance %", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
    )

    st.subheader("Session-wise history")
    status_table(
        [
            {
                "Date": r["date"], "Time": r["time"],
                "Subject": config.subject_label(r["subject"]), "Status": r["status"],
            }
            for r in history
        ]
    )

    if st.button("Generate my attendance excel", icon=":material/description:"):
        try:
            report_path = excel_utils.generate_student_report(student["id"])
            with open(report_path, "rb") as f:
                st.download_button(
                    "Download my attendance excel",
                    data=f.read(),
                    file_name=os.path.basename(report_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    icon=":material/download:",
                )
        except Exception as e:
            st.error(f"Could not generate report: {e}")


# ---------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------
def render_dashboard():
    professor = st.session_state.professor
    page_header("📊", "Dashboard", f"Welcome back, {professor['name']}", variant="indigo")

    students = database.get_all_students()
    today = date.today().strftime("%Y-%m-%d")

    if professor["role"] == "teacher":
        subject_code = professor["subject"]
        st.caption(f":material/menu_book: {config.subject_label(subject_code)}")
        today_records = database.get_attendance_by_date(today, subject=subject_code)
    else:
        today_records = database.get_attendance_by_date(today)

    present_today = len([r for r in today_records if r["status"] == "Present"])
    absent_today = len([r for r in today_records if r["status"] == "Absent"])

    stat_row(
        [
            ("🧑‍🎓", "Total students registered", len(students), "indigo"),
            ("✅", "Present today", present_today, "green"),
            ("❌", "Absent today", absent_today, "red"),
        ]
    )

    st.subheader("Today's attendance")
    if today_records:
        rows = [
            {
                "Roll No": r["roll_no"],
                "Name": r["name"],
                "Division": r["division"],
                "Status": r["status"],
                "Time": r["time"],
                "Subject": config.subject_label(r["subject"]),
            }
            for r in today_records
        ]
        status_table(rows)
    else:
        st.caption("No attendance taken yet today. Go to **Take attendance** in the sidebar.")


# ---------------------------------------------------------------------
# MANAGE STUDENTS
# ---------------------------------------------------------------------
def render_manage_students():
    page_header("🧑‍🎓", "Manage students", "Pre-feed student details (10-20 students recommended)", variant="teal")

    tab_add, tab_view = st.tabs([":material/add: Add student", ":material/list: View / delete students"])

    with tab_add:
        with st.form("add_student_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full name*")
                roll_no = st.text_input("Roll number*")
            with col2:
                usn = st.text_input("University serial number (USN)*")
                division = st.selectbox("Division", config.DIVISIONS)

            photo = st.file_uploader(
                "Student photo* (clear, front-facing, single face)",
                type=["jpg", "jpeg", "png"],
            )

            submitted = st.form_submit_button("Add student", type="primary", icon=":material/person_add:")
            if submitted:
                if not (name and roll_no and usn and photo):
                    st.error("Please fill all required fields and upload a photo.")
                elif database.roll_or_usn_exists(roll_no, usn):
                    st.error("A student with this roll number or USN already exists.")
                else:
                    ext = os.path.splitext(photo.name)[1]
                    safe_name = f"{roll_no}_{usn}{ext}"
                    photo_path = os.path.join(config.STUDENT_PHOTOS_DIR, safe_name)
                    with open(photo_path, "wb") as f:
                        f.write(photo.getbuffer())

                    # sanity check: make sure a face can actually be found
                    test_encoding = face_utils.encode_single_photo(photo_path)
                    if test_encoding is None:
                        os.remove(photo_path)
                        st.error(
                            "No clear face could be detected in that photo. "
                            "Please upload a clearer, front-facing photo."
                        )
                    else:
                        database.add_student(name, roll_no, usn, division, photo_path)
                        face_utils.refresh_encodings()
                        st.success(f"{name} added successfully!")

    with tab_view:
        students = database.get_all_students()
        if not students:
            st.caption("No students added yet.")
        else:
            for s in students:
                with st.container(border=True, horizontal=True, vertical_alignment="center", key=f"row_student_{s['id']}"):
                    if os.path.exists(s["photo_path"]):
                        st.image(s["photo_path"], width=56)
                    with st.container(width="stretch"):
                        st.markdown(f"**{s['name']}**")
                        st.caption(f"Roll no. {s['roll_no']} · USN {s['usn']} · Division {s['division']}")
                    if st.button("Delete", key=f"del_{s['id']}", icon=":material/delete:", type="tertiary"):
                        if os.path.exists(s["photo_path"]):
                            os.remove(s["photo_path"])
                        database.delete_student(s["id"])
                        face_utils.refresh_encodings()
                        st.toast(f"Removed {s['name']}.", icon=":material/delete:")
                        st.rerun()


# ---------------------------------------------------------------------
# MANAGE TEACHERS (HOD only)
# ---------------------------------------------------------------------
def render_manage_teachers():
    page_header(
        "👩‍🏫", "Manage subject teachers",
        "Create login accounts for each 7th sem subject teacher", variant="violet",
    )

    with st.form("add_teacher_form", clear_on_submit=True):
        subject_code = st.selectbox(
            "Subject*", [s["code"] for s in config.SUBJECTS], format_func=config.subject_label
        )
        subj = config.SUBJECT_BY_CODE[subject_code]
        st.text_input("Teacher name", value=subj["teacher"], disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username*")
        with col2:
            password = st.text_input("Password*", type="password")

        submitted = st.form_submit_button(
            "Create teacher account", type="primary", icon=":material/person_add:"
        )
        if submitted:
            if not (username and password):
                st.error("Username and password are required.")
            elif database.get_professor_by_subject(subject_code):
                st.error(f"A teacher account already exists for {config.subject_label(subject_code)}.")
            else:
                database.add_professor(
                    subj["teacher"], "Subject Teacher", subject_code, "", username, password, role="teacher"
                )
                st.success(f"Account created for {subj['teacher']} ({subject_code}).")
                st.rerun()

    st.subheader("Existing teacher accounts")
    teachers = database.get_teachers()
    if not teachers:
        st.caption("No teacher accounts created yet.")
    else:
        for t in teachers:
            with st.container(border=True, horizontal=True, vertical_alignment="center", key=f"row_teacher_{t['id']}"):
                with st.container(width="stretch"):
                    st.markdown(f"**{t['name']}**")
                    st.caption(f"{config.subject_label(t['subject'])} · Username `{t['username']}`")
                if st.button("Delete", key=f"del_teacher_{t['id']}", icon=":material/delete:", type="tertiary"):
                    database.delete_professor(t["id"])
                    st.toast("Teacher account removed.", icon=":material/delete:")
                    st.rerun()


# ---------------------------------------------------------------------
# TAKE ATTENDANCE
# ---------------------------------------------------------------------
def render_take_attendance():
    page_header(
        "📸", "Take attendance",
        "Upload row-wise classroom photo(s) to auto-mark attendance", variant="amber",
    )

    students = database.get_all_students()
    if not students:
        st.warning("Please add students first (see 'Manage students').", icon=":material/warning:")
        return

    professor = st.session_state.professor
    if professor["role"] == "teacher":
        subject = professor["subject"]
        st.text_input("Subject", value=config.subject_label(subject), disabled=True)
    else:
        subject = st.selectbox(
            "Subject*", [s["code"] for s in config.SUBJECTS], format_func=config.subject_label
        )

    session_date = st.date_input("Session date", value=date.today())

    images = st.file_uploader(
        "Upload one or more classroom photos (multiple row photos supported)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if st.button(
        "Run face recognition & mark attendance", type="primary",
        icon=":material/face:", disabled=not (subject and images),
    ):
        with st.spinner("Detecting and recognizing faces..."):
            saved_paths = []
            for img in images:
                path = os.path.join(
                    config.CLASSROOM_UPLOADS_DIR,
                    f"{session_date}_{subject}_{img.name}",
                )
                with open(path, "wb") as f:
                    f.write(img.getbuffer())
                saved_paths.append(path)

            result = attendance_engine.process_classroom_images(
                saved_paths,
                subject=subject,
                professor_id=professor["id"],
                session_date=session_date.strftime("%Y-%m-%d"),
            )

        st.success("Attendance recorded.", icon=":material/check_circle:")
        stat_row(
            [
                ("✅", "Present", len(result["present_ids"]), "green"),
                ("❌", "Absent", len(result["absent_ids"]), "red"),
                ("❔", "Unrecognized faces", result["unknown_faces_count"], "amber"),
            ]
        )

        st.subheader("Annotated photos")
        st.caption(":green[Green] = recognized · :red[Red] = unknown face")
        cols = st.columns(min(3, len(result["annotated_images"])) or 1)
        for i, img in enumerate(result["annotated_images"]):
            cols[i % len(cols)].image(img, width="stretch")

        col_p, col_a = st.columns(2)
        with col_p:
            st.markdown(":green[**Present students**]")
            present_students = [database.get_student_by_id(sid) for sid in result["present_ids"]]
            if present_students:
                st.dataframe(
                    [{"Roll No": s["roll_no"], "Name": s["name"], "USN": s["usn"]} for s in present_students],
                    hide_index=True,
                )
            else:
                st.caption("No known students were recognized in the uploaded photo(s).")

        with col_a:
            st.markdown(":red[**Absent students**]")
            absent_students = [database.get_student_by_id(sid) for sid in result["absent_ids"]]
            if absent_students:
                st.dataframe(
                    [{"Roll No": s["roll_no"], "Name": s["name"], "USN": s["usn"]} for s in absent_students],
                    hide_index=True,
                )

        try:
            excel_path = excel_utils.generate_daily_excel(result["date"], subject=result["subject"])
            with open(excel_path, "rb") as f:
                st.download_button(
                    "Download today's excel report",
                    data=f.read(),
                    file_name=os.path.basename(excel_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    icon=":material/download:",
                )
        except Exception as e:
            st.error(f"Could not generate Excel report: {e}")


# ---------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------
def render_reports():
    page_header(
        "🗂️", "Attendance reports",
        "Browse past sessions and download Excel reports", variant="blue",
    )

    professor = st.session_state.professor
    role = professor["role"]

    dates = database.get_all_attendance_dates()
    if not dates:
        st.info("No attendance has been recorded yet.", icon=":material/info:")
        return

    selected_date = st.selectbox("Select a date", dates)

    if role == "teacher":
        selected_subject = professor["subject"]
        st.caption(f":material/menu_book: {config.subject_label(selected_subject)}")
        filtered = database.get_attendance_by_date(selected_date, subject=selected_subject)
    else:
        records = database.get_attendance_by_date(selected_date)
        subjects = sorted({r["subject"] for r in records if r["subject"]})
        selected_subject = st.selectbox(
            "Filter by subject", ["All"] + subjects,
            format_func=lambda c: "All subjects" if c == "All" else config.subject_label(c),
        )
        filtered = records if selected_subject == "All" else [r for r in records if r["subject"] == selected_subject]

    present = [r for r in filtered if r["status"] == "Present"]
    absent = [r for r in filtered if r["status"] == "Absent"]

    stat_row([("✅", "Present", len(present), "green"), ("❌", "Absent", len(absent), "red")])

    status_table(
        [
            {
                "Roll No": r["roll_no"], "Name": r["name"], "USN": r["usn"],
                "Division": r["division"], "Status": r["status"],
                "Time": r["time"], "Subject": config.subject_label(r["subject"]),
            }
            for r in filtered
        ]
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Generate / refresh excel for this view", icon=":material/description:"):
            try:
                subject_arg = None if selected_subject == "All" else selected_subject
                excel_path = excel_utils.generate_daily_excel(selected_date, subject=subject_arg)
                with open(excel_path, "rb") as f:
                    st.download_button(
                        "Download excel report",
                        data=f.read(),
                        file_name=os.path.basename(excel_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_daily",
                        icon=":material/download:",
                    )
            except Exception as e:
                st.error(f"Could not generate Excel report: {e}")

    with col_b:
        if selected_subject != "All" and st.button(
            "Generate attendance register (roll no. wise, with %)", icon=":material/percent:"
        ):
            try:
                reg_path = excel_utils.generate_subject_register(selected_subject)
                with open(reg_path, "rb") as f:
                    st.download_button(
                        "Download attendance register",
                        data=f.read(),
                        file_name=os.path.basename(reg_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_register",
                        icon=":material/download:",
                    )
            except Exception as e:
                st.error(f"Could not generate register: {e}")

    if role == "hod" and os.path.exists(config.MASTER_EXCEL_FILE):
        with open(config.MASTER_EXCEL_FILE, "rb") as f:
            st.download_button(
                "Download full master log (all dates, all subjects)",
                data=f.read(),
                file_name="Attendance_Master_Log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_master",
                icon=":material/download:",
            )


# ---------------------------------------------------------------------
# MAIN NAVIGATION
# ---------------------------------------------------------------------
def main():
    if st.session_state.student_logged_in:
        render_student_portal()
        return

    if not st.session_state.logged_in:
        render_login()
        return

    professor = st.session_state.professor
    role = professor["role"]

    with st.sidebar:
        st.markdown(f"### :primary[:material/school:] {config.APP_TITLE}")
        st.caption(config.COLLEGE_NAME)

        if role == "hod":
            st.badge("HOD", icon=":material/supervisor_account:", color="violet")
            st.write(f"**{professor['name']}**")
            pages = ["Dashboard", "Manage students", "Manage teachers", "Take attendance", "Attendance reports"]
        else:
            st.badge("Subject teacher", icon=":material/person:", color="blue")
            st.write(f"**{professor['name']}**")
            st.caption(config.subject_label(professor["subject"]))
            pages = ["Dashboard", "Manage students", "Take attendance", "Attendance reports"]

        page = st.radio(
            "Navigate", pages,
            format_func=lambda p: f"{NAV_ICONS.get(p, '')}  {p}",
            label_visibility="collapsed",
        )

        st.space("large")
        if st.button("Log out", icon=":material/logout:", width="stretch"):
            st.session_state.logged_in = False
            st.session_state.professor = None
            st.session_state.login_role = None
            st.rerun()

    if page == "Dashboard":
        render_dashboard()
    elif page == "Manage students":
        render_manage_students()
    elif page == "Manage teachers":
        render_manage_teachers()
    elif page == "Take attendance":
        render_take_attendance()
    elif page == "Attendance reports":
        render_reports()


if __name__ == "__main__":
    main()
