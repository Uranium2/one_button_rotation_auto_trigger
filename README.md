WoW One-Button Rotation Auto Trigger
=================================

Lightweight personal tool to detect the One-Button Rotation suggestion icon in World of Warcraft and send a mapped key press.

Note on in-game overlays
------------------------
Detection is more reliable when UI overlays around the spell icon (assist arrow, hotkey labels, glows, key-press flashes) are disabled. A recommended addon that provides fine-grained control is "Just Assisted Combat".

Install the addon from CurseForge:

https://www.curseforge.com/wow/addons/just-assisted-combat

Recommended addon settings (in-game, AddOn settings) to improve detection:

- Remove/disable hotkey labels for the action bar.
- Set Highlight Mode to "No Glows" (so the yellow/red glows are not rendered).
- Disable "Show Key Press Flash" (removes flash effects when pressing keys).

Install options: use the CurseForge client or place the addon folder into your
`_retail_/Interface/AddOns` directory.

Disclaimer
----------
This tool interacts with the game screen and simulates key presses. Using
automation tools may violate the World of Warcraft Terms of Service or EULA.
Use this software at your own risk. I am not responsible for any account
suspensions or bans that may result from using this tool. Additionally, I do
not claim ownership of any game icons, images or assets: those are property
of their respective owners.
WoW One-Button Rotation Auto Trigger
===================================

Lightweight Windows-only tool that watches the in-game One-Button Rotation
suggestion icon and simulates a mapped key press when a known spell icon is
detected.

Requirements
------------
- Windows 10 or 11 (tool is developed and tested on Windows)
- Python 3.11+ installed and available from the Command Prompt
- Dev/runtime dependencies are declared in `pyproject.toml` (the project
  uses `uv` to install/run)

Quick overview
--------------
- Start the UI, select a class and spec, configure the on-screen region that
  contains the rotation suggestion icon, and map spells to keys. The scanner
  runs in the background and will press the mapped key when the detected
  icon changes.

Installation (Windows — using Command Prompt)
---------------------------------------------
1. Open Command Prompt (cmd) and install `uv`:

   ```
   pip install uv
   ```

2. Use `uv` to install runtime dependencies from `pyproject.toml` and the lock
   file:

   ```
   uv sync
   ```

3. Run the app from `main.py` (recommended using `uv run` so the locked
   environment is used):

   ```
   uv run python main.py
   ```

   If you prefer, you can run `python main.py` after installing dependencies
   with `pip` -> `python -m pip install -r requirements.txt`

Configuration — UI workflow
---------------------------
- Class & Spec: choose a Class and Spec from the dropdowns in the main window.
- Configure Region: click "Configure Region" and draw a rectangle over the
  in-game rotation suggestion icon (the app will capture this area each
  scan cycle). I recommand to use the Addon `Just Assisted Combat` use the
  largest icone size possible and Configure the Region over the first Spell.
- Configure Spell Mapping: opens the mapping dialog where each known icon for
  the selected class/spec is listed. For each icon you assign the key that
  should be sent when that icon is detected.
- Start / Pause: toggle the scanner using hotkey.
- Toggle Hotkey: set the global hotkey in the main window. The hotkey is
  registered globally (works when the game is focused) and saved to the
  profile metadata.

Trigger key format
------------------
The mapping UI accepts simple keys, modifier combinations and mixed
keyboard+mouse combos. Tokens are case- and spacing-tolerant and are joined
with `+`. The app normalizes common synonyms (for example `control` → `ctrl`,
`scrollup` → `wheel_up`).

Examples:

- `1` — numeric key 1
- `space` — the space bar
- `ctrl+a` or `ctrl + a` — Ctrl + A
- `ctrl+wheel_up` or `ctrl+scrollup` — hold Ctrl and scroll up (mapped to a
  fixed 5 notches)
- `alt+mouse4` or `side1` — hold Alt and press the first extra mouse button

Supported mouse tokens (use these names in mappings): `wheel_up`,
`wheel_down`, `left_click`, `right_click`, `middle_click`, `mouse_down`,
`mouse_up`, `mouse4`, `mouse5`, `xbutton1`, `xbutton2`, `side1`, `side2`.

Notes:
- Wheel amount: the scanner uses a fixed 5-notch scroll for `wheel_up`/
  `wheel_down`.
- Modifier keys (Ctrl/Alt/Shift/Win) are sent with `pydirectinput`.
- Mouse/wheel/extra-button events are synthesized via the OS (Win32) so they
  reliably pair with the on-screen mouse actions.
- The value you enter is forwarded to `core.input_sender.press_key()`; test
  unusual combos in the app if unsure.

Configuration file
------------------
Profiles and metadata are stored in `config/profiles.json`. The UI manages this
file automatically; manual edits are possible but not recommended. The
structure includes a top-level `_meta` object used for things like the last
selected class/spec and the registered hotkey. Example snippet:

```json
{
  "_meta": { "last_class": "mage", "last_spec": "fire", "hotkey": "=" },
  "mage_fire": {
    "region": { "x": 1420, "y": 820, "width": 64, "height": 64 },
    "spell_mapping": { "fireball": "1", "pyroblast": "2" }
  }
}
```

If you edit `config/profiles.json` by hand, ensure you keep valid JSON and
that keys follow the expected shapes (see `core/profile_manager.py`).

You can delete `config/profiles.json` if the file is corrupted.

Updating the base icon data (scraping from Wowhead)
--------------------------------------------------
The project ships with a simple scraper used to build the base icon dataset
from Wowhead. The scraper script is `wowhead_spell_scraper.py` and the
generated output lives in `data/` as files named like
`<class>_<spec>_spell_icon_urls.txt` and accompanying `_debug.html` files.

Typical workflow to refresh or extend the icon dataset:

1. Run `wowhead_spell_scraper.py` to generate/update the URL lists under
   `data/`.
3. Use the saved URLs or download the PNGs to `data/icons/<class>/<spec>/` to
   update the local icon files used by the matcher.

Note: the scraper is a convenience tool and depends on Wowhead's page layout
— if Wowhead changes layout the scraper may need adjustments. Respect
Wowhead's robots policy and copyright when scraping.

Troubleshooting
---------------
- If the global hotkey registration fails, ensure you run the app without
  restrictions and that the `keyboard` package supports your environment.
- If detection seems unreliable, try disabling in-game overlays (see the top
  of this file) or re-capture the region with a tight box around the icon.
  Set the `single button assistant` in big with no extra layout on it.
  No Yellow arrow, no dot for range check, no keybind, no blink, no GCD.
- Missing dependencies: run `uv sync` again or `pip install` the packages in
  `pyproject.toml` (see `pyproject.toml` for the exact list).

Legal / Disclaimer
------------------
This tool captures screen pixels and sends simulated keyboard input. Using
automation with online games may violate the game's Terms of Service or EULA.
Use at your own risk. The author takes no responsibility for account
penalties. Game icons and assets belong to their respective owners.

Files of interest
-----------------
- `main.py` — application entry point
- `ui/main_window.py` — main Tkinter UI
- `core/profile_manager.py` — profile persistence (`config/profiles.json`)
- `core/matcher.py` — image matcher implementation
- `wowhead_spell_scraper.py` — helper to build icon URL lists from Wowhead
