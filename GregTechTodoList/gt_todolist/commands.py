from mcdreforged.api.all import *

from . import TodoManager
from .constants import *
from .interface import UI


def register_commands(builder: SimpleCommandBuilder, manager: TodoManager, server: PluginServerInterface):
    @builder.command("!!todo")
    def welcome_cmd(source: CommandSource, _context: CommandContext):
        source.reply(UI.render_welcome())

    @builder.command("!!todo help")
    def help_cmd(source: CommandSource, _context: CommandContext):
        source.reply(UI.render_help())

    @builder.command("!!todo list")
    @builder.command("!!todo l")
    def list_tasks(source: CommandSource, _context: CommandContext):
        source.reply(RText("======= [ GregTech Todo List ] =======", color=RColor.gold))
        tasks_found = False
        for tid, task in manager.data["tasks"].items():
            if task["status"] != STATUS_DONE:
                source.reply(UI.render_task_line(tid, task, manager.data["tasks"]))
                tasks_found = True
        if not tasks_found:
            source.reply("§7(当前没有进行中的任务)")

    @builder.command("!!todo archive")
    @builder.command("!!todo ar")
    def list_archive(source: CommandSource, _context: CommandContext):
        source.reply(RText("======= [ GT 已归档任务 ] =======", color=RColor.gold))
        tasks_found = False
        for tid, task in manager.data["tasks"].items():
            if task["status"] == STATUS_DONE:
                # 同样调用 UI.render_task_line，它现在能自动适配已完成状态
                source.reply(UI.render_task_line(tid, task, manager.data["tasks"]))
                tasks_found = True
        if not tasks_found:
            source.reply("§7(归档记录为空)")

    @builder.command("!!todo add <title>")
    @builder.command("!!todo a <title>")
    def add_task(source: CommandSource, context: CommandContext):
        creator = source.player if source.is_player else "Console"
        tid = manager.add_task(context['title'], creator)
        source.reply(f"§a任务 §l#{tid} §r§a已成功立项！")

    @builder.command("!!todo info <id>")
    @builder.command("!!todo i <id>")
    def show_info(source: CommandSource, context: CommandContext):
        """调用重构后的 UI 渲染器展示详细信息"""
        tid = str(context['id'])
        task = manager.data["tasks"].get(tid)
        if not task:
            source.reply("§c未找到任务 ID")
            return
        # 使用 interface.py 中的 render_task_info 方法
        source.reply(UI.render_task_info(tid, task, manager.data["tasks"]))

    @builder.command("!!todo append <id> <list_prop> <value>")
    @builder.command("!!todo ap <id> <list_prop> <value>")
    def append_prop(source: CommandSource, context: CommandContext):
        real_prop = LIST_PROP_ALIASES.get(context['list_prop'].lower())
        if not real_prop:
            source.reply(f"§c无效列表别称: {context['list_prop']}")
            return

        # 核心逻辑：依赖项合法性检查
        val = str(context['value'])
        if real_prop == "dependencies" and val not in manager.data["tasks"]:
            source.reply(f"§c引用错误：任务 #{val} 不存在，无法添加为前置依赖")
            return

        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), real_prop, val, editor):
            source.reply(f"§a已向任务 #{context['id']} 列表 §e{real_prop} §a追加: §f{val}")

    @builder.command("!!todo remove <id> <list_prop> <value>")
    @builder.command("!!todo rm <id> <list_prop> <value>")
    def remove_prop(source: CommandSource, context: CommandContext):
        real_prop = LIST_PROP_ALIASES.get(context['list_prop'].lower())
        if not real_prop:
            source.reply(f"§c无效列表别称: {context['list_prop']}")
            return

        editor = source.player if source.is_player else "Console"
        val = str(context['value'])

        if manager.remove_item(str(context['id']), real_prop, val, editor):
            source.reply(f"§a已从任务 #{context['id']} 的 §e{real_prop} §a中移除: §f{val}")
        else:
            source.reply(f"§c移除失败：项 §f{val} §c不在列表内或任务 ID 错误")

    @builder.command("!!todo set <id> <prop> <value>")
    @builder.command("!!todo s <id> <prop> <value>")
    def set_prop(source: CommandSource, context: CommandContext):
        alias = context['prop'].lower()
        real_prop = PROP_ALIASES.get(alias)
        if not real_prop:
            source.reply(f"§c无效属性别称: {context['prop']}")
            return

        val = context['value']

        rval = RText(val)

        if real_prop == "tier":
            tier_map = {t.upper(): t for t in GT_TIERS}
            if val.isdigit():
                idx = int(val)
                if 0 <= idx < len(GT_TIERS):
                    val = GT_TIERS[idx]
                else:
                    source.reply(f"§c[错误] 电压等级数字越界！合法范围: 0-{len(GT_TIERS) - 1}")
                    return
            elif val.upper() in tier_map:
                val = tier_map[val.upper()]
            else:
                source.reply(f"§c[错误] 无效的电压名称！可选: {', '.join(GT_TIERS)}")
                return
            rval = RText(val, color=UI.get_tier_color(val))

        elif real_prop == "priority":
            prio_map = {p.upper(): p for p in PRIORITIES}
            no_space_map = {p.replace(' ', '').upper(): p for p in PRIORITIES}

            if val.isdigit():
                idx = int(val)
                if 0 <= idx < len(PRIORITIES):
                    val = PRIORITIES[idx]
                else:
                    source.reply(f"§c[错误] 优先级数字越界！合法范围: 0-4 (0=Very High, 4=Very Low)")
                    return
            elif val.upper() in prio_map:
                val = prio_map[val.upper()]
            elif val.upper() in no_space_map:
                val = no_space_map[val.upper()]
            else:
                source.reply(f"§c[错误] 无效优先级！请输入 0-4 或名称: {', '.join(PRIORITIES)}")
                return
            rval = RText(val, color=UI.get_priority_color(val))

        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), real_prop, val, editor):
            # 成功反馈：包含带有颜色的 rval
            source.reply(RTextList(f"§a任务 #{context['id']} 属性 §e{real_prop} §a已更新为 ", rval))

    @builder.command("!!todo note <id> <content>")
    @builder.command("!!todo n <id> <content>")
    def add_note(source: CommandSource, context: CommandContext):
        author = source.player if source.is_player else "Console"
        if manager.add_note(str(context['id']), context['content'], author):
            source.reply(f"§a进度已记录至任务 #{context['id']}")

    @builder.command("!!todo restore <id>")
    def restore_task(source: CommandSource, context: CommandContext):
        """将已归档任务恢复为进行中"""
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", STATUS_IN_PROGRESS, editor):
            source.reply(f"§b任务 #{context['id']} 已从归档中恢复至进行中状态 ▶")

    @builder.command("!!todo complete <id>")
    def complete_task(source: CommandSource, context: CommandContext):
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", STATUS_DONE, editor):
            source.reply(f"§a任务 #{context['id']} 已完工并移入归档 ✔")

    @builder.command("!!todo pause <id>")
    def pause_task(source: CommandSource, context: CommandContext):
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", STATUS_ON_HOLD, editor):
            source.reply(f"§a任务 #{context['id']} 已标记为暂停 ⏸")

    @builder.command("!!todo resume <id>")
    def resume_task(source: CommandSource, context: CommandContext):
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", STATUS_IN_PROGRESS, editor):
            source.reply(f"§a任务 #{context['id']} 已恢复运行 ▶")
