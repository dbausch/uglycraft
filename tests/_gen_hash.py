"""Canonical-content hash probe for generated levels (spec 0054 / BL-40).

Run as:  python -m tests._gen_hash <level> <seed>

Prints a sha256 over the recursively sorted content of
levels.get_level(<level>) under set_game_seed(<seed>) — collections are
canonicalised so only real content differences change the hash, never
iteration order.

Not a test module (no test_ prefix); executed in subprocesses with varying
PYTHONHASHSEED by tests/test_generation_determinism.py.
"""
import hashlib
import json
import sys

from uglycraft import levels


def canonical(obj):
    if isinstance(obj, dict):
        return sorted((str(k), canonical(v)) for k, v in obj.items())
    if isinstance(obj, (list, tuple, set, frozenset)):
        return sorted(str(canonical(x)) for x in obj)
    return obj


def level_hash(level_num, seed):
    levels.set_game_seed(seed)
    d = levels.get_level(level_num)
    return hashlib.sha256(
        json.dumps(canonical(d), default=str).encode()).hexdigest()


if __name__ == '__main__':
    print(level_hash(int(sys.argv[1]), int(sys.argv[2])))
