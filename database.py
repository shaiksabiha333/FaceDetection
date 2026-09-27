import sqlite3
from datetime import datetime
from pathlib import Path

from config import DB_PATH, DEFAULT_APPLICATIONS


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                pin_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS face_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                model_path TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL UNIQUE,
                executable_path TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS user_app_permissions (
                user_id INTEGER NOT NULL,
                application_id INTEGER NOT NULL,
                PRIMARY KEY(user_id, application_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_app_pins (
                user_id INTEGER NOT NULL,
                application_id INTEGER NOT NULL,
                pin_hash TEXT NOT NULL,
                PRIMARY KEY(user_id, application_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                application TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                pin_result TEXT NOT NULL,
                face_result TEXT NOT NULL,
                final_result TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL
            );
            """
        )

        for name, path in DEFAULT_APPLICATIONS:
            conn.execute(
                """
                INSERT OR IGNORE INTO applications
                (app_name, executable_path)
                VALUES (?, ?)
                """,
                (name, path),
            )


def create_user(name, username, pin_hash):
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO users
            (name, username, pin_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                username,
                pin_hash,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def get_users():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, username, created_at
            FROM users
            ORDER BY username
            """
        ).fetchall()


def get_user(user_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id=?",
            (user_id,),
        ).fetchone()


def get_user_by_username(username):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,),
        ).fetchone()


def delete_user(user_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM users WHERE id=?",
            (user_id,),
        )


def get_user_permissions(user_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT a.*
            FROM applications a
            JOIN user_app_permissions p
              ON p.application_id=a.id
            WHERE p.user_id=?
            ORDER BY a.app_name
            """,
            (user_id,),
        ).fetchall()


def set_user_permissions(user_id, application_ids):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM user_app_permissions WHERE user_id=?",
            (user_id,),
        )

        for app_id in application_ids:
            conn.execute(
                """
                INSERT INTO user_app_permissions
                (user_id, application_id)
                VALUES (?, ?)
                """,
                (user_id, app_id),
            )


def get_applications():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM applications ORDER BY id"
        ).fetchall()


def get_application(app_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM applications WHERE id=?",
            (app_id,),
        ).fetchone()


def update_application_path(app_id, path):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE applications
            SET executable_path=?
            WHERE id=?
            """,
            (path, app_id),
        )


def has_permission(user_id, app_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM user_app_permissions
            WHERE user_id=? AND application_id=?
            """,
            (user_id, app_id),
        ).fetchone()

        return row is not None


def set_face_model(user_id, model_path):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO face_models(user_id, model_path)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET model_path=excluded.model_path
            """,
            (user_id, str(model_path)),
        )


def get_face_model(user_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM face_models WHERE user_id=?",
            (user_id,),
        ).fetchone()


def add_security_log(
    username,
    application,
    pin_result,
    face_result,
    final_result,
):
    now = datetime.now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO security_logs
            (username, application, date, time,
             pin_result, face_result, final_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                application,
                now.strftime("%d-%m-%Y"),
                now.strftime("%H:%M:%S"),
                pin_result,
                face_result,
                final_result,
            ),
        )


def get_security_logs(limit=500):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT username, application, date, time,
                   pin_result, face_result, final_result
            FROM security_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def get_admin_password_hash():
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT password_hash
            FROM admin_settings
            WHERE id=1
            """
        ).fetchone()

        return row["password_hash"] if row else None


def set_admin_password(password_hash):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO admin_settings(id, password_hash)
            VALUES (1, ?)
            ON CONFLICT(id)
            DO UPDATE SET password_hash=excluded.password_hash
            """,
            (password_hash,),
        )

# ============================================================
# APPLICATION-SPECIFIC USER PINS
# ============================================================

def ensure_user_app_pins_table():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_app_pins (
                user_id INTEGER NOT NULL,
                application_id INTEGER NOT NULL,
                pin_hash TEXT NOT NULL,
                PRIMARY KEY(user_id, application_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            )
            """
        )


def set_user_app_pin(user_id, application_id, pin_hash):
    ensure_user_app_pins_table()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_app_pins(user_id, application_id, pin_hash)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, application_id)
            DO UPDATE SET pin_hash=excluded.pin_hash
            """,
            (user_id, application_id, pin_hash),
        )


def get_user_app_pin(user_id, application_id):
    ensure_user_app_pins_table()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT pin_hash
            FROM user_app_pins
            WHERE user_id=? AND application_id=?
            """,
            (user_id, application_id),
        ).fetchone()
        return row["pin_hash"] if row else None


def delete_user_app_pin(user_id, application_id):
    ensure_user_app_pins_table()
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM user_app_pins
            WHERE user_id=? AND application_id=?
            """,
            (user_id, application_id),
        )
