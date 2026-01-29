from mcdreforged.api.all import RColor

# --- 属性定义 ---
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

# --- 自动生成别称映射 ---
def _generate_aliases(prop_def: dict) -> dict:
    aliases = {}
    for prop, alias_list in prop_def.items():
        for alias in alias_list:
            aliases[alias] = prop
    return aliases

PROP_ALIASES = _generate_aliases(TASK_PROPERTIES)
LIST_PROP_ALIASES = _generate_aliases(LIST_PROPERTIES)

# --- 格雷科技电压等级映射 ---
GT_TIERS = [
    'ULV', 'LV', 'MV', 'HV', 'EV', 'IV', 'LuV', 'ZPM', 
    'UV', 'UHV', 'UEV', 'UIV', 'UXV', 'OpV', 'MAX'
]

# --- 电压专属颜色映射 ---
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

PRIORITIES = [
    'Very High', 'High', 'Medium', 'Low', 'Very Low'
]

PRIORITY_COLORS = {
    'Very High': RColor.dark_red,
    'High': RColor.red,
    'Medium': RColor.yellow,
    'Low': RColor.green,
    'Very Low': RColor.gray
}

STATUS_COLORS = {
    'Done': RColor.green,
    'In Progress': RColor.aqua,
    'On Hold': RColor.red
}

# --- 任务状态标识 ---
STATUS_DONE = "Done"
STATUS_IN_PROGRESS = "In Progress"
STATUS_ON_HOLD = "On Hold"