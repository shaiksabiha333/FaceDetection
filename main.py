import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from authentication import hash_pin, verify_pin, valid_pin_format
from config import MODEL_DIR
from dashboard import Dashboard
from database import (
    init_db,
    get_users,
    get_applications,
    get_user_by_username,
    delete_user,
    get_security_logs,
    get_admin_password_hash,
    set_admin_password,
    set_user_permissions,
)
from registration import register_user
from settings import SettingsWindow


# ============================================================
# FACEGUARD - MAIN APPLICATION
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class FaceGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FaceGuard - Multi-Factor Application Authentication")
        self.geometry("1100x760")
        self.minsize(950, 680)

        init_db()

        self.current_user_id = None
        self.selected_user_id = None

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.show_welcome()

    # --------------------------------------------------------
    # GENERAL UI HELPERS
    # --------------------------------------------------------

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_welcome(self):
        self.clear()

        outer = ctk.CTkFrame(self, corner_radius=0, fg_color="#181818")
        outer.pack(fill="both", expand=True)

        # Header
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=45, pady=(35, 10))

        ctk.CTkLabel(
            header,
            text="FaceGuard",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#66ccff",
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="LOCAL APPLICATION SECURITY",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#777777",
        ).pack(side="right", pady=12)

        # Main card
        card = ctk.CTkFrame(
            outer,
            corner_radius=22,
            fg_color="#242424",
            border_width=1,
            border_color="#3a3a3a",
        )
        card.pack(fill="both", expand=True, padx=45, pady=25)

        ctk.CTkLabel(
            card,
            text="Secure Application Access",
            font=ctk.CTkFont(size=30, weight="bold"),
        ).pack(pady=(55, 8))

        ctk.CTkLabel(
            card,
            text="Authenticate with your application PIN and registered face.",
            font=ctk.CTkFont(size=15),
            text_color="#999999",
        ).pack(pady=(0, 35))

        users = get_users()

        if users:
            ctk.CTkLabel(
                card,
                text="Registered user",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=(5, 8))

            self.user_options = {
                u["username"]: u["id"] for u in users
            }

            self.user_var = ctk.StringVar(
                value=users[0]["username"]
            )
            self.selected_user_id = users[0]["id"]

            self.user_menu = ctk.CTkOptionMenu(
                card,
                variable=self.user_var,
                values=[u["username"] for u in users],
                width=330,
                height=42,
                command=self.select_user_option,
            )
            self.user_menu.pack(pady=5)

            ctk.CTkButton(
                card,
                text="Continue to Dashboard  →",
                width=330,
                height=46,
                corner_radius=10,
                font=ctk.CTkFont(size=15, weight="bold"),
                command=self.continue_user,
            ).pack(pady=28)

        else:
            ctk.CTkLabel(
                card,
                text="No registered users found.",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#ffbb66",
            ).pack(pady=(30, 5))

            ctk.CTkLabel(
                card,
                text="Open Admin Setup to register the first user.",
                text_color="#888888",
            ).pack(pady=5)

        ctk.CTkButton(
            card,
            text="⚙  Admin Setup / Registration",
            width=280,
            height=40,
            fg_color="#333333",
            hover_color="#444444",
            command=self.admin_setup,
        ).pack(pady=10)

        ctk.CTkLabel(
            outer,
            text="🔒 All authentication data is stored locally on this computer.",
            text_color="#666666",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 20))

    def select_user_option(self, value):
        self.selected_user_id = self.user_options.get(value)

    def continue_user(self):
        if not self.selected_user_id:
            messagebox.showerror("User Required", "Please select a user.")
            return

        self.current_user_id = self.selected_user_id
        self.show_dashboard()

    def show_dashboard(self):
        self.clear()

        Dashboard(
            self,
            self.current_user_id,
            on_logout=self.logout,
            on_admin=self.admin_setup,
        ).pack(fill="both", expand=True)

    def logout(self):
        self.current_user_id = None
        self.selected_user_id = None
        self.show_welcome()

    def admin_setup(self):
        AdminPasswordWindow(self)

    def refresh_welcome(self):
        self.show_welcome()


# ============================================================
# ADMIN PASSWORD WINDOW
# ============================================================

class AdminPasswordWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.title("FaceGuard - Administrator Authentication")
        self.geometry("460x330")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        card = ctk.CTkFrame(self, corner_radius=18)
        card.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(
            card,
            text="Administrator",
            font=ctk.CTkFont(size=25, weight="bold"),
        ).pack(pady=(30, 5))

        ctk.CTkLabel(
            card,
            text="Protected administration area",
            text_color="#888888",
        ).pack(pady=(0, 22))

        self.password_entry = ctk.CTkEntry(
            card,
            width=310,
            height=42,
            show="*",
            placeholder_text="Administrator password",
        )
        self.password_entry.pack(pady=8)

        ctk.CTkButton(
            card,
            text="Authenticate",
            width=220,
            height=42,
            command=self.login,
        ).pack(pady=15)

        ctk.CTkLabel(
            card,
            text="First use: create a password of at least 6 characters.",
            text_color="#666666",
            font=ctk.CTkFont(size=11),
            wraplength=320,
        ).pack(pady=5)

        self.password_entry.bind("<Return>", lambda _event: self.login())
        self.after(100, self.password_entry.focus)

    def login(self):
        password = self.password_entry.get()

        if not password:
            messagebox.showerror(
                "Missing Password",
                "Please enter the administrator password.",
                parent=self,
            )
            return

        stored_hash = get_admin_password_hash()

        if stored_hash is None:
            if len(password) < 6:
                messagebox.showerror(
                    "Weak Password",
                    "Administrator password must contain at least 6 characters.",
                    parent=self,
                )
                return

            set_admin_password(hash_pin(password))

            messagebox.showinfo(
                "Admin Password Created",
                "Administrator password created successfully.",
                parent=self,
            )

            self.destroy()
            AdminPanel(self.parent)
            return

        if verify_pin(password, stored_hash):
            self.destroy()
            AdminPanel(self.parent)
        else:
            messagebox.showerror(
                "Access Denied",
                "Incorrect administrator password.",
                parent=self,
            )
            self.password_entry.delete(0, "end")
            self.password_entry.focus()


# ============================================================
# ADMIN PANEL
# ============================================================

class AdminPanel(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.title("FaceGuard - Administrator")
        self.geometry("1180x760")
        self.minsize(1050, 700)
        self.transient(parent)
        self.grab_set()

        self.build()

    def build(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(20, 5))

        ctk.CTkLabel(
            header,
            text="Administrator Console",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="SECURITY MANAGEMENT",
            text_color="#66ccff",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="right", pady=8)

        ctk.CTkLabel(
            self,
            text="Register users, assign application access, configure paths and review security events.",
            text_color="#888888",
        ).pack(pady=(0, 12))

        tabs = ctk.CTkTabview(self, corner_radius=12)
        tabs.pack(fill="both", expand=True, padx=25, pady=10)

        register_tab = tabs.add("Register User")
        users_tab = tabs.add("Users")
        apps_tab = tabs.add("Application Paths")
        logs_tab = tabs.add("Security Logs")

        self.build_registration(register_tab)
        self.build_users(users_tab)
        self.build_apps(apps_tab)
        self.build_logs(logs_tab)

    # --------------------------------------------------------
    # REGISTRATION
    # --------------------------------------------------------

    def build_registration(self, parent):
        content = ctk.CTkScrollableFrame(parent)
        content.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            content,
            text="Create a New User",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 3))

        ctk.CTkLabel(
            content,
            text="Each selected application gets its own private PIN.",
            text_color="#888888",
        ).pack(anchor="w", padx=15, pady=(0, 18))

        info = ctk.CTkFrame(content, corner_radius=14)
        info.pack(fill="x", padx=10, pady=5)

        self.name_e = ctk.CTkEntry(
            info,
            width=360,
            height=40,
            placeholder_text="Full name",
        )
        self.name_e.grid(row=0, column=0, padx=15, pady=10, sticky="ew")

        self.user_e = ctk.CTkEntry(
            info,
            width=360,
            height=40,
            placeholder_text="Unique username",
        )
        self.user_e.grid(row=1, column=0, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(
            info,
            text="User information",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=1, padx=20, pady=(10, 3), sticky="w")

        ctk.CTkLabel(
            info,
            text="PINs must contain 1-12 digits.",
            text_color="#888888",
        ).grid(row=1, column=1, padx=20, pady=3, sticky="w")

        info.grid_columnconfigure(0, weight=1)
        info.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            content,
            text="Application Access & PINs",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(25, 3))

        ctk.CTkLabel(
            content,
            text="Select an application and set its private PIN and confirmation.",
            text_color="#888888",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.app_rows = {}

        for app in get_applications():
            row = ctk.CTkFrame(
                content,
                corner_radius=12,
                border_width=1,
                border_color="#383838",
            )
            row.pack(fill="x", padx=10, pady=6)

            enabled = ctk.BooleanVar(value=False)
            pin_entry = ctk.CTkEntry(
                row,
                width=180,
                height=38,
                placeholder_text="PIN",
                show="*",
                state="disabled",
            )
            confirm_entry = ctk.CTkEntry(
                row,
                width=180,
                height=38,
                placeholder_text="Confirm PIN",
                show="*",
                state="disabled",
            )

            def toggle_entries(var=enabled, pin=pin_entry, confirm=confirm_entry):
                state = "normal" if var.get() else "disabled"
                pin.configure(state=state)
                confirm.configure(state=state)
                if not var.get():
                    pin.delete(0, "end")
                    confirm.delete(0, "end")

            ctk.CTkCheckBox(
                row,
                text=app["app_name"],
                variable=enabled,
                command=toggle_entries,
                width=190,
            ).pack(side="left", padx=15, pady=14)

            pin_entry.pack(side="left", padx=6, pady=10)
            confirm_entry.pack(side="left", padx=6, pady=10)

            self.app_rows[app["id"]] = {
                "enabled": enabled,
                "pin": pin_entry,
                "confirm": confirm_entry,
            }

        self.reg_status = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(size=13),
        )
        self.reg_status.pack(pady=(18, 5))

        self.reg_progress = ctk.CTkProgressBar(content, width=600)
        self.reg_progress.set(0)
        self.reg_progress.pack(pady=5)
        self.reg_progress.pack_forget()

        ctk.CTkButton(
            content,
            text="Register User & Capture Face",
            width=300,
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.do_register,
        ).pack(pady=(12, 25))

    def do_register(self):
        name = self.name_e.get().strip()
        username = self.user_e.get().strip()

        application_ids = []
        application_pins = {}

        for app_id, row in self.app_rows.items():
            if row["enabled"].get():
                pin = row["pin"].get().strip()
                confirm = row["confirm"].get().strip()

                application_ids.append(app_id)
                application_pins[app_id] = (pin, confirm)

        if not name or not username:
            messagebox.showerror(
                "Missing Information",
                "Enter the full name and username.",
                parent=self,
            )
            return

        if get_user_by_username(username):
            messagebox.showerror(
                "Username Exists",
                "Choose a different username.",
                parent=self,
            )
            return

        if not application_ids:
            messagebox.showerror(
                "No Application Selected",
                "Select at least one application.",
                parent=self,
            )
            return

        for app_id in application_ids:
            pin, confirm = application_pins[app_id]

            if not valid_pin_format(pin):
                messagebox.showerror(
                    "Invalid PIN",
                    "Each PIN must contain only digits and be 1-12 digits long.",
                    parent=self,
                )
                return

            if pin != confirm:
                app = next(
                    a for a in get_applications() if a["id"] == app_id
                )
                messagebox.showerror(
                    "PIN Mismatch",
                    f"PIN and Confirm PIN do not match for {app['app_name']}.",
                    parent=self,
                )
                return

        # Disable the registration button indirectly by changing status.
        self.reg_status.configure(
            text="Starting camera registration...",
            text_color="#66ccff",
        )
        self.reg_progress.set(0)
        self.reg_progress.pack(pady=5)
        self.update_idletasks()

        def progress_callback(message):
            # IMPORTANT:
            # register_user/train_model_from_camera sends ONE text message.
            # The old callback expected (n, total), causing the error shown
            # by the user. This callback intentionally accepts one argument.
            try:
                self.after(
                    0,
                    lambda m=str(message): self.update_registration_status(m),
                )
            except Exception:
                pass

        def worker():
            try:
                user_id = register_user(
                    name=name,
                    username=username,
                    application_pins=application_pins,
                    application_ids=application_ids,
                    progress_callback=progress_callback,
                )

                self.after(
                    0,
                    lambda uid=user_id: self.registration_finished(
                        True, uid, name
                    ),
                )

            except Exception as exc:
                self.after(
                    0,
                    lambda err=str(exc): self.registration_finished(
                        False, err, name
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def update_registration_status(self, message):
        if self.winfo_exists():
            self.reg_status.configure(
                text=str(message),
                text_color="#66ccff",
            )

    def registration_finished(self, success, value, name):
        if not self.winfo_exists():
            return

        self.reg_progress.pack_forget()

        if success:
            self.reg_status.configure(
                text="✓ Registration Successful",
                text_color="#55dd88",
            )

            messagebox.showinfo(
                "Registration Successful",
                f"{name} has been registered successfully.\n\n"
                "Application permissions, private PINs and the face model were saved.",
                parent=self,
            )

            self.clear_registration_form()
            self.parent.refresh_welcome()
        else:
            self.reg_status.configure(
                text="Registration failed",
                text_color="#ff7777",
            )

            messagebox.showerror(
                "Registration Error",
                str(value),
                parent=self,
            )

    def clear_registration_form(self):
        self.name_e.delete(0, "end")
        self.user_e.delete(0, "end")

        for row in self.app_rows.values():
            row["enabled"].set(False)
            row["pin"].configure(state="normal")
            row["confirm"].configure(state="normal")
            row["pin"].delete(0, "end")
            row["confirm"].delete(0, "end")
            row["pin"].configure(state="disabled")
            row["confirm"].configure(state="disabled")

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    def build_users(self, parent):
        self.users_box = ctk.CTkScrollableFrame(parent)
        self.users_box.pack(fill="both", expand=True, padx=20, pady=20)
        self.refresh_users()

    def refresh_users(self):
        for widget in self.users_box.winfo_children():
            widget.destroy()

        users = get_users()

        if not users:
            ctk.CTkLabel(
                self.users_box,
                text="No users registered.",
                text_color="#888888",
            ).pack(pady=30)
            return

        for user in users:
            row = ctk.CTkFrame(
                self.users_box,
                corner_radius=10,
            )
            row.pack(fill="x", pady=6)

            ctk.CTkLabel(
                row,
                text=user["name"],
                font=ctk.CTkFont(size=15, weight="bold"),
                width=250,
                anchor="w",
            ).pack(side="left", padx=15, pady=13)

            ctk.CTkLabel(
                row,
                text=f'@{user["username"]}',
                text_color="#888888",
                width=180,
                anchor="w",
            ).pack(side="left", padx=5)

            ctk.CTkButton(
                row,
                text="Delete",
                width=90,
                fg_color="#8f3030",
                hover_color="#aa3838",
                command=lambda uid=user["id"], un=user["username"]: self.delete_user(uid, un),
            ).pack(side="right", padx=12)

    def delete_user(self, user_id, username):
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete user '{username}' and their registered face model?",
            parent=self,
        ):
            return

        delete_user(user_id)

        model_path = MODEL_DIR / f"user_{user_id}.yml"
        try:
            if model_path.exists():
                model_path.unlink()
        except OSError:
            pass

        self.refresh_users()
        self.parent.refresh_welcome()

    # --------------------------------------------------------
    # APPLICATION PATHS
    # --------------------------------------------------------

    def build_apps(self, parent):
        ctk.CTkLabel(
            parent,
            text="Application Executable Paths",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            parent,
            text="Configure the real Windows executable used after successful authentication.",
            text_color="#888888",
        ).pack(pady=(0, 15))

        box = ctk.CTkScrollableFrame(parent)
        box.pack(fill="both", expand=True, padx=20, pady=10)

        for app in get_applications():
            row = ctk.CTkFrame(box, corner_radius=10)
            row.pack(fill="x", pady=6)

            configured = bool(app["executable_path"])

            ctk.CTkLabel(
                row,
                text=app["app_name"],
                width=190,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left", padx=12, pady=14)

            ctk.CTkLabel(
                row,
                text=app["executable_path"] or "Path not configured",
                width=560,
                anchor="w",
                text_color="#55dd88" if configured else "#ff7777",
            ).pack(side="left", padx=8)

            ctk.CTkButton(
                row,
                text="Edit",
                width=80,
                command=self.open_settings,
            ).pack(side="right", padx=12)

    def open_settings(self):
        SettingsWindow(self)

    # --------------------------------------------------------
    # SECURITY LOGS
    # --------------------------------------------------------

    def build_logs(self, parent):
        ctk.CTkLabel(
            parent,
            text="Security Activity",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            parent,
            text="Recent authentication and PIN-reset events.",
            text_color="#888888",
        ).pack(pady=(0, 12))

        box = ctk.CTkTextbox(parent, height=520)
        box.pack(fill="both", expand=True, padx=20, pady=10)

        logs = get_security_logs()

        if not logs:
            box.insert("end", "No security events recorded yet.\n")
        else:
            for log in logs:
                box.insert(
                    "end",
                    f"[{log['date']} {log['time']}]  "
                    f"{log['username']}  |  "
                    f"{log['application']}  |  "
                    f"PIN: {log['pin_result']}  |  "
                    f"FACE: {log['face_result']}  |  "
                    f"RESULT: {log['final_result']}\n\n",
                )

        box.configure(state="disabled")


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":
    app = FaceGuardApp()
    app.mainloop()
