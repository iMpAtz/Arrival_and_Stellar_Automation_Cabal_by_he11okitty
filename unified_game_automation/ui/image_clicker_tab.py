# Image Clicker tab UI
# Allows importing template images, defining search areas, and running detection
#
# This tab is independent from the shared BotCore mutual-exclusion system.
# The Image Clicker runs on its own thread and only stops on explicit user
# action (Stop button, hotkey, or ESC emergency stop).

import os
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

    # ================================================================== #
    #  UI CREATION
    # ================================================================== #

    def create_ui(self):
        colors = self.main_window.colors

        main = tk.Frame(self.parent_frame, bg="white")
        main.pack(fill=tk.BOTH, expand=True)

        # ---- Scrollable wrapper ---- #
        canvas = tk.Canvas(main, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg="white")

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scroll
        def _on_mwheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mwheel))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        container = self._scroll_frame

        # ---- 1) Intro card ---- #
        self._create_intro_card(container, colors)
        # ---- 2) Search Areas card ---- #
        self._create_search_areas_card(container, colors)
        # ---- 3) Image List card ---- #
        self._create_image_list_card(container, colors)
        # ---- 4) Image Config card ---- #
        self._create_image_config_card(container, colors)
        # ---- 5) Control buttons ---- #
        self._create_control_buttons(container, colors)

    # ------------------------------------------------------------------ #
    # 1) Intro
    # ------------------------------------------------------------------ #
    def _create_intro_card(self, parent, colors):
        card = tk.Frame(parent, bg=colors["intro_bg"], relief="flat", bd=0)
        card.pack(fill=tk.X, padx=0, pady=(0, 6))

        inner = tk.Frame(card, bg=colors["intro_bg"])
        inner.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(inner, text="🖱️", font=("Segoe UI", 12), bg=colors["intro_bg"]).pack(
            side=tk.LEFT, padx=(0, 6)
        )

        text_frame = tk.Frame(inner, bg=colors["intro_bg"])
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            text_frame,
            text="IMAGE CLICKER — Automated Image Detection & Click",
            font=("Segoe UI", 9, "bold"),
            bg=colors["intro_bg"],
            fg=colors["text"],
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            text_frame,
            text="Import template images • Define search areas • Auto-detect & click",
            font=("Segoe UI", 7),
            bg=colors["intro_bg"],
            fg=colors["text_light"],
            anchor="w",
        ).pack(fill=tk.X)

    # ------------------------------------------------------------------ #
    # 2) Search Areas
    # ------------------------------------------------------------------ #
    def _create_search_areas_card(self, parent, colors):
        card = tk.Frame(parent, bg="white", relief="flat", bd=0)
        card.pack(fill=tk.X, padx=0, pady=(0, 6))

        header = tk.Frame(card, bg=colors["warning"], height=28)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="📐 Search Areas",
            font=("Segoe UI", 8, "bold"),
            bg=colors["warning"],
            fg="white",
        ).pack(side=tk.LEFT, padx=10, pady=5)

        body = tk.Frame(card, bg="white")
        body.pack(fill=tk.X, padx=10, pady=6)

        # Listbox
        list_frame = tk.Frame(body, bg="white")
        list_frame.pack(fill=tk.X)

        self.area_listbox = tk.Listbox(
            list_frame, height=4, font=("Segoe UI", 8), selectmode=tk.SINGLE,
            bg=colors["entry_bg"], fg=colors["entry_fg"],
        )
        self.area_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        area_sb = tk.Scrollbar(list_frame, orient="vertical", command=self.area_listbox.yview)
        area_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.area_listbox.configure(yscrollcommand=area_sb.set)

        # Buttons
        btn_frame = tk.Frame(body, bg="white")
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        tk.Button(
            btn_frame, text="➕ Add Area", font=("Segoe UI", 7, "bold"),
            bg=colors["primary"], fg="white", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self._add_search_area,
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
            btn_frame, text="🗑️ Remove", font=("Segoe UI", 7, "bold"),
            bg=colors["danger"], fg="white", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self._remove_search_area,
        ).pack(side=tk.LEFT)

    # ------------------------------------------------------------------ #
    # 3) Image List
    # ------------------------------------------------------------------ #
    def _create_image_list_card(self, parent, colors):
        card = tk.Frame(parent, bg="white", relief="flat", bd=0)
        card.pack(fill=tk.X, padx=0, pady=(0, 6))

        header = tk.Frame(card, bg=colors["primary"], height=28)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="🖼️ Template Images",
            font=("Segoe UI", 8, "bold"),
            bg=colors["primary"],
            fg="white",
        ).pack(side=tk.LEFT, padx=10, pady=5)

        body = tk.Frame(card, bg="white")
        body.pack(fill=tk.X, padx=10, pady=6)

        # Treeview for images
        tree_frame = tk.Frame(body, bg="white")
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

        tree_sb = tk.Scrollbar(tree_frame, orient="vertical", command=self.image_tree.yview)
        self.image_tree.configure(yscrollcommand=tree_sb.set)

        self.image_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.image_tree.bind("<<TreeviewSelect>>", self._on_image_selected)

        # Buttons
        btn_frame = tk.Frame(body, bg="white")
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        tk.Button(
            btn_frame, text="📥 Import Image", font=("Segoe UI", 7, "bold"),
            bg=colors["success"], fg="white", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self._import_image,
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
            btn_frame, text="🗑️ Remove Image", font=("Segoe UI", 7, "bold"),
            bg=colors["danger"], fg="white", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self._remove_image,
        ).pack(side=tk.LEFT)

    # ------------------------------------------------------------------ #
    # 4) Image Config
    # ------------------------------------------------------------------ #
    def _create_image_config_card(self, parent, colors):
        card = tk.Frame(parent, bg="white", relief="flat", bd=0)
        card.pack(fill=tk.X, padx=0, pady=(0, 6))

        header = tk.Frame(card, bg=colors["info"], height=28)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="⚙️ Selected Image Settings",
            font=("Segoe UI", 8, "bold"),
            bg=colors["info"],
            fg="white",
        ).pack(side=tk.LEFT, padx=10, pady=5)

        body = tk.Frame(card, bg="white")
        body.pack(fill=tk.X, padx=10, pady=6)
        self._config_body = body

        # Name
        row_name = tk.Frame(body, bg="white")
        row_name.pack(fill=tk.X, pady=2)
        tk.Label(row_name, text="Name:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_name_var = tk.StringVar()
        tk.Entry(row_name, textvariable=self.cfg_name_var, font=("Segoe UI", 8),
                 width=25, relief="solid", bd=1).pack(side=tk.LEFT, padx=(5, 0))

        # Enabled
        row_enabled = tk.Frame(body, bg="white")
        row_enabled.pack(fill=tk.X, pady=2)
        tk.Label(row_enabled, text="Enabled:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row_enabled, variable=self.cfg_enabled_var, bg="white").pack(side=tk.LEFT)

        # Threshold
        row_thresh = tk.Frame(body, bg="white")
        row_thresh.pack(fill=tk.X, pady=2)
        tk.Label(row_thresh, text="Threshold:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_threshold_var = tk.StringVar(value="0.85")
        tk.Entry(row_thresh, textvariable=self.cfg_threshold_var, font=("Segoe UI", 8),
                 width=8, relief="solid", bd=1).pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(row_thresh, text="(0.0 – 1.0)", font=("Segoe UI", 7),
                 bg="white", fg=colors["text_light"]).pack(side=tk.LEFT, padx=(6, 0))

        # Search Area
        row_area = tk.Frame(body, bg="white")
        row_area.pack(fill=tk.X, pady=2)
        tk.Label(row_area, text="Search Area:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_area_var = tk.StringVar(value="Full Screen")
        self.cfg_area_combo = ttk.Combobox(row_area, textvariable=self.cfg_area_var,
                                           state="readonly", width=20, font=("Segoe UI", 8))
        self.cfg_area_combo.pack(side=tk.LEFT, padx=(5, 0))
        self._refresh_area_combo()

        # Click Type
        row_click = tk.Frame(body, bg="white")
        row_click.pack(fill=tk.X, pady=2)
        tk.Label(row_click, text="Click Type:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_click_var = tk.StringVar(value="Left Click")
        ttk.Combobox(row_click, textvariable=self.cfg_click_var,
                     values=CLICK_TYPES, state="readonly", width=15,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(5, 0))

        # Offset X / Y
        row_offset = tk.Frame(body, bg="white")
        row_offset.pack(fill=tk.X, pady=2)
        tk.Label(row_offset, text="Offset X:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_offset_x_var = tk.StringVar(value="0")
        tk.Entry(row_offset, textvariable=self.cfg_offset_x_var, font=("Segoe UI", 8),
                 width=6, relief="solid", bd=1).pack(side=tk.LEFT, padx=(5, 8))
        tk.Label(row_offset, text="Y:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"]).pack(side=tk.LEFT)
        self.cfg_offset_y_var = tk.StringVar(value="0")
        tk.Entry(row_offset, textvariable=self.cfg_offset_y_var, font=("Segoe UI", 8),
                 width=6, relief="solid", bd=1).pack(side=tk.LEFT, padx=(5, 0))

        # Cooldown
        row_cd = tk.Frame(body, bg="white")
        row_cd.pack(fill=tk.X, pady=2)
        tk.Label(row_cd, text="Cooldown (ms):", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], width=12, anchor="w").pack(side=tk.LEFT)
        self.cfg_cooldown_var = tk.StringVar(value="1000")
        tk.Entry(row_cd, textvariable=self.cfg_cooldown_var, font=("Segoe UI", 8),
                 width=8, relief="solid", bd=1).pack(side=tk.LEFT, padx=(5, 0))

        # Apply button
        apply_frame = tk.Frame(body, bg="white")
        apply_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(
            apply_frame, text="💾 Apply Changes", font=("Segoe UI", 8, "bold"),
            bg=colors["success"], fg="white", relief="flat", padx=15, pady=4,
            cursor="hand2", command=self._apply_image_config,
        ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------ #
    # 5) Controls
    # ------------------------------------------------------------------ #
    def _create_control_buttons(self, parent, colors):
        card = tk.Frame(parent, bg="white", relief="flat", bd=0)
        card.pack(fill=tk.X, padx=0, pady=(0, 6))

        body = tk.Frame(card, bg="white")
        body.pack(fill=tk.X, padx=10, pady=8)

        # Scan interval
        interval_row = tk.Frame(body, bg="white")
        interval_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(interval_row, text="Scan Interval (ms):", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], anchor="w").pack(side=tk.LEFT)
        self.scan_interval_var = tk.StringVar(value="200")
        tk.Entry(interval_row, textvariable=self.scan_interval_var, font=("Segoe UI", 8),
                 width=8, relief="solid", bd=1).pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(interval_row, text="(delay between scan cycles)",
                 font=("Segoe UI", 7), bg="white", fg=colors["text_light"]).pack(
            side=tk.LEFT, padx=(6, 0))

        # Hotkey row
        hotkey_row = tk.Frame(body, bg="white")
        hotkey_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hotkey_row, text="Toggle Hotkey:", font=("Segoe UI", 8, "bold"),
                 bg="white", fg=colors["text"], anchor="w").pack(side=tk.LEFT)
        self.hotkey_var = tk.StringVar(value=self._hotkey_name)
        self.hotkey_entry = tk.Entry(hotkey_row, textvariable=self.hotkey_var,
                                     font=("Segoe UI", 8), width=8, relief="solid", bd=1)
        self.hotkey_entry.pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(
            hotkey_row, text="Set", font=("Segoe UI", 7, "bold"),
            bg=colors["primary"], fg="white", relief="flat", padx=8, pady=2,
            cursor="hand2", command=self._update_hotkey,
        ).pack(side=tk.LEFT, padx=(4, 0))
        self.hotkey_status_var = tk.StringVar(value=f"(Press {self._hotkey_name} to toggle)")
        tk.Label(hotkey_row, textvariable=self.hotkey_status_var,
                 font=("Segoe UI", 7), bg="white", fg=colors["text_light"]).pack(
            side=tk.LEFT, padx=(6, 0))

        # Buttons
        btn_frame = tk.Frame(body, bg="white")
        btn_frame.pack()

        self.btn_start = tk.Button(
            btn_frame, text="▶️ START (F6)", font=("Segoe UI", 9, "bold"),
            bg=colors["success"], fg="white", relief="flat", padx=30, pady=8,
            cursor="hand2", command=self.start_automation,
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_stop = tk.Button(
            btn_frame, text="⏹️ STOP (F6)", font=("Segoe UI", 9, "bold"),
            bg=colors["danger"], fg="white", relief="flat", padx=30, pady=8,
            cursor="hand2", state=tk.DISABLED, command=self.stop_automation,
        )
        self.btn_stop.pack(side=tk.LEFT)

    # ================================================================== #
    #  HOTKEY
    # ================================================================== #

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
        # Update button labels
        self.btn_start.config(text=f"▶️ START ({self._hotkey_name})")
        self.btn_stop.config(text=f"⏹️ STOP ({self._hotkey_name})")
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

    # ================================================================== #
    #  SEARCH AREA ACTIONS
    # ================================================================== #

    def _add_search_area(self):
        if self._running:
            return

        name_win = tk.Toplevel(self.main_window.root)
        name_win.title("New Search Area")
        name_win.geometry("300x120")
        name_win.attributes("-topmost", True)
        name_win.resizable(False, False)

        tk.Label(name_win, text="Area name:", font=("Segoe UI", 9)).pack(pady=(12, 4))
        name_var = tk.StringVar(value=f"Area {len(self._search_areas)}")
        name_entry = tk.Entry(name_win, textvariable=name_var, width=25, font=("Segoe UI", 9))
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

        tk.Button(name_win, text="OK & Select Area", command=on_ok,
                  font=("Segoe UI", 8, "bold"), bg="#2196F3", fg="white",
                  relief="flat", padx=12, pady=4).pack(pady=(10, 0))
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

    # ================================================================== #
    #  IMAGE LIST ACTIONS
    # ================================================================== #

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

    # ================================================================== #
    #  START / STOP  (no BotCore mutual exclusion)
    # ================================================================== #

    def start_automation(self):
        if self._running:
            return

        # Validate scan interval
        try:
            interval = int(self.scan_interval_var.get())
            if interval < 50:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Scan interval must be ≥ 50 ms")
            return

        # Push config to automation
        self.automation.set_image_configs(self._image_configs)
        self.automation.set_search_areas(self._search_areas)
        self.automation.set_scan_interval(interval)

        if self.automation.start():
            self._running = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)

    def stop_automation(self):
        self.automation.stop()
        self._running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.update_status("Image Clicker stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self._running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def cleanup(self):
        """Called when the application is closing."""
        self._unregister_hotkey()
        if self._running:
            self.automation.stop()

    # ================================================================== #
    #  CONFIG PERSISTENCE
    # ================================================================== #

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
