LOGICAL_W = 960
LOGICAL_H = 540
TILE = 32
COLS = LOGICAL_W // TILE          # 30
ROWS = 16
STATUS_H = LOGICAL_H - ROWS * TILE  # 28

FPS = 30
TITLE = "UGLYCRAFT"
SAVE_FILE = "uglycraft.hsc"

EASY = 'easy'
HARD = 'hard'

# Movement timing (milliseconds per tile move)
BASE_MOVE_MS  = 80
BASE_ENEMY_MS = 160
BOSS_MOVE_MS  = 80   # boss moves at the same speed as the player

# Key-repeat timings
FIRST_REPEAT_MS = 180
REPEAT_MS       = 80

STARTING_LIVES  = 9
SHIELD_COST_PTS    = 1000
WALL_HITS_TO_BREAK = 3   # bumps required to destroy one inner wall
BREAKS_PER_CREDIT  = 2   # walls to destroy to earn one placement credit
LIFE_COST_PTS      = 5000
LIFE_PENALTY = 500         # flat points lost on death

# Points awarded when treasure item_no is collected (item_no 1 yields 0, 2→100, …)
TREASURE_POINTS = {1: 0, 2: 100, 3: 200, 4: 300, 5: 400,
                   6: 500, 7: 600, 8: 700, 9: 800}

TREASURE_NAMES = {
    1: "Rope",       2: "Big Diamond",   3: "Small Gems",
    4: "Small Diamond", 5: "Gold Bar",   6: "Silver Bar",
    7: "Well",       8: "Lamp",          9: "Big Gem",
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
