# Auto Mail Receive tab — CustomTkinter rewrite
# All business logic preserved; only UI widgets changed.

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import mouse
import json
import os
import sys
from automation.mail_automation import MailAutomation

_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "muted": "#888888",
}


def _section_header(parent, title, color=None):
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color="#ffffff", anchor="w").pack(side=tk.LEFT, padx=12, pady=4)


class MailTab:
    def __init__(self, parent_frame, main_window):
        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = MailAutomation(
            main_window.game_connector,
            main_window.update_status,
            main_window.bot_core,
        )

        self.click_coords_1 = None
        self.click_coords_2 = None

        self.create_ui()
        self.load_config()

    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "mail_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    # ──────────────────────────────────────────────────────────
    def create_ui(self):
        scroll = ctk.CTkScrollableFrame(self.parent_frame, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # Intro
        intro = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        inner = ctk.CTkFrame(intro, fg_color="transparent")
        inner.pack(fill=tk.X, padx=12, pady=8)
        ctk.CTkLabel(inner, text="📧", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(tf, text="AUTO MAIL RECEIVE — Automated Mail Collection", font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(tf, text="Automatically clicks two positions to receive in-game mail", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

        # Click Positions
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Click Positions")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        self.click_coord_var1 = tk.StringVar(value="Not set")
        self.click_coord_var2 = tk.StringVar(value="Not set")

        for i, (var, cmd) in enumerate([
            (self.click_coord_var1, self.set_click_position_1),
            (self.click_coord_var2, self.set_click_position_2),
        ], 1):
            row = ctk.CTkFrame(coord_body, fg_color="transparent")
            row.pack(fill=tk.X, pady=(0, 4 if i == 1 else 0))
            ctk.CTkLabel(row, text=f"Position {i}:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=90, anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(row, textvariable=var, font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w").pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)
            ctk.CTkButton(row, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=60, height=28, corner_radius=6, command=cmd).pack(side=tk.RIGHT)

        # Delay
        delay_card = ctk.CTkFrame(scroll, corner_radius=8)
        delay_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(delay_card, "⏱️  Delay Settings", _A["success"])
        delay_body = ctk.CTkFrame(delay_card, fg_color="transparent")
        delay_body.pack(fill=tk.X, padx=12, pady=8)

        delay_row = ctk.CTkFrame(delay_body, fg_color="transparent")
        delay_row.pack(fill=tk.X)
        ctk.CTkLabel(delay_row, text="Delay (ms):", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=90, anchor="w").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="500")
        self.delay_entry = ctk.CTkEntry(delay_row, textvariable=self.delay_var, width=90, height=28, font=ctk.CTkFont("Segoe UI", 11), placeholder_text="500")
        self.delay_entry.pack(side=tk.LEFT, padx=(6, 8))
        ctk.CTkLabel(delay_row, text="(delay between clicks)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # Controls
        ctrl = ctk.CTkFrame(scroll, fg_color="transparent")
        ctrl.pack(fill=tk.X, pady=(4, 8))
        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack()

        self.btn_start = ctk.CTkButton(btn_row, text="▶  START", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["success"], hover_color="#258a5e", width=120, height=38, corner_radius=8, state="disabled", command=self.start_automation)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ctk.CTkButton(btn_row, text="⏹  STOP", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["danger"], hover_color="#c9302c", width=120, height=38, corner_radius=8, state="disabled", command=self.stop_automation)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_save_config = ctk.CTkButton(btn_row, text="💾  Save Config", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=130, height=38, corner_radius=8, command=self.save_config)
        self.btn_save_config.pack(side=tk.LEFT)

    # ══════════════════════════════════════════════════════════
    # BUSINESS LOGIC — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def set_click_position_1(self):
        self._set_click_position(1, self.click_coord_var1)

    def set_click_position_2(self):
        self._set_click_position(2, self.click_coord_var2)

    def _set_click_position(self, position_num, coord_var):
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return
        messagebox.showinfo("Instruction", f"Click on Position {position_num} in the game window.\nThe coordinates will be captured automatically.")
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                mouse.wait(button='left')
                x, y = mouse.get_position()
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)
                if success:
                    coords = (rel_x, rel_y)
                    if position_num == 1:
                        self.click_coords_1 = coords
                        self.automation.set_click_position_1(coords)
                    elif position_num == 2:
                        self.click_coords_2 = coords
                        self.automation.set_click_position_2(coords)
                    coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Position {position_num} set at ({rel_x}, {rel_y})")
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        threading.Thread(target=capture_click, daemon=True).start()

    def _check_enable_start(self):
        if self.click_coords_1 and self.click_coords_2:
            self.btn_start.configure(state="normal")

    def save_config(self):
        config_data = {
            "click_coords_1": list(self.click_coords_1) if self.click_coords_1 else None,
            "click_coords_2": list(self.click_coords_2) if self.click_coords_2 else None,
            "delay_ms": self.delay_var.get(),
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Mail Receive config saved successfully!")
            messagebox.showinfo("Config Saved", "Mail Receive configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Mail Receive config: {e}")

    def load_config(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("click_coords_1"):
                self.click_coords_1 = tuple(data["click_coords_1"])
                self.automation.set_click_position_1(self.click_coords_1)
                self.click_coord_var1.set(f"({self.click_coords_1[0]}, {self.click_coords_1[1]})")
            if data.get("click_coords_2"):
                self.click_coords_2 = tuple(data["click_coords_2"])
                self.automation.set_click_position_2(self.click_coords_2)
                self.click_coord_var2.set(f"({self.click_coords_2[0]}, {self.click_coords_2[1]})")
            if data.get("delay_ms"):
                self.delay_var.set(str(data["delay_ms"]))
            self._check_enable_start()
        except Exception as e:
            print(f"Failed to load Mail Receive config: {e}")

    def start_automation(self):
        if not self.main_window.set_running_tool("Auto Mail Receive"):
            return
        try:
            delay_ms = int(self.delay_var.get())
            if delay_ms < 0:
                raise ValueError
            print(f"[Mail UI] Delay input from user: {delay_ms} ms")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return
        self.automation.set_delay(delay_ms)
        print(f"[Mail UI] Delay set in automation: {delay_ms} ms")
        if self.automation.start():
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status("Auto Mail Receive started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        self.automation.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
        self.main_window.update_status("Auto Mail Receive stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
