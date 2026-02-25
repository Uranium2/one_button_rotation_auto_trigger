# ui/spell_mapping_dialog.py
"""
SpellMappingDialog: Dialog for mapping spell image icons to keyboard keys for a class/spec.
If no images found, displays a message and disables saving.
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class SpellMappingDialog(tk.Toplevel):
    def __init__(self, master, icon_dir, prev_mapping, on_save):
        super().__init__(master)
        """Dialog used to map spell icons to keyboard keys.

        `icon_dir` is the directory containing icon images. `prev_mapping`
        is an optional mapping to pre-populate entries. `on_save` is a
        callback that receives the mapping when the user presses Save.
        """
        self.title("Configure Spell Mapping")
        self.icon_dir = icon_dir
        self.prev_mapping = prev_mapping or {}
        self.result_mapping = {}
        self.on_save = on_save
        self._icons = []  # To hold Tk images for lifetime
        files = self._get_icon_files()
        if not files:
            ttk.Label(
                self,
                text="No spell icons found in this profile folder:\n" + icon_dir,
                foreground="red",
            ).pack(padx=16, pady=24)
            ttk.Button(self, text="Close", command=self.destroy).pack(pady=8)
            self.save_btn = None
            return
        self.entries = {}
        # Add scrollable canvas and scrollbar for the list of spells
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Bind the frame to canvas scrolling
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Allow scrolling with mouse wheel when cursor is over the dialog
        # Bind enter/leave to attach/detach global mousewheel handler so the
        # wheel works even when the cursor is not exactly over the scrollbar.
        def _bind_mousewheel(_e=None):
            # Windows / Mac
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Linux
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(_e=None):
            try:
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
            except Exception:
                pass

        def _on_mousewheel(event):
            # Normalize event across platforms
            if hasattr(event, "delta"):
                # Windows / Mac
                delta = int(-1 * (event.delta / 120))
            else:
                # Linux: Button-4 (up), Button-5 (down)
                if event.num == 4:
                    delta = -1
                else:
                    delta = 1
            canvas.yview_scroll(delta, "units")

        # Attach enter/leave handlers to both canvas and the scrollable frame
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        scrollable_frame.bind("<Enter>", _bind_mousewheel)
        scrollable_frame.bind("<Leave>", _unbind_mousewheel)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=12, pady=12)
        scrollbar.pack(side="right", fill="y")

        # Add the spells into the scrollable frame
        for f in files:
            spell_name = os.path.splitext(os.path.basename(f))[0]
            row = ttk.Frame(scrollable_frame)
            row.pack(fill=tk.X, pady=4)
            try:
                img = Image.open(f).resize((32, 32))
                tki = ImageTk.PhotoImage(img)
                self._icons.append(tki)
                icon_lbl = ttk.Label(row, image=tki)
                icon_lbl.pack(side=tk.LEFT, padx=(0, 7))
            except Exception:
                icon_lbl = tk.Label(row, text="[IMG]", bg="gray")
                icon_lbl.pack(side=tk.LEFT, padx=(0, 7), ipadx=12, ipady=8)
            label = ttk.Label(row, text=spell_name)
            label.pack(side=tk.LEFT, padx=(0, 7))
            entry = ttk.Entry(row, width=7)
            entry.insert(0, self.prev_mapping.get(spell_name, ""))
            entry.pack(side=tk.LEFT)
            self.entries[spell_name] = entry
        self.save_btn = ttk.Button(self, text="Save", command=self._on_save)
        self.save_btn.pack(pady=12)
        ttk.Button(self, text="Cancel", command=self.destroy).pack()

    def _get_icon_files(self):
        """Return a list of icon file paths in the dialog's icon_dir.

        Supports JPG, JPEG and PNG extensions.
        """
        if not os.path.isdir(self.icon_dir):
            return []
        return [
            os.path.join(self.icon_dir, f)
            for f in os.listdir(self.icon_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

    def _on_save(self):
        """Collect entries and invoke the save callback with the mapping."""
        mapping = {}
        for spell, entry in self.entries.items():
            key = entry.get().strip()
            if key:
                mapping[spell] = key
        self.on_save(mapping)
        self.destroy()
