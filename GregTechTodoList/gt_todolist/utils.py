from mcdreforged.api.all import *
from .constants import *
from typing import Optional

class Utils:
    @staticmethod
    def get_tier_text(tier: str) -> RText:
        """获取带有颜色的电压等级文本"""
        color = TIER_COLORS.get(tier, RColor.white)
        return RText(tier, color=color)

    @staticmethod
    def get_tier_color(tier: str) -> RColor:
        """获取电压等级对应的颜色"""
        return TIER_COLORS.get(tier, RColor.white)

    @staticmethod
    def get_priority_text(priority: str) -> RText:
        """获取带有颜色的优先级文本"""
        color = PRIORITY_COLORS.get(priority, RColor.white)
        return RText(priority, color=color)

    @staticmethod
    def get_priority_color(priority: str) -> RColor:
        """获取优先级对应的颜色"""
        return PRIORITY_COLORS.get(priority, RColor.white)

    @staticmethod
    def get_status_text(status: str) -> RText:
        """获取带有颜色的状态文本"""
        color = STATUS_COLORS.get(status, RColor.white)
        return RText(status, color=color)

    @staticmethod
    def get_status_color(status: str) -> RColor:
        """获取状态对应的颜色"""
        return STATUS_COLORS.get(status, RColor.white)

    @staticmethod
    def validate_tier(val: str) -> Optional[str]:
        """
        验证并标准化电压等级输入
        :param val: 用户输入的电压等级（数字或名称）
        :return: 标准化的电压等级名称，如果无效则返回 None
        """
        tier_map = {t.upper(): t for t in GT_TIERS}
        if val.isdigit():
            idx = int(val)
            if 0 <= idx < len(GT_TIERS):
                return GT_TIERS[idx]
        elif val.upper() in tier_map:
            return tier_map[val.upper()]
        return None

    @staticmethod
    def validate_priority(val: str) -> Optional[str]:
        """
        验证并标准化优先级输入
        :param val: 用户输入的优先级（数字或名称）
        :return: 标准化的优先级名称，如果无效则返回 None
        """
        prio_map = {p.upper(): p for p in PRIORITIES}
        no_space_map = {p.replace(' ', '').upper(): p for p in PRIORITIES}

        if val.isdigit():
            idx = int(val)
            if 0 <= idx < len(PRIORITIES):
                return PRIORITIES[idx]
        elif val.upper() in prio_map:
            return prio_map[val.upper()]
        elif val.upper() in no_space_map:
            return no_space_map[val.upper()]
        return None
