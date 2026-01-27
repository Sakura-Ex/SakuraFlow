from mcdreforged.api.all import *
from .constants import *


class UI:
    @staticmethod
    def get_tier_color(tier_name: str) -> RColor:
        """获取电压等级对应的专属颜色"""
        return TIER_COLORS.get(tier_name, RColor.white)

    @staticmethod
    def get_status_color(status: str) -> RColor:
        """获取状态对应的颜色"""
        return STATUS_COLORS.get(status, RColor.gold)

    @staticmethod
    def get_priority_color(priority: str) -> RColor:
        """获取优先级对应的颜色"""
        return PRIORITY_COLORS.get(priority, RColor.gray)

    @staticmethod
    def create_hover_info(tid: str, task: dict, tasks_db: dict) -> RTextBase:
        """通用的任务悬浮矩阵生成器"""
        dep_display = []
        for d_id in task.get("dependencies", []):
            d_task = tasks_db.get(str(d_id))
            is_d_done = d_task and d_task.get("status") == STATUS_DONE
            symbol = "§a✔" if is_d_done else "§c✘"
            dep_display.append(f"{symbol}#{d_id}")

        tier = task.get('tier', 'ULV')
        prio = task.get('priority', 'Medium')

        return RTextList(
            RText(f"任务: {task['title']}\n", color=RColor.yellow),
            RText(f"创建者: {task.get('creator', '未知')}\n", color=RColor.white),
            RText("等级: ", color=RColor.white),
            RText(f"{tier}\n", color=UI.get_tier_color(tier)),
            RText("优先级: ", color=RColor.white),
            RText(f"{prio}\n", color=UI.get_priority_color(prio)),
            RText(f"负责人: {', '.join(task.get('collaborators', [])) or '独立工厂'}\n", color=RColor.white),
            RText(f"前置依赖: {' '.join(dep_display) or '无'}\n", color=RColor.gray),
            RText("-" * 25 + "\n"),
            RText(f"最新进展: {task['notes'][-1]['content'] if task.get('notes') else '等待排产'}",
                  styles=RStyle.italic)
        )

    @staticmethod
    def render_task_line(tid: str, task: dict, tasks_db: dict) -> RTextBase:
        """渲染清单行"""
        is_done = task.get("status") == STATUS_DONE
        hover_info = UI.create_hover_info(tid, task, tasks_db)

        status_str = task.get("status", "Unknown")
        status_color = UI.get_status_color(status_str)

        btns = RTextList()
        if is_done:
            btns.append(" ")
            btns.append(
                RText("[↺]", color=RColor.blue).h("恢复任务").c(RAction.suggest_command, f"!!todo restore {tid}"))
        else:
            is_paused = status_str == STATUS_ON_HOLD
            toggle_btn = RText("[▶]", color=RColor.green).h("恢复").c(RAction.suggest_command,
                                                                      f"!!todo resume {tid}") if is_paused else \
                RText("[⏸]", color=RColor.yellow).h("暂停").c(RAction.suggest_command, f"!!todo pause {tid}")
            complete_btn = RText("[✔]", color=RColor.green).h("完工").c(RAction.suggest_command,
                                                                        f"!!todo complete {tid}")
            note_btn = RText("[✎]", color=RColor.aqua).h("笔记").c(RAction.suggest_command, f"!!todo note {tid} ")

            btns.append(" ")
            btns.append(toggle_btn)
            btns.append(" ")
            btns.append(complete_btn)
            btns.append(" ")
            btns.append(note_btn)

        return RTextList(
            RText(f"[#{tid}] ", color=RColor.green).c(RAction.suggest_command, f"!!todo info {tid}").h(hover_info),
            RText(f"[{status_str}] ", color=status_color),
            btns, " ",
            RText(task['title']).c(RAction.suggest_command, f"!!todo info {tid}").h(hover_info)
        )

    @staticmethod
    def _render_info_row(tid: str, label: str, value: RTextBase | str, alias: str, is_list: bool = False,
                         value_color: RColor = RColor.white) -> RTextList:
        """
        [抽象方法] 渲染详情页中的一行交互式属性
        """
        LABEL_COLOR = RColor.gray
        action_type = "append" if is_list else "set"
        hint = "追加" if is_list else "修改"

        cmd = f"!!todo {action_type} {tid} {alias} "
        hover = f"点击{hint}{label} ({alias})"
        if is_list:
            hover += "\n使用 !!todo remove 移除项"

        # 标签部分：永远保持点击触发修改指令
        label_component = RText(f"{label}: ", color=LABEL_COLOR).h(hover).c(RAction.suggest_command, cmd)

        # 数值部分：处理点击事件冲突
        if isinstance(value, RTextBase):
            # 如果 value 已经是 RText 对象（如依赖列表），直接使用。
            # 不在外部包装点击事件，以保留其内部（如具体某个 ID）的点击 info 事件。
            value_component = value
        else:
            # 如果是普通字符串，则包装点击修改/追加的交互逻辑
            value_component = RText(str(value), color=value_color).h(hover).c(RAction.suggest_command, cmd)

        return RTextList(label_component, value_component, "\n")

    @staticmethod
    def render_task_info(tid: str, task: dict, tasks_db: dict) -> RTextBase:
        """
        渲染详细的任务信息界面 (已通过 _render_info_row 重构)
        """
        # 依赖列表特殊渲染逻辑
        dep_list = RTextList()
        deps = task.get("dependencies", [])
        if not deps:
            dep_list.append(RText("无", color=RColor.gray))
        for i, d_id in enumerate(deps):
            d_task = tasks_db.get(str(d_id))
            if d_task:
                d_hover = UI.create_hover_info(str(d_id), d_task, tasks_db)
                dep_list.append(
                    RText(f"#{d_id}", color=RColor.green).h(d_hover).c(RAction.suggest_command, f"!!todo info {d_id}"))
            else:
                dep_list.append(RText(f"#{d_id}(已失效)", color=RColor.red))
            if i < len(deps) - 1: dep_list.append("§7, ")

        # 日志内容构建
        notes_content = []
        if task.get("notes"):
            for n in task["notes"]:
                notes_content.append(RText(f" §7[{n['time']}] §f{n['author']}: {n['content']}\n"))
        else:
            notes_content.append(RText(" §8(暂无记录)\n"))

        return RTextList(
            RText(f"======= [ 任务详情 #{tid} ] =======\n", color=RColor.gold),

            UI._render_info_row(tid, "任务标题", task['title'], "title"),
            RText("创建人员: ", color=RColor.gray), RText(f"{task.get('creator', '未知')}\n", color=RColor.white),
            UI._render_info_row(tid, "当前状态", task['status'], "s", value_color=UI.get_status_color(task['status'])),
            UI._render_info_row(tid, "电压等级", task['tier'], "t", value_color=UI.get_tier_color(task['tier'])),
            UI._render_info_row(tid, "优先级别", task['priority'], "p",
                                value_color=UI.get_priority_color(task['priority'])),
            UI._render_info_row(tid, "协作人员", ', '.join(task.get('collaborators', [])) or '未分配', "c",
                                is_list=True),
            UI._render_info_row(tid, "前置依赖", dep_list, "d", is_list=True),
            UI._render_info_row(tid, "任务描述", task.get('description', '暂无描述'), "desc"),

            RText("-" * 35 + "\n", color=RColor.dark_gray),
            RText("任务进度记录:\n", color=RColor.gold),
            *notes_content,
            RText("====================================", color=RColor.gold)
        )

    @staticmethod
    def render_help() -> RTextBase:
        """构建帮助菜单"""

        def help_line(cmd: str, desc: str, usage: str = "", full_desc: RTextBase | str = "",
                      abbr: str = "") -> RTextList:
            hover_content = RTextList()

            # 用法展示
            hover_content.append(RText("用法: ", color=RColor.gray))
            hover_content.append(RText(f"!!todo {cmd} {usage}\n", color=RColor.aqua))

            # 缩写展示
            if abbr:
                hover_content.append(RText("缩写: ", color=RColor.gray))
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

        properties_info = RTextList(
            "修改任务属性。电压(t): 0-14对应(ULV-MAX)；优先级(p): 0=Very High, 4=Very Low\n",
            RText("\n可用属性:\n", color=RColor.yellow),
            RText(" • 任务描述: ", color=RColor.gray), RText("description, desc\n", color=RColor.aqua),
            RText(" • 任务状态: ", color=RColor.gray), RText("status, stat, s\n", color=RColor.aqua),
            RText(" • 电压等级: ", color=RColor.gray), RText("tier, t\n", color=RColor.aqua),
            RText(" • 优先级:   ", color=RColor.gray), RText("priority, prio, p", color=RColor.aqua),
        )

        list_properties_info = RTextList(
            "向任务的列表字段中追加或移除项。依赖项需为有效的任务ID。\n",
            RText("\n可用列表:\n", color=RColor.yellow),
            RText(" • 前置依赖: ", color=RColor.gray), RText("dependency, dep, d\n", color=RColor.aqua),
            RText(" • 协作人员: ", color=RColor.gray), RText("collaborator, collab, c\n", color=RColor.aqua),
            RText(" • 任务标签: ", color=RColor.gray), RText("label, l", color=RColor.aqua),
        )

        return RTextList(
            RText("======= [ GT TodoList 指令帮助 ] =======\n", color=RColor.gold),
            RText("提示：点击蓝色指令可填充聊天栏；鼠标移至指令上方查看详情\n", color=RColor.gray, styles=RStyle.italic),

            help_line("list", "查看进行中任务清单", usage="", abbr="l"),
            help_line("archive", "查看已完成归档记录", usage="", abbr="ar"),
            help_line("add", "立项一个新的任务", usage="<标题>", abbr="a"),
            help_line("info", "查询特定任务的详细信息", usage="<id>", abbr="i"),
            help_line("note", "追加一条任务进度记录", usage="<id> <内容>", abbr="n"),
            help_line("set", "修改任务的核心属性", usage="<id> <属性> <值>", full_desc=properties_info, abbr="s"),
            help_line("append", "向任务追加协作人或依赖", usage="<id> <列表> <值>", full_desc=list_properties_info,
                      abbr="ap"),
            help_line("remove", "从任务中移除协作人或依赖", usage="<id> <列表> <值>", full_desc=list_properties_info,
                      abbr="rm"),
            help_line("pause", "挂起当前任务", usage="<id>"),
            help_line("resume", "恢复挂起任务", usage="<id>"),
            help_line("complete", "标记任务完工并归档", usage="<id>"),
            help_line("restore", "将已完成任务重新激活", usage="<id>"),

            RText("=======================================", color=RColor.gold)
        )
