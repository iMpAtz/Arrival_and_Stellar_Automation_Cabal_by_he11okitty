# Main tabbed window for the Unified Game Automation Tool
# Title: "Stellar and Arrival Skill Automation"

import tkinter as tk
from tkinter import ttk, scrolledtext
import keyboard
import time
from datetime import datetime
from PIL import Image, ImageTk
import os
from core.game_connector import GameConnector
from core.ocr_engine import OCREngine
from ui.stellar_tab import StellarTab
from ui.arrival_tab import ArrivalTab
from ui.heil_tab import HeilTab

class MainWindow:
    def __init__(self):
        """Initialize the main tabbed window"""
        self.root = tk.Tk()
        self.root.title("CABAL Automation Tool - v3.0 By Hello Kitty Gang (Not for selling)")
        self.root.geometry("700x600")
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)
        self.root.minsize(700, 800)
        # Set background color
        self.root.configure(bg='#f0f0f0')

        # Set window icon using Hello Kitty image
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'images_5.jpg')
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, icon_photo)
        except Exception as e:
            print(f"Could not set window icon: {e}")

        # Track which tool is currently running (mutual exclusion)
        self.current_running_tool = None
        self.start_time = None
        self.iteration_count = 0

        # Initialize status variable first
        self.status_var = tk.StringVar(value="Initializing...")
        
        # Statistics variables
        self.stats_text = tk.StringVar(value="Ready")

        # Configure ttk style
        self.setup_styles()

        # Shared components (after status_var is created)
        self.game_connector = GameConnector(self.update_status)
        self.ocr_engine = OCREngine(self.update_status)

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
        
        # Modern color scheme
        self.colors = {
            'primary': '#2196F3',      # Blue
            'success': '#4CAF50',      # Green
            'danger': '#f44336',       # Red
            'warning': '#FF9800',      # Orange
            'info': '#00BCD4',         # Cyan
            'dark': '#263238',         # Dark Blue Gray
            'light': '#ECEFF1',        # Light Gray
            'bg': '#FAFAFA',           # Background
            'text': '#212121',         # Text
            'text_light': '#757575'    # Light Text
        }
        
        # Configure notebook (tabs)
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', 
                       padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'),
                       background=self.colors['light'])
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['primary'])],
                 foreground=[('selected', 'white'), ('!selected', self.colors['text'])])
        
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
        style.configure('Card.TFrame', background='white', relief='flat', borderwidth=1)
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
                       background='white',
                       foreground=self.colors['info'])
        
        style.configure('Heading.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       background='white',
                       foreground=self.colors['dark'])
        
        # LabelFrame style
        style.configure('Card.TLabelframe', 
                       background='white',
                       relief='flat',
                       borderwidth=2,
                       padding=15)
        style.configure('Card.TLabelframe.Label',
                       font=('Segoe UI', 11, 'bold'),
                       background='white',
                       foreground=self.colors['dark'])

    def create_ui(self):
        """Create the main UI with tabs"""
        # Main frame with modern styling
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Header section
        self.create_header(main_frame)

        # Auto-connect to game and show status
        self.auto_connect_to_game()

        # Create notebook for tabs with modern styling
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # Create tab frames with card styling
        arrival_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        stellar_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)
        heil_frame = tk.Frame(self.notebook, bg='white', padx=10, pady=10)

        # Add tabs to notebook with emoji icons
        self.notebook.add(arrival_frame, text="  ⚔️  Arrival Skill  ")
        self.notebook.add(stellar_frame, text="  ⭐  Stellar System  ")
        self.notebook.add(heil_frame, text="  🎯  Heil Auto  ")

        # Create tab instances
        self.arrival_tab = ArrivalTab(arrival_frame, self)
        self.stellar_tab = StellarTab(stellar_frame, self)
        self.heil_tab = HeilTab(heil_frame, self)

        # Status and Log section
        self.create_status_section(main_frame)

        # Footer section
        self.create_footer(main_frame)

    def create_header(self, parent):
        """Create header section with connection info"""
        # Header card
        header_card = tk.Frame(parent, bg='white', relief='flat', bd=0)
        header_card.pack(fill=tk.X, pady=(0, 10))
        
        # Add shadow effect with frame
        shadow_frame = tk.Frame(parent, bg='#e0e0e0', height=2)
        shadow_frame.place(in_=header_card, relx=0, rely=1, relwidth=1)
        
        # Inner padding frame
        header_inner = tk.Frame(header_card, bg='white')
        header_inner.pack(fill=tk.X, padx=12, pady=8)
        
        # Title section
        title_frame = tk.Frame(header_inner, bg='white')
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Try to load Hello Kitty image
        try:
            # Look for image at data/images_5.jpg
            img_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'images_5.jpg')
            
            if os.path.exists(img_path):
                # Load and resize image
                img = Image.open(img_path)
                img = img.resize((30, 30), Image.Resampling.LANCZOS)
                self.hello_kitty_photo = ImageTk.PhotoImage(img)
                
                # Add image label
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
                                text="v3.0",
                                font=('Segoe UI', 8, 'bold'),
                                bg=self.colors['primary'],
                                fg='white',
                                padx=6,
                                pady=1)
        version_badge.pack(side=tk.LEFT, padx=(8, 0))
        
        # Connection status section
        status_frame = tk.Frame(header_inner, bg='white')
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
                fg=self.colors['text_light'],
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
        else:
            self.update_status("⚠️ Game not found - make sure the game is running")
            if hasattr(self, 'connection_indicator'):
                self.connection_indicator.config(fg=self.colors['danger'])
                self.connection_text.config(text="Disconnected", fg=self.colors['danger'])

    def update_status(self, message):
        """Update the status display with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.status_var.set(formatted_message)
        print(f"Status: {formatted_message}")  # Also print to console for debugging
        
        # Update statistics if automation is running
        if self.current_running_tool and self.start_time:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            stats_text = f"⏱️ Running: {minutes}m {seconds}s | Tool: {self.current_running_tool}"
            self.stats_text.set(stats_text)
        elif not self.current_running_tool:
            self.stats_text.set("Ready to start automation")

    def set_running_tool(self, tool_name):
        """Set which tool is currently running (mutual exclusion)"""
        if self.current_running_tool is not None and self.current_running_tool != tool_name:
            self.update_status(f"❌ Cannot start {tool_name}: {self.current_running_tool} is already running")
            return False

        self.current_running_tool = tool_name
        self.start_time = time.time()
        self.iteration_count = 0
        
        # Update stats display
        self.stats_text.set(f"▶️ Starting {tool_name}...")
        
        return True

    def clear_running_tool(self):
        """Clear the currently running tool"""
        if self.current_running_tool and self.start_time:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            final_stats = f"⏹️ Stopped {self.current_running_tool} | Total time: {minutes}m {seconds}s"
            self.stats_text.set(final_stats)
        
        self.current_running_tool = None
        self.start_time = None

    def emergency_stop(self):
        """Emergency stop triggered by ESC key"""
        if self.current_running_tool:
            self.update_status(f"🚨 EMERGENCY STOP - {self.current_running_tool} stopped!")

            # Stop whichever tool is running
            if self.current_running_tool == "Stellar System":
                self.stellar_tab.emergency_stop()
            elif self.current_running_tool == "Arrival Skill":
                self.arrival_tab.emergency_stop()
            elif self.current_running_tool == "Heil Auto":
                self.heil_tab.emergency_stop()

            self.clear_running_tool()

            # Bring window to front
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.attributes('-topmost', False)

    def on_closing(self):
        """Clean up when closing the application"""
        keyboard.unhook_all()  # Remove all keyboard hooks
        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()
