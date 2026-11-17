"""
attendance_engine.py
---------------------
Glue logic: takes one or more uploaded classroom images, runs face
recognition on all of them, marks every recognized student Present
(only once, even if they appear in 3 different row photos), marks every
other pre-fed student Absent, and returns a clean summary for the UI +
Excel export.
"""

from datetime import datetime

from PIL import Image, ImageDraw

import database
import face_utils


def process_classroom_images(image_paths, subject, professor_id, session_date=None):
    """
    image_paths: list of file paths to classroom photos (can be 1 or many -
                 e.g. multiple row-wise photos of the same session).
    subject:     subject/session name, used to keep attendance separate per
                 lecture if a professor takes attendance more than once a day.
    professor_id: id of the logged-in professor (for record-keeping).
    session_date: "YYYY-MM-DD" string; defaults to today.

    Returns a dict:
        {
            "present_ids": set of recognized student ids,
            "absent_ids": set of student ids not seen in any photo,
            "unknown_faces_count": int (faces detected but not in database),
            "annotated_images": [PIL.Image, ...]   (boxes drawn for review)
        }
    """
    if session_date is None:
        session_date = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    all_students = database.get_all_students()
    all_student_ids = {s["id"] for s in all_students}

    known_ids, known_encodings = face_utils.get_known_encodings()

    present_ids = set()
    unknown_faces_count = 0
    annotated_images = []

    for image_path in image_paths:
        results = face_utils.recognize_faces_in_image(
            image_path, known_ids, known_encodings
        )

        pil_image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(pil_image)

        for r in results:
            top, right, bottom, left = r["location"]
            if r["student_id"] is not None:
                present_ids.add(r["student_id"])
                student = database.get_student_by_id(r["student_id"])
                label = student["name"] if student else "Unknown"
                color = (0, 200, 0)  # green box = recognized
            else:
                unknown_faces_count += 1
                label = "Unknown"
                color = (220, 30, 30)  # red box = not in database

            draw.rectangle(((left, top), (right, bottom)), outline=color, width=3)
            draw.rectangle(((left, bottom - 20), (right, bottom)), fill=color)
            draw.text((left + 4, bottom - 18), label, fill=(255, 255, 255))

        annotated_images.append(pil_image)

    absent_ids = all_student_ids - present_ids

    # Write to database: Present for recognized students, Absent for everyone else
    for sid in present_ids:
        database.mark_attendance(sid, session_date, time_now, "Present", subject, professor_id)
    for sid in absent_ids:
        database.mark_attendance(sid, session_date, time_now, "Absent", subject, professor_id)

    return {
        "date": session_date,
        "subject": subject,
        "present_ids": present_ids,
        "absent_ids": absent_ids,
        "unknown_faces_count": unknown_faces_count,
        "annotated_images": annotated_images,
    }
