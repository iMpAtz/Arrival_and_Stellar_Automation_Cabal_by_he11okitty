# Arrival Skill tab UI
# Ported from arrival_skill_ocr/ui.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import mouse
import re
from data.arrival_data import get_offensive_skills, get_defensive_skills, get_stat_variations
from automation.arrival_automation import ArrivalAutomation
import os
from datetime import datetime
import sys

class ArrivalTab:
    def __init__(self, parent_frame, main_window):
        """Initialize the Arrival Skill tab"""
        self.parent_frame = parent_frame
        self.main_window = main_window

        # Automation components
        self.automation = ArrivalAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status,
            main_window.bot_core
        )
        self.automation.set_target_found_callback(self.on_target_found)

        # UI state
        self.area = None
        self.apply_button_coords = None
        self.change_button_coords = None

        # Create UI
        self.create_ui()

    def create_ui(self):
        """Create the arrival skill UI"""
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
        
        icon_label = tk.Label(intro_inner, text="⚔️", font=('Segoe UI', 12), bg='#E3F2FD')
        icon_label.pack(side=tk.LEFT, padx=(0, 6))
        
        text_frame = tk.Frame(intro_inner, bg='#E3F2FD')
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title = tk.Label(text_frame, text="ARRIVAL SKILL - OCR Stat Reroll", 
                        font=('Segoe UI', 9, 'bold'), bg='#E3F2FD', fg=colors['text'], anchor='w')
        title.pack(fill=tk.X)
        
        instructions = (
            "1) Set Buttons  •  2) Define Area  •  3) Select Stats  •  4) Start"
        )
        subtitle = tk.Label(text_frame, text=instructions, 
                           font=('Segoe UI', 7), bg='#E3F2FD', fg=colors['text_light'], anchor='w')
        subtitle.pack(fill=tk.X, pady=(1, 0))

        # Button coordinates section
        coord_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        coord_card.pack(fill=tk.X, padx=0, pady=(0, 5))
        
        coord_header = tk.Frame(coord_card, bg=colors['primary'], height=28)
        coord_header.pack(fill=tk.X)
        tk.Label(coord_header, text="📍 Button Coordinates", 
                font=('Segoe UI', 8, 'bold'), bg=colors['primary'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        coord_body = tk.Frame(coord_card, bg='white')
        coord_body.pack(fill=tk.X, padx=10, pady=5)

        # Apply button
        apply_frame = tk.Frame(coord_body, bg='white')
        apply_frame.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(apply_frame, text="Apply:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.apply_coord_var = tk.StringVar(value="Not set")
        apply_value = tk.Label(apply_frame, textvariable=self.apply_coord_var, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        apply_value.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        apply_btn = tk.Button(apply_frame, text="Set", 
                             font=('Segoe UI', 7, 'bold'),
                             bg=colors['primary'], fg='white', 
                             relief='flat', padx=10, pady=3,
                             cursor='hand2', command=self.set_apply_button)
        apply_btn.pack(side=tk.RIGHT)

        # Change button
        change_frame = tk.Frame(coord_body, bg='white')
        change_frame.pack(fill=tk.X)
        
        tk.Label(change_frame, text="Change:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.change_coord_var = tk.StringVar(value="Not set")
        change_value = tk.Label(change_frame, textvariable=self.change_coord_var, 
                               font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        change_value.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        change_btn = tk.Button(change_frame, text="Set", 
                              font=('Segoe UI', 7, 'bold'),
                              bg=colors['primary'], fg='white', 
                              relief='flat', padx=10, pady=3,
                              cursor='hand2', command=self.set_change_button)
        change_btn.pack(side=tk.RIGHT)

        # OCR Area
        area_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        area_card.pack(fill=tk.X, padx=0, pady=(0, 5))
        
        area_body = tk.Frame(area_card, bg='white')
        area_body.pack(fill=tk.X, padx=10, pady=4)
        
        self.btn_define_area = tk.Button(area_body, text="📐 Define OCR Area", 
                                         font=('Segoe UI', 8, 'bold'),
                                         bg='#FF9800', fg='white',
                                         relief='flat', padx=20, pady=6,
                                         cursor='hand2', command=self.define_area)
        self.btn_define_area.pack()

        # Stat selection section
        stats_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        stats_card.pack(fill=tk.X, padx=0, pady=(0, 5))
        
        stats_header = tk.Frame(stats_card, bg=colors['success'], height=28)
        stats_header.pack(fill=tk.X)
        tk.Label(stats_header, text="⚙️ Desired Stats", 
                font=('Segoe UI', 8, 'bold'), bg=colors['success'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        stats_body = tk.Frame(stats_card, bg='white')
        stats_body.pack(fill=tk.X, padx=10, pady=5)

        # Offensive stat 1
        off_frame = tk.Frame(stats_body, bg='white')
        off_frame.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(off_frame, text="Offensive:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.off_stat = tk.StringVar()
        offensive_skills = [""] + get_offensive_skills()
        self.off_stat_dropdown = ttk.Combobox(off_frame, textvariable=self.off_stat, 
                                             values=offensive_skills, state="readonly", width=16, font=('Segoe UI', 7))
        self.off_stat_dropdown.pack(side=tk.LEFT, padx=(5, 6))
        self.off_stat_dropdown.bind("<<ComboboxSelected>>", self.update_off_variations)
        
        tk.Label(off_frame, text="Min:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text']).pack(side=tk.LEFT, padx=(3, 3))
        
        self.off_var = tk.StringVar()
        self.off_var_dropdown = ttk.Combobox(off_frame, textvariable=self.off_var, 
                                            state="readonly", width=7, font=('Segoe UI', 7))
        self.off_var_dropdown.pack(side=tk.LEFT)

        # Offensive stat 2
        off_frame2 = tk.Frame(stats_body, bg='white')
        off_frame2.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(off_frame2, text="Offensive 2:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.off_stat2 = tk.StringVar()
        self.off_stat2_dropdown = ttk.Combobox(off_frame2, textvariable=self.off_stat2, 
                                              values=offensive_skills, state="readonly", width=16, font=('Segoe UI', 7))
        self.off_stat2_dropdown.pack(side=tk.LEFT, padx=(5, 6))
        self.off_stat2_dropdown.bind("<<ComboboxSelected>>", self.update_off2_variations)
        
        tk.Label(off_frame2, text="Min:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text']).pack(side=tk.LEFT, padx=(3, 3))
        
        self.off_var2 = tk.StringVar()
        self.off_var2_dropdown = ttk.Combobox(off_frame2, textvariable=self.off_var2, 
                                             state="readonly", width=7, font=('Segoe UI', 7))
        self.off_var2_dropdown.pack(side=tk.LEFT)

        # Offensive stat 3
        off_frame3 = tk.Frame(stats_body, bg='white')
        off_frame3.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(off_frame3, text="Offensive 3:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.off_stat3 = tk.StringVar()
        self.off_stat3_dropdown = ttk.Combobox(off_frame3, textvariable=self.off_stat3, 
                                              values=offensive_skills, state="readonly", width=16, font=('Segoe UI', 7))
        self.off_stat3_dropdown.pack(side=tk.LEFT, padx=(5, 6))
        self.off_stat3_dropdown.bind("<<ComboboxSelected>>", self.update_off3_variations)
        
        tk.Label(off_frame3, text="Min:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text']).pack(side=tk.LEFT, padx=(3, 3))
        
        self.off_var3 = tk.StringVar()
        self.off_var3_dropdown = ttk.Combobox(off_frame3, textvariable=self.off_var3, 
                                             state="readonly", width=7, font=('Segoe UI', 7))
        self.off_var3_dropdown.pack(side=tk.LEFT)

        # Defensive stat 1
        def_frame = tk.Frame(stats_body, bg='white')
        def_frame.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(def_frame, text="Defensive:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.def_stat = tk.StringVar()
        defensive_skills = [""] + get_defensive_skills()
        self.def_stat_dropdown = ttk.Combobox(def_frame, textvariable=self.def_stat, 
                                             values=defensive_skills, state="readonly", width=16, font=('Segoe UI', 7))
        self.def_stat_dropdown.pack(side=tk.LEFT, padx=(5, 6))
        self.def_stat_dropdown.bind("<<ComboboxSelected>>", self.update_def_variations)
        
        tk.Label(def_frame, text="Min:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text']).pack(side=tk.LEFT, padx=(3, 3))
        
        self.def_var = tk.StringVar()
        self.def_var_dropdown = ttk.Combobox(def_frame, textvariable=self.def_var, 
                                            state="readonly", width=7, font=('Segoe UI', 7))
        self.def_var_dropdown.pack(side=tk.LEFT)

        # Defensive stat 2
        def_frame2 = tk.Frame(stats_body, bg='white')
        def_frame2.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(def_frame2, text="Defensive 2:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.def_stat2 = tk.StringVar()
        self.def_stat2_dropdown = ttk.Combobox(def_frame2, textvariable=self.def_stat2, 
                                              values=defensive_skills, state="readonly", width=16, font=('Segoe UI', 7))
        self.def_stat2_dropdown.pack(side=tk.LEFT, padx=(5, 6))
        self.def_stat2_dropdown.bind("<<ComboboxSelected>>", self.update_def2_variations)
        
        tk.Label(def_frame2, text="Min:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text']).pack(side=tk.LEFT, padx=(3, 3))
        
        self.def_var2 = tk.StringVar()
        self.def_var2_dropdown = ttk.Combobox(def_frame2, textvariable=self.def_var2, 
                                             state="readonly", width=7, font=('Segoe UI', 7))
        self.def_var2_dropdown.pack(side=tk.LEFT)

        # Delay setting
        delay_frame = tk.Frame(stats_body, bg='white')
        delay_frame.pack(fill=tk.X)
        
        tk.Label(delay_frame, text="Delay (ms):", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.delay_var = tk.StringVar(value="1000")
        self.delay_entry = tk.Entry(delay_frame, textvariable=self.delay_var, 
                                    font=('Segoe UI', 8), width=10, relief='solid', bd=1)
        self.delay_entry.pack(side=tk.LEFT, padx=(5, 6))
        
        tk.Label(delay_frame, text="(between actions)", 
                font=('Segoe UI', 7), bg='white', fg=colors['text_light']).pack(side=tk.LEFT)

        # Control buttons
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

    def set_apply_button(self):
        """Set the apply button coordinates"""
        # Connect to game if needed
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            "Click on the 'Apply' button in the game window.\n"
            "The coordinates will be captured automatically."
        )

        # Change cursor to indicate click mode
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            """Capture the mouse click coordinates"""
            try:
                # Wait for mouse click (exactly as in main.py)
                mouse.wait(button='left')
                x, y = mouse.get_position()

                # Convert to window-relative coordinates
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                if success:
                    self.apply_button_coords = (rel_x, rel_y)
                    self.automation.set_apply_button(self.apply_button_coords)
                    self.apply_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Apply button set at ({rel_x}, {rel_y})")
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                # Reset cursor
                self.main_window.root.config(cursor="")

        # Start capture in thread
        threading.Thread(target=capture_click, daemon=True).start()

    def set_change_button(self):
        """Set the change button coordinates"""
        # Connect to game if needed
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            "Click on the 'Change' button in the game window.\n"
            "The coordinates will be captured automatically."
        )

        # Change cursor to indicate click mode
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            """Capture the mouse click coordinates"""
            try:
                # Wait for mouse click (exactly as in main.py)
                mouse.wait(button='left')
                x, y = mouse.get_position()

                # Convert to window-relative coordinates
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                if success:
                    self.change_button_coords = (rel_x, rel_y)
                    self.automation.set_change_button(self.change_button_coords)
                    self.change_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Change button set at ({rel_x}, {rel_y})")
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                # Reset cursor
                self.main_window.root.config(cursor="")

        # Start capture in thread
        threading.Thread(target=capture_click, daemon=True).start()

    def define_area(self):
        """Define the OCR area using the shared area selector"""
        def area_callback(area):
            """Callback when area is selected"""
            self.area = area
            self.automation.set_area(area)
            self.btn_start.config(state=tk.NORMAL)
            self.main_window.update_status(f"OCR area defined: {area}")

        # Use the shared area selector
        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback

        self.main_window.area_selector.select_area()

    def update_off_variations(self, event=None):
        """Update the offensive stat variations dropdown based on selected stat"""
        selected_stat = self.off_stat.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.off_var_dropdown['values'] = variations
            if variations:
                self.off_var.set(variations[0])  # Select first variation by default
        else:
            self.off_var_dropdown['values'] = []
            self.off_var.set("")

    def update_off2_variations(self, event=None):
        """Update the offensive stat 2 variations dropdown based on selected stat"""
        selected_stat = self.off_stat2.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.off_var2_dropdown['values'] = variations
            if variations:
                self.off_var2.set(variations[0])  # Select first variation by default
        else:
            self.off_var2_dropdown['values'] = []
            self.off_var2.set("")

    def update_off3_variations(self, event=None):
        """Update the offensive stat 3 variations dropdown based on selected stat"""
        selected_stat = self.off_stat3.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.off_var3_dropdown['values'] = variations
            if variations:
                self.off_var3.set(variations[0])  # Select first variation by default
        else:
            self.off_var3_dropdown['values'] = []
            self.off_var3.set("")

    def update_def_variations(self, event=None):
        """Update the defensive stat variations dropdown based on selected stat"""
        selected_stat = self.def_stat.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.def_var_dropdown['values'] = variations
            if variations:
                self.def_var.set(variations[0])  # Select first variation by default
        else:
            self.def_var_dropdown['values'] = []
            self.def_var.set("")

    def update_def2_variations(self, event=None):
        """Update the defensive stat 2 variations dropdown based on selected stat"""
        selected_stat = self.def_stat2.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.def_var2_dropdown['values'] = variations
            if variations:
                self.def_var2.set(variations[0])  # Select first variation by default
        else:
            self.def_var2_dropdown['values'] = []
            self.def_var2.set("")

    def start_automation(self):
        """Start the arrival skill automation"""
        # Check if another tool is running
        if not self.main_window.set_running_tool("Arrival Skill"):
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

        # Check if at least one stat is specified
        if not self.off_stat.get() and not self.off_stat2.get() and not self.off_stat3.get() and not self.def_stat.get() and not self.def_stat2.get():
            messagebox.showerror("Error", "Please specify at least one stat to look for.")
            self.main_window.clear_running_tool()
            return

        # Prepare desired stats
        desired_stats = {
            'offensive': [],
            'defensive': []
        }

        # Add offensive stat 1 if specified
        stat_name = self.off_stat.get()
        if stat_name:
            variation = self.off_var.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return

            # Extract numeric value from the variation
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                off_val = int(value_match.group(1))
                desired_stats['offensive'].append((stat_name, off_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} with minimum value {variation}")

        # Add offensive stat 2 if specified
        stat_name = self.off_stat2.get()
        if stat_name:
            variation = self.off_var2.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return

            # Extract numeric value from the variation
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                off_val = int(value_match.group(1))
                desired_stats['offensive'].append((stat_name, off_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} (option 2) with minimum value {variation}")

        # Add offensive stat 3 if specified
        stat_name = self.off_stat3.get()
        if stat_name:
            variation = self.off_var3.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return

            # Extract numeric value from the variation
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                off_val = int(value_match.group(1))
                desired_stats['offensive'].append((stat_name, off_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} (option 3) with minimum value {variation}")

        # Add defensive stat 1 if specified
        stat_name = self.def_stat.get()
        if stat_name:
            variation = self.def_var.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return

            # Extract numeric value from the variation
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                def_val = int(value_match.group(1))
                desired_stats['defensive'].append((stat_name, def_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} with minimum value {variation}")

        # Add defensive stat 2 if specified
        stat_name = self.def_stat2.get()
        if stat_name:
            variation = self.def_var2.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return

            # Extract numeric value from the variation
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                def_val = int(value_match.group(1))
                desired_stats['defensive'].append((stat_name, def_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} (option 2) with minimum value {variation}")

        # Set the delay in automation
        self.automation.set_delay(delay_ms)

        # Start automation
        if self.automation.start(desired_stats):
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.main_window.update_status("Arrival skill automation started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        """Stop the arrival skill automation"""
        self.automation.stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.clear_running_tool()
        self.main_window.update_status("Arrival skill automation stopped")
        self.generate_summary("stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        self.automation.emergency_stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.clear_running_tool()

    def on_target_found(self):
        """Called when target stat is found"""
        self.generate_summary("target_found")

    def generate_summary(self, reason):
        """Generate and save summary to file"""
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"arrival_summary_{timestamp}.txt"
            
            # Create summaries directory if it doesn't exist
            summaries_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'summaries')
            os.makedirs(summaries_dir, exist_ok=True)
            
            filepath = os.path.join(summaries_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("ARRIVAL SKILL AUTOMATION SUMMARY\n")
                f.write("=" * 40 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Reason: {reason}\n")
                
                # Desired stats
                offensive_stats = []
                defensive_stats = []
                
                if self.off_stat.get():
                    offensive_stats.append(f"{self.off_stat.get()} (Min: {self.off_var.get()})")
                if self.off_stat2.get():
                    offensive_stats.append(f"{self.off_stat2.get()} (Min: {self.off_var2.get()})")
                if self.off_stat3.get():
                    offensive_stats.append(f"{self.off_stat3.get()} (Min: {self.off_var3.get()})")
                if self.def_stat.get():
                    defensive_stats.append(f"{self.def_stat.get()} (Min: {self.def_var.get()})")
                if self.def_stat2.get():
                    defensive_stats.append(f"{self.def_stat2.get()} (Min: {self.def_var2.get()})")
                
                f.write(f"Desired Offensive Stats: {', '.join(offensive_stats) if offensive_stats else 'None'}\n")
                f.write(f"Desired Defensive Stats: {', '.join(defensive_stats) if defensive_stats else 'None'}\n")
                f.write(f"Delay: {self.delay_var.get()}ms\n")
                
                # Stats counter data
                total_rolls = sum(self.automation.stat_counter.values())
                if total_rolls > 0:
                    f.write("\nSTATISTICS ENCOUNTERED:\n")
                    for stat_key, count in sorted(self.automation.stat_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_rolls) * 100
                        f.write(f"  {stat_key}: {count} times ({percentage:.1f}%)\n")
                
                # Unmapped OCR data
                if self.automation.unmapped_ocr_counter:
                    f.write("\nUNMAPPED OCR DETECTIONS:\n")
                    for unmapped_key, count in sorted(self.automation.unmapped_ocr_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_rolls) * 100 if total_rolls > 0 else 0
                        f.write(f"  {unmapped_key}: {count} times ({percentage:.1f}%)\n")
                
                f.write("\nAutomation completed.\n")
            
            self.main_window.update_status(f"Summary saved to: {filename}")
            
        except Exception as e:
            self.main_window.update_status(f"Failed to save summary: {str(e)}")
