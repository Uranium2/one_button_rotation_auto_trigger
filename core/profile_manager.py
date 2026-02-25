# core/profile_manager.py
"""
ProfileManager: Handles loading, saving, and updating WoW class/spec profiles.
Supports region (x, y, width, height) storage and spell mapping.

Profiles are stored in `config/profiles.json` as a mapping keyed by
"<class>_<spec>". Each profile contains `region` and `spell_mapping`.
"""

import os
import json


def get_profile_path():
    """Return absolute path to the profiles JSON file.

    The path is resolved relative to this module so callers can import this
    package from anywhere.
    """
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "profiles.json")
    )


PROFILE_PATH = get_profile_path()


def _profile_key(class_name: str, spec_name: str) -> str:
    """Return the canonical profile key for a class and spec.

    Example: "Death Knight", "Blood" -> "death_knight_blood"
    """
    return (
        f"{class_name.lower().replace(' ', '_')}_{spec_name.lower().replace(' ', '_')}"
    )


class ProfileManager:
    """Manage loading, saving and updating class/spec profiles.

    Profiles are stored as a JSON mapping keyed by "{class}_{spec}" and
    contain `region` and `spell_mapping` entries.
    """

    def __init__(self):
        """Initialize the manager and load profiles from disk."""
        self.profile_path = PROFILE_PATH
        self._profiles = {}
        self._load()

    def _load(self):
        """Load profiles from the JSON file into memory.

        If the file does not exist or is invalid the in-memory profiles dict
        will be set to an empty dict.
        """
        try:
            with open(self.profile_path, "r") as f:
                profiles = json.load(f)
                if not isinstance(profiles, dict):
                    profiles = {}
                self._profiles = profiles
        except Exception:
            self._profiles = {}

    def _save(self):
        """Persist the current profiles dict to the profiles JSON file."""
        with open(self.profile_path, "w") as f:
            json.dump(self._profiles, f, indent=2)

    def get_region(self, class_name: str, spec_name: str):
        """Return the stored region for a class/spec or None.

        Region is a dict with keys `x`, `y`, `width`, `height` or None when
        no region has been configured.
        """
        key = _profile_key(class_name, spec_name)
        profile = self._profiles.get(key)
        if isinstance(profile, dict):
            return profile.get("region")
        return None

    def set_region(self, class_name: str, spec_name: str, region_dict):
        """Validate and save a region for a given class/spec.

        The region_dict must contain integer keys `x`, `y`, `width`, `height`.
        """
        if not isinstance(region_dict, dict) or not all(
            k in region_dict for k in ("x", "y", "width", "height")
        ):
            raise ValueError("Region dict must have x, y, width, height keys.")
        key = _profile_key(class_name, spec_name)
        if key not in self._profiles or not isinstance(self._profiles.get(key), dict):
            self._profiles[key] = {"region": None, "spell_mapping": {}}
        self._profiles[key]["region"] = region_dict
        self._save()

    def get_spell_mapping(self, class_name: str, spec_name: str):
        """Return the spell->key mapping for a class/spec.

        Returns an empty dict if no mapping is present.
        """
        key = _profile_key(class_name, spec_name)
        profile = self._profiles.get(key)
        if isinstance(profile, dict):
            return profile.get("spell_mapping", {})
        return {}

    def set_spell_mapping(self, class_name: str, spec_name: str, mapping_dict):
        """Save a spell-to-key mapping for the class/spec and persist it."""
        key = _profile_key(class_name, spec_name)
        if key not in self._profiles or not isinstance(self._profiles.get(key), dict):
            self._profiles[key] = {"region": None, "spell_mapping": {}}
        self._profiles[key]["spell_mapping"] = mapping_dict
        self._save()

    def get_last_selected(self):
        """Return the last selected (class, spec) tuple or None.

        The value is read from a top-level '_meta' entry in the profiles JSON.
        """
        meta = self._profiles.get("_meta")
        if isinstance(meta, dict):
            last_class = meta.get("last_class")
            last_spec = meta.get("last_spec")
            if last_class and last_spec:
                return last_class, last_spec
        return None

    def set_last_selected(self, class_name: str, spec_name: str):
        """Store the last selected class/spec into the profiles JSON under '_meta'."""
        meta = self._profiles.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["last_class"] = class_name
        meta["last_spec"] = spec_name
        self._profiles["_meta"] = meta
        self._save()

    def get_hotkey(self):
        """Return the configured global toggle hotkey (string) or None."""
        meta = self._profiles.get("_meta")
        if isinstance(meta, dict):
            return meta.get("hotkey")
        return None

    def set_hotkey(self, hotkey: str):
        """Persist the configured global toggle hotkey under '_meta'."""
        meta = self._profiles.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["hotkey"] = hotkey
        self._profiles["_meta"] = meta
        self._save()


def get_icon_dir(class_name: str, spec_name: str) -> str:
    """Return the absolute path to the icon directory for the class/spec."""
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "icons",
            class_name.lower().replace(" ", "_"),
            spec_name.lower().replace(" ", "_"),
        )
    )
