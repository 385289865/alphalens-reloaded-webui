#!/usr/bin/env python3
"""Alphalens Service Manager - Interactive Menu Mode.

Usage:
    python -m alphalens              Interactive menu mode
    python -m alphalens --mode prod   Production mode
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alphalens import _ensure_dirs
from manage import cli

if __name__ == "__main__":
    _ensure_dirs()
    # Invoke the 'menu' subcommand directly
    sys.argv = ["alphalens", "menu"] + [a for a in sys.argv[1:] if a]
    cli()
