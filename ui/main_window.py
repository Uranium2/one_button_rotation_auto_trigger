# ui/main_window.py
"""
Tkinter UI Main Window for WoW One-Button Rotation Auto Trigger
"""

import os
import threading
import tkinter as tk
import time
from tkinter import ttk

try:
    import keyboard

    KEYBOARD_AVAILABLE = True
except Exception:
    keyboard = None
    KEYBOARD_AVAILABLE = False

from core.input_sender import press_key, emergency_release_modifiers
from core.matcher import match_region_with_hash_cache
from core.profile_manager import ProfileManager, get_icon_dir
from core.scanner import capture_region
from ui.region_selector import RegionSelector
from ui.spell_mapping_dialog import SpellMappingDialog

CLASSES = [
    "Death Knight",
    "Demon Hunter",
    "Druid",
    "Evoker",
    "Hunter",
    "Mage",
    "Monk",
    "Paladin",
    "Priest",
    "Rogue",
    "Shaman",
    "Warlock",
    "Warrior",
]
ALL_SPECS = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Demon Hunter": ["Havoc", "Vengeance"],
    "Druid": ["Balance", "Feral", "Guardian", "Restoration"],
    "Evoker": ["Devastation", "Preservation", "Augmentation"],
    "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],
    "Mage": ["Arcane", "Fire", "Frost"],
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
    "Paladin": ["Holy", "Protection", "Retribution"],
    "Priest": ["Discipline", "Holy", "Shadow"],
    "Rogue": ["Assassination", "Outlaw", "Subtlety"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"],
    "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"],
}

# Application defaults / constants
DEFAULT_HOTKEY = "="
DEFAULT_LOOP_HOTKEY = "."
EMERGENCY_HOTKEY = "esc"
DEFAULT_LOOP_INTERVAL = 0.05
LOOP_INDICATOR_ON = "Loop: On"
LOOP_INDICATOR_OFF = "Loop: Off"


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        """Main application window and controller.

        Builds the Tkinter UI, manages profile selection and triggers the
        scanning/matching flow when toggled.
        """
        self.title("WoW One-Button Rotation Auto Trigger")
        self.geometry("360x480")
        self.resizable(False, False)
        self.profile_mgr = ProfileManager()
        self.class_var = tk.StringVar(value=CLASSES[0])
        self.spec_var = tk.StringVar(value=ALL_SPECS[CLASSES[0]][0])
        # initial runtime settings required by the layout
        self.loop_interval = 0.05
        # attempt to restore persisted loop interval (ProfileManager may override below)
        try:
            stored = None
            # profile_mgr is set next; guard in case _build_layout uses it
        except Exception:
            pass
        # set up UI
        self._restoring = True
        self._build_layout()
        self._set_class_options()
        # try to restore last selected class/spec from profile manager
        last = self.profile_mgr.get_last_selected()
        if last:
            cls, spec = last
            if cls in CLASSES and spec in ALL_SPECS.get(cls, []):
                self.class_var.set(cls)
                self._set_spec_options(cls)
                self.spec_var.set(spec)
        else:
            self._set_spec_options(CLASSES[0])
        # trace spec_var changes to persist last selected (avoids relying on
        # Combobox events which may not fire for programmatic changes)
        try:
            self.spec_var.trace_add("write", self._spec_var_trace)
        except Exception:
            # fallback for older tkinter
            try:
                self.spec_var.trace("w", self._spec_var_trace)
            except Exception:
                pass
        self._restoring = False

        # Initialize running state
        self.running = False
        # hotkey state
        self._hotkey_handle = None
        self._hotkey_value = None
        # loop hotkey state
        self._loop_hotkey_handle = None
        self._loop_hotkey_value = None
        # emergency kill hotkey handle
        self._kill_hotkey_handle = None
        self._loop_running = False
        # loop interval (seconds)
        self.loop_interval = 0.05
        # try restore persisted loop interval
        stored = self.profile_mgr.get_loop_interval()
        if stored is not None:
            try:
                self.loop_interval = float(stored)
            except Exception:
                pass

        # Bind global hotkey for toggle functionality
        self.bind_hotkey()
        # Ensure last selection is saved on app close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def bind_hotkey(self):
        # Run global hotkey listener in a daemon thread so UI stays responsive
        def listen_key():
            # initial registration uses saved hotkey or default '='
            hotkey = self.profile_mgr.get_hotkey() or DEFAULT_HOTKEY
            try:
                self._hotkey_handle = keyboard.add_hotkey(
                    hotkey, lambda: self._on_toggle()
                )
                self._hotkey_value = hotkey
            except Exception:
                # fallback to '=' if registration fails
                try:
                    self._hotkey_handle = keyboard.add_hotkey(
                        DEFAULT_HOTKEY, lambda: self._on_toggle()
                    )
                    self._hotkey_value = DEFAULT_HOTKEY
                except Exception:
                    self._hotkey_handle = None
                    self._hotkey_value = DEFAULT_HOTKEY
            # also register loop hotkey (saved or default '/')
            try:
                loop_key = self.profile_mgr.get_loop_hotkey() or DEFAULT_LOOP_HOTKEY
                self._loop_hotkey_handle = keyboard.add_hotkey(
                    loop_key, lambda: self._on_toggle_loop()
                )
                self._loop_hotkey_value = loop_key
            except Exception:
                # ignore loop hotkey registration errors silently here
                self._loop_hotkey_handle = None
                self._loop_hotkey_value = "."
            # register emergency stop hotkey (Escape) to immediately stop loop
            try:
                self._kill_hotkey_handle = keyboard.add_hotkey(
                    EMERGENCY_HOTKEY, lambda: self._on_emergency_stop()
                )
            except Exception:
                self._kill_hotkey_handle = None

            keyboard.wait()

        threading.Thread(target=listen_key, daemon=True).start()

    def _build_layout(self):
        """Create and place all widgets used by the main window."""
        # Class and Spec on one line
        cs_frame = ttk.Frame(self)
        cs_frame.pack(pady=(18, 6), fill=tk.X)
        ttk.Label(cs_frame, text="Class:").pack(side=tk.LEFT, padx=(0, 6))
        self.class_combo = ttk.Combobox(
            cs_frame,
            values=CLASSES,
            textvariable=self.class_var,
            state="readonly",
            width=15,
        )
        self.class_combo.bind("<<ComboboxSelected>>", self._on_class_selected)
        self.class_combo.pack(side=tk.LEFT)
        ttk.Label(cs_frame, text="Spec:").pack(side=tk.LEFT, padx=(12, 6))
        self.spec_combo = ttk.Combobox(
            cs_frame, values=[], textvariable=self.spec_var, state="readonly", width=15
        )
        # persist spec selection when changed
        self.spec_combo.bind("<<ComboboxSelected>>", self._on_spec_selected)
        self.spec_combo.pack(side=tk.LEFT)
        ttk.Button(
            self, text="Configure Region", command=self._on_configure_region
        ).pack(pady=(18, 8))
        ttk.Button(
            self,
            text="Configure Spell Mapping",
            command=self._on_configure_spell_mapping,
        ).pack(pady=(0, 8))
        ttk.Label(self, text="Logger Output:").pack()
        # Detection uses the hash matcher (fast, robust)
        # Make the logger smaller so the main window can fit controls
        self.log_box = tk.Text(self, height=10, width=36, state="disabled", bg="#f5f5f5")
        self.log_box.pack(padx=8, pady=(2, 0))
        # Hotkey configuration entry (toggle hotkey on its own row)
        top_frame = ttk.Frame(self)
        top_frame.pack(pady=(8, 6), fill=tk.X)
        ttk.Label(top_frame, text="Toggle Hotkey:").pack(side=tk.LEFT, padx=(0, 6))
        self.hotkey_var = tk.StringVar(
            value=self.profile_mgr.get_hotkey() or DEFAULT_HOTKEY
        )
        self.hotkey_entry = ttk.Entry(top_frame, width=6, textvariable=self.hotkey_var)
        self.hotkey_entry.pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Set", command=self._on_set_hotkey).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        # Loop hotkey on its own row
        loop_frame = ttk.Frame(self)
        loop_frame.pack(pady=(4, 4), fill=tk.X)
        ttk.Label(loop_frame, text="Loop Hotkey:").pack(side=tk.LEFT, padx=(0, 6))
        self.loop_hotkey_var = tk.StringVar(
            value=self.profile_mgr.get_loop_hotkey() or DEFAULT_LOOP_HOTKEY
        )
        self.loop_hotkey_entry = ttk.Entry(
            loop_frame, width=6, textvariable=self.loop_hotkey_var
        )
        self.loop_hotkey_entry.pack(side=tk.LEFT)
        ttk.Button(loop_frame, text="Set", command=self._on_set_loop_hotkey).pack(
            side=tk.LEFT, padx=(6, 8)
        )

        # Interval on its own row
        interval_frame = ttk.Frame(self)
        interval_frame.pack(pady=(2, 6), fill=tk.X)
        ttk.Label(interval_frame, text="Interval (s):").pack(side=tk.LEFT, padx=(0, 6))
        # guard access in case attribute isn't set on the Tk instance
        self.loop_interval_var = tk.StringVar(
            value=f"{getattr(self, 'loop_interval', DEFAULT_LOOP_INTERVAL):.2f}"
        )
        self.loop_interval_entry = ttk.Entry(
            interval_frame, width=6, textvariable=self.loop_interval_var
        )
        self.loop_interval_entry.pack(side=tk.LEFT)
        ttk.Button(interval_frame, text="Set", command=self._on_set_loop_interval).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        # Loop running indicator
        self.loop_indicator_var = tk.StringVar(value="Loop: Off")
        self.loop_indicator_label = ttk.Label(
            self, textvariable=self.loop_indicator_var, foreground="#006400"
        )
        self.loop_indicator_label.pack(pady=(6, 0))

        # Emergency stop button (visible clickable control)
        ttk.Button(
            self, text="Emergency Stop (Esc)", command=self._on_emergency_stop
        ).pack(pady=(6, 0))

    def _set_class_options(self):
        """Populate the class combobox with available classes."""
        self.class_combo["values"] = CLASSES

    def _set_spec_options(self, class_name):
        """Update the spec combobox when a class is selected.

        Sets the first spec as the default selection.
        """
        specs = ALL_SPECS[class_name]
        self.spec_combo["values"] = specs
        self.spec_var.set(specs[0])

    def _on_class_selected(self, event):
        """Handle class selection change from the UI."""
        new_class = self.class_var.get()
        self._set_spec_options(new_class)
        self._log(f"Selected class: {new_class}")

    def _on_spec_selected(self, event):
        """Handle spec selection change and persist last selection."""
        new_spec = self.spec_var.get()
        self._log(f"Selected spec: {new_spec}")
        self.profile_mgr.set_last_selected(self.class_var.get(), self.spec_var.get())

    def _spec_var_trace(self, *args):
        """Trace callback for spec_var changes used to persist last selection.

        This is invoked on both user and programmatic changes; ignore calls
        while restoring initial state.
        """
        if getattr(self, "_restoring", False):
            return
        try:
            self.profile_mgr.set_last_selected(
                self.class_var.get(), self.spec_var.get()
            )
        except Exception:
            pass

    def _on_configure_region(self):
        """Open the region selector and save the chosen region."""
        class_name = self.class_var.get()
        spec_name = self.spec_var.get()
        prior = self.profile_mgr.get_region(class_name, spec_name)
        if prior:
            prinfo = f"Previous region: x={prior['x']} y={prior['y']} w={prior['width']} h={prior['height']}"
            self._log(prinfo)

        def on_region_selected(region_tuple):
            """Callback for RegionSelector; receives (x,y,w,h) or None."""
            if region_tuple is None:
                self._log("Region selection cancelled or too small.")
                return
            x, y, w, h = region_tuple
            self._log(f"Selected region: x={x}, y={y}, w={w}, h={h}")
            region_dict = {"x": x, "y": y, "width": w, "height": h}
            try:
                self.profile_mgr.set_region(class_name, spec_name, region_dict)
                self._log("Region saved.")
                # save last selected as well
                try:
                    self.profile_mgr.set_last_selected(class_name, spec_name)
                except Exception:
                    pass
            except Exception as ex:
                self._log("Error saving region: " + str(ex))

        RegionSelector(self, on_region_selected)

    def _on_configure_spell_mapping(self):
        """Open the spell mapping dialog for the selected profile."""
        class_name = self.class_var.get()
        spec_name = self.spec_var.get()
        icon_dir = get_icon_dir(class_name, spec_name)
        icon_dir = os.path.abspath(icon_dir)
        prev = self.profile_mgr.get_spell_mapping(class_name, spec_name)

        def on_save(mapping):
            """Callback invoked by SpellMappingDialog when Save is pressed."""
            self.profile_mgr.set_spell_mapping(class_name, spec_name, mapping)
            self._log(
                f"Spell mapping saved for {class_name} {spec_name} ({len(mapping)} spells)."
            )
            # persist last selected on save as well
            try:
                self.profile_mgr.set_last_selected(class_name, spec_name)
            except Exception:
                pass

        SpellMappingDialog(self, icon_dir, prev, on_save)

    def _on_set_hotkey(self):
        """Set and register a new global hotkey from the UI entry."""
        new_key = self.hotkey_var.get().strip()
        if not new_key:
            self._log("Hotkey cannot be empty.")
            return
        try:
            # unregister previous
            try:
                if getattr(self, "_hotkey_value", None) is not None:
                    keyboard.remove_hotkey(self._hotkey_value)
            except Exception:
                pass
            # register new
            self._hotkey_handle = keyboard.add_hotkey(
                new_key, lambda: self._on_toggle()
            )
            self._hotkey_value = new_key
            self.profile_mgr.set_hotkey(new_key)
            self._log(f"Hotkey set to: {new_key}")
        except Exception as e:
            self._log(f"Failed to set hotkey: {e}")

    def _on_set_loop_hotkey(self):
        """Set and register a new global loop-mode hotkey from the UI entry."""
        new_key = self.loop_hotkey_var.get().strip()
        if not new_key:
            self._log("Loop hotkey cannot be empty.")
            return
        try:
            # unregister previous loop hotkey if present
            try:
                if getattr(self, "_loop_hotkey_value", None) is not None:
                    keyboard.remove_hotkey(self._loop_hotkey_value)
            except Exception:
                pass
            # register new
            self._loop_hotkey_handle = keyboard.add_hotkey(
                new_key, lambda: self._on_toggle_loop()
            )
            self._loop_hotkey_value = new_key
            self.profile_mgr.set_loop_hotkey(new_key)
            self._log(f"Loop hotkey set to: {new_key}")
        except Exception as e:
            self._log(f"Failed to set loop hotkey: {e}")

    def _on_set_loop_interval(self):
        """Set the loop interval from the UI entry."""
        val = self.loop_interval_var.get().strip()
        try:
            f = float(val)
            if f <= 0:
                raise ValueError("Interval must be positive")
            self.loop_interval = f
            try:
                self.profile_mgr.set_loop_interval(self.loop_interval)
            except Exception:
                pass
            self._log(f"Loop interval set to {self.loop_interval:.3f}s")
        except Exception as e:
            self._log(f"Invalid interval: {e}")

    def _on_toggle(self):
        """Capture region, run matcher and send input if a mapped spell is found."""
        self._log("Action triggered. Capturing region and detecting spell.")

        class_name = self.class_var.get()
        spec_name = self.spec_var.get()
        region = self.profile_mgr.get_region(class_name, spec_name)
        mapping = self.profile_mgr.get_spell_mapping(class_name, spec_name)

        if not region:
            self._log("Region not configured. Please configure the region first.")
            return

        if not mapping:
            self._log("Spell mapping not configured. Please map your spells first.")
            return

        try:
            # Initialize icon_dir
            icon_dir = get_icon_dir(class_name, spec_name)

            # Capture the region
            img = capture_region(region)

            # Perform and benchmark cached matching
            start_time = time.time()
            detected_spell, score = match_region_with_hash_cache(img, icon_dir)
            label = "[Hash Matching]"
            elapsed_time = time.time() - start_time

            self._log(
                f"{label} {elapsed_time:.4f}s || Detected Spell: {detected_spell} (score={score:.3f})"
            )

            # Check if the spell maps to a key
            if detected_spell in mapping:
                key = mapping[detected_spell]
                press_key(key)
                self._log(f"Detected spell: {detected_spell}. Pressed key: {key}")
            else:
                self._log(
                    f"Spell {detected_spell} not found in mapping. No key pressed."
                )
        except Exception as e:
            self._log(f"Error: {str(e)}")

    def _on_toggle_loop(self):
        """Start/stop looped triggering: repeatedly capture/detect/send until toggled off."""
        # Use a background thread for the loop so the UI stays responsive.
        if getattr(self, "_loop_running", False):
            # stop loop
            self._loop_running = False
            self._log("Loop mode stopped.")
            return

        # start loop
        self._loop_running = True
        self.loop_indicator_var.set("Loop: On")

        def loop_worker():
            self._log("Loop mode started.")
            class_name = self.class_var.get()
            spec_name = self.spec_var.get()
            region = self.profile_mgr.get_region(class_name, spec_name)
            mapping = self.profile_mgr.get_spell_mapping(class_name, spec_name)

            if not region:
                self._log("Region not configured. Please configure the region first.")
                self._loop_running = False
                return

            if not mapping:
                self._log("Spell mapping not configured. Please map your spells first.")
                self._loop_running = False
                return

            try:
                while self._loop_running:
                    img = capture_region(region)
                    detected_spell, score = match_region_with_hash_cache(
                        img, get_icon_dir(class_name, spec_name)
                    )
                    if detected_spell in mapping:
                        key = mapping[detected_spell]
                        press_key(key)
                        self._log(
                            f"Loop: Detected {detected_spell} -> pressed {key} (score={score:.3f})"
                        )
                    else:
                        self._log(
                            f"Loop: Detected {detected_spell} not mapped (score={score:.3f})"
                        )
                    # respect user-configured loop interval at runtime
                    time.sleep(self.loop_interval)
            except Exception as e:
                self._log(f"Loop error: {str(e)}")
            finally:
                self._loop_running = False
                self.loop_indicator_var.set("Loop: Off")
                self._log("Loop mode ended.")

        threading.Thread(target=loop_worker, daemon=True).start()

    def _on_close(self):
        """Save last selected class/spec and close the application."""
        try:
            self.profile_mgr.set_last_selected(
                self.class_var.get(), self.spec_var.get()
            )
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            try:
                self.quit()
            except Exception:
                pass

    def _on_emergency_stop(self):
        """Immediate stop handler: stops loop and releases modifiers.

        Bound to the Escape key and the Emergency Stop button in the UI.
        """
        if getattr(self, "_loop_running", False):
            self._loop_running = False
            # best-effort release modifiers so no key remains stuck
            try:
                emergency_release_modifiers()
            except Exception as ex:
                self._log(f"Emergency release failed: {ex}")
            self.loop_indicator_var.set("Loop: Off")
            self._log("Emergency stop pressed: loop halted and modifiers released.")
        else:
            # still attempt cleanup even if loop not running
            try:
                emergency_release_modifiers()
                self._log("Emergency release invoked (no loop running).")
            except Exception as ex:
                self._log(f"Emergency release failed: {ex}")

    def _log(self, msg):
        """Append a line to the UI log textbox (thread-safe enough for this app)."""
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"{msg}\n")
        self.log_box.config(state=tk.DISABLED)
        self.log_box.see(tk.END)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
