# Heil Auto tab UI
# Simple auto-click automation without OCR

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import mouse
from automation.heil_automation import HeilAutomation

class HeilTab:
    def __init__(self, parent_frame, main_window):
        """Initialize the Heil Auto tab"""
        self.parent_frame = parent_frame
        self.main_window = main_window

        # Automation components (no OCR needed)
        self.automation = HeilAutomation(
            main_window.game_connector,
            main_window.update_status
        )

        # UI state
        self.click_coords = None

        # Create UI
        self.create_ui()

    def create_ui(self):
        """Create the Heil Auto UI"""
        # Get colors from main window
        colors = self.main_window.colors if hasattr(self.main_window, 'colors') else {
            'primary': '#2196F3', 'success': '#4CAF50', 'danger': '#f44336',
            'text': '#212121', 'text_light': '#757575'
        }
        
        # Main container
        main_frame = tk.Frame(self.parent_frame, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instructions card
        intro_card = tk.Frame(main_frame, bg='#E3F2FD', relief='flat', bd=0)
        intro_card.pack(fill=tk.X, padx=0, pady=(0, 6))
        
        intro_inner = tk.Frame(intro_card, bg='#E3F2FD')
        intro_inner.pack(fill=tk.X, padx=10, pady=6)
        
        icon_label = tk.Label(intro_inner, text="🎯", font=('Segoe UI', 12), bg='#E3F2FD')
        icon_label.pack(side=tk.LEFT, padx=(0, 6))
        
        text_frame = tk.Frame(intro_inner, bg='#E3F2FD')
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title = tk.Label(text_frame, text="HEIL AUTO - Simple Auto-Click", 
                        font=('Segoe UI', 9, 'bold'), bg='#E3F2FD', fg=colors['text'], anchor='w')
        title.pack(fill=tk.X)
        
        instructions = (
            "1) Set Position  •  2) Set Delay  •  3) Start"
        )
        subtitle = tk.Label(text_frame, text=instructions, 
                           font=('Segoe UI', 7), bg='#E3F2FD', fg=colors['text_light'], anchor='w')
        subtitle.pack(fill=tk.X, pady=(1, 0))

        # Click position section
        coord_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        coord_card.pack(fill=tk.X, padx=0, pady=(0, 6))
        
        coord_header = tk.Frame(coord_card, bg=colors['primary'], height=28)
        coord_header.pack(fill=tk.X)
        tk.Label(coord_header, text="📍 Click Position", 
                font=('Segoe UI', 8, 'bold'), bg=colors['primary'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        coord_body = tk.Frame(coord_card, bg='white')
        coord_body.pack(fill=tk.X, padx=10, pady=6)
        
        coord_row = tk.Frame(coord_body, bg='white')
        coord_row.pack(fill=tk.X)
        
        tk.Label(coord_row, text="Position:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.click_coord_var = tk.StringVar(value="Not set")
        coord_value = tk.Label(coord_row, textvariable=self.click_coord_var, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        coord_value.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        set_btn = tk.Button(coord_row, text="Set Position", 
                           font=('Segoe UI', 8, 'bold'),
                           bg=colors['primary'], fg='white', 
                           relief='flat', padx=12, pady=4,
                           cursor='hand2', command=self.set_click_position)
        set_btn.pack(side=tk.RIGHT)

        # Delay settings section
        delay_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        delay_card.pack(fill=tk.X, padx=0, pady=(0, 6))
        
        delay_header = tk.Frame(delay_card, bg=colors['success'], height=28)
        delay_header.pack(fill=tk.X)
        tk.Label(delay_header, text="⏱️ Delay Settings", 
                font=('Segoe UI', 8, 'bold'), bg=colors['success'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        delay_body = tk.Frame(delay_card, bg='white')
        delay_body.pack(fill=tk.X, padx=10, pady=6)
        
        delay_row = tk.Frame(delay_body, bg='white')
        delay_row.pack(fill=tk.X)
        
        tk.Label(delay_row, text="Delay (ms):", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.delay_var = tk.StringVar(value="1000")
        self.delay_entry = tk.Entry(delay_row, textvariable=self.delay_var, 
                                    font=('Segoe UI', 8), width=10, relief='solid', bd=1)
        self.delay_entry.pack(side=tk.LEFT, padx=(5, 8))
        
        tk.Label(delay_row, text="(delay between clicks)", 
                font=('Segoe UI', 7), bg='white', fg=colors['text_light']).pack(side=tk.LEFT)

        # Control buttons section
        control_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        control_card.pack(fill=tk.X, padx=0, pady=(0, 0))
        
        control_body = tk.Frame(control_card, bg='white')
        control_body.pack(fill=tk.X, padx=10, pady=8)
        
        button_frame = tk.Frame(control_body, bg='white')
        button_frame.pack()
        
        self.btn_start = tk.Button(button_frame, text="▶️ START", 
                                   font=('Segoe UI', 9, 'bold'),
                                   bg=colors['success'], fg='white',
                                   relief='flat', padx=30, pady=8,
                                   cursor='hand2', state=tk.DISABLED,
                                   command=self.start_automation)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 6))
        
        self.btn_stop = tk.Button(button_frame, text="⏹️ STOP", 
                                  font=('Segoe UI', 9, 'bold'),
                                  bg=colors['danger'], fg='white',
                                  relief='flat', padx=30, pady=8,
                                  cursor='hand2', state=tk.DISABLED,
                                  command=self.stop_automation)
        self.btn_stop.pack(side=tk.LEFT)

    def set_click_position(self):
        """Set the click position coordinates"""
        # Connect to game if needed
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            "Click on the position where you want to auto-click in the game window.\n"
            "The coordinates will be captured automatically."
        )

        # Change cursor to indicate click mode
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            """Capture the mouse click coordinates"""
            try:
                # Wait for mouse click
                mouse.wait(button='left')
                x, y = mouse.get_position()

                # Convert to window-relative coordinates
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                if success:
                    self.click_coords = (rel_x, rel_y)
                    self.automation.set_click_position(self.click_coords)
                    self.click_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Click position set at ({rel_x}, {rel_y})")
                    
                    # Enable start button
                    self.btn_start.config(state=tk.NORMAL)
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                # Reset cursor
                self.main_window.root.config(cursor="")

        # Start capture in thread
        threading.Thread(target=capture_click, daemon=True).start()

    def start_automation(self):
        """Start the Heil automation"""
        # Check if another tool is running
        if not self.main_window.set_running_tool("Heil Auto"):
            return

        # Validate delay input
        try:
            delay_ms = int(self.delay_var.get())
            if delay_ms < 0:
                raise ValueError("Delay must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return

        # Set the delay in automation
        self.automation.set_delay(delay_ms)

        # Start automation
        if self.automation.start():
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.main_window.update_status("Heil Auto started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        """Stop the Heil automation"""
        self.automation.stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.clear_running_tool()
        self.main_window.update_status("Heil Auto stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        self.automation.emergency_stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.clear_running_tool()
