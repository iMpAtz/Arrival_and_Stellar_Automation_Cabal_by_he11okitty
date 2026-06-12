import tkinter as tk
from tkinter import messagebox
import mouse

from data.pet_data import get_pet_untrain_steps, get_pet_ocr_options, get_default_pet_delay
from automation.pet_automation import PetAutomation
import os
from datetime import datetime
import sys


class PetTab:
    def __init__(self, parent_frame, main_window):

        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = PetAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.bot_core,
            on_target_found=self._on_target_found
        )

        self.area = None
        self.coord_vars = []
        self.coord_buttons = []
        self._running = False

        self.create_ui()

    # -------------------------
    def create_ui(self):

        colors = self.main_window.colors

        main = tk.Frame(self.parent_frame, bg="white")
        main.pack(fill=tk.BOTH, expand=True)

        # Intro card (same style direction as other tabs)
        intro_card = tk.Frame(main, bg=colors["intro_bg"], relief="flat", bd=0)
        intro_card.pack(fill=tk.X, padx=0, pady=(0, 6))

        intro_inner = tk.Frame(intro_card, bg=colors["intro_bg"])
        intro_inner.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(intro_inner, text="🐾", font=("Segoe UI", 12), bg=colors["intro_bg"]).pack(side=tk.LEFT, padx=(0, 6))

        title_wrap = tk.Frame(intro_inner, bg=colors["intro_bg"])
        title_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            title_wrap,
            text="PET TRAINING - Untrain Automation",
            font=("Segoe UI", 9, "bold"),
            bg=colors["intro_bg"],
            fg=colors["text"],
            anchor="w"
        ).pack(fill=tk.X)
        tk.Label(
            title_wrap,
            text="1) Set Positions  •  2) Define OCR Area  •  3) Select OCR Targets  •  4) Start",
            font=("Segoe UI", 7),
            bg=colors["intro_bg"],
            fg=colors["text_light"],
            anchor="w"
        ).pack(fill=tk.X, pady=(1, 0))

        # =========================
        # COORDINATES (STABLE STYLE)
        # =========================
        coord_card = tk.Frame(main, bg="white")
        coord_card.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(
            coord_card,
            text="📍 Click Positions (5 Required)",
            bg=colors['warning'],
            fg="white",
            font=("Segoe UI", 9, "bold")
        ).pack(fill=tk.X)

        coord_body = tk.Frame(coord_card, bg="white")
        coord_body.pack(fill=tk.X, padx=10, pady=8)

        steps = get_pet_untrain_steps()

        for i, name in enumerate(steps):

            row = tk.Frame(coord_body, bg="white")
            row.pack(fill=tk.X, pady=2)

            tk.Label(row, text=f"{i+1}. {name}", width=30, anchor="w", bg="white").pack(side=tk.LEFT)

            var = tk.StringVar(value="Not set")
            self.coord_vars.append(var)

            tk.Label(row, textvariable=var, bg="white", fg=colors['primary']).pack(side=tk.LEFT)

            btn = tk.Button(
                row,
                text="Set",
                font=('Segoe UI', 7, 'bold'),
                bg=colors['primary'],
                fg="white",
                relief='flat',
                padx=10,
                pady=3,
                cursor='hand2',
                command=lambda i=i: self.set_pos(i)
            )
            btn.pack(side=tk.RIGHT)

            self.coord_buttons.append(btn)

        # =========================
        # OCR OPTIONS (MULTI SELECT FIX)
        # =========================
        ocr_card = tk.Frame(main, bg="white")
        ocr_card.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(
            ocr_card,
            text="🔍 OCR Targets (Select Multiple)",
            bg=colors['success'],
            fg="white",
            font=("Segoe UI", 9, "bold")
        ).pack(fill=tk.X)

        ocr_scroll_container = tk.Frame(ocr_card, bg="white")
        ocr_scroll_container.pack(fill=tk.X, padx=10, pady=5)
        ocr_canvas = tk.Canvas(ocr_scroll_container, bg="white", height=140, highlightthickness=0)
        ocr_scrollbar = tk.Scrollbar(ocr_scroll_container, orient="vertical", command=ocr_canvas.yview)
        ocr_options_frame = tk.Frame(ocr_canvas, bg="white")

        ocr_options_frame.bind(
            "<Configure>",
            lambda e: ocr_canvas.configure(scrollregion=ocr_canvas.bbox("all"))
        )
        ocr_canvas.create_window((0, 0), window=ocr_options_frame, anchor="nw")
        ocr_canvas.configure(yscrollcommand=ocr_scrollbar.set)

        ocr_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ocr_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            ocr_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(_event):
            ocr_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(_event):
            ocr_canvas.unbind_all("<MouseWheel>")

        ocr_canvas.bind("<Enter>", _bind_mousewheel)
        ocr_canvas.bind("<Leave>", _unbind_mousewheel)
        self.ocr_vars = {}

        for item in get_pet_ocr_options():
            var = tk.BooleanVar(value=False)
            self.ocr_vars[item] = var
            chk = tk.Checkbutton(
                ocr_options_frame,
                text=item,
                variable=var,
                bg="white",
                anchor="w",
                justify="left"
            )
            chk.pack(fill=tk.X, anchor="w")

        area_btn = tk.Button(
            ocr_card,
            text="📐 Define OCR Area",
            font=('Segoe UI', 8, 'bold'),
            bg=colors['primary'],
            fg="white",
            relief='flat',
            padx=20,
            pady=6,
            cursor='hand2',
            command=self.define_area
        )
        area_btn.pack(padx=10, pady=(0, 8), anchor="e")

        # =========================
        # DELAY
        # =========================
        delay_frame = tk.Frame(main, bg="white")
        delay_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(delay_frame, text="Delay (ms):", bg="white").pack(side=tk.LEFT)

        self.delay_var = tk.StringVar(value=str(get_default_pet_delay()))
        tk.Entry(delay_frame, textvariable=self.delay_var, width=10).pack(side=tk.LEFT, padx=5)

        # =========================
        # CONTROL
        # =========================
        control = tk.Frame(main, bg="white")
        control.pack(pady=10)

        self.start_btn = tk.Button(
            control,
            text="▶️ START",
            font=('Segoe UI', 9, 'bold'),
            bg=colors['success'],
            fg="white",
            relief='flat',
            padx=30,
            pady=8,
            cursor='hand2',
            command=self.start
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.stop_btn = tk.Button(
            control,
            text="⏹️ STOP",
            font=('Segoe UI', 9, 'bold'),
            bg=colors['danger'],
            fg="white",
            relief='flat',
            padx=30,
            pady=8,
            cursor='hand2',
            state=tk.DISABLED,
            command=self.stop
        )
        self.stop_btn.pack(side=tk.LEFT)

    # -------------------------
    def set_pos(self, idx):
        if self._running:
            return
        # If the previous run stopped via stop_event, clear it so capture works.
        self.main_window.bot_core.start()
        messagebox.showinfo(
            "Set Position",
            f"Click step #{idx + 1} position in game window.\nCoordinate will be captured automatically."
        )

        self.main_window.root.config(cursor="crosshair")

        def capture():
            try:
                pos = self.main_window.bot_core.wait_for_mouse_click(mouse, button="left")
                if not pos:
                    return
                x, y = pos
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)
                coords = (rel_x, rel_y) if success else (x, y)

                self.coord_vars[idx].set(str(coords))
                setters = [
                    self.automation.set_pet_training_coords,
                    self.automation.set_untrain_pet_icon_coords,
                    self.automation.set_wrong_slot_coords,
                    self.automation.set_untrain_button_coords,
                    self.automation.set_yes_button_coords,
                ]
                setters[idx](coords)
                self.main_window.update_status(f"Pet step #{idx + 1} set at {coords}")
                self.main_window.root.after(
                    0,
                    lambda: messagebox.showinfo("Position Set", f"Step #{idx + 1} set at {coords}")
                )
            finally:
                self.main_window.root.after(0, lambda: self.main_window.root.config(cursor=""))

        self.main_window.bot_core.register_thread(f"pet-capture-{idx}", capture, daemon=True)

    # -------------------------
    def start(self):
        if self._running:
            return
        if not self.main_window.set_running_tool("Pet Untrain", automation=self.automation):
            messagebox.showwarning("Busy", "Another automation is already running.")
            return

        selected = [label for label, var in self.ocr_vars.items() if var.get()]

        if not selected:
            messagebox.showwarning("OCR", "Please select at least 1 OCR target")
            return

        self.automation.set_ocr_search_texts(selected)
        self.automation.set_area(self.area)

        try:
            self.automation.set_delay(int(self.delay_var.get()))
        except Exception:
            self.automation.set_delay(800)

        if self.automation.start():
            self._running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.main_window.clear_running_tool()

    # -------------------------
    def stop(self):
        self.automation.stop()
        self._running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.generate_summary("stopped")

    # -------------------------
    def emergency_stop(self):
        self.automation.emergency_stop()
        self._running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def define_area(self):
        # If the previous run stopped via stop_event, clear it so selector works.
        self.main_window.bot_core.start()
        def area_callback(area):
            self.area = area
            self.automation.set_area(area)
            self.main_window.update_status(f"Pet OCR area set: {area}")

        if not hasattr(self.main_window, "area_selector"):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def _on_target_found(self, normalized_text):
        def notify():
            self._running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            messagebox.showinfo(
                "Pet Target Found",
                f"Selected OCR option found.\nAutomation stopped.\n\nOCR: {normalized_text[:120]}"
            )

        self.main_window.root.after(0, notify)
        self.generate_summary("target_found", normalized_text)

    def generate_summary(self, reason, ocr_text=""):
        """Generate and save summary to file"""
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pet_summary_{timestamp}.txt"
            
            # Create summaries directory if it doesn't exist
            summaries_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'summaries')
            os.makedirs(summaries_dir, exist_ok=True)
            
            filepath = os.path.join(summaries_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("PET UNTRAIN AUTOMATION SUMMARY\n")
                f.write("=" * 40 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Reason: {reason}\n")
                
                # Selected OCR targets
                selected_targets = [label for label, var in self.ocr_vars.items() if var.get()]
                f.write(f"Selected OCR Targets: {', '.join(selected_targets)}\n")
                f.write(f"Delay: {self.delay_var.get()}ms\n")
                
                if ocr_text:
                    f.write(f"OCR Text Found: {ocr_text}\n")
                
                # Calculate percentages if we have multiple targets
                if len(selected_targets) > 1:
                    f.write("\nPERCENTAGES:\n")
                    for target in selected_targets:
                        if target.lower() in ocr_text.lower():
                            f.write(f"Match: {target} - 100.0%\n")
                        else:
                            f.write(f"No Match: {target} - 0.0%\n")
                
                # Show all OCR texts detected
                if self.automation.unmapped_ocr_counter:
                    f.write("\nALL DETECTED OCR TEXTS:\n")
                    total_ocr_reads = sum(self.automation.unmapped_ocr_counter.values())
                    for text_key, count in sorted(self.automation.unmapped_ocr_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_ocr_reads) * 100 if total_ocr_reads > 0 else 0
                        f.write(f"  '{text_key}': {count} times ({percentage:.1f}%)\n")
                
                f.write("\nAutomation completed.\n")
            
            self.main_window.update_status(f"Summary saved to: {filename}")
            
        except Exception as e:
            self.main_window.update_status(f"Failed to save summary: {str(e)}")