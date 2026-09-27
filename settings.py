import customtkinter as ctk
from tkinter import filedialog, messagebox
from database import get_applications, update_application_path


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("FaceGuard - Settings")
        self.geometry("760x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Application Paths",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(
            self,
            text="Configure the real Windows executable used for each protected app.",
            text_color="gray",
        ).pack(pady=(0, 15))

        self.rows = {}
        for app in get_applications():
            row = ctk.CTkFrame(self)
            row.pack(fill="x", padx=25, pady=6)
            ctk.CTkLabel(row, text=app["app_name"], width=170, anchor="w").pack(
                side="left", padx=10
            )
            entry = ctk.CTkEntry(row, width=430)
            entry.insert(0, app["executable_path"])
            entry.pack(side="left", padx=5)
            ctk.CTkButton(
                row, text="Browse", width=90,
                command=lambda e=entry: self.browse(e)
            ).pack(side="left", padx=5)
            self.rows[app["id"]] = entry

        ctk.CTkButton(
            self, text="Save Settings", width=180, height=40,
            command=self.save
        ).pack(pady=25)

    def browse(self, entry):
        path = filedialog.askopenfilename(
            title="Select Windows executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def save(self):
        for app_id, entry in self.rows.items():
            update_application_path(app_id, entry.get().strip())
        messagebox.showinfo("Saved", "Application paths saved successfully.")
        self.destroy()
