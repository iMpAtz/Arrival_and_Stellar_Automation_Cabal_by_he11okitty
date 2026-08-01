# Heil Auto tab — CustomTkinter rewrite
# Simple auto-click automation without OCR (with inventory management)
# All business logic preserved; only UI widgets changed.

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import mouse
import json
import os
import sys
from automation.heil_automation import HeilAutomation

_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "warning": "#e8a317", "purple": "#7c3aed", "muted": "#888888",
    "surface2": "#333333",
}


def _section_header(parent, title, color=None):
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color="#ffffff", anchor="w").pack(side=tk.LEFT, padx=12, pady=4)


class HeilTab:
    def __init__(self, parent_frame, main_window):
        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = HeilAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status,
            main_window.bot_core,
        )

        self.click_coords_1 = None
        self.click_coords_2 = None
        self.click_coords_3 = None
        self.click_coords_4 = None
        self.click_coords_5 = None
        self.ocr_area_message = None

        self.create_ui()
        self.load_config()

    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "heil_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────
    def create_ui(self):
        scroll = ctk.CTkScrollableFrame(self.parent_frame, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # Intro
        intro = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        intro_inner = ctk.CTkFrame(intro, fg_color="transparent")
        intro_inner.pack(fill=tk.X, padx=12, pady=8)
        ctk.CTkLabel(intro_inner, text="🎯", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(intro_inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(tf, text="HEIL AUTO — Auto-Click with Inventory Management", font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(tf, text="1) Set 5 Click Positions  •  2) Define OCR Area  •  3) Set Delay  •  4) Start", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

        # Click positions
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Click Positions (5 required)")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        positions = [
            ("Position 1:", "(Main)", self.set_click_position_1, _A["primary"]),
            ("Position 2:", "(Close Heil)", self.set_click_position_2, _A["warning"]),
            ("Position 3:", "(Inventory sort click)", self.set_click_position_3, _A["warning"]),
            ("Position 4:", "(Cabal Icon bottom right)", self.set_click_position_4, _A["warning"]),
            ("Position 5:", "(Heil's Research)", self.set_click_position_5, _A["warning"]),
        ]

        self.click_coord_var1 = tk.StringVar(value="Not set")
        self.click_coord_var2 = tk.StringVar(value="Not set")
        self.click_coord_var3 = tk.StringVar(value="Not set")
        self.click_coord_var4 = tk.StringVar(value="Not set")
        self.click_coord_var5 = tk.StringVar(value="Not set")
        coord_vars = [self.click_coord_var1, self.click_coord_var2, self.click_coord_var3, self.click_coord_var4, self.click_coord_var5]

        for i, (label, hint, cmd, btn_color) in enumerate(positions):
            row = ctk.CTkFrame(coord_body, fg_color="transparent")
            row.pack(fill=tk.X, pady=(0, 4))
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont("Segoe UI", 11, "bold"), width=90, anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(row, textvariable=coord_vars[i], font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w").pack(side=tk.LEFT, padx=(6, 4), fill=tk.X, expand=True)
            ctk.CTkLabel(row, text=hint, font=ctk.CTkFont("Segoe UI", 9), text_color=_A["muted"]).pack(side=tk.LEFT, padx=(0, 6))
            ctk.CTkButton(row, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=btn_color, hover_color="#1a5a8e" if btn_color == _A["primary"] else "#cc8c0e", width=60, height=28, corner_radius=6, command=cmd).pack(side=tk.RIGHT)

        # OCR Detection Area
        ocr_card = ctk.CTkFrame(scroll, corner_radius=8)
        ocr_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(ocr_card, "📐  OCR Detection Area", _A["purple"])
        ocr_body = ctk.CTkFrame(ocr_card, fg_color="transparent")
        ocr_body.pack(fill=tk.X, padx=12, pady=8)

        ocr_row = ctk.CTkFrame(ocr_body, fg_color="transparent")
        ocr_row.pack(fill=tk.X)
        ctk.CTkLabel(ocr_row, text="Inventory Msg:", font=ctk.CTkFont("Segoe UI", 11, "bold"), anchor="w").pack(side=tk.LEFT)
        self.btn_define_area_message = ctk.CTkButton(ocr_row, text="Define OCR Area (Message)", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["purple"], hover_color="#6b2fc7", height=30, corner_radius=6, command=self.define_ocr_area_message)
        self.btn_define_area_message.pack(side=tk.LEFT, padx=(8, 6))
        ctk.CTkLabel(ocr_row, text="(inventory full detection)", font=ctk.CTkFont("Segoe UI", 9), text_color=_A["muted"]).pack(side=tk.LEFT)

        # Delay settings
        delay_card = ctk.CTkFrame(scroll, corner_radius=8)
        delay_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(delay_card, "⏱️  Delay Settings", _A["success"])
        delay_body = ctk.CTkFrame(delay_card, fg_color="transparent")
        delay_body.pack(fill=tk.X, padx=12, pady=8)

        d1 = ctk.CTkFrame(delay_body, fg_color="transparent")
        d1.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(d1, text="Position 1:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="1000")
        self.delay_entry = ctk.CTkEntry(d1, textvariable=self.delay_var, width=90, height=28, font=ctk.CTkFont("Segoe UI", 11), placeholder_text="1000")
        self.delay_entry.pack(side=tk.LEFT, padx=(6, 8))
        ctk.CTkLabel(d1, text="ms (delay for main click)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        d2 = ctk.CTkFrame(delay_body, fg_color="transparent")
        d2.pack(fill=tk.X)
        ctk.CTkLabel(d2, text="Positions 2-5:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side=tk.LEFT)
        ctk.CTkLabel(d2, text="1000 ms (fixed for inventory management)", font=ctk.CTkFont("Segoe UI", 11), text_color=_A["muted"]).pack(side=tk.LEFT, padx=(6, 0))

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
        self._set_click_position(1, "Main Action", self.click_coord_var1)

    def set_click_position_2(self):
        self._set_click_position(2, "Inventory Management", self.click_coord_var2)

    def set_click_position_3(self):
        self._set_click_position(3, "Inventory Management", self.click_coord_var3)

    def set_click_position_4(self):
        self._set_click_position(4, "Inventory Management", self.click_coord_var4)

    def set_click_position_5(self):
        self._set_click_position(5, "Inventory Management", self.click_coord_var5)

    def _set_click_position(self, position_num, position_type, coord_var):
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return
        messagebox.showinfo("Instruction", f"Click on Position {position_num} ({position_type}) in the game window.\nThe coordinates will be captured automatically.")
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
                    elif position_num == 3:
                        self.click_coords_3 = coords
                        self.automation.set_click_position_3(coords)
                    elif position_num == 4:
                        self.click_coords_4 = coords
                        self.automation.set_click_position_4(coords)
                    elif position_num == 5:
                        self.click_coords_5 = coords
                        self.automation.set_click_position_5(coords)
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

    def define_ocr_area_message(self):
        def area_callback(area):
            self.ocr_area_message = area
            self.automation.set_ocr_area_message(area)
            self.main_window.update_status(f"OCR area (Inventory Message) defined: {area}")
            self._check_enable_start()

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def _check_enable_start(self):
        if (self.click_coords_1 and self.click_coords_2 and
            self.click_coords_3 and self.click_coords_4 and self.click_coords_5 and
            self.ocr_area_message):
            self.btn_start.configure(state="normal")

    def save_config(self):
        config_data = {
            "click_coords_1": list(self.click_coords_1) if self.click_coords_1 else None,
            "click_coords_2": list(self.click_coords_2) if self.click_coords_2 else None,
            "click_coords_3": list(self.click_coords_3) if self.click_coords_3 else None,
            "click_coords_4": list(self.click_coords_4) if self.click_coords_4 else None,
            "click_coords_5": list(self.click_coords_5) if self.click_coords_5 else None,
            "ocr_area_message": list(self.ocr_area_message) if self.ocr_area_message else None,
            "delay_ms": self.delay_var.get(),
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Heil Auto config saved successfully!")
            messagebox.showinfo("Config Saved", "Heil Auto configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Heil Auto config: {e}")

    def load_config(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for i in range(1, 6):
                key = f"click_coords_{i}"
                if data.get(key):
                    coords = tuple(data[key])
                    setattr(self, key, coords)
                    getattr(self.automation, f"set_click_position_{i}")(coords)
                    getattr(self, f"click_coord_var{i}").set(f"({coords[0]}, {coords[1]})")
            if data.get("ocr_area_message"):
                self.ocr_area_message = tuple(data["ocr_area_message"])
                self.automation.set_ocr_area_message(self.ocr_area_message)
            if data.get("delay_ms"):
                self.delay_var.set(str(data["delay_ms"]))
            self._check_enable_start()
        except Exception as e:
            print(f"Failed to load Heil Auto config: {e}")

    def start_automation(self):
        if not self.main_window.set_running_tool("Heil Auto"):
            return
        try:
            delay_ms = int(self.delay_var.get())
            if delay_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return
        self.automation.set_delay(delay_ms)
        if self.automation.start():
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status("Heil Auto started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        self.automation.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
        self.main_window.update_status("Heil Auto stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
