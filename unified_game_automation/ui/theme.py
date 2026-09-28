# Centralized UI theme palette and styling helpers for CustomTkinter widgets

import customtkinter as ctk
import tkinter as tk

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
    "teal":     "#0d9488",
    "orange":   "#ea580c",
    "bg":       "#111827",
    "panel":    "#1f2937",
    "panel2":   "#273449",
    "input":    "#111827",
    "text":     "#f3f4f6",
    "text_dim": "#aab4c3",
    "line":     "#374151",
}

# Alias for backwards compatibility with UI tab modules
_A = ACCENT


def section_header(parent, title, color=None):
    """Create a standardized section header banner in CustomTkinter scroll views."""
    color = color or ACCENT["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=34)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(
        header,
        text=title,
        font=ctk.CTkFont("Segoe UI", 11, "bold"),
        text_color="#ffffff",
        anchor="w",
    ).pack(side=tk.LEFT, padx=12, pady=4)
    return header


def card(parent, **kwargs):
    """Shared card styling so every tab has the same visual rhythm."""
    options = {"corner_radius": 10, "border_width": 1,
               "border_color": ACCENT["line"], "fg_color": ACCENT["panel"]}
    options.update(kwargs)
    return ctk.CTkFrame(parent, **options)


def status_pill(parent, variable, color=None):
    """Compact status chip used by the shell and optional tab controls."""
    return ctk.CTkLabel(parent, textvariable=variable,
                        font=ctk.CTkFont("Segoe UI", 10, "bold"),
                        text_color="#ffffff", fg_color=color or ACCENT["surface2"],
                        corner_radius=8, padx=10, pady=4)
