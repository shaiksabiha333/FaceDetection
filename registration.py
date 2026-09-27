from authentication import hash_pin, valid_pin_format
from database import (
    create_user,
    set_user_permissions,
    set_face_model,
    set_user_app_pin,
)
from face_recognition import train_model_from_camera, save_model
from config import MODEL_DIR, FACE_SAMPLES_REQUIRED


def register_user(
    name,
    username,
    application_pins,
    application_ids,
    progress_callback=None,
):
    name = name.strip()
    username = username.strip()

    # -------------------------------------------------
    # BASIC VALIDATION
    # -------------------------------------------------

    if not name or not username:
        raise ValueError(
            "Full name and username are required."
        )

    if not application_ids:
        raise ValueError(
            "Select at least one application."
        )

    # -------------------------------------------------
    # VALIDATE APPLICATION PINS
    # -------------------------------------------------

    for app_id in application_ids:

        if app_id not in application_pins:
            raise ValueError(
                "PIN is missing for one of the selected applications."
            )

        pin, confirm_pin = application_pins[app_id]

        pin = pin.strip()
        confirm_pin = confirm_pin.strip()

        if not valid_pin_format(pin):
            raise ValueError(
                "Each PIN must contain only digits and be 1 to 12 digits long."
            )

        if pin != confirm_pin:
            raise ValueError(
                "PIN and Confirm PIN do not match."
            )

    # -------------------------------------------------
    # TEMPORARILY CREATE USER
    # -------------------------------------------------
    #
    # The old users.pin_hash column is still required
    # by the existing database structure.
    #
    # We use the first application's PIN as the
    # temporary/general PIN for compatibility.
    #
    # Application authentication will use
    # user_app_pins instead.
    # -------------------------------------------------

    first_app_id = application_ids[0]
    first_pin = application_pins[first_app_id][0]

    general_pin_hash = hash_pin(first_pin)

    user_id = create_user(
        name,
        username,
        general_pin_hash,
    )

    try:

        # -------------------------------------------------
        # SAVE APPLICATION PERMISSIONS
        # -------------------------------------------------

        set_user_permissions(
            user_id,
            application_ids,
        )

        # -------------------------------------------------
        # SAVE APPLICATION-SPECIFIC PIN HASHES
        # -------------------------------------------------

        for app_id in application_ids:

            pin = application_pins[app_id][0]

            pin_hash = hash_pin(pin)

            set_user_app_pin(
                user_id,
                app_id,
                pin_hash,
            )

        # -------------------------------------------------
        # FACE REGISTRATION
        # -------------------------------------------------

        model = train_model_from_camera(
            samples_required=FACE_SAMPLES_REQUIRED,
            progress_callback=progress_callback,
        )

        # -------------------------------------------------
        # SAVE FACE MODEL
        # -------------------------------------------------

        model_path = MODEL_DIR / f"user_{user_id}.yml"

        save_model(
            model,
            model_path,
        )

        set_face_model(
            user_id,
            model_path,
        )

        return user_id

    except Exception:

        # Database cleanup is handled by the caller,
        # as in the previous registration implementation.
        raise