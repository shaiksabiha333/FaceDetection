import cv2

import os

CASCADE_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "haarcascades",
    "haarcascade_frontalface_default.xml"
)

def create_detector():
    detector = cv2.CascadeClassifier(CASCADE_PATH)
    if detector.empty():
        raise RuntimeError("OpenCV Haar face detector could not be loaded.")
    return detector


def detect_faces(gray_frame, detector):
    return detector.detectMultiScale(
        gray_frame,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(80, 80),
    )


def crop_largest_face(gray_frame, faces):
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
    face = gray_frame[y:y+h, x:x+w]
    return face, (x, y, w, h)
