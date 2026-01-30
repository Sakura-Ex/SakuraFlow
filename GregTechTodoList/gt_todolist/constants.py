from mcdreforged.api.all import RColor, RText
from .enums import Status, Priority


# --- Helper Functions ---
def _generate_aliases(prop_def: dict) -> dict:
    """自动生成别称映射"""
    aliases = {}
    for prop, alias_list in prop_def.items():
        for alias in alias_list:
            aliases[alias] = prop
    return aliases


# --- Property Definitions ---
# 结构: { 标准属性名: [别名列表] }
TASK_PROPERTIES = {
    'title': ['title'],
    'description': ['desc', 'description'],
    'status': ['stat', 's', 'status'],
    'tier': ['tier', 't'],
    'priority': ['prio', 'p', 'priority']
}

LIST_PROPERTIES = {
    'collaborators': ['collab', 'c', 'collaborators', 'collaborator'],
    'dependencies': ['dep', 'd', 'dependencies', 'dependency'],
    'labels': ['label', 'l', 'labels']
}

PROP_ALIASES = _generate_aliases(TASK_PROPERTIES)
LIST_PROP_ALIASES = _generate_aliases(LIST_PROPERTIES)

# --- Status Configuration ---
STATUS_DONE = Status.DONE.value
STATUS_IN_PROGRESS = Status.IN_PROGRESS.value
STATUS_ON_HOLD = Status.ON_HOLD.value

# --- Tier Configuration ---
GT_TIERS = [
    'ULV', 'LV', 'MV', 'HV', 'EV', 'IV', 'LuV', 'ZPM',
    'UV', 'UHV', 'UEV', 'UIV', 'UXV', 'OpV', 'MAX'
]

TIER_COLORS = {
    'ULV': RColor.dark_gray,
    'LV': RColor.gray,
    'MV': RColor.aqua,
    'HV': RColor.gold,
    'EV': RColor.dark_purple,
    'IV': RColor.blue,
    'LuV': RColor.light_purple,
    'ZPM': RColor.red,
    'UV': RColor.dark_aqua,
    'UHV': RColor.dark_red,
    'UEV': RColor.green,
    'UIV': RColor.dark_green,
    'UXV': RColor.yellow,
    'OpV': RColor.blue,
    'MAX': RColor.red
}

# --- Priority Configuration ---
# 保持向后兼容，虽然推荐使用 Priority 枚举
PRIORITIES = [p.value for p in Priority]

# --- UI Formatting ---
LIST_ITEM_SEPERATOR = RText(", ", color=RColor.gray)
COLON = RText(": ", color=RColor.gray)
ITEMIZE_PREFIX = [
    RText("• ", color=RColor.gray),
    RText("- ", color=RColor.gray),
    RText("* ", color=RColor.gray),
    RText("· ", color=RColor.gray)
]
