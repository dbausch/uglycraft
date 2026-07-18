"""Import-isolation test for the World extraction (spec 0045 W6).

world.py is the pygame-free rules layer: importing it (and everything it
pulls in — constants, levels, entities, rooms, crafting, levelgraph,
levellayout) must never import pygame.  Checked in a subprocess so the
test is immune to whatever the pytest process itself has already imported.
"""
import os
import subprocess
import sys

_CHECK = """
import sys
from uglycraft import world
offenders = sorted(m for m in sys.modules if m.split('.')[0] == 'pygame')
assert not offenders, f'importing world pulled in pygame: {offenders}'
assert hasattr(world, 'World')
"""


def test_world_imports_without_pygame():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    res = subprocess.run([sys.executable, '-c', _CHECK], cwd=root,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
