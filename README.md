# 🎓 AI-Based Face Recognition Attendance Management System

A fully working, **100% Python** implementation of your synopsis:
Streamlit for the interface (frontend + backend logic combined, no HTML/CSS/JS
files needed), SQLite for the database (no server install), and the
`face_recognition` (dlib-based) library for face detection & recognition —
exactly the tech stack named in your synopsis, just swapping MERN → Streamlit
so the **entire project is Python**, which is easier for one person to build,
run, and demo from a laptop.

---

## 1. What you are getting

```
attendance_system/
├── app.py                 -> the entire UI (run this file)
├── config.py               -> all folder paths & settings in one place
├── database.py              -> SQLite tables + all DB functions
├── face_utils.py             -> face detection/encoding/recognition logic
├── attendance_engine.py       -> ties recognition -> database together
├── excel_utils.py               -> generates the daily + master Excel reports
├── requirements.txt
├── README.md                      -> this file
└── data/
    ├── attendance.db          -> created automatically on first run
    ├── student_photos/         -> pre-fed student photos are stored here
    ├── classroom_uploads/       -> uploaded row-wise classroom photos
    ├── attendance_excel/         -> generated Excel reports land here
    └── encodings/                -> cached face "fingerprints" (.pkl file)
```

Everything — photos, database, Excel reports — lives inside the `data/`
folder on **your own laptop**. Nothing is uploaded anywhere.

---

## 2. Install the tools (one-time)

1. **Install Python 3.10 or 3.11** (recommended — dlib installs more easily
   on these versions than on the very latest Python).
   Download from https://www.python.org/downloads/ and, during install,
   tick **"Add Python to PATH"**.

2. **Install Visual Studio Code**: https://code.visualstudio.com/

3. In VS Code, install the **Python extension** (search "Python" by
   Microsoft in the Extensions panel, `Ctrl+Shift+X`).

4. **Install CMake** (required to build dlib):
   - Windows: download the installer from https://cmake.org/download/ and
     tick "Add CMake to PATH" during install.
   - Alternatively `pip install cmake` (already in requirements.txt) often
     works on its own.

5. (Windows only, if dlib still fails to build) Install
   **"Desktop development with C++"** workload from the free
   *Visual Studio Build Tools*: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   dlib compiles C++ code during installation, and Windows needs this
   compiler present. This is the single most common blocker — see the
   troubleshooting section if you hit errors here.

---

## 3. Open the project folder in VS Code

1. Unzip the project anywhere, e.g. `C:\Projects\attendance_system`.
2. Open VS Code → `File > Open Folder...` → select `attendance_system`.
3. Open a terminal inside VS Code: `Terminal > New Terminal`.

---

## 4. Create a virtual environment (keeps this project's libraries separate)

In the VS Code terminal:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You'll know it worked because your terminal prompt now starts with `(venv)`.
In VS Code, also click the Python version in the bottom-right status bar and
select the `venv` interpreter, so IntelliSense/debugging use the same
environment.

---

## 5. Install the required libraries

```bash
pip install -r requirements.txt
```

This installs Streamlit, pandas, openpyxl, Pillow, numpy, and — the
important one — `dlib` + `face_recognition`.

### If `dlib` fails to install (very common on Windows)

Try, in this order:

**Option A — precompiled wheel (fastest, no compiler needed):**
```bash
pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl
```
(pick the file matching your Python version, e.g. `cp310` for Python 3.10,
`cp311` for Python 3.11 — check the repo for the right link)

**Option B — install the C++ Build Tools** (see Section 2, step 5) and
re-run `pip install -r requirements.txt`.

**Option C — use conda instead of pip** (conda has prebuilt dlib packages):
```bash
conda install -c conda-forge dlib
pip install face_recognition streamlit pandas openpyxl pillow numpy
```

**Option D — fallback library (only if A/B/C all fail):** swap
`face_recognition` for `deepface` (pure pip install, no C++ compiler
needed). This changes `face_utils.py`'s internals — ask me and I'll
convert it for you if you get stuck here.

---

## 6. Run the app

```bash
streamlit run app.py
```

A browser tab opens automatically at `http://localhost:8501`. That's your
whole application — frontend and backend together.

---

## 7. Using the system (first run)

1. **Create your professor account** (first screen, one-time).
2. Go to **Manage Students** → **Add Student** and add your 10–20 students:
   name, roll number, USN, division, and one clear front-facing photo each.
   *(Tip: a well-lit, forward-facing passport-style photo per student gives
   the most reliable recognition.)*
3. Go to **Take Attendance**:
   - Type the subject/session name.
   - Upload one or more row-wise classroom photos (you can upload several
     photos of different rows from the same session — the system merges
     them and only marks each student present once).
   - Click **Run Face Recognition & Mark Attendance**.
   - The system shows annotated photos (green box = recognized student,
     red box = a face it doesn't recognize — correctly ignored, never
     marked present), plus Present/Absent lists.
   - Click **Download Today's Excel Report**.
4. Go to **Attendance Reports** any time to browse past dates/subjects and
   re-download Excel reports, or the full all-time master log.

---

## 8. How the recognition logic avoids false positives

- Every pre-fed student photo is converted into a 128-number "face
  fingerprint" (an *encoding*) using `face_recognition`, cached in
  `data/encodings/face_encodings.pkl`.
- When a classroom photo is uploaded, every face found in it is compared
  against all known fingerprints.
- A face is only labelled with a student's name if the closest match is
  within the tolerance set in `config.py` (`FACE_MATCH_TOLERANCE = 0.52`).
  Anyone whose face doesn't closely match a known student — a visitor, a
  guest, someone not yet added to the system — is labelled "Unknown" and
  is **never** marked present. This directly satisfies your requirement:
  *"if a person is not in the database, it shouldn't recognize that."*
- Lower the tolerance (e.g. `0.45`) for stricter matching if you notice any
  wrong matches; raise it slightly (e.g. `0.58`) if real students are being
  missed. This is the main value you'll tune during your demo/testing.

---

## 9. Notes for your final-year report / viva

- **Frontend + Backend:** Streamlit renders the UI directly from Python —
  there's no separate "frontend code" vs "backend code" split like in
  MERN; `app.py` is both, which is why the whole project can stay in
  Python. You can describe this in your report as "a Python-native
  full-stack web framework" if asked why it differs from the MERN stack
  mentioned in the initial synopsis.
- **Database:** SQLite (file-based, `data/attendance.db`) instead of MySQL
  — functionally equivalent for this scale (10–20 students) and needs zero
  server setup on a personal laptop. If your evaluators specifically want
  MySQL, only `database.py` needs to change (swap `sqlite3` connection for
  `mysql-connector-python`); the rest of the app is unaffected.
  Pandas is still used exactly as your synopsis specifies, for the Excel
  generation layer.
- **Face Detection & Recognition:** `face_recognition` (dlib-based) — the
  exact library named in your synopsis.
- **Excel Reports:** generated with pandas + openpyxl, matching your
  required columns (Roll No, USN, Name, Division, Status, Time) plus a
  Summary sheet with total present/absent and roll number lists.

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `dlib` fails to build | See Section 5 options A–D above |
| `ModuleNotFoundError: No module named 'streamlit'` | Make sure `(venv)` is active, then `pip install -r requirements.txt` again |
| Photo upload says "No clear face could be detected" | Use a photo with one clear, front-facing, well-lit face; avoid sunglasses/heavy shadows |
| Classroom photo recognizes nobody | Check `FACE_MATCH_TOLERANCE` in `config.py`; also make sure lighting isn't too dark and faces aren't too small/blurry in the photo |
| App says port already in use | Run `streamlit run app.py --server.port 8502` instead |
| Want to reset everything | Close the app, delete `data/attendance.db` and everything inside `data/encodings/`, then restart |

---

## 11. Possible extensions if you want to go further

- Add a live webcam capture option (`face_recognition` + `opencv-python`,
  `cv2.VideoCapture(0)`) instead of only file uploads.
- Add attendance percentage charts per student (Streamlit has `st.bar_chart`
  built in — no extra library needed).
- Export a monthly/semester consolidated Excel report by looping over all
  cached dates in `excel_utils.py`.
- Deploy the same code to Streamlit Community Cloud for a live demo link.

Good luck with your project — this is a genuinely solid, demo-able B.Tech
final year submission as it stands. Reach out if you want the webcam
version, MySQL version, or deepface fallback built out too.
