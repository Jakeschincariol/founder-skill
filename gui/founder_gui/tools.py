"""Load the skills' own Python tools, so every number the GUI shows comes from the same code the terminal runs."""

import importlib.util
import math
import os

GUI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(GUI_DIR)
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

_cache = {}


def load(folder, name):
    key = (folder, name)
    if key not in _cache:
        path = os.path.join(SKILLS_DIR, folder, name + ".py")
        spec = importlib.util.spec_from_file_location("founder_gui_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[key] = mod
    return _cache[key]


def unit_economics():
    return load("founder-cfo", "unit_economics")


def panel():
    return load("founder-consumer", "panel")


def pricing():
    return load("founder-pricing", "van_westendorp")


def compile_plan():
    return load("founder-plan", "compile")


def clean(obj):
    """Make a value JSON-safe for the browser: tuples to lists, inf and nan to None."""
    if isinstance(obj, float):
        return None if (math.isinf(obj) or math.isnan(obj)) else obj
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    return obj
