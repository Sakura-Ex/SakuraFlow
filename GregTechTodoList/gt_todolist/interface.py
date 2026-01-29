from mcdreforged.api.all import *
from .constants import *
from .utils import Utils


class UI:
    @staticmethod
    def make_header(title: str = "", width: int = 50) -> str:
        """生成居中的标题分割线"""
        if not title:
            return "=" * width
        
        # 格式：======= [ 标题 ] =======
        # 左右各留一个空格，标题两侧加 [ ]
        inner_text = f" [ {title} ] "
        remaining = width - len(inner_text)
        if remaining < 0:
            return inner_text # 标题过长则直接返回
            
        left_pad = remaining // 2
        right_pad = remaining - left_pad
        
        return "=" * left_pad + inner_text + "=" * right_pad

    @staticmethod
    def create_hover_info(tid: str, task: dict, tasks_db: dict, server: ServerInterface) -> RTextBase:
        """通用的任务悬浮矩阵生成器"""
        dep_display = []
        for d_id in task.get("dependencies", []):
            d_task = tasks_db.get(str(d_id))
            is_d_done = d_task and d_task.get("status") == STATUS_DONE
            symbol = RText("✔", color=RColor.green) if is_d_done else RText("✘", color=RColor.red)
            dep_display.append(RTextList(symbol, f"#{d_id}"))

        tier = task.get('tier', 'ULV')
        prio = task.get('priority', 'Medium')

        return RTextList(
            RText(f"{server.tr('todo.common.task')}: {task['title']}\n", color=RColor.yellow),
            RText(f"{server.tr('todo.common.creator')}: {task.get('creator', server.tr('todo.common.unknown'))}\n", color=RColor.white),
            RText(f"{server.tr('todo.common.tier')}: ", color=RColor.white),
            Utils.get_tier_text(tier), "\n",
            RText(f"{server.tr('todo.common.priority')}: ", color=RColor.white),
            Utils.get_priority_text(prio), "\n",
            RText(f"{server.tr('todo.common.collaborators')}: {', '.join(task.get('collaborators', [])) or server.tr('todo.common.unassigned')}\n", color=RColor.white),
            RText(f"{server.tr('todo.common.dependencies')}: ", color=RColor.gray),
            RTextList(*[RTextList(d, " ") for d in dep_display]) if dep_display else RText(server.tr('todo.common.none'), color=RColor.gray),
            "\n",
            RText("-" * 25 + "\n"),
            RText(f"{server.tr('todo.ui.hover.latest_progress')}: {task['notes'][-1]['content'] if task.get('notes') else server.tr('todo.ui.hover.waiting_record')}",
                  styles=RStyle.italic)
        )

    @staticmethod
    def render_task_line(tid: str, task: dict, tasks_db: dict, server: ServerInterface) -> RTextBase:
        """渲染清单行"""
        is_done = task.get("status") == STATUS_DONE
        hover_info = UI.create_hover_info(tid, task, tasks_db, server)

        status_str = task.get("status", "Unknown")
        status_text = Utils.get_status_text(status_str)

        # 使用 Utils 获取颜色
        status_color = Utils.get_status_color(status_str)

        btns = RTextList()
        if is_done:
            btns.append(" ")
            btns.append(
                Utils.create_button("↺", RColor.blue, server.tr('todo.action.restore'), RAction.suggest_command, f"!!todo restore {tid}"))
        else:
            is_paused = status_str == STATUS_ON_HOLD
            toggle_btn = Utils.create_button("▶", RColor.green, server.tr('todo.action.resume'), RAction.suggest_command,
                                             f"!!todo resume {tid}") if is_paused else \
                Utils.create_button("⏸", RColor.yellow, server.tr('todo.action.pause'), RAction.suggest_command, f"!!todo pause {tid}")
            complete_btn = Utils.create_button("✔", RColor.green, server.tr('todo.action.complete'), RAction.suggest_command,
                                               f"!!todo complete {tid}")
            note_btn = Utils.create_button("✎", RColor.aqua, server.tr('todo.action.note'), RAction.suggest_command, f"!!todo note {tid} ")

            btns.append(" ")
            btns.append(toggle_btn)
            btns.append(" ")
            btns.append(complete_btn)
            btns.append(" ")
            btns.append(note_btn)

        return RTextList(
            RText(f"[#{tid}] ", color=RColor.green).c(RAction.suggest_command, f"!!todo info {tid}").h(hover_info),
            RText("[", color=status_color), status_text, RText("] ", color=status_color),
            btns, " ",
            RText(task['title']).c(RAction.suggest_command, f"!!todo info {tid}").h(hover_info)
        )

    @staticmethod
    def _render_info_row(tid: str, label: str, value: RTextBase | str, cmd: str, server: ServerInterface, is_list: bool = False,
                         value_color: RColor = RColor.white) -> RTextList:
        """
        [抽象方法] 渲染详情页中的一行交互式属性
        """
        LABEL_COLOR = RColor.gray
        action_type = "append" if is_list else "set"
        hint = server.tr('todo.action.append') if is_list else server.tr('todo.action.modify')

        cmd_str = f"!!todo {action_type} {tid} {cmd} "
        hover = server.tr('todo.ui.hover.click_to_action', hint, label)
        if is_list:
            hover += "\n" + server.tr('todo.ui.hover.remove_hint')

        # 标签部分：永远保持点击触发修改指令
        label_component = RText(f"{label}: ", color=LABEL_COLOR).h(hover).c(RAction.suggest_command, cmd_str)

        # 数值部分：处理点击事件冲突
        if isinstance(value, RTextBase):
            value_component = value.c(RAction.suggest_command, cmd_str).h(hover)
        else:
            # 如果是普通字符串，则包装点击修改/追加的交互逻辑
            value_component = RText(str(value), color=value_color).h(hover).c(RAction.suggest_command, cmd_str)

        return RTextList(label_component, value_component, "\n")

    @staticmethod
    def render_task_info(tid: str, task: dict, tasks_db: dict, server: ServerInterface) -> RTextBase:
        """
        渲染详细的任务信息界面 (已通过 _render_info_row 重构)
        """
        # 依赖列表特殊渲染逻辑
        dep_list = RTextList()
        deps = task.get("dependencies", [])
        if not deps:
            dep_list.append(RText(server.tr('todo.common.none'), color=RColor.gray))
        for i, d_id in enumerate(deps):
            d_task = tasks_db.get(str(d_id))
            if d_task:
                d_hover = UI.create_hover_info(str(d_id), d_task, tasks_db, server)
                dep_list.append(
                    RText(f"#{d_id}", color=RColor.green).h(d_hover).c(RAction.suggest_command, f"!!todo info {d_id}"))
            else:
                dep_list.append(RText(f"#{d_id}{server.tr('todo.ui.info.invalid_dep')}", color=RColor.red))
            if i < len(deps) - 1: dep_list.append(RText(", ", color=RColor.gray))

        # 日志内容构建
        notes_content = []
        if task.get("notes"):
            for n in task["notes"]:
                notes_content.append(RTextList(
                    RText(f" [{n['time']}] ", color=RColor.gray),
                    RText(f"{n['author']}: {n['content']}\n", color=RColor.white)
                ))
        else:
            notes_content.append(RText(f" {server.tr('todo.ui.info.no_records')}\n", color=RColor.dark_gray))

        return RTextList(
            RText(f"{UI.make_header(server.tr('todo.ui.info.header', tid))}\n", color=RColor.gold),

            UI._render_info_row(tid, server.tr('todo.common.title'), task['title'], "title", server),
            RText(f"{server.tr('todo.common.creator')}: ", color=RColor.gray), RText(f"{task.get('creator', server.tr('todo.common.unknown'))}\n", color=RColor.white),
            UI._render_info_row(tid, server.tr('todo.common.status'), Utils.get_status_text(task['status']), "status", server,
                                value_color=Utils.get_status_color(task['status'])),
            UI._render_info_row(tid, server.tr('todo.common.tier'), Utils.get_tier_text(task['tier']), "tier", server,
                                value_color=Utils.get_tier_color(task['tier'])),
            UI._render_info_row(tid, server.tr('todo.common.priority'), Utils.get_priority_text(task['priority']), "priority", server,
                                value_color=Utils.get_priority_color(task['priority'])),
            UI._render_info_row(tid, server.tr('todo.common.collaborators'), ', '.join(task.get('collaborator', [])) or server.tr('todo.common.unassigned'), "collaborators", server,
                                is_list=True),
            UI._render_info_row(tid, server.tr('todo.common.dependencies'), dep_list, "dependency", server, is_list=True),
            UI._render_info_row(tid, server.tr('todo.common.description'), task.get('description', server.tr('todo.ui.info.no_desc')), "description", server),

            RText("-" * 35 + "\n", color=RColor.dark_gray),
            RText(f"{server.tr('todo.ui.info.progress_header')}:\n", color=RColor.gold),
            *notes_content,
            RText(f"{UI.make_header()}\n", color=RColor.gold)
        )

    @staticmethod
    def render_help(server: ServerInterface) -> RTextBase:
        """构建帮助菜单"""

        def help_line(cmd: str, desc: str, usage: str = "", full_desc: RTextBase | str = "",
                      abbr: str = "") -> RTextList:
            hover_content = RTextList()

            # 用法展示
            hover_content.append(RText(f"{server.tr('todo.common.usage')}: ", color=RColor.gray))
            hover_content.append(RText(f"!!todo {cmd} {usage}\n", color=RColor.aqua))

            # 缩写展示
            if abbr:
                hover_content.append(RText(f"{server.tr('todo.common.alias')}: ", color=RColor.gray))
                hover_content.append(RText(f"!!todo {abbr}\n", color=RColor.aqua))

                hover_content.append(RText("-" * 20 + "\n", color=RColor.dark_gray))

            # 详细描述展示
            if full_desc != "":
                hover_content.append(full_desc)
            else:
                hover_content.append(desc)

            return RTextList(
                RText(f"!!todo {cmd}", color=RColor.aqua)
                .c(RAction.suggest_command, f"!!todo {cmd} ")
                .h(hover_content),
                RText(" : ", color=RColor.gray).c(RAction.suggest_command, f"!!todo {cmd} ").h(hover_content),
                RText(f"{desc}\n", color=RColor.white).c(RAction.suggest_command, f"!!todo {cmd} ").h(hover_content)
            )

        def build_props_info(header_key: str, props_dict: dict) -> RTextList:
            info = RTextList(RText(f"{server.tr(header_key)}\n", color=RColor.yellow))
            items = list(props_dict.items())
            for i, (prop, aliases) in enumerate(items):
                # 获取属性的本地化名称，例如 ##.prop.description
                prop_name = server.tr(f"todo.prop.{prop}")
                alias_str = ", ".join(sorted(aliases))
                info.append(RText(server.tr('todo.help.prop_item_prefix'), color=RColor.gray))
                info.append(RText(f"{prop_name}", color=RColor.gray))
                info.append(RText(server.tr('todo.help.prop_item_suffix'), color=RColor.gray))
                # 如果是最后一行，不加换行符
                suffix = "\n" if i < len(items) - 1 else ""
                info.append(RText(f"{alias_str}{suffix}", color=RColor.aqua))
            return info

        properties_info = RTextList(
            server.tr('todo.help.desc.set.main'), "\n\n",
            build_props_info('todo.help.available_props', TASK_PROPERTIES)
        )
        
        list_properties_info = RTextList(
            server.tr('todo.help.desc.list.main'), "\n\n",
            build_props_info('todo.help.available_lists', LIST_PROPERTIES)
        )

        return RTextList(
            RText(f"{UI.make_header(server.tr('todo.help.header'))}\n", color=RColor.gold),
            RText(f"{server.tr('todo.help.hint')}\n", color=RColor.gray, styles=RStyle.italic),

            help_line("list", server.tr('todo.help.list'), usage="", abbr="l"),
            help_line("archive", server.tr('todo.help.archive'), usage="", abbr="ar"),
            help_line("add", server.tr('todo.help.add'), usage="<title>", abbr="a"),
            help_line("info", server.tr('todo.help.info'), usage="<id>", abbr="i"),
            help_line("note", server.tr('todo.help.note'), usage="<id> <content>", abbr="n"),
            help_line("set", server.tr('todo.help.set'), usage="<id> <prop> <value>", full_desc=properties_info, abbr="s"),
            help_line("append", server.tr('todo.help.append'), usage="<id> <list> <value>", full_desc=list_properties_info,
                      abbr="ap"),
            help_line("remove", server.tr('todo.help.remove'), usage="<id> <list> <value>", full_desc=list_properties_info,
                      abbr="rm"),
            help_line("pause", server.tr('todo.help.pause'), usage="<id>"),
            help_line("resume", server.tr('todo.help.resume'), usage="<id>"),
            help_line("complete", server.tr('todo.help.complete'), usage="<id>"),
            help_line("restore", server.tr('todo.help.restore'), usage="<id>"),

            RText(f"{UI.make_header()}\n", color=RColor.gold)
        )

    @staticmethod
    def render_welcome(server: ServerInterface) -> RTextBase:
        """渲染欢迎界面"""
        return RTextList(
            RText(f"{UI.make_header(server.tr('todo.welcome.header'))}\n", color=RColor.gold),
            RText(f"{server.tr('todo.welcome.line1')}\n", color=RColor.white),
            RText(f"{server.tr('todo.welcome.line2')}\n", color=RColor.gray),
            Utils.create_button(server.tr('todo.welcome.btn.help'), RColor.aqua, server.tr('todo.welcome.hover.help'), RAction.suggest_command, "!!todo help"),
            " ",
            Utils.create_button(server.tr('todo.welcome.btn.list'), RColor.green, server.tr('todo.welcome.hover.list'), RAction.suggest_command, "!!todo list"),
            " ",
            Utils.create_button(server.tr('todo.welcome.btn.add'), RColor.yellow, server.tr('todo.welcome.hover.add'), RAction.suggest_command, "!!todo add ")
        )
