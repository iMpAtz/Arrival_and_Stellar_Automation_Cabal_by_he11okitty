# Pet Untrain tab — CustomTkinter rewrite

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import mouse
import json
import os
import sys
from data.pet_data import get_pet_ep39_steps, get_pet_untrain_steps, get_default_pet_delay, get_pet_ocr_options
from data.pet_data import PET_CONFIG_VERSION, normalize_pet_config
from automation.pet_automation import PetAutomation
from ui.theme import ACCENT as _A, section_header as _section_header

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
            on_needs_review=self.on_needs_review,
        )

        # Coordinate storage
        self.step_coords = {step: None for step in get_pet_untrain_steps() + get_pet_ep39_steps()}
        self.ocr_area = None
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
        ctk.CTkLabel(tf, text="1) Set Positions  •  2) Define Areas  •  3) Select OCR Targets  •  4) Start", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

        workflow_card = ctk.CTkFrame(scroll, corner_radius=8)
        workflow_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(workflow_card, "Pet Workflow", _A["teal"])
        self.workflow_mode_var = tk.StringVar(value="Standard")
        self.workflow_seg = ctk.CTkSegmentedButton(
            workflow_card, values=["Standard", "EP39"],
            variable=self.workflow_mode_var, command=self._on_workflow_changed,
        )
        self.workflow_seg.pack(fill=tk.X, padx=12, pady=8)
        self.workflow_hint = ctk.CTkLabel(
            workflow_card, text="", anchor="w", wraplength=500,
            font=ctk.CTkFont("Segoe UI", 11),
        )
        self.workflow_hint.pack(fill=tk.X, padx=12, pady=(0, 8))

        # Step coordinates
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Step Positions")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        self.step_coord_vars = {}
        self.step_rows = {}
        steps = get_pet_untrain_steps() + get_pet_ep39_steps()
        for step in steps:
            self.step_coord_vars[step] = tk.StringVar(value="Not set")
            row = ctk.CTkFrame(coord_body, fg_color="transparent")
            self.step_rows[step] = row
            row.pack(fill=tk.X, pady=(0, 4))
            step_label = {"EP39 Click 1": "EP39 Click 1 (Convert)",
                          "EP39 Click 2": "EP39 Click 2 (OK)",
                          "EP39 Click 3": "EP39 Click 3 (Cancel)"}.get(step, step)
            ctk.CTkLabel(row, text=f"{step_label}:", font=ctk.CTkFont("Segoe UI", 11, "bold"), anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(row, textvariable=self.step_coord_vars[step], font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w").pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)
            ctk.CTkButton(row, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=60, height=28, corner_radius=6, command=lambda s=step: self.set_step_position(s)).pack(side=tk.RIGHT)

        # OCR area
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

        # Area status labels
        area_status_row = ctk.CTkFrame(area_frame, fg_color="transparent")
        area_status_row.pack(fill=tk.X, pady=(4, 0))
        self.ocr_area_label = ctk.CTkLabel(area_status_row, text="OCR Area: Not set", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w")
        self.ocr_area_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

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

        # Delay
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
        self._on_workflow_changed(self.workflow_mode_var.get())

    # ══════════════════════════════════════════════════════════
    # WORKFLOW SELECTION
    # ══════════════════════════════════════════════════════════

    def _active_steps(self):
        return get_pet_ep39_steps() if self.workflow_mode_var.get() == "EP39" else get_pet_untrain_steps()


    def _on_workflow_changed(self, selected_mode):
        if self.automation.running:
            self.workflow_mode_var.set("EP39" if self.automation.workflow_mode == "ep39" else "Standard")
            return
        ep39 = selected_mode == "EP39"
        self.automation.set_workflow_mode("ep39" if ep39 else "standard")
        for row in self.step_rows.values():
            row.pack_forget()
        for step in self._active_steps():
            self.step_rows[step].pack(fill=tk.X, pady=(0, 4))
        self.workflow_hint.configure(text=(
            "EP39: Convert → read stat. Confirmed target → Cancel and stop. "
            "Clear non-target text (including new stats) → OK and repeat. "
            "Unclear OCR → retry, then stop with the popup open."
            if ep39 else "Standard: Five positions with detection before each click."
        ))
        self._check_enable_start()


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
                point = self.main_window.bot_core.wait_for_mouse_click(mouse)
                if point is None:
                    return
                x, y = point
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                def on_captured():
                    if success:
                        self.step_coords[step_name] = (rel_x, rel_y)
                        self.automation.set_step_coords(step_name, (rel_x, rel_y))
                        self.step_coord_vars[step_name].set(f"({rel_x}, {rel_y})")
                        self.main_window.update_status(f"'{step_name}' set at ({rel_x}, {rel_y})")
                        self._check_enable_start()
                    else:
                        messagebox.showerror("Error", "Failed to convert coordinates")

                self.main_window.post_ui(on_captured)
            except Exception as e:
                self.main_window.post_ui(lambda err=str(e): messagebox.showerror("Error", f"Failed to capture click: {err}"))
            finally:
                self.main_window.post_ui(lambda: self.main_window.root.config(cursor=""))

        self.main_window.bot_core.register_calibration(capture_click)

    def define_ocr_area(self):
        def area_callback(area):
            area = self.main_window.game_connector.screen_to_client_area(area)
            self.ocr_area = area
            self.automation.set_ocr_area(area)
            self.ocr_area_label.configure(text=f"OCR Area: {area}")
            self._check_enable_start()
            self.main_window.update_status(f"OCR area defined: {area}")

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()


    def _check_enable_start(self):
        """Require every active workflow position and an OCR region."""
        ready = self.ocr_area is not None and all(
            self.step_coords[step] is not None for step in self._active_steps()
        )
        self.btn_start.configure(state="normal" if ready else "disabled")

    def _get_selected_ocr_targets(self):
        targets = []
        for opt, var in self.ocr_check_vars.items():
            if var.get():
                targets.append(opt)
        return targets

    def save_config(self):
        config_data = {
            "schema_version": PET_CONFIG_VERSION,
            "workflow_mode": "ep39" if self.workflow_mode_var.get() == "EP39" else "standard",
            "step_coords": {k: list(v) if v else None for k, v in self.step_coords.items()},
            "ocr_area": self.ocr_area if self.ocr_area else None,
            "delay_ms": self.delay_var.get(),
            "selected_ocr_options": [opt for opt, var in self.ocr_check_vars.items() if var.get()],
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            from core.profiles import atomic_json
            atomic_json(path, config_data)
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
                data = normalize_pet_config(json.load(f))

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
                self.ocr_area = data["ocr_area"]
                self.automation.set_ocr_area(self.ocr_area)
                self.ocr_area_label.configure(text=f"OCR Area: {self.ocr_area}")

            # Delay
            if data.get("delay_ms"):
                self.delay_var.set(str(data["delay_ms"]))

            # OCR options
            if data.get("selected_ocr_options"):
                for opt in data["selected_ocr_options"]:
                    if opt in self.ocr_check_vars:
                        self.ocr_check_vars[opt].set(True)

            # Missing workflow_mode keeps legacy configurations on Standard.
            self.workflow_mode_var.set("EP39" if data.get("workflow_mode") == "ep39" else "Standard")
            self._on_workflow_changed(self.workflow_mode_var.get())

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

        ocr_targets = self._get_selected_ocr_targets()
        if not ocr_targets:
            messagebox.showwarning("Warning", "Please select at least one OCR target skill to search for.")
            self.main_window.clear_running_tool()
            return
        self.automation.set_ocr_targets(ocr_targets)

        self.automation.set_workflow_mode("ep39" if self.workflow_mode_var.get() == "EP39" else "standard")
        self.automation.set_delay(delay_ms)

        if self.automation.start():
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status("Pet Untrain automation started (OCR)")
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

    def on_needs_review(self, issue, raw_text):
        """Leave the game's popup untouched and warn on the Tk UI thread."""
        def show_popup():
            self._check_enable_start()
            self.btn_stop.configure(state="disabled")
            self.main_window.clear_running_tool()
            messagebox.showwarning(
                "EP39: Needs Review",
                "อ่านชื่อ stat ไม่ชัดหลังลองอ่าน 3 ครั้ง บอตหยุดแล้ว\n"
                "ยังไม่ได้กด OK หรือ Cancel และค้าง popup เกมไว้\n"
                "โปรดตรวจ stat และจัดหน้าจอเกมให้พร้อมก่อนกด START อีกครั้ง\n\n"
                f"เหตุผล: {issue}\nOCR: {raw_text or '(ว่าง)'}",
            )
        self.main_window.post_run_ui(show_popup)

    def on_target_found(self, mode_or_target, target_name=None):
        """Show popup notification when a target is found."""
        def show_popup():
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.main_window.clear_running_tool()
            messagebox.showinfo("OCR Target Found", f"[{target_name or mode_or_target}]")

        if hasattr(self.main_window, "root") and self.main_window.root:
            self.main_window.post_run_ui(show_popup)
        else:
            show_popup()
