"""FastBot - Humanoid Robot Survival Challenge powered by FastMind"""
__version__ = "0.1.0"

import os
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PKG_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
