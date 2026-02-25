# core/scanner.py
"""
Scanner: Handles region-based screen captures.
"""

import mss
from PIL import Image


def capture_region(region):
    """
    Captures a screenshot of the specified region.

    Args:
        region (dict): A dictionary with keys 'x', 'y', 'width', 'height'.

    Returns:
        PIL.Image.Image: The captured screenshot as a Pillow Image.
    """
    """Capture a screen region and return a Pillow Image.

    `region` is expected to be a dict with keys 'x','y','width','height'.
    """
    with mss.mss() as sct:
        monitor = {
            "top": region["y"],
            "left": region["x"],
            "width": region["width"],
            "height": region["height"],
        }
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img
