"""Materials, tools, recipes, and inventory for Act 2 crafting."""
from uglycraft.constants import WALL_STONE


# ── Material types ────────────────────────────────────────────────────────────

MAT_ROCKS   = 'rocks'
MAT_PLANKS  = 'planks'
MAT_METAL   = 'metal'
MAT_CRYSTAL = 'crystal'

MATERIAL_NAMES = {
    MAT_ROCKS:   'Rocks',
    MAT_PLANKS:  'Planks',
    MAT_METAL:   'Scrap Metal',
    MAT_CRYSTAL: 'Forge Crystal',
}

MATERIAL_ICONS = {
    MAT_ROCKS:   'icon_rocks',
    MAT_PLANKS:  'icon_planks',
    MAT_METAL:   'icon_metal',
    MAT_CRYSTAL: 'icon_crystal',
}

# ── Tool types ────────────────────────────────────────────────────────────────

TOOL_HAMMER    = 'hammer'
TOOL_CHISEL    = 'chisel'
TOOL_RUNESTONE = 'runestone'

TOOL_NAMES = {
    TOOL_HAMMER:    'Hammer',
    TOOL_CHISEL:    'Chisel',
    TOOL_RUNESTONE: 'Runestone',
}

TOOL_ICONS = {
    TOOL_HAMMER:    'icon_hammer',
    TOOL_CHISEL:    'icon_chisel',
    TOOL_RUNESTONE: 'icon_runestone',
}

# ── Craftable item types ──────────────────────────────────────────────────────

CRAFT_BLOCK   = 'block'
CRAFT_BRIDGE       = 'bridge'
CRAFT_BELL         = 'bell'
CRAFT_BARRICADE    = 'barricade'
CRAFT_PORTAL_PAIR  = 'portal_pair'
CRAFT_COMPASS      = 'compass'

CRAFT_NAMES = {
    CRAFT_BLOCK:  'Block',
    CRAFT_BRIDGE:      'Bridge',
    CRAFT_BELL:        'Bell',
    CRAFT_BARRICADE:   'Barricade',
    CRAFT_PORTAL_PAIR: 'Portal Pair',
    CRAFT_COMPASS:     'Compass',
}

CRAFT_ICONS = {
    CRAFT_BLOCK:  'icon_block',
    CRAFT_BRIDGE:      'icon_bridge',
    CRAFT_BELL:        'icon_bell',
    CRAFT_BARRICADE:   'icon_barricade',
    CRAFT_PORTAL_PAIR: 'icon_portal_pair',
    CRAFT_COMPASS:     'icon_compass',
}

# ── Recipes ───────────────────────────────────────────────────────────────────
# Each recipe: (result, {material: count}, required_tool_or_None)

# Blocks and bridges are earned as credits, not crafted (spec 0073 D2): the
# player collects rubble / planks (or mines walls) to bank half-credits and
# builds by placing.  Only the (still-dormant) advanced recipes remain.
RECIPES = [
    (CRAFT_BELL,        {MAT_METAL: 3},                        TOOL_HAMMER),
    (CRAFT_BARRICADE,   {MAT_ROCKS: 2, MAT_PLANKS: 1},        TOOL_CHISEL),
    (CRAFT_PORTAL_PAIR, {MAT_CRYSTAL: 2},                      TOOL_RUNESTONE),
    (CRAFT_COMPASS,     {MAT_METAL: 1, MAT_CRYSTAL: 1},       TOOL_RUNESTONE),
]


# ── Key colours ───────────────────────────────────────────────────────────────

KEY_RED    = 'red'
KEY_BLUE   = 'blue'
KEY_GREEN  = 'green'
KEY_YELLOW = 'yellow'
KEY_CYAN   = 'cyan'
KEY_PURPLE = 'purple'
KEY_ORANGE = 'orange'

KEY_COLORS = {
    KEY_RED:    (220,  50,  50),
    KEY_BLUE:   ( 80, 140, 255),
    KEY_GREEN:  ( 60, 200,  80),
    KEY_YELLOW: (220, 200,  50),
    KEY_CYAN:   ( 50, 200, 220),
    KEY_PURPLE: (160,  80, 255),
    KEY_ORANGE: (230, 120,  40),
}

KEY_NAMES = {
    KEY_RED:    'Red Key',
    KEY_BLUE:   'Blue Key',
    KEY_GREEN:  'Green Key',
    KEY_YELLOW: 'Yellow Key',
    KEY_CYAN:   'Cyan Key',
    KEY_PURPLE: 'Purple Key',
    KEY_ORANGE: 'Orange Key',
}


class Inventory:
    """Player inventory for Act 2: materials, tools, crafted items."""

    def __init__(self):
        self.materials = {
            MAT_ROCKS: 0,
            MAT_PLANKS: 0,
            MAT_METAL: 0,
            MAT_CRYSTAL: 0,
        }
        self.tools = set()
        self.keys = {}  # {key_color: count}
        self.crafted = {}  # {craft_type: count}
        self.active_item = CRAFT_BLOCK

    def add_material(self, mat_type, count=1):
        if mat_type in self.materials:
            self.materials[mat_type] += count

    def add_tool(self, tool_type):
        self.tools.add(tool_type)

    def add_key(self, key_color):
        self.keys[key_color] = self.keys.get(key_color, 0) + 1

    def use_key(self, key_color):
        if self.keys.get(key_color, 0) > 0:
            self.keys[key_color] -= 1
            return True
        return False

    def has_key(self, key_color):
        return self.keys.get(key_color, 0) > 0

    def can_craft(self, recipe_idx):
        result, ingredients, tool = RECIPES[recipe_idx]
        if tool and tool not in self.tools:
            return False
        for mat, count in ingredients.items():
            if self.materials.get(mat, 0) < count:
                return False
        return True

    def craft(self, recipe_idx):
        if not self.can_craft(recipe_idx):
            return False
        result, ingredients, tool = RECIPES[recipe_idx]
        for mat, count in ingredients.items():
            self.materials[mat] -= count
        self.crafted[result] = self.crafted.get(result, 0) + 1
        return True

    def has_item(self, craft_type):
        return self.crafted.get(craft_type, 0) > 0

    def use_item(self, craft_type):
        if self.crafted.get(craft_type, 0) > 0:
            self.crafted[craft_type] -= 1
            return True
        return False

