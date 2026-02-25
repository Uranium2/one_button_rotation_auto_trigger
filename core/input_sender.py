# core/input_sender.py
"""
InputSender: Handles key press simulation.
"""

import pydirectinput


def press_key(key):
    """Simulate pressing `key` using pydirectinput.

    Args:
        key (str): Key string understood by pydirectinput (eg. '1', 'space').
    """
    pydirectinput.press(key)
