from mcdreforged.api.all import RTextBase, RText, RColor, RTextList, ServerInterface, CommandSource, RAction, RStyle

from . import TodoManager
from .constants import *
from .constants import PAGE_SIZE
from .enums import Status, Tier, Priority
from .utils import Utils, ItemizeBuilder


class UI:
    @staticmethod
    def make_dividing_line(content: str | RTextBase = "", width: int = 50, newline: bool = True) -> RTextBase:
        """生成居中的标题分割线"""
        if not str(content):
            line = RText("=" * width, color=RColor.gold)
        else:
            # 格式：======= [ 标题 ] =======
            # 左右各留一个空格，标题两侧加 [ ]
            remaining = width - len(str(content)) - 4
            if remaining < 0:
                line = RTextList("[ ", content, " ]").set_color(RColor.gold)  # 标题过长则直接返回
            else:
                left_pad = remaining // 2
                right_pad = remaining - left_pad

                line = RTextList("=" * left_pad, "[ ", content, " ]", "=" * right_pad).set_color(RColor.gold)
        return line + ("\n" if newline else "")

    @staticmethod
    def create_hover_info(tid: str, task: dict, tasks_db: dict, server: ServerInterface) -> RTextBase:
        """通用的任务悬浮矩阵生成器"""
        dep_display = []
        for d_id in task.get("dependencies", []):
            d_task = tasks_db.get(str(d_id))
            is_d_done = d_task and d_task.get("status") == Status.DONE.value

            color = RColor.green if is_d_done else RColor.red
            symbol = "✔" if is_d_done else "✘"

            dep_display.append(RTextList(symbol, RText(f"#{d_id}")).set_color(color))

        tier = task.get('tier', 'ULV')
        prio = task.get('priority', 'Medium')

        collabs = task.get('collaborators', [])
        collab_text = Utils.list_to_rtext(collabs) if collabs else server.tr('sakuraflow.common.unassigned')

        return RTextList(
            RText(f"{server.tr('sakuraflow.common.task')}: {task['title']}\n", color=RColor.yellow),
            RText(f"{server.tr('sakuraflow.common.creator')}: {task.get('creator', server.tr('sakuraflow.common.unknown'))}\n",
                  color=RColor.gray),
            RText(f"{server.tr('sakuraflow.common.tier')}: ", color=RColor.gray),
            Tier.get_rtext(tier), "\n",
            RText(f"{server.tr('sakuraflow.common.priority')}: ", color=RColor.gray),
            Priority.get_rtext(prio, server), "\n",
            RText(f"{server.tr('sakuraflow.common.collaborators')}: ", color=RColor.gray), collab_text, "\n",
            RText(f"{server.tr('sakuraflow.common.dependencies')}: ", color=RColor.gray),
            Utils.list_to_rtext(dep_display) if dep_display else RText(server.tr('sakuraflow.common.none'),
                                                                       color=RColor.gray),
            "\n",
            RText("-" * 25 + "\n"),
            RText(
                f"{server.tr('sakuraflow.ui.hover.latest_progress')}: {task['notes'][-1]['content'] if task.get('notes') else server.tr('sakuraflow.ui.hover.waiting_record')}",
                color=RColor.gray)
        )

    @staticmethod
    def render_task_line(tid: str, task: dict, tasks_db: dict, server: ServerInterface, source: CommandSource) -> RTextBase:
        """渲染清单行"""
        is_done = task.get("status") == Status.DONE.value
        hover_info = UI.create_hover_info(tid, task, tasks_db, server)

        status_str = task.get("status", "Unknown")
        status_text = Status.get_rtext(status_str, server)

        # 使用 Utils 获取颜色
        status_color = Status.get_color(status_str)

        btns = RTextList()
        if is_done:
            btns.append(
                Utils.create_button("↺", RColor.blue, server.tr('sakuraflow.action.restore'), f"{COMMAND_PREFIX} restore {tid}"))
        else:
            is_paused = status_str == Status.ON_HOLD.value
            toggle_btn = Utils.create_button("▶", RColor.green, server.tr('sakuraflow.action.resume'),
                                             f"{COMMAND_PREFIX} resume {tid}") if is_paused else \
                Utils.create_button("⏸", RColor.yellow, server.tr('sakuraflow.action.pause'), f"{COMMAND_PREFIX} pause {tid}")
            complete_btn = Utils.create_button("✔", RColor.green, server.tr('sakuraflow.action.complete'),
                                               f"{COMMAND_PREFIX} complete {tid}")
            note_btn = Utils.create_button("✎", RColor.aqua, server.tr('sakuraflow.action.note'), f"{COMMAND_PREFIX} note {tid} ")

            btns.append(toggle_btn, " ", complete_btn, " ", note_btn)
            if source.is_player:
                claim_btn = Utils.create_button("★", RColor.gold, server.tr('sakuraflow.action.claim'), f"{COMMAND_PREFIX} set {tid} collaborators {source.player}")
                btns.append(claim_btn)

        return RTextList(
            RText(f"[#{tid}] ", color=RColor.green).c(RAction.suggest_command, f"{COMMAND_PREFIX} info {tid}").h(hover_info),
            RText("[", color=status_color), status_text, RText("] ", color=status_color).h(hover_info),
            " ", btns, " ",
            RText(task['title']).c(RAction.suggest_command, f"{COMMAND_PREFIX} info {tid}").h(hover_info)
        )

    @staticmethod
    def _render_info_row(tid: str, label: str, value: RTextBase | str, cmd: str, server: ServerInterface,
                         is_list: bool = False,
                         value_color: RColor = RColor.white) -> RTextList:
        """
        [抽象方法] 渲染详情页中的一行交互式属性
        """
        LABEL_COLOR = RColor.gray
        action_type = "append" if is_list else "set"
        hint = server.tr('sakuraflow.action.append') if is_list else server.tr('sakuraflow.action.modify')

        cmd_str = f"{COMMAND_PREFIX} {action_type} {tid} {cmd} "
        hover = server.tr('sakuraflow.ui.hover.click_to_action', hint, label)
        if is_list:
            hover += "\n" + server.tr('sakuraflow.ui.hover.remove_hint', COMMAND_PREFIX)

        # 标签部分：永远保持点击触发修改指令
        label_component = RText(f"{label}: ", color=LABEL_COLOR).h(hover).c(RAction.suggest_command, cmd_str)

        # 数值部分：处理点击事件冲突
        if isinstance(value, RTextBase):
            value_component = value
        else:
            # 如果是普通字符串，则包装点击修改/追加的交互逻辑
            value_component = RText(str(value), color=value_color)
        value_component.h(hover).c(RAction.suggest_command, cmd_str)
        return RTextList(label_component, value_component, "\n")

    @staticmethod
    def render_task_info(tid: str, task: dict, tasks_db: dict, server: ServerInterface) -> RTextBase:
        """
        渲染详细的任务信息界面 (已通过 _render_info_row 重构)
        """
        # 依赖列表特殊渲染逻辑
        deps = task.get("dependencies", [])
        if not deps:
            dep_list = RText(server.tr('sakuraflow.common.none'), color=RColor.gray)
        else:
            dep_items = []
            for d_id in deps:
                d_task = tasks_db.get(str(d_id))
                if d_task:
                    is_d_done = d_task.get("status") == Status.DONE.value
                    color = RColor.green if is_d_done else RColor.red
                    symbol = "✔" if is_d_done else "✘"

                    d_hover = UI.create_hover_info(str(d_id), d_task, tasks_db, server)
                    dep_items.append(
                        RTextList(symbol, RText(f"#{d_id}"))
                        .set_color(color)
                        .h(d_hover)
                        .c(RAction.suggest_command, f"{COMMAND_PREFIX} info {d_id}")
                    )
                else:
                    dep_items.append(RText(f"#{d_id}{server.tr('sakuraflow.ui.info.invalid_dep')}", color=RColor.red))
            dep_list = Utils.list_to_rtext(dep_items)

        # 日志内容构建
        notes_content = []
        if task.get("notes"):
            for n in task["notes"]:
                notes_content.append(RTextList(
                    RText(f" [{n['time']}] ", color=RColor.gray),
                    RText(f"{n['author']}"),
                    COLON,
                    RText(f"{n['content']}\n")
                ))
        else:
            notes_content.append(RText(f" {server.tr('sakuraflow.ui.info.no_records')}\n", color=RColor.dark_gray))

        collabs = task.get('collaborators', [])
        collab_val = Utils.list_to_rtext(collabs) if collabs else server.tr('sakuraflow.common.unassigned')

        description = task.get('description', '')
        if not description:
            description = server.tr('sakuraflow.ui.info.no_desc')

        return RTextList(
            UI.make_dividing_line(server.tr('sakuraflow.ui.info.header', tid)),
            UI._render_info_row(tid, server.tr('sakuraflow.common.title'), task['title'], "title", server),
            RText(f"{server.tr('sakuraflow.common.creator')}: ", color=RColor.gray),
            RText(f"{task.get('creator', server.tr('sakuraflow.common.unknown'))}\n", color=RColor.white),
            UI._render_info_row(tid, server.tr('sakuraflow.common.status'), Status.get_rtext(task['status'], server),
                                "status", server, value_color=Status.get_color(task['status'])),
            UI._render_info_row(tid, server.tr('sakuraflow.common.tier'), Tier.get_rtext(task['tier']),
                                "tier", server, value_color=Tier.get_color(task['tier'])),
            UI._render_info_row(tid, server.tr('sakuraflow.common.priority'), Priority.get_rtext(task['priority'], server),
                                "priority", server, value_color=Priority.get_color(task['priority'])),
            UI._render_info_row(tid, server.tr('sakuraflow.common.collaborators'), collab_val, "collaborators", server,
                                is_list=True),
            UI._render_info_row(tid, server.tr('sakuraflow.common.dependencies'), dep_list, "dependency", server,
                                is_list=True),
            UI._render_info_row(tid, server.tr('sakuraflow.common.description'),
                                description, "description", server),

            RText("-" * 35 + "\n", color=RColor.dark_gray),
            RText(f"{server.tr('sakuraflow.ui.info.progress_header')}\n", color=RColor.gold),
            *notes_content,
            UI.make_dividing_line(newline=False)
        )

    @staticmethod
    def render_help(server: ServerInterface) -> RTextBase:
        """构建帮助菜单"""

        def help_line(cmd: str, desc: str, usage: str = "", full_desc: RTextBase | str = "",
                      abbr: str = "") -> RTextList:
            hover_content = RTextList()

            # 用法展示
            hover_content.append(RText(f"{server.tr('sakuraflow.common.usage')}: ", color=RColor.gray))
            hover_content.append(RText(f"{COMMAND_PREFIX} {cmd} {usage}\n", color=RColor.aqua))

            # 缩写展示
            if abbr:
                hover_content.append(RText(f"{server.tr('sakuraflow.common.alias')}: ", color=RColor.gray))
                hover_content.append(RText(f"{COMMAND_PREFIX} {abbr}\n", color=RColor.aqua))

                hover_content.append(RText("-" * 20 + "\n", color=RColor.dark_gray))

            # 详细描述展示
            if full_desc != "":
                hover_content.append(full_desc)
            else:
                hover_content.append(desc)

            return RTextList(
                RText(f"{COMMAND_PREFIX} {cmd}", color=RColor.aqua)
                .c(RAction.suggest_command, f"{COMMAND_PREFIX} {cmd} ")
                .h(hover_content),
                RText(" : ", color=RColor.gray).c(RAction.suggest_command, f"{COMMAND_PREFIX} {cmd} ").h(hover_content),
                RText(f"{desc}\n", color=RColor.white).c(RAction.suggest_command, f"{COMMAND_PREFIX} {cmd} ").h(hover_content)
            )

        def build_props_info(header_key: str, props_dict: dict) -> RTextList:
            # 标题独立显示
            result = RTextList(RText(f"{server.tr(header_key)}\n", color=RColor.yellow))

            # 使用 ItemizeBuilder 构建列表部分
            builder = ItemizeBuilder()
            items = list(props_dict.items())
            for i, (prop, aliases) in enumerate(items):
                prop_name = server.tr(f"sakuraflow.prop.{prop}")

                alias_items = [RText(a, color=RColor.aqua) for a in sorted(aliases)]
                alias_list = Utils.list_to_rtext(alias_items)

                line = RTextList(
                    RText(prop_name, color=RColor.gray),
                    COLON,
                    alias_list
                )
                builder.add_line(line)

            result.append(builder.build())
            return result

        properties_info = RTextList(
            server.tr('sakuraflow.help.desc.set.main'), "\n\n",
            build_props_info('sakuraflow.help.available_props', TASK_PROPERTIES)
        )

        list_properties_info = RTextList(
            server.tr('sakuraflow.help.desc.list.main'), "\n\n",
            build_props_info('sakuraflow.help.available_lists', LIST_PROPERTIES)
        )

        return RTextList(
            UI.make_dividing_line(server.tr('sakuraflow.help.header')),
            RText(f"{server.tr('sakuraflow.help.hint')}\n", color=RColor.gray, styles=RStyle.italic),

            help_line("list", server.tr('sakuraflow.help.list'), usage="", abbr="l"),
            help_line("archive", server.tr('sakuraflow.help.archive'), usage="", abbr="ar"),
            help_line("search", server.tr('sakuraflow.help.search'), usage="<query>", abbr="find"),
            help_line("add", server.tr('sakuraflow.help.add'), usage="<title>", abbr="a"),
            help_line("info", server.tr('sakuraflow.help.info'), usage="<id>", abbr="i"),
            help_line("note", server.tr('sakuraflow.help.note'), usage="<id> <content>", abbr="n"),
            help_line("set", server.tr('sakuraflow.help.set'), usage="<id> <prop> <value>", full_desc=properties_info,
                      abbr="s"),
            help_line("append", server.tr('sakuraflow.help.append'), usage="<id> <list> <value>",
                      full_desc=list_properties_info,
                      abbr="ap"),
            help_line("remove", server.tr('sakuraflow.help.remove'), usage="<id> <list> <value>",
                      full_desc=list_properties_info,
                      abbr="rm"),
            help_line("pause", server.tr('sakuraflow.help.pause'), usage="<id>"),
            help_line("resume", server.tr('sakuraflow.help.resume'), usage="<id>"),
            help_line("complete", server.tr('sakuraflow.help.complete'), usage="<id>"),
            help_line("restore", server.tr('sakuraflow.help.restore'), usage="<id>"),

            UI.make_dividing_line(newline=False)
        )

    @staticmethod
    def render_welcome(server: ServerInterface) -> RTextBase:
        """渲染欢迎界面"""
        return RTextList(
            UI.make_dividing_line(server.tr('sakuraflow.welcome.header')),
            RText(f"{server.tr('sakuraflow.welcome.line1')}\n", color=RColor.white),
            RText(f"{server.tr('sakuraflow.welcome.line2')}\n", color=RColor.gray),
            RText(f"{server.tr('sakuraflow.welcome.btn_line')}", color=RColor.gray),
            COLON,
            Utils.create_button(server.tr('sakuraflow.welcome.btn.help'), RColor.aqua, server.tr('sakuraflow.welcome.hover.help'),
                                f"{COMMAND_PREFIX} help"),
            " ",
            Utils.create_button(server.tr('sakuraflow.welcome.btn.list'), RColor.green, server.tr('sakuraflow.welcome.hover.list'),
                                f"{COMMAND_PREFIX} list"),
            " ",
            Utils.create_button(server.tr('sakuraflow.welcome.btn.add'), RColor.yellow, server.tr('sakuraflow.welcome.hover.add'),
                                f"{COMMAND_PREFIX} add ")
        )

    @staticmethod
    def render_paged_list(source: CommandSource, tasks: dict, manager: TodoManager, header_key: str, empty_key: str, 
                          input_page: int = 1, cmd_prefix: str = "list"):
        """
        渲染分页列表
        :param tasks: 要渲染的任务字典 {tid: task_data}
        :param manager: TodoManager 实例，用于查找依赖任务信息
        :param cmd_prefix: 翻页命令的前缀，例如 "search"
        """
        server = source.get_server()
        page_size = PAGE_SIZE

        # 将字典转换为列表以便切片
        filtered_tasks = []
        for tid, task in tasks.items():
            filtered_tasks.append((tid, task))

        total_items = len(filtered_tasks)

        if total_items == 0:
            source.reply(UI.make_dividing_line(server.tr(header_key), newline=False))
            source.reply(RText(server.tr(empty_key), color=RColor.gray))
            return

        total_pages = (total_items + page_size - 1) // page_size
        
        if input_page > 0:
            page = (input_page - 1) % total_pages
        else:
            page = input_page % total_pages

        start_index = page * page_size
        end_index = start_index + page_size

        # 顶部只显示标题，不显示页码
        source.reply(UI.make_dividing_line(server.tr(header_key), newline=False))

        for tid, task in filtered_tasks[start_index:end_index]:
            source.reply(UI.render_task_line(tid, task, manager.data["tasks"], server, source))

        # 底部显示页码和翻页按钮
        footer = RTextList()

        # 上一页按钮
        if page > 0:
            prev_cmd = f"{COMMAND_PREFIX} {cmd_prefix} {page}"
            footer.append(Utils.create_button("<<", RColor.aqua, server.tr("sakuraflow.action.prev_page"), prev_cmd))
        else:
            footer.append(RText("[<<]", color=RColor.gray))

        footer.append(f" {page + 1}/{total_pages} ")

        # 下一页按钮
        if page < total_pages - 1:
            next_cmd = f"{COMMAND_PREFIX} {cmd_prefix} {page + 2}"
            footer.append(Utils.create_button(">>", RColor.aqua, server.tr("sakuraflow.action.next_page"), next_cmd))
        else:
            footer.append(RText("[>>]", color=RColor.gray))

        source.reply(UI.make_dividing_line(footer, newline=False))
