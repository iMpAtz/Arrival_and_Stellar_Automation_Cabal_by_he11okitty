"""Diagnostics, calibration preview, offline replay and run controls."""
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw
from core.replay import analyze_image
from core.paths import writable_root
from core.profiles import export_profile, import_profile
from ui.theme import ACCENT, section_header, card


class WorkbenchTab:
    def __init__(self, parent, main_window):
        self.main = main_window
        self.image = None
        self._busy = False
        panel = ctk.CTkScrollableFrame(parent)
        panel.pack(fill="both", expand=True)
        intro = card(panel, fg_color=("#dbeafe", "#172b43"), border_color=ACCENT["primary"])
        intro.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(intro, text="🧭  WORKBENCH", anchor="w",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=ACCENT["text"]).pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(intro, text="Connect → calibrate → preview → run",
                     anchor="w", text_color=ACCENT["text_dim"],
                     font=ctk.CTkFont("Segoe UI", 11)).pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(intro, text="The buttons below inspect frames without sending game input."
                     " Use Dry run for a complete no-click rehearsal.",
                     anchor="w", justify="left", wraplength=560,
                     text_color=ACCENT["text_dim"]).pack(fill="x", padx=14, pady=(0, 12))
        section_header(panel, "Safety limits")
        self.dry = tk.BooleanVar(value=False)
        safety = card(panel)
        safety.pack(fill="x", pady=(0, 10))
        ctk.CTkCheckBox(safety, text="Dry run — suppress all mouse input", variable=self.dry, command=self.configure_run).pack(anchor="w", padx=12, pady=(10, 4))
        row = ctk.CTkFrame(safety, fg_color="transparent")
        row.pack(fill="x", pady=8)
        self.minutes = tk.StringVar(value="30")
        self.actions = tk.StringVar(value="10000")
        for label, var in (("Max minutes", self.minutes), ("Max actions", self.actions)):
            ctk.CTkLabel(row, text=label, text_color=ACCENT["text_dim"]).pack(side="left", padx=4)
            ctk.CTkEntry(row, textvariable=var, width=75).pack(side="left")
        ctk.CTkButton(row, text="Apply limits", width=100, command=self.configure_run).pack(side="left", padx=4)
        self.evidence = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(safety, text="Save one screenshot when a reroll needs review", variable=self.evidence,
                       command=self.configure_run).pack(anchor="w", padx=12, pady=(0, 10))
        section_header(panel, "Game connection")
        connection = card(panel)
        connection.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(connection, text="Select the intended visible D3D client. The selected window is used for capture and input.",
                     wraplength=580, justify="left", text_color=ACCENT["text_dim"]).pack(fill="x", padx=12, pady=(10, 2))
        self.windows = {}
        self.window_choice = ctk.CTkComboBox(
            connection,
            values=["Refresh to select a game window"],
            width=520,
            fg_color=ACCENT["input"],
            button_color=ACCENT["primary"],
            button_hover_color="#1a5a8e",
            dropdown_fg_color=ACCENT["surface2"],
            dropdown_hover_color=ACCENT["primary"],
            dropdown_text_color=ACCENT["text"],
            text_color=ACCENT["text"],
        )
        self.window_choice.pack(fill="x", padx=12, pady=6)
        row = ctk.CTkFrame(connection, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(row, text="Refresh windows", command=self.refresh_windows).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Attach selected", command=self.attach).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Run diagnostics", command=self.diagnostics).pack(side="left", padx=4)
        section_header(panel, "Offline observation")
        observation = card(panel)
        observation.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(observation, text="Choose a tool and inspect a live crop or saved screenshot. No automation is started.",
                     wraplength=580, justify="left", text_color=ACCENT["text_dim"]).pack(fill="x", padx=12, pady=(10, 4))
        self.tool = ctk.CTkComboBox(
            observation,
            values=["Arrival", "Stellar", "Pet OCR", "Pet EP39"],
            width=220,
            fg_color=ACCENT["input"],
            button_color=ACCENT["primary"],
            button_hover_color="#1a5a8e",
            dropdown_fg_color=ACCENT["surface2"],
            dropdown_hover_color=ACCENT["primary"],
            dropdown_text_color=ACCENT["text"],
            text_color=ACCENT["text"],
        )
        self.tool.set("Arrival")
        self.tool.pack(anchor="w", padx=12, pady=6)
        row = ctk.CTkFrame(observation, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(row, text="Preview game + regions", command=self.preview).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Read live crop", command=self.read_live).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Open saved crop", command=self.open_crop).pack(side="left", padx=4)
        self.preview_label = ctk.CTkLabel(observation, text="Configure the tool's region and targets, then preview here.",
                                         wraplength=580, justify="left")
        self.preview_label.pack(fill="x", padx=12, pady=8)
        self.output = ctk.CTkTextbox(panel, height=200)
        self.output.pack(fill="x", pady=8)
        self.output.configure(state="disabled", font=("Consolas", 10))
        section_header(panel, "Profiles and evidence")
        row = ctk.CTkFrame(panel, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Save displayed image", command=self.save_image).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Export saved settings", command=self.export).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Import profile", command=self.import_saved).pack(side="left", padx=4)
        ctk.CTkLabel(panel, text="Profiles contain settings last saved in each tab and copies of referenced assets.\nImport takes effect after restarting the app. Previous JSON files get .bak backups.", wraplength=550).pack(pady=8)
        self.diagnostics()

    def show(self, value):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", json.dumps(value, indent=2, ensure_ascii=False) if not isinstance(value, str) else value)
        self.output.configure(state="disabled")

    def idle(self):
        if self.main.bot_core.is_busy() or self.main.image_clicker_tab.automation.running or self._busy:
            self.show("Stop automation and wait for pending observations before changing settings or inspecting.")
            return False
        return True

    def configure_run(self):
        core = self.main.bot_core
        if not self.idle():
            self.dry.set(core.dry_run)
            return
        try:
            minutes, actions = int(self.minutes.get()), int(self.actions.get())
            if minutes <= 0 or actions <= 0:
                raise ValueError
        except ValueError:
            self.show("Limits must be positive whole numbers.")
            self.dry.set(core.dry_run)
            return
        core.dry_run = self.dry.get()
        core.max_seconds, core.max_actions = minutes*60, actions
        core.save_evidence = self.evidence.get()
        self.show({"dry_run": core.dry_run, "max_minutes": minutes, "max_actions": actions})

    def refresh_windows(self):
        self.windows = {f"{title} [{hwnd}]": hwnd for hwnd, title in self.main.game_connector.available_windows()}
        values = list(self.windows) or ["No game windows found"]
        self.window_choice.configure(values=values)
        self.window_choice.set(values[0])

    def attach(self):
        if self.idle():
            hwnd = self.windows.get(self.window_choice.get())
            connected = bool(hwnd and self.main.game_connector.attach_window(hwnd))
            self.show("Connected" if connected else "Select an available game window")
            from ui.theme import ACCENT
            color = ACCENT["success"] if connected else ACCENT["danger"]
            for prefix in ("", "mini_"):
                indicator = getattr(self.main, prefix+"connection_indicator", None)
                label = getattr(self.main, prefix+"connection_text", None)
                if indicator is not None:
                    indicator.configure(text_color=color)
                if label is not None:
                    label.configure(text="Connected" if connected else "Disconnected", text_color=color)

    def diagnostics(self):
        self.show({"ocr": self.main.ocr_engine.diagnostics(),
                   "game_connected": self.main.game_connector.is_connected(),
                   "ocr_metrics": dict(self.main.ocr_engine.metrics),
                   "reports": str(writable_root()/"summaries")})

    def selected(self):
        name = self.tool.get()
        tab = {"Arrival": self.main.arrival_tab, "Stellar": self.main.stellar_tab,
               "Pet OCR": self.main.pet_tab, "Pet EP39": self.main.pet_tab}[name]
        auto = tab.automation
        area = getattr(auto, "ocr_area", None) or auto.area
        return name, tab, area

    def display_image(self, image):
        self.image = image.copy()
        thumb = image.copy()
        thumb.thumbnail((530, 260))
        self._photo = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
        self.preview_label.configure(image=self._photo, text="")

    def preview(self):
        if not self.idle():
            return
        name, tab, area = self.selected()
        connector = self.main.game_connector
        image = connector.take_screenshot()
        rect = connector.get_window_rect()
        region = connector.resolve_area(area)
        if image is None or rect is None:
            self.show("Game capture unavailable")
            return
        draw = ImageDraw.Draw(image)
        if region:
            x, y, w, h = region
            draw.rectangle((x-rect.left, y-rect.top, x-rect.left+w, y-rect.top+h), outline="red", width=3)
        for key, point in vars(tab.automation).items():
            if key.endswith("_coords") and isinstance(point, (list, tuple)) and len(point) == 2:
                x, y = point
                draw.ellipse((x-5, y-5, x+5, y+5), fill="yellow")
                draw.text((x+7, y), key, fill="yellow")
        for key, point in getattr(tab.automation, "coords", {}).items():
            if name.startswith("Pet") and key.startswith("ep39_") != (name == "Pet EP39"):
                continue
            if point:
                x, y = point
                draw.ellipse((x-5, y-5, x+5, y+5), fill="yellow")
                draw.text((x+7, y), key, fill="yellow")
        self.display_image(image)
        self.show("Red: detection region. Yellow: click targets. This annotated preview is not an OCR crop.")

    def read_live(self):
        if not self.idle():
            return
        _, _, area = self.selected()
        if not area:
            self.show("Define a detection region in the tool's tab first")
            return
        image = self.main.game_connector.take_screenshot(area)
        if image is None:
            self.show("Capture unavailable; check the game window and calibration")
            return
        self.inspect(image)

    def open_crop(self):
        if not self.idle():
            return
        path = filedialog.askopenfilename(filetypes=[("Screenshots", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            try:
                with Image.open(path) as image:
                    self.inspect(image.convert("RGB"))
            except Exception as exc:
                self.show(str(exc))

    def inspect(self, image):
        name, tab, _ = self.selected()
        self.display_image(image)
        constraints = []
        if name == "Stellar":
            try:
                constraints = [(c["name"], int(str(c["min_value"]).lstrip("+") or 0)) for c in tab.get_selected_option_constraints()]
            except ValueError:
                self.show("Minimums must be whole numbers")
                return
        elif name == "Arrival":
            import re
            from data.arrival_data import get_base_stat_name
            for stat, value in ((tab.off_stat, tab.off_var), (tab.off_stat2, tab.off_var2),
                                (tab.off_stat3, tab.off_var3), (tab.def_stat, tab.def_var), (tab.def_stat2, tab.def_var2)):
                digits = re.search(r"\d+", value.get().replace(",", ""))
                if stat.get() and digits:
                    constraints.append((get_base_stat_name(stat.get()), int(digits[0])))
        pet_settings = None
        if name.startswith("Pet"):
            pet_settings = (tab._get_selected_ocr_targets(), "ep39" if name == "Pet EP39" else "standard")
        self._busy = True
        self.show("Observing… no input will be sent.")
        def worker():
            try:
                if pet_settings:
                    from automation.pet_automation import PetAutomation
                    class SavedFrame:
                        def take_screenshot(self, area=None):
                            return image
                    auto = PetAutomation(SavedFrame(), self.main.ocr_engine)
                    auto.set_area((0, 0, *image.size))
                    auto.set_ocr_targets(pet_settings[0])
                    auto.set_workflow_mode(pet_settings[1])
                    hit, normalized = auto._ocr_match_pet_targets(require_targets=False)
                    decision = "unknown" if not auto._last_ocr_valid else "matched" if hit else "absent"
                    if auto._last_ocr_valid and not pet_settings[0]:
                        decision = "no_targets"
                    result = {
                        "workflow": pet_settings[1], "decision": decision,
                        "text": auto._last_ocr_raw, "normalized_text": normalized,
                        "targets_selected": bool(pet_settings[0]),
                        "issue": auto._last_ocr_issue,
                    }
                    if not auto._last_ocr_raw.strip():
                        result["crop_size"] = list(image.size)
                        result["ocr_diagnostics"] = self.main.ocr_engine.diagnostics()
                    if name == "Pet EP39":
                        result["next_step"] = {
                            "matched": "Confirm OCR again before Cancel and target_found",
                            "absent": "OK, then Convert for the next roll",
                            "unknown": "Retry OCR; if still unclear, needs_review with popup left open",
                            "no_targets": "Text read successfully. Select target skills in the Pet tab before starting.",
                        }[decision]
                else:
                    result = analyze_image(image, name, self.main.ocr_engine, constraints)
            except Exception as exc:
                result = {"error": str(exc)}
            def done():
                self._busy = False
                self.show(result)
            self.main.post_ui(done)
        threading.Thread(target=worker, name="offline-observation", daemon=True).start()

    def save_image(self):
        if self.image is not None:
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if path:
                self.image.save(path)

    def export(self):
        if not self.idle():
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Profile", "*.json")])
        if path:
            try:
                export_profile(writable_root()/"data", path)
                self.show("Exported saved settings and assets. Keep the JSON and its assets folder together.")
            except Exception as exc:
                self.show(str(exc))

    def import_saved(self):
        if not self.idle():
            return
        path = filedialog.askopenfilename(filetypes=[("Profile", "*.json")])
        if path:
            try:
                names = import_profile(path, writable_root()/"data")
                self.show("Imported: " + ", ".join(names) + ". Restart the app to load these settings.")
            except Exception as exc:
                self.show(str(exc))
