# core/input_sender.py
"""
InputSender: Handles key press simulation.
"""

import time
import ctypes
import pydirectinput


def press_key(key: str) -> None:
    """Simulate a key or combined input using pydirectinput.

    Supports simple keys ("1", "space"), keyboard combos ("ctrl+shift+1")
    and mixed keyboard+mouse combos ("ctrl+wheel_up").

    Syntax examples:
      - "1" -> press the 1 key
      - "ctrl+1" -> hold ctrl, press 1, release ctrl
      - "ctrl+shift+1" -> hold ctrl+shift, press 1, release modifiers
      - "ctrl+wheel_up" -> hold ctrl, scroll wheel up, release ctrl
      - "left_click" -> left mouse click

    Mouse actions supported: wheel_up, wheel_down, left_click, right_click,
    middle_click, mouse_down, mouse_up.

    Wheel amount can be specified with a colon, e.g. "wheel_up:3".
    Side / extra mouse buttons are supported via tokens:
      - "mouse4", "mouse5", "xbutton1", "xbutton2", "side1", "side2"
    These are sent as XBUTTON1/XBUTTON2 events via Win32 API.

    Args:
        key: specification string as described above.
    """
    if not isinstance(key, str) or not key:
        return

    token_list = [t.strip().lower() for t in key.split("+") if t.strip()]

    # canonicalize common synonyms for modifiers and mouse actions
    SYNONYMS = {
        # modifiers
        "control": "ctrl",
        "lctrl": "ctrl",
        "rctrl": "ctrl",
        "ctl": "ctrl",
        "cmd": "win",
        "command": "win",
        "meta": "win",
        "option": "alt",
        # mouse/scroll synonyms
        "wheelup": "wheel_up",
        "wheel_up": "wheel_up",
        "wheel-up": "wheel_up",
        "wheeldown": "wheel_down",
        "wheel-down": "wheel_down",
        "scrollup": "wheel_up",
        "scroll_up": "wheel_up",
        "scroll-up": "wheel_up",
        "scrolldown": "wheel_down",
        "scroll_down": "wheel_down",
        "scroll-down": "wheel_down",
        "leftclick": "left_click",
        "left_click": "left_click",
        "rightclick": "right_click",
        "right_click": "right_click",
        "middleclick": "middle_click",
        "middle_click": "middle_click",
        # extra mouse buttons (side buttons)
        "mouse4": "xbutton1",
        "mouse5": "xbutton2",
        "xbutton1": "xbutton1",
        "xbutton2": "xbutton2",
        "side1": "xbutton1",
        "side2": "xbutton2",
    }

    MOUSE_ACTIONS = {
        "wheel_up",
        "wheel_down",
        "left_click",
        "right_click",
        "middle_click",
        "xbutton1",
        "xbutton2",
        "mouse_down",
        "mouse_up",
    }

    mouse_tokens = []
    key_tokens = []

    print(f"Pressing: {key} -> tokens: {token_list}")

    for tok in token_list:
        # ignore any amount suffix like wheel_up:3 — always use fixed amount
        if ":" in tok:
            name = tok.split(":", 1)[0].strip()
            base = SYNONYMS.get(name, name)
            candidate = base
        else:
            base = SYNONYMS.get(tok, tok)
            candidate = base

        if base in MOUSE_ACTIONS:
            mouse_tokens.append(candidate)
        else:
            key_tokens.append(base)

    try:
        # pure simple key
        if len(token_list) == 1 and token_list[0] not in MOUSE_ACTIONS:
            pydirectinput.press(key_tokens[0])
            return

        # if there are only keyboard tokens, use hotkey which handles modifiers
        if mouse_tokens == [] and len(key_tokens) >= 1:
            pydirectinput.hotkey(*key_tokens)
            return

        # For mixed keyboard + mouse actions:
        # Use Win32 keybd_event to press modifiers so subsequent mouse_event wheel/XBUTTON
        # events observe the modifier state. Non-modifier keys are sent via pydirectinput
        # while modifiers are held.
        MODIFIERS = {"ctrl", "alt", "shift", "win"}

        modifier_tokens = [k for k in key_tokens if k in MODIFIERS]
        normal_key_tokens = [k for k in key_tokens if k not in MODIFIERS]

        # Press modifiers using pydirectinput only. Win32 is used only for mouse/wheel/XBUTTON events.
        for m in modifier_tokens:
            pydirectinput.keyDown(m)
            time.sleep(0.02)

        # perform mouse actions in order (fixed wheel amount = 5 notches)
        for name in mouse_tokens:
            amount = 5

            if name == "wheel_up":
                WHEEL_DELTA = 120
                MOUSEEVENTF_WHEEL = 0x0800
                ctypes.windll.user32.mouse_event(
                    MOUSEEVENTF_WHEEL, 0, 0, int(abs(amount)) * WHEEL_DELTA, 0
                )
            elif name == "wheel_down":
                WHEEL_DELTA = 120
                MOUSEEVENTF_WHEEL = 0x0800
                ctypes.windll.user32.mouse_event(
                    MOUSEEVENTF_WHEEL, 0, 0, -int(abs(amount)) * WHEEL_DELTA, 0
                )
            elif name == "left_click":
                pydirectinput.click()
            elif name == "right_click":
                pydirectinput.rightClick()
            elif name == "middle_click":
                pydirectinput.middleClick()
            elif name in ("xbutton1", "xbutton2"):
                btn = 1 if name.endswith("1") else 2
                XDOWN = 0x0080
                XUP = 0x0100
                XBUTTON1 = 0x0001
                XBUTTON2 = 0x0002
                data = XBUTTON1 if btn == 1 else XBUTTON2
                ctypes.windll.user32.mouse_event(XDOWN, 0, 0, data, 0)
                time.sleep(0.01)
                ctypes.windll.user32.mouse_event(XUP, 0, 0, data, 0)
            elif name == "mouse_down":
                pydirectinput.mouseDown()
            elif name == "mouse_up":
                pydirectinput.mouseUp()

            # tiny cooldown between actions
            time.sleep(0.02)

        # press any non-modifier keys while modifiers still held
        for nk in normal_key_tokens:
            pydirectinput.press(nk)
            time.sleep(0.02)
    finally:
        # release modifiers pressed via pydirectinput
        for m in reversed(modifier_tokens):
            pydirectinput.keyUp(m)
            time.sleep(0.01)
