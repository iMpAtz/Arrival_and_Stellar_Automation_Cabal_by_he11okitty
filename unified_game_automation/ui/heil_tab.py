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

        # Automation components (with OCR for inventory detection)
        self.automation = HeilAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status
        )

        # UI state
        self.click_coords_1 = None
        self.click_coords_2 = None
        self.click_coords_3 = None
        self.click_coords_4 = None
        self.click_coords_5 = None
        self.ocr_area_count = None  # OCR area for item count (X / Y)
        self.ocr_area_message = None  # OCR area for inventory message

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
        
        title = tk.Label(text_frame, text="HEIL AUTO - Auto-Click with Inventory Management", 
                        font=('Segoe UI', 9, 'bold'), bg='#E3F2FD', fg=colors['text'], anchor='w')
        title.pack(fill=tk.X)
        
        instructions = (
            "1) Set 4 Click Positions  •  2) Define OCR Area  •  3) Set Delay  •  4) Start"
        )
        subtitle = tk.Label(text_frame, text=instructions, 
                           font=('Segoe UI', 7), bg='#E3F2FD', fg=colors['text_light'], anchor='w')
        subtitle.pack(fill=tk.X, pady=(1, 0))

        # Click positions section
        coord_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        coord_card.pack(fill=tk.X, padx=0, pady=(0, 6))
        
        coord_header = tk.Frame(coord_card, bg=colors['primary'], height=28)
        coord_header.pack(fill=tk.X)
        tk.Label(coord_header, text="📍 Click Positions (4 required)", 
                font=('Segoe UI', 8, 'bold'), bg=colors['primary'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        coord_body = tk.Frame(coord_card, bg='white')
        coord_body.pack(fill=tk.X, padx=10, pady=6)
        
        # Position 1
        coord_row1 = tk.Frame(coord_body, bg='white')
        coord_row1.pack(fill=tk.X, pady=(0, 3))
        
        tk.Label(coord_row1, text="Position 1:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.click_coord_var1 = tk.StringVar(value="Not set")
        coord_value1 = tk.Label(coord_row1, textvariable=self.click_coord_var1, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        coord_value1.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        set_btn1 = tk.Button(coord_row1, text="Set", 
                           font=('Segoe UI', 7, 'bold'),
                           bg=colors['primary'], fg='white', 
                           relief='flat', padx=10, pady=3,
                           cursor='hand2', command=self.set_click_position_1)
        set_btn1.pack(side=tk.RIGHT)
        
        tk.Label(coord_row1, text="(Main)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.RIGHT, padx=(0, 5))

        # Position 2
        coord_row2 = tk.Frame(coord_body, bg='white')
        coord_row2.pack(fill=tk.X, pady=(0, 3))
        
        tk.Label(coord_row2, text="Position 2:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.click_coord_var2 = tk.StringVar(value="Not set")
        coord_value2 = tk.Label(coord_row2, textvariable=self.click_coord_var2, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        coord_value2.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        set_btn2 = tk.Button(coord_row2, text="Set", 
                           font=('Segoe UI', 7, 'bold'),
                           bg='#FF9800', fg='white', 
                           relief='flat', padx=10, pady=3,
                           cursor='hand2', command=self.set_click_position_2)
        set_btn2.pack(side=tk.RIGHT)
        
        tk.Label(coord_row2, text="(Close Heil)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.RIGHT, padx=(0, 5))

        # Position 3
        coord_row3 = tk.Frame(coord_body, bg='white')
        coord_row3.pack(fill=tk.X, pady=(0, 3))
        
        tk.Label(coord_row3, text="Position 3:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.click_coord_var3 = tk.StringVar(value="Not set")
        coord_value3 = tk.Label(coord_row3, textvariable=self.click_coord_var3, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        coord_value3.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        set_btn3 = tk.Button(coord_row3, text="Set", 
                           font=('Segoe UI', 7, 'bold'),
                           bg='#FF9800', fg='white', 
                           relief='flat', padx=10, pady=3,
                           cursor='hand2', command=self.set_click_position_3)
        set_btn3.pack(side=tk.RIGHT)
        
        tk.Label(coord_row3, text="(Inventory sort click)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.RIGHT, padx=(0, 5))

        # Position 4
        coord_row4 = tk.Frame(coord_body, bg='white')
        coord_row4.pack(fill=tk.X)
        
        tk.Label(coord_row4, text="Position 4:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.click_coord_var4 = tk.StringVar(value="Not set")
        coord_value4 = tk.Label(coord_row4, textvariable=self.click_coord_var4, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        coord_value4.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        set_btn4 = tk.Button(coord_row4, text="Set", 
                           font=('Segoe UI', 7, 'bold'),
                           bg='#FF9800', fg='white', 
                           relief='flat', padx=10, pady=3,
                           cursor='hand2', command=self.set_click_position_4)
        set_btn4.pack(side=tk.RIGHT)
        
        tk.Label(coord_row4, text="(Cabal Icon Click it on bottom right)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.RIGHT, padx=(0, 5))

        # Position 5
        coord_row5 = tk.Frame(coord_body, bg='white')
        coord_row5.pack(fill=tk.X, pady=(3, 0))
        
        tk.Label(coord_row5, text="Position 5:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=10, anchor='w').pack(side=tk.LEFT)
        
        self.click_coord_var5 = tk.StringVar(value="Not set")
        coord_value5 = tk.Label(coord_row5, textvariable=self.click_coord_var5, 
                              font=('Segoe UI', 8), bg='white', fg=colors['primary'], anchor='w')
        coord_value5.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        set_btn5 = tk.Button(coord_row5, text="Set", 
                           font=('Segoe UI', 7, 'bold'),
                           bg='#FF9800', fg='white', 
                           relief='flat', padx=10, pady=3,
                           cursor='hand2', command=self.set_click_position_5)
        set_btn5.pack(side=tk.RIGHT)
        
        tk.Label(coord_row5, text="(click on Heil's Research)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.RIGHT, padx=(0, 5))

        # OCR Area section
        ocr_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        ocr_card.pack(fill=tk.X, padx=0, pady=(0, 6))
        
        ocr_header = tk.Frame(ocr_card, bg='#9C27B0', height=28)
        ocr_header.pack(fill=tk.X)
        tk.Label(ocr_header, text="📐 OCR Detection Areas", 
                font=('Segoe UI', 8, 'bold'), bg='#9C27B0', fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        ocr_body = tk.Frame(ocr_card, bg='white')
        ocr_body.pack(fill=tk.X, padx=10, pady=6)
        
        # OCR Area 1: Item Count (X / Y)
        ocr_row1 = tk.Frame(ocr_body, bg='white')
        ocr_row1.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(ocr_row1, text="Item Count:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=12, anchor='w').pack(side=tk.LEFT)
        
        self.btn_define_area_count = tk.Button(ocr_row1, text="OCR area (Item Count)", 
                                               font=('Segoe UI', 8, 'bold'),
                                               bg='#9C27B0', fg='white',
                                               relief='flat', padx=15, pady=4,
                                               cursor='hand2', command=self.define_ocr_area_count)
        self.btn_define_area_count.pack(side=tk.LEFT, padx=(5, 0))
        
        tk.Label(ocr_row1, text="(for stop condition)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.LEFT, padx=(5, 0))
        
        # OCR Area 2: Inventory Message
        ocr_row2 = tk.Frame(ocr_body, bg='white')
        ocr_row2.pack(fill=tk.X)
        
        tk.Label(ocr_row2, text="Inventory Msg:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=12, anchor='w').pack(side=tk.LEFT)
        
        self.btn_define_area_message = tk.Button(ocr_row2, text="Define OCR Area (Message)", 
                                                 font=('Segoe UI', 8, 'bold'),
                                                 bg='#9C27B0', fg='white',
                                                 relief='flat', padx=15, pady=4,
                                                 cursor='hand2', command=self.define_ocr_area_message)
        self.btn_define_area_message.pack(side=tk.LEFT, padx=(5, 0))
        
        tk.Label(ocr_row2, text="(for inventory full detection)", font=('Segoe UI', 7), 
                bg='white', fg=colors['text_light']).pack(side=tk.LEFT, padx=(5, 0))

        # Delay settings section
        delay_card = tk.Frame(main_frame, bg='white', relief='flat', bd=0)
        delay_card.pack(fill=tk.X, padx=0, pady=(0, 6))
        
        delay_header = tk.Frame(delay_card, bg=colors['success'], height=28)
        delay_header.pack(fill=tk.X)
        tk.Label(delay_header, text="⏱️ Delay Settings", 
                font=('Segoe UI', 8, 'bold'), bg=colors['success'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        delay_body = tk.Frame(delay_card, bg='white')
        delay_body.pack(fill=tk.X, padx=10, pady=6)
        
        # Delay for Position 1
        delay_row1 = tk.Frame(delay_body, bg='white')
        delay_row1.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(delay_row1, text="Position 1:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=12, anchor='w').pack(side=tk.LEFT)
        
        self.delay_var = tk.StringVar(value="1000")
        self.delay_entry = tk.Entry(delay_row1, textvariable=self.delay_var, 
                                    font=('Segoe UI', 8), width=10, relief='solid', bd=1)
        self.delay_entry.pack(side=tk.LEFT, padx=(5, 8))
        
        tk.Label(delay_row1, text="ms (delay for main click)", 
                font=('Segoe UI', 7), bg='white', fg=colors['text_light']).pack(side=tk.LEFT)
        
        # Delay for Positions 2-5 (fixed, shown as info)
        delay_row2 = tk.Frame(delay_body, bg='white')
        delay_row2.pack(fill=tk.X)
        
        tk.Label(delay_row2, text="Positions 2-5:", font=('Segoe UI', 8, 'bold'), 
                bg='white', fg=colors['text'], width=12, anchor='w').pack(side=tk.LEFT)
        
        tk.Label(delay_row2, text="1000 ms (fixed for inventory management)", 
                font=('Segoe UI', 8), bg='white', fg=colors['text_light']).pack(side=tk.LEFT, padx=(5, 0))

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

    def set_click_position_1(self):
        """Set click position 1 (main action)"""
        self._set_click_position(1, "Main Action", self.click_coord_var1)

    def set_click_position_2(self):
        """Set click position 2 (inventory management)"""
        self._set_click_position(2, "Inventory Management", self.click_coord_var2)

    def set_click_position_3(self):
        """Set click position 3 (inventory management)"""
        self._set_click_position(3, "Inventory Management", self.click_coord_var3)

    def set_click_position_4(self):
        """Set click position 4 (inventory management)"""
        self._set_click_position(4, "Inventory Management", self.click_coord_var4)

    def set_click_position_5(self):
        """Set click position 5 (inventory management)"""
        self._set_click_position(5, "Inventory Management", self.click_coord_var5)

    def _set_click_position(self, position_num, position_type, coord_var):
        """Generic method to set a click position"""
        # Connect to game if needed
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            f"Click on Position {position_num} ({position_type}) in the game window.\n"
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
                    coords = (rel_x, rel_y)
                    
                    # Store coordinates based on position number
                    if position_num == 1:
                        self.click_coords_1 = coords
                        self.automation.set_click_position_1(coords)
                    elif position_num == 2:
                        self.click_coords_2 = coords
                        self.automation.set_click_position_2(coords)
                    elif position_num == 3:
                        self.click_coords_3 = coords
                        self.automation.set_click_position_3(coords)
                    elif position_num == 4:
                        self.click_coords_4 = coords
                        self.automation.set_click_position_4(coords)
                    elif position_num == 5:
                        self.click_coords_5 = coords
                        self.automation.set_click_position_5(coords)
                    
                    coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Position {position_num} set at ({rel_x}, {rel_y})")
                    
                    # Enable start button if all positions are set
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                # Reset cursor
                self.main_window.root.config(cursor="")

        # Start capture in thread
        threading.Thread(target=capture_click, daemon=True).start()

    def define_ocr_area_count(self):
        """Define the OCR area for item count detection (X / Y format)"""
        def area_callback(area):
            """Callback when area is selected"""
            self.ocr_area_count = area
            self.automation.set_ocr_area_count(area)
            self.main_window.update_status(f"OCR area (Item Count) defined: {area}")
            self._check_enable_start()

        # Use the shared area selector
        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback

        self.main_window.area_selector.select_area()

    def define_ocr_area_message(self):
        """Define the OCR area for inventory message detection"""
        def area_callback(area):
            """Callback when area is selected"""
            self.ocr_area_message = area
            self.automation.set_ocr_area_message(area)
            self.main_window.update_status(f"OCR area (Inventory Message) defined: {area}")
            self._check_enable_start()

        # Use the shared area selector
        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback

        self.main_window.area_selector.select_area()

    def _check_enable_start(self):
        """Check if all required fields are set and enable start button"""
        if (self.click_coords_1 and self.click_coords_2 and 
            self.click_coords_3 and self.click_coords_4 and self.click_coords_5 and 
            self.ocr_area_count and self.ocr_area_message):
            self.btn_start.config(state=tk.NORMAL)

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
            print(f"[UI] Delay input from user: {delay_ms} ms")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return

        # Set the delay in automation
        self.automation.set_delay(delay_ms)
        print(f"[UI] Delay set in automation: {delay_ms} ms")

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
