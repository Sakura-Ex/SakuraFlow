from typing import Optional, Any, List

from mcdreforged.api.all import *

from .constants import *
from .constants import ITEMIZE_PREFIX


class Utils:
    @staticmethod
    def info_msg(server: ServerInterface, key: str, *args: Any) -> RTextList:
        """
        构建 [INFO] 消息
        :param server: ServerInterface 实例
        :param key: Translation Key
        :param args: 格式化参数
        :return: RTextList
        """
        content = server.tr(key, *args)

        # 如果内容是字符串，包装成 RText 并赋予绿色
        # 如果是 RTextBase，我们尝试给它设置颜色作为默认颜色
        if isinstance(content, str):
            msg_body = RText(content, color=RColor.green)
        else:
            msg_body = content.set_color(RColor.green)

        return RTextList(RText("[INFO] ", color=RColor.green), msg_body)

    @staticmethod
    def error_msg(server: ServerInterface, key: str, *args: Any) -> RTextList:
        """
        构建 [ERROR] 消息
        :param server: ServerInterface 实例
        :param key: Translation Key
        :param args: 格式化参数
        :return: RTextList
        """
        content = server.tr(key, *args)
        if isinstance(content, str):
            msg_body = RText(content, color=RColor.red)
        else:
            msg_body = content.set_color(RColor.red)

        return RTextList(RText("[ERROR] ", color=RColor.red), msg_body)

    @staticmethod
    def create_button(text: str, color: RColor, hover: str, value: str, action: RAction = RAction.suggest_command) -> RText:
        """
        创建一个带方括号的交互式按钮
        :param text: 按钮显示的文本 (例如 '✔', '▶', '查看帮助')
        :param color: 按钮文本颜色
        :param hover: 悬浮提示信息
        :param value: 点击动作的值
        :param action: 点击动作类型
        :return: RText 组件
        """
        return RText(f"[{text}]", color=color).h(hover).c(action, value)

    @staticmethod
    def list_to_rtext(val: List) -> RTextBase:
        if not val:
            return RText("")
        else:
            line = RTextList(val[0])
            for i in range(1, len(val)):
                line.append(LIST_ITEM_SEPERATOR).append(val[i])
            return line


class ItemizeBuilder:
    def __init__(self):
        self.lines = []
        self.current_level = 0
        self.max_level = len(ITEMIZE_PREFIX) - 1

    def add_line(self, text: str | RTextBase) -> 'ItemizeBuilder':
        """在当前层级添加一行"""
        self.lines.append((self.current_level, text))
        return self

    def indent(self) -> 'ItemizeBuilder':
        """增加缩进层级"""
        self.current_level = min(self.current_level + 1, self.max_level)
        return self

    def dedent(self) -> 'ItemizeBuilder':
        """减少缩进层级"""
        self.current_level = max(self.current_level - 1, 0)
        return self

    def build(self) -> RTextList:
        """构建最终的富文本列表"""
        result = RTextList()
        for i, (level, text) in enumerate(self.lines):
            prefix = ITEMIZE_PREFIX[level]

            # 确保 text 是 RTextBase 类型
            line_content = text if isinstance(text, RTextBase) else RText(text)

            # 为每行添加缩进和项目符号
            # 缩进使用空格实现
            indent_space = "  " * level

            line = RTextList(indent_space, prefix, line_content)

            # 如果不是最后一行，添加换行符
            if i < len(self.lines) - 1:
                line.append("\n")

            result.append(line)

        return result
