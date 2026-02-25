# core/matcher.py
"""
Matcher: Hash-based matching for captured region images against cached icons.

This module keeps a simple cache of imagehash.average_hash() values for each
icon in a profile folder and matches captured images by Hamming distance.
"""

import os
import numpy as np
from PIL import Image
import imagehash


_cached_icons = {}


def load_icons_to_cache(icon_dir):
    """Load icons and compute average_hash for each icon in icon_dir.

    Stores entries under _cached_icons[icon_dir] as a mapping:
        spell_name -> { 'hash': ImageHash, 'raw': PIL.Image }
    """
    cache = {}
    if not os.path.isdir(icon_dir):
        _cached_icons[icon_dir] = cache
        return

    for icon_file in os.listdir(icon_dir):
        if not icon_file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        spell_name = os.path.splitext(icon_file)[0]
        icon_path = os.path.join(icon_dir, icon_file)
        try:
            icon_img = Image.open(icon_path).convert("RGB")
            h = imagehash.average_hash(icon_img)
            cache[spell_name] = {"hash": h, "raw": icon_img}
        except Exception as e:
            print(f"Error loading icon {icon_file}: {e}")

    _cached_icons[icon_dir] = cache


def _ensure_cache(icon_dir: str):
    """Ensure the icon_dir has been loaded into the module cache."""
    if icon_dir not in _cached_icons:
        load_icons_to_cache(icon_dir)


def match_region_with_hash_cache(captured_img, icon_dir):
    """Match captured image against cached icon hashes.

    Returns (best_match, score) where score is normalized in [0,1] (higher is
    better). If no icons are available returns (None, 0.0).
    """
    _ensure_cache(icon_dir)

    # Normalize captured image to a PIL RGB image
    if isinstance(captured_img, Image.Image):
        cap_img = captured_img.convert("RGB")
    else:
        cap_img = Image.fromarray(np.array(captured_img)).convert("RGB")

    try:
        cap_hash = imagehash.average_hash(cap_img)
    except Exception as e:
        print(f"Error computing hash for captured image: {e}")
        return None, 0.0

    best_match = None
    best_score = -1.0
    for spell_name, data in _cached_icons[icon_dir].items():
        try:
            tmpl_hash = data.get("hash")
            if tmpl_hash is None:
                continue
            dist = cap_hash - tmpl_hash
            bits = tmpl_hash.hash.size
            score = 1.0 - (dist / float(bits))
            if score > best_score:
                best_score = score
                best_match = spell_name
        except Exception as e:
            print(f"Hash compare error for {spell_name}: {e}")

    if best_match is None:
        return None, 0.0
    return best_match, float(best_score)
