# Stellar System tab UI
# Ported from main.py stellar system functionality

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import mouse
from data.stellar_data import get_stellar_options
from automation.stellar_automation import StellarAutomation
import os
from datetime import datetime
import sys

class StellarTab:
    def __init__(self, parent_frame, main_window):
        """Initialize the Stellar System tab"""
        self.parent_frame = parent_frame
        self.main_window = main_window

        # Automation components
        self.automation = StellarAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status,
            main_window.bot_core
        )
        self.automation.set_target_found_callback(self.on_target_found)

        # UI state
        self.area = None
        self.imprint_button_coords = None
        self.match_mode_var = tk.StringVar(value="single")
        self.or_rows = []

        # Create UI
        self.create_ui()

    def create_ui(self):
        """Create the stellar system UI"""
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
        
        icon_label = tk.Label(intro_inner, text="⭐", font=('Segoe UI', 12), bg='#E3F2FD')
        icon_label.pack(side=tk.LEFT, padx=(0, 6))
        
        text_frame = tk.Frame(intro_inner, bg='#E3F2FD')
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title = tk.Label(text_frame, text="STELLAR SYSTEM - Option Reroll", 
                        font=('Segoe UI', 9, 'bold'), bg='#E3F2FD', fg=colors['text'], anchor='w')
        title.pack(fill=tk.X)
        
        instructions = (
            "1) Set Imprint  •  2) Define Area  •  3) Configure  •  4) Start"
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
        
        imprint_frame = tk.Frame(coord_body, bg='white')
        imprint_frame.pack(fill=tk.X)
        
        tk.Label(imprint_frame, text="Imprint:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=9, anchor='w').pack(side=tk.LEFT)
        
        self.imprint_coord_var = tk.StringVar(value="Not set")
        imprint_value = tk.Label(imprint_frame, textvariable=self.imprint_coord_var, 
                                font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        imprint_value.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        imprint_btn = tk.Button(imprint_frame, text="Set", 
                               font=('Segoe UI', 7, 'bold'),
                               bg=colors['primary'], fg='white', 
                               relief='flat', padx=10, pady=3,
                               cursor='hand2', command=self.set_imprint_button)
        imprint_btn.pack(side=tk.RIGHT)

        # Option configuration section
        option_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        option_card.pack(fill=tk.X, padx=0, pady=(0, 5))
        
        option_header = tk.Frame(option_card, bg=colors['success'], height=28)
        option_header.pack(fill=tk.X)
        tk.Label(option_header, text="⚙️ Option Configuration", 
                font=('Segoe UI', 8, 'bold'), bg=colors['success'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        option_body = tk.Frame(option_card, bg='white')
        option_body.pack(fill=tk.X, padx=10, pady=5)

        # Match mode
        logic_frame = tk.Frame(option_body, bg='white')
        logic_frame.pack(fill=tk.X, pady=(0, 4))

        tk.Label(logic_frame, text="Match mode:", font=('Segoe UI', 8, 'bold'),
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)

        tk.Radiobutton(logic_frame, text="Single", variable=self.match_mode_var, value="single",
                       font=('Segoe UI', 8), bg='white', fg=colors['text'], selectcolor='white',
                       activebackground='white', command=self.update_match_mode).pack(side=tk.LEFT, padx=(5, 2))

        tk.Radiobutton(logic_frame, text="OR", variable=self.match_mode_var, value="or",
                       font=('Segoe UI', 8), bg='white', fg=colors['text'], selectcolor='white',
                       activebackground='white', command=self.update_match_mode).pack(side=tk.LEFT, padx=(5, 2))

        # Option name
        name_frame = tk.Frame(option_body, bg='white')
        name_frame.pack(fill=tk.X, pady=(0, 4))
        self.single_option_frame = name_frame
        
        tk.Label(name_frame, text="Option:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.combo_option_name = ttk.Combobox(name_frame, values=get_stellar_options(), 
                                             state="readonly", width=20, font=('Segoe UI', 7))
        self.combo_option_name.pack(side=tk.LEFT, padx=(5, 0))

        self.or_options_frame = tk.Frame(option_body, bg='white')
        self.or_options_frame.pack(fill=tk.X, pady=(0, 4))
        self.or_options_frame.pack_forget()

        or_header = tk.Frame(self.or_options_frame, bg='white')
        or_header.pack(fill=tk.X)
        tk.Label(or_header, text="OR stat constraints:", font=('Segoe UI', 8, 'bold'),
                bg='white', fg=colors['text']).pack(side=tk.LEFT)
        add_constraint_btn = tk.Button(or_header, text="+ Add stat",
                                      font=('Segoe UI', 8), bg=colors['primary'], fg='white',
                                      relief='flat', padx=8, pady=2, cursor='hand2',
                                      command=self.add_or_constraint_row)
        add_constraint_btn.pack(side=tk.RIGHT)

        self.or_rows_container = tk.Frame(self.or_options_frame, bg='white')
        self.or_rows_container.pack(fill=tk.X, pady=(4, 0))

        # Minimum value
        value_frame = tk.Frame(option_body, bg='white')
        value_frame.pack(fill=tk.X)
        self.single_min_frame = value_frame
        
        tk.Label(value_frame, text="Min value:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.entry_option_min_value = tk.Entry(value_frame, font=('Segoe UI', 8), 
                                               width=10, relief='solid', bd=1)
        self.entry_option_min_value.pack(side=tk.LEFT, padx=(5, 6))
        
        tk.Label(value_frame, text="(optional)", 
                font=('Segoe UI', 7), bg='white', fg=colors['text_light']).pack(side=tk.LEFT)

        # Visual effect settings section
        effect_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        effect_card.pack(fill=tk.X, padx=0, pady=(0, 5))
        
        effect_header = tk.Frame(effect_card, bg='#FF9800', height=28)
        effect_header.pack(fill=tk.X)
        tk.Label(effect_header, text="✨ Visual Effect", 
                font=('Segoe UI', 8, 'bold'), bg='#FF9800', fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        effect_body = tk.Frame(effect_card, bg='white')
        effect_body.pack(fill=tk.X, padx=10, pady=5)
        
        delay_frame = tk.Frame(effect_body, bg='white')
        delay_frame.pack(fill=tk.X)
        
        tk.Label(delay_frame, text="Clear delay:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.entry_effect_delay = tk.Entry(delay_frame, font=('Segoe UI', 8), 
                                          width=8, relief='solid', bd=1)
        self.entry_effect_delay.pack(side=tk.LEFT, padx=(5, 6))
        self.entry_effect_delay.insert(0, "1000")
        
        tk.Label(delay_frame, text="ms (wait for effects)", 
                font=('Segoe UI', 7), bg='white', fg=colors['text_light']).pack(side=tk.LEFT)

        # OCR Area
        area_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        area_card.pack(fill=tk.X, padx=0, pady=(0, 5))
        
        area_body = tk.Frame(area_card, bg='white')
        area_body.pack(fill=tk.X, padx=10, pady=4)
        
        self.btn_define_area = tk.Button(area_body, text="📐 Define OCR Area", 
                                         font=('Segoe UI', 8, 'bold'),
                                         bg='#9C27B0', fg='white',
                                         relief='flat', padx=20, pady=6,
                                         cursor='hand2', command=self.define_area)
        self.btn_define_area.pack()

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

    def set_imprint_button(self):
        """Set the imprint button coordinates"""
        # Clear any stale stop_event from prior runs so capture can work.
        self.main_window.bot_core.start()
        # Connect to game if needed
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            "Click on the 'Imprint' button in the game window.\n"
            "The coordinates will be captured automatically."
        )

        # Change cursor to indicate click mode
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            """Capture the mouse click coordinates"""
            try:
                pos = self.main_window.bot_core.wait_for_mouse_click(mouse, button='left')
                if not pos:
                    return
                x, y = pos

                # Convert to window-relative coordinates
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                if success:
                    self.imprint_button_coords = (rel_x, rel_y)
                    self.automation.set_imprint_button(self.imprint_button_coords)
                    self.imprint_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Imprint button set at ({rel_x}, {rel_y})")
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                # Reset cursor
                self.main_window.root.config(cursor="")

        # Start capture in thread
        self.main_window.bot_core.register_thread("stellar-capture-imprint", capture_click, daemon=True)

    def define_area(self):
        """Define the OCR area using the shared area selector"""
        self.main_window.bot_core.start()
        def area_callback(area):
            """Callback when area is selected"""
            self.area = area
            self.automation.set_area(area)
            self.btn_start.config(state=tk.NORMAL)
            self.main_window.update_status(f"Area defined: {area}")

        # Use the shared area selector
        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback

        self.main_window.area_selector.select_area()

    def add_or_constraint_row(self, option_name="", min_value=""):
        colors = self.main_window.colors if hasattr(self.main_window, 'colors') else {'text': '#212121'}
        row_frame = tk.Frame(self.or_rows_container, bg='white')
        row_frame.pack(fill=tk.X, pady=(0, 4))

        option_var = tk.StringVar(value=option_name)
        option_combo = ttk.Combobox(row_frame, textvariable=option_var,
                                    values=get_stellar_options(), state="readonly",
                                    width=20, font=('Segoe UI', 7))
        option_combo.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(row_frame, text="Min:", font=('Segoe UI', 8, 'bold'),
                bg='white', fg=colors['text']).pack(side=tk.LEFT, padx=(0, 4))
        min_entry = tk.Entry(row_frame, font=('Segoe UI', 8), width=8,
                             relief='solid', bd=1)
        min_entry.insert(0, min_value)
        min_entry.pack(side=tk.LEFT, padx=(0, 5))

        remove_btn = tk.Button(row_frame, text="✕", font=('Segoe UI', 8), bg='white',
                               fg=colors['text'], relief='flat', padx=4, pady=0,
                               cursor='hand2', command=lambda: self.remove_or_constraint_row(row_frame))
        remove_btn.pack(side=tk.LEFT)

        self.or_rows.append({'frame': row_frame, 'combo': option_combo, 'entry': min_entry})

    def remove_or_constraint_row(self, row_frame):
        for row in self.or_rows:
            if row['frame'] is row_frame:
                row_frame.destroy()
                self.or_rows.remove(row)
                break

    def get_selected_option_constraints(self):
        if self.match_mode_var.get() == "or":
            constraints = []
            for row in self.or_rows:
                name = row['combo'].get().strip()
                min_value = row['entry'].get().strip()
                if name:
                    constraints.append({'name': name, 'min_value': min_value})
            return constraints

        option_name = self.combo_option_name.get().strip()
        option_min_value = self.entry_option_min_value.get().strip()
        return [{'name': option_name, 'min_value': option_min_value}] if option_name else []

    def get_selected_option_names(self):
        return [constraint['name'] for constraint in self.get_selected_option_constraints()]

    def format_selected_constraints(self):
        constraints = self.get_selected_option_constraints()
        return ", ".join(
            f"{constraint['name']} ({constraint['min_value']})" if constraint['min_value'] else constraint['name']
            for constraint in constraints
        )

    def update_match_mode(self):
        if self.match_mode_var.get() == "or":
            self.single_option_frame.pack_forget()
            self.single_min_frame.pack_forget()
            self.or_options_frame.pack(fill=tk.X, pady=(0, 4))
            if not self.or_rows:
                self.add_or_constraint_row()
            self.combo_option_name.config(state=tk.DISABLED)
            self.entry_option_min_value.config(state="disabled")
        else:
            self.or_options_frame.pack_forget()
            self.single_option_frame.pack(fill=tk.X, pady=(0, 4))
            self.single_min_frame.pack(fill=tk.X)
            self.combo_option_name.config(state="readonly")
            self.entry_option_min_value.config(state="normal")

    def start_automation(self):
        """Start the stellar automation"""
        # Check if another tool is running
        if not self.main_window.set_running_tool("Stellar System", automation=self.automation):
            return

        # Get configuration
        effect_delay = self.entry_effect_delay.get().strip()
        constraints = self.get_selected_option_constraints()

        if not constraints:
            if self.match_mode_var.get() == "single":
                messagebox.showwarning("Missing Option", "Please select an option name.")
            else:
                messagebox.showwarning("Missing Options", "Please add one or more OR stat constraints.")
            self.main_window.clear_running_tool()
            return

        # Validate effect delay
        try:
            effect_delay_ms = int(effect_delay) if effect_delay else 1000
            if effect_delay_ms < 0:
                effect_delay_ms = 1000
        except ValueError:
            effect_delay_ms = 1000

        # Set the effect delay in automation
        self.automation.set_effect_delay(effect_delay_ms)

        # Start automation
        if self.automation.start(constraints):
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.main_window.update_status("Stellar automation started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        """Stop the stellar automation"""
        self.automation.stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.clear_running_tool()
        self.main_window.update_status("Stellar automation stopped")
        self.generate_summary("stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        self.automation.emergency_stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.main_window.clear_running_tool()

    def on_target_found(self):
        """Called when target option is found"""
        self.generate_summary("target_found")

    def generate_summary(self, reason):
        """Generate and save summary to file"""
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stellar_summary_{timestamp}.txt"
            
            # Create summaries directory if it doesn't exist
            summaries_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'summaries')
            os.makedirs(summaries_dir, exist_ok=True)
            
            filepath = os.path.join(summaries_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("STELLAR SYSTEM AUTOMATION SUMMARY\n")
                f.write("=" * 40 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Option(s): {self.format_selected_constraints()}\n")
                f.write(f"Effect Delay: {self.entry_effect_delay.get()}ms\n")
                f.write(f"Wrong Read Counter: {self.automation.wrong_read_counter}\n")
                
                # Calculate total attempts
                total_attempts = sum(self.automation.stat_counter.values()) + self.automation.wrong_read_counter
                if total_attempts > 0:
                    success_rate = ((total_attempts - self.automation.wrong_read_counter) / total_attempts) * 100
                    error_rate = (self.automation.wrong_read_counter / total_attempts) * 100
                    
                    f.write("\nOVERALL PERCENTAGES:\n")
                    f.write(f"Success Rate: {success_rate:.1f}%\n")
                    f.write(f"Error Rate: {error_rate:.1f}%\n")
                
                # Show detailed stats for each value found
                if self.automation.stat_counter:
                    f.write("\nDETECTED VALUES STATISTICS:\n")
                    target_value = None
                    if self.entry_option_min_value.get().isdigit():
                        target_value = int(self.entry_option_min_value.get())
                    
                    for value_str, count in sorted(self.automation.stat_counter.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True):
                        percentage = (count / total_attempts) * 100 if total_attempts > 0 else 0
                        status = ""
                        if target_value is not None and value_str.isdigit():
                            value_int = int(value_str)
                            if self.combo_option_name.get().lower() == "penetration":
                                # For penetration, check if >= target
                                if value_int >= target_value:
                                    status = " ✓ TARGET MET"
                                else:
                                    status = " ✗ BELOW TARGET"
                            else:
                                # For other options, check exact match or >=
                                if value_int >= target_value:
                                    status = " ✓ TARGET MET"
                                else:
                                    status = " ✗ BELOW TARGET"
                        
                        f.write(f"  Value {value_str}: {count} times ({percentage:.1f}%){status}\n")
                
                # Show unmapped OCR texts (other options detected)
                if self.automation.unmapped_ocr_counter:
                    f.write("\nOTHER DETECTED OPTIONS:\n")
                    for text_key, count in sorted(self.automation.unmapped_ocr_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_attempts) * 100 if total_attempts > 0 else 0
                        f.write(f"  '{text_key}': {count} times ({percentage:.1f}%)\n")
                
                f.write("\nAutomation completed.\n")
            
            self.main_window.update_status(f"Summary saved to: {filename}")
            
        except Exception as e:
            self.main_window.update_status(f"Failed to save summary: {str(e)}")