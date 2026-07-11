"""Spec 0054 / BL-40 — level generation must not depend on PYTHONHASHSEED.

The same game seed must produce byte-identical level content in every
Python process.  PYTHONHASHSEED salts str hashing, so any str-set iteration
order leaking into an rng pool makes generation process-dependent; this test
runs the canonical-hash probe (tests/_gen_hash.py) in subprocesses under
different hash seeds and requires one single hash per level.

Level 13 / seed 777: multi-grid, the known pre-fix failing case (4 distinct
hashes across PYTHONHASHSEED=0..3).  Level 11 / seed 777: single-grid
control, already stable pre-fix.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _probe(level, seed, hashseed):
    env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
    out = subprocess.run(
        [sys.executable, '-m', 'tests._gen_hash', str(level), str(seed)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


@pytest.mark.parametrize('level', [11, 13])
def test_generation_ignores_hash_seed(level):
    hashes = {_probe(level, 777, hs) for hs in (0, 1, 2)}
    assert len(hashes) == 1, (
        f'level {level} seed 777 content varies with PYTHONHASHSEED: '
        f'{sorted(hashes)}')
