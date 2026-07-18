#!/usr/bin/env python3
"""PyInstaller entry point.

PyInstaller runs its entry *script* as ``__main__``, outside package
context, where a relative or self import would fail. This thin launcher
sidesteps that: the repo root is on ``sys.path``, so ``uglycraft`` imports
cleanly and we hand off to its ``main()``. For normal use prefer
``python -m uglycraft`` (which runs ``uglycraft/__main__.py``)."""
from uglycraft.main import main

main()
