from mcdreforged.api.all import RColor

# --- 字段别称映射 ---
PROP_ALIASES = {
    'title': 'title',
    'desc': 'description', 'description': 'description',
    'stat': 'status', 's': 'status', 'status': 'status',
    'tier': 'tier', 't': 'tier',
    'prio': 'priority', 'p': 'priority', 'priority': 'priority'
}

# --- 列表字段别称映射 (支持 append/remove) ---
LIST_PROP_ALIASES = {
    'collab': 'collaborators', 'c': 'collaborators', 'collaborators': 'collaborators', 'collaborator': 'collaborators',
    'dep': 'dependencies', 'd': 'dependencies', 'dependencies': 'dependencies', 'dependency': 'dependencies',
    'label': 'labels', 'l': 'labels', 'labels': 'labels'
}

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