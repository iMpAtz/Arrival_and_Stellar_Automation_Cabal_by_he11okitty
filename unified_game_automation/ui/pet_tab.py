# Pet Untrain tab — CustomTkinter rewrite
# Updated to support YOLO26 (ONNX) Object Detection alongside OCR.

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import mouse
import json
import os
import sys
from data.pet_data import get_pet_untrain_steps, get_default_pet_delay, get_pet_ocr_options, get_pet_yolo_class_options
from automation.pet_automation import PetAutomation

_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "warning": "#e8a317", "purple": "#7c3aed", "muted": "#888888",
    "surface2": "#333333", "teal": "#0d9488", "orange": "#ea580c",
}

# Detection mode options for the segmented button
_DETECTION_MODES = ["OCR Only", "YOLO Only", "OCR + YOLO"]
_MODE_MAP = {"OCR Only": "ocr", "YOLO Only": "yolo", "OCR + YOLO": "hybrid"}
_MODE_REVERSE = {v: k for k, v in _MODE_MAP.items()}


def _section_header(parent, title, color=None):
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color="#ffffff", anchor="w").pack(side=tk.LEFT, padx=12, pady=4)


class PetTab:
    def __init__(self, parent_frame, main_window):
        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = PetAutomation(
            game_connector=main_window.game_connector,
            ocr_engine=main_window.ocr_engine,
            status_callback=main_window.update_status,
            bot_core=main_window.bot_core,
            on_target_found=self.on_target_found,
        )

        # Coordinate storage
        self.step_coords = {step: None for step in get_pet_untrain_steps()}
        self.ocr_area = None
        self.yolo_area = None
        self.ocr_targets = []
        self.selected_ocr_options = {}

        self.create_ui()
        self.load_config()

    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "pet_config.json")
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
        ctk.CTkLabel(inner, text="🐾", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(tf, text="PET UNTRAIN — Automated Pet Skill Reroll", font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(tf, text="1) Set Positions  •  2) Define Areas  •  3) Select Mode & Targets  •  4) Start", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

        # Step coordinates
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Step Positions")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        self.step_coord_vars = {}
        steps = get_pet_untrain_steps()
        for step in steps:
            self.step_coord_vars[step] = tk.StringVar(value="Not set")
            row = ctk.CTkFrame(coord_body, fg_color="transparent")
            row.pack(fill=tk.X, pady=(0, 4))
            ctk.CTkLabel(row, text=f"{step}:", font=ctk.CTkFont("Segoe UI", 11, "bold"), anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(row, textvariable=self.step_coord_vars[step], font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w").pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)
            ctk.CTkButton(row, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=60, height=28, corner_radius=6, command=lambda s=step: self.set_step_position(s)).pack(side=tk.RIGHT)

        # ── Detection Mode Selector ──────────────────────────
        mode_card = ctk.CTkFrame(scroll, corner_radius=8)
        mode_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(mode_card, "🔀  Detection Mode", _A["teal"])
        mode_body = ctk.CTkFrame(mode_card, fg_color="transparent")
        mode_body.pack(fill=tk.X, padx=12, pady=8)

        self.detection_mode_var = tk.StringVar(value="OCR Only")
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_body,
            values=_DETECTION_MODES,
            variable=self.detection_mode_var,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            selected_color=_A["teal"],
            selected_hover_color="#0f766e",
            command=self._on_mode_changed,
        )
        self.mode_seg.pack(fill=tk.X)

        # ── OCR Area & YOLO Area buttons ─────────────────────
        area_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        area_frame.pack(fill=tk.X, pady=(0, 8))
        area_btn_row = ctk.CTkFrame(area_frame, fg_color="transparent")
        area_btn_row.pack(fill=tk.X)

        self.btn_define_ocr_area = ctk.CTkButton(
            area_btn_row, text="📐  Define OCR Area",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["purple"], hover_color="#6b2fc7",
            height=36, corner_radius=8,
            command=self.define_ocr_area,
        )
        self.btn_define_ocr_area.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.btn_define_yolo_area = ctk.CTkButton(
            area_btn_row, text="🎯  Define YOLO Area",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["teal"], hover_color="#0f766e",
            height=36, corner_radius=8,
            command=self.define_yolo_area,
        )
        self.btn_define_yolo_area.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # Area status labels
        area_status_row = ctk.CTkFrame(area_frame, fg_color="transparent")
        area_status_row.pack(fill=tk.X, pady=(4, 0))
        self.ocr_area_label = ctk.CTkLabel(area_status_row, text="OCR Area: Not set", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w")
        self.ocr_area_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.yolo_area_label = ctk.CTkLabel(area_status_row, text="YOLO Area: Not set (fallback → OCR)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="e")
        self.yolo_area_label.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # ── OCR Target selection (checkbox grid) ─────────────
        self.ocr_target_card = ctk.CTkFrame(scroll, corner_radius=8)
        self.ocr_target_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(self.ocr_target_card, "🎯  OCR Target Skills (select desired)", _A["success"])
        target_body = ctk.CTkFrame(self.ocr_target_card, fg_color="transparent")
        target_body.pack(fill=tk.X, padx=12, pady=8)

        ocr_options = get_pet_ocr_options()
        self.ocr_check_vars = {}
        # 2-column grid
        for i, opt in enumerate(ocr_options):
            r = i // 2
            c = i % 2
            var = tk.BooleanVar(value=False)
            self.ocr_check_vars[opt] = var
            cb = ctk.CTkCheckBox(
                target_body, text=opt,
                variable=var,
                font=ctk.CTkFont("Segoe UI", 11),
                corner_radius=4,
                checkbox_width=20, checkbox_height=20,
                onvalue=True, offvalue=False,
            )
            cb.grid(row=r, column=c, sticky="w", padx=(0, 16), pady=2)

        # ── YOLO26 Settings Card ─────────────────────────────
        self.yolo_card = ctk.CTkFrame(scroll, corner_radius=8)
        self.yolo_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(self.yolo_card, "🤖  YOLO26 Object Detection Settings", _A["orange"])
        yolo_body = ctk.CTkFrame(self.yolo_card, fg_color="transparent")
        yolo_body.pack(fill=tk.X, padx=12, pady=8)

        # Model Path
        model_row = ctk.CTkFrame(yolo_body, fg_color="transparent")
        model_row.pack(fill=tk.X, pady=(0, 6))
        ctk.CTkLabel(model_row, text="Model (.onnx):", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side=tk.LEFT)
        self.yolo_model_var = tk.StringVar(value="")
        self.yolo_model_entry = ctk.CTkEntry(
            model_row, textvariable=self.yolo_model_var,
            font=ctk.CTkFont("Segoe UI", 10), height=28,
            placeholder_text="Select YOLO26 .onnx model file...",
        )
        self.yolo_model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ctk.CTkButton(
            model_row, text="Browse", width=70, height=28,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=_A["orange"], hover_color="#c2410c",
            corner_radius=6, command=self._browse_yolo_model,
        ).pack(side=tk.RIGHT)

        # Confidence Threshold
        conf_row = ctk.CTkFrame(yolo_body, fg_color="transparent")
        conf_row.pack(fill=tk.X, pady=(0, 6))
        ctk.CTkLabel(conf_row, text="Confidence:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side=tk.LEFT)
        self.yolo_conf_var = tk.DoubleVar(value=0.25)
        self.yolo_conf_label = ctk.CTkLabel(conf_row, text="0.25", font=ctk.CTkFont("Segoe UI", 11), width=40, text_color=_A["orange"])
        self.yolo_conf_label.pack(side=tk.RIGHT)
        self.yolo_conf_slider = ctk.CTkSlider(
            conf_row, from_=0.05, to=0.95, number_of_steps=18,
            variable=self.yolo_conf_var,
            button_color=_A["orange"], button_hover_color="#c2410c",
            progress_color=_A["orange"],
            command=self._on_conf_changed,
        )
        self.yolo_conf_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))

        # ── YOLO Target Classes Card (checkbox grid, same style as OCR) ──
        self.yolo_target_card = ctk.CTkFrame(scroll, corner_radius=8)
        self.yolo_target_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(self.yolo_target_card, "🎯  YOLO Target Classes (select desired — OR logic)", _A["orange"])
        yolo_target_body = ctk.CTkFrame(self.yolo_target_card, fg_color="transparent")
        yolo_target_body.pack(fill=tk.X, padx=12, pady=8)

        yolo_options = get_pet_yolo_class_options()
        self._yolo_class_list = yolo_options
        self.automation.set_yolo_class_names(yolo_options)
        self.yolo_target_check_vars = {}
        # 2-column grid — identical to OCR target card
        for i, opt in enumerate(yolo_options):
            r = i // 2
            c = i % 2
            var = tk.BooleanVar(value=False)
            self.yolo_target_check_vars[opt] = var
            cb = ctk.CTkCheckBox(
                yolo_target_body, text=opt,
                variable=var,
                font=ctk.CTkFont("Segoe UI", 11),
                corner_radius=4,
                checkbox_width=20, checkbox_height=20,
                onvalue=True, offvalue=False,
            )
            cb.grid(row=r, column=c, sticky="w", padx=(0, 16), pady=2)

        # ── Delay ────────────────────────────────────────────
        delay_card = ctk.CTkFrame(scroll, corner_radius=8)
        delay_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(delay_card, "⏱️  Delay Settings", _A["warning"])
        delay_body = ctk.CTkFrame(delay_card, fg_color="transparent")
        delay_body.pack(fill=tk.X, padx=12, pady=8)

        delay_row = ctk.CTkFrame(delay_body, fg_color="transparent")
        delay_row.pack(fill=tk.X)
        ctk.CTkLabel(delay_row, text="Delay (ms):", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=90, anchor="w").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value=str(get_default_pet_delay()))
        self.delay_entry = ctk.CTkEntry(delay_row, textvariable=self.delay_var, width=90, height=28, font=ctk.CTkFont("Segoe UI", 11), placeholder_text="800")
        self.delay_entry.pack(side=tk.LEFT, padx=(6, 8))
        ctk.CTkLabel(delay_row, text="(delay between actions)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # ── Controls ─────────────────────────────────────────
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

        # Apply initial mode visibility
        self._on_mode_changed(self.detection_mode_var.get())

    # ══════════════════════════════════════════════════════════
    # MODE SWITCHING & YOLO UI HELPERS
    # ══════════════════════════════════════════════════════════

    def _on_mode_changed(self, selected_mode):
        """Show/hide OCR and YOLO sections based on detection mode."""
        mode = _MODE_MAP.get(selected_mode, "ocr")
        self.automation.set_detection_mode(mode)

        show_ocr = mode in ("ocr", "hybrid")
        show_yolo = mode in ("yolo", "hybrid")

        # Toggle OCR section visibility
        if show_ocr:
            self.ocr_target_card.pack(fill=tk.X, pady=(0, 8))
        else:
            self.ocr_target_card.pack_forget()

        # Toggle YOLO settings + target card visibility
        if show_yolo:
            self.yolo_card.pack(fill=tk.X, pady=(0, 8))
            self.yolo_target_card.pack(fill=tk.X, pady=(0, 8))
        else:
            self.yolo_card.pack_forget()
            self.yolo_target_card.pack_forget()

        # Toggle area buttons
        if show_ocr:
            self.btn_define_ocr_area.configure(state="normal")
        else:
            self.btn_define_ocr_area.configure(state="disabled")

        if show_yolo:
            self.btn_define_yolo_area.configure(state="normal")
        else:
            self.btn_define_yolo_area.configure(state="disabled")

        self._check_enable_start()

    def _browse_yolo_model(self):
        """Open a file dialog to select a YOLO26 ONNX model file."""
        file_path = filedialog.askopenfilename(
            title="Select YOLO26 ONNX Model",
            filetypes=[("ONNX Models", "*.onnx"), ("All files", "*.*")],
        )
        if file_path:
            self.yolo_model_var.set(file_path)
            self.automation.set_yolo_model_path(file_path)
            self.main_window.update_status(f"YOLO model selected: {os.path.basename(file_path)}")
            self._check_enable_start()

    def _on_conf_changed(self, value):
        """Update the confidence threshold display and push to automation."""
        val = round(float(value), 2)
        self.yolo_conf_label.configure(text=f"{val:.2f}")
        self.automation.set_yolo_conf_threshold(val)

    def _get_selected_yolo_targets(self):
        """Return a list of YOLO class names that the user has checked."""
        return [name for name, var in self.yolo_target_check_vars.items() if var.get()]

    # ══════════════════════════════════════════════════════════
    # BUSINESS LOGIC
    # ══════════════════════════════════════════════════════════

    def set_step_position(self, step_name):
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return
        messagebox.showinfo("Instruction", f"Click on '{step_name}' in the game window.\nThe coordinates will be captured automatically.")
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                mouse.wait(button='left')
                x, y = mouse.get_position()
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)
                if success:
                    self.step_coords[step_name] = (rel_x, rel_y)
                    self.automation.set_step_coords(step_name, (rel_x, rel_y))
                    self.step_coord_vars[step_name].set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"'{step_name}' set at ({rel_x}, {rel_y})")
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        threading.Thread(target=capture_click, daemon=True).start()

    def define_ocr_area(self):
        def area_callback(area):
            self.ocr_area = area
            self.automation.set_ocr_area(area)
            self.ocr_area_label.configure(text=f"OCR Area: {area}")
            # Update YOLO fallback label if no dedicated YOLO area
            if not self.yolo_area:
                self.yolo_area_label.configure(text=f"YOLO Area: Not set (fallback → OCR)")
            self._check_enable_start()
            self.main_window.update_status(f"OCR area defined: {area}")

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def define_yolo_area(self):
        """Define a dedicated ROI area for YOLO26 detection, separate from OCR."""
        def area_callback(area):
            self.yolo_area = area
            self.automation.set_yolo_area(area)
            self.yolo_area_label.configure(text=f"YOLO Area: {area}")
            self._check_enable_start()
            self.main_window.update_status(f"YOLO area defined: {area}")

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def _check_enable_start(self):
        """Enable the Start button when minimum requirements for the active mode are met."""
        all_coords_set = all(coords is not None for coords in self.step_coords.values())
        if not all_coords_set:
            self.btn_start.configure(state="disabled")
            return

        mode = _MODE_MAP.get(self.detection_mode_var.get(), "ocr")

        if mode == "ocr":
            ready = self.ocr_area is not None
        elif mode == "yolo":
            has_area = (self.yolo_area is not None) or (self.ocr_area is not None)
            has_model = bool(self.yolo_model_var.get().strip())
            ready = has_area and has_model
        else:  # hybrid
            has_ocr_area = self.ocr_area is not None
            has_yolo_area = (self.yolo_area is not None) or (self.ocr_area is not None)
            has_model = bool(self.yolo_model_var.get().strip())
            ready = has_ocr_area and has_yolo_area and has_model

        self.btn_start.configure(state="normal" if ready else "disabled")

    def _get_selected_ocr_targets(self):
        targets = []
        for opt, var in self.ocr_check_vars.items():
            if var.get():
                targets.append(opt)
        return targets

    def save_config(self):
        config_data = {
            "step_coords": {k: list(v) if v else None for k, v in self.step_coords.items()},
            "ocr_area": list(self.ocr_area) if self.ocr_area else None,
            "yolo_area": list(self.yolo_area) if self.yolo_area else None,
            "delay_ms": self.delay_var.get(),
            "selected_ocr_options": [opt for opt, var in self.ocr_check_vars.items() if var.get()],
            # YOLO settings
            "detection_mode": _MODE_MAP.get(self.detection_mode_var.get(), "ocr"),
            "yolo_model_path": self.yolo_model_var.get(),
            "yolo_conf_threshold": round(self.yolo_conf_var.get(), 2),
            "yolo_selected_targets": self._get_selected_yolo_targets(),
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Pet Untrain config saved successfully!")
            messagebox.showinfo("Config Saved", "Pet Untrain configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Pet Untrain config: {e}")

    def load_config(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Step coordinates
            if data.get("step_coords"):
                for step, coords in data["step_coords"].items():
                    if coords and step in self.step_coords:
                        self.step_coords[step] = tuple(coords)
                        self.automation.set_step_coords(step, tuple(coords))
                        if step in self.step_coord_vars:
                            self.step_coord_vars[step].set(f"({coords[0]}, {coords[1]})")

            # OCR area
            if data.get("ocr_area"):
                self.ocr_area = tuple(data["ocr_area"])
                self.automation.set_ocr_area(self.ocr_area)
                self.ocr_area_label.configure(text=f"OCR Area: {self.ocr_area}")

            # YOLO area
            if data.get("yolo_area"):
                self.yolo_area = tuple(data["yolo_area"])
                self.automation.set_yolo_area(self.yolo_area)
                self.yolo_area_label.configure(text=f"YOLO Area: {self.yolo_area}")

            # Delay
            if data.get("delay_ms"):
                self.delay_var.set(str(data["delay_ms"]))

            # OCR options
            if data.get("selected_ocr_options"):
                for opt in data["selected_ocr_options"]:
                    if opt in self.ocr_check_vars:
                        self.ocr_check_vars[opt].set(True)

            # Detection mode
            if data.get("detection_mode"):
                mode_key = data["detection_mode"]
                display = _MODE_REVERSE.get(mode_key, "OCR Only")
                self.detection_mode_var.set(display)
                self.automation.set_detection_mode(mode_key)

            # YOLO model path
            if data.get("yolo_model_path"):
                self.yolo_model_var.set(data["yolo_model_path"])
                self.automation.set_yolo_model_path(data["yolo_model_path"])

            # YOLO selected targets
            if data.get("yolo_selected_targets"):
                for target_name in data["yolo_selected_targets"]:
                    if target_name in self.yolo_target_check_vars:
                        self.yolo_target_check_vars[target_name].set(True)

            # YOLO confidence
            if data.get("yolo_conf_threshold") is not None:
                val = float(data["yolo_conf_threshold"])
                self.yolo_conf_var.set(val)
                self.yolo_conf_label.configure(text=f"{val:.2f}")
                self.automation.set_yolo_conf_threshold(val)



            # Apply mode visibility
            self._on_mode_changed(self.detection_mode_var.get())

            self._check_enable_start()
        except Exception as e:
            print(f"Failed to load Pet Untrain config: {e}")

    def start_automation(self):
        if not self.main_window.set_running_tool("Pet Untrain"):
            return
        try:
            delay_ms = int(self.delay_var.get())
            if delay_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return

        mode = _MODE_MAP.get(self.detection_mode_var.get(), "ocr")
        self.automation.set_detection_mode(mode)

        # Validate OCR targets when OCR is active
        if mode in ("ocr", "hybrid"):
            ocr_targets = self._get_selected_ocr_targets()
            if not ocr_targets:
                messagebox.showwarning("Warning", "Please select at least one OCR target skill to search for.")
                self.main_window.clear_running_tool()
                return
            self.automation.set_ocr_targets(ocr_targets)

        # Validate YOLO targets when YOLO is active
        if mode in ("yolo", "hybrid"):
            model_path = self.yolo_model_var.get().strip()
            if not model_path:
                messagebox.showwarning("Warning", "Please select a YOLO26 ONNX model file.")
                self.main_window.clear_running_tool()
                return
            self.automation.set_yolo_model_path(model_path)
            self.automation.set_yolo_conf_threshold(self.yolo_conf_var.get())

            yolo_targets = self._get_selected_yolo_targets()
            if not yolo_targets:
                messagebox.showwarning("Warning", "Please select at least one YOLO target class.")
                self.main_window.clear_running_tool()
                return
            self.automation.set_yolo_targets(yolo_targets)

        self.automation.set_delay(delay_ms)

        if self.automation.start():
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status(f"Pet Untrain automation started (Mode: {mode.upper()})")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        self.automation.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
        self.main_window.update_status("Pet Untrain automation stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()

    def on_target_found(self, mode_or_target, target_name=None, conf_pct=0.0, bbox=None, cid=None):
        """Show popup notification when a target is found."""
        def show_popup():
            if mode_or_target == "yolo" or target_name is not None:
                cname = target_name if target_name else str(mode_or_target)
                conf_val = float(conf_pct)
                if 0 < conf_val <= 1.0:
                    conf_val *= 100.0
                popup_msg = f"[{cname}] [{conf_val:.2f}%]"
                messagebox.showinfo("YOLO Target Found", popup_msg)
            else:
                messagebox.showinfo("OCR Target Found", f"[{mode_or_target}]")

        if hasattr(self.main_window, "root") and self.main_window.root:
            self.main_window.root.after(0, show_popup)
        else:
            show_popup()