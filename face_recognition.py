import os
import time
import cv2
import numpy as np

from config import FACE_SIZE, FACE_CONFIDENCE_THRESHOLD


# ---------------------------------------------------------
# Haar Cascade Paths
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FACE_CASCADE_PATH = os.path.join(
    BASE_DIR,
    "data",
    "haarcascades",
    "haarcascade_frontalface_default.xml"
)

EYE_CASCADE_PATH = os.path.join(
    BASE_DIR,
    "data",
    "haarcascades",
    "haarcascade_eye.xml"
)


face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)


if face_cascade.empty():
    raise RuntimeError(
        "Face Haar cascade could not be loaded:\n"
        + FACE_CASCADE_PATH
    )


if eye_cascade.empty():
    raise RuntimeError(
        "Eye Haar cascade could not be loaded:\n"
        + EYE_CASCADE_PATH
    )


# ---------------------------------------------------------
# LBPH Recognizer
# ---------------------------------------------------------

def create_recognizer():
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "OpenCV Face module is not available.\n\n"
            "Make sure opencv-contrib-python is installed."
        )

    return cv2.face.LBPHFaceRecognizer_create()


# ---------------------------------------------------------
# Capture Face Samples for Registration
# ---------------------------------------------------------

def train_model_from_camera(
    samples_required=35,
    progress_callback=None
):
    """
    Opens the webcam and captures face samples.

    Returns:
        trained LBPH recognizer
    """

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError(
            "Could not open the webcam.\n\n"
            "Please check that your camera is connected and available."
        )

    samples = []

    try:
        while len(samples) < samples_required:

            ret, frame = camera.read()

            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(100, 100)
            )

            display_frame = frame.copy()

            if len(faces) == 0:

                cv2.putText(
                    display_frame,
                    "No face detected",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

            elif len(faces) > 1:

                cv2.putText(
                    display_frame,
                    "Only one face should be visible",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

            else:

                x, y, w, h = faces[0]

                face = gray[y:y + h, x:x + w]

                face = cv2.resize(face, FACE_SIZE)

                samples.append(face)

                cv2.rectangle(
                    display_frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    f"Samples: {len(samples)}/{samples_required}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

                if progress_callback:
                    progress_callback(
                        f"Capturing face samples: "
                        f"{len(samples)}/{samples_required}"
                    )

            cv2.imshow(
                "FaceGuard - Face Registration",
                display_frame
            )

            key = cv2.waitKey(30) & 0xFF

            if key == 27:
                raise RuntimeError(
                    "Face registration cancelled by the user."
                )

    finally:
        camera.release()
        cv2.destroyAllWindows()

    # -----------------------------------------------------
    # Train LBPH
    # -----------------------------------------------------

    recognizer = create_recognizer()

    labels = np.array(
        [0] * len(samples),
        dtype=np.int32
    )

    recognizer.train(
        samples,
        labels
    )

    if progress_callback:
        progress_callback(
            "Face model trained successfully."
        )

    return recognizer


# ---------------------------------------------------------
# Save LBPH Model
# ---------------------------------------------------------

def save_model(model, model_path):

    os.makedirs(
        os.path.dirname(str(model_path)),
        exist_ok=True
    )

    model.save(str(model_path))


# ---------------------------------------------------------
# Eye Detection
# ---------------------------------------------------------

def detect_eyes(gray_face):

    eyes = eye_cascade.detectMultiScale(
        gray_face,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(20, 20)
    )

    return eyes


# ---------------------------------------------------------
# Liveness Detection
# ---------------------------------------------------------

def perform_liveness_check(
    progress_callback=None,
    timeout=35
):
    """
    Basic challenge-response liveness detection.

    User must:
        1. Blink
        2. Move head left
        3. Move head right

    This is a basic liveness layer, not a high-security
    anti-spoofing system.
    """

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return False, "Could not open the webcam."

    start_time = time.time()

    blink_detected = False
    left_detected = False
    right_detected = False

    eye_closed_frames = 0
    eye_open_frames = 0

    face_positions = []

    # Position of the face when LEFT movement is detected.
    # The old logic required the face to move all the way to
    # the right side of the camera frame after moving left.
    # That often failed when the user simply turned/returned
    # toward the center.
    left_reference_position = None

    stage = "blink"

    try:

        while True:

            elapsed = time.time() - start_time

            if elapsed > timeout:

                return (
                    False,
                    "Liveness verification timed out."
                )

            ret, frame = camera.read()

            if not ret:
                continue

            frame = cv2.flip(frame, 1)

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(120, 120)
            )

            display_frame = frame.copy()

            # -------------------------------------------------
            # No face / multiple faces
            # -------------------------------------------------

            if len(faces) == 0:

                cv2.putText(
                    display_frame,
                    "Please show your face",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

                if progress_callback:
                    progress_callback(
                        "Please look at the camera."
                    )

                cv2.imshow(
                    "FaceGuard - Liveness Verification",
                    display_frame
                )

                if cv2.waitKey(30) & 0xFF == 27:
                    return False, "Liveness cancelled."

                continue

            if len(faces) > 1:

                cv2.putText(
                    display_frame,
                    "Only one person should be visible",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

                if progress_callback:
                    progress_callback(
                        "Only one face should be visible."
                    )

                cv2.imshow(
                    "FaceGuard - Liveness Verification",
                    display_frame
                )

                if cv2.waitKey(30) & 0xFF == 27:
                    return False, "Liveness cancelled."

                continue

            # -------------------------------------------------
            # Face information
            # -------------------------------------------------

            x, y, w, h = faces[0]

            cv2.rectangle(
                display_frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            face_gray = gray[
                y:y + h,
                x:x + w
            ]

            # -------------------------------------------------
            # BLINK DETECTION
            # -------------------------------------------------

            if not blink_detected:

                upper_face = face_gray[
                    int(h * 0.15):
                    int(h * 0.60),
                    :
                ]

                eyes = detect_eyes(upper_face)

                if len(eyes) >= 2:

                    eye_open_frames += 1
                    eye_closed_frames = 0

                else:

                    eye_closed_frames += 1

                    if eye_closed_frames >= 2:

                        blink_detected = True

                cv2.putText(
                    display_frame,
                    "Blink: "
                    + ("DONE" if blink_detected else "PLEASE BLINK"),
                    (20, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 0)
                    if blink_detected
                    else (255, 255, 0),
                    2
                )

                if progress_callback:

                    if blink_detected:

                        progress_callback(
                            "Blink detected. Now move your head LEFT."
                        )

                    else:

                        progress_callback(
                            "Please blink once."
                        )

            # -------------------------------------------------
            # HEAD MOVEMENT
            # -------------------------------------------------

            else:

                face_center_x = x + (w / 2)

                frame_center_x = frame.shape[1] / 2

                relative_position = (
                    face_center_x - frame_center_x
                )

                face_positions.append(
                    relative_position
                )

                # Keep recent positions
                if len(face_positions) > 15:
                    face_positions.pop(0)

                # ---------------------------------------------
                # LEFT
                # ---------------------------------------------

                if not left_detected:

                    # Detect a clear movement to the user's LEFT.
                    # The image is mirrored, so this appears on the
                    # LEFT side of the displayed camera image.
                    if relative_position < -40:

                        left_detected = True
                        left_reference_position = relative_position

                        if progress_callback:
                            progress_callback(
                                "Head LEFT detected. "
                                "Now move your head RIGHT."
                            )

                # ---------------------------------------------
                # RIGHT
                # ---------------------------------------------

                elif not right_detected:

                    # IMPORTANT:
                    # Do not require the face to reach +55 pixels
                    # from the screen center. After moving LEFT,
                    # most users naturally move back toward the
                    # center when turning RIGHT.
                    #
                    # Example:
                    # LEFT position  = -50
                    # Center position =   0
                    #
                    # Moving from -50 to 0 is a RIGHT movement of
                    # 50 pixels and should be accepted.
                    if (
                        left_reference_position is not None
                        and
                        (
                            relative_position
                            - left_reference_position
                        ) >= 40
                    ):

                        right_detected = True

                        if progress_callback:
                            progress_callback(
                                "Head RIGHT detected. "
                                "Liveness verification complete."
                            )

                cv2.putText(
                    display_frame,
                    "Blink: DONE",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    "Head Left: "
                    + ("DONE" if left_detected else "MOVE LEFT"),
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0)
                    if left_detected
                    else (255, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    "Head Right: "
                    + ("DONE" if right_detected else "MOVE RIGHT"),
                    (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0)
                    if right_detected
                    else (255, 255, 0),
                    2
                )

            # -------------------------------------------------
            # COMPLETE
            # -------------------------------------------------

            if (
                blink_detected
                and left_detected
                and right_detected
            ):

                cv2.putText(
                    display_frame,
                    "LIVENESS VERIFIED",
                    (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.85,
                    (0, 255, 0),
                    2
                )

                cv2.imshow(
                    "FaceGuard - Liveness Verification",
                    display_frame
                )

                cv2.waitKey(700)

                return (
                    True,
                    "Liveness verification successful."
                )

            cv2.imshow(
                "FaceGuard - Liveness Verification",
                display_frame
            )

            key = cv2.waitKey(30) & 0xFF

            if key == 27:

                return (
                    False,
                    "Liveness verification cancelled."
                )

    finally:

        camera.release()

        cv2.destroyAllWindows()


# ---------------------------------------------------------
# Verify Registered User Face
# ---------------------------------------------------------

def verify_user_face(
    model_path,
    progress_callback=None
):
    """
    Performs:

        1. Liveness detection
        2. LBPH face recognition
    """

    # -----------------------------------------------------
    # Liveness
    # -----------------------------------------------------

    if progress_callback:
        progress_callback(
            "Starting liveness verification..."
        )

    live_ok, live_message = perform_liveness_check(
        progress_callback=progress_callback,
        timeout=35
    )

    if not live_ok:

        return (
            False,
            live_message
        )

    # -----------------------------------------------------
    # Load LBPH Model
    # -----------------------------------------------------

    if not os.path.exists(model_path):

        return (
            False,
            "Registered face model was not found."
        )

    try:

        recognizer = create_recognizer()

        recognizer.read(
            str(model_path)
        )

    except Exception as exc:

        return (
            False,
            f"Could not load face model: {exc}"
        )

    # -----------------------------------------------------
    # Open Camera for Face Recognition
    # -----------------------------------------------------

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():

        camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        return (
            False,
            "Could not open webcam for face recognition."
        )

    start_time = time.time()

    try:

        while time.time() - start_time < 15:

            ret, frame = camera.read()

            if not ret:
                continue

            frame = cv2.flip(
                frame,
                1
            )

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(100, 100)
            )

            display_frame = frame.copy()

            if len(faces) == 0:

                if progress_callback:
                    progress_callback(
                        "Liveness passed. "
                        "Please show your registered face."
                    )

                cv2.putText(
                    display_frame,
                    "Show your registered face",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 0, 255),
                    2
                )

            elif len(faces) > 1:

                if progress_callback:
                    progress_callback(
                        "Multiple faces detected. "
                        "Only one person should be visible."
                    )

                cv2.putText(
                    display_frame,
                    "Only one face should be visible",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

            else:

                x, y, w, h = faces[0]

                face = gray[
                    y:y + h,
                    x:x + w
                ]

                face = cv2.resize(
                    face,
                    FACE_SIZE
                )

                try:

                    label, confidence = recognizer.predict(
                        face
                    )

                except Exception:

                    label = -1
                    confidence = 999.0

                cv2.rectangle(
                    display_frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    f"Confidence: {confidence:.1f}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

                # -------------------------------------------------
                # LBPH
                #
                # Lower confidence = better match
                # -------------------------------------------------

                if (
                    label == 0
                    and confidence <= FACE_CONFIDENCE_THRESHOLD
                ):

                    if progress_callback:
                        progress_callback(
                            "Registered face verified successfully."
                        )

                    cv2.putText(
                        display_frame,
                        "FACE VERIFIED",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.85,
                        (0, 255, 0),
                        2
                    )

                    cv2.imshow(
                        "FaceGuard - Face Recognition",
                        display_frame
                    )

                    cv2.waitKey(700)

                    return (
                        True,
                        "Face recognition successful."
                    )

                else:

                    if progress_callback:
                        progress_callback(
                            "Face does not match the registered user."
                        )

                    cv2.putText(
                        display_frame,
                        "FACE NOT RECOGNIZED",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2
                    )

            cv2.imshow(
                "FaceGuard - Face Recognition",
                display_frame
            )

            key = cv2.waitKey(30) & 0xFF

            if key == 27:

                return (
                    False,
                    "Face verification cancelled."
                )

        return (
            False,
            "Face verification timed out."
        )

    finally:

        camera.release()

        cv2.destroyAllWindows()