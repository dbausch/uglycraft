"""Materials, tools, recipes, and inventory for Act 2 crafting."""
from constants import WALL_STONE


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

# ── Tool types ────────────────────────────────────────────────────────────────

TOOL_HAMMER    = 'hammer'
TOOL_CHISEL    = 'chisel'
TOOL_RUNESTONE = 'runestone'

TOOL_NAMES = {
    TOOL_HAMMER:    'Hammer',
    TOOL_CHISEL:    'Chisel',
    TOOL_RUNESTONE: 'Runestone',
}

# ── Craftable item types ──────────────────────────────────────────────────────

CRAFT_STONE_WALL   = 'stone_wall'
CRAFT_BRIDGE       = 'bridge'
CRAFT_BELL         = 'bell'
CRAFT_BARRICADE    = 'barricade'
CRAFT_PORTAL_PAIR  = 'portal_pair'
CRAFT_COMPASS      = 'compass'

CRAFT_NAMES = {
    CRAFT_STONE_WALL:  'Stone Wall',
    CRAFT_BRIDGE:      'Bridge',
    CRAFT_BELL:        'Bell',
    CRAFT_BARRICADE:   'Barricade',
    CRAFT_PORTAL_PAIR: 'Portal Pair',
    CRAFT_COMPASS:     'Compass',
}

# ── Recipes ───────────────────────────────────────────────────────────────────
# Each recipe: (result, {material: count}, required_tool_or_None)

RECIPES = [
    (CRAFT_STONE_WALL,  {MAT_ROCKS: 3},                        None),
    (CRAFT_BRIDGE,      {MAT_PLANKS: 2},                       None),
    (CRAFT_BELL,        {MAT_METAL: 3},                        TOOL_HAMMER),
    (CRAFT_BARRICADE,   {MAT_ROCKS: 2, MAT_PLANKS: 1},        TOOL_CHISEL),
    (CRAFT_PORTAL_PAIR, {MAT_CRYSTAL: 2},                      TOOL_RUNESTONE),
    (CRAFT_COMPASS,     {MAT_METAL: 1, MAT_CRYSTAL: 1},       TOOL_RUNESTONE),
]


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
        self.crafted = {}  # {craft_type: count}
        self.active_item = CRAFT_STONE_WALL

    def add_material(self, mat_type, count=1):
        if mat_type in self.materials:
            self.materials[mat_type] += count

    def add_tool(self, tool_type):
        self.tools.add(tool_type)

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

    def can_quick_place_wall(self):
        """Check if we have enough rocks to auto-craft and place a stone wall."""
        return self.materials.get(MAT_ROCKS, 0) >= 3

    def quick_place_wall(self):
        """Auto-craft and consume a stone wall from rocks."""
        if self.can_quick_place_wall():
            self.materials[MAT_ROCKS] -= 3
            return True
        if self.has_item(CRAFT_STONE_WALL):
            return self.use_item(CRAFT_STONE_WALL)
        return False
