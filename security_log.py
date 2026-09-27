from database import add_security_log


def record_attempt(username, application, pin_result, face_result, final_result):
    add_security_log(username, application, pin_result, face_result, final_result)
