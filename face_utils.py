"""
face_utils.py
-------------
Everything related to face detection & recognition using the `face_recognition`
library (which is built on top of dlib), exactly as specified in the project
synopsis.

Key idea:
    1. Every pre-fed student photo is converted into a 128-number "face
       encoding" (a fingerprint of that face). This is cached to disk
       (data/encodings/face_encodings.pkl) so we don't recompute it every run.
    2. When a classroom photo is uploaded, we detect every face in it,
       compute its encoding, and compare it against all cached student
       encodings.
    3. A face only counts as "recognized" if it is close enough to a known
       student's encoding (controlled by config.FACE_MATCH_TOLERANCE).
       Anyone not in the database is correctly left as "Unknown" and is
       NEVER marked present.
"""

import os
import pickle

import face_recognition
import numpy as np
from PIL import Image, ImageOps

import config
import database


def _load_image_as_rgb(path):
    """
    Load ANY image (JPEG, PNG with alpha, palette/P-mode PNG, CMYK JPEG,
    16-bit PNG, grayscale, HEIC-converted files, screenshots, etc.) and
    return a clean, guaranteed 8-bit, 3-channel, contiguous RGB numpy array.

    dlib is strict: it only accepts 8-bit gray or 8-bit RGB, and it wants a
    C-contiguous array. face_recognition.load_image_file() usually handles
    this, but some real-world phone/screenshot images (RGBA, CMYK, 16-bit,
    or paletted PNGs) slip through and cause:
        "Unsupported image type, must be 8bit gray or RGB image."
    Routing every image through this function fixes that for good.
    """
    img = Image.open(path)

    # Respect the camera's rotation metadata instead of leaving it sideways
    img = ImageOps.exif_transpose(img)

    # Force to standard 8-bit RGB regardless of source mode (RGBA, P, CMYK,
    # L, I;16, etc.)
    img = img.convert("RGB")

    arr = np.array(img, dtype=np.uint8)

    # Guarantee C-contiguous memory layout, which dlib also requires
    arr = np.ascontiguousarray(arr)

    return arr


def _load_cache():
    if os.path.exists(config.ENCODINGS_FILE):
        with open(config.ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def _save_cache(cache):
    with open(config.ENCODINGS_FILE, "wb") as f:
        pickle.dump(cache, f)


def encode_single_photo(photo_path):
    """Return the 128-d face encoding for the FIRST face found in a photo, or None."""
    image = _load_image_as_rgb(photo_path)
    encodings = face_recognition.face_encodings(image)
    if len(encodings) == 0:
        return None
    return encodings[0]


def refresh_encodings():
    """
    Recompute (or reuse cached) encodings for every student currently in the
    database. Call this once after adding/removing a student. Returns a dict:
        { student_id: encoding_vector }
    Also returns a list of student_ids for whom NO face could be detected in
    their pre-fed photo (so the UI can warn the professor).
    """
    students = database.get_all_students()
    cache = _load_cache()
    new_cache = {}
    failed_ids = []

    for s in students:
        sid = s["id"]
        photo_path = s["photo_path"]
        cache_key = f"{sid}:{os.path.getmtime(photo_path)}"

        if cache_key in cache:
            new_cache[cache_key] = cache[cache_key]
            continue

        encoding = encode_single_photo(photo_path)
        if encoding is None:
            failed_ids.append(sid)
            continue

        new_cache[cache_key] = {"student_id": sid, "encoding": encoding}

    _save_cache(new_cache)
    return failed_ids


def get_known_encodings():
    """
    Load the cached encodings and return two aligned lists:
        student_ids: [id1, id2, ...]
        encodings:   [enc1, enc2, ...]
    ready to be passed into face_recognition.compare_faces / face_distance.
    """
    cache = _load_cache()
    student_ids, encodings = [], []
    for entry in cache.values():
        student_ids.append(entry["student_id"])
        encodings.append(entry["encoding"])
    return student_ids, encodings


def recognize_faces_in_image(image_path, known_student_ids, known_encodings):
    """
    Detect every face in a classroom image and try to match each one against
    the known students.

    Returns a list of dicts, one per detected face:
        {
            "student_id": <id or None if unrecognized>,
            "location": (top, right, bottom, left),
            "distance": <float, lower = better match, None if no known faces>
        }
    """
    image = _load_image_as_rgb(image_path)
    face_locations = face_recognition.face_locations(
        image, model=config.FACE_DETECTION_MODEL
    )
    face_encodings = face_recognition.face_encodings(image, face_locations)

    results = []
    for location, face_encoding in zip(face_locations, face_encodings):
        matched_id = None
        best_distance = None

        if known_encodings:
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])

            if best_distance <= config.FACE_MATCH_TOLERANCE:
                matched_id = known_student_ids[best_index]

        results.append(
            {
                "student_id": matched_id,
                "location": location,
                "distance": best_distance,
            }
        )
    return results
