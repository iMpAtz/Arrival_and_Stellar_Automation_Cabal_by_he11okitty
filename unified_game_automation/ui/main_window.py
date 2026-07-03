# Main tabbed window for the Unified Game Automation Tool
# Title: "Stellar and Arrival Skill Automation"

import tkinter as tk
from tkinter import ttk, scrolledtext
import keyboard
import time
import threading
from datetime import datetime
from PIL import Image, ImageTk
import os
from core.game_connector import GameConnector
from core.ocr_engine import OCREngine
from core.bot_core import BotCore
from ui.stellar_tab import StellarTab
from ui.arrival_tab import ArrivalTab
from ui.heil_tab import HeilTab
from ui.mail_tab import MailTab
from ui.pet_tab import PetTab
from ui.image_clicker_tab import ImageClickerTab
# Color Palettes for Light and Dark themes
LIGHT_COLORS = {
    'primary': '#2196F3',
    'success': '#4CAF50',
    'danger': '#f44336',
    'warning': '#FF9800',
    'info': '#00BCD4',
    'dark': '#263238',
    'light': '#ECEFF1',
    'bg': '#FAFAFA',
    'card_bg': '#FFFFFF',
    'text': '#212121',
    'text_light': '#546E7A',
    'border': '#E0E0E0',
    'entry_bg': '#FFFFFF',
    'entry_fg': '#212121',
    'intro_bg': '#E3F2FD',
}

DARK_COLORS = {
    'primary': '#1E88E5',
    'success': '#43A047',
    'danger': '#E53935',
    'warning': '#FB8C00',
    'info': '#00ACC1',
    'dark': '#ECEFF1',
    'light': '#455A64',
    'bg': '#121212',
    'card_bg': '#1E1E1E',
    'text': '#E0E0E0',
    'text_light': '#B0BEC5',
    'border': '#37474F',
    'entry_bg': '#2C2C2C',
    'entry_fg': '#E0E0E0',
    'intro_bg': '#1A237E',
}

class MainWindow:
    def __init__(self):
        """Initialize the main tabbed window"""
        self.root = tk.Tk()
        self.root.title("CABAL Automation Tool - v6.0.4 By Hello Kitty Gang (Not for selling)")
        self.root.geometry("600x1000")
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)
        self.root.minsize(700, 800)
        # Set background color
        self.root.configure(bg='#f0f0f0')

        # Set window icon using Hello Kitty image
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'logo.png')
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, icon_photo)
        except Exception as e:
            print(f"Could not set window icon: {e}")

        # Global runtime controller for all tabs/automations.
        self.bot_core = BotCore()

        # Initialize status variable first
        self.status_var = tk.StringVar(value="Initializing...")
        
        # Statistics variables
        self.stats_text = tk.StringVar(value="Ready")

        # Theme and color settings
        self.theme_var = tk.StringVar(value="light")
        self.colors = LIGHT_COLORS
        self.mini_frame = None

        # Configure ttk style
        self.setup_styles()

        # Shared components (after status_var is created)
        self.game_connector = GameConnector(self.update_status)
        self.ocr_engine = OCREngine(self.update_status)
        self.bot_core.set_status_callback(self.update_status)

        # Set up emergency kill switch (ESC key)
        keyboard.add_hotkey('esc', self.emergency_stop)

        # Create UI
        self.create_ui()

        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Setup custom ttk styles for better UI"""
        style = ttk.Style()
        
        # Try to use a modern theme
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')
        
        # Ensure self.colors is initialized
        if not hasattr(self, 'colors'):
            self.colors = LIGHT_COLORS
        
        # Configure notebook (tabs)
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', 
                       padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'),
                       background=self.colors['light'],
                       foreground=self.colors['text_light'])
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['primary']), ('!selected', self.colors['light'])],
                 foreground=[('selected', '#000000'), ('!selected', self.colors['text_light'])])
        
        # Custom button styles
        style.configure('Primary.TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       padding=[15, 8],
                       relief='flat')
        style.map('Primary.TButton',
                 background=[('active', self.colors['primary']), ('!active', self.colors['primary'])],
                 foreground=[('active', 'white'), ('!active', 'white')])
        
        style.configure('Success.TButton', 
                       font=('Segoe UI', 10),
                       padding=[15, 8])
        style.map('Success.TButton',
                 foreground=[('!active', self.colors['success'])])
        
        style.configure('Danger.TButton', 
                       font=('Segoe UI', 10),
                       padding=[15, 8])
        style.map('Danger.TButton',
                 foreground=[('!active', self.colors['danger'])])
        
        # Frame styles
        style.configure('Card.TFrame', background=self.colors['card_bg'], relief='flat', borderwidth=1)
        style.configure('TFrame', background=self.colors['bg'])
        
        # Label styles
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 16, 'bold'),
                       background=self.colors['bg'],
                       foreground=self.colors['dark'])
        
        style.configure('Subtitle.TLabel', 
                       font=('Segoe UI', 11),
                       background=self.colors['bg'],
                       foreground=self.colors['text_light'])
        
        style.configure('Status.TLabel', 
                       font=('Segoe UI', 9),
                       background=self.colors['card_bg'],
                       foreground=self.colors['info'])
        
        style.configure('Heading.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       background=self.colors['card_bg'],
                       foreground=self.colors['dark'])
        
        # LabelFrame style
        style.configure('Card.TLabelframe', 
                       background=self.colors['card_bg'],
                       relief='flat',
                       borderwidth=2,
                       padding=15)
        style.configure('Card.TLabelframe.Label',
                       font=('Segoe UI', 11, 'bold'),
                       background=self.colors['card_bg'],
                       foreground=self.colors['dark'])

        # Combobox style
        style.configure('TCombobox', 
                        fieldbackground=self.colors['entry_bg'],
                        background=self.colors['light'],
                        foreground=self.colors['entry_fg'],
                        arrowcolor=self.colors['text'])
        
        # Configure Combobox popdown listbox style via option_add
        self.root.option_add('*TCombobox*Listbox.background', self.colors['entry_bg'])
        self.root.option_add('*TCombobox*Listbox.foreground', self.colors['entry_fg'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.colors['primary'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')

    def toggle_always_on_top(self):
        """Toggle the Always on Top attribute of the main window"""
        current_state = self.root.attributes("-topmost")
        new_state = not current_state
        self.root.attributes("-topmost", new_state)
        self.update_topmost_button_ui(new_state)

    def update_topmost_button_ui(self, is_topmost):
        """Helper to sync topmost button appearance in both standard and mini layouts"""
        if is_topmost:
            for btn_attr in ('topmost_btn', 'mini_topmost_btn'):
                if hasattr(self, btn_attr) and getattr(self, btn_attr):
                    getattr(self, btn_attr).config(
                        text="📌 On Top: ON",
                        bg=self.colors['primary'],
                        fg='white',
                        activebackground=self.colors['primary'],
                        activeforeground='white'
                    )
        else:
            off_fg = 'white' if self.theme_var.get() == 'dark' else self.colors['text_light']
            for btn_attr in ('topmost_btn', 'mini_topmost_btn'):
                if hasattr(self, btn_attr) and getattr(self, btn_attr):
                    getattr(self, btn_attr).config(
                        text="📌 On Top: OFF",
                        bg=self.colors['light'],
                        fg=off_fg,
                        activebackground=self.colors['light'],
                        activeforeground=off_fg
                    )

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_theme = self.theme_var.get()
        new_theme = "dark" if current_theme == "light" else "light"
        self.theme_var.set(new_theme)
        self.apply_theme(new_theme)

    def apply_theme(self, theme_name):
        """Apply the specified theme to the entire UI"""
        if theme_name == "dark":
            self.colors = DARK_COLORS
            if hasattr(self, 'theme_btn') and self.theme_btn:
                self.theme_btn.config(
                    text="☀️ Light Mode",
                    bg='#455A64',
                    fg='#ECEFF1',
                    activebackground='#546E7A',
                    activeforeground='#ECEFF1'
                )
            if hasattr(self, 'mini_mode_btn') and self.mini_mode_btn:
                self.mini_mode_btn.config(
                    bg='#455A64',
                    fg='#ECEFF1',
                    activebackground='#546E7A',
                    activeforeground='#ECEFF1'
                )
            if hasattr(self, 'standard_mode_btn') and self.standard_mode_btn:
                self.standard_mode_btn.config(
                    bg='#455A64',
                    fg='#ECEFF1',
                    activebackground='#546E7A',
                    activeforeground='#ECEFF1'
                )
        else:
            self.colors = LIGHT_COLORS
            if hasattr(self, 'theme_btn') and self.theme_btn:
                self.theme_btn.config(
                    text="🌙 Dark Mode",
                    bg='#ECEFF1',
                    fg='#263238',
                    activebackground='#CFD8DC',
                    activeforeground='#263238'
                )
            if hasattr(self, 'mini_mode_btn') and self.mini_mode_btn:
                self.mini_mode_btn.config(
                    bg='#ECEFF1',
                    fg='#263238',
                    activebackground='#CFD8DC',
                    activeforeground='#263238'
                )
            if hasattr(self, 'standard_mode_btn') and self.standard_mode_btn:
                self.standard_mode_btn.config(
                    bg='#ECEFF1',
                    fg='#263238',
                    activebackground='#CFD8DC',
                    activeforeground='#263238'
                )

        # Update root and styles
        self.root.configure(bg=self.colors['bg'])
        self.setup_styles()
        
        # Traverse and update all widgets in the window
        self.apply_theme_to_widget(self.root, theme_name)
        
        # Update specific controls that need manual refreshing/overrides
        is_topmost = self.root.attributes("-topmost")
        self.update_topmost_button_ui(is_topmost)

    def apply_theme_to_widget(self, widget, theme_name):
        """Recursively apply the theme colors to standard Tkinter widgets"""
        colors = self.colors
        
        # Skip some widgets that shouldn't be recursed or processed if destroyed
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return

        # Determine the widget's role and update its color accordingly
        if isinstance(widget, tk.Frame):
            try:
                curr_bg = widget.cget('bg').lower()
                if curr_bg in ('white', '#ffffff', '#1e1e1e', 'systemwindow', 'systembuttonface'):
                    widget.configure(bg=colors['card_bg'])
                elif curr_bg in ('#e3f2fd', '#1a237e', '#0d47a1'):
                    widget.configure(bg=colors['intro_bg'])
                elif curr_bg in ('#fafafa', '#f0f0f0', '#121212', '#eceff1', '#2c2c2c'):
                    if widget == self.root or widget.master == self.root:
                        widget.configure(bg=colors['bg'])
                    else:
                        widget.configure(bg=colors['card_bg'] if theme_name == 'dark' else 'white')
                elif curr_bg == '#e0e0e0':
                    widget.configure(bg=colors['border'])
            except Exception:
                pass
                
        elif isinstance(widget, tk.Label):
            try:
                curr_bg = widget.cget('bg').lower()
                curr_fg = widget.cget('fg').lower()
                
                # Track if bg is intro-style
                is_intro_bg = curr_bg in ('#e3f2fd', '#1a237e', '#0d47a1')
                
                # Update background
                if curr_bg in ('white', '#ffffff', '#1e1e1e', 'systemwindow', 'systembuttonface'):
                    widget.configure(bg=colors['card_bg'])
                elif is_intro_bg:
                    widget.configure(bg=colors['intro_bg'])
                elif curr_bg in ('#fafafa', '#f0f0f0', '#121212'):
                    widget.configure(bg=colors['bg'])
                
                # Update foreground
                fg_updated = False
                if curr_fg in ('#212121', 'black', '#e0e0e0', 'systemwindowtext'):
                    widget.configure(fg=colors['text'])
                    fg_updated = True
                elif curr_fg in ('#757575', '#b0bec5', '#546e7a'):
                    widget.configure(fg=colors['text_light'])
                    fg_updated = True
                elif curr_fg in ('#263238', '#eceff1'):
                    widget.configure(fg=colors['dark'])
                    fg_updated = True
                elif curr_fg in ('#2196f3', '#1e88e5', '#3b82f6'):
                    widget.configure(fg=colors['primary'])
                    fg_updated = True
                elif curr_fg in ('#4caf50', '#43a047'):
                    widget.configure(fg=colors['success'])
                    fg_updated = True
                elif curr_fg in ('#f44336', '#e53935'):
                    widget.configure(fg=colors['danger'])
                    fg_updated = True
                
                # Fallback: if fg wasn't matched and label is on intro/card bg, force update
                if not fg_updated and is_intro_bg:
                    # Check font to decide text vs text_light
                    try:
                        font = widget.cget('font')
                        if 'bold' in str(font).lower():
                            widget.configure(fg=colors['text'])
                        else:
                            widget.configure(fg=colors['text_light'])
                    except Exception:
                        widget.configure(fg=colors['text_light'])
                elif not fg_updated:
                    # Generic fallback for card-bg labels
                    new_bg = widget.cget('bg').lower()
                    if new_bg == colors['card_bg'].lower() or new_bg == colors['bg'].lower():
                        widget.configure(fg=colors['text'])
            except Exception:
                pass
                
        elif isinstance(widget, tk.Button):
            try:
                # Exclude theme, topmost and mini buttons as they are managed separately
                if widget not in (getattr(self, 'theme_btn', None), getattr(self, 'topmost_btn', None), 
                                  getattr(self, 'mini_mode_btn', None), getattr(self, 'standard_mode_btn', None),
                                  getattr(self, 'mini_topmost_btn', None)):
                    curr_bg = widget.cget('bg').lower()
                    curr_fg = widget.cget('fg').lower()
                    
                    # Map button backgrounds
                    if curr_bg in ('#2196f3', '#1e88e5', '#3b82f6'):
                        widget.configure(bg=colors['primary'], activebackground=colors['primary'])
                    elif curr_bg in ('#4caf50', '#43a047', 'green'):
                        widget.configure(bg=colors['success'], activebackground=colors['success'])
                    elif curr_bg in ('#f44336', '#e53935', 'red'):
                        widget.configure(bg=colors['danger'], activebackground=colors['danger'])
                    elif curr_bg in ('#ff9800', '#f57c00'):
                        widget.configure(bg=colors['warning'], activebackground=colors['warning'])
                    elif curr_bg in ('#9c27b0', '#8e24aa'):
                        widget.configure(bg='#8E24AA' if theme_name == 'dark' else '#9C27B0', activebackground='#8E24AA' if theme_name == 'dark' else '#9C27B0')
                    elif curr_bg in ('white', '#ffffff', '#2c2c2c', '#1e1e1e', 'systemwindow', 'systembuttonface'):
                        widget.configure(bg=colors['card_bg'], fg=colors['text'], activebackground=colors['card_bg'], activeforeground=colors['text'])
                    
                    # Map button text color
                    if curr_fg in ('white', '#ffffff'):
                        widget.configure(fg='white', activeforeground='white')
                    elif curr_fg in ('#212121', 'black', '#e0e0e0', 'systemwindowtext'):
                        widget.configure(fg=colors['text'], activeforeground=colors['text'])
            except Exception:
                pass

        elif isinstance(widget, tk.Entry):
            try:
                widget.configure(bg=colors['entry_bg'], fg=colors['entry_fg'], insertbackground=colors['entry_fg'])
            except Exception:
                pass
            
        elif isinstance(widget, tk.Radiobutton):
            try:
                widget.configure(
                    bg=colors['card_bg'] if theme_name == 'dark' else 'white',
                    fg=colors['text'],
                    selectcolor=colors['card_bg'] if theme_name == 'dark' else 'white',
                    activebackground=colors['card_bg'] if theme_name == 'dark' else 'white',
                    activeforeground=colors['text']
                )
            except Exception:
                pass
            
        elif isinstance(widget, tk.Checkbutton):
            try:
                widget.configure(
                    bg=colors['card_bg'] if theme_name == 'dark' else 'white',
                    fg=colors['text'],
                    selectcolor=colors['card_bg'] if theme_name == 'dark' else 'white',
                    activebackground=colors['card_bg'] if theme_name == 'dark' else 'white',
                    activeforeground=colors['text']
                )
            except Exception:
                pass

        elif isinstance(widget, tk.Canvas):
            try:
                curr_bg = widget.cget('bg').lower()
                if curr_bg in ('white', '#ffffff', '#1e1e1e'):
                    widget.configure(bg=colors['card_bg'])
            except Exception:
                pass

        # Recurse for children
        try:
            for child in widget.winfo_children():
                self.apply_theme_to_widget(child, theme_name)
        except Exception:
            pass

    def create_ui(self):
        """Create the main UI with tabs"""
        # Main frame with modern styling
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Header section
        self.create_header(self.main_frame)

        # Auto-connect to game and show status
        self.auto_connect_to_game()

        # Create notebook for tabs with modern styling
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # Create tab frames with card styling
        arrival_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        stellar_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        heil_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        mail_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        pet_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        image_clicker_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)

        # Add tabs to notebook with emoji icons
        self.notebook.add(arrival_frame, text="Arrival Skill")
        self.notebook.add(stellar_frame, text="Stellar System")
        self.notebook.add(heil_frame, text="Heil Auto")
        self.notebook.add(mail_frame, text="Mail Receive")
        self.notebook.add(pet_frame, text="Pet Untrain")
        self.notebook.add(image_clicker_frame, text="Image Clicker")

        # Create tab instances
        self.arrival_tab = ArrivalTab(arrival_frame, self)
        self.stellar_tab = StellarTab(stellar_frame, self)
        self.heil_tab = HeilTab(heil_frame, self)
        self.mail_tab = MailTab(mail_frame, self)
        self.pet_tab = PetTab(pet_frame, self)
        self.image_clicker_tab = ImageClickerTab(image_clicker_frame, self)
        # Status and Log section
        self.create_status_section(self.main_frame)

        # Footer section
        self.create_footer(self.main_frame)

    def create_header(self, parent):
        """Create header section with connection info and toolbar"""
        # Header card
        header_card = tk.Frame(parent, bg='white', relief='flat', bd=0)
        header_card.pack(fill=tk.X, pady=(0, 0))
        
        # === Row 1: Title + Connection Status ===
        title_row = tk.Frame(header_card, bg='white')
        title_row.pack(fill=tk.X, padx=12, pady=(8, 4))
        
        # Title section (left)
        title_frame = tk.Frame(title_row, bg='white')
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Try to load Hello Kitty image
        try:
            img_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'logo.png')
            if os.path.exists(img_path):
                img = Image.open(img_path)
                img = img.resize((30, 30), Image.Resampling.LANCZOS)
                self.hello_kitty_photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(title_frame, image=self.hello_kitty_photo, bg='white')
                img_label.pack(side=tk.LEFT, padx=(0, 8))
            else:
                print(f"Hello Kitty image not found at: {img_path}")
        except Exception as e:
            print(f"Could not load Hello Kitty image: {e}")
        
        title_label = tk.Label(title_frame, 
                              text="CABAL Automation By Hello Kitty Gang", 
                              font=('Segoe UI', 14, 'bold'),
                              bg='white',
                              fg=self.colors['dark'])
        title_label.pack(side=tk.LEFT)
        
        version_badge = tk.Label(title_frame,
                                text="v6.0.4",
                                font=('Segoe UI', 8, 'bold'),
                                bg=self.colors['primary'],
                                fg='white',
                                padx=6,
                                pady=1)
        version_badge.pack(side=tk.LEFT, padx=(8, 0))

        # Connection status (right side of title row)
        status_frame = tk.Frame(title_row, bg='white')
        status_frame.pack(side=tk.RIGHT)
        
        connection_label = tk.Label(status_frame,
                                   text="Connection:",
                                   font=('Segoe UI', 8),
                                   bg='white',
                                   fg=self.colors['text_light'])
        connection_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.connection_indicator = tk.Label(status_frame, 
                                            text="●", 
                                            font=("Arial", 16),
                                            bg='white',
                                            fg='#9E9E9E')
        self.connection_indicator.pack(side=tk.LEFT)
        
        self.connection_text = tk.Label(status_frame,
                                       text="Checking...",
                                       font=('Segoe UI', 8, 'bold'),
                                       bg='white',
                                       fg=self.colors['text_light'])
        self.connection_text.pack(side=tk.LEFT, padx=(3, 0))

        # === Row 2: Toolbar (toggle buttons) ===
        toolbar_row = tk.Frame(header_card, bg=self.colors['bg'])
        toolbar_row.pack(fill=tk.X, padx=12, pady=(0, 6))

        # Always on top toggle button
        self.topmost_btn = tk.Button(toolbar_row, 
                                     text="📌 On Top: ON",
                                     font=('Segoe UI', 7, 'bold'),
                                     bg=self.colors['primary'],
                                     fg='white',
                                     relief='flat',
                                     padx=8,
                                     pady=2,
                                     cursor='hand2',
                                     activebackground=self.colors['primary'],
                                     activeforeground='white',
                                     command=self.toggle_always_on_top)
        self.topmost_btn.pack(side=tk.LEFT, padx=(0, 6))

        # Theme toggle button
        self.theme_btn = tk.Button(toolbar_row, 
                                   text="🌙 Dark Mode",
                                   font=('Segoe UI', 7, 'bold'),
                                   bg=self.colors['light'],
                                   fg=self.colors['dark'],
                                   relief='flat',
                                   padx=8,
                                   pady=2,
                                   cursor='hand2',
                                   activebackground=self.colors['light'],
                                   activeforeground=self.colors['dark'],
                                   command=self.toggle_theme)
        self.theme_btn.pack(side=tk.LEFT)

        # Mini Mode toggle button
        self.mini_mode_btn = tk.Button(toolbar_row, 
                                       text="🗖 Mini Mode",
                                       font=('Segoe UI', 7, 'bold'),
                                       bg=self.colors['light'],
                                       fg=self.colors['dark'],
                                       relief='flat',
                                       padx=8,
                                       pady=2,
                                       cursor='hand2',
                                       activebackground=self.colors['light'],
                                       activeforeground=self.colors['dark'],
                                       command=self.switch_to_mini_mode)
        self.mini_mode_btn.pack(side=tk.RIGHT)
        
        # Shadow separator
        shadow_frame = tk.Frame(header_card, bg='#e0e0e0', height=2)
        shadow_frame.pack(fill=tk.X)

    def create_status_section(self, parent):
        """Create enhanced status display section"""
        # Status card with modern design
        status_card = tk.Frame(parent, bg='white', relief='flat', bd=0)
        status_card.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Card shadow
        shadow = tk.Frame(parent, bg='#e0e0e0', height=2)
        shadow.place(in_=status_card, relx=0, rely=1, relwidth=1)
        
        # Card header
        card_header = tk.Frame(status_card, bg=self.colors['primary'])
        card_header.pack(fill=tk.X)
        
        header_label = tk.Label(card_header,
                               text="📊 Status & Stats",
                               font=('Segoe UI', 9, 'bold'),
                               bg=self.colors['primary'],
                               fg='white',
                               anchor='w')
        header_label.pack(fill=tk.X, padx=12, pady=6)
        
        # Card body
        card_body = tk.Frame(status_card, bg='white')
        card_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        # Current status
        status_container = tk.Frame(card_body, bg='white')
        status_container.pack(fill=tk.X, pady=(0, 6))
        
        status_icon = tk.Label(status_container,
                              text="⚡",
                              font=('Segoe UI', 12),
                              bg='white',
                              fg=self.colors['primary'])
        status_icon.pack(side=tk.LEFT, padx=(0, 6))
        
        status_text_frame = tk.Frame(status_container, bg='white')
        status_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(status_text_frame, 
                text="Current Status:", 
                font=('Segoe UI', 8),
                bg='white',
                fg=self.colors['text_light'],
                anchor='w').pack(fill=tk.X)
        
        self.status_var.set("Ready")
        self.status_label = tk.Label(status_text_frame, 
                                     textvariable=self.status_var,
                                     font=('Segoe UI', 9, 'bold'),
                                     bg='white',
                                     fg=self.colors['info'],
                                     anchor='w',
                                     wraplength=600,
                                     justify='left')
        self.status_label.pack(fill=tk.X, pady=(1, 0))
        
        # Separator
        tk.Frame(card_body, bg='#e0e0e0', height=1).pack(fill=tk.X, pady=6)
        
        # Statistics
        stats_container = tk.Frame(card_body, bg='white')
        stats_container.pack(fill=tk.X)
        
        stats_icon = tk.Label(stats_container,
                             text="📈",
                             font=('Segoe UI', 12),
                             bg='white',
                             fg=self.colors['success'])
        stats_icon.pack(side=tk.LEFT, padx=(0, 6))
        
        stats_text_frame = tk.Frame(stats_container, bg='white')
        stats_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(stats_text_frame,
                text="Statistics:",
                font=('Segoe UI', 8),
                bg='white',
                fg=self.colors["text_light"],
                anchor='w').pack(fill=tk.X)
        
        self.stats_label = tk.Label(stats_text_frame, 
                                    textvariable=self.stats_text,
                                    font=('Segoe UI', 9),
                                    bg='white',
                                    fg=self.colors['text'],
                                    anchor='w')
        self.stats_label.pack(fill=tk.X, pady=(1, 0))

    def create_footer(self, parent):
        """Create footer with emergency stop and info"""
        # Footer frame
        footer_frame = tk.Frame(parent, bg=self.colors['bg'])
        footer_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Emergency stop card
        emergency_card = tk.Frame(footer_frame, bg=self.colors['danger'], relief='flat', bd=0)
        emergency_card.pack(fill=tk.X)
        
        emergency_inner = tk.Frame(emergency_card, bg=self.colors['danger'])
        emergency_inner.pack(fill=tk.X, padx=12, pady=6)
        
        emergency_icon = tk.Label(emergency_inner,
                                 text="🚨",
                                 font=('Segoe UI', 12),
                                 bg=self.colors['danger'],
                                 fg='white')
        emergency_icon.pack(side=tk.LEFT, padx=(0, 6))
        
        emergency_label = tk.Label(emergency_inner, 
                                  text="Emergency Stop: Press ESC key to stop all automation",
                                  font=('Segoe UI', 9, 'bold'),
                                  bg=self.colors['danger'],
                                  fg='white')
        emergency_label.pack(side=tk.LEFT)

    def auto_connect_to_game(self):
        """Automatically connect to the game and show connection status"""
        if self.game_connector.connect_to_game():
            # Get game window info for display
            window_rect = self.game_connector.get_window_rect()
            if window_rect:
                window_info = f"✅ Connected to game ({window_rect.width}x{window_rect.height})"
            else:
                window_info = "✅ Connected to game window"
            self.update_status(window_info)
            
            # Update connection indicator
            if hasattr(self, 'connection_indicator'):
                self.connection_indicator.config(fg=self.colors['success'])
                self.connection_text.config(text="Connected", fg=self.colors['success'])
            if hasattr(self, 'mini_connection_indicator'):
                self.mini_connection_indicator.config(fg=self.colors['success'])
                self.mini_connection_text.config(text="Connected", fg=self.colors['success'])
        else:
            self.update_status("⚠️ Game not found - make sure the game is running")
            if hasattr(self, 'connection_indicator'):
                self.connection_indicator.config(fg=self.colors['danger'])
                self.connection_text.config(text="Disconnected", fg=self.colors['danger'])
            if hasattr(self, 'mini_connection_indicator'):
                self.mini_connection_indicator.config(fg=self.colors['danger'])
                self.mini_connection_text.config(text="Disconnected", fg=self.colors['danger'])

    def update_status(self, message):
        """Update the status display with timestamp"""
        formatted_message = str(message)

        def ui_update():
            self.status_var.set(formatted_message)
            try:
                print(f"Status: {formatted_message}")
            except UnicodeEncodeError:
                try:
                    print(f"Status: {formatted_message.encode('ascii', 'replace').decode('ascii')}")
                except Exception:
                    pass
            active_tool = self.bot_core.active_tool()
            if active_tool:
                started_at = self.bot_core._started_at
                elapsed = max(0, time.time() - started_at) if started_at else 0
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                stats_text = f"⏱️ Running: {minutes}m {seconds}s | Tool: {active_tool}"
                self.stats_text.set(stats_text)
            else:
                self.stats_text.set("Ready to start automation")

        if threading.current_thread() is threading.main_thread():
            ui_update()
        else:
            self.root.after(0, ui_update)

    def set_running_tool(self, tool_name, automation=None):
        """Set which tool is currently running (mutual exclusion)"""
        return self.bot_core.begin_run(tool_name, automation=automation)

    def clear_running_tool(self):
        """Clear the currently running tool"""
        self.bot_core.end_run()

    def emergency_stop(self):
        """Emergency stop triggered by ESC key"""
        # Always stop Image Clicker (it runs independently of BotCore)
        if hasattr(self, 'image_clicker_tab'):
            self.image_clicker_tab.emergency_stop()

        if self.bot_core.is_busy():
            self.update_status("🚨 EMERGENCY STOP - stopping active automation")
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

            self.bot_core.emergency_stop()
            self.clear_running_tool()

            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.attributes('-topmost', False)

    def on_closing(self):
        """Clean up when closing the application"""
        if hasattr(self, 'image_clicker_tab'):
            self.image_clicker_tab.cleanup()
        self.bot_core.emergency_stop()
        keyboard.unhook_all()  # Remove all keyboard hooks
        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()

    # --- Mini Mode Layout and Switching Logic ---
    def create_mini_ui(self):
        """Create the compact Mini Mode UI frame"""
        if self.mini_frame is not None:
            return
        
        self.mini_frame = tk.Frame(self.root, bg=self.colors['bg'])
        
        # Inner container for spacing
        mini_container = tk.Frame(self.mini_frame, bg=self.colors['bg'])
        mini_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- Row 1: Header (Title, Connection, standard mode toggle) ---
        header_row = tk.Frame(mini_container, bg=self.colors['bg'])
        header_row.pack(fill=tk.X, pady=(0, 6))
        
        mini_title = tk.Label(header_row, 
                              text="🐱 CABAL Mini", 
                              font=('Segoe UI', 10, 'bold'),
                              bg=self.colors['bg'],
                              fg=self.colors['primary'])
        mini_title.pack(side=tk.LEFT)
        
        # Mini Connection status
        self.mini_connection_indicator = tk.Label(header_row, 
                                             text="●", 
                                             font=("Arial", 12),
                                             bg=self.colors['bg'],
                                             fg='#9E9E9E')
        self.mini_connection_indicator.pack(side=tk.LEFT, padx=(8, 2))
        
        self.mini_connection_text = tk.Label(header_row,
                                        text="Checking...",
                                        font=('Segoe UI', 8, 'bold'),
                                        bg=self.colors['bg'],
                                        fg=self.colors['text_light'])
        self.mini_connection_text.pack(side=tk.LEFT)
        
        # Standard mode button
        self.standard_mode_btn = tk.Button(header_row, 
                                           text="🗖 Standard Mode",
                                           font=('Segoe UI', 7, 'bold'),
                                           bg=self.colors['light'],
                                           fg=self.colors['dark'],
                                           relief='flat',
                                           padx=6,
                                           pady=2,
                                           cursor='hand2',
                                           activebackground=self.colors['light'],
                                           activeforeground=self.colors['dark'],
                                           command=self.switch_to_standard_mode)
        self.standard_mode_btn.pack(side=tk.RIGHT)
        
        # --- Row 2: Status & Stats Card ---
        card_frame = tk.Frame(mini_container, bg=self.colors['card_bg'], relief='flat', bd=0)
        card_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # Add thin border to match cards
        border_frame = tk.Frame(card_frame, bg=self.colors['border'], height=1)
        border_frame.pack(fill=tk.X)
        
        status_inner = tk.Frame(card_frame, bg=self.colors['card_bg'], padx=8, pady=6)
        status_inner.pack(fill=tk.BOTH, expand=True)
        
        # Compact Status display
        status_line = tk.Frame(status_inner, bg=self.colors['card_bg'])
        status_line.pack(fill=tk.X)
        
        tk.Label(status_line, 
                 text="Status:", 
                 font=('Segoe UI', 8, 'bold'),
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_light']).pack(side=tk.LEFT)
        
        self.mini_status_lbl = tk.Label(status_line, 
                                       textvariable=self.status_var,
                                       font=('Segoe UI', 8),
                                       bg=self.colors['card_bg'],
                                       fg=self.colors['info'],
                                       anchor='w',
                                       justify='left')
        self.mini_status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Compact Stats display
        stats_line = tk.Frame(status_inner, bg=self.colors['card_bg'])
        stats_line.pack(fill=tk.X, pady=(4, 0))
        
        tk.Label(stats_line, 
                 text="Stats:", 
                 font=('Segoe UI', 8, 'bold'),
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_light']).pack(side=tk.LEFT)
        
        self.mini_stats_lbl = tk.Label(stats_line, 
                                      textvariable=self.stats_text,
                                      font=('Segoe UI', 8),
                                      bg=self.colors['card_bg'],
                                      fg=self.colors['text'],
                                      anchor='w',
                                      justify='left')
        self.mini_stats_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # --- Row 3: Action Buttons (Emergency Stop, On Top) ---
        actions_row = tk.Frame(mini_container, bg=self.colors['bg'])
        actions_row.pack(fill=tk.X)
        
        # Mini On Top button
        self.mini_topmost_btn = tk.Button(actions_row, 
                                          text="📌 On Top: ON",
                                          font=('Segoe UI', 7, 'bold'),
                                          bg=self.colors['primary'],
                                          fg='white',
                                          relief='flat',
                                          padx=8,
                                          pady=2,
                                          cursor='hand2',
                                          activebackground=self.colors['primary'],
                                          activeforeground='white',
                                          command=self.toggle_always_on_top)
        self.mini_topmost_btn.pack(side=tk.LEFT)
        
        # Mini Emergency Stop button (Big Red)
        self.mini_stop_btn = tk.Button(actions_row, 
                                       text="🛑 Emergency Stop (ESC)",
                                       font=('Segoe UI', 8, 'bold'),
                                       bg=self.colors['danger'],
                                       fg='white',
                                       relief='flat',
                                       padx=12,
                                       pady=2,
                                       cursor='hand2',
                                       activebackground=self.colors['danger'],
                                       activeforeground='white',
                                       command=self.emergency_stop)
        self.mini_stop_btn.pack(side=tk.RIGHT)

    def switch_to_mini_mode(self):
        """Switch the window layout to compact Mini Mode"""
        # Save standard geometry
        self.normal_geometry = self.root.geometry()
        
        # Hide standard interface
        self.main_frame.pack_forget()
        
        # Create mini UI if not exists
        if self.mini_frame is None:
            self.create_mini_ui()
            # Sync topmost state of the button
            is_topmost = self.root.attributes("-topmost")
            self.update_topmost_button_ui(is_topmost)
            # Apply current theme to new mini UI widgets
            self.apply_theme_to_widget(self.mini_frame, self.theme_var.get())
        
        # Show mini UI
        self.mini_frame.pack(fill=tk.BOTH, expand=True)
        
        # Adjust window constraints
        self.root.minsize(380, 160)
        self.root.geometry("380x160")
        
        # Trigger game connector connection check to populate mini connection status
        self.auto_connect_to_game()

    def switch_to_standard_mode(self):
        """Switch the window layout back to Standard Mode"""
        # Hide mini interface
        if self.mini_frame:
            self.mini_frame.pack_forget()
            
        # Show standard interface
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        # Restore window constraints
        self.root.minsize(700, 800)
        self.root.geometry(self.normal_geometry)
        
        # Trigger game connector connection check to populate standard connection status
        self.auto_connect_to_game()
