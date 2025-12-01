# Area selection with drag-and-drop functionality
# Ported from main.py area selection logic

import tkinter as tk
from tkinter import messagebox

class OverlayWindow(tk.Toplevel):
    """Red overlay window to show selected area"""
    def __init__(self, master, x, y, w, h, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.config(bg="black")
        self.attributes("-transparentcolor", "black")

        self.geometry(f"{w}x{h}+{x}+{y}")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_rectangle(
            0, 0, w, h,
            outline="red",
            width=2,
            fill=""
        )

    def close_overlay(self):
        self.destroy()

class AreaSelector:
    def __init__(self, root, callback=None):
        """Initialize the area selector with drag-and-drop functionality"""
        self.root = root
        self.callback = callback
        self.overlay_window = None

    def select_area(self):
        """Start area selection process"""
        try:
            # Close existing overlay if any
            if hasattr(self, "overlay_window") and self.overlay_window is not None:
                self.overlay_window.close_overlay()
                self.overlay_window = None

            # Show instruction first
            messagebox.showinfo(
                "Area Selection",
                "Click and drag to select the OCR area.\n"
                "Press ESC to cancel."
            )

            # Create fullscreen overlay for selection
            overlay = tk.Toplevel(self.root)
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-alpha', 0.2)
            overlay.attributes('-topmost', True)
            overlay.configure(bg='grey')

            # Variables for selection
            start_x, start_y = 0, 0
            rect = None

            # Handle mouse events
            def on_press(event):
                nonlocal start_x, start_y, rect
                try:
                    start_x, start_y = event.x, event.y
                    rect = tk.Canvas(overlay, bg='red', height=1, width=1)
                    rect.place(x=start_x, y=start_y)
                except Exception as e:
                    print(f"Error in on_press: {e}")

            def on_drag(event):
                nonlocal rect, start_x, start_y
                try:
                    if rect:
                        width = abs(event.x - start_x)
                        height = abs(event.y - start_y)
                        x = min(start_x, event.x)
                        y = min(start_y, event.y)
                        rect.place(x=x, y=y, width=width, height=height)
                except Exception as e:
                    print(f"Error in on_drag: {e}")

            def on_release(event):
                try:
                    left = min(start_x, event.x)
                    top = min(start_y, event.y)
                    right = max(start_x, event.x)
                    bottom = max(start_y, event.y)
                    width = right - left
                    height = bottom - top

                    # Validate area dimensions
                    if width <= 0 or height <= 0:
                        messagebox.showerror("Error", "Invalid area selection (width or height <= 0).")
                        overlay.destroy()
                        return

                    # Store area as (left, top, width, height)
                    area = (left, top, width, height)

                    # Destroy overlay first to prevent focus issues
                    overlay.destroy()

                    # Create red overlay to show selected area temporarily
                    self.overlay_window = OverlayWindow(self.root, left, top, width, height)

                    # Call callback with the selected area
                    if self.callback:
                        self.callback(area)

                    # Auto-remove the red overlay after 2 seconds
                    self.root.after(2000, self.clear_overlay)

                    messagebox.showinfo("Success", f"Area defined: ({left}, {top}, {width}, {height})")

                except Exception as e:
                    print(f"Error in on_release: {e}")
                    messagebox.showerror("Error", f"Failed to define area: {str(e)}")
                    try:
                        overlay.destroy()
                    except:
                        pass

            def on_escape(event):
                try:
                    overlay.destroy()
                except:
                    pass

            # Bind events
            overlay.bind("<ButtonPress-1>", on_press)
            overlay.bind("<B1-Motion>", on_drag)
            overlay.bind("<ButtonRelease-1>", on_release)
            overlay.bind("<Escape>", on_escape)

        except Exception as e:
            print(f"Error in select_area: {e}")
            messagebox.showerror("Error", f"Failed to start area selection: {str(e)}")

    def clear_overlay(self):
        """Clear the red overlay window"""
        if hasattr(self, "overlay_window") and self.overlay_window is not None:
            self.overlay_window.close_overlay()
            self.overlay_window = None
