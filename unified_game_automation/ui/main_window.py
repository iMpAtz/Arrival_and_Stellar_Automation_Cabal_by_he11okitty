# Main tabbed window for the Unified Game Automation Tool
# Title: "Stellar and Arrival Skill Automation"
# Redesigned with CustomTkinter for a modern dark-themed UI

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import keyboard
import time
import threading
from datetime import datetime
from PIL import Image, ImageTk
import os
import sys
from core.game_connector import GameConnector
from core.ocr_engine import OCREngine
from core.bot_core import BotCore
from ui.stellar_tab import StellarTab
from ui.arrival_tab import ArrivalTab
from ui.heil_tab import HeilTab
from ui.mail_tab import MailTab
from ui.pet_tab import PetTab
from ui.image_clicker_tab import ImageClickerTab
from ui.macro_tab import MacroTab

# ──────────────────────────────────────────────────────────────
# Monkey-patch: CTkScrollableFrame._check_if_valid_scroll
# CustomTkinter 6.0.0 crashes when scrolling over ttk widgets
# (Combobox, Treeview) because event.widget can be a string path
# instead of a widget object.  Guard against that.
# ──────────────────────────────────────────────────────────────
_orig_check = ctk.CTkScrollableFrame._check_if_valid_scroll

def _patched_check_if_valid_scroll(self, widget):
    if isinstance(widget, str):
        return False
    try:
        return _orig_check(self, widget)
    except (AttributeError, TypeError):
        return False

ctk.CTkScrollableFrame._check_if_valid_scroll = _patched_check_if_valid_scroll

# ──────────────────────────────────────────────────────────────
# Color constants for manual accent overrides
# ──────────────────────────────────────────────────────────────
ACCENT = {
    "primary":  "#1f6aa5",
    "success":  "#2fa572",
    "danger":   "#d9534f",
    "warning":  "#e8a317",
    "info":     "#17a2b8",
    "purple":   "#7c3aed",
    "surface":  "#2b2b2b",
    "surface2": "#333333",
    "muted":    "#888888",
}


# ──────────────────────────────────────────────────────────────
# Lightweight Tooltip (no external package needed)
# ──────────────────────────────────────────────────────────────
class ToolTip:
    """Hover tooltip for any widget."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._cancel)
        widget.bind("<ButtonPress>", self._cancel)

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self, _event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        label = tk.Label(
            tw, text=self.text,
            justify=tk.LEFT,
            background="#1e1e1e", foreground="#e0e0e0",
            relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 9),
            padx=8, pady=4,
        )
        label.pack()

    def _hide(self):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


# ──────────────────────────────────────────────────────────────
# MainWindow
# ──────────────────────────────────────────────────────────────
class MainWindow:
    def __init__(self):
        """Initialize the main tabbed window."""

        # ── CTk setup ──
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(
            "CABAL Automation Tool — v6.0.5 By Hello Kitty Gang (Not for selling)"
        )
        self.root.geometry("680x1020")
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)
        self.root.minsize(680, 800)

        # Set window icon (top-left title bar & taskbar)
        try:
            base_dir = getattr(
                sys,
                "_MEIPASS",
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..")
                ),
            )
            icon_path = os.path.join(base_dir, "data", "logo.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(
                    os.path.dirname(__file__), "..", "data", "logo.ico"
                )
            if os.path.exists(icon_path):
                # iconbitmap sets native Windows title bar icon (.ico)
                self.root.iconbitmap(icon_path)
                # Keep reference to prevent garbage collection
                icon_img = Image.open(icon_path)
                self._icon_photo = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, self._icon_photo)
        except Exception as e:
            print(f"Could not set window icon: {e}")

        # ── Shared runtime core ──
        self.bot_core = BotCore()
        self.status_var = tk.StringVar(value="Initializing…")
        self.stats_text = tk.StringVar(value="Ready")
        self.theme_var = tk.StringVar(value="dark")

        # For backwards compat with tab code that reads self.main_window.colors
        self.colors = {
            "primary": ACCENT["primary"],
            "success": ACCENT["success"],
            "danger":  ACCENT["danger"],
            "warning": ACCENT["warning"],
            "info":    ACCENT["info"],
            "dark":    "#e0e0e0",
            "light":   "#3a3a3a",
            "bg":      "#1a1a1a",
            "card_bg": "#2b2b2b",
            "text":    "#e0e0e0",
            "text_light": "#a0a0a0",
            "border":  "#404040",
            "entry_bg": "#333333",
            "entry_fg": "#e0e0e0",
            "intro_bg": "#1e2a3a",
        }
        self.mini_frame = None

        # Configure ttk styles for Treeview (used by Image Clicker)
        self._setup_ttk_styles()

        # Shared components
        self.game_connector = GameConnector(self.update_status)
        self.ocr_engine = OCREngine(self.update_status)
        self.bot_core.set_status_callback(self.update_status)

        # ESC emergency stop
        keyboard.add_hotkey("esc", self.emergency_stop)

        # Build UI
        self.create_ui()

        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ──────────────────────────────────────────────────────────
    # ttk styles (only for Treeview — no CTk equivalent)
    # ──────────────────────────────────────────────────────────
    def _setup_ttk_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="#e0e0e0",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            font=("Segoe UI", 9),
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background="#333333",
            foreground="#e0e0e0",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT["primary"])],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#444444")],
        )
        # Combobox dark style (used inside image clicker settings)
        style.configure(
            "TCombobox",
            fieldbackground="#333333",
            background="#3a3a3a",
            foreground="#e0e0e0",
            arrowcolor="#e0e0e0",
        )
        self.root.option_add("*TCombobox*Listbox.background", "#333333")
        self.root.option_add("*TCombobox*Listbox.foreground", "#e0e0e0")
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT["primary"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    # ──────────────────────────────────────────────────────────
    # UI CREATION
    # ──────────────────────────────────────────────────────────
    def create_ui(self):
        """Build the main UI: header → tabs → status → footer."""

        # Main frame
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Header
        self.create_header(self.main_frame)

        # Auto-connect game
        self.auto_connect_to_game()

        # Tabview
        self.tabview = ctk.CTkTabview(
            self.main_frame,
            corner_radius=10,
            segmented_button_fg_color=ACCENT["surface"],
            segmented_button_selected_color=ACCENT["primary"],
            segmented_button_unselected_color=ACCENT["surface2"],
        )
        self.tabview.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # Add tabs
        tab_names = [
            "⚔ Arrival",
            "⭐ Stellar",
            "🎯 Heil",
            "📧 Mail",
            "🐾 Pet",
            "🖱 Img Clicker",
            "🕹️ Macro",
        ]
        for name in tab_names:
            self.tabview.add(name)

        # Create tab instances — each tab class receives the CTkFrame for its tab
        self.arrival_tab = ArrivalTab(self.tabview.tab("⚔ Arrival"), self)
        self.stellar_tab = StellarTab(self.tabview.tab("⭐ Stellar"), self)
        self.heil_tab = HeilTab(self.tabview.tab("🎯 Heil"), self)
        self.mail_tab = MailTab(self.tabview.tab("📧 Mail"), self)
        self.pet_tab = PetTab(self.tabview.tab("🐾 Pet"), self)
        self.image_clicker_tab = ImageClickerTab(self.tabview.tab("🖱 Img Clicker"), self)
        self.macro_tab = MacroTab(self.tabview.tab("🕹️ Macro"), self)

        # Status section
        self.create_status_section(self.main_frame)

        # Footer
        self.create_footer(self.main_frame)

    # ──────────────────────────────────────────────────────────
    # HEADER
    # ──────────────────────────────────────────────────────────
    def create_header(self, parent):
        """Header card: logo + title + connection + toolbar."""
        header = ctk.CTkFrame(parent, corner_radius=10)
        header.pack(fill=tk.X, pady=(0, 0))

        # Row 1 — Title + Connection
        row1 = ctk.CTkFrame(header, fg_color="transparent")
        row1.pack(fill=tk.X, padx=14, pady=(10, 4))

        # Logo image
        try:
            img_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "logo.png"
            )
            if os.path.exists(img_path):
                logo_img = ctk.CTkImage(
                    light_image=Image.open(img_path),
                    dark_image=Image.open(img_path),
                    size=(32, 32),
                )
                ctk.CTkLabel(row1, image=logo_img, text="").pack(
                    side=tk.LEFT, padx=(0, 10)
                )
        except Exception:
            pass

        # Title
        ctk.CTkLabel(
            row1,
            text="CABAL Automation",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
        ).pack(side=tk.LEFT)

        # Version badge
        ctk.CTkLabel(
            row1,
            text=" v6.0.5 ",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            fg_color=ACCENT["primary"],
            corner_radius=6,
            text_color="#ffffff",
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Connection indicator (right)
        conn_frame = ctk.CTkFrame(row1, fg_color="transparent")
        conn_frame.pack(side=tk.RIGHT)

        ctk.CTkLabel(
            conn_frame,
            text="Connection:",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=ACCENT["muted"],
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.connection_indicator = ctk.CTkLabel(
            conn_frame, text="●", font=ctk.CTkFont("Segoe UI", 16),
            text_color=ACCENT["muted"],
        )
        self.connection_indicator.pack(side=tk.LEFT)

        self.connection_text = ctk.CTkLabel(
            conn_frame,
            text="Checking…",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=ACCENT["muted"],
        )
        self.connection_text.pack(side=tk.LEFT, padx=(3, 0))

        # Row 2 — Toolbar
        row2 = ctk.CTkFrame(header, fg_color="transparent")
        row2.pack(fill=tk.X, padx=14, pady=(0, 10))

        # Always-on-top toggle
        self.topmost_btn = ctk.CTkButton(
            row2,
            text="📌 On Top: ON",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=ACCENT["primary"],
            hover_color="#1a5a8e",
            width=120, height=28,
            corner_radius=6,
            command=self.toggle_always_on_top,
        )
        self.topmost_btn.pack(side=tk.LEFT, padx=(0, 6))
        ToolTip(self.topmost_btn, "Keep this window on top of all others")

        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            row2,
            text="☀ Light Mode",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=ACCENT["surface2"],
            hover_color="#444444",
            width=120, height=28,
            corner_radius=6,
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side=tk.LEFT)
        ToolTip(self.theme_btn, "Switch between dark and light themes")

        # Mini mode (right side)
        self.mini_mode_btn = ctk.CTkButton(
            row2,
            text="🗗 Mini Mode",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=ACCENT["surface2"],
            hover_color="#444444",
            width=110, height=28,
            corner_radius=6,
            command=self.switch_to_mini_mode,
        )
        self.mini_mode_btn.pack(side=tk.RIGHT)
        ToolTip(self.mini_mode_btn, "Switch to compact mini mode")

    # ──────────────────────────────────────────────────────────
    # STATUS SECTION
    # ──────────────────────────────────────────────────────────
    def create_status_section(self, parent):
        """Status & stats card with progress bar."""
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill=tk.X, pady=(10, 0))

        # Section label
        ctk.CTkLabel(
            card,
            text="📊  Status & Stats",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(10, 4))

        # Progress bar (indeterminate when automation runs)
        self.progress_bar = ctk.CTkProgressBar(
            card, mode="indeterminate", height=4, corner_radius=2,
            progress_color=ACCENT["primary"],
        )
        self.progress_bar.pack(fill=tk.X, padx=14, pady=(0, 6))
        self.progress_bar.set(0)

        # Status row
        status_row = ctk.CTkFrame(card, fg_color="transparent")
        status_row.pack(fill=tk.X, padx=14, pady=(0, 2))

        ctk.CTkLabel(
            status_row, text="⚡", font=ctk.CTkFont("Segoe UI", 14),
        ).pack(side=tk.LEFT, padx=(0, 6))

        status_text_frame = ctk.CTkFrame(status_row, fg_color="transparent")
        status_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ctk.CTkLabel(
            status_text_frame, text="Current Status:",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=ACCENT["muted"], anchor="w",
        ).pack(fill=tk.X)

        self.status_var.set("Ready")
        self.status_label = ctk.CTkLabel(
            status_text_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=ACCENT["info"],
            anchor="w",
            wraplength=550,
            justify="left",
        )
        self.status_label.pack(fill=tk.X, pady=(1, 0))

        # Separator line
        ctk.CTkFrame(card, height=1, fg_color="#404040").pack(
            fill=tk.X, padx=14, pady=4
        )

        # Stats row
        stats_row = ctk.CTkFrame(card, fg_color="transparent")
        stats_row.pack(fill=tk.X, padx=14, pady=(0, 10))

        ctk.CTkLabel(
            stats_row, text="📈", font=ctk.CTkFont("Segoe UI", 14),
        ).pack(side=tk.LEFT, padx=(0, 6))

        stats_text_frame = ctk.CTkFrame(stats_row, fg_color="transparent")
        stats_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ctk.CTkLabel(
            stats_text_frame, text="Statistics:",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=ACCENT["muted"], anchor="w",
        ).pack(fill=tk.X)

        self.stats_label = ctk.CTkLabel(
            stats_text_frame,
            textvariable=self.stats_text,
            font=ctk.CTkFont("Segoe UI", 11),
            anchor="w",
        )
        self.stats_label.pack(fill=tk.X, pady=(1, 0))

    # ──────────────────────────────────────────────────────────
    # FOOTER
    # ──────────────────────────────────────────────────────────
    def create_footer(self, parent):
        """Emergency-stop footer bar."""
        footer = ctk.CTkFrame(
            parent, corner_radius=10,
            fg_color=ACCENT["danger"],
        )
        footer.pack(fill=tk.X, pady=(10, 0))

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill=tk.X, padx=14, pady=8)

        ctk.CTkLabel(
            inner, text="🚨",
            font=ctk.CTkFont("Segoe UI", 14),
            text_color="#ffffff",
        ).pack(side=tk.LEFT, padx=(0, 8))

        ctk.CTkLabel(
            inner,
            text="Emergency Stop: Press ESC key to stop all automation",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color="#ffffff",
        ).pack(side=tk.LEFT)

    # ──────────────────────────────────────────────────────────
    # TOGGLE HANDLERS
    # ──────────────────────────────────────────────────────────
    def toggle_always_on_top(self):
        """Toggle the Always on Top attribute of the main window."""
        current_state = self.root.attributes("-topmost")
        new_state = not current_state
        self.root.attributes("-topmost", new_state)
        self.update_topmost_button_ui(new_state)

    def update_topmost_button_ui(self, is_topmost):
        """Sync topmost button text in standard and mini layouts."""
        if is_topmost:
            for btn_attr in ("topmost_btn", "mini_topmost_btn"):
                btn = getattr(self, btn_attr, None)
                if btn:
                    btn.configure(
                        text="📌 On Top: ON",
                        fg_color=ACCENT["primary"],
                    )
        else:
            for btn_attr in ("topmost_btn", "mini_topmost_btn"):
                btn = getattr(self, btn_attr, None)
                if btn:
                    btn.configure(
                        text="📌 On Top: OFF",
                        fg_color=ACCENT["surface2"],
                    )

    def toggle_theme(self):
        """Toggle between dark and light themes."""
        current = self.theme_var.get()
        new_theme = "light" if current == "dark" else "dark"
        self.theme_var.set(new_theme)
        ctk.set_appearance_mode(new_theme)

        if new_theme == "dark":
            self.theme_btn.configure(text="☀ Light Mode")
            self.colors.update({
                "dark":    "#e0e0e0",
                "light":   "#3a3a3a",
                "bg":      "#1a1a1a",
                "card_bg": "#2b2b2b",
                "text":    "#e0e0e0",
                "text_light": "#a0a0a0",
                "border":  "#404040",
                "entry_bg": "#333333",
                "entry_fg": "#e0e0e0",
                "intro_bg": "#1e2a3a",
            })
        else:
            self.theme_btn.configure(text="🌙 Dark Mode")
            self.colors.update({
                "dark":    "#263238",
                "light":   "#ECEFF1",
                "bg":      "#FAFAFA",
                "card_bg": "#FFFFFF",
                "text":    "#212121",
                "text_light": "#546E7A",
                "border":  "#E0E0E0",
                "entry_bg": "#FFFFFF",
                "entry_fg": "#212121",
                "intro_bg": "#E3F2FD",
            })

    # ──────────────────────────────────────────────────────────
    # GAME CONNECTION
    # ──────────────────────────────────────────────────────────
    def auto_connect_to_game(self):
        """Automatically connect to the game and show connection status."""
        if self.game_connector.connect_to_game():
            window_rect = self.game_connector.get_window_rect()
            if window_rect:
                window_info = (
                    f"✅ Connected to game ({window_rect.width()}x{window_rect.height()})"
                )
            else:
                window_info = "✅ Connected to game window"
            self.update_status(window_info)

            if hasattr(self, "connection_indicator"):
                self.connection_indicator.configure(text_color=ACCENT["success"])
                self.connection_text.configure(
                    text="Connected", text_color=ACCENT["success"]
                )
            if hasattr(self, "mini_connection_indicator"):
                self.mini_connection_indicator.configure(
                    text_color=ACCENT["success"]
                )
                self.mini_connection_text.configure(
                    text="Connected", text_color=ACCENT["success"]
                )
        else:
            self.update_status(
                "⚠️ Game not found — make sure the game is running"
            )
            if hasattr(self, "connection_indicator"):
                self.connection_indicator.configure(text_color=ACCENT["danger"])
                self.connection_text.configure(
                    text="Disconnected", text_color=ACCENT["danger"]
                )
            if hasattr(self, "mini_connection_indicator"):
                self.mini_connection_indicator.configure(
                    text_color=ACCENT["danger"]
                )
                self.mini_connection_text.configure(
                    text="Disconnected", text_color=ACCENT["danger"]
                )

    # ──────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────
    def update_status(self, message):
        """Update the status display with timestamp."""
        formatted = str(message)

        def ui_update():
            self.status_var.set(formatted)
            try:
                print(f"Status: {formatted}")
            except UnicodeEncodeError:
                try:
                    print(
                        f"Status: {formatted.encode('ascii', 'replace').decode('ascii')}"
                    )
                except Exception:
                    pass

            active_tool = self.bot_core.active_tool()
            has_bar = hasattr(self, "progress_bar")
            if active_tool:
                started_at = self.bot_core._started_at
                elapsed = max(0, time.time() - started_at) if started_at else 0
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                stats = f"⏱️ Running: {minutes}m {seconds}s | Tool: {active_tool}"
                self.stats_text.set(stats)
                if has_bar:
                    self.progress_bar.start()
            else:
                self.stats_text.set("Ready to start automation")
                if has_bar:
                    self.progress_bar.stop()
                    self.progress_bar.set(0)

        if threading.current_thread() is threading.main_thread():
            ui_update()
        else:
            self.root.after(0, ui_update)

    # ──────────────────────────────────────────────────────────
    # RUNNING TOOL (mutual exclusion)
    # ──────────────────────────────────────────────────────────
    def set_running_tool(self, tool_name, automation=None):
        """Set which tool is currently running (mutual exclusion)."""
        return self.bot_core.begin_run(tool_name, automation=automation)

    def clear_running_tool(self):
        """Clear the currently running tool."""
        self.bot_core.end_run()

    # ──────────────────────────────────────────────────────────
    # EMERGENCY STOP
    # ──────────────────────────────────────────────────────────
    def emergency_stop(self):
        """Emergency stop triggered by ESC key."""
        # Always stop Image Clicker (independent of BotCore)
        if hasattr(self, "image_clicker_tab"):
            self.image_clicker_tab.emergency_stop()

        if self.bot_core.is_busy():
            self.update_status("🚨 EMERGENCY STOP — stopping active automation")
            active_tool = self.bot_core.active_tool()
            if active_tool == "Stellar System":
                self.stellar_tab.emergency_stop()
            elif active_tool == "Arrival Skill":
                self.arrival_tab.emergency_stop()
            elif active_tool == "Auto Mail Receive":
                self.mail_tab.emergency_stop()
            elif active_tool == "Heil Auto":
                self.heil_tab.emergency_stop()
            elif active_tool == "Pet Untrain":
                self.pet_tab.emergency_stop()
            elif active_tool == "Macro":
                self.macro_tab.stop_automation()

            self.bot_core.emergency_stop()
            self.clear_running_tool()

            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.attributes("-topmost", False)

    # ──────────────────────────────────────────────────────────
    # CLOSE
    # ──────────────────────────────────────────────────────────
    def on_closing(self):
        """Clean up when closing the application."""
        if hasattr(self, "image_clicker_tab"):
            self.image_clicker_tab.cleanup()
        self.bot_core.emergency_stop()
        keyboard.unhook_all()
        self.root.destroy()

    def run(self):
        """Start the application."""
        self.root.mainloop()

    # ──────────────────────────────────────────────────────────
    # MINI MODE
    # ──────────────────────────────────────────────────────────
    def create_mini_ui(self):
        """Create the compact Mini Mode UI frame."""
        if self.mini_frame is not None:
            return

        self.mini_frame = ctk.CTkFrame(self.root, fg_color="transparent")

        container = ctk.CTkFrame(self.mini_frame, fg_color="transparent")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Row 1 — Header
        row1 = ctk.CTkFrame(container, fg_color="transparent")
        row1.pack(fill=tk.X, pady=(0, 6))

        ctk.CTkLabel(
            row1, text="🐱 CABAL Mini",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=ACCENT["primary"],
        ).pack(side=tk.LEFT)

        self.mini_connection_indicator = ctk.CTkLabel(
            row1, text="●", font=ctk.CTkFont("Segoe UI", 14),
            text_color=ACCENT["muted"],
        )
        self.mini_connection_indicator.pack(side=tk.LEFT, padx=(10, 2))

        self.mini_connection_text = ctk.CTkLabel(
            row1, text="Checking…",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=ACCENT["muted"],
        )
        self.mini_connection_text.pack(side=tk.LEFT)

        self.standard_mode_btn = ctk.CTkButton(
            row1,
            text="🗗 Standard Mode",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=ACCENT["surface2"],
            hover_color="#444444",
            width=130, height=26,
            corner_radius=6,
            command=self.switch_to_standard_mode,
        )
        self.standard_mode_btn.pack(side=tk.RIGHT)

        # Row 2 — Status card
        card = ctk.CTkFrame(container, corner_radius=8)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        status_inner = ctk.CTkFrame(card, fg_color="transparent")
        status_inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        status_line = ctk.CTkFrame(status_inner, fg_color="transparent")
        status_line.pack(fill=tk.X)

        ctk.CTkLabel(
            status_line, text="Status:",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=ACCENT["muted"],
        ).pack(side=tk.LEFT)

        self.mini_status_lbl = ctk.CTkLabel(
            status_line, textvariable=self.status_var,
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=ACCENT["info"],
            anchor="w",
        )
        self.mini_status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        stats_line = ctk.CTkFrame(status_inner, fg_color="transparent")
        stats_line.pack(fill=tk.X, pady=(4, 0))

        ctk.CTkLabel(
            stats_line, text="Stats:",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=ACCENT["muted"],
        ).pack(side=tk.LEFT)

        self.mini_stats_lbl = ctk.CTkLabel(
            stats_line, textvariable=self.stats_text,
            font=ctk.CTkFont("Segoe UI", 10), anchor="w",
        )
        self.mini_stats_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        # Row 3 — Actions
        row3 = ctk.CTkFrame(container, fg_color="transparent")
        row3.pack(fill=tk.X)

        self.mini_topmost_btn = ctk.CTkButton(
            row3,
            text="📌 On Top: ON",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=ACCENT["primary"],
            hover_color="#1a5a8e",
            width=120, height=28,
            corner_radius=6,
            command=self.toggle_always_on_top,
        )
        self.mini_topmost_btn.pack(side=tk.LEFT)

        self.mini_stop_btn = ctk.CTkButton(
            row3,
            text="🛑 Emergency Stop (ESC)",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=ACCENT["danger"],
            hover_color="#c9302c",
            height=28,
            corner_radius=6,
            command=self.emergency_stop,
        )
        self.mini_stop_btn.pack(side=tk.RIGHT)

    def switch_to_mini_mode(self):
        """Switch the window layout to compact Mini Mode."""
        self.normal_geometry = self.root.geometry()
        self.main_frame.pack_forget()

        if self.mini_frame is None:
            self.create_mini_ui()
            is_topmost = self.root.attributes("-topmost")
            self.update_topmost_button_ui(is_topmost)

        self.mini_frame.pack(fill=tk.BOTH, expand=True)
        self.root.minsize(400, 170)
        self.root.geometry("400x170")
        self.auto_connect_to_game()

    def switch_to_standard_mode(self):
        """Switch the window layout back to Standard Mode."""
        if self.mini_frame:
            self.mini_frame.pack_forget()

        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.root.minsize(680, 800)
        self.root.geometry(self.normal_geometry)
        self.auto_connect_to_game()
