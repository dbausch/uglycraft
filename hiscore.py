"""High-score persistence — plain-text file, top-10 entries."""
import os
from constants import SAVE_FILE

MAX_ENTRIES = 10


def load_scores():
    """Return list of (name, score) sorted descending by score."""
    scores = []
    if not os.path.exists(SAVE_FILE):
        return scores
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.rsplit(None, 1)
                if len(parts) == 2:
                    try:
                        scores.append((parts[0], int(parts[1])))
                    except ValueError:
                        pass
    except OSError:
        pass
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:MAX_ENTRIES]


def save_score(name, score):
    """Append entry and rewrite file keeping top MAX_ENTRIES."""
    scores = load_scores()
    scores.append((name.strip() or "Anonymous", score))
    scores.sort(key=lambda x: x[1], reverse=True)
    scores = scores[:MAX_ENTRIES]
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            for n, s in scores:
                f.write(f"{n} {s}\n")
    except OSError:
        pass
    return scores


def qualifies(score):
    """True if score earns a place on the board."""
    if score <= 0:
        return False
    scores = load_scores()
    if len(scores) < MAX_ENTRIES:
        return True
    return score > scores[-1][1]
