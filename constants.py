LOGICAL_W = 960
LOGICAL_H = 540
TILE = 32
COLS = LOGICAL_W // TILE          # 30
ROWS = 16
STATUS_H = LOGICAL_H - ROWS * TILE  # 28

FPS = 30
TITLE = "UGLYCRAFT"
def _save_file():
    import sys, os
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.environ.get('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    data_dir = os.path.join(base, 'uglycraft')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'uglycraft.hsc')

SAVE_FILE = _save_file()

EASY = 'easy'
HARD = 'hard'

# Movement timing (milliseconds per tile move)
BASE_MOVE_MS  = 80
BASE_ENEMY_MS = 160
BOSS_MOVE_MS  = 82   # boss is ~2% slower than the player (80 ms × 1.02)

# Key-repeat timings
FIRST_REPEAT_MS = 180
REPEAT_MS       = 80

STARTING_LIVES  = 9
SHIELD_COST_PTS    = 250
SHIELD_DURATION_MS = 10_000  # shield lasts 10 seconds
WALL_HITS_TO_BREAK = 3   # bumps required to destroy one inner wall
BREAKS_PER_CREDIT  = 2   # walls to destroy to earn one placement credit

# ── Wall types ───────────────────────────────────────────────────────────────
WALL_STONE      = 'stone'       # breakable in 3 bumps (default, Act 1 + Act 2)
WALL_WOODEN     = 'wooden'      # breakable in 2 bumps (Act 2)
WALL_REINFORCED = 'reinforced'  # indestructible interior wall (Act 2)

WALL_BUMPS = {
    WALL_STONE:  3,
    WALL_WOODEN: 2,
}

# ── Act 2 constants ──────────────────────────────────────────────────────────
ACT2_START_LEVEL = 11
ACT2_BASE_MOVE_MS  = 80
ACT2_BASE_ENEMY_MS = 200
LIFE_PENALTY = 500         # flat points lost on death

# Points awarded when treasure item_no is collected (item_no 1 yields 0, 2→100, …)
TREASURE_POINTS = {1: 100, 2: 200, 3: 300, 4: 400, 5: 500,
                   6: 600, 7: 700, 8: 800, 9: 900, 10: 1000}

TREASURE_NAMES = {
    1: "Coin",       2: "Big Diamond",   3: "Small Gems",
    4: "Trophy",        5: "Gold Ingot", 6: "Platinum Ingot",
    7: "Necklace",   8: "Lantern",        9: "Emerald",
    10: "Crown",
}

# ── Palette ──────────────────────────────────────────────────────────────────
BLACK    = (  0,   0,   0)
WHITE    = (255, 255, 255)
DKGRAY   = ( 40,  40,  40)
GRAY     = (128, 128, 128)
RED      = (200,  30,  30)
DKRED    = (110,  15,  15)
ORANGE   = (230, 120,  30)
YELLOW   = (255, 210,   0)
GOLD     = (212, 175,  55)
LTGREEN  = ( 80, 220,  80)
DKGREEN  = ( 20,  80,  20)
CYAN     = (  0, 200, 220)
LTBLUE   = (100, 160, 255)
BLUE     = ( 50,  80, 200)
BROWN    = (150,  80,  30)
DKBROWN  = ( 80,  40,  10)
SILVER   = (190, 190, 200)
DKSILVER = (110, 110, 125)
MAGENTA  = (200,  50, 200)
LTYELLOW = (255, 240, 120)
CREAM    = (255, 245, 200)

HUD_BG   = ( 16,  16,  24)   # same blue-gray family as border_wall, but darker
HUD_TEXT = (255, 200, 100)
HUD_LIFE = (255,  80,  80)
HUD_KEY  = (160, 220, 255)
