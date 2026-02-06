from mcdreforged.api.all import *

from . import TodoManager
from .constants import *
from .enums import Status, Priority, Tier
from .interface import UI
from .utils import Utils


def register_commands(builder: SimpleCommandBuilder, manager: TodoManager):
    @builder.command(COMMAND_PREFIX)
    def welcome_cmd(source: CommandSource, _context: CommandContext):
        source.reply(UI.render_welcome(source.get_server()))

    @builder.command(f"{COMMAND_PREFIX} help")
    def help_cmd(source: CommandSource, _context: CommandContext):
        source.reply(UI.render_help(source.get_server()))

    @builder.command(f"{COMMAND_PREFIX} list")
    @builder.command(f"{COMMAND_PREFIX} l")
    @builder.command(f"{COMMAND_PREFIX} list <page>")
    @builder.command(f"{COMMAND_PREFIX} l <page>")
    def list_tasks(source: CommandSource, context: CommandContext):
        page = context.get("page", 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
        UI.render_paged_list(source, manager, 'todo.list.header', 'todo.list.empty', False, page)

    @builder.command(f"{COMMAND_PREFIX} archive")
    @builder.command(f"{COMMAND_PREFIX} ar")
    @builder.command(f"{COMMAND_PREFIX} archive <page>")
    @builder.command(f"{COMMAND_PREFIX} ar <page>")
    def list_archive(source: CommandSource, context: CommandContext):
        page = context.get("page", 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
        UI.render_paged_list(source, manager, 'todo.archive.header', 'todo.archive.empty', True, page)

    @builder.command(f"{COMMAND_PREFIX} add <title>")
    @builder.command(f"{COMMAND_PREFIX} a <title>")
    def add_task(source: CommandSource, context: CommandContext):
        server = source.get_server()
        creator = source.player if source.is_player else "Console"
        tid = manager.add_task(context['title'], creator)

        # 构建富文本参数
        tid_text = RText(f"#{tid}", color=RColor.green, styles=RStyle.bold)
        source.reply(Utils.info_msg(server, 'todo.msg.add_success', tid_text))

    @builder.command(f"{COMMAND_PREFIX} info <id>")
    @builder.command(f"{COMMAND_PREFIX} i <id>")
    def show_info(source: CommandSource, context: CommandContext):
        """调用重构后的 UI 渲染器展示详细信息"""
        server = source.get_server()
        tid = str(context['id'])
        task = manager.data["tasks"].get(tid)
        if not task:
            source.reply(Utils.error_msg(server, 'todo.msg.not_found'))
            return
        # 使用 interface.py 中的 render_task_info 方法
        source.reply(UI.render_task_info(tid, task, manager.data["tasks"], server))

    @builder.command(f"{COMMAND_PREFIX} append <id> <list_prop> <value>")
    @builder.command(f"{COMMAND_PREFIX} ap <id> <list_prop> <value>")
    def append_prop(source: CommandSource, context: CommandContext):
        server = source.get_server()
        real_prop = LIST_PROP_ALIASES.get(context['list_prop'].lower())
        if not real_prop:
            source.reply(Utils.error_msg(server, 'todo.msg.invalid_list_alias', context['list_prop']))
            return

        # 核心逻辑：依赖项合法性检查
        val = str(context['value'])
        if real_prop == "dependencies" and val not in manager.data["tasks"]:
            source.reply(Utils.error_msg(server, 'todo.msg.dep_not_found', val))
            return

        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), real_prop, val, editor):
            prop_text = RText(real_prop, color=RColor.yellow)
            source.reply(Utils.info_msg(server, 'todo.msg.append_success', context['id'], prop_text, val))

    @builder.command(f"{COMMAND_PREFIX} remove <id> <list_prop> <value>")
    @builder.command(f"{COMMAND_PREFIX} rm <id> <list_prop> <value>")
    def remove_prop(source: CommandSource, context: CommandContext):
        server = source.get_server()
        real_prop = LIST_PROP_ALIASES.get(context['list_prop'].lower())
        if not real_prop:
            source.reply(Utils.error_msg(server, 'todo.msg.invalid_list_alias', context['list_prop']))
            return

        editor = source.player if source.is_player else "Console"
        val = str(context['value'])

        if manager.remove_item(str(context['id']), real_prop, val, editor):
            prop_text = RText(real_prop, color=RColor.yellow)
            source.reply(Utils.info_msg(server, 'todo.msg.remove_success', context['id'], prop_text, val))
        else:
            source.reply(Utils.error_msg(server, 'todo.msg.remove_failed', val))

    @builder.command(f"{COMMAND_PREFIX} set <id> <prop> <value>")
    @builder.command(f"{COMMAND_PREFIX} s <id> <prop> <value>")
    def set_prop(source: CommandSource, context: CommandContext):
        server = source.get_server()
        alias = context['prop'].lower()
        real_prop = PROP_ALIASES.get(alias)
        if not real_prop:
            source.reply(Utils.error_msg(server, 'todo.msg.invalid_prop_alias', context['prop']))
            return

        val = context['value']

        rval = RText(val)

        if real_prop == "tier":
            validated_tier = Tier.validate(val)
            if validated_tier:
                val = validated_tier
                rval = Tier.get_rtext(val)
            else:
                tier_list = Utils.list_to_rtext([Tier.get_rtext(t.value) for t in Tier])
                source.reply(Utils.error_msg(server, 'todo.msg.invalid_tier', len(GT_TIERS) - 1, tier_list))
                return

        elif real_prop == "priority":
            validated_prio = Priority.validate(val)
            if validated_prio:
                val = validated_prio
                rval = Priority.get_rtext(val, server)
            else:
                prio_list = Utils.list_to_rtext([Priority.get_rtext(p.value) for p in Priority])
                source.reply(Utils.error_msg(server, 'todo.msg.invalid_priority', prio_list))
                return

        elif real_prop == "status":
            validated_status = Status.validate(val)
            if validated_status:
                val = validated_status
                rval = Status.get_rtext(val, server)
            else:
                status_list = Utils.list_to_rtext([Status.get_rtext(s.value) for s in Status])
                source.reply(Utils.error_msg(server, 'todo.msg.invalid_status', status_list))
                return

        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), real_prop, val, editor):
            prop_text = RText(real_prop, color=RColor.yellow)

            # 如果是 status 属性，尝试获取翻译后的文本
            if real_prop == "status":
                rval = Status.get_rtext(val, server)

            source.reply(Utils.info_msg(server, 'todo.msg.set_success', context['id'], prop_text, rval))

    @builder.command(f"{COMMAND_PREFIX} note <id> <content>")
    @builder.command(f"{COMMAND_PREFIX} n <id> <content>")
    def add_note(source: CommandSource, context: CommandContext):
        server = source.get_server()
        author = source.player if source.is_player else "Console"
        if manager.add_note(str(context['id']), context['content'], author):
            source.reply(Utils.info_msg(server, 'todo.msg.note_success', context['id']))

    @builder.command(f"{COMMAND_PREFIX} restore <id>")
    def restore_task(source: CommandSource, context: CommandContext):
        """将已归档任务恢复为进行中"""
        server = source.get_server()
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", Status.IN_PROGRESS.value, editor):
            source.reply(Utils.info_msg(server, 'todo.msg.restore_success', context['id']))

    @builder.command(f"{COMMAND_PREFIX} complete <id>")
    def complete_task(source: CommandSource, context: CommandContext):
        server = source.get_server()
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", Status.DONE.value, editor):
            source.reply(Utils.info_msg(server, 'todo.msg.complete_success', context['id']))

    @builder.command(f"{COMMAND_PREFIX} pause <id>")
    def pause_task(source: CommandSource, context: CommandContext):
        server = source.get_server()
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", Status.ON_HOLD.value, editor):
            source.reply(Utils.info_msg(server, 'todo.msg.pause_success', context['id']))

    @builder.command(f"{COMMAND_PREFIX} resume <id>")
    def resume_task(source: CommandSource, context: CommandContext):
        server = source.get_server()
        editor = source.player if source.is_player else "Console"
        if manager.update_task(str(context['id']), "status", Status.IN_PROGRESS.value, editor):
            source.reply(Utils.info_msg(server, 'todo.msg.resume_success', context['id']))

    # TODO 加入 setdefault 方法给所有 prop 设置默认值，而不是只能修改默认 tier
    @builder.command(f"{COMMAND_PREFIX} default_tier <tier>")
    def set_default_tier(source: CommandSource, context: CommandContext):  # TODO 使用通用的 setdefault 命令代替专属命令
        server = source.get_server()
        val = context['tier']
        validated_tier = Tier.validate(val)

        if validated_tier:
            manager.set_default_tier(validated_tier)
            tier_text = Tier.get_rtext(validated_tier)
            source.reply(Utils.info_msg(server, 'todo.msg.default_tier_success', tier_text))
        else:
            tier_list = Utils.list_to_rtext([Tier.get_rtext(t.value) for t in Tier])
            source.reply(Utils.error_msg(server, 'todo.msg.invalid_tier', len(GT_TIERS) - 1, tier_list))
