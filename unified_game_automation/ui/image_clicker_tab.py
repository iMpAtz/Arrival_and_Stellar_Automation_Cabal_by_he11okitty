# Image Clicker tab — CustomTkinter rewrite
# Allows importing template images, defining search areas, and running detection
#
# This tab is independent from the shared BotCore mutual-exclusion system.
# The Image Clicker runs on its own thread and only stops on explicit user
# action (Stop button, hotkey, or ESC emergency stop).

import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import keyboard

from core.area_selector import AreaSelector
from data.image_clicker_data import (
    CLICK_TYPES,
    SUPPORTED_FILETYPES,
    get_default_image_config,
    get_default_search_area,
    import_image_file,
    load_config,
    save_config,
)
from automation.image_clicker_automation import ImageClickerAutomation

_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "warning": "#e8a317", "info": "#17a2b8", "purple": "#7c3aed",
    "muted": "#888888", "surface2": "#333333",
}


def _section_header(parent, title, color=None):
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color="#ffffff", anchor="w").pack(side=tk.LEFT, padx=12, pady=4)


class ImageClickerTab:
    def __init__(self, parent_frame, main_window):
        """Initialize the Image Clicker tab."""
        self.parent_frame = parent_frame
        self.main_window = main_window

        # Automation engine — fully self-contained, no BotCore dependency
        self.automation = ImageClickerAutomation(
            main_window.game_connector,
            status_callback=main_window.update_status,
        )

        # Data model
        self._image_configs = []    # list[dict]
        self._search_areas = []     # list[dict]

        self._running = False
        self._selected_image_index = None

        # Hotkey
        self._hotkey_name = "F6"
        self._hotkey_hook = None

        # Load persisted config
        self._load_config()

        # Build UI
        self.create_ui()

        # Populate lists from loaded config
        self._refresh_area_listbox()
        self._refresh_image_tree()

        # Register default hotkey
        self._register_hotkey()

    # ══════════════════════════════════════════════════════════
    #  UI CREATION
    # ══════════════════════════════════════════════════════════

    def create_ui(self):
        scroll = ctk.CTkScrollableFrame(self.parent_frame, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # 1) Intro
        self._create_intro_card(scroll)
        # 2) Search Areas
        self._create_search_areas_card(scroll)
        # 3) Image List
        self._create_image_list_card(scroll)
        # 4) Image Config
        self._create_image_config_card(scroll)
        # 5) Controls
        self._create_control_buttons(scroll)

    # ────────────────────────────────────────────────────────
    # 1) Intro
    # ────────────────────────────────────────────────────────
    def _create_intro_card(self, parent):
        intro = ctk.CTkFrame(parent, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        inner = ctk.CTkFrame(intro, fg_color="transparent")
        inner.pack(fill=tk.X, padx=12, pady=8)
        ctk.CTkLabel(inner, text="🖱️", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(tf, text="IMAGE CLICKER — Automated Image Detection & Click", font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(tf, text="Import template images • Define search areas • Auto-detect & click", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

    # ────────────────────────────────────────────────────────
    # 2) Search Areas
    # ────────────────────────────────────────────────────────
    def _create_search_areas_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.pack(fill=tk.X, pady=(0, 8))
        _section_header(card, "📐  Search Areas", _A["warning"])
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill=tk.X, padx=12, pady=8)

        # Listbox (tk — no CTk equivalent for Listbox)
        list_frame = ctk.CTkFrame(body, fg_color="transparent")
        list_frame.pack(fill=tk.X)

        self.area_listbox = tk.Listbox(
            list_frame, height=4, font=("Segoe UI", 10), selectmode=tk.SINGLE,
            bg="#2b2b2b", fg="#e0e0e0", selectbackground=_A["primary"],
            selectforeground="#ffffff", relief="flat", bd=0,
            highlightthickness=1, highlightcolor=_A["primary"],
            highlightbackground="#404040",
        )
        self.area_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        area_sb = ctk.CTkScrollbar(list_frame, command=self.area_listbox.yview)
        area_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.area_listbox.configure(yscrollcommand=area_sb.set)

        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(6, 0))
        ctk.CTkButton(btn_frame, text="➕ Add Area", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=100, height=30, corner_radius=6, command=self._add_search_area).pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkButton(btn_frame, text="🗑️ Remove", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["danger"], hover_color="#c9302c", width=100, height=30, corner_radius=6, command=self._remove_search_area).pack(side=tk.LEFT)

    # ────────────────────────────────────────────────────────
    # 3) Image List
    # ────────────────────────────────────────────────────────
    def _create_image_list_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.pack(fill=tk.X, pady=(0, 8))
        _section_header(card, "🖼️  Template Images", _A["primary"])
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill=tk.X, padx=12, pady=8)

        # Treeview (ttk — no CTk table widget)
        tree_frame = ctk.CTkFrame(body, fg_color="transparent")
        tree_frame.pack(fill=tk.X)

        columns = ("enabled", "threshold", "area", "click_type")
        self.image_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=5, selectmode="browse",
        )
        self.image_tree.heading("enabled", text="On")
        self.image_tree.heading("threshold", text="Threshold")
        self.image_tree.heading("area", text="Search Area")
        self.image_tree.heading("click_type", text="Click Type")

        self.image_tree.column("enabled", width=30, anchor="center")
        self.image_tree.column("threshold", width=65, anchor="center")
        self.image_tree.column("area", width=120, anchor="w")
        self.image_tree.column("click_type", width=90, anchor="w")

        tree_sb = ctk.CTkScrollbar(tree_frame, command=self.image_tree.yview)
        self.image_tree.configure(yscrollcommand=tree_sb.set)

        self.image_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.image_tree.bind("<<TreeviewSelect>>", self._on_image_selected)

        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(6, 0))
        ctk.CTkButton(btn_frame, text="📥 Import Image", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["success"], hover_color="#258a5e", width=130, height=30, corner_radius=6, command=self._import_image).pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkButton(btn_frame, text="🗑️ Remove Image", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["danger"], hover_color="#c9302c", width=130, height=30, corner_radius=6, command=self._remove_image).pack(side=tk.LEFT)

    # ────────────────────────────────────────────────────────
    # 4) Image Config
    # ────────────────────────────────────────────────────────
    def _create_image_config_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.pack(fill=tk.X, pady=(0, 8))
        _section_header(card, "⚙️  Selected Image Settings", _A["info"])
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill=tk.X, padx=12, pady=8)
        self._config_body = body

        # Name
        self.cfg_name_var = tk.StringVar()
        self._cfg_row_entry(body, "Name:", self.cfg_name_var, 180)

        # Enabled
        self.cfg_enabled_var = tk.BooleanVar(value=True)
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(row, text="Enabled:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        ctk.CTkCheckBox(row, text="", variable=self.cfg_enabled_var, width=24, checkbox_width=20, checkbox_height=20).pack(side=tk.LEFT)

        # Threshold
        self.cfg_threshold_var = tk.StringVar(value="0.85")
        r_th = self._cfg_row_entry(body, "Threshold:", self.cfg_threshold_var, 80)
        ctk.CTkLabel(r_th, text="(0.0 – 1.0)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT, padx=(8, 0))

        # Search Area
        row_area = ctk.CTkFrame(body, fg_color="transparent")
        row_area.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(row_area, text="Search Area:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        self.cfg_area_var = tk.StringVar(value="Full Screen")
        self.cfg_area_combo = ttk.Combobox(row_area, textvariable=self.cfg_area_var, state="readonly", width=20, font=("Segoe UI", 10))
        self.cfg_area_combo.pack(side=tk.LEFT, padx=(6, 0))
        self._refresh_area_combo()

        # Click Type
        row_click = ctk.CTkFrame(body, fg_color="transparent")
        row_click.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(row_click, text="Click Type:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        self.cfg_click_var = tk.StringVar(value="Left Click")
        ttk.Combobox(row_click, textvariable=self.cfg_click_var, values=CLICK_TYPES, state="readonly", width=15, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(6, 0))

        # Offset X / Y
        row_off = ctk.CTkFrame(body, fg_color="transparent")
        row_off.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(row_off, text="Offset X:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        self.cfg_offset_x_var = tk.StringVar(value="0")
        ctk.CTkEntry(row_off, textvariable=self.cfg_offset_x_var, width=60, height=28, font=ctk.CTkFont("Segoe UI", 11)).pack(side=tk.LEFT, padx=(6, 10))
        ctk.CTkLabel(row_off, text="Y:", font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.cfg_offset_y_var = tk.StringVar(value="0")
        ctk.CTkEntry(row_off, textvariable=self.cfg_offset_y_var, width=60, height=28, font=ctk.CTkFont("Segoe UI", 11)).pack(side=tk.LEFT)

        # Cooldown
        self.cfg_cooldown_var = tk.StringVar(value="1000")
        r_cd = self._cfg_row_entry(body, "Cooldown (ms):", self.cfg_cooldown_var, 80)

        # Apply button
        apply_frame = ctk.CTkFrame(body, fg_color="transparent")
        apply_frame.pack(fill=tk.X, pady=(8, 0))
        ctk.CTkButton(apply_frame, text="💾 Apply Changes", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["success"], hover_color="#258a5e", width=140, height=32, corner_radius=6, command=self._apply_image_config).pack(side=tk.RIGHT)

    def _cfg_row_entry(self, parent, label, var, width):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        ctk.CTkEntry(row, textvariable=var, width=width, height=28, font=ctk.CTkFont("Segoe UI", 11)).pack(side=tk.LEFT, padx=(6, 0))
        return row

    # ────────────────────────────────────────────────────────
    # 5) Controls
    # ────────────────────────────────────────────────────────
    def _create_control_buttons(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.pack(fill=tk.X, pady=(0, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill=tk.X, padx=12, pady=8)

        # Scan interval
        intv = ctk.CTkFrame(body, fg_color="transparent")
        intv.pack(fill=tk.X, pady=(0, 6))
        ctk.CTkLabel(intv, text="Scan Interval (ms):", font=ctk.CTkFont("Segoe UI", 11, "bold"), anchor="w").pack(side=tk.LEFT)
        self.scan_interval_var = tk.StringVar(value="200")
        ctk.CTkEntry(intv, textvariable=self.scan_interval_var, width=80, height=28, font=ctk.CTkFont("Segoe UI", 11)).pack(side=tk.LEFT, padx=(6, 8))
        ctk.CTkLabel(intv, text="(delay between scan cycles)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # Hotkey
        hk = ctk.CTkFrame(body, fg_color="transparent")
        hk.pack(fill=tk.X, pady=(0, 8))
        ctk.CTkLabel(hk, text="Toggle Hotkey:", font=ctk.CTkFont("Segoe UI", 11, "bold"), anchor="w").pack(side=tk.LEFT)
        self.hotkey_var = tk.StringVar(value=self._hotkey_name)
        self.hotkey_entry = ctk.CTkEntry(hk, textvariable=self.hotkey_var, width=80, height=28, font=ctk.CTkFont("Segoe UI", 11))
        self.hotkey_entry.pack(side=tk.LEFT, padx=(6, 6))
        ctk.CTkButton(hk, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=50, height=28, corner_radius=6, command=self._update_hotkey).pack(side=tk.LEFT, padx=(0, 6))
        self.hotkey_status_var = tk.StringVar(value=f"(Press {self._hotkey_name} to toggle)")
        ctk.CTkLabel(hk, textvariable=self.hotkey_status_var, font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # Buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack()

        self.btn_start = ctk.CTkButton(btn_row, text=f"▶️ START ({self._hotkey_name})", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["success"], hover_color="#258a5e", width=140, height=38, corner_radius=8, command=self.start_automation)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = ctk.CTkButton(btn_row, text=f"⏹️ STOP ({self._hotkey_name})", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["danger"], hover_color="#c9302c", width=140, height=38, corner_radius=8, state="disabled", command=self.stop_automation)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_save_config = ctk.CTkButton(btn_row, text="💾 Save Config", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=130, height=38, corner_radius=8, command=self._on_user_save_config)
        self.btn_save_config.pack(side=tk.LEFT)

    def _on_user_save_config(self):
        """Explicitly save configuration and inform user."""
        self._save_config()
        if hasattr(self.main_window, 'update_status'):
            self.main_window.update_status("Image Clicker config saved successfully!")
        messagebox.showinfo("Config Saved", "Image Clicker configuration has been saved.")

    # ══════════════════════════════════════════════════════════
    #  HOTKEY — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def _register_hotkey(self):
        """Register the toggle hotkey using the keyboard module."""
        self._unregister_hotkey()
        try:
            self._hotkey_hook = keyboard.add_hotkey(
                self._hotkey_name, self._toggle_from_hotkey, suppress=False
            )
        except Exception as e:
            self.main_window.update_status(f"Failed to register hotkey '{self._hotkey_name}': {e}")

    def _unregister_hotkey(self):
        """Remove the previously registered hotkey."""
        if self._hotkey_hook is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_hook)
            except Exception:
                pass
            self._hotkey_hook = None

    def _update_hotkey(self):
        """Update hotkey from the entry field."""
        new_key = self.hotkey_var.get().strip()
        if not new_key:
            messagebox.showwarning("Warning", "Please enter a hotkey (e.g. F6, F7, ctrl+shift+i)")
            return
        self._hotkey_name = new_key
        self._register_hotkey()
        self.hotkey_status_var.set(f"(Press {self._hotkey_name} to toggle)")
        self.btn_start.configure(text=f"▶️ START ({self._hotkey_name})")
        self.btn_stop.configure(text=f"⏹️ STOP ({self._hotkey_name})")
        self.main_window.update_status(f"Image Clicker hotkey set to: {self._hotkey_name}")

    def _toggle_from_hotkey(self):
        """Called from the keyboard hotkey — schedule on main thread."""
        self.main_window.root.after(0, self._toggle)

    def _toggle(self):
        """Toggle start/stop."""
        if self._running:
            self.stop_automation()
        else:
            self.start_automation()

    # ══════════════════════════════════════════════════════════
    #  SEARCH AREA ACTIONS — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def _add_search_area(self):
        if self._running:
            return

        name_win = ctk.CTkToplevel(self.main_window.root)
        name_win.title("New Search Area")
        name_win.geometry("300x140")
        name_win.attributes("-topmost", True)
        name_win.resizable(False, False)

        ctk.CTkLabel(name_win, text="Area name:", font=ctk.CTkFont("Segoe UI", 12)).pack(pady=(16, 6))
        name_var = tk.StringVar(value=f"Area {len(self._search_areas)}")
        name_entry = ctk.CTkEntry(name_win, textvariable=name_var, width=220, font=ctk.CTkFont("Segoe UI", 12))
        name_entry.pack()
        name_entry.focus_set()

        def on_ok(_event=None):
            area_name = name_var.get().strip()
            if not area_name:
                messagebox.showwarning("Warning", "Please enter a name.", parent=name_win)
                return
            for a in self._search_areas:
                if a["name"] == area_name:
                    messagebox.showwarning("Warning", f"'{area_name}' already exists.", parent=name_win)
                    return
            name_win.destroy()
            self._select_area_for_name(area_name)

        ctk.CTkButton(name_win, text="OK & Select Area", command=on_ok, font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=140, height=32, corner_radius=6).pack(pady=(12, 0))
        name_win.bind("<Return>", on_ok)

    def _select_area_for_name(self, area_name):
        # Clear BotCore stop_event so the area selector overlay works
        self.main_window.bot_core.start()

        def area_callback(area):
            left, top, width, height = area
            new_area = {
                "name": area_name,
                "x": left,
                "y": top,
                "width": width,
                "height": height,
                "is_full_screen": False,
            }
            self._search_areas.append(new_area)
            self._refresh_area_listbox()
            self._refresh_area_combo()
            self._save_config()
            self.main_window.update_status(f"Search area '{area_name}' added: {area}")

        selector = AreaSelector(self.main_window.root, area_callback)
        selector.select_area()

    def _remove_search_area(self):
        sel = self.area_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select an area to remove.")
            return
        idx = sel[0]
        area = self._search_areas[idx]
        if area.get("is_full_screen") or area.get("name") == "Full Screen":
            messagebox.showwarning("Warning", "'Full Screen' cannot be removed.")
            return
        name = area.get("name", "")
        self._search_areas.pop(idx)
        self._refresh_area_listbox()
        self._refresh_area_combo()
        self._save_config()
        self.main_window.update_status(f"Search area '{name}' removed")

    def _refresh_area_listbox(self):
        self.area_listbox.delete(0, tk.END)
        for a in self._search_areas:
            name = a.get("name", "?")
            if a.get("is_full_screen"):
                self.area_listbox.insert(tk.END, f"{name}  (entire game window)")
            else:
                x, y, w, h = a.get("x", 0), a.get("y", 0), a.get("width", 0), a.get("height", 0)
                self.area_listbox.insert(tk.END, f"{name}  →  ({x}, {y}, {w}×{h})")

    def _refresh_area_combo(self):
        names = [a.get("name", "?") for a in self._search_areas]
        self.cfg_area_combo["values"] = names
        if names and self.cfg_area_var.get() not in names:
            self.cfg_area_var.set(names[0])

    # ══════════════════════════════════════════════════════════
    #  IMAGE LIST ACTIONS — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def _import_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Template Image",
            filetypes=SUPPORTED_FILETYPES,
        )
        if not file_path:
            return

        dest_path = import_image_file(file_path)
        if not dest_path:
            messagebox.showerror("Error", f"Failed to import image:\n{file_path}")
            return

        cfg = get_default_image_config()
        cfg["name"] = os.path.splitext(os.path.basename(dest_path))[0]
        cfg["file_path"] = dest_path
        self._image_configs.append(cfg)

        self._refresh_image_tree()
        self._save_config()
        self.main_window.update_status(f"Imported image: {cfg['name']}")

    def _remove_image(self):
        sel = self.image_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select an image to remove.")
            return
        item = sel[0]
        idx = self.image_tree.index(item)
        if 0 <= idx < len(self._image_configs):
            name = self._image_configs[idx].get("name", "")
            self._image_configs.pop(idx)
            self._refresh_image_tree()
            self._selected_image_index = None
            self._save_config()
            self.main_window.update_status(f"Removed image: {name}")

    def _on_image_selected(self, _event=None):
        sel = self.image_tree.selection()
        if not sel:
            return
        idx = self.image_tree.index(sel[0])
        if idx < 0 or idx >= len(self._image_configs):
            return
        self._selected_image_index = idx
        cfg = self._image_configs[idx]

        self.cfg_name_var.set(cfg.get("name", ""))
        self.cfg_enabled_var.set(cfg.get("enabled", True))
        self.cfg_threshold_var.set(str(cfg.get("threshold", 0.85)))
        self.cfg_area_var.set(cfg.get("search_area_name", "Full Screen"))
        self.cfg_click_var.set(cfg.get("click_type", "Left Click"))
        self.cfg_offset_x_var.set(str(cfg.get("offset_x", 0)))
        self.cfg_offset_y_var.set(str(cfg.get("offset_y", 0)))
        self.cfg_cooldown_var.set(str(cfg.get("cooldown_ms", 1000)))

    def _apply_image_config(self):
        idx = self._selected_image_index
        if idx is None or idx < 0 or idx >= len(self._image_configs):
            messagebox.showinfo("Info", "Select an image first.")
            return

        try:
            threshold = float(self.cfg_threshold_var.get())
            if not (0.0 <= threshold <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Threshold must be a number between 0.0 and 1.0")
            return

        try:
            offset_x = int(self.cfg_offset_x_var.get())
            offset_y = int(self.cfg_offset_y_var.get())
        except ValueError:
            messagebox.showerror("Error", "Offsets must be integers")
            return

        try:
            cooldown = int(self.cfg_cooldown_var.get())
            if cooldown < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Cooldown must be a positive integer (ms)")
            return

        cfg = self._image_configs[idx]
        cfg["name"] = self.cfg_name_var.get().strip() or cfg["name"]
        cfg["enabled"] = self.cfg_enabled_var.get()
        cfg["threshold"] = threshold
        cfg["search_area_name"] = self.cfg_area_var.get()
        cfg["click_type"] = self.cfg_click_var.get()
        cfg["offset_x"] = offset_x
        cfg["offset_y"] = offset_y
        cfg["cooldown_ms"] = cooldown

        self._refresh_image_tree()
        self._save_config()
        self.main_window.update_status(f"Updated config for '{cfg['name']}'")

    def _refresh_image_tree(self):
        self.image_tree.delete(*self.image_tree.get_children())
        for cfg in self._image_configs:
            enabled_str = "✅" if cfg.get("enabled", True) else "❌"
            self.image_tree.insert(
                "", "end",
                text=cfg.get("name", ""),
                values=(
                    enabled_str,
                    f"{cfg.get('threshold', 0.85):.2f}",
                    cfg.get("search_area_name", "Full Screen"),
                    cfg.get("click_type", "Left Click"),
                ),
            )
        self.image_tree["displaycolumns"] = ("enabled", "threshold", "area", "click_type")
        self.image_tree.heading("#0", text="Name")
        self.image_tree.column("#0", width=120, anchor="w")

    # ══════════════════════════════════════════════════════════
    #  START / STOP — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def start_automation(self):
        if self._running:
            return

        try:
            interval = int(self.scan_interval_var.get())
            if interval < 50:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Scan interval must be ≥ 50 ms")
            return

        self.automation.set_image_configs(self._image_configs)
        self.automation.set_search_areas(self._search_areas)
        self.automation.set_scan_interval(interval)

        if self.automation.start():
            self._running = True
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")

    def stop_automation(self):
        self.automation.stop()
        self._running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.update_status("Image Clicker stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self._running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    def cleanup(self):
        """Called when the application is closing."""
        self._unregister_hotkey()
        if self._running:
            self.automation.stop()

    # ══════════════════════════════════════════════════════════
    #  CONFIG PERSISTENCE — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def _save_config(self):
        data = {
            "images": self._image_configs,
            "search_areas": self._search_areas,
        }
        save_config(data)

    def _load_config(self):
        data = load_config()
        self._image_configs = data.get("images", [])
        self._search_areas = data.get("search_areas", [get_default_search_area("Full Screen")])
        names = [a.get("name") for a in self._search_areas]
        if "Full Screen" not in names:
            self._search_areas.insert(0, get_default_search_area("Full Screen"))
