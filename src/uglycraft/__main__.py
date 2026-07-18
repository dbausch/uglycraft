"""Package entry point: `python -m uglycraft` runs the game.

Run this way the package is already initialised, so the absolute import
below resolves. (PyInstaller instead runs the repo-root run_game.py as
__main__ — see that file.)"""
from uglycraft.main import main

main()
