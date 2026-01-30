from enum import Enum
from typing import List, Optional

from mcdreforged.api.all import RColor, ServerInterface, RText


class BaseProperty(Enum):
    """
    支持翻译、颜色和别名的富属性枚举基类
    """

    def __new__(cls, value: str, color: RColor, aliases: List[str] = None, trans_key: Optional[str] = None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.color = color
        obj.aliases = aliases if aliases else []
        obj.trans_key = trans_key
        return obj

    def get_display_name(self, server: Optional[ServerInterface] = None) -> str:
        """获取显示名称（支持翻译）"""
        if server and self.trans_key:
            return server.tr(self.trans_key)
        return self.value

    def to_rtext(self, server: Optional[ServerInterface] = None) -> RText:
        """获取带有颜色的富文本对象"""
        return RText(self.get_display_name(server), color=self.color)

    @classmethod
    def get_rtext(cls, value: str, server: Optional[ServerInterface] = None) -> RText:
        """
        静态方法：根据值或别名获取对应的富文本对象
        如果找不到对应的枚举成员，则返回默认白色文本
        """
        member = cls.from_alias(value)
        if member:
            return member.to_rtext(server)
        return RText(value, color=RColor.white)

    @classmethod
    def get_color(cls, value: str) -> RColor:
        """
        静态方法：根据值或别名获取对应的颜色
        如果找不到对应的枚举成员，则返回默认白色
        """
        member = cls.from_alias(value)
        if member:
            return member.color
        return RColor.white

    @classmethod
    def from_alias(cls, alias: str) -> Optional['BaseProperty']:
        """通过别名或值查找枚举成员"""
        if alias is None:
            return None
        alias_lower = str(alias).lower()

        # 移除空格的匹配逻辑（针对 Priority 如 "Very High" -> "veryhigh"）
        alias_no_space = alias_lower.replace(" ", "")

        for member in cls:
            # 1. 精确匹配值 (忽略大小写)
            if member.value.lower() == alias_lower:
                return member
            # 2. 匹配别名列表
            if alias_lower in member.aliases:
                return member
            # 3. 匹配去除空格后的值 (针对 Priority)
            if member.value.lower().replace(" ", "") == alias_no_space:
                return member
        return None

    @classmethod
    def validate(cls, val: str) -> Optional[str]:
        """
        验证并标准化输入
        :param val: 用户输入的值（别名或全称）
        :return: 标准化的值名称，如果无效则返回 None
        """
        member = cls.from_alias(str(val))
        return member.value if member else None


class Status(BaseProperty):
    DONE = ("Done", RColor.green, ['done', 'd', 'finished', 'finish', 'complete', 'completed'], "todo.status.done")
    IN_PROGRESS = ("In Progress", RColor.aqua, ['in progress', 'inprogress', 'ip', 'progress', 'p', 'doing'],
                   "todo.status.in_progress")
    ON_HOLD = ("On Hold", RColor.red, ['on hold', 'onhold', 'hold', 'oh', 'h', 'pause', 'paused', 'waiting'],
               "todo.status.on_hold")


class Priority(BaseProperty):
    VERY_HIGH = ("Very High", RColor.dark_red, ['veryhigh', 'vh', '0'], "todo.priority.very_high")
    HIGH = ("High", RColor.red, ['high', 'h', '1'], "todo.priority.high")
    MEDIUM = ("Medium", RColor.yellow, ['medium', 'med', 'm', '2'], "todo.priority.medium")
    LOW = ("Low", RColor.green, ['low', 'l', '3'], "todo.priority.low")
    VERY_LOW = ("Very Low", RColor.gray, ['verylow', 'vl', '4'], "todo.priority.very_low")


class Tier(BaseProperty):
    ULV = ("ULV", RColor.dark_gray, ['0'])
    LV = ("LV", RColor.gray, ['1'])
    MV = ("MV", RColor.aqua, ['2'])
    HV = ("HV", RColor.gold, ['3'])
    EV = ("EV", RColor.dark_purple, ['4'])
    IV = ("IV", RColor.blue, ['5'])
    LuV = ("LuV", RColor.light_purple, ['6'])
    ZPM = ("ZPM", RColor.red, ['7'])
    UV = ("UV", RColor.dark_aqua, ['8'])
    UHV = ("UHV", RColor.dark_red, ['9'])
    UEV = ("UEV", RColor.green, ['10'])
    UIV = ("UIV", RColor.dark_green, ['11'])
    UXV = ("UXV", RColor.yellow, ['12'])
    OpV = ("OpV", RColor.blue, ['13'])
    MAX = ("MAX", RColor.red, ['14'])
