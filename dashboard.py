import queue
import threading
import customtkinter as ctk
from tkinter import messagebox

from database import (
    get_user,
    get_user_permissions,
    get_face_model,
    get_user_app_pin,
    has_permission,
    set_user_app_pin,
)
from authentication import verify_pin, hash_pin, valid_pin_format
from face_recognition import verify_user_face
from app_launcher import launch_application, launch_special_windows_target
from security_log import record_attempt


# ============================================================
# FACEGUARD UI THEME
# ============================================================

BG = "#0B1120"
SURFACE = "#111827"
SURFACE_2 = "#172033"
BORDER = "#263449"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
ACCENT = "#4F8CFF"
ACCENT_HOVER = "#3B78E8"
SUCCESS = "#22C55E"
DANGER = "#EF4444"
WARNING = "#F59E0B"


def apply_theme():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def badge(parent, text, kind="neutral"):
    colors = {
        "success": ("#12351F", SUCCESS),
        "danger": ("#3A171B", DANGER),
        "warning": ("#3A2B0D", WARNING),
        "neutral": ("#1E293B", MUTED),
        "blue": ("#142A52", ACCENT),
    }
    bg_color, fg_color = colors.get(kind, colors["neutral"])
    return ctk.CTkLabel(
        parent,
        text=text,
        fg_color=bg_color,
        text_color=fg_color,
        corner_radius=10,
        padx=10,
        pady=4,
        font=ctk.CTkFont(size=11, weight="bold"),
    )


# ============================================================
# APPLICATION PIN DIALOG
# ============================================================

class PinDialog(ctk.CTkToplevel):
    def __init__(self, parent, user_id, app_row, on_result):
        super().__init__(parent)
        self.user_id = user_id
        self.app_row = app_row
        self.on_result = on_result
        self._closing = False

        self.title("FaceGuard • Application PIN")
        self.geometry("500x430")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)

        container = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20, border_width=1, border_color=BORDER)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(container, text="🔐", font=ctk.CTkFont(size=34)).pack(pady=(22, 2))
        ctk.CTkLabel(
            container, text="Application PIN", text_color=TEXT,
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack()
        ctk.CTkLabel(
            container, text=app_row["app_name"], text_color=ACCENT,
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(4, 2))
        ctk.CTkLabel(
            container, text="Enter the private PIN assigned to this application.",
            text_color=MUTED, wraplength=390
        ).pack(pady=(0, 18))

        self.pin_entry = ctk.CTkEntry(
            container, width=300, height=46, show="•", justify="center",
            placeholder_text="Enter PIN", font=ctk.CTkFont(size=17)
        )
        self.pin_entry.pack(pady=4)

        self.status = ctk.CTkLabel(container, text="", text_color=DANGER, wraplength=390)
        self.status.pack(pady=(8, 8))

        ctk.CTkButton(
            container, text="Verify PIN  →", width=300, height=44,
            corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.verify
        ).pack(pady=(4, 8))

        ctk.CTkButton(
            container, text="Forgot PIN? Reset securely", width=300, height=36,
            fg_color="transparent", hover_color=SURFACE_2, text_color=MUTED,
            command=self.forgot_pin
        ).pack()

        ctk.CTkLabel(
            container, text="PIN is checked locally and is never displayed.",
            text_color="#64748B", font=ctk.CTkFont(size=10)
        ).pack(pady=(14, 0))

        self.pin_entry.focus()
        self.bind("<Return>", lambda _e: self.verify())
        self.bind("<Escape>", lambda _e: self.close())

    def close(self):
        if not self._closing:
            self._closing = True
            self.destroy()

    def verify(self):
        pin = self.pin_entry.get().strip()
        user = get_user(self.user_id)
        if not user:
            self.status.configure(text="User account not found.")
            self.on_result(False, "FAILED", "NOT_CHECKED")
            self.close()
            return

        stored_hash = get_user_app_pin(self.user_id, self.app_row["id"])
        if not stored_hash:
            self.status.configure(text="Application PIN is not configured.")
            record_attempt(user["username"], self.app_row["app_name"], "NOT_CONFIGURED", "NOT_CHECKED", "ACCESS DENIED")
            self.on_result(False, "NOT_CONFIGURED", "NOT_CHECKED")
            return

        if not verify_pin(pin, stored_hash):
            self.status.configure(text="Incorrect PIN. Please try again.")
            self.pin_entry.delete(0, "end")
            self.pin_entry.focus()
            record_attempt(user["username"], self.app_row["app_name"], "FAILED", "NOT_CHECKED", "ACCESS DENIED")
            return

        self.close()
        self.on_result(True, "SUCCESS", "NOT_CHECKED")

    def forgot_pin(self):
        self.close()
        self.on_result("RESET_REQUEST", "RESET_REQUEST", "NOT_CHECKED")


# ============================================================
# RESET PIN DIALOG
# ============================================================

class ResetPinDialog(ctk.CTkToplevel):
    def __init__(self, parent, user_id, app_row, on_reset):
        super().__init__(parent)
        self.user_id = user_id
        self.app_row = app_row
        self.on_reset = on_reset

        self.title("FaceGuard • Create New PIN")
        self.geometry("520x500")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20, border_width=1, border_color=BORDER)
        box.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(box, text="✓", text_color=SUCCESS, font=ctk.CTkFont(size=38, weight="bold")).pack(pady=(22, 0))
        ctk.CTkLabel(box, text="Identity Verified", text_color=TEXT, font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(box, text=f"Create a new PIN for {app_row['app_name']}", text_color=ACCENT, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5, 10))

        info = ctk.CTkFrame(box, fg_color="#12351F", corner_radius=12)
        info.pack(fill="x", padx=30, pady=(0, 18))
        ctk.CTkLabel(
            info,
            text="Your registered face and application permission were verified.\nYour old PIN cannot be recovered.",
            text_color="#B7F7C8", justify="center", wraplength=390
        ).pack(padx=14, pady=12)

        ctk.CTkLabel(box, text="New PIN • 1–12 digits", text_color=MUTED).pack(anchor="w", padx=55)
        self.new_pin = ctk.CTkEntry(box, width=390, height=44, show="•", placeholder_text="New private PIN")
        self.new_pin.pack(pady=(5, 12))

        ctk.CTkLabel(box, text="Confirm new PIN", text_color=MUTED).pack(anchor="w", padx=55)
        self.confirm_pin = ctk.CTkEntry(box, width=390, height=44, show="•", placeholder_text="Repeat new PIN")
        self.confirm_pin.pack(pady=(5, 4))

        self.status = ctk.CTkLabel(box, text="", text_color=DANGER, wraplength=390)
        self.status.pack(pady=5)

        ctk.CTkButton(
            box, text="Save New PIN", width=390, height=44, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.reset
        ).pack(pady=(5, 5))

        ctk.CTkButton(
            box, text="Cancel", width=390, height=34, fg_color="transparent",
            hover_color=SURFACE_2, text_color=MUTED, command=self.destroy
        ).pack()

        self.new_pin.focus()
        self.bind("<Return>", lambda _e: self.reset())
        self.bind("<Escape>", lambda _e: self.destroy())

    def reset(self):
        new_pin = self.new_pin.get().strip()
        confirm_pin = self.confirm_pin.get().strip()
        if not valid_pin_format(new_pin):
            self.status.configure(text="Use only 1 to 12 digits.")
            return
        if new_pin != confirm_pin:
            self.status.configure(text="The two PINs do not match.")
            return
        try:
            set_user_app_pin(self.user_id, self.app_row["id"], hash_pin(new_pin))
        except Exception as exc:
            self.status.configure(text=f"Could not save PIN: {exc}")
            return
        self.on_reset()
        self.destroy()


# ============================================================
# DASHBOARD
# ============================================================

class Dashboard(ctk.CTkFrame):
    def __init__(self, parent, user_id, on_logout, on_admin):
        super().__init__(parent, fg_color=BG)
        self.parent = parent
        self.user_id = user_id
        self.on_logout = on_logout
        self.on_admin = on_admin
        self._face_queue = None
        self._face_job = None
        self._face_running = False
        self._pending_app = None

        user = get_user(user_id)
        if not user:
            messagebox.showerror("Error", "User account not found.")
            return
        self.username = user["username"]
        self.full_name = user["name"]

        self.build_header()
        self.build_content()
        self.load_apps()

    def build_header(self):
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=78)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", padx=28)
        ctk.CTkLabel(brand, text="●", text_color=ACCENT, font=ctk.CTkFont(size=26)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(brand, text="FaceGuard", text_color=TEXT, font=ctk.CTkFont(size=23, weight="bold")).pack(side="left")
        ctk.CTkLabel(brand, text="  Secure local app access", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(side="left")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right", padx=22)
        ctk.CTkButton(actions, text="⚙ Admin", width=92, height=34, fg_color=SURFACE_2, hover_color=BORDER, command=self.on_admin).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Logout", width=82, height=34, fg_color="#3A171B", hover_color="#542027", text_color="#FCA5A5", command=self.on_logout).pack(side="left", padx=4)

    def build_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=25)

        welcome = ctk.CTkFrame(content, fg_color="transparent")
        welcome.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(welcome, text=f"Welcome back, {self.full_name}", text_color=TEXT, font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(welcome, text=f"@{self.username}  •  Choose an application to begin secure authentication.", text_color=MUTED, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(4, 0))

        security = ctk.CTkFrame(content, fg_color="#101E35", corner_radius=14, border_width=1, border_color="#20385F")
        security.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(security, text="🛡", font=ctk.CTkFont(size=22)).pack(side="left", padx=(16, 8), pady=12)
        ctk.CTkLabel(security, text="Protected by application PIN + liveness + registered face", text_color="#C7DBFF", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        badge(security, "LOCAL ONLY", "blue").pack(side="right", padx=16)

        self.grid_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)

    def load_apps(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        apps = get_user_permissions(self.user_id)
        if not apps:
            empty = ctk.CTkFrame(self.grid_frame, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
            empty.pack(fill="x", pady=20)
            ctk.CTkLabel(empty, text="No protected applications", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(25, 5))
            ctk.CTkLabel(empty, text="Ask the administrator to assign applications to your account.", text_color=MUTED).pack(pady=(0, 25))
            return

        for col in range(2):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="apps")

        for i, app in enumerate(apps):
            card = ctk.CTkFrame(self.grid_frame, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
            card.grid(row=i // 2, column=i % 2, padx=(0 if i % 2 == 0 else 9, 9 if i % 2 == 0 else 0), pady=9, sticky="nsew")
            self.grid_frame.grid_rowconfigure(i // 2, weight=1)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=18, pady=(17, 5))
            icon = "▣" if "Chrome" not in app["app_name"] else "◉"
            ctk.CTkLabel(top, text=icon, text_color=ACCENT, font=ctk.CTkFont(size=27)).pack(side="left", padx=(0, 10))
            title_box = ctk.CTkFrame(top, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(title_box, text=app["app_name"], text_color=TEXT, font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(title_box, text="Protected application", text_color=MUTED, font=ctk.CTkFont(size=10)).pack(anchor="w")

            status_row = ctk.CTkFrame(card, fg_color="transparent")
            status_row.pack(fill="x", padx=18, pady=(6, 12))
            configured = bool(app["executable_path"])
            app_pin = get_user_app_pin(self.user_id, app["id"])
            badge(status_row, "READY" if configured else "PATH NEEDED", "success" if configured else "warning").pack(side="left", padx=(0, 6))
            badge(status_row, "PIN SET" if app_pin else "PIN NOT SET", "success" if app_pin else "danger").pack(side="left")

            ctk.CTkButton(card, text="Authenticate & Open  →", height=40, corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"), command=lambda a=app: self.start_auth(a)).pack(fill="x", padx=18, pady=(0, 18))

    def start_auth(self, app):
        if self._face_running:
            return
        if not has_permission(self.user_id, app["id"]):
            record_attempt(self.username, app["app_name"], "NOT_CHECKED", "NOT_CHECKED", "ACCESS DENIED")
            messagebox.showerror("Access Denied", "You do not have permission for this application.")
            return
        if not get_user_app_pin(self.user_id, app["id"]):
            record_attempt(self.username, app["app_name"], "NOT_CONFIGURED", "NOT_CHECKED", "ACCESS DENIED")
            messagebox.showerror("PIN Not Configured", f"No PIN is configured for {app['app_name']}.\n\nPlease configure an application PIN before accessing it.")
            return
        self._pending_app = app
        PinDialog(self, self.user_id, app, self.after_pin)

    def after_pin(self, pin_ok, pin_result, _face_result):
        app = self._pending_app
        if not app:
            messagebox.showerror("Authentication Error", "Selected application information is missing.")
            return
        if pin_ok == "RESET_REQUEST":
            self.start_pin_reset(app)
            return
        if not pin_ok:
            return
        model = get_face_model(self.user_id)
        if not model:
            record_attempt(self.username, app["app_name"], "SUCCESS", "FAILED", "ACCESS DENIED")
            messagebox.showerror("Access Denied", "Registered face model is missing.")
            return
        self.start_face_verification(app, model["model_path"], "access")

    def start_pin_reset(self, app):
        if not has_permission(self.user_id, app["id"]):
            record_attempt(self.username, app["app_name"], "RESET_REQUEST", "NOT_CHECKED", "RESET_DENIED")
            messagebox.showerror("Reset Denied", "Your account does not have permission for this application.")
            return
        model = get_face_model(self.user_id)
        if not model:
            record_attempt(self.username, app["app_name"], "RESET_REQUEST", "FAILED", "RESET_DENIED")
            messagebox.showerror("Reset Denied", "A registered face model is required to reset the PIN.")
            return
        self.start_face_verification(app, model["model_path"], "reset")

    def start_face_verification(self, app, model_path, purpose):
        if self._face_running:
            return
        self._face_running = True
        self._face_queue = queue.Queue()

        self.face_status = ctk.CTkToplevel(self)
        self.face_status.title("FaceGuard • Identity Verification")
        self.face_status.geometry("560x430")
        self.face_status.resizable(False, False)
        self.face_status.configure(fg_color=BG)
        self.face_status.transient(self)
        self.face_status.grab_set()
        self.face_status.protocol("WM_DELETE_WINDOW", self.cancel_face_verification)

        box = ctk.CTkFrame(self.face_status, fg_color=SURFACE, corner_radius=20, border_width=1, border_color=BORDER)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(box, text="◉", text_color=ACCENT, font=ctk.CTkFont(size=42)).pack(pady=(18, 0))
        ctk.CTkLabel(box, text="Verify Your Identity", text_color=TEXT, font=ctk.CTkFont(size=23, weight="bold")).pack()
        ctk.CTkLabel(box, text=app["app_name"], text_color=ACCENT, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(4, 10))

        if purpose == "reset":
            msg = "PIN reset requires your registered face and permission for this application."
        else:
            msg = "Follow the camera prompts to complete liveness and face verification."
        ctk.CTkLabel(box, text=msg, text_color=MUTED, wraplength=430, justify="center").pack(pady=(0, 16))

        self.face_status_label = ctk.CTkLabel(box, text="Starting camera…", text_color=TEXT, font=ctk.CTkFont(size=15, weight="bold"), wraplength=440)
        self.face_status_label.pack(pady=12)

        self.face_progress = ctk.CTkProgressBar(box, width=390, height=8, corner_radius=5, progress_color=ACCENT)
        self.face_progress.set(0.05)
        self.face_progress.pack(pady=12)

        ctk.CTkLabel(box, text="Camera processing stays on this computer.", text_color="#64748B", font=ctk.CTkFont(size=10)).pack(pady=(8, 5))
        ctk.CTkButton(box, text="Cancel", width=150, height=34, fg_color="transparent", border_width=1, border_color=BORDER, hover_color=SURFACE_2, text_color=MUTED, command=self.cancel_face_verification).pack()

        self._face_job = self.after(60, self._poll_face_queue, app, purpose)
        threading.Thread(target=self._face_worker, args=(model_path,), daemon=True).start()

    def cancel_face_verification(self):
        if not self._face_running:
            return
        # The recognition worker owns the camera. We close the UI immediately;
        # the worker is daemonized and will finish when OpenCV releases the camera.
        self._face_running = False
        if self._face_job:
            try:
                self.after_cancel(self._face_job)
            except Exception:
                pass
            self._face_job = None
        try:
            self.face_status.grab_release()
            self.face_status.destroy()
        except Exception:
            pass

    def _face_worker(self, model_path):
        try:
            def progress(text):
                if self._face_queue is not None:
                    self._face_queue.put(("progress", text))
            ok, message = verify_user_face(model_path, progress_callback=progress)
            self._face_queue.put(("done", ok, message))
        except Exception as exc:
            self._face_queue.put(("done", False, str(exc)))

    def _poll_face_queue(self, app, purpose):
        if not self._face_running:
            return
        try:
            while True:
                item = self._face_queue.get_nowait()
                if item[0] == "progress":
                    if self.face_status.winfo_exists():
                        self.face_status_label.configure(text=item[1])
                        self.face_progress.set(self._progress_from_text(item[1]))
                elif item[0] == "done":
                    self._finish_face_verification(app, purpose, item[1], item[2])
                    return
        except queue.Empty:
            pass
        except Exception as exc:
            self._finish_face_verification(app, purpose, False, str(exc))
            return
        if self._face_running:
            self._face_job = self.after(60, self._poll_face_queue, app, purpose)

    @staticmethod
    def _progress_from_text(text):
        lower = text.lower()
        if "blink" in lower:
            return 0.25
        if "left" in lower:
            return 0.50
        if "right" in lower:
            return 0.75
        if "complete" in lower or "verified" in lower:
            return 1.0
        return 0.10

    def _finish_face_verification(self, app, purpose, ok, message):
        self._face_running = False
        if self._face_job:
            try:
                self.after_cancel(self._face_job)
            except Exception:
                pass
            self._face_job = None
        try:
            self.face_status.grab_release()
            self.face_status.destroy()
        except Exception:
            pass

        if not ok:
            if purpose == "reset":
                record_attempt(self.username, app["app_name"], "RESET_REQUEST", "FAILED", "RESET_DENIED")
                messagebox.showerror("PIN Reset Denied", "Face verification failed.\n\n" + message)
            else:
                record_attempt(self.username, app["app_name"], "SUCCESS", "FAILED", "ACCESS DENIED")
                messagebox.showerror("Access Denied", "Authentication failed.\n\n" + message)
            return

        if not has_permission(self.user_id, app["id"]):
            result = "RESET_DENIED" if purpose == "reset" else "ACCESS DENIED"
            record_attempt(self.username, app["app_name"], "RESET_REQUEST" if purpose == "reset" else "SUCCESS", "SUCCESS", result)
            messagebox.showerror("Access Denied", "Your account does not have permission for this application.")
            return

        if purpose == "reset":
            record_attempt(self.username, app["app_name"], "RESET_REQUEST", "SUCCESS", "RESET_VERIFIED")
            ResetPinDialog(self, self.user_id, app, lambda: self.pin_reset_success(app))
            return

        self.finish_normal_access(app)

    def pin_reset_success(self, app):
        record_attempt(self.username, app["app_name"], "RESET_SUCCESS", "SUCCESS", "PIN_RESET")
        messagebox.showinfo("PIN Reset Successful", f"The PIN for {app['app_name']} has been reset successfully.\n\nUse the new PIN the next time you access the application.")
        self.load_apps()

    def finish_normal_access(self, app):
        try:
            special_launched = launch_special_windows_target(app["app_name"])
            if not special_launched:
                executable_path = app["executable_path"]
                if not executable_path:
                    raise FileNotFoundError(f"No executable path is configured for {app['app_name']}.")
                launch_application(executable_path)
            record_attempt(self.username, app["app_name"], "SUCCESS", "SUCCESS", "ACCESS GRANTED")
            messagebox.showinfo("Access Granted", f"{app['app_name']} is being opened.")
        except Exception as exc:
            record_attempt(self.username, app["app_name"], "SUCCESS", "SUCCESS", "LAUNCH FAILED")
            messagebox.showerror("Launch Error", str(exc))
