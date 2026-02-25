# ui/region_selector.py
"""
RegionSelector: Fullscreen rectangle selector for screen region (Tkinter).
Returns: (x, y, width, height)
"""

import tkinter as tk
from typing import Optional, Callable


class RegionSelector(tk.Toplevel):
    def __init__(self, master, callback: Callable[[Optional[tuple]], None]):
        super().__init__(master)
        self.withdraw()  # Hide until setup
        self.callback = callback
        self.overrideredirect(True)
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+0+0")
        self.attributes("-alpha", 0.3)
        self.configure(bg="black")
        self.lift()
        # Use default background or explicit bg="black" for Canvas
        self.canvas = tk.Canvas(self, highlightthickness=0, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.start_x: Optional[int] = None
        self.start_y: Optional[int] = None
        self.rect = None
        self.bind_events()
        self.deiconify()  # Show

    def bind_events(self):
        """Bind mouse and keyboard events for rectangle selection."""
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.close())

    def on_press(self, event):
        """Handle mouse press: start rectangle at event coordinates."""
        self.start_x, self.start_y = event.x, event.y
        if self.rect:
            self.canvas.delete(self.rect)
        if self.start_x is not None and self.start_y is not None:
            self.rect = self.canvas.create_rectangle(
                int(self.start_x),
                int(self.start_y),
                int(self.start_x),
                int(self.start_y),
                outline="red",
                width=2,
                fill="",
            )
        else:
            self.rect = None

    def on_motion(self, event):
        """Update rectangle while the mouse is dragged."""
        if (
            self.rect is not None
            and self.start_x is not None
            and self.start_y is not None
        ):
            self.canvas.coords(
                self.rect,
                int(self.start_x),
                int(self.start_y),
                int(event.x),
                int(event.y),
            )

    def on_release(self, event):
        """Finalize rectangle on mouse release and return the region.

        Calls the `callback` with either (x, y, w, h) or None if the
        selection was too small or cancelled.
        """
        if self.start_x is None or self.start_y is None:
            self.close()
            self.callback(None)
            return
        x0, y0 = int(self.start_x), int(self.start_y)
        x1, y1 = int(event.x), int(event.y)
        x, y = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0), abs(y1 - y0)
        self.close()
        if w > 5 and h > 5:
            self.callback((x, y, w, h))
        else:
            self.callback(None)

    def close(self):
        self.destroy()
